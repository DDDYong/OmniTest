"""
-------------------------------------------------
File:           redis_client.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    Redis缓存连接和基本操作封装
-------------------------------------------------
"""
import json
from contextlib import contextmanager
from typing import Any, Optional, Dict, List, Union

import redis

from config.config_manager import config_manager
from ..logger_util import logger

# 尝试导入paramiko库以支持SSH隧道
ssh_enabled = False
try:
    import paramiko

    ssh_enabled = True
except ImportError:
    logger.warning("未安装paramiko库,SSH隧道功能将不可用.请使用 'pip install paramiko' 安装.")


class RedisClient:
    """Redis客户端类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Redis客户端
        
        Args:
            config: Redis配置,如果不提供则使用默认配置
        """
        # 创建配置实例
        config_instance = config_manager

        # 获取Redis配置
        self.config = config_instance.get_redis_config(config)

        # 获取SSH配置
        self.ssh_config = config_instance.get_ssh_config()

        # SSH隧道对象
        self.ssh_tunnel = None

        # 如果启用了SSH隧道,则创建隧道并更新Redis配置
        if self.ssh_config['use_ssh'] and ssh_enabled:
            self._create_ssh_tunnel()
            self.config = self._update_config_for_ssh(self.config)

        # 创建连接
        self.redis_conn = self._create_connection()

        logger.info(f"Redis客户端初始化成功,连接到 {self.config['host']}:{self.config['port']}")

    def _create_ssh_tunnel(self):
        """
        创建SSH隧道连接到Redis服务器
        """
        try:
            # 创建SSH客户端
            ssh_client = paramiko.SSHClient()

            # 自动添加未知主机密钥
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 连接SSH服务器
            logger.info(f"正在建立SSH隧道到 {self.ssh_config['ssh_host']}:{self.ssh_config['ssh_port']}")
            ssh_client.connect(
                hostname = self.ssh_config['ssh_host'],
                port = self.ssh_config['ssh_port'],
                username = self.ssh_config['ssh_username'],
                password = self.ssh_config.get('ssh_password'),
                key_filename = self.ssh_config.get('ssh_key_file'),
                passphrase = self.ssh_config.get('ssh_passphrase')
            )

            # 创建本地端口转发,将本地端口转发到远程Redis服务器
            local_port = self.ssh_config['local_bind_port'] if self.ssh_config['local_bind_port'] else 6380
            self.ssh_tunnel = ssh_client.get_transport().open_channel(
                'direct-tcpip',
                (self.config['host'], self.config['port']),
                ('127.0.0.1', local_port)
            )

            self.ssh_client = ssh_client
            self.local_ssh_port = local_port

            logger.info(f"SSH隧道建立成功,本地端口: {local_port}")

        except Exception as e:
            logger.error(f"创建SSH隧道失败: {str(e)}")
            raise

    def _update_config_for_ssh(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新Redis配置以使用SSH隧道
        
        Args:
            config: 原始Redis配置
            
        Returns:
            Dict[str, Any]: 更新后的Redis配置
        """
        updated_config = config.copy()
        # 修改连接地址为本地回环地址和SSH隧道的本地端口
        updated_config['host'] = '127.0.0.1'
        updated_config['port'] = self.local_ssh_port

        logger.debug(f"Redis配置已更新为使用SSH隧道: {updated_config['host']}:{updated_config['port']}")
        return updated_config

    def _create_connection(self):
        """
        创建Redis连接
        
        Returns:
            redis.Redis: Redis连接对象
        """
        # 构建Redis连接参数
        redis_config = {
            'host': self.config['host'],
            'port': self.config['port'],
            'db': self.config['db'],
            'password': self.config['password'],
            'decode_responses': self.config['decode_responses']
        }

        # 添加可选的超时参数
        if 'socket_connect_timeout' in self.config:
            redis_config['socket_connect_timeout'] = self.config['socket_connect_timeout']
        if 'socket_timeout' in self.config:
            redis_config['socket_timeout'] = self.config['socket_timeout']
        if 'socket_keepalive' in self.config:
            redis_config['socket_keepalive'] = self.config['socket_keepalive']

        try:
            # 连接Redis
            conn = redis.Redis(**redis_config)

            # 测试连接
            conn.ping()
            return conn
        except Exception as e:
            logger.error(f"创建Redis连接失败: {str(e)}")
            raise

    @contextmanager
    def get_connection(self):
        """
        获取Redis连接的上下文管理器
        
        Yields:
            redis.Redis: Redis连接
        """
        try:
            # 检查连接是否正常
            try:
                self.redis_conn.ping()
            except:
                # 重新连接
                self.redis_conn = self._create_connection()

            yield self.redis_conn
        except Exception as e:
            logger.error(f"获取Redis连接失败: {str(e)}")
            raise

    # String 操作
    def set(self, key: str, value: Any, ex: Optional[int] = None, px: Optional[int] = None,
            nx: bool = False, xx: bool = False) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值(会自动序列化为JSON)
            ex: 过期时间(秒)
            px: 过期时间(毫秒)
            nx: 如果为True,仅当键不存在时设置
            xx: 如果为True,仅当键存在时设置
            
        Returns:
            bool: 设置是否成功
        """
        with self.get_connection() as conn:
            try:
                # 序列化复杂数据类型
                if not isinstance(value, (str, bytes, int, float)):
                    value = json.dumps(value)

                result = conn.set(key, value, ex = ex, px = px, nx = nx, xx = xx)
                logger.debug(f"设置键值成功: {key}")
                return result
            except Exception as e:
                logger.error(f"设置键值失败: {key}, 错误: {str(e)}")
                raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取键对应的值
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            Any: 键对应的值,如果键不存在则返回默认值
        """
        with self.get_connection() as conn:
            try:
                value = conn.get(key)
                if value is None:
                    return default

                # 尝试解析JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # 如果不是JSON,则返回原始字符串
                    return value
            except Exception as e:
                logger.error(f"获取键值失败: {key}, 错误: {str(e)}")
                raise

    def delete(self, key: Union[str, List[str]]) -> int:
        """
        删除键
        
        Args:
            key: 单个键或键列表
            
        Returns:
            int: 删除的键数量
        """
        with self.get_connection() as conn:
            try:
                if isinstance(key, list):
                    count = conn.delete(*key)
                else:
                    count = conn.delete(key)
                logger.debug(f"删除键成功: {key}, 删除数量: {count}")
                return count
            except Exception as e:
                logger.error(f"删除键失败: {key}, 错误: {str(e)}")
                raise

    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            seconds: 过期时间(秒)
            
        Returns:
            bool: 设置是否成功
        """
        with self.get_connection() as conn:
            try:
                result = conn.expire(key, seconds)
                logger.debug(f"设置键过期时间成功: {key}, {seconds}秒")
                return result
            except Exception as e:
                logger.error(f"设置键过期时间失败: {key}, 错误: {str(e)}")
                raise

    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        Args:
            key: 键名
            
        Returns:
            int: 剩余生存时间(秒),如果键不存在返回-2,如果键存在但没有设置过期时间返回-1
        """
        with self.get_connection() as conn:
            try:
                result = conn.ttl(key)
                logger.debug(f"获取键剩余时间成功: {key}, 剩余时间: {result}秒")
                return result
            except Exception as e:
                logger.error(f"获取键剩余时间失败: {key}, 错误: {str(e)}")
                raise

    # Hash 操作
    def hset(self, name: str, key: str, value: Any) -> int:
        """
        设置哈希表字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 值(会自动序列化为JSON)
            
        Returns:
            int: 设置成功的字段数量
        """
        with self.get_connection() as conn:
            try:
                # 序列化复杂数据类型
                if not isinstance(value, (str, bytes, int, float)):
                    value = json.dumps(value)

                result = conn.hset(name, key, value)
                logger.debug(f"设置哈希表字段成功: {name}:{key}")
                return result
            except Exception as e:
                logger.error(f"设置哈希表字段失败: {name}:{key}, 错误: {str(e)}")
                raise

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """
        获取哈希表字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            default: 默认值
            
        Returns:
            Any: 字段对应的值,如果字段不存在则返回默认值
        """
        with self.get_connection() as conn:
            try:
                value = conn.hget(name, key)
                if value is None:
                    return default

                # 尝试解析JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            except Exception as e:
                logger.error(f"获取哈希表字段失败: {name}:{key}, 错误: {str(e)}")
                raise

    def hgetall(self, name: str) -> Dict[str, Any]:
        """
        获取哈希表所有字段和值
        
        Args:
            name: 哈希表名
            
        Returns:
            Dict[str, Any]: 哈希表所有字段和值
        """
        with self.get_connection() as conn:
            try:
                result = conn.hgetall(name)

                # 尝试解析JSON值
                decoded_result = {}
                for k, v in result.items():
                    try:
                        decoded_result[k] = json.loads(v)
                    except json.JSONDecodeError:
                        decoded_result[k] = v

                logger.debug(f"获取哈希表所有字段成功: {name}")
                return decoded_result
            except Exception as e:
                logger.error(f"获取哈希表所有字段失败: {name}, 错误: {str(e)}")
                raise

    def hdel(self, name: str, *keys) -> int:
        """
        删除哈希表字段
        
        Args:
            name: 哈希表名
            *keys: 字段名列表
            
        Returns:
            int: 删除的字段数量
        """
        with self.get_connection() as conn:
            try:
                count = conn.hdel(name, *keys)
                logger.debug(f"删除哈希表字段成功: {name}, 字段: {keys}, 删除数量: {count}")
                return count
            except Exception as e:
                logger.error(f"删除哈希表字段失败: {name}, 错误: {str(e)}")
                raise

    # List 操作
    def lpush(self, name: str, *values) -> int:
        """
        在列表左侧添加元素
        
        Args:
            name: 列表名
            *values: 要添加的元素
            
        Returns:
            int: 列表长度
        """
        with self.get_connection() as conn:
            try:
                # 序列化复杂数据类型
                serialized_values = []
                for v in values:
                    if not isinstance(v, (str, bytes, int, float)):
                        v = json.dumps(v)
                    serialized_values.append(v)

                result = conn.lpush(name, *serialized_values)
                logger.debug(f"左侧推入列表成功: {name}, 元素数量: {len(values)}")
                return result
            except Exception as e:
                logger.error(f"左侧推入列表失败: {name}, 错误: {str(e)}")
                raise

    def rpush(self, name: str, *values) -> int:
        """
        在列表右侧添加元素
        
        Args:
            name: 列表名
            *values: 要添加的元素
            
        Returns:
            int: 列表长度
        """
        with self.get_connection() as conn:
            try:
                # 序列化复杂数据类型
                serialized_values = []
                for v in values:
                    if not isinstance(v, (str, bytes, int, float)):
                        v = json.dumps(v)
                    serialized_values.append(v)

                result = conn.rpush(name, *serialized_values)
                logger.debug(f"右侧推入列表成功: {name}, 元素数量: {len(values)}")
                return result
            except Exception as e:
                logger.error(f"右侧推入列表失败: {name}, 错误: {str(e)}")
                raise

    def lrange(self, name: str, start: int, end: int) -> List[Any]:
        """
        获取列表指定范围的元素
        
        Args:
            name: 列表名
            start: 起始索引
            end: 结束索引
            
        Returns:
            List[Any]: 列表元素列表
        """
        with self.get_connection() as conn:
            try:
                values = conn.lrange(name, start, end)

                # 尝试解析JSON
                result = []
                for v in values:
                    try:
                        result.append(json.loads(v))
                    except json.JSONDecodeError:
                        result.append(v)

                logger.debug(f"获取列表范围元素成功: {name}, 范围: {start}-{end}")
                return result
            except Exception as e:
                logger.error(f"获取列表范围元素失败: {name}, 错误: {str(e)}")
                raise

    # Set 操作
    def sadd(self, name: str, *values) -> int:
        """
        添加集合元素
        
        Args:
            name: 集合名
            *values: 要添加的元素
            
        Returns:
            int: 添加的元素数量
        """
        with self.get_connection() as conn:
            try:
                # 序列化复杂数据类型
                serialized_values = []
                for v in values:
                    if not isinstance(v, (str, bytes, int, float)):
                        v = json.dumps(v)
                    serialized_values.append(v)

                result = conn.sadd(name, *serialized_values)
                logger.debug(f"添加集合元素成功: {name}, 元素数量: {len(values)}")
                return result
            except Exception as e:
                logger.error(f"添加集合元素失败: {name}, 错误: {str(e)}")
                raise

    def smembers(self, name: str) -> List[Any]:
        """
        获取集合所有元素
        
        Args:
            name: 集合名
            
        Returns:
            List[Any]: 集合元素列表
        """
        with self.get_connection() as conn:
            try:
                values = conn.smembers(name)

                # 尝试解析JSON
                result = []
                for v in values:
                    try:
                        result.append(json.loads(v))
                    except json.JSONDecodeError:
                        result.append(v)

                logger.debug(f"获取集合所有元素成功: {name}")
                return result
            except Exception as e:
                logger.error(f"获取集合所有元素失败: {name}, 错误: {str(e)}")
                raise

    # 缓存装饰器
    def cache_result(self, key_prefix: str, expire_seconds: int = 3600):
        """
        缓存函数结果的装饰器
        
        Args:
            key_prefix: 缓存键前缀
            expire_seconds: 过期时间(秒)
            
        Returns:
            function: 装饰后的函数
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args))}:{hash(str(sorted(kwargs.items())))}"

                # 尝试从缓存获取结果
                result = self.get(cache_key)
                if result is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return result

                # 执行函数
                result = func(*args, **kwargs)

                # 缓存结果
                self.set(cache_key, result, ex = expire_seconds)
                logger.debug(f"缓存结果: {cache_key}")

                return result

            return wrapper

        return decorator

    def close(self):
        """
        关闭Redis连接和SSH隧道
        """
        try:
            # 关闭Redis连接
            if hasattr(self, 'redis_conn') and self.redis_conn:
                self.redis_conn.close()
                logger.info("Redis连接已关闭")

            # 关闭SSH隧道和SSH客户端
            if hasattr(self, 'ssh_tunnel') and self.ssh_tunnel:
                self.ssh_tunnel.close()
                self.ssh_tunnel = None
                logger.info("SSH隧道已关闭")

            if hasattr(self, 'ssh_client') and self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
                logger.info("SSH客户端已关闭")

        except Exception as e:
            logger.error(f"关闭连接失败: {str(e)}")

    def __del__(self):
        """
        析构函数,确保连接被关闭
        """
        self.close()


# 创建全局Redis客户端实例
redis_client = None


def get_redis_client(config: Optional[Dict[str, Any]] = None) -> RedisClient:
    """
    获取Redis客户端实例(单例模式)
    
    Args:
        config: Redis配置
        
    Returns:
        RedisClient: Redis客户端实例
    """
    global redis_client
    if redis_client is None:
        redis_client = RedisClient(config)
    return redis_client
