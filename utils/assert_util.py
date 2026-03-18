"""
-------------------------------------------------
File:           assert_util.py
Author:         duanyang
Date:           2025/12/01
-------------------------------------------------
Description:
断言工具模块
提供统一的断言方法, 集成日志记录和失败截图功能适用于API、Web和App测试断言场景
-------------------------------------------------
"""
from typing import Any, Optional, Union

# 直接导入依赖模块
from utils.logger_util import logger
from utils.screenshot_util import ScreenshotUtils


class AssertUtil:
    """
    断言工具类
    提供统一的断言方法, 集成日志和失败截图功能
    """

    def __init__(self, driver: Optional[Any] = None):
        """
        初始化断言工具
        
        Args:
            driver: WebDriver或AppiumDriver实例, 用于截图功能
        """
        self.driver = driver

    def _log_assertion(self, condition: bool, message: str, details: Optional[str] = None) -> None:
        """
        记录断言信息并在失败时截图
        
        Args:
            condition: 断言条件
            message: 断言消息
            details: 详细信息（如期望值和实际值）
        """
        log_message = f"断言: {message}"
        if details:
            log_message += f"\n详情: {details}"

        if not condition:
            # 断言失败时记录错误日志
            if logger:
                logger.error(log_message)
            else:
                print(f"ERROR: {log_message}")

            # 尝试截图
            if self.driver and ScreenshotUtils:
                try:
                    screenshot_utils = ScreenshotUtils()
                    screenshot_utils.capture_screenshot(
                        driver = self.driver,
                        filename = f"assert_failure_{message[:30]}",
                        description = f"断言失败: {message}"
                    )
                except Exception as e:
                    if logger:
                        logger.error(f"截图失败: {e}")
                    else:
                        print(f"ERROR: 截图失败 - {e}")

    # 基本断言方法
    def equals(self, actual: Any, expected: Any, message: str = "值不相等") -> 'AssertUtil':
        """
        断言两个值相等
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"期望值={expected}, 实际值={actual}"
        self._log_assertion(actual == expected, message, details)
        assert actual == expected, f"{message}\n{details}"
        return self

    def not_equals(self, actual: Any, expected: Any, message: str = "值不应相等") -> 'AssertUtil':
        """
        断言两个值不相等
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"值={actual}不应等于{expected}"
        self._log_assertion(actual != expected, message, details)
        assert actual != expected, f"{message}\n{details}"
        return self

    def contains(self, container: Union[
        str, list, dict, set], item: Any, message: str = "不包含指定元素") -> 'AssertUtil':
        """
        断言容器包含指定元素
        
        Args:
            container: 容器对象（字符串、列表、字典、集合等）
            item: 要检查的元素
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"容器={container}, 元素={item}"
        self._log_assertion(item in container, message, details)
        assert item in container, f"{message}\n{details}"
        return self

    def not_contains(self, container: Union[
        str, list, dict, set], item: Any, message: str = "应不包含指定元素") -> 'AssertUtil':
        """
        断言容器不包含指定元素
        
        Args:
            container: 容器对象
            item: 要检查的元素
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"容器={container}, 元素={item}"
        self._log_assertion(item not in container, message, details)
        assert item not in container, f"{message}\n{details}"
        return self

    def is_true(self, condition: bool, message: str = "条件应为True") -> 'AssertUtil':
        """
        断言条件为True
        
        Args:
            condition: 要检查的条件
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"条件值={condition}"
        self._log_assertion(bool(condition), message, details)
        assert bool(condition), f"{message}\n{details}"
        return self

    def is_false(self, condition: bool, message: str = "条件应为False") -> 'AssertUtil':
        """
        断言条件为False
        
        Args:
            condition: 要检查的条件
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"条件值={condition}"
        self._log_assertion(not condition, message, details)
        assert not condition, f"{message}\n{details}"
        return self

    def is_none(self, value: Any, message: str = "值应为None") -> 'AssertUtil':
        """
        断言值为None
        
        Args:
            value: 要检查的值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"值={value}"
        self._log_assertion(value is None, message, details)
        assert value is None, f"{message}\n{details}"
        return self

    def is_not_none(self, value: Any, message: str = "值不应为None") -> 'AssertUtil':
        """
        断言值不为None
        
        Args:
            value: 要检查的值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"值={value}"
        self._log_assertion(value is not None, message, details)
        assert value is not None, f"{message}\n{details}"
        return self

    def is_instance(self, obj: Any, expected_type: type, message: str = "类型不匹配") -> 'AssertUtil':
        """
        断言对象为指定类型
        
        Args:
            obj: 要检查的对象
            expected_type: 期望的类型
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"对象类型={type(obj).__name__}, 期望类型={expected_type.__name__}"
        self._log_assertion(isinstance(obj, expected_type), message, details)
        assert isinstance(obj, expected_type), f"{message}\n{details}"
        return self

    def greater_than(self, actual: Union[int, float], expected: Union[
        int, float], message: str = "值应大于期望值") -> 'AssertUtil':
        """
        断言实际值大于期望值
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"实际值={actual}, 期望值={expected}"
        self._log_assertion(actual > expected, message, details)
        assert actual > expected, f"{message}\n{details}"
        return self

    def less_than(self, actual: Union[int, float], expected: Union[
        int, float], message: str = "值应小于期望值") -> 'AssertUtil':
        """
        断言实际值小于期望值
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"实际值={actual}, 期望值={expected}"
        self._log_assertion(actual < expected, message, details)
        assert actual < expected, f"{message}\n{details}"
        return self

    def greater_than_or_equals(self, actual: Union[int, float], expected: Union[int, float],
                               message: str = "值应大于等于期望值") -> 'AssertUtil':
        """
        断言实际值大于等于期望值
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"实际值={actual}, 期望值={expected}"
        self._log_assertion(actual >= expected, message, details)
        assert actual >= expected, f"{message}\n{details}"
        return self

    def less_than_or_equals(self, actual: Union[int, float], expected: Union[int, float],
                            message: str = "值应小于等于期望值") -> 'AssertUtil':
        """
        断言实际值小于等于期望值
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"实际值={actual}, 期望值={expected}"
        self._log_assertion(actual <= expected, message, details)
        assert actual <= expected, f"{message}\n{details}"
        return self

    # Web元素特定断言方法
    def element_is_displayed(self, element: Any, message: str = "元素不可见") -> 'AssertUtil':
        """
        断言Web元素可见
        
        Args:
            element: Web元素对象
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            result = element.is_displayed()
            details = f"元素显示状态={result}"
            self._log_assertion(result, message, details)
            assert result, f"{message}\n{details}"
        except Exception as e:
            details = f"检查元素显示状态时出错: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"
        return self

    def element_is_enabled(self, element: Any, message: str = "元素不可用") -> 'AssertUtil':
        """
        断言Web元素可用
        
        Args:
            element: Web元素对象
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            result = element.is_enabled()
            details = f"元素可用状态={result}"
            self._log_assertion(result, message, details)
            assert result, f"{message}\n{details}"
        except Exception as e:
            details = f"检查元素可用状态时出错: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"
        return self

    def element_text_equals(self, element: Any, expected_text: str, message: str = "元素文本不匹配") -> 'AssertUtil':
        """
        断言Web元素文本等于期望值
        
        Args:
            element: Web元素对象
            expected_text: 期望的文本
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            actual_text = element.text.strip() if hasattr(element, 'text') else str(element)
            details = f"实际文本='{actual_text}', 期望文本='{expected_text}'"
            self._log_assertion(actual_text == expected_text, message, details)
            assert actual_text == expected_text, f"{message}\n{details}"
        except Exception as e:
            details = f"获取元素文本时出错: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"
        return self

    def element_attribute_equals(self, element: Any, attribute_name: str, expected_value: str,
                                 message: str = "元素属性值不匹配") -> 'AssertUtil':
        """
        断言Web元素属性值等于期望值
        
        Args:
            element: Web元素对象
            attribute_name: 属性名称
            expected_value: 期望的属性值
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            actual_value = element.get_attribute(attribute_name)
            details = f"属性'{attribute_name}' - 实际值='{actual_value}', 期望值='{expected_value}'"
            self._log_assertion(actual_value == expected_value, message, details)
            assert actual_value == expected_value, f"{message}\n{details}"
        except Exception as e:
            details = f"获取元素属性时出错: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"
        return self

    # API响应特定断言方法
    def status_code_equals(self, response: Any, expected_code: int, message: str = "HTTP状态码不匹配") -> 'AssertUtil':
        """
        断言HTTP响应状态码等于期望值
        
        Args:
            response: API响应对象
            expected_code: 期望的状态码
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            actual_code = response.status_code if hasattr(response, 'status_code') else int(response)
            details = f"实际状态码={actual_code}, 期望状态码={expected_code}"
            self._log_assertion(actual_code == expected_code, message, details)
            assert actual_code == expected_code, f"{message}\n{details}"
        except Exception as e:
            details = f"获取状态码时出错: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"
        return self

    def response_json_contains(self, response: Any, expected_key: str, message: str = "响应JSON中缺少指定键") -> 'AssertUtil':
        """
        断言API响应JSON包含指定键
        
        Args:
            response: API响应对象
            expected_key: 期望的键名
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            response_json = response.json() if hasattr(response, 'json') else response
            details = f"响应JSON={response_json}, 查找键='{expected_key}'"
            self._log_assertion(expected_key in response_json, message, details)
            assert expected_key in response_json, f"{message}\n{details}"
        except Exception as e:
            details = f"解析响应JSON时出错: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"
        return self

    def response_json_equals(self, response: Any, expected_value: Any, path: Optional[str] = None,
                             message: str = "响应JSON值不匹配") -> 'AssertUtil':
        """
        断言API响应JSON值等于期望值
        
        Args:
            response: API响应对象
            expected_value: 期望的值
            path: JSON路径（点分隔, 如 'data.user.name'）, None表示整个响应
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            response_json = response.json() if hasattr(response, 'json') else response

            if path:
                # 根据路径获取值
                value = response_json
                for part in path.split('.'):
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        details = f"无法在路径'{path}'找到值, 响应JSON={response_json}"
                        self._log_assertion(False, message, details)
                        assert False, f"{message}\n{details}"
                actual_value = value
            else:
                actual_value = response_json

            details = f"路径'{path or '整个响应'}' - 实际值={actual_value}, 期望值={expected_value}"
            self._log_assertion(actual_value == expected_value, message, details)
            assert actual_value == expected_value, f"{message}\n{details}"
        except Exception as e:
            details = f"解析响应JSON时出错: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"
        return self

    # 上下文管理器方法, 用于异常断言
    def raises(self, exception_type: type, callable_obj: callable, *args, **kwargs) -> 'AssertUtil':
        """
        断言调用可调用对象时会引发指定类型的异常
        
        Args:
            exception_type: 期望的异常类型
            callable_obj: 要调用的可调用对象
            *args: 传递给可调用对象的位置参数
            **kwargs: 传递给可调用对象的关键字参数
            
        Returns:
            断言工具实例, 支持链式调用
        """
        try:
            callable_obj(*args, **kwargs)
            # 如果没有引发异常, 断言失败
            message = f"未引发预期的异常 {exception_type.__name__}"
            self._log_assertion(False, message)
            assert False, message
        except exception_type:
            # 引发了预期的异常, 断言通过
            message = f"成功引发预期的异常 {exception_type.__name__}"
            if logger:
                logger.info(message)
            return self
        except Exception as e:
            # 引发了其他类型的异常, 断言失败
            message = f"引发了错误的异常类型"
            details = f"期望={exception_type.__name__}, 实际={type(e).__name__}: {str(e)}"
            self._log_assertion(False, message, details)
            assert False, f"{message}\n{details}"

    # 自定义断言方法, 允许用户提供自定义条件
    def assert_that(self, condition: bool, message: str = "断言失败") -> 'AssertUtil':
        """
        自定义断言条件
        
        Args:
            condition: 断言条件
            message: 自定义错误消息
            
        Returns:
            断言工具实例, 支持链式调用
        """
        details = f"条件值={condition}"
        self._log_assertion(condition, message, details)
        assert condition, f"{message}\n{details}"
        return self

    # 设置驱动对象（用于截图）
    def set_driver(self, driver: Any) -> 'AssertUtil':
        """
        设置WebDriver或AppiumDriver实例
        
        Args:
            driver: WebDriver或AppiumDriver实例
            
        Returns:
            断言工具实例, 支持链式调用
        """
        self.driver = driver
        return self


