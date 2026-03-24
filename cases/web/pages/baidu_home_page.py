"""
-------------------------------------------------
File:           baidu_home_page.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
百度首页页面类 - 封装百度首页的元素定位和操作方法
用于Web测试样例中的百度搜索功能测试
-------------------------------------------------
"""
import time
from typing import Optional, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from utils.logger import logger
from utils.web.element_handler import ElementHandler
from utils.web.web_base_page import WebBasePage


class BaiduHomePage(WebBasePage):
    """
    百度首页页面类
    封装百度首页的元素定位和操作方法
    """

    # 页面元素定位器 - 使用百度搜索的标准元素ID
    SEARCH_BOX = (By.ID, "chat-textarea")  # 搜索框
    SEARCH_BUTTON = (By.ID, "chat-submit-button")  # 搜索按钮

    def __init__(self, driver):
        """
        初始化百度首页
        
        Args:
            driver: WebDriver实例
        """
        super().__init__(driver)
        self.element_handler = ElementHandler(driver)
        logger.info("初始化百度首页页面类")

    def open_baidu_homepage(self, url: str = "https://www.baidu.com") -> bool:
        """
        打开百度首页
        
        Args:
            url: 百度首页URL
            
        Returns:
            bool: 是否成功打开页面
        """
        logger.info(f"打开百度首页: {url}")

        try:
            self.open(url)
            time.sleep(2)
            self.max_window()
            
            # 验证页面标题
            actual_title = self.get_page_title()
            if "百度一下" in actual_title:
                logger.info(f"百度首页打开成功,页面标题: {actual_title}")
                return True
            else:
                logger.error(f"百度首页标题不匹配: 期望包含'百度一下', 实际为'{actual_title}'")
                return False
        except Exception as e:
            logger.error(f"打开百度首页失败: {str(e)}")
            return False

    def find_search_box(self, timeout: Optional[int] = None) -> Any:
        """
        查找搜索框元素
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            Any: 搜索框元素或None
        """
        logger.info("查找百度搜索框元素")

        try:
            search_box = self.element_handler.wait_for_element_present(self.SEARCH_BOX)
            logger.info("搜索框元素查找成功")
            return search_box
        except Exception as e:
            logger.error(f"搜索框元素查找失败: {str(e)}")
            return None

    def enter_search_keyword(self, keyword: str, timeout: Optional[int] = None) -> bool:
        """
        在搜索框中输入关键词
        
        Args:
            keyword: 搜索关键词
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否成功输入
        """
        logger.info(f"在搜索框中输入关键词: {keyword}")

        try:
            search_box = self.find_search_box(timeout = timeout)
            if search_box:
                search_box.clear()
                search_box.send_keys(keyword)
                logger.info("关键词输入成功")
                return True
            return False
        except Exception as e:
            logger.error(f"关键词输入失败: {str(e)}")
            return False

    def click_search_button(self, timeout: Optional[int] = None) -> bool:
        """
        点击搜索按钮
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否成功点击
        """
        logger.info("点击百度搜索按钮")

        try:
            search_button = self.element_handler.wait_for_element_clickable(self.SEARCH_BUTTON)
            if search_button:
                search_button.click()
                logger.info("搜索按钮点击成功")
                return True
            return False
        except Exception as e:
            logger.error(f"搜索按钮点击失败: {str(e)}")
            return False

    def press_enter_key(self, timeout: Optional[int] = None) -> bool:
        """
        在搜索框中按回车键进行搜索
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否成功执行
        """
        logger.info("在搜索框中按回车键")

        try:
            search_box = self.find_search_box(timeout = timeout)
            if search_box:
                search_box.send_keys(Keys.ENTER)
                logger.info("回车键执行成功")
                return True
            return False
        except Exception as e:
            logger.error(f"回车键执行失败: {str(e)}")
            return False

    def perform_search(self, keyword: str, use_enter: bool = False, timeout: Optional[int] = None) -> bool:
        """
        执行完整的搜索流程
        
        Args:
            keyword: 搜索关键词
            use_enter: 是否使用回车键搜索(默认使用点击搜索按钮)
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否成功执行搜索
        """
        logger.info(f"执行百度搜索: 关键词='{keyword}', 使用回车='{use_enter}'")

        # 输入关键词
        if not self.enter_search_keyword(keyword, timeout):
            return False

        # 执行搜索
        if use_enter:
            return self.press_enter_key(timeout)
        else:
            return self.click_search_button(timeout)
