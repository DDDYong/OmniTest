"""
-------------------------------------------------
File:           test_app_login_debug.py
Author:         duanyang
Date:           2026/2/27
-------------------------------------------------
Description:
登录功能调试测试类,用于开发调试阶段使用
-------------------------------------------------
"""

import pytest

from cases.app.pages.login_page import LoginPage
from utils import assert_util as AssertUtil
from utils.db.mysql_client import MySQLClient
from utils.logger import logger


class TestLogin:
    """登录功能测试类"""

    driver = None
    appium_manager = None

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

        # 加载测试数据
        from utils.file import FileHandler
        try:
            config_data = FileHandler().read_yaml("config/app_config.yaml")
            app_config = config_data["android_app_test"]
            TestLogin.device_capabilities = app_config["device_capabilities"]
            appium_server = app_config["appium_server"]
            
            test_data = FileHandler.get_test_data("test_data/app_test_cases.yaml")
            TestLogin.test_data = test_data
            logger.info("成功加载测试数据")
        except Exception as e:
            logger.error(f"加载测试数据失败: {str(e)}")
            pytest.skip("无法加载测试数据,跳过测试")

        # 创建Appium驱动
        try:
            logger.info("创建Appium驱动")
            TestLogin.driver = appium_manager.create_driver(TestLogin.device_capabilities)
            logger.info("成功创建Appium会话")
        except Exception as e:
            logger.error(f"创建Appium会话失败: {str(e)}")
            pytest.fail(f"无法连接到Appium服务器: {str(e)}")

        # 测试执行前的清理
        yield

        # 测试结束后清理资源
        if TestLogin.driver:
            try:
                logger.info("关闭Appium会话")
                TestLogin.driver.quit()
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

            # 检查是否已在登录页面
            if login_page.is_element_displayed(login_page.AGREE_BUTTON, 2):
                logger.info("已在登录页面, 无需处理")
                return

            logger.warning("重置应用状态")

            # 重置应用
            TestLogin.driver.reset()
            
            # 重新初始化登录页面
            login_page = LoginPage(TestLogin.driver)
            if not login_page.is_element_displayed(login_page.AGREE_BUTTON, 5):
                logger.error("应用重置后未返回到登录页面")
                pytest.fail("应用重置后未返回到登录页面")

        except Exception as e:
            logger.error(f"测试方法设置时发生错误: {str(e)}")
            pytest.fail(f"无法初始化测试环境: {str(e)}")

        logger.info("测试方法设置完成")
        logger.info("-" * 50)

    def _switch_test_environment(self, login_page):
        """
        切换到测试环境
        """
        if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
            logger.info("找到DoKit浮标, 开始切换环境")
            if login_page.switch_environment():
                logger.info("环境切换成功, 应用将自动退出")
                if login_page.launch_app_by_icon():
                    logger.info("应用重新启动成功")
                    return True
                else:
                    logger.error("应用重新启动失败")
                    pytest.fail("应用重新启动失败")
        return False
    
    @pytest.mark.smoke
    @pytest.mark.app
    def test_login_with_valid_phone_password(self):
        """手机号+有效的密码登录"""
        logger.info("测试使用手机号+有效的密码登录")

        # 获取驱动实例
        driver = TestLogin.driver
        login_page = LoginPage(driver)
        assert_util = AssertUtil(driver)

        # 同意协议和权限
        login_page.agree_protocol_and_permission()

        # 选择账号密码登录
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON):
            logger.error("未找到账号密码登录按钮")
            pytest.fail("未找到账号密码登录按钮")
        login_page.select_pwd_login()

        # 切换测试环境
        self._switch_test_environment(login_page)

        # 重新选择密码登录
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON, 2):
            logger.error("未找到密码登录按钮")
            pytest.fail("未找到密码登录按钮")
        login_page.select_pwd_login()

        # 等待登录页面加载完成
        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        # 使用默认的中国大陆区号,无需额外选择
        logger.info("使用默认的中国大陆区号")

        # 执行登录操作
        login_page.input_phone("17370000003")
        login_page.input_password("123456")
        login_page.click_login()

        # 验证登录结果
        logger.info("登录操作已执行, 等待登录完成")
        # 处理首页弹窗
        for _ in range(3):
            if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        assert_util.equals(login_page.is_element_displayed(login_page.HOME_LOGO, 3), True, "登录失败未进入首页")
        logger.info("账号密码登录成功")

    @pytest.mark.app
    def test_login_with_invalid_phone_password(self):
        """手机号+错误的密码登录"""
        logger.info("测试使用手机号+错误的密码登录")

        # 获取驱动实例
        driver = TestLogin.driver
        login_page = LoginPage(driver)
        assert_util = AssertUtil(driver)

        # 同意协议和权限
        login_page.agree_protocol_and_permission()

        # 选择账号密码登录
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON):
            logger.error("未找到账号密码登录按钮")
            pytest.fail("未找到账号密码登录按钮")
        login_page.select_pwd_login()

        # 切换测试环境
        self._switch_test_environment(login_page)

        # 重新选择密码登录
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON, 2):
            logger.error("未找到密码登录按钮")
            pytest.fail("未找到密码登录按钮")
        login_page.select_pwd_login()

        # 等待登录页面加载完成
        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        # 使用默认的中国大陆区号,无需额外选择
        logger.info("使用默认的中国大陆区号")

        # 执行登录操作
        login_page.input_phone("17370000003")
        login_page.input_password("17370000003")
        login_page.click_login()

        # 验证错误提示
        assert_util.is_true(login_page.check_for_toast("账号或密码错误", 10))
        logger.info("✅账号+错误的密码登录失败")

    @pytest.mark.smoke
    @pytest.mark.app
    def test_login_with_valid_phone_captcha(self):
        """使用手机号+有效验证码登录"""
        logger.info("使用手机号+有效验证码登录")

        # 获取驱动实例
        driver = TestLogin.driver
        login_page = LoginPage(driver)
        assert_util = AssertUtil(driver)

        # 同意协议和权限
        login_page.agree_protocol_and_permission()

        # 选择验证码登录
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 2):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")
        login_page.select_captcha_login()

        # 切换测试环境
        self._switch_test_environment(login_page)

        # 重新选择验证码登录
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 2):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")
        login_page.select_captcha_login()

        # 等待登录页面加载完成
        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        # 使用默认的中国大陆区号,无需额外选择
        logger.info("使用默认的中国大陆区号")

        # 输入手机号并获取验证码
        login_page.input_phone("17370000004")
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
            logger.info(f"获取到的验证码为: {captcha}")
        except Exception as e:
            logger.error(e)
            pytest.fail("从数据库获取验证码失败")

        # 输入验证码并登录
        login_page.input_captcha(captcha)

        # 验证登录结果
        logger.info("登录操作已执行, 等待登录完成")
        # 处理首页弹窗
        for _ in range(3):
            if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        assert_util.equals(login_page.is_element_displayed(login_page.HOME_LOGO, 3), True, "登录失败未进入首页")
        logger.info("✅手机号+验证码登录成功")

    @pytest.mark.app
    def test_login_with_invalid_phone_captcha(self):
        """使用手机号+错误的验证码登录"""
        logger.info("使用手机号+错误的验证码登录")

        # 获取驱动实例
        driver = TestLogin.driver
        login_page = LoginPage(driver)
        assert_util = AssertUtil(driver)

        # 同意协议和权限
        login_page.agree_protocol_and_permission()

        # 选择验证码登录
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 2):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")
        login_page.select_captcha_login()

        # 切换测试环境
        self._switch_test_environment(login_page)

        # 重新选择验证码登录
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 2):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")
        login_page.select_captcha_login()

        # 等待登录页面加载完成
        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        # 使用默认的中国大陆区号,无需额外选择
        logger.info("使用默认的中国大陆区号")

        # 输入手机号并获取验证码
        login_page.input_phone("17370000004")
        login_page.click_captcha()
        login_page.input_captcha("0000")

        # 验证错误提示
        assert_util.is_true(login_page.check_for_toast("验证码已经失效啦", 10))
        logger.info("✅手机号+错误的验证码登录失败")
