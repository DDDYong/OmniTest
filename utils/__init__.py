"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
工具模块包,提供各种辅助功能和工具类
-------------------------------------------------
"""

# 导入子模块 - 仅在需要时导入，避免循环依赖
# from . import api
# from . import app
# from . import db
# 暂时注释掉导入performance模块,避免依赖问题
# from . import performance
# from . import web

# 导入通用工具 - 不依赖其他模块的工具可以直接导入
from .common_util import CommonUtils, util
# 导入装饰器
from .decorator_util import retry, timing, exception_handler, log_function, timeout, singleton
# 导入数据处理相关
from .file_util import FileHandler
# 导入日志相关 - 核心模块，需要首先导入
from .logger_util import logger
# 导入路径工具
from .path_util import PathUtil, path_util
# 导入截图工具
from .screenshot_util import ScreenshotUtils

# 数据库客户端 - 延迟导入，避免循环依赖
# from .db.mysql_client import MySQLClient
# from .db.redis_client import RedisClient


__all__ = [
    # 日志相关
    'logger',

    # 数据处理相关
    'FileHandler',

    # 通用工具
    'CommonUtils', 'util',

    # 截图工具
    'ScreenshotUtils',

    # 装饰器
    'retry', 'timing', 'exception_handler', 'log_function', 'timeout', 'singleton',

    # 路径工具
    'PathUtil', 'path_util',

    # 数据库相关 - 延迟导入，避免循环依赖
    # 'MySQLClient', 'RedisClient',

    # 子模块 - 延迟导入，避免循环依赖
    # 'api',
    # 'app',
    # 'performance',
    # 'web',
    # 'database'
]
