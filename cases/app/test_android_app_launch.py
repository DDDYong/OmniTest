"""
-------------------------------------------------
File:           test_android_app_launch.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
App测试 - 安卓应用启动和验证
-------------------------------------------------
"""
import os
import time

import pytest
import yaml

from config.config_manager import config
from utils.app.app_base_page import AppBasePage
from utils.app.appium_manager import AppiumManager
from utils.file_util import FileHandler
from utils.logger_util import logger


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
        try:
            # 将属性设置为类属性
            TestAndroidAppLaunch.test_data = FileHandler().read_yaml("test_data/app_test_data.yaml")
            # 提取测试配置
            TestAndroidAppLaunch.app_config = TestAndroidAppLaunch.test_data["android_app_test"]
            TestAndroidAppLaunch.device_capabilities = TestAndroidAppLaunch.app_config["device_capabilities"]
            TestAndroidAppLaunch.appium_server = TestAndroidAppLaunch.app_config["appium_server"]
            TestAndroidAppLaunch.expected_results = TestAndroidAppLaunch.app_config["expected_results"]
            TestAndroidAppLaunch.test_scenarios = TestAndroidAppLaunch.app_config["test_scenarios"]
            logger.info("成功加载测试数据")
        except (FileNotFoundError, yaml.YAMLError, KeyError) as e:
            logger.error(f"加载测试数据失败: {str(e)}")
            pytest.skip("无法加载测试数据,跳过测试")

        # 初始化Appium管理器
        try:
            TestAndroidAppLaunch.appium_manager = AppiumManager(
                host = TestAndroidAppLaunch.appium_server["host"],
                port = TestAndroidAppLaunch.appium_server["port"],
                timeout = TestAndroidAppLaunch.appium_server["timeout"]
            )
            logger.info("成功初始化Appium管理器")
        except (ConnectionError, RuntimeError) as e:
            logger.error(f"初始化Appium管理器失败: {str(e)}")
            pytest.skip("无法初始化Appium管理器,跳过测试")

        # 初始化WebDriver和页面类
        TestAndroidAppLaunch.driver = None
        TestAndroidAppLaunch.base_page = None

        # 测试环境信息
        try:
            env = config.get_config_value('env.default', 'test')
            logger.info(f"当前测试环境: {env}")
        except (KeyError, TypeError):
            logger.info("当前测试环境: test")
        logger.info(f"Appium服务器: {TestAndroidAppLaunch.appium_server['host']}:{TestAndroidAppLaunch.appium_server['port']}")
        logger.info(f"目标设备: {TestAndroidAppLaunch.device_capabilities.get('deviceName', 'Android Device')}")
        logger.info(f"目标应用: {TestAndroidAppLaunch.device_capabilities.get('appPackage', '未知')}")

        # 测试执行前的清理
        yield

        # 测试结束后清理资源（Appium会话已在setup_test中关闭）
        logger.info("=" * 60)
        logger.info("安卓应用启动测试执行完成")
        logger.info("=" * 60)

    @pytest.fixture(scope = "class", autouse = True)
    def setup_test(self, request):
        """
        测试类级别的设置
        连接到Appium服务器并创建WebDriver
        """
        logger.info("\n" + "-" * 50)
        logger.info("开始执行测试类设置")

        # 检查Appium服务器状态
        is_server_running = request.cls.appium_manager.check_server_status()
        if not is_server_running:
            logger.warning("Appium服务器未运行, 尝试启动...")
            # 尝试启动Appium服务器
            start_success = request.cls.appium_manager.start_appium_service(
                host = request.cls.appium_server["host"],
                port = request.cls.appium_server["port"]
            )
            if not start_success:
                logger.error("无法启动Appium服务器")
                pytest.skip("Appium服务器未运行")

        # 连接到Appium服务器并创建WebDriver
        try:
            logger.info("连接到Appium服务器")
            # 确保之前的会话已关闭
            if request.cls.driver:
                try:
                    request.cls.driver.quit()
                    logger.info("已关闭之前的Appium会话")
                except Exception as e:
                    logger.warning(f"关闭之前会话时发生错误: {str(e)}")

            # 创建新的驱动
            request.cls.driver = request.cls.appium_manager.create_driver(request.cls.device_capabilities)
            # 从测试数据中获取截图保存路径
            screenshot_dir = request.cls.test_data.get("generic_test_settings", {}).get("screenshot_dir")
            request.cls.base_page = AppBasePage(request.cls.driver, screenshot_dir = screenshot_dir)
            logger.info("成功创建Appium会话")
        except Exception as e:
            logger.error(f"创建Appium会话失败: {str(e)}")
            pytest.fail(f"无法连接到Appium服务器: {str(e)}")

        # 测试类执行完成后的清理
        yield

        # 确保关闭Appium会话
        if request.cls.driver:
            try:
                logger.info("关闭Appium会话")
                request.cls.driver.quit()
                request.cls.driver = None
                request.cls.base_page = None
            except Exception as e:
                logger.error(f"关闭Appium会话时发生错误: {str(e)}")

        logger.info("测试类执行完成")

    @staticmethod
    def _get_test_scenario(scenario_name):
        """
        获取指定名称的测试场景配置
        
        Args:
            scenario_name: 场景名称
            
        Returns:
            dict: 场景配置
        """
        for scenario in TestAndroidAppLaunch.test_scenarios:
            if scenario["name"] == scenario_name:
                return scenario
        return None

    @pytest.mark.smoke
    @pytest.mark.app
    def test_appium_server_connection(self):
        """
        测试Appium服务器连接
        验证是否能成功连接到Appium服务器
        """
        logger.info("验证Appium服务器连接")

        # 检查Appium服务器状态
        is_connected = TestAndroidAppLaunch.appium_manager.check_server_status()
        assert is_connected, f"Appium服务器连接失败: {TestAndroidAppLaunch.expected_results['error_messages']['appium_server_down']}"
        logger.info("Appium服务器连接验证通过")

        # 服务器连接测试通过
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
        launch_scenario = self._get_test_scenario("app_launch")
        
        if not launch_scenario:
            pytest.fail("未找到应用启动测试场景配置")

        # 验证应用包名
        expected_package = launch_scenario["expected"]["package"]
        current_package = TestAndroidAppLaunch.base_page.get_current_package()
        assert current_package == expected_package, \
            f"包名不匹配: 期望'{expected_package}', 实际'{current_package}'"
        logger.info(f"包名验证通过: {current_package}")

        # 获取当前活动
        current_activity = TestAndroidAppLaunch.base_page.get_current_activity()
        logger.info(f"当前活动: {current_activity}")

        # 截图保存
        screenshot_path = TestAndroidAppLaunch.base_page.take_screenshot(filename = f"app_launched_{time.time()}")
        logger.info(f"应用启动截图保存到: {screenshot_path}")

        # 验证应用是否正常运行
        assert TestAndroidAppLaunch.expected_results["app_launches_successfully"], "应用应该成功启动"

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
                "platform_name": TestAndroidAppLaunch.driver.capabilities.get("platformName"),
                "platform_version": TestAndroidAppLaunch.driver.capabilities.get("platformVersion"),
                "device_name": TestAndroidAppLaunch.driver.capabilities.get("deviceName"),
                "automation_name": TestAndroidAppLaunch.driver.capabilities.get("automationName")
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
        screenshot_path = TestAndroidAppLaunch.base_page.take_screenshot(screenshot_filename)

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
        验证能否成功返回上一个活动
        """
        logger.info("执行返回按钮测试")

        # 获取当前活动
        original_activity = TestAndroidAppLaunch.base_page.get_current_activity()
        logger.info(f"当前活动: {original_activity}")

        # 执行返回操作
        back_success = TestAndroidAppLaunch.base_page.back()
        assert back_success, "返回操作失败"

        # 等待页面转换
        time.sleep(1)

        # 获取返回后的活动
        new_activity = TestAndroidAppLaunch.base_page.get_current_activity()
        logger.info(f"返回后的活动: {new_activity}")

    def teardown_method(self):
        """
        每个测试方法执行后的清理
        捕获测试失败时的截图
        """
        # 获取当前测试状态
        import sys
        current_test_name = getattr(self, 'current_test_name', 'unknown')

        # 如果测试失败,捕获截图
        if sys.exc_info()[0] is not None:
            logger.error(f"测试用例 {current_test_name} 失败")

            # 捕获失败截图
            timestamp = int(time.time())
            screenshot_filename = f"failed_{current_test_name}_{timestamp}.png"
            if TestAndroidAppLaunch.base_page:
                TestAndroidAppLaunch.base_page.take_screenshot(screenshot_filename)
                logger.error(f"已捕获失败截图: {screenshot_filename}")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])
