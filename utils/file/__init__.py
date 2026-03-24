"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2026/03/24
-------------------------------------------------
Description:    
文件处理工具包初始化文件
-------------------------------------------------
"""

from .file_handler import FileHandler

# 定义DataHandler作为FileHandler的别名,保持代码兼容性
DataHandler = FileHandler

__all__ = ['FileHandler', 'DataHandler']
