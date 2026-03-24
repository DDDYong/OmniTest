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


# 导入通用工具 - 不依赖其他模块的工具可以直接导入
from .common import CommonUtils, util
# 导入装饰器
from .decorator import retry, timing, exception_handler, log_function, timeout, singleton
# 导入日志相关 - 核心模块, 需要首先导入
from .logger import logger
# 导入路径工具
from .path import PathUtil, path_util
# 导入断言工具（使用__import__避免关键字冲突）
assert_module = __import__('utils.assert.assertions', fromlist=['AssertUtil'])
assert_util = assert_module.AssertUtil

__all__ = [
    # 日志相关
    'logger',

    # 通用工具
    'CommonUtils', 'util',

    # 装饰器
    'retry', 'timing', 'exception_handler', 'log_function', 'timeout', 'singleton',

    # 路径工具
    'PathUtil', 'path_util',
    
    # 断言工具
    'AssertUtil', 'assert_util',

]
