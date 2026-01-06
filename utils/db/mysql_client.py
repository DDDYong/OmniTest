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
import select
import socket
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple, Union

import pymysql
import pymysql.cursors

from config.config_manager import config_manager
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
        self.config_instance = config_manager

        # 获取数据库配置
        self.mysql_config = self.config_instance.get_mysql_config(config)

        # 获取SSH配置
        self.ssh_config = self.config_instance.get_ssh_config()

        # SSH隧道
        self.ssh_client = None
        self.local_port = None  # 本地端口
        self.forward_thread = None  # 端口转发线程
        self.server_socket = None  # socket服务器
        self._stop_forwarding = False  # 停止转发标志

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
            local_port = self.local_port if self.ssh_config['use_ssh'] else None
        )

        logger.info(f"MySQL客户端初始化成功,连接到 {self.config['host']}:{self.config['port']}/{self.config['db']}" +
                    (" (通过SSH隧道)" if self.ssh_config['use_ssh'] else ""))

    def _check_paramiko_available(self):
        """检查paramiko库是否可用"""
        return 'paramiko' in globals()

    def _create_ssh_tunnel(self):
        """
        创建SSH隧道（使用本地端口转发）
        
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

            # 获取一个可用的本地端口
            self.local_port = self._get_available_local_port()

            # 创建端口转发线程
            self.forward_thread = threading.Thread(
                target = self._forward_tunnel,
                args = (self.local_port, self.mysql_config['host'], self.mysql_config['port'])
            )
            self.forward_thread.daemon = True
            self.forward_thread.start()

            # 等待端口转发建立
            time.sleep(1)

            logger.info(f"SSH隧道创建成功,将远程 {self.mysql_config['host']}:{self.mysql_config['port']} 映射到本地端口 {self.local_port}")

        except Exception as e:
            logger.error(f"创建SSH隧道失败: {str(e)}")
            self._close_ssh_tunnel()
            raise

    def _forward_tunnel(self, local_port, remote_host, remote_port):
        """
        创建SSH隧道转发
        
        Args:
            local_port: 本地端口
            remote_host: 远程主机
            remote_port: 远程端口
        """
        try:
            # 创建本地socket服务器
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', local_port))
            self.server_socket.listen(100)
            # 设置socket为非阻塞模式，以便可以优雅退出
            self.server_socket.settimeout(1.0)

            while not self._stop_forwarding:
                try:
                    # 接受本地连接
                    client_socket, client_addr = self.server_socket.accept()

                    # 为每个连接创建转发线程
                    thread = threading.Thread(
                        target = self._handle_client,
                        args = (client_socket, remote_host, remote_port)
                    )
                    thread.daemon = True
                    thread.start()

                except socket.timeout:
                    # 超时是正常的，继续检查停止标志
                    continue
                except Exception as e:
                    if not self._stop_forwarding:
                        logger.error(f"接受客户端连接失败: {str(e)}")
                    break

        except Exception as e:
            if not self._stop_forwarding:
                logger.error(f"创建SSH隧道转发失败: {str(e)}")
        finally:
            try:
                if self.server_socket:
                    self.server_socket.close()
                    self.server_socket = None
            except:
                pass

    def _handle_client(self, client_socket, remote_host, remote_port):
        """
        处理客户端连接

        Args:
            client_socket: 客户端socket
            remote_host: 远程主机
            remote_port: 远程端口
        """
        try:
            # 通过SSH连接到远程服务器
            transport = self.ssh_client.get_transport()
            channel = transport.open_channel(
                'direct-tcpip',
                (remote_host, remote_port),
                client_socket.getpeername()
            )

            # 开始数据转发
            while True:
                r, w, x = select.select([client_socket, channel], [], [])

                if client_socket in r:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    channel.send(data)

                if channel in r:
                    data = channel.recv(1024)
                    if not data:
                        break
                    client_socket.send(data)

        except Exception as e:
            logger.error(f"处理客户端连接失败: {str(e)}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            try:
                channel.close()
            except:
                pass

    def _get_available_local_port(self):
        """
        获取一个可用的本地端口

        Returns:
            int: 可用的本地端口号
        """
        # 创建一个临时socket来获取可用端口
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # 绑定到任意可用端口
            return s.getsockname()[1]  # 返回端口号

    def _update_config_for_ssh(self):
        """
        更新数据库配置以使用SSH隧道
        """
        self.config['host'] = '127.0.0.1'  # 本地回环地址
        self.config['port'] = self.local_port  # 本地端口

    def execute_query(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> List[Dict[str, Any]]:
        """
        执行查询语句

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        return self.pool.execute_query(sql, params)

    def get_one(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> Optional[Dict[str, Any]]:
        """
        获取单条记录

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            Optional[Dict[str, Any]]: 单条记录
        """
        return self.pool.get_one(sql, params)

    def execute_update(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> int:
        """
        执行更新语句

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            int: 影响的行数
        """
        return self.pool.execute_update(sql, params)

    def execute_many(self, sql: str, params_list: List[Union[Tuple, Dict]]) -> int:
        """
        批量执行语句

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            int: 影响的总行数
        """
        return self.pool.execute_many(sql, params_list)

    def close(self):
        """
        关闭数据库客户端,释放所有资源
        """
        if hasattr(self, 'pool'):
            self.pool.close()
        self._close_ssh_tunnel()

    def _close_ssh_tunnel(self):
        """
        关闭SSH隧道
        """
        if self.ssh_client:
            try:
                # 设置停止标志
                self._stop_forwarding = True

                # 先关闭socket服务器
                if self.server_socket:
                    try:
                        self.server_socket.close()
                    except:
                        pass
                    self.server_socket = None

                # 等待转发线程结束
                if self.forward_thread and self.forward_thread.is_alive():
                    self.forward_thread.join(timeout = 2.0)

                # 关闭SSH客户端
                self.ssh_client.close()
                self.ssh_client = None
                logger.info("SSH隧道已关闭")
            except Exception as e:
                logger.error(f"关闭SSH隧道失败: {str(e)}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class ConnectionPool:
    """
    简单的数据库连接池实现
    """

    def __init__(self, config, pool_size = DEFAULT_POOL_SIZE, max_overflow = DEFAULT_MAX_OVERFLOW,
                 recycle = DEFAULT_RECYCLE, timeout = DEFAULT_TIMEOUT, local_port = None):
        """
        初始化连接池

        Args:
            config: 数据库连接配置
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            recycle: 连接回收时间（秒）
            timeout: 连接超时时间（秒）
            local_port: 本地端口（用于SSH隧道）
        """
        self.config = config
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.recycle = recycle
        self.timeout = timeout
        self.local_port = local_port

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

        # 正常创建连接（SSH隧道已经通过本地端口转发处理）
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
                    return conn
                else:
                    # 等待连接可用
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
                        raise TimeoutError(f"获取数据库连接超时,等待时间: {self.timeout}秒")

    def return_connection(self, conn):
        """
        归还数据库连接

        Args:
            conn: 数据库连接
        """
        with self.lock:
            # 检查连接是否有效
            if not self._is_valid_connection(conn, time.time()):
                # 连接无效,关闭连接
                try:
                    conn.close()
                    self.current_connections -= 1
                except:
                    pass
                return

            # 如果连接池已满,则关闭连接
            if self.connection_queue.full():
                try:
                    conn.close()
                    self.current_connections -= 1
                except:
                    pass
            else:
                # 将连接放回连接池
                self.connection_queue.put((conn, time.time()))

    def close(self):
        """
        关闭连接池,释放所有连接
        """
        with self.lock:
            while not self.connection_queue.empty():
                try:
                    conn, _ = self.connection_queue.get(block = False)
                    conn.close()
                    self.current_connections -= 1
                except:
                    pass

            logger.info(f"MySQL连接池已关闭,所有连接已释放")

    @contextmanager
    def get_connection_context(self):
        """
        上下文管理器,自动获取和归还连接

        Yields:
            pymysql.connections.Connection: 数据库连接
        """
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn:
                self.return_connection(conn)

    def execute_query(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> List[Dict[str, Any]]:
        """
        执行查询语句

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        with self.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def get_one(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> Optional[Dict[str, Any]]:
        """
        获取单条记录

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            Optional[Dict[str, Any]]: 单条记录
        """
        with self.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def execute_update(self, sql: str, params: Optional[Union[Tuple, Dict]] = None) -> int:
        """
        执行更新语句

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            int: 影响的行数
        """
        with self.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount

    def execute_many(self, sql: str, params_list: List[Union[Tuple, Dict]]) -> int:
        """
        批量执行语句

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            int: 影响的总行数
        """
        with self.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, params_list)
                conn.commit()
                return cursor.rowcount

    def transaction(self, operations: List[Tuple[str, Optional[Union[Tuple, Dict]]]]) -> bool:
        """
        执行事务

        Args:
            operations: 操作列表,每个元素为(sql, params)元组

        Returns:
            bool: 事务是否成功
        """
        with self.get_connection_context() as conn:
            try:
                with conn.cursor() as cursor:
                    for sql, params in operations:
                        cursor.execute(sql, params)
                    conn.commit()
                    return True
            except Exception as e:
                conn.rollback()
                logger.error(f"事务执行失败: {str(e)}")
                return False
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