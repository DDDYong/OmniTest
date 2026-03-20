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
import logging.config
import os
from datetime import datetime


# ANSI颜色代码
COLOR_CODES = {
    'DEBUG': '\033[0;36m',  # 青色
    'INFO': '\033[0;32m',  # 绿色
    'WARNING': '\033[0;33m',  # 黄色
    'ERROR': '\033[0;31m',  # 红色
    'CRITICAL': '\033[1;31m',  # 亮红色
    'RESET': '\033[0m'  # 重置颜色
}


# 自定义彩色格式化器
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        # 保存原始消息
        original_msg = record.getMessage()

        # 获取日志级别对应的颜色
        color = COLOR_CODES.get(record.levelname, COLOR_CODES['RESET'])
        reset = COLOR_CODES['RESET']

        # 格式化时间
        record.asctime = self.formatTime(record, self.datefmt)

        # 构建带颜色的日志消息（整行同一颜色）
        log_message = f'{color}{record.asctime} - [{record.levelname}] - {record.filename}:{record.lineno} - {original_msg}{reset}'

        return log_message


def _get_default_log_config():
    """获取默认日志级别"""
    env_override = os.environ.get("LOG_LEVEL") or os.environ.get("OMNITEST_LOG_LEVEL")
    if env_override:
        return env_override
    try:
        # 读取配置文件
        import yaml
        env = os.environ.get('OMNITEST_ENV', 'test')  # 默认为test环境
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', f'{env}.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding = 'utf-8') as f:
                config = yaml.safe_load(f)
                log_level = config.get('log', {}).get('level', 'DEBUG')
                return log_level
    except Exception:
        pass
    env = os.environ.get('OMNITEST_ENV', 'test')
    env_defaults = {"dev": "DEBUG", "test": "INFO", "prod": "WARNING"}
    return env_defaults.get(str(env).lower(), "INFO")


DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
DEFAULT_LOG_LEVEL = _get_default_log_config()
_LOGGING_INITIALIZED = False


class _ExtraDefaultFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "config_alias"):
            record.config_alias = "-"
        if not hasattr(record, "reload"):
            record.reload = "-"
        if not hasattr(record, "module_name"):
            record.module_name = record.name
        return True


def _attach_default_filters() -> None:
    default_filter = _ExtraDefaultFilter()
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(default_filter)
    root.addFilter(default_filter)

    app = logging.getLogger("OmniTest")
    for handler in app.handlers:
        handler.addFilter(default_filter)
    app.addFilter(default_filter)


def init_logging() -> bool:
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return True

    config_path = os.environ.get("LOG_CONFIG_PATH") or os.environ.get("OMNITEST_LOGGING_CONFIG")
    if not config_path and str(os.environ.get("OMNITEST_USE_LOGGING_YAML", "")).strip() in {"1", "true", "True"}:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, "config", "logging.yaml")

    if not config_path:
        return False

    abs_path = os.path.abspath(config_path)
    try:
        import yaml

        with open(abs_path, "r", encoding = "utf-8") as f:
            config = yaml.safe_load(f) or {}
        if not isinstance(config, dict):
            return False
        logging.config.dictConfig(config)
        _attach_default_filters()
        _LOGGING_INITIALIZED = True
        return True
    except Exception:
        return False


def set_log_level(level: str) -> None:
    target = get_logger()
    try:
        numeric = getattr(logging, str(level).upper())
    except Exception:
        numeric = logging.INFO
    target.setLevel(numeric)
    for handler in target.handlers:
        handler.setLevel(numeric)


def refresh_log_level() -> str:
    level = _get_default_log_config()
    set_log_level(level)
    return level


class Logger:
    """日志记录器类"""

    def __init__(self, logger_name = "OmniTest", log_file = None):
        """
        初始化日志记录器
        
        Args:
            logger_name: 日志记录器名称
            log_file: 日志文件路径,默认为None使用配置中的日志文件
        """
        init_logging()
        self.logger = logging.getLogger(logger_name)

        log_level = getattr(logging, DEFAULT_LOG_LEVEL.upper(), getattr(logging, "DEBUG"))
        log_dir = DEFAULT_LOG_DIR
        self.logger.setLevel(log_level)

        # 避免重复添加处理器
        if not self.logger.handlers:
            # 创建格式化器
            file_formatter = logging.Formatter(
                '%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)s - %(message)s'
            )
            # 创建彩色格式化器用于控制台
            console_formatter = ColoredFormatter()

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
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(_ExtraDefaultFilter())
            self.logger.addHandler(file_handler)

            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(console_formatter)
            console_handler.addFilter(_ExtraDefaultFilter())
            self.logger.addHandler(console_handler)
            self.logger.addFilter(_ExtraDefaultFilter())

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


# 懒加载logger实例, 避免循环依赖
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


# 向后兼容: 确保直接导入logger时可用
logger = get_logger()
