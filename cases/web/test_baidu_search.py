"""
-------------------------------------------------
File:           test_baidu_search.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
Web测试样例 - 百度搜索功能测试
演示如何使用Web工具类进行页面操作、元素交互和结果验证
-------------------------------------------------
"""
import os

import pytest

from cases.web.pages.baidu_home_page import BaiduHomePage
from utils.common_util import util
from utils.logger_util import logger


# 添加pytest标记,方便测试过滤
@pytest.mark.web
class TestBaiduSearch:
    """
    百度搜索功能测试类
    包含打开百度首页、输入关键词搜索和验证搜索结果等测试用例
    """

    # 类变量，用于存储driver和页面对象
    driver = None
    baidu_home_page = None

    @classmethod
    def setup_class(cls):
        """
        测试类级别的初始化
        设置WebDriver和页面对象
        """
        logger.info("=" * 60)
        logger.info("开始执行百度搜索功能测试")
        logger.info("=" * 60)

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            # 设置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu")

            # 直接指定ChromeDriver路径
            chromedriver_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "utils", "drivers", "chromedriver-mac-arm64", "chromedriver"
            )

            if os.path.exists(chromedriver_path):
                logger.info(f"使用指定路径的ChromeDriver: {chromedriver_path}")
                service = Service(chromedriver_path)
                cls.driver = webdriver.Chrome(service = service, options = chrome_options)
            else:
                logger.warning(f"未找到ChromeDriver: {chromedriver_path}")
                cls.driver = webdriver.Chrome(options = chrome_options)

            cls.driver.implicitly_wait(10)
            logger.info("WebDriver初始化完成")

            # 初始化百度首页页面类
            cls.baidu_home_page = BaiduHomePage(cls.driver)
            logger.info("百度首页页面类初始化完成")

        except Exception as e:
            logger.error(f"WebDriver初始化失败: {str(e)}")
            pytest.skip("WebDriver初始化失败,跳过测试")

    @classmethod
    def teardown_class(cls):
        """
        测试类级别的清理
        """
        logger.info("=" * 60)
        logger.info("百度搜索功能测试执行完成")
        logger.info("=" * 60)

        # 清理WebDriver资源
        if cls.driver:
            logger.info("关闭WebDriver...")
            cls.driver.quit()
            logger.info("WebDriver已关闭")

    def setup_method(self):
        """
        每个测试用例执行前的设置
        确保每次测试都从百度首页开始
        """
        logger.info("-" * 50)
        logger.info("开始执行测试用例")

        # 打开百度首页
        self.baidu_home_page.open_baidu_homepage()

        logger.info("百度首页已打开")
        self.baidu_home_page.max_window()

    @staticmethod
    def teardown_method():
        """
        每个测试用例执行后的清理
        """
        logger.info("测试用例执行完成")
        logger.info("-" * 50)

    @pytest.mark.smoke
    @pytest.mark.web
    def test_baidu_homepage_load(self):
        """
        测试百度首页加载
        验证页面标题和搜索框元素是否正确加载
        """
        logger.info("验证百度首页加载成功")

        # 获取页面标题
        actual_title = self.baidu_home_page.get_page_title()
        assert "百度一下" in actual_title, \
            f"百度首页标题不正确: 期望包含'百度一下', 实际为'{actual_title}'"
        logger.info(f"页面标题验证通过: {actual_title}")

        # 验证搜索框元素
        search_box = self.baidu_home_page.find_search_box()
        assert search_box is not None, "未找到搜索框元素"
        logger.info("搜索框元素验证通过")

        logger.info("百度首页加载测试通过")

    @pytest.mark.smoke
    @pytest.mark.web
    def test_baidu_search_trae(self):
        """
        测试百度搜索"trae"关键字
        验证搜索流程和搜索结果
        """
        logger.info("执行百度搜索'trae'关键字测试")

        # 执行搜索
        search_success = self.baidu_home_page.perform_search(
            keyword = "trae",
            use_enter = False,  # 使用点击搜索按钮
            timeout = 10
        )

        # 验证搜索操作是否成功
        assert search_success, "搜索操作执行失败"
        logger.info("搜索关键词 'trae' 执行成功")
        util.sleep(2)
        # 验证搜索结果页面包含"trae"关键词
        new_title = self.baidu_home_page.get_page_title()
        assert "trae" in new_title.lower(), \
            f"搜索后页面标题不包含关键词: 标题='{new_title}', 关键词='trae'"
        logger.info(f"搜索后页面标题验证通过: {new_title}")

        logger.info("百度搜索'trae'关键字测试通过")

    @pytest.mark.web
    def test_baidu_search_with_enter(self):
        """
        测试使用回车键进行搜索
        """
        logger.info("测试使用回车键进行搜索")

        # 执行搜索（使用回车键）
        search_success = self.baidu_home_page.perform_search(
            keyword = "trae",
            use_enter = True,  # 使用回车键搜索
            timeout = 10
        )

        # 验证搜索操作是否成功
        assert search_success, "回车键搜索操作执行失败"
        logger.info("回车键搜索执行成功")
        logger.info("回车键搜索测试通过")
        util.sleep(2)
