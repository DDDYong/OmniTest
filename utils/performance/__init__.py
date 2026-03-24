"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
性能测试模块,提供Locust性能测试的基础封装和工具函数,导出性能测试相关的核心类和工具
-------------------------------------------------
"""

# 从性能测试基类导入核心类(暂时注释,避免Locust版本不兼容问题)
# from .locust_base import (
#     PerformanceBaseTaskSet,
#     PerformanceBaseUser,
#     PerformanceTestListener,
#     LocustMaster,
#     listener
# )

# 从性能测试工具导入工具类
from .performance_utils import PerformanceUtils

# 定义公共接口
__all__ = [
    # 核心类(暂时注释,避免Locust版本不兼容问题)
    # 'PerformanceBaseTaskSet',
    # 'PerformanceBaseUser', 
    # 'PerformanceTestListener',
    # 'LocustMaster',
    # 'listener',
    # 工具类
    'PerformanceUtils'
]
