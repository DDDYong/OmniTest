"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
Web自动化测试模块,导出ElementHandler和WebBasePage等Web测试相关类
-------------------------------------------------
"""
from .element_handler import ElementHandler
from .web_base_page import WebBasePage

__all__ = [
    'ElementHandler',
    'WebBasePage'
]
