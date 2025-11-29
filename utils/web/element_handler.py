"""
-------------------------------------------------
File:           element_handler.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
Web自动化元素操作处理器,封装Selenium的元素定位和操作方法,支持各种元素交互和异常处理
-------------------------------------------------
"""
from typing import Optional, List, Tuple, Union

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotVisibleException,
    ElementNotInteractableException,
    TimeoutException,
    StaleElementReferenceException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.decorator_util import retry, timing
from utils.logger_util import logger
from utils.screenshot_util import ScreenshotUtils


# 导入移至函数内部避免循环依赖


class ElementHandler:
    """
    元素操作处理器类
    """

    def __init__(self, driver: webdriver, timeout: Optional[int] = None):
        """
        初始化元素处理器
        
        Args:
            driver: Selenium WebDriver实例
            timeout: 超时时间（秒）,默认为配置文件中的DEFAULT_TIMEOUT
        """
        self.driver = driver
        # 延迟导入获取配置值
        default_timeout = 30
        if timeout is None:
            try:
                from config import config
                default_timeout = config.DEFAULT_TIMEOUT
            except ImportError:
                logger.warning("无法导入config模块，使用默认超时时间")
        self.timeout = timeout or default_timeout
        self.wait = WebDriverWait(
            driver = self.driver,
            timeout = self.timeout,
            poll_frequency = 0.5,
            ignored_exceptions = [
                NoSuchElementException,
                StaleElementReferenceException
            ]
        )

    def _get_locator_type(self, locator: str) -> Tuple[str, str]:
        """
        解析定位器字符串
        
        Args:
            locator: 定位器字符串,格式如 "id=login_button", "xpath=//div[@class='header']"
            
        Returns:
            Tuple[str, str]: (定位器类型, 定位器值)
        """
        try:
            locator_type, locator_value = locator.split("=", 1)
            return locator_type.lower(), locator_value
        except ValueError:
            logger.error(f"无效的定位器格式: {locator},格式应为 'type=value'")
            raise ValueError(f"无效的定位器格式: {locator}")

    def _get_by_method(self, locator_type: str) -> By:
        """
        根据定位器类型返回By对象
        
        Args:
            locator_type: 定位器类型字符串
            
        Returns:
            By: By对象
        """
        by_methods = {
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'class_name': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'tag_name': By.TAG_NAME,
            'link': By.LINK_TEXT,
            'link_text': By.LINK_TEXT,
            'partial_link': By.PARTIAL_LINK_TEXT,
            'partial_link_text': By.PARTIAL_LINK_TEXT,
            'css': By.CSS_SELECTOR,
            'css_selector': By.CSS_SELECTOR,
            'xpath': By.XPATH
        }

        if locator_type not in by_methods:
            logger.error(f"不支持的定位器类型: {locator_type}")
            raise ValueError(f"不支持的定位器类型: {locator_type}")

        return by_methods[locator_type]

    def _get_by_and_value(self, locator: Union[str, Tuple[str, str]]) -> Tuple[By, str]:
        """
        获取By对象和定位器值
        
        Args:
            locator: 定位器,可以是字符串("id=login")或元组(By.ID, "login")
            
        Returns:
            Tuple[By, str]: (By对象, 定位器值)
        """
        if isinstance(locator, str):
            locator_type, locator_value = self._get_locator_type(locator)
            by_method = self._get_by_method(locator_type)
            return by_method, locator_value
        elif isinstance(locator, tuple) and len(locator) == 2:
            return locator
        else:
            logger.error(f"无效的定位器: {locator}")
            raise ValueError(f"无效的定位器格式: {locator}")

    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def find_element(self, locator: Union[str, Tuple[str, str]]) -> WebElement:
        """
        查找单个元素
        
        Args:
            locator: 定位器
            
        Returns:
            WebElement: 找到的元素
        """
        by, value = self._get_by_and_value(locator)
        element = self.driver.find_element(by, value)
        logger.info(f"找到元素: {by}={value}")
        return element

    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def find_elements(self, locator: Union[str, Tuple[str, str]]) -> List[WebElement]:
        """
        查找多个元素
        
        Args:
            locator: 定位器
            
        Returns:
            List[WebElement]: 找到的元素列表
        """
        by, value = self._get_by_and_value(locator)
        elements = self.driver.find_elements(by, value)
        logger.info(f"找到 {len(elements)} 个元素: {by}={value}")
        return elements

    def wait_for_element_present(self, locator: Union[str, Tuple[str, str]]) -> WebElement:
        """
        等待元素出现
        
        Args:
            locator: 定位器
            
        Returns:
            WebElement: 找到的元素
        """
        by, value = self._get_by_and_value(locator)
        try:
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            logger.info(f"元素已出现: {by}={value}")
            return element
        except TimeoutException:
            logger.error(f"超时: 元素未出现 - {by}={value}")
            # 创建ScreenshotUtils实例并调用方法
            ScreenshotUtils().take_screenshot(self.driver, "element_not_present")
            raise

    def wait_for_element_visible(self, locator: Union[str, Tuple[str, str]]) -> WebElement:
        """
        等待元素可见
        
        Args:
            locator: 定位器
            
        Returns:
            WebElement: 找到的元素
        """
        by, value = self._get_by_and_value(locator)
        try:
            element = self.wait.until(EC.visibility_of_element_located((by, value)))
            logger.info(f"元素已可见: {by}={value}")
            return element
        except TimeoutException:
            logger.error(f"超时: 元素不可见 - {by}={value}")
            # 创建ScreenshotUtils实例并调用方法
            ScreenshotUtils().take_screenshot(self.driver, "element_not_visible")
            raise

    def wait_for_element_clickable(self, locator: Union[str, Tuple[str, str]]) -> WebElement:
        """
        等待元素可点击
        
        Args:
            locator: 定位器
            
        Returns:
            WebElement: 找到的元素
        """
        by, value = self._get_by_and_value(locator)
        try:
            element = self.wait.until(EC.element_to_be_clickable((by, value)))
            logger.info(f"元素可点击: {by}={value}")
            return element
        except TimeoutException:
            logger.error(f"超时: 元素不可点击 - {by}={value}")
            screenshot_utils.take_screenshot(self.driver, "element_not_clickable")
            raise

    def wait_for_element_invisible(self, locator: Union[str, Tuple[str, str]]) -> bool:
        """
        等待元素不可见
        
        Args:
            locator: 定位器
            
        Returns:
            bool: 元素是否不可见
        """
        by, value = self._get_by_and_value(locator)
        try:
            result = self.wait.until(EC.invisibility_of_element_located((by, value)))
            logger.info(f"元素已不可见: {by}={value}")
            return result
        except TimeoutException:
            logger.error(f"超时: 元素仍然可见 - {by}={value}")
            screenshot_utils.take_screenshot(self.driver, "element_still_visible")
            raise

    @timing
    def click(self, locator: Union[str, Tuple[str, str]]) -> None:
        """
        点击元素
        
        Args:
            locator: 定位器
        """
        element = self.wait_for_element_clickable(locator)
        try:
            element.click()
            logger.info(f"点击元素: {locator}")
        except (ElementNotInteractableException, ElementNotVisibleException) as e:
            logger.error(f"无法点击元素: {locator}, 错误: {str(e)}")
            # 尝试使用JavaScript点击
            logger.info(f"尝试使用JavaScript点击元素: {locator}")
            self.driver.execute_script("arguments[0].click();", element)

    @timing
    def double_click(self, locator: Union[str, Tuple[str, str]]) -> None:
        """
        双击元素
        
        Args:
            locator: 定位器
        """
        from selenium.webdriver.common.action_chains import ActionChains

        element = self.wait_for_element_visible(locator)
        actions = ActionChains(self.driver)
        actions.double_click(element).perform()
        logger.info(f"双击元素: {locator}")

    @timing
    def right_click(self, locator: Union[str, Tuple[str, str]]) -> None:
        """
        右键点击元素
        
        Args:
            locator: 定位器
        """
        from selenium.webdriver.common.action_chains import ActionChains

        element = self.wait_for_element_visible(locator)
        actions = ActionChains(self.driver)
        actions.context_click(element).perform()
        logger.info(f"右键点击元素: {locator}")

    @timing
    def input_text(self, locator: Union[str, Tuple[str, str]], text: str, clear_first: bool = True) -> None:
        """
        在输入框中输入文本
        
        Args:
            locator: 定位器
            text: 要输入的文本
            clear_first: 是否先清空输入框
        """
        element = self.wait_for_element_visible(locator)

        if clear_first:
            self.clear_text(locator)

        element.send_keys(text)
        logger.info(f"在元素 {locator} 中输入文本: {text}")

    @timing
    def clear_text(self, locator: Union[str, Tuple[str, str]]) -> None:
        """
        清空输入框
        
        Args:
            locator: 定位器
        """
        element = self.wait_for_element_visible(locator)
        element.clear()
        logger.info(f"清空元素 {locator} 的文本")

    def get_text(self, locator: Union[str, Tuple[str, str]]) -> str:
        """
        获取元素的文本内容
        
        Args:
            locator: 定位器
            
        Returns:
            str: 元素的文本内容
        """
        element = self.wait_for_element_visible(locator)
        text = element.text.strip()
        logger.info(f"获取元素 {locator} 的文本: {text}")
        return text

    def get_attribute(self, locator: Union[str, Tuple[str, str]], attribute: str) -> str:
        """
        获取元素的属性值
        
        Args:
            locator: 定位器
            attribute: 属性名
            
        Returns:
            str: 属性值
        """
        element = self.wait_for_element_present(locator)
        value = element.get_attribute(attribute)
        logger.info(f"获取元素 {locator} 的属性 {attribute}: {value}")
        return value

    def get_css_property(self, locator: Union[str, Tuple[str, str]], property_name: str) -> str:
        """
        获取元素的CSS属性值
        
        Args:
            locator: 定位器
            property_name: CSS属性名
            
        Returns:
            str: CSS属性值
        """
        element = self.wait_for_element_present(locator)
        value = element.value_of_css_property(property_name)
        logger.info(f"获取元素 {locator} 的CSS属性 {property_name}: {value}")
        return value

    def is_element_present(self, locator: Union[str, Tuple[str, str]]) -> bool:
        """
        检查元素是否存在
        
        Args:
            locator: 定位器
            
        Returns:
            bool: 元素是否存在
        """
        try:
            by, value = self._get_by_and_value(locator)
            self.driver.find_element(by, value)
            logger.info(f"元素存在: {locator}")
            return True
        except NoSuchElementException:
            logger.info(f"元素不存在: {locator}")
            return False

    def is_element_visible(self, locator: Union[str, Tuple[str, str]]) -> bool:
        """
        检查元素是否可见
        
        Args:
            locator: 定位器
            
        Returns:
            bool: 元素是否可见
        """
        try:
            element = self.find_element(locator)
            is_visible = element.is_displayed()
            logger.info(f"元素可见性: {locator}, 可见={is_visible}")
            return is_visible
        except NoSuchElementException:
            logger.info(f"元素不存在: {locator}, 视为不可见")
            return False

    def is_element_enabled(self, locator: Union[str, Tuple[str, str]]) -> bool:
        """
        检查元素是否可用
        
        Args:
            locator: 定位器
            
        Returns:
            bool: 元素是否可用
        """
        try:
            element = self.find_element(locator)
            is_enabled = element.is_enabled()
            logger.info(f"元素可用性: {locator}, 可用={is_enabled}")
            return is_enabled
        except NoSuchElementException:
            logger.info(f"元素不存在: {locator}, 视为不可用")
            return False

    def select_dropdown_by_value(self, locator: Union[str, Tuple[str, str]], value: str) -> None:
        """
        通过value值选择下拉框选项
        
        Args:
            locator: 定位器
            value: option的value值
        """
        from selenium.webdriver.support.ui import Select

        element = self.wait_for_element_present(locator)
        select = Select(element)
        select.select_by_value(value)
        logger.info(f"通过value选择下拉框 {locator}: {value}")

    def select_dropdown_by_text(self, locator: Union[str, Tuple[str, str]], text: str) -> None:
        """
        通过文本选择下拉框选项
        
        Args:
            locator: 定位器
            text: option的文本
        """
        from selenium.webdriver.support.ui import Select

        element = self.wait_for_element_present(locator)
        select = Select(element)
        select.select_by_visible_text(text)
        logger.info(f"通过文本选择下拉框 {locator}: {text}")

    def select_dropdown_by_index(self, locator: Union[str, Tuple[str, str]], index: int) -> None:
        """
        通过索引选择下拉框选项
        
        Args:
            locator: 定位器
            index: 选项索引（从0开始）
        """
        from selenium.webdriver.support.ui import Select

        element = self.wait_for_element_present(locator)
        select = Select(element)
        select.select_by_index(index)
        logger.info(f"通过索引选择下拉框 {locator}: {index}")

    def scroll_to_element(self, locator: Union[str, Tuple[str, str]]) -> None:
        """
        滚动到元素可见位置
        
        Args:
            locator: 定位器
        """
        element = self.find_element(locator)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        logger.info(f"滚动到元素: {locator}")

    def scroll_to_top(self) -> None:
        """
        滚动到页面顶部
        """
        self.driver.execute_script("window.scrollTo(0, 0);")
        logger.info("滚动到页面顶部")

    def scroll_to_bottom(self) -> None:
        """
        滚动到页面底部
        """
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        logger.info("滚动到页面底部")

    def switch_to_frame(self, frame_reference: Union[str, int, WebElement]) -> None:
        """
        切换到iframe
        
        Args:
            frame_reference: iframe的名称、ID、索引或元素对象
        """
        self.wait.until(EC.frame_to_be_available_and_switch_to_it(frame_reference))
        logger.info(f"切换到iframe: {frame_reference}")

    def switch_to_default_content(self) -> None:
        """
        切换回默认的上下文
        """
        self.driver.switch_to.default_content()
        logger.info("切换回默认上下文")

    def switch_to_parent_frame(self) -> None:
        """
        切换到父级iframe
        """
        self.driver.switch_to.parent_frame()
        logger.info("切换到父级iframe")

    def switch_to_window(self, window_index: int = 0) -> None:
        """
        切换到指定索引的窗口
        
        Args:
            window_index: 窗口索引
        """
        windows = self.driver.window_handles
        if window_index < len(windows):
            self.driver.switch_to.window(windows[window_index])
            logger.info(f"切换到窗口索引: {window_index}, 窗口句柄: {windows[window_index]}")
        else:
            logger.error(f"窗口索引超出范围: {window_index}, 可用窗口数: {len(windows)}")
            raise IndexError(f"窗口索引超出范围: {window_index}")

    def switch_to_new_window(self) -> None:
        """
        切换到新打开的窗口
        """
        windows = self.driver.window_handles
        if len(windows) > 1:
            self.driver.switch_to.window(windows[-1])
            logger.info(f"切换到新窗口: {windows[-1]}")
        else:
            logger.error("没有新窗口可供切换")
            raise IndexError("没有新窗口可供切换")

    def close_current_window(self) -> None:
        """
        关闭当前窗口
        """
        current_window = self.driver.current_window_handle
        self.driver.close()
        logger.info(f"关闭当前窗口: {current_window}")

        # 如果还有其他窗口,切换到第一个
        windows = self.driver.window_handles
        if windows:
            self.driver.switch_to.window(windows[0])
            logger.info(f"切换到剩余窗口: {windows[0]}")
