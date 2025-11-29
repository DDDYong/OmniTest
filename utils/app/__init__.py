"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
APP自动化模块,导出AppiumManager和AppBasePage等APP测试相关类
-------------------------------------------------
"""

from .app_base_page import AppBasePage
from .appium_manager import AppiumManager

__all__ = ['AppiumManager', 'AppBasePage']
