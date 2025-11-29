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
# 添加项目根目录到Python路径
import os
import sys
from typing import Optional, List, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.web.web_base_page import WebBasePage
from utils.web.element_handler import ElementHandler
from utils.logger_util import logger
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class BaiduHomePage(WebBasePage):
    """
    百度首页页面类
    封装百度首页的元素定位和操作方法
    """

    # 页面元素定位器
    SEARCH_BOX = (By.ID, "kw")  # 搜索框
    SEARCH_BUTTON = (By.ID, "su")  # 搜索按钮
    RESULT_COUNT = (By.XPATH, "//div[@class='result-stats']")  # 搜索结果数量
    RESULT_ITEMS = (By.XPATH, "//div[contains(@class, 'result')]")  # 搜索结果项
    NAVIGATION_LINKS = (By.XPATH, "//div[@id='s-top-left']/a")  # 顶部导航链接
    NEWS_LINK = (By.LINK_TEXT, "新闻")  # 新闻链接
    IMAGE_LINK = (By.LINK_TEXT, "图片")  # 图片链接
    VIDEO_LINK = (By.LINK_TEXT, "视频")  # 视频链接
    TIEBA_LINK = (By.LINK_TEXT, "贴吧")  # 贴吧链接
    ADVANCED_SEARCH_LINK = (By.XPATH, "//a[contains(text(),'高级搜索')]")  # 高级搜索链接

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
            self.open_page(url)
            # 验证页面标题
            expected_title = "百度一下,你就知道"
            actual_title = self.get_page_title()

            if expected_title in actual_title:
                logger.info(f"百度首页打开成功,页面标题: {actual_title}")
                return True
            else:
                logger.error(f"百度首页标题不匹配: 期望包含'{expected_title}', 实际为'{actual_title}'")
                return False
        except Exception as e:
            logger.error(f"打开百度首页失败: {str(e)}")
            return False

    def find_search_box(self, timeout: Optional[int] = None) -> Any:
        """
        查找搜索框元素
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            Any: 搜索框元素或None
        """
        logger.info("查找百度搜索框元素")

        try:
            search_box = self.element_handler.find_element(
                *self.SEARCH_BOX,
                timeout = timeout
            )
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
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功输入
        """
        logger.info(f"在搜索框中输入关键词: {keyword}")

        try:
            search_box = self.find_search_box(timeout = timeout)

            if search_box:
                # 清除输入框内容
                search_box.clear()
                # 输入关键词
                search_box.send_keys(keyword)
                logger.info("关键词输入成功")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"关键词输入失败: {str(e)}")
            return False

    def click_search_button(self, timeout: Optional[int] = None) -> bool:
        """
        点击搜索按钮
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功点击
        """
        logger.info("点击百度搜索按钮")

        try:
            search_button = self.element_handler.find_element(
                *self.SEARCH_BUTTON,
                timeout = timeout
            )

            if search_button:
                self.element_handler.click_element(search_button)
                logger.info("搜索按钮点击成功")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"搜索按钮点击失败: {str(e)}")
            return False

    def press_enter_key(self, timeout: Optional[int] = None) -> bool:
        """
        在搜索框中按回车键进行搜索
        
        Args:
            timeout: 超时时间（秒）
            
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
            else:
                return False
        except Exception as e:
            logger.error(f"回车键执行失败: {str(e)}")
            return False

    def perform_search(self, keyword: str, use_enter: bool = False, timeout: Optional[int] = None) -> bool:
        """
        执行完整的搜索流程
        
        Args:
            keyword: 搜索关键词
            use_enter: 是否使用回车键搜索（默认使用点击搜索按钮）
            timeout: 超时时间（秒）
            
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

    def wait_for_search_results(self, timeout: Optional[int] = None) -> bool:
        """
        等待搜索结果加载
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功加载结果
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        logger.info(f"等待搜索结果加载,超时时间: {timeout}秒")

        try:
            # 等待结果统计元素出现
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self.RESULT_COUNT)
            )
            logger.info("搜索结果加载成功")
            return True
        except Exception as e:
            logger.error(f"搜索结果加载超时: {str(e)}")
            return False

    def get_search_result_count(self) -> Optional[int]:
        """
        获取搜索结果数量
        
        Returns:
            Optional[int]: 搜索结果数量,如果获取失败则返回None
        """
        logger.info("获取搜索结果数量")

        try:
            result_count_element = self.element_handler.find_element(
                *self.RESULT_COUNT,
                timeout = 5
            )

            if result_count_element:
                result_text = result_count_element.text
                logger.info(f"搜索结果统计文本: {result_text}")

                # 简单解析结果数量
                # 例如: "百度为您找到相关结果约12,345个"
                import re
                match = re.search(r'约(\d+(?:,\d+)*)个', result_text)
                if match:
                    count_str = match.group(1).replace(',', '')
                    count = int(count_str)
                    logger.info(f"解析到搜索结果数量: {count}")
                    return count
                else:
                    logger.warning("无法从结果文本中解析数量")
                    return None
            else:
                return None
        except Exception as e:
            logger.error(f"获取搜索结果数量失败: {str(e)}")
            return None

    def get_search_results_list(self, timeout: Optional[int] = None) -> List[Any]:
        """
        获取搜索结果列表
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            List[Any]: 搜索结果元素列表
        """
        logger.info("获取搜索结果列表")

        try:
            results = self.element_handler.find_elements(
                *self.RESULT_ITEMS,
                timeout = timeout
            )

            logger.info(f"找到 {len(results)} 个搜索结果项")
            return results
        except Exception as e:
            logger.error(f"获取搜索结果列表失败: {str(e)}")
            return []

    def check_results_contain_keyword(self, keyword: str) -> bool:
        """
        检查搜索结果是否包含关键词
        
        Args:
            keyword: 要检查的关键词
            
        Returns:
            bool: 是否至少有一个结果包含关键词
        """
        logger.info(f"检查搜索结果是否包含关键词: {keyword}")

        results = self.get_search_results_list()

        if not results:
            logger.warning("没有找到搜索结果")
            return False

        # 检查每个结果是否包含关键词
        keyword_lower = keyword.lower()
        for i, result in enumerate(results, 1):
            try:
                result_text = result.text.lower()
                if keyword_lower in result_text:
                    logger.info(f"结果 {i} 包含关键词 '{keyword}'")
                    return True
            except Exception as e:
                logger.warning(f"检查结果 {i} 时出错: {str(e)}")
                continue

        logger.warning(f"没有结果包含关键词 '{keyword}'")
        return False


