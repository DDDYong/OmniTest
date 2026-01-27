"""
-------------------------------------------------
File:           __init__.py
Author:         duanyang
Date:           2026/01/17
-------------------------------------------------
Description:
性能测试用例包
-------------------------------------------------
"""

from .locust_template import PerformanceTestUser, BusinessTaskSet
# 导入Locust测试脚本
from .lottery_locust_test import LotteryUser

__all__ = [
    'LotteryUser',
    'PerformanceTestUser',
    'BusinessTaskSet'
]
