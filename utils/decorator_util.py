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
    # 使用默认值, 避免在装饰时导入config
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
                    logger.warning("无法导入config模块, 使用默认的重试配置")

            last_exception = None
            for attempt in range(actual_max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e)

                    # 检查是否包含502错误信息, 如果是则直接终止进程
                    if "502" in error_str or "too many 502 error responses" in error_str:
                        logger.error(f"检测到502错误, 服务不可用, 直接终止进程: {error_str}")
                        import sys
                        sys.exit(1)

                    logger.info(f"函数 {func.__name__} 尝试 {attempt + 1}/{actual_max_retries} 失败: {error_str}")
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


def wait(delay_seconds = None):
    """
    等待装饰器
    在函数执行前等待指定时间

    Args:
        delay_seconds: 等待时间（秒）,默认使用配置文件中的默认等待时间

    Returns:
        function: 装饰后的函数
    """
    # 使用默认值, 避免在装饰时导入config
    default_delay = delay_seconds if delay_seconds is not None else 1

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 在实际执行时获取配置值
            actual_delay = default_delay

            # 只有在需要时才导入config
            if delay_seconds is None:
                try:
                    from config.config_manager import config
                    actual_delay = config.DEFAULT_WAIT_TIME
                except ImportError:
                    logger.warning("无法导入config模块, 使用默认的等待配置")

            # 记录等待信息
            logger.info(f"函数 {func.__name__} 开始等待 {actual_delay} 秒")

            # 执行等待
            time.sleep(actual_delay)

            logger.info(f"函数 {func.__name__} 等待完成, 开始执行")

            # 执行原函数
            return func(*args, **kwargs)

        return wrapper

    return decorator


def wait_random(min_delay = 1, max_delay = 5):
    """
    随机等待装饰器
    在函数执行前等待随机时长

    Args:
        min_delay: 最小等待时间（秒）
        max_delay: 最大等待时间（秒）

    Returns:
        function: 装饰后的函数
    """
    import random

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成随机等待时间
            actual_delay = random.uniform(min_delay, max_delay)

            # 记录等待信息
            logger.info(f"函数 {func.__name__} 开始随机等待 {actual_delay:.2f} 秒 (范围: {min_delay}-{max_delay}秒)")

            # 执行等待
            time.sleep(actual_delay)

            logger.info(f"函数 {func.__name__} 随机等待完成, 开始执行")

            # 执行原函数
            return func(*args, **kwargs)

        return wrapper

    return decorator


def wait_with_jitter(base_delay = 2, jitter_factor = 0.3, jitter_type = "relative"):
    """
    带抖动的等待装饰器
    在基础等待时间上添加随机抖动

    Args:
        base_delay: 基础等待时间（秒）
        jitter_factor: 抖动因子
        jitter_type: 抖动类型
            - "relative": 相对抖动（默认）, jitter_factor为比例（0-1之间）
            - "absolute": 绝对抖动, jitter_factor为绝对时间（秒）, 支持正负值

    Returns:
        function: 装饰后的函数
    """
    import random

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 根据抖动类型计算抖动范围
            if jitter_type == "relative":
                # 相对抖动：jitter_factor为比例（0-1之间）
                jitter_range = base_delay * jitter_factor
                min_delay = base_delay - jitter_range
                max_delay = base_delay + jitter_range
                jitter_description = f"±{jitter_factor * 100:.0f}%"
            else:
                # 绝对抖动：jitter_factor为绝对时间（秒）, 支持正负值
                min_delay = base_delay + jitter_factor
                max_delay = base_delay - jitter_factor
                jitter_description = f"±{abs(jitter_factor)}秒"

            # 确保最小延迟不小于0.1秒
            min_delay = max(0.1, min_delay)
            max_delay = max(0.1, max_delay)

            # 如果最大值小于最小值, 交换它们
            if max_delay < min_delay:
                min_delay, max_delay = max_delay, min_delay

            # 生成带抖动的等待时间
            actual_delay = random.uniform(min_delay, max_delay)

            # 记录等待信息
            logger.info(f"函数 {func.__name__} 开始带抖动等待 {actual_delay:.2f} 秒 (基础: {base_delay}秒, 抖动: {jitter_description})")

            # 执行等待
            time.sleep(actual_delay)

            logger.info(f"函数 {func.__name__} 带抖动等待完成, 开始执行")

            # 执行原函数
            return func(*args, **kwargs)

        return wrapper

    return decorator


def wait_after(delay_seconds = None):
    """
    后等待装饰器
    在函数执行后等待指定时间

    Args:
        delay_seconds: 等待时间（秒）,默认使用配置文件中的默认等待时间

    Returns:
        function: 装饰后的函数
    """
    # 使用默认值, 避免在装饰时导入config
    default_delay = delay_seconds if delay_seconds is not None else 1

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 在实际执行时获取配置值
            actual_delay = default_delay

            # 只有在需要时才导入config
            if delay_seconds is None:
                try:
                    from config.config_manager import config
                    actual_delay = config.DEFAULT_WAIT_TIME
                except ImportError:
                    logger.warning("无法导入config模块, 使用默认的等待配置")

            # 执行原函数
            result = func(*args, **kwargs)

            # 记录等待信息
            logger.info(f"函数 {func.__name__} 执行完成, 开始等待 {actual_delay} 秒")

            # 执行等待
            time.sleep(actual_delay)

            logger.info(f"函数 {func.__name__} 等待完成")

            return result

        return wrapper

    return decorator


def wait_until(condition_func = None, timeout = None, interval = 1):
    """
    条件等待装饰器
    等待条件满足后再执行函数

    Args:
        condition_func: 条件判断函数, 返回True表示条件满足
        timeout: 最大等待时间（秒）, 默认无限等待
        interval: 检查间隔（秒）

    Returns:
        function: 装饰后的函数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            wait_count = 0

            # 如果有条件函数, 等待条件满足
            if condition_func:
                logger.info(f"函数 {func.__name__} 等待条件满足...")

                while True:
                    wait_count += 1

                    # 检查条件
                    try:
                        if condition_func():
                            logger.info(f"函数 {func.__name__} 条件已满足, 等待 {wait_count} 次后开始执行")
                            break
                    except Exception as e:
                        logger.warning(f"条件检查失败: {str(e)}")

                    # 检查超时
                    if timeout and (time.time() - start_time) >= timeout:
                        logger.error(f"函数 {func.__name__} 等待超时（{timeout}秒）, 条件未满足")
                        raise TimeoutError(f"等待条件超时（{timeout}秒）")

                    # 等待间隔
                    time.sleep(interval)

            # 执行原函数
            return func(*args, **kwargs)

        return wrapper

    return decorator


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
    # 使用默认值, 避免在装饰时导入config
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
                    logger.warning("无法导入config模块, 使用默认的超时配置")

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