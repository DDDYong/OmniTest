"""
-------------------------------------------------
File:           web_base_page.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
Web自动化基础页面类,实现POM模式中的页面基类功能,提供页面交互的通用方法
-------------------------------------------------
"""
from typing import Optional, Dict, Union

from selenium.webdriver.remote.webdriver import WebDriver

from utils.logger_util import logger


class WebBasePage:
    """
    Web自动化页面基类
    """

    def __init__(self, driver: WebDriver, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        初始化页面类
        
        Args:
            driver: WebDriver实例
            base_url: 基础URL
            timeout: 超时时间（秒）
        """
        self.driver = driver
        self.base_url = base_url or "https://www.baidu.com"
        self.timeout = timeout or 10

    def open(self, url: Optional[str] = None) -> 'WebBasePage':
        """
        打开页面
        
        Args:
            url: 页面URL,如果为None则使用基础URL
            
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        if url:
            full_url = url
        else:
            full_url = self.base_url

        logger.info(f"打开页面: {full_url}")
        self.driver.get(full_url)
        return self

    def max_window(self) -> 'WebBasePage':
        """
        最大化窗口

        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        logger.info("最大化窗口")
        self.driver.maximize_window()
        return self

    def back(self) -> 'WebBasePage':
        """
        返回上一页

        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        logger.info("返回上一页")
        self.driver.back()
        return self

    def refresh(self) -> 'WebBasePage':
        """
        刷新当前页面
        
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        logger.info("刷新当前页面")
        self.driver.refresh()
        return self

    def get_current_url(self) -> str:
        """
        获取当前页面URL
        
        Returns:
            str: 当前页面URL
        """
        url = self.driver.current_url
        logger.info(f"当前页面URL: {url}")
        return url

    def get_page_title(self) -> str:
        """
        获取页面标题
        
        Returns:
            str: 页面标题
        """
        title = self.driver.title
        logger.info(f"页面标题: {title}")
        return title

    def is_url_contains(self, text: str) -> bool:
        """
        检查URL是否包含指定文本
        
        Args:
            text: 要检查的文本
            
        Returns:
            bool: URL是否包含指定文本
        """
        current_url = self.get_current_url()
        contains = text in current_url
        logger.info(f"URL包含检查: '{text}' {'在' if contains else '不在'} URL中")
        return contains

    def is_title_contains(self, text: str) -> bool:
        """
        检查页面标题是否包含指定文本
        
        Args:
            text: 要检查的文本
            
        Returns:
            bool: 页面标题是否包含指定文本
        """
        title = self.get_page_title()
        contains = text in title
        logger.info(f"标题包含检查: '{text}' {'在' if contains else '不在'} 标题中")
        return contains

    def wait_for_page_loaded(self, timeout: Optional[int] = None) -> bool:
        """
        等待页面加载完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 页面是否加载完成
        """
        timeout = timeout or self.timeout
        logger.info(f"等待页面加载完成,超时时间: {timeout}秒")

        def page_loaded(driver: WebDriver) -> bool:
            """检查页面是否加载完成"""
            return driver.execute_script("return document.readyState") == "complete"

        # 等待页面加载完成
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException

        try:
            WebDriverWait(self.driver, timeout).until(page_loaded)
            logger.info("页面加载完成")
            return True
        except TimeoutException:
            logger.error(f"页面加载超时: {timeout}秒")
            return False
        return self

    def switch_to_window(self, window_index: int = 0) -> 'WebBasePage':
        """
        切换到指定索引的窗口
        
        Args:
            window_index: 窗口索引
            
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        self.element_handler.switch_to_window(window_index)
        return self

    def switch_to_new_window(self) -> 'WebBasePage':
        """
        切换到新打开的窗口
        
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        self.element_handler.switch_to_new_window()
        return self

    def close_current_window(self) -> 'WebBasePage':
        """
        关闭当前窗口
        
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        self.element_handler.close_current_window()
        return self

    def accept_alert(self, wait_time: Optional[int] = None) -> str:
        """
        接受警告框
        
        Args:
            wait_time: 等待时间（秒）
            
        Returns:
            str: 警告框的文本
        """
        wait_time = wait_time or self.timeout
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        logger.info("等待并接受警告框")
        try:
            alert = WebDriverWait(self.driver, wait_time).until(EC.alert_is_present())
            alert_text = alert.text
            alert.accept()
            logger.info(f"接受警告框,文本: {alert_text}")
            return alert_text
        except TimeoutException:
            logger.error(f"警告框未出现: {wait_time}秒")
            raise

    def dismiss_alert(self, wait_time: Optional[int] = None) -> str:
        """
        关闭警告框
        
        Args:
            wait_time: 等待时间（秒）
            
        Returns:
            str: 警告框的文本
        """
        wait_time = wait_time or self.timeout
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        logger.info("等待并关闭警告框")
        try:
            alert = WebDriverWait(self.driver, wait_time).until(EC.alert_is_present())
            alert_text = alert.text
            alert.dismiss()
            logger.info(f"关闭警告框,文本: {alert_text}")
            return alert_text
        except TimeoutException:
            logger.error(f"警告框未出现: {wait_time}秒")
            raise

    def send_keys_to_alert(self, text: str, wait_time: Optional[int] = None) -> None:
        """
        向警告框输入文本
        
        Args:
            text: 要输入的文本
            wait_time: 等待时间（秒）
        """
        wait_time = wait_time or self.timeout
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        logger.info(f"向警告框输入文本: {text}")
        try:
            alert = WebDriverWait(self.driver, wait_time).until(EC.alert_is_present())
            alert.send_keys(text)
            logger.info(f"成功向警告框输入文本")
        except TimeoutException:
            logger.error(f"警告框未出现: {wait_time}秒")
            raise

    def handle_popup(self, accept: bool = True, wait_time: Optional[int] = None) -> str:
        """
        处理弹窗
        
        Args:
            accept: 是否接受弹窗
            wait_time: 等待时间（秒）
            
        Returns:
            str: 弹窗的文本
        """
        return self.accept_alert(wait_time) if accept else self.dismiss_alert(wait_time)

    def get_cookies(self) -> Dict[str, str]:
        """
        获取所有cookies
        
        Returns:
            Dict[str, str]: cookies字典
        """
        cookies = {cookie['name']: cookie['value'] for cookie in self.driver.get_cookies()}
        logger.info(f"获取到 {len(cookies)} 个cookies")
        return cookies

    def get_cookie(self, name: str) -> Optional[str]:
        """
        获取指定名称的cookie
        
        Args:
            name: cookie名称
            
        Returns:
            Optional[str]: cookie值
        """
        cookie = self.driver.get_cookie(name)
        value = cookie['value'] if cookie else None
        logger.info(f"获取cookie - 名称: {name}, 值: {value}")
        return value

    def add_cookie(self, name: str, value: str, path: str = '/', domain: Optional[
        str] = None, secure: bool = False) -> 'WebBasePage':
        """
        添加cookie
        
        Args:
            name: cookie名称
            value: cookie值
            path: cookie路径
            domain: cookie域名
            secure: 是否安全
            
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        cookie = {
            'name': name,
            'value': value,
            'path': path,
            'secure': secure
        }
        if domain:
            cookie['domain'] = domain

        logger.info(f"添加cookie: {name}={value}")
        self.driver.add_cookie(cookie)
        return self

    def delete_cookie(self, name: str) -> 'WebBasePage':
        """
        删除指定名称的cookie
        
        Args:
            name: cookie名称
            
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        logger.info(f"删除cookie: {name}")
        self.driver.delete_cookie(name)
        return self

    def delete_all_cookies(self) -> 'WebBasePage':
        """
        删除所有cookies
        
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        logger.info("删除所有cookies")
        self.driver.delete_all_cookies()
        return self

    # 元素操作方法,直接委托给ElementHandler
    def find_element(self, locator: Union[str, tuple]):
        """
        查找单个元素
        
        Args:
            locator: 定位器
        """
        return self.element_handler.find_element(locator)

    def find_elements(self, locator: Union[str, tuple]):
        """
        查找多个元素
        
        Args:
            locator: 定位器
        """
        return self.element_handler.find_elements(locator)

    def click(self, locator: Union[str, tuple]) -> 'WebBasePage':
        """
        点击元素
        
        Args:
            locator: 定位器
            
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        self.element_handler.click(locator)
        return self

    def input_text(self, locator: Union[str, tuple], text: str, clear_first: bool = True) -> 'WebBasePage':
        """
        输入文本
        
        Args:
            locator: 定位器
            text: 要输入的文本
            clear_first: 是否先清空
            
        Returns:
            WebBasePage: 页面实例（用于链式调用）
        """
        self.element_handler.input_text(locator, text, clear_first)
        return self

    def get_text(self, locator: Union[str, tuple]) -> str:
        """
        获取元素文本
        
        Args:
            locator: 定位器
            
        Returns:
            str: 元素文本
        """
        return self.element_handler.get_text(locator)

    def is_element_present(self, locator: Union[str, tuple]) -> bool:
        """
        检查元素是否存在
        
        Args:
            locator: 定位器
            
        Returns:
            bool: 元素是否存在
        """
        return self.element_handler.is_element_present(locator)

    def is_element_visible(self, locator: Union[str, tuple]) -> bool:
        """
        检查元素是否可见
        
        Args:
            locator: 定位器
            
        Returns:
            bool: 元素是否可见
        """
        return self.element_handler.is_element_visible(locator)