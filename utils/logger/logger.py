import logging
import logging.config
import os
from datetime import datetime


COLOR_CODES = {
    "DEBUG": "\033[0;36m",
    "INFO": "\033[0;32m",
    "WARNING": "\033[0;33m",
    "ERROR": "\033[0;31m",
    "CRITICAL": "\033[1;31m",
    "RESET": "\033[0m",
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        original_msg = record.getMessage()
        color = COLOR_CODES.get(record.levelname, COLOR_CODES["RESET"])
        reset = COLOR_CODES["RESET"]
        record.asctime = self.formatTime(record, self.datefmt)
        log_message = (
            f"{color}{record.asctime} - [{record.levelname}] - "
            f"{record.filename}:{record.lineno} - {original_msg}{reset}"
        )
        return log_message


def _get_default_log_config():
    env_override = os.environ.get("LOG_LEVEL") or os.environ.get("OMNITEST_LOG_LEVEL")
    if env_override:
        return env_override
    try:
        from config.config_manager import config

        log_level = config.get_config_value("log.level", "DEBUG")
        return log_level
    except Exception:
        pass
    env = os.environ.get("OMNITEST_ENV", "test")
    env_defaults = {"dev": "DEBUG", "test": "INFO", "prod": "WARNING"}
    return env_defaults.get(str(env).lower(), "INFO")


DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
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

        with open(abs_path, "r", encoding="utf-8") as f:
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
    def __init__(self, logger_name="OmniTest", log_file=None):
        init_logging()
        self.logger = logging.getLogger(logger_name)

        log_level = getattr(logging, DEFAULT_LOG_LEVEL.upper(), getattr(logging, "DEBUG"))
        log_dir = DEFAULT_LOG_DIR
        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            file_formatter = logging.Formatter(
                "%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)s - %(message)s"
            )
            console_formatter = ColoredFormatter()

            if log_file:
                self.log_file = log_file
            else:
                os.makedirs(log_dir, exist_ok=True)
                today = datetime.now().strftime("%Y%m%d")
                self.log_file = os.path.join(log_dir, f"test_{today}.log")

            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(_ExtraDefaultFilter())
            self.logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(console_formatter)
            console_handler.addFilter(_ExtraDefaultFilter())
            self.logger.addHandler(console_handler)
            self.logger.addFilter(_ExtraDefaultFilter())

    def get_logger(self):
        return self.logger

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    def exception(self, message):
        self.logger.exception(message)


logger = None


def get_logger():
    global logger
    if logger is None:
        logger = Logger().get_logger()
    return logger
