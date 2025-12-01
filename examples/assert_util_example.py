"""
-------------------------------------------------
File:           assert_util_example.py
Author:         duanyang
Date:           2025/12/01
-------------------------------------------------
Description:
断言工具使用示例
展示如何在API、Web和App测试中使用assert_util模块
-------------------------------------------------
"""
# 添加项目根目录到Python路径
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.assert_util import AssertUtil, assert_equal, assert_contains, assert_true, assert_false
from utils.assert_util import assert_not_none, assert_instance
from utils.assert_util import assert_element_displayed, assert_element_text


def example_basic_assertions():
    """
    基本断言示例
    展示如何使用AssertUtil进行基本的断言操作
    """
    print("\n===== 基本断言示例 =====\n")

    # 创建断言工具实例
    assert_util = AssertUtil()

    # 基本值相等断言
    actual_value = 42
    expected_value = 42
    assert_util.equals(actual_value, expected_value, "值应该等于42")

    # 字符串包含断言
    text = "Hello, World!"
    substring = "World"
    assert_util.contains(text, substring, "文本应该包含'World'")

    # 布尔条件断言
    is_valid = True
    assert_util.is_true(is_valid, "条件应该为True")

    # 链式调用
    user_data = {
        "name": "Alice",
        "age": 30,
        "email": "alice@example.com"
    }

    assert_util \
        .contains(user_data, "name", "用户数据应该包含name字段") \
        .equals(user_data["age"], 30, "用户年龄应该是30") \
        .contains(user_data["email"], "@", "邮箱应该包含@符号")

    print("基本断言测试通过!")


def example_shortcut_functions():
    """
    便捷函数示例
    展示如何使用模块级别的便捷函数
    """
    print("\n===== 便捷函数示例 =====\n")

    # 使用便捷函数
    assert_equal("test", "test", "字符串应该相等")
    assert_contains([1, 2, 3, 4, 5], 3, "列表应该包含3")
    assert_true(True, "这个应该为True")
    assert_false(False, "这个应该为False")
    assert_not_none("some value", "值不应该为None")
    assert_instance(42, int, "值应该是整数类型")

    print("便捷函数测试通过!")


def example_api_response_assertions():
    """
    API响应断言示例
    模拟API响应并展示相关断言
    """
    print("\n===== API响应断言示例 =====\n")

    # 创建断言工具实例
    assert_util = AssertUtil()

    # 模拟API响应
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data

        def json(self):
            return self._json_data

    # 创建模拟响应
    mock_response = MockResponse(
        status_code = 200,
        json_data = {
            "status": "success",
            "data": {
                "user": {
                    "id": 1,
                    "name": "Bob",
                    "email": "bob@example.com"
                },
                "permissions": ["read", "write", "admin"]
            },
            "message": "User fetched successfully"
        }
    )

    # 状态码断言
    assert_util.status_code_equals(mock_response, 200, "状态码应该为200")

    # 响应中包含键断言
    assert_util.response_json_contains(mock_response, "status", "响应应该包含status字段")

    # 响应JSON值断言 (整个响应)
    assert_util.response_json_contains(mock_response, "data", "响应应该包含data字段")

    # 响应JSON值断言 (指定路径)
    assert_util.response_json_equals(mock_response, "Bob", "data.user.name", "用户名应该是Bob")
    assert_util.response_json_equals(mock_response, "success", "status", "状态应该为success")

    # 响应中的数组包含元素断言
    response_data = mock_response.json()
    assert_util.contains(response_data["data"]["permissions"], "admin", "用户应该有admin权限")

    print("API响应断言测试通过!")


def example_web_element_assertions():
    """
    Web元素断言示例
    模拟Web元素并展示相关断言
    """
    print("\n===== Web元素断言示例 =====\n")

    # 模拟WebDriver
    class MockDriver:
        def get_screenshot_as_file(self, file_path):
            print(f"已保存截图到: {file_path}")
            return True

    # 模拟Web元素
    class MockElement:
        def __init__(self, displayed = True, enabled = True, text = "Test Element"):
            self._displayed = displayed
            self._enabled = enabled
            self._text = text
            self._attributes = {}

        def is_displayed(self):
            return self._displayed

        def is_enabled(self):
            return self._enabled

        @property
        def text(self):
            return self._text

        def get_attribute(self, name):
            return self._attributes.get(name)

        def set_attribute(self, name, value):
            self._attributes[name] = value

    # 创建模拟元素
    mock_driver = MockDriver()
    mock_element = MockElement(text = "登录按钮")
    mock_element.set_attribute("value", "登录")

    # 创建带有driver的断言工具
    assert_util = AssertUtil(driver = mock_driver)

    # 元素可见性断言
    assert_util.element_is_displayed(mock_element, "登录按钮应该可见")

    # 元素可用性断言
    assert_util.element_is_enabled(mock_element, "登录按钮应该可用")

    # 元素文本断言
    assert_util.element_text_equals(mock_element, "登录按钮", "按钮文本应该是'登录按钮'")

    # 使用便捷函数
    assert_element_displayed(mock_element, "使用便捷函数: 元素应该可见")
    assert_element_text(mock_element, "登录按钮", "使用便捷函数: 元素文本应该匹配")

    print("Web元素断言测试通过!")


