"""
-------------------------------------------------
File:           mysql_client.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    MySQL数据库连接池和增删改查操作封装,支持SSH隧道连接
-------------------------------------------------
"""
import queue
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple, Union

import pymysql
import pymysql.cursors

from config.config_manager import ConfigManager as Config
from ..logger_util import logger

# 连接池配置默认值
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 5
DEFAULT_RECYCLE = 3600  # 连接回收时间（秒）
DEFAULT_TIMEOUT = 30  # 连接超时时间（秒）

try:
    import paramiko
except ImportError:
    logger.warning("paramiko库未安装,SSH隧道功能将不可用。请安装: pip install paramiko")


class MySQLClient:
    """MySQL数据库客户端类,支持SSH隧道连接"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化MySQL客户端
        
        Args:
            config: 数据库配置,如果不提供则使用默认配置
        """
        # 获取配置实例
        self.config_instance = Config()

        # 获取数据库配置
        self.mysql_config = self.config_instance.get_mysql_config(config)

        # 获取SSH配置
        self.ssh_config = self.config_instance.get_ssh_config()

        # SSH隧道
        self.ssh_client = None
        self.ssh_tunnel = None

        # 最终使用的连接配置
        self.config = self.mysql_config.copy()

        # 如果启用SSH隧道,则创建隧道并修改连接配置
        if self.ssh_config['use_ssh'] and self._check_paramiko_available():
            self._create_ssh_tunnel()
            self._update_config_for_ssh()

        # 创建数据库连接池
        self.pool = self._create_pool()

    def _create_pool(self):
        """
        创建数据库连接池
        
        Returns:
            ConnectionPool: 连接池对象
        """
        # 获取连接池配置
        pool_config = self.mysql_config.get('pool_config', {})
        pool_size = pool_config.get('pool_size', DEFAULT_POOL_SIZE)
        max_overflow = pool_config.get('max_overflow', DEFAULT_MAX_OVERFLOW)
        recycle = pool_config.get('recycle', DEFAULT_RECYCLE)
        timeout = pool_config.get('timeout', DEFAULT_TIMEOUT)

        # 创建连接池
        return ConnectionPool(
            config = self.config,
            pool_size = pool_size,
            max_overflow = max_overflow,
            recycle = recycle,
            timeout = timeout,
            ssh_tunnel = self.ssh_tunnel if self.ssh_config['use_ssh'] else None
        )

        logger.info(f"MySQL客户端初始化成功,连接到 {self.config['host']}:{self.config['port']}/{self.config['db']}" +
                    (" (通过SSH隧道)" if self.ssh_config['use_ssh'] else ""))

    def _check_paramiko_available(self):
        """检查paramiko库是否可用"""
        return 'paramiko' in globals()

    def _create_ssh_tunnel(self):
        """
        创建SSH隧道
        
        Raises:
            Exception: SSH连接失败时抛出异常
        """
        if not self._check_paramiko_available():
            logger.error("paramiko库未安装,无法创建SSH隧道")
            raise ImportError("paramiko库未安装,无法创建SSH隧道")

        try:
            # 创建SSH客户端
            self.ssh_client = paramiko.SSHClient()

            # 自动添加主机密钥
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # SSH连接配置
            ssh_connect_config = {
                'hostname': self.ssh_config['ssh_host'],
                'port': self.ssh_config['ssh_port'],
                'username': self.ssh_config['ssh_username']
            }

            # 使用密码或密钥文件连接
            if self.ssh_config['ssh_password']:
                ssh_connect_config['password'] = self.ssh_config['ssh_password']
            elif self.ssh_config['ssh_key_file']:
                ssh_connect_config['key_filename'] = self.ssh_config['ssh_key_file']
            else:
                raise ValueError("SSH连接需要密码或私钥文件")

            logger.info(f"正在通过SSH连接到 {self.ssh_config['ssh_host']}:{self.ssh_config['ssh_port']}")
            self.ssh_client.connect(**ssh_connect_config)

            # 创建SSH隧道,将本地端口映射到远程MySQL服务器
            self.ssh_tunnel = self.ssh_client.get_transport().open_channel(
                'direct-tcpip',
                (self.mysql_config['host'], self.mysql_config['port']),
                (self.ssh_config['local_bind_address'], 0)
            )

            logger.info(f"SSH隧道创建成功,将远程 {self.mysql_config['host']}:{self.mysql_config['port']} 映射到本地端口")

        except Exception as e:
            logger.error(f"创建SSH隧道失败: {str(e)}")
            self._close_ssh_tunnel()
            raise

    def _update_config_for_ssh(self):
        """
        更新数据库配置以使用SSH隧道
        """
        self.config['host'] = self.ssh_config['local_bind_address']
        self.config['port'] = self.ssh_config['local_mysql_port']