@pytest.fixture(scope = "function")
def web_driver(browser):
    """
    WebDriver的fixture实现
    
    Args:
        browser: 浏览器类型,来自conftest.py中的fixture
        
    Yields:
        WebDriver: 浏览器驱动实例
    """
    driver = None
    try:
        if browser.lower() == "chrome":
            options = Options()
            # 添加一些常用的Chrome选项
            options.add_argument("--start-maximized")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-gpu")
            # 在无头模式下运行（可选）
            # options.add_argument("--headless")

            # 使用webdriver-manager自动管理Chrome驱动
            from webdriver_manager.chrome import ChromeDriverManager
            driver = webdriver.Chrome(options = options)
        elif browser.lower() == "firefox":
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            options = FirefoxOptions()
            options.add_argument("--start-maximized")
            driver = webdriver.Firefox(options = options)
        elif browser.lower() == "edge":
            from selenium.webdriver.edge.options import Options as EdgeOptions
            options = EdgeOptions()
            options.add_argument("--start-maximized")
            driver = webdriver.Edge(options = options)
        elif browser.lower() == "safari":
            driver = webdriver.Safari()
        else:
            raise ValueError(f"不支持的浏览器类型: {browser}")

        logger.info(f"{browser}浏览器驱动初始化完成")
        yield driver
    except Exception as e:
        logger.error(f"初始化浏览器驱动时出错: {e}")
        raise
    finally:
        if driver:
            driver.quit()
            logger.info(f"{browser}浏览器驱动已关闭")

    def click_navigation_link(self, link_text: str, timeout: Optional[int] = None) -> bool:
        """
        点击顶部导航链接
        
        Args:
            link_text: 链接文本
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功点击
        """
        logger.info(f"点击导航链接: {link_text}")

        try:
            # 构建链接的定位器
            link_locator = (By.LINK_TEXT, link_text)

            # 查找并点击链接
            link_element = self.element_handler.find_element(
                *link_locator,
                timeout = timeout
            )

            if link_element:
                # 保存当前窗口句柄
                current_window = self.driver.current_window_handle

                # 点击链接
                self.element_handler.click_element(link_element)

                # 等待新窗口打开
                WebDriverWait(self.driver, timeout or self.DEFAULT_TIMEOUT).until(
                    EC.number_of_windows_to_be(2)
                )

                # 切换到新窗口
                for window_handle in self.driver.window_handles:
                    if window_handle != current_window:
                        self.driver.switch_to.window(window_handle)
                        logger.info(f"切换到新窗口: {self.get_page_title()}")
                        break

                logger.info(f"导航链接 '{link_text}' 点击成功")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"点击导航链接 '{link_text}' 失败: {str(e)}")
            return False

    def go_back(self) -> bool:
        """
        返回上一页
        
        Returns:
            bool: 是否成功返回
        """
        logger.info("返回上一页")

        try:
            self.driver.back()
            logger.info("成功返回上一页")
            return True
        except Exception as e:
            logger.error(f"返回上一页失败: {str(e)}")
            return False

    def refresh_page(self) -> bool:
        """
        刷新当前页面
        
        Returns:
            bool: 是否成功刷新
        """
        logger.info("刷新页面")

        try:
            super().refresh_page()
            logger.info("页面刷新成功")
            return True
        except Exception as e:
            logger.error(f"页面刷新失败: {str(e)}")
            return False
