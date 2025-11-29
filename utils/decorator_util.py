"""
-------------------------------------------------
File:           decorator_util.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
装饰器模块,提供常用的装饰器函数,如重试、计时、异常处理、日志记录、超时控制和单例模式等
-------------------------------------------------
"""
import functools
import time

from utils.logger_util import logger


# 导入移至函数内部避免循环依赖


def retry(max_retries = None, delay = None, exceptions = (Exception,)):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数,默认使用配置文件中的值
        delay: 重试间隔（秒）,默认使用配置文件中的值
        exceptions: 捕获的异常类型
        
    Returns:
        function: 装饰后的函数
    """
    # 使用默认值，避免在装饰时导入config
    default_max_retries = max_retries if max_retries is not None else 3
    default_delay = delay if delay is not None else 1

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 在实际执行时获取配置值
            actual_max_retries = default_max_retries
            actual_delay = default_delay

            # 只有在需要时才导入config
            if max_retries is None or delay is None:
                try:
                    from config.config_manager import config
                    if max_retries is None:
                        actual_max_retries = config.DEFAULT_RETRY_COUNT
                    if delay is None:
                        actual_delay = config.RETRY_INTERVAL
                except ImportError:
                    logger.warning("无法导入config模块，使用默认的重试配置")

            last_exception = None
            for attempt in range(actual_max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.info(f"函数 {func.__name__} 尝试 {attempt + 1}/{actual_max_retries} 失败: {str(e)}")
                    if attempt < actual_max_retries - 1:
                        logger.info(f"{actual_delay}秒后重试...")
                        time.sleep(actual_delay)
            logger.error(f"函数 {func.__name__} 达到最大重试次数 {actual_max_retries} 后执行失败")
            raise last_exception

        return wrapper

    return decorator


def timing(func):
    """
    计时装饰器
    记录函数执行时间
    
    Args:
        func: 要装饰的函数
        
    Returns:
        function: 装饰后的函数
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"函数 {func.__name__} 执行耗时: {execution_time:.4f} 秒")
        return result

    return wrapper


def exception_handler(exceptions = (Exception,), default_value = None):
    """
    异常处理装饰器
    捕获指定的异常并返回默认值
    
    Args:
        exceptions: 要捕获的异常类型
        default_value: 捕获异常后返回的默认值
        
    Returns:
        function: 装饰后的函数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.error(f"函数 {func.__name__} 执行异常: {str(e)}")
                logger.exception("异常详情:")
                return default_value

        return wrapper

    return decorator


def log_function(func):
    """
    日志装饰器
    记录函数的调用和返回值
    
    Args:
        func: 要装饰的函数
        
    Returns:
        function: 装饰后的函数
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 记录函数调用
        logger.info(f"调用函数 {func.__name__}")
        logger.debug(f"参数: args={args}, kwargs={kwargs}")

        # 执行函数
        try:
            result = func(*args, **kwargs)
            # 记录返回值
            logger.debug(f"函数 {func.__name__} 返回: {result}")
            logger.info(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
            raise

    return wrapper


def timeout(seconds = None):
    """
    超时装饰器
    限制函数的执行时间
    
    Args:
        seconds: 超时时间（秒）,默认使用配置文件中的默认超时时间
        
    Returns:
        function: 装饰后的函数
    """
    # 使用默认值，避免在装饰时导入config
    default_seconds = seconds if seconds is not None else 30

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 在实际执行时获取配置值
            actual_seconds = default_seconds

            # 只有在需要时才导入config
            if seconds is None:
                try:
                    from config.config_manager import config
                    actual_seconds = config.DEFAULT_TIMEOUT
                except ImportError:
                    logger.warning("无法导入config模块，使用默认的超时配置")

            # 定义超时异常
            class TimeoutError(Exception):
                pass

            # 定义目标函数的包装器
            def target():
                nonlocal result, exception
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    exception = e

            # 初始化结果和异常
            result = None
            exception = None

            # 创建并启动线程
            import threading
            thread = threading.Thread(target = target)
            thread.daemon = True
            thread.start()

            # 等待线程完成或超时
            thread.join(actual_seconds)

            # 检查线程是否仍然在运行
            if thread.is_alive():
                raise TimeoutError(f"函数 {func.__name__} 执行超时（{actual_seconds}秒）")

            # 如果有异常,重新抛出
            if exception is not None:
                raise exception

            # 返回结果
            return result

        return wrapper

    return decorator


def singleton(cls):
    """
    单例模式装饰器
    确保类只有一个实例
    
    Args:
        cls: 要装饰的类
        
    Returns:
        class: 装饰后的类
    """
    instances = {}

    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