class ConnectionPool:
    """
    简单的数据库连接池实现
    """

    def __init__(self, config, pool_size = DEFAULT_POOL_SIZE, max_overflow = DEFAULT_MAX_OVERFLOW,
                 recycle = DEFAULT_RECYCLE, timeout = DEFAULT_TIMEOUT, ssh_tunnel = None):
        """
        初始化连接池
        
        Args:
            config: 数据库连接配置
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            recycle: 连接回收时间（秒）
            timeout: 连接超时时间（秒）
            ssh_tunnel: SSH隧道对象
        """
        self.config = config
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.recycle = recycle
        self.timeout = timeout
        self.ssh_tunnel = ssh_tunnel

        # 连接队列
        self.connection_queue = queue.Queue(maxsize = pool_size)
        # 当前创建的连接数
        self.current_connections = 0
        # 锁,保证线程安全
        self.lock = threading.RLock()

        # 初始化连接池
        self._init_pool()

    def _init_pool(self):
        """
        初始化连接池,创建初始连接
        """
        for _ in range(self.pool_size):
            try:
                conn = self._create_connection()
                if conn:
                    self.connection_queue.put((conn, time.time()))
                    self.current_connections += 1
            except Exception as e:
                logger.error(f"初始化连接池失败: {str(e)}")

        logger.info(f"MySQL连接池初始化完成,初始连接数: {self.current_connections}")

    def _create_connection(self):
        """
        创建单个数据库连接
        
        Returns:
            pymysql.connections.Connection: 数据库连接
        """
        # 提取必要的连接参数
        conn_config = {
            'host': self.config['host'],
            'port': self.config['port'],
            'user': self.config['user'],
            'password': self.config['password'],
            'db': self.config['db'],
            'charset': self.config.get('charset', 'utf8mb4'),  # 默认使用utf8mb4字符集
            'cursorclass': pymysql.cursors.DictCursor
        }

        # 如果使用SSH隧道,需要特殊处理连接
        if self.ssh_tunnel:
            try:
                # 创建连接时使用SSH隧道
                conn = pymysql.connect(
                    sock = self.ssh_tunnel,
                    user = self.config['user'],
                    password = self.config['password'],
                    database = self.config['db'],
                    charset = self.config.get('charset', 'utf8mb4'),
                    cursorclass = pymysql.cursors.DictCursor
                )
                return conn
            except Exception as e:
                logger.error(f"通过SSH隧道创建数据库连接失败: {str(e)}")
                raise
        else:
            # 正常创建连接
            try:
                conn = pymysql.connect(**conn_config)
                return conn
            except Exception as e:
                logger.error(f"创建数据库连接失败: {str(e)}")
                raise

    def _is_valid_connection(self, conn, create_time):
        """
        检查连接是否有效
        
        Args:
            conn: 数据库连接
            create_time: 创建时间
            
        Returns:
            bool: 连接是否有效
        """
        # 检查连接是否已关闭
        if not conn.open:
            return False

        # 检查连接是否超过回收时间
        if time.time() - create_time > self.recycle:
            return False

        # 检查连接是否可用
        try:
            conn.ping()
            return True
        except:
            return False

    def get_connection(self):
        """
        获取一个数据库连接
        
        Returns:
            pymysql.connections.Connection: 数据库连接
        """
        with self.lock:
            # 尝试从连接池获取连接
            try:
                # 非阻塞获取连接
                conn, create_time = self.connection_queue.get(block = False)

                # 检查连接是否有效
                if not self._is_valid_connection(conn, create_time):
                    # 连接无效,关闭并创建新连接
                    try:
                        conn.close()
                        self.current_connections -= 1
                    except:
                        pass

                    # 创建新连接
                    conn = self._create_connection()
                    create_time = time.time()

                return conn

            except queue.Empty:
                # 连接池为空,检查是否可以创建新连接
                if self.current_connections < self.pool_size + self.max_overflow:
                    # 创建新的溢出连接
                    conn = self._create_connection()
                    self.current_connections += 1
                    logger.debug(f"创建溢出连接,当前连接数: {self.current_connections}")
                    return conn
                else:
                    # 达到最大连接数,等待连接可用
                    logger.debug(f"连接池已满,等待连接释放...")
                    try:
                        conn, create_time = self.connection_queue.get(timeout = self.timeout)

                        # 检查连接是否有效
                        if not self._is_valid_connection(conn, create_time):
                            # 连接无效,关闭并创建新连接
                            try:
                                conn.close()
                                self.current_connections -= 1
                            except:
                                pass

                            # 创建新连接
                            conn = self._create_connection()
                            create_time = time.time()

                        return conn
                    except queue.Empty:
                        raise TimeoutError(f"获取数据库连接超时,超时时间: {self.timeout}秒")

    def return_connection(self, conn):
        """
        归还连接到连接池
        
        Args:
            conn: 数据库连接
        """
        with self.lock:
            try:
                # 检查连接是否有效
                if conn.open:
                    # 尝试归还到连接池
                    try:
                        self.connection_queue.put((conn, time.time()), block = False)
                    except queue.Full:
                        # 连接池已满,关闭多余连接
                        conn.close()
                        self.current_connections -= 1
                        logger.debug(f"连接池已满,关闭多余连接,当前连接数: {self.current_connections}")
                else:
                    # 连接已关闭,减少计数
                    self.current_connections -= 1
                    logger.debug(f"归还已关闭的连接,当前连接数: {self.current_connections}")
            except Exception as e:
                logger.error(f"归还连接到连接池失败: {str(e)}")

    def close_all(self):
        """
        关闭所有连接
        """
        with self.lock:
            closed_count = 0

            # 关闭队列中的所有连接
            while not self.connection_queue.empty():
                try:
                    conn, _ = self.connection_queue.get(block = False)
                    if conn.open:
                        conn.close()
                        closed_count += 1
                except Exception as e:
                    logger.error(f"关闭连接失败: {str(e)}")

            self.current_connections = 0
            logger.info(f"关闭所有数据库连接,共关闭: {closed_count}个连接")

    @property
    def stats(self):
        """
        获取连接池统计信息
        
        Returns:
            Dict: 连接池统计信息
        """
        return {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'current_connections': self.current_connections,
            'available_connections': self.connection_queue.qsize()
        }

    def get_stats_string(self):
        """
        获取连接池统计信息字符串
        
        Returns:
            str: 连接池统计信息
        """
        stats = self.stats
        return (
            f"MySQL连接池统计 - 池大小: {stats['pool_size']}, "
            f"最大溢出: {stats['max_overflow']}, "
            f"当前连接数: {stats['current_connections']}, "
            f"可用连接数: {stats['available_connections']}"
        )

    def _close_ssh_tunnel(self):
        """
        关闭SSH隧道和连接
        """
        if hasattr(self, 'ssh_tunnel') and self.ssh_tunnel:
            try:
                self.ssh_tunnel.close()
                logger.info("SSH隧道已关闭")
            except Exception as e:
                logger.error(f"关闭SSH隧道失败: {str(e)}")

        if hasattr(self, 'ssh_client') and self.ssh_client:
            try:
                self.ssh_client.close()
                logger.info("SSH连接已关闭")
            except Exception as e:
                logger.error(f"关闭SSH客户端失败: {str(e)}")

        self.ssh_tunnel = None
        self.ssh_client = None

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器
        
        Yields:
            pymysql.connections.Connection: 数据库连接
        """
        conn = None
        try:
            # 从连接池获取连接
            conn = self.pool.get_connection()
            yield conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {str(e)}")
            raise
        finally:
            # 归还连接到连接池
            if conn:
                self.pool.return_connection(conn)

    def execute_query(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: SQL参数,用于防止SQL注入
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                    logger.debug(f"查询SQL执行成功: {sql}")
                    return result
                except Exception as e:
                    logger.error(f"查询SQL执行失败: {sql}, 错误: {str(e)}")
                    raise

    def execute_update(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> int:
        """
        执行更新SQL（INSERT, UPDATE, DELETE）
        
        Args:
            sql: SQL语句
            params: SQL参数,用于防止SQL注入
            
        Returns:
            int: 受影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    affected_rows = cursor.execute(sql, params)
                    conn.commit()
                    logger.debug(f"更新SQL执行成功: {sql}, 受影响行数: {affected_rows}")
                    return affected_rows
                except Exception as e:
                    conn.rollback()
                    logger.error(f"更新SQL执行失败: {sql}, 错误: {str(e)}")
                    raise

    def execute_many(self, sql: str, params_list: List[Union[Tuple, Dict]]) -> int:
        """
        批量执行SQL
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            int: 受影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    affected_rows = cursor.executemany(sql, params_list)
                    conn.commit()
                    logger.debug(f"批量SQL执行成功: {sql}, 受影响行数: {affected_rows}")
                    return affected_rows
                except Exception as e:
                    conn.rollback()
                    logger.error(f"批量SQL执行失败: {sql}, 错误: {str(e)}")
                    raise

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        Example:
            with mysql_client.transaction():
                mysql_client.execute_update("UPDATE table SET column = %s WHERE id = %s", (value, id))
                mysql_client.execute_update("INSERT INTO table VALUES (%s, %s)", (id, value))
        """
        with self.get_connection() as conn:
            # 保存原始autocommit设置
            original_autocommit = conn.autocommit
            try:
                # 开始事务
                conn.autocommit(False)
                yield conn
                # 提交事务
                conn.commit()
                logger.debug("事务提交成功")
            except Exception as e:
                # 回滚事务
                conn.rollback()
                logger.error(f"事务执行失败,已回滚: {str(e)}")
                raise
            finally:
                # 恢复自动提交设置
                conn.autocommit = original_autocommit

    def get_one(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> Optional[Dict[str, Any]]:
        """
        获取单条记录
        
        Args:
            sql: SQL语句
            params: SQL参数
            
        Returns:
            Optional[Dict[str, Any]]: 查询结果,如果没有结果则返回None
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql, params)
                    result = cursor.fetchone()
                    logger.debug(f"获取单条记录SQL执行成功: {sql}")
                    return result
                except Exception as e:
                    logger.error(f"获取单条记录SQL执行失败: {sql}, 错误: {str(e)}")
                    raise

    def get_scalar(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> Any:
        """
        获取单个值
        
        Args:
            sql: SQL语句
            params: SQL参数
            
        Returns:
            Any: 查询结果中的单个值,如果没有结果则返回None
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql, params)
                    result = cursor.fetchone()
                    if result:
                        # 返回结果的第一个值
                        return list(result.values())[0]
                    return None
                except Exception as e:
                    logger.error(f"获取单个值SQL执行失败: {sql}, 错误: {str(e)}")
                    raise

    def close(self):
        """
        关闭数据库连接池和SSH隧道
        """
        # 关闭MySQL连接池
        try:
            if hasattr(self, 'pool') and self.pool:
                self.pool.close_all()
                logger.info("MySQL连接池已关闭")
                logger.debug(self.pool.get_stats_string())
        except Exception as e:
            logger.error(f"关闭MySQL连接池失败: {str(e)}")

        # 关闭SSH隧道
        self._close_ssh_tunnel()

    def get_pool_stats(self):
        """
        获取连接池统计信息
        
        Returns:
            Dict: 连接池统计信息,即使没有初始化也返回基础结构
        """
        if hasattr(self, 'pool') and self.pool:
            try:
                stats = self.pool.stats
                stats_str = self.pool.get_stats_string()
                logger.info(f"获取MySQL连接池统计信息: {stats_str}")
                return stats
            except Exception as e:
                logger.error(f"获取连接池统计信息失败: {str(e)}")
                return {'error': str(e), 'pool_initialized': False}
        logger.warning("连接池尚未初始化")
        return {'pool_size': 0, 'max_overflow': 0, 'current_connections': 0, 'available_connections': 0,
                'pool_initialized': False}

    def __del__(self):
        """
        析构函数,确保连接被关闭
        """
        self.close()


# 创建全局MySQL客户端实例
mysql_client = None


def get_mysql_client(config: Optional[Dict[str, Any]] = None) -> MySQLClient:
    """
    获取MySQL客户端实例（单例模式）
    
    Args:
        config: 数据库配置
        
    Returns:
        MySQLClient: MySQL客户端实例
    """
    global mysql_client
    if mysql_client is None:
        mysql_client = MySQLClient(config)
    return mysql_client