def example_exception_assertions():
    """
    异常断言示例
    展示如何断言代码会引发特定异常
    """
    print("\n===== 异常断言示例 =====\n")

    # 创建断言工具实例
    assert_util = AssertUtil()

    # 定义一个会引发异常的函数
    def divide(a, b):
        return a / b

    # 断言函数会引发ZeroDivisionError异常
    assert_util.raises(ZeroDivisionError, divide, 10, 0)

    # 断言函数会引发TypeError异常
    def convert_to_int(value):
        return int(value)

    assert_util.raises(TypeError, convert_to_int, "not a number")

    print("异常断言测试通过!")


def example_custom_assertions():
    """
    自定义断言示例
    展示如何使用自定义条件进行断言
    """
    print("\n===== 自定义断言示例 =====\n")

    # 创建断言工具实例
    assert_util = AssertUtil()

    # 自定义复杂条件断言
    user_data = {
        "name": "Charlie",
        "age": 25,
        "active": True,
        "login_count": 15
    }

    # 自定义条件：用户必须是活跃的且年龄大于18
    custom_condition = user_data["active"] and user_data["age"] > 18
    assert_util.assert_that(custom_condition, "用户应该是活跃的成年人")

    # 自定义条件：用户登录次数应该在合理范围内
    login_count_valid = 1 <= user_data["login_count"] <= 100
    assert_util.assert_that(login_count_valid, "用户登录次数应该在1-100之间")

    print("自定义断言测试通过!")


def example_chained_assertions():
    """
    链式调用断言示例
    展示如何使用链式调用来组合多个断言
    """
    print("\n===== 链式调用断言示例 =====\n")

    # 创建断言工具实例
    assert_util = AssertUtil()

    # 复杂对象的链式断言
    product = {
        "id": "P123",
        "name": "智能手机",
        "price": 5999.99,
        "in_stock": True,
        "specs": {
            "cpu": "A15",
            "ram": "8GB",
            "storage": "256GB"
        },
        "categories": ["电子产品", "手机", "智能手机"]
    }

    # 使用链式调用进行多个断言
    assert_util \
        .is_not_none(product, "产品对象不应该为None") \
        .equals(product["id"], "P123", "产品ID应该是P123") \
        .greater_than(product["price"], 5000, "产品价格应该大于5000") \
        .is_true(product["in_stock"], "产品应该有库存") \
        .contains(product["categories"], "手机", "产品类别应该包含'手机'") \
        .equals(product["specs"]["ram"], "8GB", "产品RAM应该是8GB") \
        .contains(product["name"], "手机", "产品名称应该包含'手机'")

    print("链式调用断言测试通过!")


def example_setting_driver():
    """
    设置驱动示例
    展示如何在断言工具创建后设置或更改driver
    """
    print("\n===== 设置驱动示例 =====\n")

    # 先创建没有driver的断言工具
    assert_util = AssertUtil()

    # 执行一些基本断言
    assert_util.equals(10, 10, "10应该等于10")

    # 模拟WebDriver
    class MockDriver:
        def get_screenshot_as_file(self, file_path):
            print(f"已保存截图到: {file_path}")
            return True

    # 设置driver (支持链式调用)
    mock_driver = MockDriver()
    assert_util.set_driver(mock_driver)

    # 现在断言失败会有截图功能
    # 下面的断言会通过，不会触发截图
    assert_util.equals(20, 20, "20应该等于20")

    print("设置驱动测试通过!")


if __name__ == "__main__":
    print("断言工具使用示例")
    print("====================")

    try:
        # 运行各种断言示例
        example_basic_assertions()
        example_shortcut_functions()
        example_api_response_assertions()
        example_web_element_assertions()
        example_exception_assertions()
        example_custom_assertions()
        example_chained_assertions()
        example_setting_driver()

        print("\n====================")
        print("所有断言示例测试通过!")
        print("请参考以上示例在您的测试用例中使用断言工具。")
        print("====================")

    except AssertionError as e:
        print(f"\n断言失败: {e}")
        print("示例中的失败是正常的，展示了断言失败时的错误信息格式。")
    except Exception as e:
        print(f"\n示例执行出错: {e}")
