"""
-------------------------------------------------
File:           test_android_app_launch.py
Author:         duanyang
Date:           2026/03/19
-------------------------------------------------
Description:
支持并行执行的安卓应用启动测试用例
-------------------------------------------------
"""
import time

import allure
import pytest

from utils.app.app_base_page import AppBasePage
from utils.decorator_util import app_test
from utils.file_util import FileHandler
from utils.logger_util import logger
from utils.screenshot_util import ScreenshotUtils


@pytest.mark.parallel
class TestAndroidAppLaunch:
    """支持并行执行的安卓应用启动测试类"""

    @pytest.fixture(scope = "class", autouse = True)
    def class_setup(self, request):
        """
        测试类级别的初始化, 加载测试数据
        """
        file_handler = FileHandler()
        test_data = file_handler.read_yaml("test_data/app_test_cases.yaml")
        request.cls.test_data = test_data
        logger.info("测试数据加载完成")

    @pytest.fixture(scope = "function", autouse = True)
    def setup_method(self, parallel_appium_driver, request):
        """
        测试方法级别的初始化
        确保每个测试方法执行前应用都处于正确状态
        """
        logger.info("\n" + "-" * 50)
        logger.info(f"开始执行测试方法: {request.node.name}")

        driver = parallel_appium_driver
        request.cls.base_page = AppBasePage(driver)

        logger.info("测试方法设置完成")
        logger.info("-" * 50)

    @app_test(
        smoke = True,
        feature = "应用启动",
        story = "Appium连接",
        title = "Appium服务器连接测试",
        tags = ["smoke", "app", "launch", "appium"],
        severity = "critical",
        description = "测试Appium服务器连接功能"
    )
    def test_appium_server_connection(self, parallel_appium_driver):
        """
        测试Appium服务器连接
        验证是否能成功连接到Appium服务器
        """
        scenario_name = "appium_connection"
        logger.info(f"测试Appium服务器连接 - 场景: {scenario_name}")

        driver = parallel_appium_driver

        with allure.step("验证Appium服务器连接"):
            # 获取设备信息验证连接
            device_info = {
                "platform_name": driver.capabilities.get("platformName"),
                "platform_version": driver.capabilities.get("platformVersion"),
                "device_name": driver.capabilities.get("deviceName"),
                "automation_name": driver.capabilities.get("automationName")
            }

            logger.info(f"设备信息: {device_info}")
            assert device_info["platform_name"] == "Android", \
                f"平台不匹配: 期望'Android', 实际'{device_info['platform_name']}'"
            assert device_info["device_name"] != "", "设备名称不能为空"
            assert device_info["automation_name"] == "UiAutomator2", \
                f"自动化引擎不匹配: 期望'UiAutomator2', 实际'{device_info['automation_name']}'"

            logger.info("Appium服务器连接验证通过")

    @app_test(
        smoke = True,
        feature = "应用启动",
        story = "应用启动",
        title = "应用启动测试",
        tags = ["smoke", "app", "launch"],
        severity = "critical",
        description = "测试应用是否能成功启动并进入主界面"
    )
    def test_app_launch(self, parallel_appium_driver):
        """
        测试应用启动
        验证应用是否能成功启动并进入主界面
        """
        scenario_name = "app_launch"
        logger.info(f"测试应用启动 - 场景: {scenario_name}")

        driver = parallel_appium_driver
        base_page = self.base_page

        # 获取测试数据和预期结果
        with allure.step("应用启动测试"):
            test_scenarios = self.test_data.get("test_scenarios", [])
            launch_scenario = {}
            for scenario in test_scenarios:
                if scenario.get("name") == scenario_name:
                    launch_scenario = scenario
                    break
            expected = launch_scenario.get("expected", {})

        if not launch_scenario:
            pytest.fail("未找到应用启动测试场景配置")

        # 获取目标应用包名
        expected_package = expected.get("package", "")
        app_package = driver.capabilities.get("appPackage")

        with allure.step("启动应用"):
            logger.info(f"启动应用: {app_package}")

            # 尝试启动应用，最多重试3次
            max_retries = 3
            for attempt in range(max_retries):
                logger.info(f"尝试启动应用 (尝试 {attempt + 1}/{max_retries})")

                # 尝试启动应用
                try:
                    # 首先尝试重置应用
                    driver.reset()
                    logger.info("应用重置成功")
                except Exception as e:
                    logger.warning(f"应用重置失败: {str(e)}")
                    # 如果重置失败，尝试激活应用
                    if app_package:
                        driver.activate_app(app_package)
                        logger.info(f"尝试激活应用: {app_package}")

                # 等待应用启动
                logger.info("等待应用启动...")
                time.sleep(3)

                # 验证应用包名
                current_package = base_page.get_current_package()
                logger.info(f"当前包名: {current_package}")

                if current_package == expected_package:
                    logger.info(f"包名验证通过: {current_package}")
                    break
                else:
                    logger.warning(f"包名不匹配: 期望'{expected_package}', 实际'{current_package}' (尝试 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        # 最后一次尝试失败，尝试通过图标启动
                        logger.info("尝试通过图标启动应用")
                        if base_page.launch_app_by_icon():
                            logger.info("通过图标启动应用成功")
                            time.sleep(2)
                            current_package = base_page.get_current_package()
                            if current_package == expected_package:
                                logger.info(f"包名验证通过: {current_package}")
                                break

                        # 最后一次尝试失败，进行截图
                        screenshot_path = ScreenshotUtils().capture_screenshot(driver, name = f"app_launch_failed_{time.time()}")
                        logger.error(f"应用启动失败，截图保存到: {screenshot_path}")
                        assert current_package == expected_package, \
                            f"包名不匹配: 期望'{expected_package}', 实际'{current_package}'"

        with allure.step("获取当前活动"):
            current_activity = base_page.get_current_activity()
            logger.info(f"当前活动: {current_activity}")

        with allure.step("验证当前活动"):
            assert current_activity == expected["current_activity"], \
                f"当前活动不匹配: 期望'{expected['current_activity']}', 实际'{current_activity}'"
        logger.info("应用启动测试通过")

    @app_test(
        feature = "应用启动",
        story = "设备信息",
        title = "设备信息测试",
        tags = ["app", "launch", "device"],
        severity = "normal",
        description = "测试获取设备信息功能"
    )
    def test_device_info(self, parallel_appium_driver):
        """
        测试设备信息
        验证获取的设备信息是否正确
        """
        scenario_name = "device_info"
        logger.info(f"测试设备信息 - 场景: {scenario_name}")

        driver = parallel_appium_driver
        
        try:
            with allure.step("获取设备信息"):
                # 获取设备信息
                device_info = {
                    "platform_name": driver.capabilities.get("platformName"),
                    "platform_version": driver.capabilities.get("platformVersion"),
                    "device_name": driver.capabilities.get("deviceName"),
                    "automation_name": driver.capabilities.get("automationName")
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
