"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2026/03/24
-------------------------------------------------
Description:    
通用工具包初始化文件
-------------------------------------------------
"""

from .common import CommonUtils

# 创建工具类实例
util = CommonUtils()

__all__ = ['CommonUtils', 'util']
