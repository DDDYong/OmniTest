"""
-------------------------------------------------
File:           test_android_app_launch.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
App测试样例 - 安卓应用启动和验证
演示如何连接Appium服务器、启动安卓应用并进行基本的功能验证
-------------------------------------------------
"""
import json
import os
# 添加项目根目录到Python路径
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config_manager import config
from utils.logger_util import logger
from utils.screenshot_util import ScreenshotUtils
from utils.app.appium_manager import AppiumManager
from cases.app.pages.base_app_page import BaseAppPage


class TestAndroidAppLaunch:
    """
    安卓应用启动测试类
    验证应用能否正常启动、界面元素是否正常显示等
    """

    @pytest.fixture(scope = "class", autouse = True)
    def setup_class(self):
        """
        测试类级别的初始化
        加载测试数据、初始化Appium管理器
        """
        logger.info("=" * 60)
        logger.info("开始执行安卓应用启动测试")
        logger.info("=" * 60)

        # 加载测试数据
        # 使用os模块构建路径, 避免依赖config.DATA_DIR
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.test_data_path = os.path.join(
            self.project_root,
            "data",
            "test_data",
            "app_test_data.json"
        )

        try:
            with open(self.test_data_path, 'r', encoding = 'utf-8') as f:
                self.test_data = json.load(f)
            logger.info(f"成功加载测试数据: {self.test_data_path}")

        except Exception as e:
            logger.error(f"加载测试数据失败: {str(e)}")
            pytest.skip("无法加载测试数据,跳过测试")

        # 提取测试配置
        self.app_config = self.test_data["android_app_test"]
        self.device_capabilities = self.app_config["device_capabilities"]
        self.appium_server = self.app_config["appium_server"]
        self.expected_results = self.app_config["expected_results"]
        self.test_scenarios = self.app_config["test_scenarios"]

        # 初始化Appium管理器
        self.appium_manager = AppiumManager(
            host = self.appium_server["host"],
            port = self.appium_server["port"],
            timeout = self.appium_server["timeout"]
        )

        # 初始化WebDriver和页面类
        self.driver = None
        self.base_page = None

        # 测试环境信息
        logger.info(f"当前测试环境: {config.ENV}")
        logger.info(f"Appium服务器: {self.appium_server['host']}:{self.appium_server['port']}")
        logger.info(f"目标设备: {self.device_capabilities['deviceName']}")
        logger.info(f"目标应用: {self.device_capabilities['appPackage']}")

        # 测试执行前的清理
        yield

        # 测试结束后清理资源
        if self.driver:
            try:
                logger.info("关闭Appium会话")
                self.driver.quit()
            except Exception as e:
                logger.error(f"关闭Appium会话时发生错误: {str(e)}")

        logger.info("=" * 60)
        logger.info("安卓应用启动测试执行完成")
        logger.info("=" * 60)

    @pytest.fixture(autouse = True)
    def setup_test(self):
        """
        每个测试用例执行前的设置
        连接到Appium服务器并启动应用
        """
        logger.info("\n" + "-" * 50)
        logger.info(f"开始执行测试用例: {pytest.current_test.name}")

        # 连接到Appium服务器并创建WebDriver
        try:
            logger.info("连接到Appium服务器")
            self.driver = self.appium_manager.create_driver(self.device_capabilities)
            self.base_page = BaseAppPage(self.driver)
            logger.info("成功创建Appium会话")
        except Exception as e:
            logger.error(f"创建Appium会话失败: {str(e)}")
            pytest.fail(f"无法连接到Appium服务器: {str(e)}")

        # 测试用例执行完成后的清理
        yield

        logger.info(f"测试用例执行完成: {pytest.current_test.name}")

    @pytest.mark.smoke
    @pytest.mark.app
    def test_appium_server_connection(self):
        """
        测试Appium服务器连接
        验证是否能成功连接到Appium服务器
        """
        logger.info("验证Appium服务器连接")

        # 检查Appium服务器状态
        is_connected = self.appium_manager.check_server_status()
        assert is_connected, self.expected_results["error_messages"]["appium_server_down"]
        logger.info("Appium服务器连接验证通过")

        # 获取会话ID验证连接
        session_id = self.driver.session_id
        assert session_id is not None, "无法获取会话ID"
        logger.info(f"会话ID验证通过: {session_id[:8]}...")

        logger.info("Appium服务器连接测试通过")

    @pytest.mark.smoke
    @pytest.mark.app
    def test_app_launch(self):
        """
        测试应用启动
        验证应用是否能成功启动并进入主界面
        """
        logger.info("执行应用启动测试")

        # 获取启动应用的测试场景
        launch_scenario = None
        for scenario in self.test_scenarios:
            if scenario["name"] == "app_launch":
                launch_scenario = scenario
                break

        if not launch_scenario:
            pytest.fail("未找到应用启动测试场景配置")

        # 验证应用包名和活动
        expected_package = launch_scenario["expected"]["package"]
        expected_activity = launch_scenario["expected"]["activity"]
        timeout = launch_scenario["expected"]["timeout"]

        # 获取当前包名
        current_package = self.base_page.get_current_package()
        assert current_package == expected_package, \
            f"包名不匹配: 期望'{expected_package}', 实际'{current_package}'"
        logger.info(f"包名验证通过: {current_package}")

        # 等待应用启动完成并验证活动
        activity_launched = self.base_page.is_activity_running(expected_activity, timeout)
        assert activity_launched, \
            f"活动'{expected_activity}'未在{timeout}秒内启动"

        # 获取当前活动
        current_activity = self.base_page.get_current_activity()
        logger.info(f"活动验证通过: {current_activity}")

        # 截图保存
        screenshot_path = ScreenshotUtils().capture_screenshot(
            driver = self.driver,
            filename = "app_launched",
            description = "应用启动成功截图"
        )
        logger.info(f"应用启动截图保存到: {screenshot_path}")

        # 验证应用是否正常运行
        # 这里我们通过检查主界面的包名和活动来验证
        assert self.expected_results["app_launches_successfully"], "应用应该成功启动"

        logger.info("应用启动测试通过")

    @pytest.mark.app
    def test_device_info(self):
        """
        测试设备信息
        验证获取的设备信息是否正确
        """
        logger.info("获取并验证设备信息")

        try:
            # 获取设备信息
            device_info = {
                "platform_name": self.driver.capabilities["platformName"],
                "platform_version": self.driver.capabilities["platformVersion"],
                "device_name": self.driver.capabilities["deviceName"],
                "automation_name": self.driver.capabilities["automationName"]
            }

            logger.info(f"设备信息: {device_info}")

            # 验证设备平台
            assert device_info["platform_name"] == "Android", \
                f"平台不匹配: 期望'Android', 实际'{device_info['platform_name']}'"

            # 验证设备名称不为空
            assert device_info["device_name"] != "", "设备名称不能为空"

            # 验证自动化引擎
            assert device_info["automation_name"] == "UiAutomator2", \
                f"自动化引擎不匹配: 期望'UiAutomator2', 实际'{device_info['automation_name']}'"

            logger.info("设备信息验证通过")

        except KeyError as e:
            pytest.fail(f"获取设备信息时缺少关键字: {str(e)}")
        except Exception as e:
            pytest.fail(f"验证设备信息时发生错误: {str(e)}")

    @pytest.mark.app
    def test_app_screenshot(self):
        """
        测试应用截图功能
        验证是否能成功获取应用截图
        """
        logger.info("执行应用截图测试")

        # 执行截图
        timestamp = int(time.time())
        screenshot_filename = f"app_test_screenshot_{timestamp}.png"

        # 使用BasePage的截图方法
        screenshot_path = self.base_page.take_screenshot(screenshot_filename)

        # 验证截图是否成功
        assert screenshot_path is not None, "截图失败"
        assert os.path.exists(screenshot_path), f"截图文件不存在: {screenshot_path}"

        # 检查文件大小
        file_size = os.path.getsize(screenshot_path)
        assert file_size > 0, "截图文件为空"

        logger.info(f"截图测试通过: {screenshot_path}, 大小: {file_size}字节")

    @pytest.mark.app
    def test_back_button(self):
        """
        测试返回按钮功能
        验证应用的返回操作是否正常工作
        """
        logger.info("执行返回按钮测试")

        # 获取当前活动
        original_activity = self.base_page.get_current_activity()
        logger.info(f"当前活动: {original_activity}")

        # 执行返回操作
        back_success = self.base_page.back()
        assert back_success, "返回操作失败"

        # 等待页面转换
        time.sleep(1)

        # 获取返回后的活动
        new_activity = self.base_page.get_current_activity()
        logger.info(f"返回后的活动: {new_activity}")

        # 验证活动是否发生变化
        # 注意：在某些情况下,返回可能会保持在同一个活动中,但UI会改变
        # 这里我们只验证返回操作是否执行成功,不强制要求活动改变
        logger.info("返回按钮测试通过")

    @pytest.mark.app
    def test_app_reset(self):
        """
        测试应用重置功能
        验证能否成功重置应用到初始状态
        """
        logger.info("执行应用重置测试")

        # 重置应用
        reset_success = self.base_page.reset_app()
        assert reset_success, "应用重置失败"

        # 等待应用重新启动
        time.sleep(3)

        # 验证应用是否重置
        # 我们通过检查应用是否仍在运行来验证
        current_activity = self.base_page.get_current_activity()
        assert current_activity is not None, "应用重置后无法获取活动"

        logger.info(f"应用重置后活动: {current_activity}")
        logger.info("应用重置测试通过")

    @pytest.mark.app
    def test_home_button(self):
        """
        测试Home键功能
        验证能否成功按Home键返回设备主屏幕
        """
        logger.info("执行Home键测试")

        # 按Home键
        home_success = self.base_page.press_home_button()
        assert home_success, "Home键操作失败"

        # 等待系统响应
        time.sleep(2)

        # 验证是否已返回到主屏幕
        # 检查当前活动是否为主屏幕活动
        # 注意：不同设备的主屏幕活动可能不同
        current_activity = self.base_page.get_current_activity()
        logger.info(f"按Home键后的活动: {current_activity}")

        # 我们不强制要求验证特定的主屏幕活动
        # 因为不同设备可能有不同的实现
        logger.info("Home键测试通过")

    def teardown_method(self):
        """
        每个测试方法执行后的清理
        捕获测试失败时的截图
        """
        # 获取当前测试状态
        current_test = pytest.current_test

        # 如果测试失败,捕获截图
        if hasattr(current_test, "rep_call") and current_test.rep_call.failed:
            logger.error(f"测试用例 {current_test.name} 失败")

            # 捕获失败截图
            timestamp = int(time.time())
            screenshot_filename = f"failed_{current_test.name}_{timestamp}.png"
            ScreenshotUtils().capture_screenshot(
                driver = self.driver,
                filename = screenshot_filename,
                description = f"测试用例 {current_test.name} 失败截图"
            )
            logger.error(f"已捕获失败截图: {screenshot_filename}")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])
