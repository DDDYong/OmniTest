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
    TimeoutException,
    StaleElementReferenceException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger_util import logger


class ElementHandler:
    """
    元素操作处理器类
    """

    def __init__(self, driver: webdriver, timeout: Optional[int] = None):
        """
        初始化元素处理器
        
        Args:
            driver: Selenium WebDriver实例
            timeout: 超时时间（秒）,默认为10秒
        """
        self.driver = driver
        self.timeout = timeout or 10
        self.wait = WebDriverWait(
            driver = self.driver,
            timeout = self.timeout,
            poll_frequency = 0.5,
            ignored_exceptions = [
                NoSuchElementException,
                StaleElementReferenceException
            ]
        )

    def _get_by_and_value(self, locator: Union[str, Tuple[str, str]]) -> Tuple[By, str]:
        """
        获取By对象和定位器值
        
        Args:
            locator: 定位器,可以是字符串("id=login")或元组(By.ID, "login")
            
        Returns:
            Tuple[By, str]: (By对象, 定位器值)
        """
        if isinstance(locator, tuple) and len(locator) == 2:
            return locator
        else:
            logger.error(f"无效的定位器: {locator}")
            raise ValueError(f"无效的定位器格式: {locator}")

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
            raise

    def click_element(self, element: WebElement) -> bool:
        """
        点击元素
        
        Args:
            element: 要点击的元素
            
        Returns:
            bool: 是否成功点击
        """
        try:
            element.click()
            logger.info("元素点击成功")
            return True
        except Exception as e:
            logger.error(f"元素点击失败: {str(e)}")
            return False

    def send_keys(self, element: WebElement, text: str) -> bool:
        """
        向元素输入文本
        
        Args:
            element: 输入元素
            text: 要输入的文本
            
        Returns:
            bool: 是否成功输入
        """
        try:
            element.clear()
            element.send_keys(text)
            logger.info(f"文本输入成功: {text}")
            return True
        except Exception as e:
            logger.error(f"文本输入失败: {str(e)}")
            return False

    def get_text(self, element: WebElement) -> str:
        """
        获取元素文本
        
        Args:
            element: 元素
            
        Returns:
            str: 元素文本
        """
        try:
            text = element.text
            logger.info(f"获取元素文本: {text}")
            return text
        except Exception as e:
            logger.error(f"获取元素文本失败: {str(e)}")
            return ""

    def get_attribute(self, element: WebElement, attribute: str) -> str:
        """
        获取元素属性
        
        Args:
            element: 元素
            attribute: 属性名
            
        Returns:
            str: 属性值
        """
        try:
            value = element.get_attribute(attribute)
            logger.info(f"获取元素属性: {attribute}={value}")
            return value
        except Exception as e:
            logger.error(f"获取元素属性失败: {str(e)}")
            return ""