# 创建一个默认实例, 方便直接导入使用
default_assert_util = AssertUtil()


# 模块级别的便捷函数, 便于直接调用
def assert_equal(actual: Any, expected: Any, message: str = "值不相等") -> None:
    """便捷函数: 断言两个值相等"""
    default_assert_util.equals(actual, expected, message)


def assert_contains(container: Union[str, list, dict, set], item: Any, message: str = "不包含指定元素") -> None:
    """便捷函数: 断言容器包含指定元素"""
    default_assert_util.contains(container, item, message)


def assert_true(condition: bool, message: str = "条件应为True") -> None:
    """便捷函数: 断言条件为True"""
    default_assert_util.is_true(condition, message)


def assert_false(condition: bool, message: str = "条件应为False") -> None:
    """便捷函数: 断言条件为False"""
    default_assert_util.is_false(condition, message)


def assert_not_none(value: Any, message: str = "值不应为None") -> None:
    """便捷函数: 断言值不为None"""
    default_assert_util.is_not_none(value, message)


def assert_instance(obj: Any, expected_type: type, message: str = "类型不匹配") -> None:
    """便捷函数: 断言对象为指定类型"""
    default_assert_util.is_instance(obj, expected_type, message)


def assert_status_code(response: Any, expected_code: int, message: str = "HTTP状态码不匹配") -> None:
    """便捷函数: 断言HTTP响应状态码"""
    default_assert_util.status_code_equals(response, expected_code, message)


def assert_element_displayed(element: Any, message: str = "元素不可见") -> None:
    """便捷函数: 断言Web元素可见"""
    default_assert_util.element_is_displayed(element, message)


def assert_element_text(element: Any, expected_text: str, message: str = "元素文本不匹配") -> None:
    """便捷函数: 断言Web元素文本"""
    default_assert_util.element_text_equals(element, expected_text, message)
