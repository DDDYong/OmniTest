"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2026/03/24
-------------------------------------------------
Description:    
路径管理工具包初始化文件
-------------------------------------------------
"""

from .path_util import PathUtil

# 创建PathUtil实例
path_util = PathUtil()

__all__ = ['PathUtil', 'path_util']
