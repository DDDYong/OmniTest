"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
接口自动化测试模块,导出ApiClient和RequestManager等接口测试相关类
-------------------------------------------------
"""
from .api_client import ApiClient
from .request_manager import RequestManager

__all__ = [
    'ApiClient',
    'RequestManager'
]
