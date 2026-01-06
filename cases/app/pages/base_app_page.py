"""
-------------------------------------------------
File:           base_app_page.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
App测试 - 基础页面类
提供移动应用测试的基础操作方法,包括元素定位、等待、交互等功能
-------------------------------------------------
"""
import time
from typing import Any, Optional, Tuple

from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotVisibleException,
    ElementNotSelectableException,
    TimeoutException
)
# 简化导入，避免appium版本兼容性问题
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.config_manager import config
from utils.logger_util import logger


class BaseAppPage:
    """
    App测试的基础页面类
    封装了App测试中常用的元素定位、等待和交互方法
    """

    # 元素定位策略映射
    LOCATOR_STRATEGIES = {
        "id": By.ID,
        "xpath": By.XPATH,
        "class_name": By.CLASS_NAME,
        "accessibility_id": "accessibility id",  # 简化处理
        "android_uiautomator": "-android uiautomator",  # 简化处理
        "ios_uiautomation": "-ios uiautomation",  # 简化处理
        "name": By.NAME,
        "tag_name": By.TAG_NAME,
        "link_text": By.LINK_TEXT,
        "partial_link_text": By.PARTIAL_LINK_TEXT
    }

    def __init__(self, driver):  # 简化类型注解
        """
        初始化基础页面类
        
        Args:
            driver: Appium WebDriver实例
        """
        self.driver = driver
        self.logger = logger

        # 从配置获取等待时间设置
        self.implicit_wait = getattr(config, "IMPLICIT_WAIT", 10)
        self.explicit_wait = getattr(config, "EXPLICIT_WAIT", 20)
        self.polling_interval = getattr(config, "POLLING_INTERVAL", 0.5)

        # 设置隐式等待
        self.set_implicit_wait(self.implicit_wait)

        self.logger.info(f"初始化 {self.__class__.__name__}")

    def set_implicit_wait(self, timeout: int = 10) -> None:
        """
        设置隐式等待时间
        
        Args:
            timeout: 等待超时时间（秒）
        """
        self.driver.implicitly_wait(timeout)
        self.logger.debug(f"设置隐式等待时间: {timeout}秒")

    def set_explicit_wait(self, timeout: int = 20) -> WebDriverWait:
        """
        创建显式等待对象
        
        Args:
            timeout: 等待超时时间（秒）
            
        Returns:
            WebDriverWait实例
        """
        return WebDriverWait(
            self.driver,
            timeout = timeout,
            poll_frequency = self.polling_interval,
            ignored_exceptions = [
                NoSuchElementException,
                ElementNotVisibleException,
                ElementNotSelectableException
            ]
        )

    def find_element(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> Optional[Any]:
        """
        查找单个元素
        
        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值
            
        Returns:
            找到的元素对象,如果未找到则返回None
        """
        strategy, value = locator

        if strategy not in self.LOCATOR_STRATEGIES:
            self.logger.error(f"无效的定位策略: {strategy}")
            return None

        try:
            if timeout is None:
                timeout = self.explicit_wait

            # 转换定位策略
            by = self.LOCATOR_STRATEGIES[strategy]

            self.logger.debug(f"查找元素: {strategy}={value}, 超时={timeout}秒")
            element = self.set_explicit_wait(timeout).until(
                EC.presence_of_element_located((by, value))
            )

            self.logger.debug(f"成功找到元素: {strategy}={value}")
            return element

        except TimeoutException:
            self.logger.warning(f"未找到元素: {strategy}={value}, 超时={timeout}秒")
            return None
        except Exception as e:
            self.logger.error(f"查找元素时发生错误: {strategy}={value}, 错误: {str(e)}")
            return None

    def find_elements(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> list:
        """
        查找多个元素
        
        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值
            
        Returns:
            元素对象列表,如果未找到则返回空列表
        """
        strategy, value = locator

        if strategy not in self.LOCATOR_STRATEGIES:
            self.logger.error(f"无效的定位策略: {strategy}")
            return []

        try:
            if timeout is None:
                timeout = self.explicit_wait

            # 转换定位策略
            by = self.LOCATOR_STRATEGIES[strategy]

            self.logger.debug(f"查找多个元素: {strategy}={value}, 超时={timeout}秒")
            elements = self.set_explicit_wait(timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )

            self.logger.debug(f"找到 {len(elements)} 个元素: {strategy}={value}")
            return elements

        except TimeoutException:
            self.logger.warning(f"未找到元素: {strategy}={value}, 超时={timeout}秒")
            return []
        except Exception as e:
            self.logger.error(f"查找元素时发生错误: {strategy}={value}, 错误: {str(e)}")
            return []

    def wait_for_element_visible(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> bool:
        """
        等待元素可见
        
        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值
            
        Returns:
            元素是否可见
        """
        strategy, value = locator

        if strategy not in self.LOCATOR_STRATEGIES:
            self.logger.error(f"无效的定位策略: {strategy}")
            return False

        try:
            if timeout is None:
                timeout = self.explicit_wait

            # 转换定位策略
            by = self.LOCATOR_STRATEGIES[strategy]

            self.logger.debug(f"等待元素可见: {strategy}={value}, 超时={timeout}秒")
            self.set_explicit_wait(timeout).until(
                EC.visibility_of_element_located((by, value))
            )

            self.logger.debug(f"元素已可见: {strategy}={value}")
            return True

        except TimeoutException:
            self.logger.warning(f"元素未在指定时间内可见: {strategy}={value}, 超时={timeout}秒")
            return False
        except Exception as e:
            self.logger.error(f"等待元素可见时发生错误: {strategy}={value}, 错误: {str(e)}")
            return False

    def click_element(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> bool:
        """
        点击元素
        
        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值
            
        Returns:
            点击是否成功
        """
        try:
            element = self.find_element(locator, timeout)

            if element:
                # 确保元素可点击
                if self.wait_for_element_visible(locator, timeout):
                    self.logger.debug(f"点击元素: {locator[0]}={locator[1]}")
                    element.click()
                    return True

            return False

        except Exception as e:
            self.logger.error(f"点击元素时发生错误: {locator[0]}={locator[1]}, 错误: {str(e)}")
            return False

    def send_keys_to_element(self, locator: Tuple[str, str], text: str, timeout: Optional[int] = None) -> bool:
        """
        向元素输入文本
        
        Args:
            locator: 定位器元组 (策略类型, 定位值)
            text: 要输入的文本
            timeout: 超时时间,如果为None则使用默认值
            
        Returns:
            输入是否成功
        """
        try:
            element = self.find_element(locator, timeout)

            if element:
                # 确保元素可见且可交互
                if self.wait_for_element_visible(locator, timeout):
                    self.logger.debug(f"向元素输入文本: {locator[0]}={locator[1]}, 文本='{text}'")
                    element.clear()
                    element.send_keys(text)
                    return True

            return False

        except Exception as e:
            self.logger.error(f"向元素输入文本时发生错误: {locator[0]}={locator[1]}, 错误: {str(e)}")
            return False

    def get_element_text(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> Optional[str]:
        """
        获取元素文本
        
        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值
            
        Returns:
            元素文本,如果未找到元素则返回None
        """
        try:
            element = self.find_element(locator, timeout)

            if element:
                text = element.text
                self.logger.debug(f"获取元素文本: {locator[0]}={locator[1]}, 文本='{text}'")
                return text

            return None

        except Exception as e:
            self.logger.error(f"获取元素文本时发生错误: {locator[0]}={locator[1]}, 错误: {str(e)}")
            return None

    def get_current_activity(self) -> Optional[str]:
        """
        获取当前活动的Activity
        
        Returns:
            当前Activity名称,如果无法获取则返回None
        """
        try:
            activity = self.driver.current_activity
            self.logger.debug(f"当前Activity: {activity}")
            return activity
        except Exception as e:
            self.logger.error(f"获取当前Activity时发生错误: {str(e)}")
            return None

    def get_current_package(self) -> Optional[str]:
        """
        获取当前应用的包名
        
        Returns:
            当前包名,如果无法获取则返回None
        """
        try:
            package = self.driver.current_package
            self.logger.debug(f"当前包名: {package}")
            return package
        except Exception as e:
            self.logger.error(f"获取当前包名时发生错误: {str(e)}")
            return None

    def is_activity_running(self, activity: str, timeout: int = 5) -> bool:
        """
        检查指定的Activity是否正在运行
        
        Args:
            activity: 要检查的Activity名称
            timeout: 等待超时时间
            
        Returns:
            Activity是否正在运行
        """
        end_time = time.time() + timeout

        while time.time() < end_time:
            current_activity = self.get_current_activity()

            if current_activity and activity in current_activity:
                self.logger.debug(f"Activity正在运行: {activity}")
                return True

            time.sleep(0.5)

        self.logger.warning(f"Activity未在指定时间内运行: {activity}")
        return False

    def scroll_down(self, amount: int = 1) -> bool:
        """
        向下滚动页面
        
        Args:
            amount: 滚动次数
            
        Returns:
            滚动是否成功
        """
        try:
            for _ in range(amount):
                # 获取屏幕尺寸
                size = self.driver.get_window_size()

                # 计算起始和结束坐标
                start_x = size['width'] / 2
                start_y = size['height'] * 0.8
                end_x = size['width'] / 2
                end_y = size['height'] * 0.2

                self.logger.debug(f"向下滚动页面: 从({start_x}, {start_y})到({end_x}, {end_y})")

                # 执行滚动操作
                self.driver.swipe(start_x, start_y, end_x, end_y, 1000)
                time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"向下滚动页面时发生错误: {str(e)}")
            return False

    def scroll_up(self, amount: int = 1) -> bool:
        """
        向上滚动页面
        
        Args:
            amount: 滚动次数
            
        Returns:
            滚动是否成功
        """
        try:
            for _ in range(amount):
                # 获取屏幕尺寸
                size = self.driver.get_window_size()

                # 计算起始和结束坐标
                start_x = size['width'] / 2
                start_y = size['height'] * 0.2
                end_x = size['width'] / 2
                end_y = size['height'] * 0.8

                self.logger.debug(f"向上滚动页面: 从({start_x}, {start_y})到({end_x}, {end_y})")

                # 执行滚动操作
                self.driver.swipe(start_x, start_y, end_x, end_y, 1000)
                time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"向上滚动页面时发生错误: {str(e)}")
            return False

    def take_screenshot(self, filename: str = None) -> Optional[str]:
        """
        截图
        
        Args:
            filename: 文件名,如果为None则自动生成
            
        Returns:
            截图保存路径,如果保存失败则返回None
        """
        try:
            if filename is None:
                filename = f"screenshot_{int(time.time())}.png"

            screenshot_path = self.driver.get_screenshot_as_file(filename)
            self.logger.debug(f"截图保存到: {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"截图时发生错误: {str(e)}")
            return None

    def back(self) -> bool:
        """
        执行返回操作
        
        Returns:
            返回操作是否成功
        """
        try:
            self.logger.debug("执行返回操作")
            self.driver.back()
            return True
        except Exception as e:
            self.logger.error(f"执行返回操作时发生错误: {str(e)}")
            return False

    def close_app(self) -> bool:
        """
        关闭应用
        
        Returns:
            关闭是否成功
        """
        try:
            self.logger.debug("关闭应用")
            self.driver.close_app()
            return True
        except Exception as e:
            self.logger.error(f"关闭应用时发生错误: {str(e)}")
            return False

    def launch_app(self) -> bool:
        """
        启动应用
        
        Returns:
            启动是否成功
        """
        try:
            self.logger.debug("启动应用")
            self.driver.launch_app()
            return True
        except Exception as e:
            self.logger.error(f"启动应用时发生错误: {str(e)}")
            return False

    def reset_app(self) -> bool:
        """
        重置应用
        
        Returns:
            重置是否成功
        """
        try:
            self.logger.debug("重置应用")
            self.driver.reset()
            return True
        except Exception as e:
            self.logger.error(f"重置应用时发生错误: {str(e)}")
            return False

    def press_home_button(self) -> bool:
        """
        按下Home键
        
        Returns:
            操作是否成功
        """
        try:
            self.logger.debug("按下Home键")
            self.driver.press_keycode(3)  # Android Home键的keycode是3
            return True
        except Exception as e:
            self.logger.error(f"按下Home键时发生错误: {str(e)}")
            return False

    def is_element_present(self, locator: Tuple[str, str]) -> bool:
        """
        快速检查元素是否存在（不等待）
        
        Args:
            locator: 定位器元组 (策略类型, 定位值)
            
        Returns:
            元素是否存在
        """
        strategy, value = locator

        if strategy not in self.LOCATOR_STRATEGIES:
            return False

        try:
            # 暂时禁用隐式等待
            current_implicit_wait = self.driver.timeouts.implicit_wait
            self.driver.implicitly_wait(0)

            # 转换定位策略
            by = self.LOCATOR_STRATEGIES[strategy]

            # 查找元素
            elements = self.driver.find_elements(by, value)

            # 恢复隐式等待
            self.driver.implicitly_wait(current_implicit_wait)

            return len(elements) > 0

        except Exception as e:
            # 恢复隐式等待
            self.driver.implicitly_wait(self.implicit_wait)
            return False

    def tap_coordinates(self, x: int, y: int, duration: int = 100) -> bool:
        """
        在指定坐标处点击
        
        Args:
            x: X坐标
            y: Y坐标
            duration: 点击持续时间（毫秒）
            
        Returns:
            点击是否成功
        """
        try:
            self.logger.debug(f"点击坐标: ({x}, {y}), 持续时间={duration}毫秒")
            self.driver.tap([(x, y)], duration)
            return True
        except Exception as e:
            self.logger.error(f"点击坐标时发生错误: ({x}, {y}), 错误: {str(e)}")
            return False


# 常用的元素定位策略别名,方便使用
class ElementLocator:
    """
    元素定位器工具类
    提供常用的元素定位方法
    """

    @staticmethod
    def id(value: str) -> Tuple[str, str]:
        return ("id", value)

    @staticmethod
    def xpath(value: str) -> Tuple[str, str]:
        return ("xpath", value)

    @staticmethod
    def class_name(value: str) -> Tuple[str, str]:
        return ("class_name", value)

    @staticmethod
    def accessibility_id(value: str) -> Tuple[str, str]:
        return ("accessibility_id", value)

    @staticmethod
    def android_uiautomator(value: str) -> Tuple[str, str]:
        return ("android_uiautomator", value)

    @staticmethod
    def ios_uiautomation(value: str) -> Tuple[str, str]:
        return ("ios_uiautomation", value)

    @staticmethod
    def name(value: str) -> Tuple[str, str]:
        return ("name", value)
