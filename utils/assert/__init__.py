"""
-------------------------------------------------
Package:        utils.assert
Description:    断言工具包
-------------------------------------------------
"""

from .assertions import AssertUtil, default_assert_util

# 导出便捷函数
from .assertions import (
    assert_equal,
    assert_contains,
    assert_true,
    assert_false,
    assert_not_none,
    assert_instance,
    assert_status_code,
    assert_element_displayed,
    assert_element_text
)

__all__ = [
    'AssertUtil',
    'default_assert_util',
    'assert_equal',
    'assert_contains',
    'assert_true',
    'assert_false',
    'assert_not_none',
    'assert_instance',
    'assert_status_code',
    'assert_element_displayed',
    'assert_element_text'
]
