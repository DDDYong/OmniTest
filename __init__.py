"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2026/01/17
-------------------------------------------------
Description:
OmniTest自动化测试框架主包
-------------------------------------------------
"""

# 设置包的版本
__version__ = "1.0.0"

# 导入核心模块
from .config.config_manager import config_manager, config

# 定义导出内容
__all__ = [
    # 配置管理
    'config_manager',
    'config',

    # 工具模块(从utils.__all__继承)
    *__import__('utils').__all__
]
