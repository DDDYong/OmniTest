"""
-------------------------------------------------
File:           test_app_login.py
Author:         duanyang
Date:           2026/03/06
-------------------------------------------------
Description:
支持并行执行的App登录测试用例
-------------------------------------------------
"""
import allure
import pytest

from cases.app.pages.login_page import LoginPage
from utils.db.mysql_client import MySQLClient
from utils.decorator_util import app_test
from utils.file_util import FileHandler
from utils.logger_util import logger


@pytest.mark.parallel
class TestLoginParallel:
    """支持并行执行的登录功能测试类"""

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
        确保每个测试方法执行前应用都处于登录页面状态
        """
        logger.info("\n" + "-" * 50)
        logger.info(f"开始执行测试方法: {request.node.name}")

        driver = parallel_appium_driver

        try:
            login_page = LoginPage(driver, test_data = self.__class__.test_data)
            
            if login_page.is_element_displayed(login_page.AGREE_BUTTON, 2):
                logger.info("已在登录页面, 无需处理")
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

            login_page = LoginPage(driver, test_data = self.__class__.test_data)
            if not login_page.is_element_displayed(login_page.AGREE_BUTTON, 5):
                logger.error("应用重置后未返回到登录页面")
                pytest.fail("应用重置后未返回到登录页面")

        except Exception as e:
            logger.error(f"测试方法设置时发生错误: {str(e)}")
            pytest.fail(f"无法初始化测试环境: {str(e)}")

        logger.info("测试方法设置完成")
        logger.info("-" * 50)

    @app_test(
        smoke = True,
        feature = "登录功能",
        story = "密码登录",
        title = "密码登录测试",
        tags = ["smoke", "app", "login"],
        severity = "critical",
        description = "测试用户使用正确的手机号和密码进行登录的功能"
    )
    def test_login_with_valid_phone_password(self, parallel_appium_driver):
        """手机号+有效的密码登录"""
        scenario_name = "password_login_valid"
        logger.info(f"测试使用手机号+有效的密码登录 - 场景: {scenario_name}")

        driver = parallel_appium_driver
        login_page = LoginPage(driver, test_data = self.__class__.test_data)

        # 获取测试数据和预期结果
        with allure.step("密码登录测试"):
            test_data = login_page.get_test_data(scenario_name)
            expected = login_page.get_expected_result(scenario_name)

        with allure.step("同意协议"):
            login_page.agree_protocol()
        with allure.step("同意权限"):
            login_page.allow_permission()

        with allure.step("选择密码登录"):
            if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON):
                logger.error("未找到账号密码登录按钮")
                pytest.fail("未找到账号密码登录按钮")
            login_page.select_pwd_login()

        with allure.step("开始环境切换流程"):
            logger.info("开始环境切换流程")
            if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
                with allure.step("点击DoKit浮标"):
                    logger.info("找到DoKit浮标, 开始切换环境")
                with allure.step("切换环境"):
                    if login_page.switch_environment():
                        with allure.step("环境切换成功, 重新启动"):
                            logger.info("环境切换成功, 应用将自动退出")
                            if login_page.launch_app_by_icon():
                                logger.info("应用重新启动成功")
                            else:
                                logger.error("应用重新启动失败")
                                pytest.fail("应用重新启动失败")
        with allure.step("开始登录操作流程"):
            logger.info("开始登录操作流程")
            if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON, 5):
                logger.error("未找到密码登录按钮")
                pytest.fail("未找到密码登录按钮")
        with allure.step("选择密码登录"):
            login_page.select_pwd_login()
        
        if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
            logger.error("登录页面未显示")
            pytest.fail("登录页面未显示")
        logger.info("登录页面已显示")

        with allure.step("选择国家区号"):
            country_code = test_data.get("country_code", "中国大陆")
            if not login_page.select_country_code(country_code):
                logger.error(f"选择{country_code}区号失败")
                pytest.fail(f"选择{country_code}区号失败")

        with allure.step("输入手机号"):
            phone = test_data.get("phone", "")
            login_page.input_phone(phone)
        with allure.step("输入密码"):
            password = test_data.get("password", "")
            login_page.input_password(password)
        with allure.step("点击登录按钮"):
            login_page.click_login()

        with allure.step("等待登录完成"):
            logger.info("登录操作已执行, 等待登录完成")
            for _ in range(3):
                if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                    login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        with allure.step("验证是否登录成功进入首页"):
            assert login_page.is_element_displayed(login_page.HOME_LOGO, 3) == expected[
                "home_screen_displayed"], "登录失败未进入首页"
            logger.info("账号密码登录成功")

    @app_test(
        feature = "登录功能",
        story = "密码登录",
        title = "错误密码登录测试",
        tags = ["app", "login", "password"],
        severity = "normal",
        description = "测试用户使用正确的手机号和错误的密码进行登录的功能"
    )
    def test_login_with_invalid_phone_password(self, parallel_appium_driver):
        """手机号+错误的密码登录"""
        scenario_name = "password_login_invalid"
        logger.info(f"测试使用手机号+错误的密码登录 - 场景: {scenario_name}")

        driver = parallel_appium_driver
        login_page = LoginPage(driver, test_data = self.__class__.test_data)

        # 获取测试数据和预期结果
        with allure.step("错误密码登录测试"):
            test_data = login_page.get_test_data(scenario_name)
            expected = login_page.get_expected_result(scenario_name)

        with allure.step("同意协议"):
            login_page.agree_protocol()
        with allure.step("同意权限"):
            login_page.allow_permission()

        with allure.step("选择密码登录"):
            if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON):
                logger.error("未找到账号密码登录按钮")
                pytest.fail("未找到账号密码登录按钮")
            login_page.select_pwd_login()

        with allure.step("开始环境切换流程"):
            logger.info("开始环境切换流程")
            if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
                with allure.step("点击DoKit浮标"):
                    logger.info("找到DoKit浮标, 开始切换环境")
                with allure.step("切换环境"):
                    if login_page.switch_environment():
                        with allure.step("环境切换成功, 重新启动"):
                            logger.info("环境切换成功, 应用将自动退出")
                            if login_page.launch_app_by_icon():
                                logger.info("应用重新启动成功")
                            else:
                                logger.error("应用重新启动失败")
                                pytest.fail("应用重新启动失败")

        with allure.step("开始登录操作流程"):
            logger.info("开始登录操作流程")
            if not login_page.is_element_displayed(login_page.PASSWORD_LOGIN_BUTTON, 5):
                logger.error("未找到密码登录按钮")
                pytest.fail("未找到密码登录按钮")

        with allure.step("选择密码登录"):
            login_page.select_pwd_login()

        with allure.step("等待登录按钮可见"):
            if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
                logger.error("登录页面未显示")
                pytest.fail("登录页面未显示")
            logger.info("登录页面已显示")

        with allure.step("选择国家区号"):
            country_code = test_data.get("country_code", "中国大陆")
            if not login_page.select_country_code(country_code):
                logger.error(f"选择{country_code}区号失败")
                pytest.fail(f"选择{country_code}区号失败")

        with allure.step("输入手机号"):
            phone = test_data.get("phone", "")
            login_page.input_phone(phone)
        with allure.step("输入错误密码"):
            password = test_data.get("password", "")
            login_page.input_password(password)
        with allure.step("点击登录按钮"):
            login_page.click_login()

        with allure.step("验证错误提示"):
            expected_toast = expected.get("toast_message", "账号或密码错误")
            assert login_page.check_for_toast(expected_toast, 10)
            logger.info("✅账号+错误的密码登录失败")

    @app_test(
        smoke = True,
        feature = "登录功能",
        story = "验证码登录",
        title = "验证码登录测试",
        tags = ["smoke", "app", "login", "captcha"],
        severity = "critical",
        description = "测试用户使用正确的手机号和有效验证码进行登录的功能"
    )
    def test_login_with_valid_phone_captcha(self, parallel_appium_driver):
        """使用手机号+有效验证码登录"""
        scenario_name = "captcha_login_valid"
        logger.info(f"使用手机号+有效验证码登录 - 场景: {scenario_name}")

        driver = parallel_appium_driver
        login_page = LoginPage(driver, test_data = self.__class__.test_data)

        # 获取测试数据和预期结果
        with allure.step("验证码登录测试"):
            test_data = login_page.get_test_data(scenario_name)
            expected = login_page.get_expected_result(scenario_name)

        with allure.step("同意协议"):
            login_page.agree_protocol()
        with allure.step("同意权限"):
            login_page.allow_permission()

        with allure.step("选择验证码登录"):
            if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
                logger.error("未找到验证码登录按钮")
                pytest.fail("未找到验证码登录按钮")
            login_page.select_captcha_login()

        with allure.step("开始环境切换流程"):
            logger.info("开始环境切换流程")
            if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
                with allure.step("点击DoKit浮标"):
                    logger.info("找到DoKit浮标, 开始切换环境")
                with allure.step("切换环境"):
                    if login_page.switch_environment():
                        with allure.step("环境切换成功, 重新启动"):
                            logger.info("环境切换成功, 应用将自动退出")
                            if login_page.launch_app_by_icon():
                                logger.info("应用重新启动成功")
                            else:
                                logger.error("应用重新启动失败")
                                pytest.fail("应用重新启动失败")

        with allure.step("开始登录操作流程"):
            logger.info("开始登录操作流程")
            if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
                logger.error("未找到验证码登录按钮-2")
                pytest.fail("未找到验证码登录按钮-2")

        with allure.step("选择验证码登录"):
            login_page.select_captcha_login()

        with allure.step("等待登录按钮可见"):
            if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
                logger.error("登录页面未显示")
                pytest.fail("登录页面未显示")
            logger.info("登录页面已显示")

        with allure.step("选择国家区号"):
            country_code = test_data.get("country_code", "中国大陆")
            if not login_page.select_country_code(country_code):
                logger.error(f"选择{country_code}区号失败")
                pytest.fail(f"选择{country_code}区号失败")

        with allure.step("输入手机号"):
            phone = test_data.get("phone", "")
            login_page.input_phone(phone)
        with allure.step("点击获取验证码"):
            login_page.click_captcha()

        with allure.step("从数据库获取验证码"):
            captcha = None
            try:
                db = MySQLClient()
                db_query = test_data.get("db_query", "select captcha from kong_test.captcha where mobile = %s and type = 10")
                db_params = test_data.get("db_params", ["8617370000004"])
                captcha_result = db.get_one(db_query, db_params)
                captcha = captcha_result["captcha"]
                logger.info(f"获取到的验证码为: {captcha}")
            except Exception as e:
                logger.error(e)
                pytest.fail("从数据库获取验证码失败")

        with allure.step("输入验证码"):
            login_page.input_captcha(captcha)

        with allure.step("等待登录完成"):
            logger.info("登录操作已执行, 等待登录完成")
            for _ in range(3):
                if login_page.is_element_displayed(login_page.HOME_DIALOG_CLOSE, 1):
                    login_page.click_element(login_page.HOME_DIALOG_CLOSE)
        with allure.step("验证是否登录成功进入首页"):
            assert login_page.is_element_displayed(login_page.HOME_LOGO, 3), "登录失败未进入首页"
            logger.info("✅手机号+验证码登录成功")

    @app_test(
        feature = "登录功能",
        story = "验证码登录",
        title = "错误验证码登录测试",
        tags = ["app", "login", "captcha"],
        severity = "normal",
        description = "测试用户使用正确的手机号和错误的验证码进行登录的功能"
    )
    def test_login_with_invalid_phone_captcha(self, parallel_appium_driver):
        """使用手机号+错误的验证码登录"""
        scenario_name = "captcha_login_invalid"
        logger.info(f"使用手机号+错误的验证码登录 - 场景: {scenario_name}")

        driver = parallel_appium_driver
        login_page = LoginPage(driver, test_data = self.__class__.test_data)

        # 获取测试数据和预期结果
        with allure.step("错误验证码登录测试"):
            test_data = login_page.get_test_data(scenario_name)
            expected = login_page.get_expected_result(scenario_name)

        with allure.step("同意协议"):
            login_page.agree_protocol()
        with allure.step("同意权限"):
            login_page.allow_permission()

        with allure.step("选择验证码登录"):
            if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
                logger.error("未找到验证码登录按钮")
                pytest.fail("未找到验证码登录按钮")
            login_page.select_captcha_login()

        with allure.step("开始环境切换流程"):
            logger.info("开始环境切换流程")
            if login_page.is_element_displayed(login_page.DOKIT_BOTTON, 2):
                with allure.step("点击DoKit浮标"):
                    logger.info("找到DoKit浮标, 开始切换环境")
                with allure.step("切换环境"):
                    if login_page.switch_environment():
                        with allure.step("环境切换成功, 重新启动"):
                            logger.info("环境切换成功, 应用将自动退出")
                            if login_page.launch_app_by_icon():
                                logger.info("应用重新启动成功")
                            else:
                                logger.error("应用重新启动失败")
                                pytest.fail("应用重新启动失败")

        with allure.step("开始登录操作流程"):
            logger.info("开始登录操作流程")
            if not login_page.is_element_displayed(login_page.PHONE_LOGIN_BUTTON, 5):
                logger.error("未找到验证码登录按钮")
                pytest.fail("未找到验证码登录按钮")

        with allure.step("选择验证码登录"):
            login_page.select_captcha_login()

        with allure.step("等待登录按钮可见"):
            if not login_page.wait_for_element_visible(login_page.LOGIN_BUTTON, timeout = 5):
                logger.error("登录页面未显示")
                pytest.fail("登录页面未显示")
            logger.info("登录页面已显示")

        with allure.step("选择国家区号"):
            country_code = test_data.get("country_code", "中国大陆")
            if not login_page.select_country_code(country_code):
                logger.error(f"选择{country_code}区号失败")
                pytest.fail(f"选择{country_code}区号失败")

        with allure.step("输入手机号"):
            phone = test_data.get("phone", "")
            login_page.input_phone(phone)
        with allure.step("点击获取验证码"):
            login_page.click_captcha()
        with allure.step("输入错误验证码"):
            invalid_captcha = test_data.get("invalid_captcha", "0000")
            login_page.input_captcha(invalid_captcha)

        with allure.step("验证错误提示"):
            expected_toast = expected.get("toast_message", "验证码已经失效啦")
            assert login_page.check_for_toast(expected_toast, 10)
            logger.info("✅手机号+错误的验证码登录失败")
