"""
-------------------------------------------------
File:           app_base_page.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
App自动化基础页面类,实现POM模式的页面基类功能,提供元素定位、操作和等待等通用方法
-------------------------------------------------
"""
import time
from typing import Optional, List, Any, Tuple

from appium.webdriver.webdriver import WebDriver as AppiumDriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotVisibleException,
    ElementNotInteractableException,
    ElementNotSelectableException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.config_manager import config
from utils.common_util import util
from utils.decorator_util import retry, wait_after_with_jitter
from utils.logger_util import logger
from utils.screenshot_util import ScreenshotUtils

# 定义MobileBy作为By的别名,保持兼容性
MobileBy = By


class AppBasePage:
    """
    APP自动化页面基类
    所有APP页面类都应该继承此类
    """

    # 元素定位策略映射
    LOCATOR_STRATEGIES = {
        "id": By.ID,
        "xpath": By.XPATH,
        "class_name": By.CLASS_NAME,
        "accessibility_id": "accessibility id",
        "android_uiautomator": "-android uiautomator",
        "ios_uiautomation": "-ios uiautomation",
        "name": By.NAME,
        "tag_name": By.TAG_NAME,
        "link_text": By.LINK_TEXT,
        "partial_link_text": By.PARTIAL_LINK_TEXT
    }

    def __init__(self, driver: AppiumDriver, screenshot_dir: Optional[str] = None, test_data: Optional[dict] = None):
        """
        初始化页面类

        Args:
            driver: Appium驱动实例
            screenshot_dir: 截图保存目录
            test_data: 测试数据字典
        """
        self.driver = driver
        self.utils = util
        self.screenshot_utils = ScreenshotUtils()
        # 测试数据
        self.test_data = test_data or {}
        # 配置
        self.default_timeout = getattr(config, "DEFAULT_TIMEOUT", 5)
        self.implicit_wait = getattr(config, "IMPLICIT_WAIT", 10)
        self.explicit_wait = getattr(config, "EXPLICIT_WAIT", 20)
        self.polling_interval = getattr(config, "POLLING_INTERVAL", 0.5)
        self.screenshot_dir = screenshot_dir

        # 设置隐式等待
        self.set_implicit_wait(self.implicit_wait)

        logger.info(f"初始化 {self.__class__.__name__}")

    def get_test_scenario(self, scenario_name: str) -> dict:
        """
        根据场景名称获取测试数据

        Args:
            scenario_name: 场景名称

        Returns:
            dict: 测试场景数据
        """
        for scenario in self.test_data.get("test_scenarios", []):
            if scenario.get("name") == scenario_name:
                return scenario
        return {}

    def get_test_data(self, scenario_name: str) -> dict:
        """
        获取测试数据

        Args:
            scenario_name: 场景名称

        Returns:
            dict: 测试数据
        """
        scenario = self.get_test_scenario(scenario_name)
        return scenario.get("test_data", {})

    def get_expected_result(self, scenario_name: str) -> dict:
        """
        获取预期结果

        Args:
            scenario_name: 场景名称

        Returns:
            dict: 预期结果
        """
        scenario = self.get_test_scenario(scenario_name)
        return scenario.get("expected", {})

    def set_implicit_wait(self, timeout: int = 10) -> None:
        """
        设置隐式等待时间

        Args:
            timeout: 等待超时时间（秒）
        """
        self.driver.implicitly_wait(timeout)
        logger.debug(f"设置隐式等待时间: {timeout}秒")

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

    # 元素定位相关方法
    def find_element(self, by: str, value: str, timeout: Optional[int] = None) -> Any:
        """
        查找单个元素

        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）,默认使用配置文件中的值

        Returns:
            Any: 找到的元素
        """
        timeout = timeout or self.default_timeout
        logger.info(f"查找元素: {by}={value}, 超时时间: {timeout}秒")

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"成功找到元素: {by}={value}")
            return element
        except TimeoutException:
            logger.error(f"超时: 未找到元素 {by}={value}")
            # 失败时截图
            self.screenshot_utils.capture_screenshot(
                driver = self.driver,
                name = f"element_not_found_{self.utils.get_timestamp()}"
            )
            raise NoSuchElementException(f"未找到元素: {by}={value}")
        except Exception as e:
            logger.error(f"查找元素时发生错误: {str(e)}")
            raise

    def find_elements(self, by: str, value: str, timeout: Optional[int] = None) -> List[Any]:
        """
        查找多个元素

        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）,默认使用配置文件中的值

        Returns:
            List[Any]: 找到的元素列表
        """
        timeout = timeout or self.default_timeout
        logger.info(f"查找多个元素: {by}={value}, 超时时间: {timeout}秒")

        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            logger.debug(f"成功找到 {len(elements)} 个元素: {by}={value}")
            return elements
        except TimeoutException:
            logger.warning(f"超时: 未找到元素 {by}={value},返回空列表")
            return []
        except Exception as e:
            logger.error(f"查找多个元素时发生错误: {str(e)}")
            return []

    def find_element_by_locator(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> Optional[Any]:
        """
        通过定位器元组查找单个元素

        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值

        Returns:
            找到的元素对象,如果未找到则返回None
        """
        strategy, value = locator

        if strategy not in self.LOCATOR_STRATEGIES:
            logger.error(f"无效的定位策略: {strategy}")
            return None

        try:
            if timeout is None:
                timeout = self.explicit_wait

            # 转换定位策略
            by = self.LOCATOR_STRATEGIES[strategy]

            logger.debug(f"查找元素: {strategy}={value}, 超时={timeout}秒")
            element = self.set_explicit_wait(timeout).until(
                EC.presence_of_element_located((by, value))
            )

            logger.debug(f"成功找到元素: {strategy}={value}")
            return element

        except TimeoutException:
            logger.warning(f"未找到元素: {strategy}={value}, 超时={timeout}秒")
            return None
        except Exception as e:
            logger.error(f"查找元素时发生错误: {strategy}={value}, 错误: {str(e)}")
            return None

    def find_elements_by_locator(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> list:
        """
        通过定位器元组查找多个元素

        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值

        Returns:
            元素对象列表,如果未找到则返回空列表
        """
        strategy, value = locator

        if strategy not in self.LOCATOR_STRATEGIES:
            logger.error(f"无效的定位策略: {strategy}")
            return []

        try:
            if timeout is None:
                timeout = self.explicit_wait

            # 转换定位策略
            by = self.LOCATOR_STRATEGIES[strategy]

            logger.debug(f"查找多个元素: {strategy}={value}, 超时={timeout}秒")
            elements = self.set_explicit_wait(timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )

            logger.debug(f"找到 {len(elements)} 个元素: {strategy}={value}")
            return elements

        except TimeoutException:
            logger.warning(f"未找到元素: {strategy}={value}, 超时={timeout}秒")
            return []
        except Exception as e:
            logger.error(f"查找元素时发生错误: {strategy}={value}, 错误: {str(e)}")
            return []

    def find_element_by_id(self, id_value: str, timeout: Optional[int] = None) -> Any:
        """
        通过ID查找元素

        Args:
            id_value: 元素ID
            timeout: 超时时间（秒）

        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.ID, id_value, timeout)

    def find_element_by_xpath(self, xpath: str, timeout: Optional[int] = None) -> Any:
        """
        通过XPath查找元素

        Args:
            xpath: XPath表达式
            timeout: 超时时间（秒）

        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.XPATH, xpath, timeout)

    def find_element_by_android_uiautomator(self, uiautomator: str, timeout: Optional[int] = None) -> Any:
        """
        通过Android UiAutomator查找元素

        Args:
            uiautomator: UiAutomator表达式
            timeout: 超时时间（秒）

        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.ANDROID_UIAUTOMATOR, uiautomator, timeout)

    def find_element_by_ios_predicate(self, predicate: str, timeout: Optional[int] = None) -> Any:
        """
        通过iOS Predicate查找元素

        Args:
            predicate: Predicate表达式
            timeout: 超时时间（秒）

        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.IOS_PREDICATE, predicate, timeout)

    def find_element_by_accessibility_id(self, accessibility_id: str, timeout: Optional[int] = None) -> Any:
        """
        通过Accessibility ID查找元素

        Args:
            accessibility_id: Accessibility ID
            timeout: 超时时间（秒）

        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.ACCESSIBILITY_ID, accessibility_id, timeout)

    # 元素操作相关方法
    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def click(self, element: Any, description: Optional[str] = None) -> None:
        """
        点击元素

        Args:
            element: 要点击的元素
            description: 元素描述（用于日志）
        """
        desc = description or "元素"
        logger.info(f"点击 {desc}")

        try:
            # 确保元素可见
            WebDriverWait(self.driver, self.default_timeout).until(
                EC.element_to_be_clickable(element)
            )

            # 点击元素
            element.click()
            logger.debug(f"成功点击 {desc}")

            # 点击后检查502错误弹窗
            self.check_and_terminate_on_502_error()
        except (ElementNotVisibleException, ElementNotInteractableException):
            logger.error(f"无法点击 {desc}: 元素不可见或不可交互")
            # 尝试滚动到元素并点击
            self.scroll_to_element(element)
            element.click()
            logger.debug(f"滚动后成功点击 {desc}")

            # 点击后检查502错误弹窗
            self.check_and_terminate_on_502_error()
        except Exception as e:
            logger.error(f"点击 {desc} 时发生错误: {str(e)}")
            # 失败时截图
            self.screenshot_utils.capture_screenshot(
                driver = self.driver,
                name = f"click_failed_{self.utils.get_timestamp()}"
            )
            raise

    def click_element(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> bool:
        """
        通过定位器点击元素

        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间,如果为None则使用默认值

        Returns:
            点击是否成功
        """
        try:
            element = self.find_element_by_locator(locator, timeout)

            if element:
                # 确保元素可点击
                if self.wait_for_element_visible(locator, timeout):
                    logger.debug(f"点击元素: {locator[0]}={locator[1]}")
                    element.click()
                    # 点击后检查502错误弹窗
                    self.check_and_terminate_on_502_error()
                    return True

            return False

        except Exception as e:
            logger.error(f"点击元素时发生错误: {locator[0]}={locator[1]}, 错误: {str(e)}")
            return False

    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def input_text(self, element: Any, text: str, description: Optional[str] = None,
                   clear_first: bool = True) -> None:
        """
        在输入框中输入文本

        Args:
            element: 输入框元素
            text: 要输入的文本
            description: 元素描述（用于日志）
            clear_first: 是否先清空输入框
        """
        desc = description or "输入框"
        logger.info(f"在 {desc} 中输入文本: {'***' if self._is_sensitive_info(text) else text}")

        try:
            # 确保元素可见且可交互
            WebDriverWait(self.driver, self.default_timeout).until(
                EC.visibility_of(element)
            )

            # 清空输入框
            if clear_first:
                element.clear()
                # 有时候clear()不能完全清空,再点击一次
                element.click()
                # 对于Android,可以使用keyevent
                if self.driver.capabilities['platformName'].lower() == 'android':
                    self.driver.keyevent(123)  # END键
                    self.driver.keyevent(67)  # DEL键,多按几次确保清空

            # 输入文本
            element.send_keys(text)
            logger.debug(f"成功在 {desc} 中输入文本")

            # 输入后检查502错误弹窗
            self.check_and_terminate_on_502_error()
        except Exception as e:
            logger.error(f"在 {desc} 中输入文本时发生错误: {str(e)}")
            # 失败时截图
            self.screenshot_utils.capture_screenshot(
                driver = self.driver,
                name = f"input_failed_{self.utils.get_timestamp()}"
            )
            raise

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
            element = self.find_element_by_locator(locator, timeout)

            if element:
                # 确保元素可见且可交互
                if self.wait_for_element_visible(locator, timeout):
                    logger.debug(f"向元素输入文本: {locator[0]}={locator[1]}, 文本='{text}'")
                    element.clear()
                    element.send_keys(text)
                    return True

            return False

        except Exception as e:
            logger.error(f"向元素输入文本时发生错误: {locator[0]}={locator[1]}, 错误: {str(e)}")
            return False

    @staticmethod
    def get_text(element: Any, description: Optional[str] = None) -> str:
        """
        获取元素文本

        Args:
            element: 元素
            description: 元素描述（用于日志）

        Returns:
            str: 元素文本
        """
        desc = description or "元素"
        logger.info(f"获取 {desc} 的文本")

        try:
            text = element.text
            logger.debug(f"成功获取 {desc} 的文本: {text}")
            return text
        except Exception as e:
            logger.error(f"获取 {desc} 的文本时发生错误: {str(e)}")
            raise

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
            element = self.find_element_by_locator(locator, timeout)

            if element:
                text = element.text
                logger.debug(f"获取元素文本: {locator[0]}={locator[1]}, 文本='{text}'")
                return text

            return None

        except Exception as e:
            logger.error(f"获取元素文本时发生错误: {locator[0]}={locator[1]}, 错误: {str(e)}")
            return None

    def is_element_displayed(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> bool:
        """
        检查元素是否可见

        Args:
            locator: 定位器元组 (策略类型, 定位值)
            timeout: 超时时间（秒）

        Returns:
            bool: 元素是否可见
        """
        strategy, value = locator

        if strategy not in self.LOCATOR_STRATEGIES:
            logger.error(f"无效的定位策略: {strategy}")
            return False

        timeout = timeout or self.default_timeout
        logger.info(f"检查元素是否可见: {strategy}={value}")

        try:
            by = self.LOCATOR_STRATEGIES[strategy]
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            logger.debug(f"元素 {strategy}={value} 可见")
            return True
        except (TimeoutException, NoSuchElementException):
            logger.debug(f"元素 {strategy}={value} 不可见或不存在")
            return False

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
            logger.error(f"无效的定位策略: {strategy}")
            return False

        try:
            if timeout is None:
                timeout = self.explicit_wait

            # 转换定位策略
            by = self.LOCATOR_STRATEGIES[strategy]

            logger.debug(f"等待元素可见: {strategy}={value}, 超时={timeout}秒")
            self.set_explicit_wait(timeout).until(
                EC.visibility_of_element_located((by, value))
            )

            logger.debug(f"元素已可见: {strategy}={value}")
            return True

        except TimeoutException:
            logger.warning(f"元素未在指定时间内可见: {strategy}={value}, 超时={timeout}秒")
            return False
        except Exception as e:
            logger.error(f"等待元素可见时发生错误: {strategy}={value}, 错误: {str(e)}")
            return False

    @staticmethod
    def is_element_enabled(element: Any, description: Optional[str] = None) -> bool:
        """
        检查元素是否可用

        Args:
            element: 元素
            description: 元素描述（用于日志）

        Returns:
            bool: 元素是否可用
        """
        desc = description or "元素"
        logger.info(f"检查 {desc} 是否可用")

        try:
            enabled = element.is_enabled()
            logger.debug(f"{desc} {'可用' if enabled else '不可用'}")
            return enabled
        except Exception as e:
            logger.error(f"检查 {desc} 是否可用时发生错误: {str(e)}")
            raise

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

    # 页面操作相关方法
    def scroll_to_element(self, element: Any, max_swipes: int = 5) -> None:
        """
        滚动到元素可见

        Args:
            element: 目标元素
            max_swipes: 最大滑动次数
        """
        logger.info("滚动到元素可见")

        for _ in range(max_swipes):
            try:
                if element.is_displayed():
                    logger.debug("元素已可见")
                    return

                # 根据平台执行滚动
                if self.driver.capabilities['platformName'].lower() == 'android':
                    self.driver.swipe(500, 1500, 500, 1000, 800)  # 向上滑动
                else:  # iOS
                    self.driver.execute_script("mobile: scroll", {
                        'direction': 'down'
                    })

                time.sleep(0.5)
            except Exception as e:
                logger.error(f"滚动时发生错误: {str(e)}")

        logger.warning(f"达到最大滚动次数 {max_swipes},元素可能仍然不可见")

    def scroll_down(self, percentage: int = 80) -> None:
        """
        向下滚动页面

        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("down", percentage)

    def scroll_up(self, percentage: int = 80) -> None:
        """
        向上滚动页面

        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("up", percentage)

    def scroll_left(self, percentage: int = 80) -> None:
        """
        向左滚动页面

        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("left", percentage)

    def scroll_right(self, percentage: int = 80) -> None:
        """
        向右滚动页面

        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("right", percentage)

    def _swipe(self, direction: str, percentage: int = 80) -> None:
        """
        滑动页面

        Args:
            direction: 滑动方向（up, down, left, right）
            percentage: 滚动距离百分比（0-100）
        """
        logger.info(f"{direction} 滑动页面 {percentage}%")

        # 获取屏幕尺寸
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = size['height'] // 2

        # 计算滑动距离
        swipe_percentage = percentage / 100

        # 根据方向设置终点坐标
        if direction == "up":
            end_y = int(start_y * (1 - swipe_percentage))
            self.driver.swipe(start_x, start_y, start_x, end_y, 800)
        elif direction == "down":
            end_y = int(start_y * (1 + swipe_percentage))
            self.driver.swipe(start_x, start_y, start_x, end_y, 800)
        elif direction == "left":
            end_x = int(start_x * (1 - swipe_percentage))
            self.driver.swipe(start_x, start_y, end_x, start_y, 800)
        elif direction == "right":
            end_x = int(start_x * (1 + swipe_percentage))
            self.driver.swipe(start_x, start_y, end_x, start_y, 800)
        else:
            raise ValueError(f"无效的滑动方向: {direction}")

        time.sleep(0.5)  # 等待滑动完成

    def get_current_activity(self) -> str:
        """
        获取当前活动（Android）或页面（iOS）

        Returns:
            str: 当前活动名称
        """
        platform = self.driver.capabilities['platformName'].lower()

        if platform == 'android':
            activity = self.driver.current_activity
            logger.info(f"当前Android活动: {activity}")
            return activity
        else:  # iOS
            context = self.driver.current_context
            logger.info(f"当前iOS上下文: {context}")
            return context

    def get_current_package(self) -> Optional[str]:
        """
        获取当前应用的包名

        Returns:
            当前包名,如果无法获取则返回None
        """
        try:
            if self.driver.capabilities['platformName'].lower() == 'android':
                package = self.driver.current_package
                logger.debug(f"当前包名: {package}")
                return package
            else:
                logger.warning("get_current_package() 方法仅适用于Android平台")
                return ""
        except Exception as e:
            logger.error(f"获取当前包名时发生错误: {str(e)}")
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
                logger.debug(f"Activity正在运行: {activity}")
                return True

            time.sleep(0.5)

        logger.warning(f"Activity未在指定时间内运行: {activity}")
        return False

    def press_back(self) -> None:
        """
        按返回键
        """
        logger.info("按返回键")
        self.driver.back()

    def back(self) -> bool:
        """
        执行返回操作

        Returns:
            返回操作是否成功
        """
        try:
            logger.debug("执行返回操作")
            self.driver.back()
            return True
        except Exception as e:
            logger.error(f"执行返回操作时发生错误: {str(e)}")
            return False

    def press_home(self) -> None:
        """
        按Home键
        """
        logger.info("按Home键")
        self.driver.press_keycode(3) if self.driver.capabilities['platformName'].lower() == 'android' else \
            self.driver.execute_script("mobile: pressButton", {"name": "home"})

    def press_home_button(self) -> bool:
        """
        按下Home键

        Returns:
            操作是否成功
        """
        try:
            logger.debug("按下Home键")
            self.driver.press_keycode(3)  # Android Home键的keycode是3
            return True
        except Exception as e:
            logger.error(f"按下Home键时发生错误: {str(e)}")
            return False

    def press_menu(self) -> None:
        """
        按菜单键
        """
        logger.info("按菜单键")
        self.driver.press_keycode(82) if self.driver.capabilities['platformName'].lower() == 'android' else \
            self.driver.execute_script("mobile: pressButton", {"name": "menu"})

    def hide_keyboard(self, key_name: Optional[str] = None) -> None:
        """
        隐藏键盘

        Args:
            key_name: 用于关闭键盘的键名（如"Done"）
        """
        logger.info("隐藏键盘")

        try:
            if key_name:
                self.driver.hide_keyboard(key_name = key_name)
            else:
                self.driver.hide_keyboard()
        except Exception as e:
            logger.warning(f"隐藏键盘时发生错误（可能键盘已隐藏）: {str(e)}")

    def tap_screen(self, x: int, y: int, duration: Optional[int] = None) -> None:
        """
        点击屏幕指定坐标

        Args:
            x: X坐标
            y: Y坐标
            duration: 点击持续时间（毫秒）
        """
        logger.info(f"点击屏幕坐标: ({x}, {y})")

        if duration:
            self.driver.tap([(x, y)], duration)
        else:
            self.driver.tap([(x, y)])

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
            logger.debug(f"点击坐标: ({x}, {y}), 持续时间={duration}毫秒")
            self.driver.tap([(x, y)], duration)
            return True
        except Exception as e:
            logger.error(f"点击坐标时发生错误: ({x}, {y}), 错误: {str(e)}")
            return False

    # 等待相关方法
    def wait_for_activity(self, activity: str, timeout: int = 10) -> bool:
        """
        等待活动启动

        Args:
            activity: 要等待的活动名称
            timeout: 超时时间（秒）

        Returns:
            bool: 是否在超时时间内启动
        """
        logger.info(f"等待活动启动: {activity}, 超时时间: {timeout}秒")

        if self.driver.capabilities['platformName'].lower() == 'android':
            result = self.driver.wait_activity(activity, timeout)
            logger.debug(f"活动启动等待结果: {'成功' if result else '失败'}")
            return result
        else:
            logger.warning("wait_for_activity() 方法仅适用于Android平台")
            return False

    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def wait_for_element(self, by: str, value: str, timeout: Optional[int] = None) -> bool:
        """
        等待元素出现

        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）

        Returns:
            bool: 是否在超时时间内出现
        """
        timeout = timeout or self.default_timeout
        logger.info(f"等待元素出现: {by}={value}, 超时时间: {timeout}秒")

        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"元素 {by}={value} 已出现")
            return True
        except TimeoutException:
            logger.debug(f"超时: 元素 {by}={value} 未出现")
            return False

    def wait_for_element_disappear(self, by: str, value: str, timeout: Optional[int] = None) -> bool:
        """
        等待元素消失

        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）

        Returns:
            bool: 是否在超时时间内消失
        """
        timeout = timeout or self.default_timeout
        logger.info(f"等待元素消失: {by}={value}, 超时时间: {timeout}秒")

        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((by, value))
            )
            logger.debug(f"元素 {by}={value} 已消失")
            return True
        except TimeoutException:
            logger.debug(f"超时: 元素 {by}={value} 未消失")
            return False

    # 应用操作相关方法
    def close_app(self) -> bool:
        """
        关闭应用

        Returns:
            关闭是否成功
        """
        try:
            logger.debug("关闭应用")
            self.driver.close_app()
            return True
        except Exception as e:
            logger.error(f"关闭应用时发生错误: {str(e)}")
            return False

    def launch_app(self) -> bool:
        """
        启动应用

        Returns:
            启动是否成功
        """
        try:
            logger.debug("启动应用")
            self.driver.launch_app()
            return True
        except Exception as e:
            logger.error(f"启动应用时发生错误: {str(e)}")
            return False

    def reset_app(self) -> bool:
        """
        重置应用

        Returns:
            重置是否成功
        """
        try:
            logger.debug("重置应用")
            self.driver.reset()
            return True
        except Exception as e:
            logger.error(f"重置应用时发生错误: {str(e)}")
            return False

    def terminate_app(self, app_id: str) -> bool:
        """
        终止应用

        Args:
            app_id: 应用ID（包名或Bundle ID）

        Returns:
            bool: 是否成功终止
        """
        logger.info(f"终止应用: {app_id}")
        result = self.driver.terminate_app(app_id)
        logger.debug(f"应用终止结果: {'成功' if result else '失败'}")
        return result

    def activate_app(self, app_id: str) -> bool:
        """
        激活应用

        Args:
            app_id: 应用ID（包名或Bundle ID）

        Returns:
            bool: 是否成功激活
        """
        logger.info(f"激活应用: {app_id}")
        result = self.driver.activate_app(app_id)
        logger.debug(f"应用激活结果: {'成功' if result else '失败'}")
        return result

    def is_app_installed(self, app_id: str) -> bool:
        """
        检查应用是否已安装

        Args:
            app_id: 应用ID（包名或Bundle ID）

        Returns:
            bool: 是否已安装
        """
        logger.info(f"检查应用是否已安装: {app_id}")
        result = self.driver.is_app_installed(app_id)
        logger.debug(f"应用安装状态: {'已安装' if result else '未安装'}")
        return result

    def install_app(self, app_path: str) -> None:
        """
        安装应用

        Args:
            app_path: 应用安装包路径
        """
        logger.info(f"安装应用: {app_path}")
        self.driver.install_app(app_path)

    def remove_app(self, app_id: str) -> None:
        """
        卸载应用

        Args:
            app_id: 应用ID（包名或Bundle ID）
        """
        logger.info(f"卸载应用: {app_id}")
        self.driver.remove_app(app_id)

    # 辅助方法
    def _is_sensitive_info(self, text: str) -> bool:
        """
        检查文本是否包含敏感信息（如密码）

        Args:
            text: 要检查的文本

        Returns:
            bool: 是否包含敏感信息
        """
        sensitive_patterns = ['password', 'pwd', 'token', 'secret', 'key']
        # 检查参数名或描述中是否包含敏感词
        caller_frame = self.utils.get_caller_info()
        caller_args = caller_frame.f_locals if caller_frame else {}

        for arg_name, arg_value in caller_args.items():
            if any(pattern in arg_name.lower() for pattern in sensitive_patterns):
                return True

        return False

    def capture_screenshot(self, filename: Optional[str] = None) -> str:
        """
        截取当前屏幕

        Args:
            filename: 截图文件名（不含路径和扩展名）

        Returns:
            str: 截图文件路径
        """
        return self.screenshot_utils.capture_screenshot(
            driver = self.driver,
            name = filename or f"app_screenshot_{self.utils.get_timestamp()}"
        )

    def take_screenshot(self, filename: str = None, description: str = "") -> Optional[str]:
        """
        截图

        Args:
            filename: 文件名,如果为None则自动生成
            description: 截图描述

        Returns:
            截图保存路径,如果保存失败则返回None
        """
        try:
            import os
            from datetime import datetime

            # 生成截图名称
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                filename = f"screenshot_{timestamp}"

            # 确保名称不包含扩展名
            if not filename.endswith('.png'):
                filename = f"{filename}.png"
            from utils.path_util import path_util
            project_root = path_util.get_project_root()
            # 确定截图保存路径
            if self.screenshot_dir:
                if self.screenshot_dir.startswith('/'):
                    screenshot_dir = os.path.join(project_root, self.screenshot_dir.lstrip('/'))
                    # 如果是相对路径, 也基于项目根目录
                else:
                    screenshot_dir = os.path.join(project_root, self.screenshot_dir)

            else:
                # 从项目配置获取截图保存路径
                screenshot_dir = config.SCREENSHOT_DIR

                # 如果配置中没有设置, 使用默认路径
                if not screenshot_dir:
                    screenshot_dir = os.path.join(project_root, "reports", "screenshots", "app")

            # 确保目录存在
            os.makedirs(screenshot_dir, exist_ok = True)

            # 生成截图路径
            screenshot_path = os.path.join(screenshot_dir, filename)

            # 执行截图
            success = self.driver.save_screenshot(screenshot_path)

            if success:
                logger.info(f"截图成功: {screenshot_path}")
                if description:
                    logger.info(f"截图描述: {description}")
                return screenshot_path
            else:
                logger.error("截图失败")
                return None

        except Exception as e:
            logger.error(f"截图时发生错误: {str(e)}")
            return None

    def check_for_toast(self, message, timeout = 10, interval = 0.02):
        """
        检测是否出现指定的Toast消息或自定义提示框
        
        Args:
            message: 要检测的Toast消息
            timeout: 超时时间（秒）
            interval: 检测间隔（秒）
            
        Returns:
            bool: 是否检测到指定的Toast或提示框
        """
        logger.info(f"检测Toast消息: {message}, 超时时间: {timeout}秒")
        import time
        start_time = time.time()

        # 增加初始延迟, 等待Toast出现
        time.sleep(0.5)

        # 循环检测
        while time.time() - start_time < timeout:
            try:
                # 方法1: 检查应用的日志输出（最有效的方法）
                try:
                    logs = self.driver.get_log('logcat')
                    for log in logs:
                        if message in log['message']:
                            logger.info(f"在日志中检测到Toast消息: {message}")
                            return True
                except Exception as e:
                    logger.debug(f"检查日志时发生错误: {str(e)}")

                # 方法2: 使用UiAutomator查找包含指定文本的元素
                try:
                    ui_query = f'new UiSelector().textContains("{message}")'
                    elements = self.driver.find_elements("android_uiautomator", ui_query)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"成功检测到包含指定文本的元素: {element.text}")
                            return True
                except Exception as e:
                    logger.debug(f"查找文本元素时发生错误: {str(e)}")

                # 方法3: 使用精确文本匹配查找元素
                try:
                    ui_query = f'new UiSelector().text("{message}")'
                    elements = self.driver.find_elements("android_uiautomator", ui_query)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"成功检测到精确匹配的元素: {element.text}")
                            return True
                except Exception as e:
                    logger.debug(f"匹配文本元素时发生错误: {str(e)}")

                # 短暂等待后继续检测
                time.sleep(interval)
            except Exception as e:
                logger.debug(f"检测Toast时发生错误: {str(e)}")
                time.sleep(interval)

        logger.warning(f"在{timeout}秒内未检测到Toast消息或提示框: {message}")
        return False

    def check_for_502_error(self) -> bool:
        """
        检测是否出现502错误弹窗
        
        Returns:
            bool: 是否检测到502错误弹窗
        """
        logger.info("检测502错误弹窗")

        # 502错误弹窗的元素定位
        error_message_locator = ("id", "com.weixiao.voice:id/tv_dialog_msg")

        try:
            # 快速检查元素是否存在（不等待）
            if self.is_element_present(error_message_locator):
                # 获取错误信息文本
                error_text = self.get_element_text(error_message_locator, timeout = 2)
                if error_text and ("502" in error_text or "Bad Gateway" in error_text or "服务器走神" in error_text):
                    logger.error(f"检测到502错误弹窗: {error_text}")
                    # 截图保存证据
                    self.take_screenshot("502_error_popup", "502错误弹窗")
                    return True
        except Exception as e:
            logger.debug(f"检测502错误弹窗时发生错误: {str(e)}")

        return False

    def check_and_terminate_on_502_error(self) -> None:
        """
        检查是否出现502错误弹窗, 如果出现则终止测试
        
        Raises:
            Exception: 当检测到502错误弹窗时抛出异常
        """
        if self.check_for_502_error():
            raise Exception("检测到502错误弹窗, 终止测试")

    @wait_after_with_jitter(1, 0.2)
    def launch_app_by_icon(self, app_name: str = "花选") -> bool:
        """
        模拟手动点击app图标启动应用

        Args:
            app_name: 应用图标名称

        Returns:
            是否启动成功
        """
        logger.info(f"模拟手动点击app图标启动应用: {app_name}")

        try:
            # # 按Home键返回主屏幕
            # self.press_home()
            # time.sleep(2)

            # 使用UiAutomator查找应用图标并点击
            logger.info(f"查找应用图标: {app_name}")
            # 构建UiAutomator表达式
            uiautomator_expr = f'new UiSelector().text("{app_name}")'
            # 查找并点击图标
            if self.click_element(("android_uiautomator", uiautomator_expr), timeout = 10):
                logger.info(f"成功点击应用图标: {app_name}")
                # 等待应用启动
                time.sleep(1)
                return True
            else:
                logger.error(f"未找到应用图标: {app_name}")
                return False

        except Exception as e:
            logger.error(f"启动应用时发生错误: {str(e)}")
            return False


# 常用的元素定位策略别名,方便使用
class ElementLocator:
    """
    元素定位器工具类
    提供常用的元素定位方法
    """

    @staticmethod
    def id(value: str) -> Tuple[str, str]:
        return "id", value

    @staticmethod
    def xpath(value: str) -> Tuple[str, str]:
        return "xpath", value

    @staticmethod
    def class_name(value: str) -> Tuple[str, str]:
        return "class_name", value

    @staticmethod
    def accessibility_id(value: str) -> Tuple[str, str]:
        return "accessibility_id", value

    @staticmethod
    def android_uiautomator(value: str) -> Tuple[str, str]:
        return "android_uiautomator", value

    @staticmethod
    def ios_uiautomation(value: str) -> Tuple[str, str]:
        return "ios_uiautomation", value

    @staticmethod
    def name(value: str) -> Tuple[str, str]:
        return "name", value