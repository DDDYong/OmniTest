"""
-------------------------------------------------
File:           test_app_login.py
Author:         duanyang
Date:           2026/2/27
-------------------------------------------------
Description:
This file contains the test_app_login module, which...
-------------------------------------------------
"""

import pytest

from cases.app.pages.login_page import LoginPage
from utils.db.mysql_client import MySQLClient
from utils.logger_util import logger


class TestLogin:
    """登录功能测试类"""

    driver = None

    @pytest.fixture(scope = "class", autouse = True)
    def setup_class(self, appium_manager):
        """
        测试类级别的初始化
        初始化Appium管理器和驱动
        """
        logger.info("=" * 60)
        logger.info("开始执行登录测试")
        logger.info("=" * 60)

        # 保存appium_manager到类属性
        TestLogin.appium_manager = appium_manager

        # 检查设备状态
        logger.info("检查设备状态...")
        try:
            import subprocess
            # 检查设备是否连接
            result = subprocess.run(["adb", "devices"], capture_output = True, text = True)
            if "device" not in result.stdout:
                logger.error("设备未连接")
                pytest.skip("设备未连接")
            logger.info("设备已连接")

            # 重启设备的UI自动化服务
            logger.info("重启设备的UI自动化服务...")
            subprocess.run(["adb", "shell", "am", "force-stop", "io.appium.uiautomator2.server"], capture_output = True)
            subprocess.run(["adb", "shell", "am", "force-stop",
                            "io.appium.uiautomator2.server.test"], capture_output = True)
            subprocess.run(["adb", "shell", "pm", "clear", "io.appium.uiautomator2.server"], capture_output = True)
            subprocess.run(["adb", "shell", "pm", "clear", "io.appium.uiautomator2.server.test"], capture_output = True)
            # 等待一段时间
            import time
            time.sleep(5)
        except Exception as e:
            logger.error(f"检查设备状态时发生错误: {str(e)}")

        # 加载测试数据
        from utils.file_util import FileHandler
        import yaml
        try:
            # 加载测试数据
            test_data = FileHandler().read_yaml("test_data/app_test_data.yaml")
            # 提取测试配置
            app_config = test_data["android_app_test"]
            TestLogin.device_capabilities = app_config["device_capabilities"]
            appium_server = app_config["appium_server"]
            logger.info("成功加载测试数据")
        except (FileNotFoundError, yaml.YAMLError, KeyError) as e:
            logger.error(f"加载测试数据失败: {str(e)}")
            pytest.skip("无法加载测试数据,跳过测试")

        # 检查Appium服务器状态
        is_server_running = appium_manager.check_server_status()
        if not is_server_running:
            logger.warning("Appium服务器未运行，尝试启动...")
            # 尝试启动Appium服务器
            start_success = appium_manager.start_appium_service(
                host = appium_server["host"],
                port = appium_server["port"]
            )
            if not start_success:
                logger.error("无法启动Appium服务器")
                pytest.skip("Appium服务器未运行")

        # 连接到Appium服务器并创建WebDriver
        try:
            logger.info("连接到Appium服务器")
            # 创建驱动
            driver = appium_manager.create_driver(TestLogin.device_capabilities)
            # 保存驱动到类属性
            TestLogin.driver = driver
            logger.info("成功创建Appium会话")
        except Exception as e:
            logger.error(f"创建Appium会话失败: {str(e)}")
            # 尝试再次重启UI自动化服务
            logger.info("再次尝试重启设备的UI自动化服务...")
            try:
                import subprocess
                # 执行adb命令重启UI自动化服务
                subprocess.run(["adb", "shell", "am", "force-stop",
                                "io.appium.uiautomator2.server"], capture_output = True)
                subprocess.run(["adb", "shell", "am", "force-stop",
                                "io.appium.uiautomator2.server.test"], capture_output = True)
                subprocess.run(["adb", "shell", "pm", "clear", "io.appium.uiautomator2.server"], capture_output = True)
                subprocess.run(["adb", "shell", "pm", "clear",
                                "io.appium.uiautomator2.server.test"], capture_output = True)
                # 等待一段时间
                import time
                time.sleep(5)
                # 重新创建驱动
                driver = appium_manager.create_driver(TestLogin.device_capabilities)
                TestLogin.driver = driver
                logger.info("成功创建Appium会话")
            except Exception as e2:
                logger.error(f"重试创建Appium会话失败: {str(e2)}")
                pytest.fail(f"无法连接到Appium服务器: {str(e)}")

        # 测试执行前的清理
        yield

        # 测试结束后清理资源
        if TestLogin.driver:
            try:
                # 检查驱动是否仍然有效
                if hasattr(TestLogin.driver, 'session_id') and TestLogin.driver.session_id:
                    logger.info("关闭Appium会话")
                    TestLogin.driver.quit()
                    TestLogin.driver = None
                else:
                    logger.info("Appium会话已终止，无需再次关闭")
                    TestLogin.driver = None
            except Exception as e:
                logger.error(f"关闭Appium会话时发生错误: {str(e)}")
                TestLogin.driver = None

        logger.info("=" * 60)
        logger.info("登录测试执行完成")
        logger.info("=" * 60)

    @pytest.fixture(scope = "function", autouse = True)
    def setup_method(self):
        """
        测试方法级别的初始化
        确保每个测试方法执行前应用都处于登录页面状态
        """
        logger.info("\n" + "-" * 50)
        logger.info("开始执行测试方法设置")

        # 确保驱动存在且有效
        if not TestLogin.driver:
            logger.error("驱动未初始化")
            pytest.fail("驱动未初始化")

        try:
            # 初始化登录页面
            login_page = LoginPage(TestLogin.driver)
            # 获取应用包名
            app_name = TestLogin.driver.capabilities.get("appPackage")
            # 获取当前设备ID
            device_id = TestLogin.driver.capabilities.get('deviceName')

            # 检查是否已在登录页面
            if login_page.is_element_displayed(login_page.AGREE_BUTTON, 2):
                logger.info("已在登录页面，无需处理")
                return

            logger.warning("清除应用数据，确保应用回到初始状态")

            # 清除应用数据并重新启动
            import subprocess

            # 构建adb命令，指定设备ID
            adb_cmd = ["adb"]
            if device_id:
                adb_cmd.extend(["-s", device_id])
            adb_cmd.extend(["shell", "pm", "clear", app_name])

            result = subprocess.run(adb_cmd, capture_output = True, text = True)
            if result.returncode == 0:
                logger.info("应用数据清除成功")
            else:
                logger.warning(f"应用数据清除失败: {result.stderr}")
                # 尝试不指定设备ID的方式
                logger.info("尝试不指定设备ID清除应用数据")
                result = subprocess.run(["adb", "shell", "pm", "clear", app_name], capture_output = True, text = True)
                if result.returncode == 0:
                    logger.info("应用数据清除成功")
                else:
                    logger.warning(f"应用数据清除再次失败: {result.stderr}")

            # 关闭旧驱动
            if TestLogin.driver:
                TestLogin.driver.quit()
            # 创建新驱动
            TestLogin.driver = TestLogin.appium_manager.create_driver(TestLogin.device_capabilities)
            logger.info("成功重新创建Appium驱动")

            # 重新初始化登录页面
            login_page = LoginPage(TestLogin.driver)
            if not login_page.is_element_displayed(login_page.AGREE_BUTTON, 2):
                logger.error("应用重新启动后未返回到登录页面")
                pytest.fail("应用重新启动后未返回到登录页面")

        except Exception as e:
            logger.error(f"测试方法设置时发生错误: {str(e)}")
            # 如果发生错误，重新创建驱动
            try:
                logger.info("重新创建Appium驱动")
                # 关闭旧驱动
                if TestLogin.driver:
                    TestLogin.driver.quit()
                # 创建新驱动
                TestLogin.driver = TestLogin.appium_manager.create_driver(TestLogin.device_capabilities)
                logger.info("成功重新创建Appium驱动")
            except Exception as e2:
                logger.error(f"重新创建驱动失败: {str(e2)}")
                pytest.fail(f"无法初始化测试环境: {str(e2)}")

        logger.info("测试方法设置完成")
        logger.info("-" * 50)

    @pytest.mark.smoke
    @pytest.mark.app
    def test_login_with_valid_phone_password(self):
        """使用有效的手机号+密码登录"""
        logger.info("测试使用有效的手机号+密码登录")

        # 获取驱动实例
        driver = TestLogin.driver

        # 初始化登录页面
        login_page = LoginPage(driver)

        login_page.agree_protocol()
        login_page.allow_permission()

        # 选择账号密码登录
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON):
            logger.error("未找到账号密码登录按钮")
            pytest.fail("未找到账号密码登录按钮")

        login_page.select_pwd_login()

        # 切换环境
        logger.info("开始环境切换流程")
        # 检查是否需要切换环境
        if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
            logger.info("找到DoKit浮标，开始切换环境")

            # 切换到测试环境
            if login_page.switch_environment():
                logger.info("环境切换成功，应用将自动退出")
                # 重新启动应用
                if login_page.launch_app_by_icon():
                    logger.info("应用重新启动成功")
                else:
                    logger.error("应用重新启动失败")
                    pytest.fail("应用重新启动失败")

        # 登录操作
        logger.info("开始登录操作流程")
        # 选择账号密码登录
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON, 2):
            logger.error("未找到密码登录按钮")
            pytest.fail("未找到密码登录按钮")

        login_page.select_pwd_login()

        # 等待登录页面加载完成
        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        # 选择中国大陆区号
        if not login_page.select_country_code("中国大陆"):
            logger.error("选择中国大陆区号失败")
            pytest.fail("选择中国大陆区号失败")

        # 输入手机号
        login_page.input_phone("17370000003")
        # 输入密码
        login_page.input_password("123456")
        # 点击登录按钮
        login_page.click_login()
        # 等待登录完成
        logger.info("登录操作已执行，等待登录完成")
        # 处理首页弹窗，最多可能有3个
        for _ in range(3):
            if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        assert login_page.is_element_displayed(login_page.HOME_LOGO, 3), "登录失败未进入首页"
        logger.info("账号密码登录成功")

    @pytest.mark.smoke
    @pytest.mark.app
    def test_login_with_valid_phone_captcha(self):
        """使用有效的手机号+密码登录"""
        logger.info("测试使用有效的手机号+密码登录")

        # 获取驱动实例
        driver = TestLogin.driver

        # 初始化登录页面
        login_page = LoginPage(driver)

        login_page.agree_protocol()
        login_page.allow_permission()

        # 选择验证码登录
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 2):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")

        login_page.select_captcha_login()

        # 切换环境
        logger.info("开始环境切换流程")

        # 检查是否需要切换环境
        if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
            logger.info("找到DoKit浮标，开始切换环境")

            # 切换到测试环境
            if login_page.switch_environment():
                logger.info("环境切换成功，应用将自动退出")
                # 重新启动应用
                if login_page.launch_app_by_icon():
                    logger.info("应用重新启动成功")
                else:
                    logger.error("应用重新启动失败")
                    pytest.fail("应用重新启动失败")

        # 登录操作
        logger.info("开始登录操作流程")

        # 选择账号密码登录
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 2):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")

        login_page.select_captcha_login()

        # 等待登录页面加载完成
        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")

        logger.info("登录页面已显示")

        # 选择中国大陆区号
        if not login_page.select_country_code("中国大陆"):
            logger.error("选择中国大陆区号失败")
            pytest.fail("选择中国大陆区号失败")

        # 输入手机号
        login_page.input_phone("17370000004")
        # 获取验证码
        login_page.click_captcha()
        # 从数据库获取验证码
        captcha = None
        try:
            db = MySQLClient()
            captcha_result = db.get_one(
                "select captcha from kong_test.captcha where mobile = %s and type = 10",
                ("8617370000004",)
            )
            captcha = captcha_result["captcha"]
            logger.info(f"获取到的验证码为：{captcha}")
        except Exception as e:
            logger.error(e)
            pytest.fail("从数据库获取验证码失败")

        # 输入验证码
        login_page.input_captcha(captcha)

        # 等待登录完成
        logger.info("登录操作已执行，等待登录完成")
        # 处理首页弹窗，最多可能有3个
        for _ in range(3):
            if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        assert login_page.is_element_displayed(login_page.HOME_LOGO, 3), "登录失败未进入首页"
        logger.info("验证码登录成功")
