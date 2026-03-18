"""
-------------------------------------------------
File:           login_page.py
Author:         duanyang
Date:           2026/2/27
-------------------------------------------------
Description:
This file contains the login_page module, which...
-------------------------------------------------
"""
import time

from utils.app.app_base_page import AppBasePage
from utils.logger_util import logger


class LoginPage(AppBasePage):
    """登录页面对象"""

    # 协议弹窗
    AGREE_BUTTON = ("id", "com.weixiao.voice:id/tv_agree")
    DISAGREE_BUTTON = ("id", "com.weixiao.voice:id/tv_disagree")
    # 系统通知权限弹窗
    NOTIFICATION_TEXT = ("id", "com.android.permissioncontroller:id/permission_message")
    NOTIFICATION_AGREE_BUTTON = ("id", "com.android.permissioncontroller:id/permission_allow_button")
    NOTIFICATION_DISAGREE_BUTTON = ("id", "com.android.permissioncontroller:id/permission_deny_button")
    # 登录页面
    LOGO_IMAGE = ("id", "com.weixiao.voice:id/iv_one_key_login_logo")
    DOKIT_BOTTON = ("id", "com.weixiao.voice:id/float_icon_id")
    DOKIT_ENV_BUTTON = ("id", "com.weixiao.voice:id/icon")
    DOKIT_ENV_TEST_BUTTON = ("xpath", "//*[@text='测试环境']")
    PROBLEM_BUTTON = ("id", "com.weixiao.voice:id/tv_login_problem")
    NEW_USER_TIPS = ("id", "com.weixiao.voice:id/iv_new_user_tip")
    PHONE_LOGIN_BUTTON = ("id", "com.weixiao.voice:id/tv_first_btn")
    PASSWORD_LOGIN_BUTTON = ("id", "com.weixiao.voice:id/tv_second_btn")

    HELP_BUTTON = ("id", "com.weixiao.voice:id/tv_login_HELP")
    AGREEMENT_CHECKBOX = ("id", "com.weixiao.voice:id/iv_login_agreement_checkbox")
    COUNTRY_CODE_BUTTON = ("xpath", "//*[@text=\"+86\"]")
    COUNTRY_CODE_LIST = ("id", "com.weixiao.voice:id/side_bar_country")
    CHINA_COUNTRY_CODE = ("xpath", "(//android.widget.FrameLayout)[19]")
    PHONE_INPUT = ("xpath", "//*[@text=\"请输入手机号码\"]")
    # 密码登录
    PASSWORD_INPUT = ("id", "com.weixiao.voice:id/et_login_input_pwd")
    SHOW_PASSWORD_BUTTON = ("id", "com.weixiao.voice:id/iv_login_show_pwd")
    LOGIN_BUTTON = ("id", "com.weixiao.voice:id/tv_login_btn")
    SWITCH_PHONE_LOGIN_BUTTON = ("id", "com.weixiao.voice:id/tv_login_other_way")
    # 手机号登录
    TIPS_TEXT = ("id", "com.weixiao.voice:id/tv_login_sub_title")
    CAPTCHA_GET_BUTTON = ("id", "com.weixiao.voice:id/tv_login_btn")
    SWITCH_PASSWORD_LOGIN_BUTTON = ("id", "com.weixiao.voice:id/tv_login_other_way")
    BACK_BUTTON = ("id", "com.weixiao.voice:id/ib_bc_back")
    PHONE_TIP_TEXT = ("id", "com.weixiao.voice:id/tv_verify_captcha_sub_title")
    MODIFY_BUTTON = ("id", "com.weixiao.voice:id/tv_verify_captcha_modify")
    COUNT_DOWN_TEXT = ("id", "com.weixiao.voice:id/tv_verify_captcha_count_down")
    CAPTCHA_INPUT = ("id", "com.weixiao.voice:id/civ_verify_captcha")
    CAPTCHA_INPUT_1 = ("id", "com.weixiao.voice:id/et_1")
    CAPTCHA_INPUT_2 = ("id", "com.weixiao.voice:id/et_2")
    CAPTCHA_INPUT_3 = ("id", "com.weixiao.voice:id/et_3")
    CAPTCHA_INPUT_4 = ("id", "com.weixiao.voice:id/et_4")

    HOME_LOGO = ("id", "com.weixiao.voice:id/iv_logo")
    HOME_DIALOG_CLOSE = ("id", "com.weixiao.voice:id/iv_home_dialog_close")

    def agree_protocol(self) -> bool:
        """
        同意协议

        Returns:
            是否同意成功
        """
        logger.info("同意协议")
        # 点击协议按钮
        if not self.click_element(self.AGREE_BUTTON):
            logger.error("点击协议按钮失败")
            return False

        return True

    def allow_permission(self) -> bool:
        """
        同意权限

        Returns:
            是否同意成功
        """
        logger.info("同意通知权限")
        # 点击同意按钮
        if not self.click_element(self.NOTIFICATION_AGREE_BUTTON):
            logger.error("点击同意按钮失败")
            return False

        return True

    def switch_environment(self) -> bool:
        """
        默认切换到测试环境

        Returns:
            是否切换成功
        """
        logger.info("切换环境")
        # 打开DoKit弹窗
        if not self.click_element(self.DOKIT_BOTTON):
            logger.error("打开DoKit弹窗失败")
            return False

        # 等待弹窗出现
        if not self.wait_for_element_visible(self.DOKIT_ENV_BUTTON, timeout = 5):
            logger.error("DoKit弹窗未出现")
            return False

        # 点击接口环境按钮
        self.click_element(self.DOKIT_ENV_BUTTON)

        # 等待测试环境选项出现
        if not self.wait_for_element_visible(self.DOKIT_ENV_TEST_BUTTON, timeout = 5):
            logger.error("未找到测试环境选项")
            return False

        # 点击测试环境选项
        self.click_element(self.DOKIT_ENV_TEST_BUTTON)
        logger.info("已选择测试环境, 应用将自动退出")
        return True

    def select_pwd_login(self):
        """切换到密码登录"""
        logger.info("切换到密码登录")
        self.click_element(self.PASSWORD_LOGIN_BUTTON)

    def select_captcha_login(self):
        """切换到验证码登录"""
        logger.info("切换到验证码登录")
        self.click_element(self.PHONE_LOGIN_BUTTON)

    def select_country_code(self, country_name: str) -> bool:
        """
        选择区号

        Args:
            country_name: 要选择的国家/地区名称

        Returns:
            选择是否成功
        """
        logger.info(f"选择国家/地区: {country_name}")

        # 点击区号按钮, 打开弹窗
        if not self.click_element(self.COUNTRY_CODE_BUTTON):
            logger.error("点击区号按钮失败")
            return False

        # 等待弹窗出现
        if not self.is_element_displayed(self.COUNTRY_CODE_LIST):
            logger.error("区号选择弹窗未出现")
            return False

        # 在弹窗中选择地区
        try:
            # 直接查找中国大陆选项
            china_locator = ("xpath", f"//*[@text='{country_name}']")

            # 滚动直到找到目标元素
            for _ in range(10):  # 最多滚动10次
                if self.is_element_displayed(china_locator):
                    # 点击目标地区
                    if self.click_element(china_locator):
                        logger.info(f"成功选择国家/地区: {country_name}")
                        return True
                # 向上滚动
                self.scroll_up(50)
                time.sleep(0.5)

            logger.error(f"未找到国家/地区: {country_name}")
            return False

        except Exception as e:
            logger.error(f"选择国家/地区时发生错误: {str(e)}")
            return False

    def input_phone(self, phone):
        """输入手机号"""
        logger.info(f"输入手机号: {phone}")
        self.send_keys_to_element(self.PHONE_INPUT, phone)

    def input_password(self, password):
        """输入密码"""
        logger.info("输入密码: ******")
        self.send_keys_to_element(self.PASSWORD_INPUT, password)

    def click_login(self):
        """点击登录按钮"""
        logger.info("点击登录按钮")
        self.click_element(self.LOGIN_BUTTON)

    def click_captcha(self):
        """点击获取验证码"""
        return self.click_element(self.CAPTCHA_GET_BUTTON)

    def input_captcha(self, captcha):
        """输入验证码

        Args:
            captcha: 4位数字验证码
        """
        logger.info(f"输入验证码: {captcha}")
        # 确保验证码是4位数字
        if len(captcha) != 4:
            logger.error(f"验证码长度错误, 应为4位, 实际为{len(captcha)}位")
            return False

        # 准备验证码输入框列表
        captcha_inputs = [
            self.CAPTCHA_INPUT_1,
            self.CAPTCHA_INPUT_2,
            self.CAPTCHA_INPUT_3,
            self.CAPTCHA_INPUT_4
        ]

        # 输入验证码
        for i, digit in enumerate(captcha):
            if not self.send_keys_to_element(captcha_inputs[i], digit, timeout = 1):
                logger.error(f"输入第{i + 1}位验证码失败")
                return False

        logger.info("验证码输入成功")
        return True
