"""
-------------------------------------------------
File:           logger_util.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
日志工具模块,提供统一的日志记录功能,支持文件和控制台输出,包含不同级别的日志记录方法
-------------------------------------------------
"""
import logging
import os
from datetime import datetime

# 避免循环导入,使用默认值,在运行时动态获取配置
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
DEFAULT_LOG_LEVEL = 'INFO'


class Logger:
    """日志记录器类"""

    def __init__(self, logger_name = "OmniTest", log_file = None):
        """
        初始化日志记录器
        
        Args:
            logger_name: 日志记录器名称
            log_file: 日志文件路径,默认为None使用配置中的日志文件
        """
        self.logger = logging.getLogger(logger_name)

        # 注意：使用延迟导入避免循环依赖
        try:
            # 仅在需要时导入配置
            from config.config_manager import config
            log_level = getattr(logging, config.LOG_LEVEL, getattr(logging, DEFAULT_LOG_LEVEL))
            log_dir = config.LOG_DIR
        except (ImportError, AttributeError):
            # 如果无法导入配置,使用默认值
            log_level = getattr(logging, DEFAULT_LOG_LEVEL)
            log_dir = DEFAULT_LOG_DIR

        self.logger.setLevel(log_level)

        # 避免重复添加处理器
        if not self.logger.handlers:
            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)s - %(message)s'
            )

            # 文件处理器
            if log_file:
                self.log_file = log_file
            else:
                # 确保日志目录存在
                os.makedirs(log_dir, exist_ok = True)
                # 按日期生成日志文件名
                today = datetime.now().strftime('%Y%m%d')
                self.log_file = os.path.join(log_dir, f"test_{today}.log")

            file_handler = logging.FileHandler(self.log_file, encoding = 'utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        """
        获取日志记录器实例
        
        Returns:
            logger: 日志记录器实例
        """
        return self.logger

    def debug(self, message):
        """记录debug级别日志"""
        self.logger.debug(message)

    def info(self, message):
        """记录info级别日志"""
        self.logger.info(message)

    def warning(self, message):
        """记录warning级别日志"""
        self.logger.warning(message)

    def error(self, message):
        """记录error级别日志"""
        self.logger.error(message)

    def critical(self, message):
        """记录critical级别日志"""
        self.logger.critical(message)

    def exception(self, message):
        """记录异常日志"""
        self.logger.exception(message)


# 懒加载logger实例，避免循环依赖
logger = None


def get_logger():
    """
    获取或创建logger实例（懒加载模式）
    
    Returns:
        logger: 日志记录器实例
    """
    global logger
    if logger is None:
        logger = Logger().get_logger()
    return logger


# 向后兼容：确保直接导入logger时可用
logger = get_logger()
