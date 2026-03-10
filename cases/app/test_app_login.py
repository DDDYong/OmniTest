"""
-------------------------------------------------
File:           test_app_login.py
Author:         duanyang
Date:           2026/03/06
-------------------------------------------------
Description:
简化版支持并行执行的App登录测试用例
使用pytest-xdist + 多设备并行，保持与原测试文件相同逻辑
-------------------------------------------------
"""

import pytest

from cases.app.pages.login_page import LoginPage
from utils.db.mysql_client import MySQLClient
from utils.logger_util import logger


@pytest.mark.parallel
class TestLoginParallelSimple:
    """支持并行执行的登录功能测试类 - 简化版"""

    @pytest.fixture(scope = "function", autouse = True)
    def setup_method(self, parallel_appium_driver, request):
        """
        测试方法级别的初始化
        确保每个测试方法执行前应用都处于登录页面状态
        """
        logger.info("\n" + "-" * 50)
        logger.info(f"开始执行测试方法: {request.node.name}")

        driver = parallel_appium_driver

        try:
            login_page = LoginPage(driver)
            
            if login_page.is_element_displayed(login_page.AGREE_BUTTON, 2):
                logger.info("已在登录页面，无需处理")
                return

            logger.warning("重置应用状态")

            try:
                driver.reset()
                logger.info("应用重置成功")
            except Exception as e:
                logger.warning(f"应用重置失败: {str(e)}")
                app_package = driver.capabilities.get("appPackage")
                app_activity = driver.capabilities.get("appActivity")

                if app_package and app_activity:
                    driver.activate_app(app_package)

            login_page = LoginPage(driver)
            if not login_page.is_element_displayed(login_page.AGREE_BUTTON, 5):
                logger.error("应用重置后未返回到登录页面")
                pytest.fail("应用重置后未返回到登录页面")

        except Exception as e:
            logger.error(f"测试方法设置时发生错误: {str(e)}")
            pytest.fail(f"无法初始化测试环境: {str(e)}")

        logger.info("测试方法设置完成")
        logger.info("-" * 50)

    @pytest.mark.smoke
    @pytest.mark.app
    @pytest.mark.parallel
    def test_login_with_valid_phone_password(self, parallel_appium_driver):
        """手机号+有效的密码登录"""
        logger.info("测试使用手机号+有效的密码登录")

        driver = parallel_appium_driver
        login_page = LoginPage(driver)

        login_page.agree_protocol()
        login_page.allow_permission()

        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON):
            logger.error("未找到账号密码登录按钮")
            pytest.fail("未找到账号密码登录按钮")

        login_page.select_pwd_login()

        logger.info("开始环境切换流程")
        if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
            logger.info("找到DoKit浮标，开始切换环境")
            if login_page.switch_environment():
                logger.info("环境切换成功，应用将自动退出")
                if login_page.launch_app_by_icon():
                    logger.info("应用重新启动成功")
                else:
                    logger.error("应用重新启动失败")
                    pytest.fail("应用重新启动失败")

        logger.info("开始登录操作流程")
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON, 5):
            logger.error("未找到密码登录按钮")
            pytest.fail("未找到密码登录按钮")

        login_page.select_pwd_login()

        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        if not login_page.select_country_code("中国大陆"):
            logger.error("选择中国大陆区号失败")
            pytest.fail("选择中国大陆区号失败")

        login_page.input_phone("17370000003")
        login_page.input_password("123456")
        login_page.click_login()

        logger.info("登录操作已执行，等待登录完成")
        for _ in range(3):
            if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        assert login_page.is_element_displayed(login_page.HOME_LOGO, 3), "登录失败未进入首页"
        logger.info("账号密码登录成功")

    @pytest.mark.app
    @pytest.mark.parallel
    @pytest.mark.skip
    def test_login_with_invalid_phone_password(self, parallel_appium_driver):
        """手机号+错误的密码登录"""
        logger.info("测试使用手机号+错误的密码登录")

        driver = parallel_appium_driver
        login_page = LoginPage(driver)

        login_page.agree_protocol()
        login_page.allow_permission()

        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON):
            logger.error("未找到账号密码登录按钮")
            pytest.fail("未找到账号密码登录按钮")

        login_page.select_pwd_login()

        logger.info("开始环境切换流程")
        if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
            logger.info("找到DoKit浮标，开始切换环境")
            if login_page.switch_environment():
                logger.info("环境切换成功，应用将自动退出")
                if login_page.launch_app_by_icon():
                    logger.info("应用重新启动成功")
                else:
                    logger.error("应用重新启动失败")
                    pytest.fail("应用重新启动失败")

        logger.info("开始登录操作流程")
        if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON, 5):
            logger.error("未找到密码登录按钮")
            pytest.fail("未找到密码登录按钮")

        login_page.select_pwd_login()

        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        if not login_page.select_country_code("中国大陆"):
            logger.error("选择中国大陆区号失败")
            pytest.fail("选择中国大陆区号失败")

        login_page.input_phone("17370000003")
        login_page.input_password("17370000003")
        login_page.click_login()

        assert login_page.check_for_toast("账号或密码错误", 10)
        logger.info("✅账号+错误的密码登录失败")

    @pytest.mark.smoke
    @pytest.mark.app
    @pytest.mark.parallel
    @pytest.mark.skip
    def test_login_with_valid_phone_captcha(self, parallel_appium_driver):
        """使用手机号+有效验证码登录"""
        logger.info("使用手机号+有效验证码登录")

        driver = parallel_appium_driver
        login_page = LoginPage(driver)

        login_page.agree_protocol()
        login_page.allow_permission()

        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
            logger.error("未找到验证码登录按钮-1")
            pytest.fail("未找到验证码登录按钮-1")

        login_page.select_captcha_login()

        logger.info("开始环境切换流程")
        if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
            logger.info("找到DoKit浮标，开始切换环境")
            if login_page.switch_environment():
                logger.info("环境切换成功，应用将自动退出")
                if login_page.launch_app_by_icon():
                    logger.info("应用重新启动成功")
                else:
                    logger.error("应用重新启动失败")
                    pytest.fail("应用重新启动失败")

        logger.info("开始登录操作流程")
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
            logger.error("未找到验证码登录按钮-2")
            pytest.fail("未找到验证码登录按钮-2")

        login_page.select_captcha_login()

        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")

        logger.info("登录页面已显示")

        if not login_page.select_country_code("中国大陆"):
            logger.error("选择中国大陆区号失败")
            pytest.fail("选择中国大陆区号失败")

        login_page.input_phone("17370000004")
        login_page.click_captcha()

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

        login_page.input_captcha(captcha)

        logger.info("登录操作已执行，等待登录完成")
        for _ in range(3):
            if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        assert login_page.is_element_displayed(login_page.HOME_LOGO, 3), "登录失败未进入首页"
        logger.info("✅手机号+验证码登录成功")

    @pytest.mark.app
    @pytest.mark.parallel
    @pytest.mark.skip
    def test_login_with_invalid_phone_captcha(self, parallel_appium_driver):
        """使用手机号+错误的验证码登录"""
        logger.info("使用手机号+错误的验证码登录")

        driver = parallel_appium_driver
        login_page = LoginPage(driver)

        login_page.agree_protocol()
        login_page.allow_permission()

        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")

        login_page.select_captcha_login()

        logger.info("开始环境切换流程")
        if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
            logger.info("找到DoKit浮标，开始切换环境")
            if login_page.switch_environment():
                logger.info("环境切换成功，应用将自动退出")
                if login_page.launch_app_by_icon():
                    logger.info("应用重新启动成功")
                else:
                    logger.error("应用重新启动失败")
                    pytest.fail("应用重新启动失败")

        logger.info("开始登录操作流程")
        if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
            logger.error("未找到验证码登录按钮")
            pytest.fail("未找到验证码登录按钮")

        login_page.select_captcha_login()

        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")

        logger.info("登录页面已显示")

        if not login_page.select_country_code("中国大陆"):
            logger.error("选择中国大陆区号失败")
            pytest.fail("选择中国大陆区号失败")

        login_page.input_phone("17370000004")
        login_page.click_captcha()
        login_page.input_captcha("0000")

        assert login_page.check_for_toast("验证码已经失效啦", 10)
        logger.info("✅手机号+错误的验证码登录失败")
