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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from cases.web.pages.baidu_home_page import BaiduHomePage
from config.config_manager import config
from utils.file_util import DataHandler
from utils.logger_util import logger
from utils.screenshot_util import ScreenshotUtils


# WebDriver夹具,用于提供WebDriver实例
@pytest.fixture(scope = "class")
def web_driver():
    """
    WebDriver夹具
    创建ChromeDriver实例并在测试完成后清理
    使用try-except来处理不同的WebDriver创建方式

    Yields:
        WebDriver: WebDriver实例
    """
    logger.info("初始化WebDriver...")
    driver = None

    try:
        # 方式1: 直接指定ChromeDriver路径（推荐）
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
            from selenium.webdriver.chrome.service import Service
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service = service, options = chrome_options)
        else:
            logger.warning(f"未找到ChromeDriver: {chromedriver_path}, 尝试使用webdriver-manager")
            # 方式2: 尝试使用webdriver-manager自动管理ChromeDriver
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service

                logger.info("使用webdriver-manager自动管理ChromeDriver")
                # 使用webdriver-manager创建Service
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service = service, options = chrome_options)
            except ImportError:
                # 如果webdriver-manager未安装,尝试直接使用webdriver.Chrome
                logger.warning("webdriver-manager未安装,尝试直接使用ChromeDriver")
                driver = webdriver.Chrome(options = chrome_options)

        driver.implicitly_wait(config.timeout.implicitly_wait)
        logger.info("WebDriver初始化完成")
        yield driver
    except Exception as e:
        logger.error(f"WebDriver初始化失败: {str(e)}")
        # 如果初始化失败,仍然尝试yield None,让测试能够继续执行
        yield None
    finally:
        # 清理WebDriver资源
        if driver:
            logger.info("关闭WebDriver...")
            driver.quit()
            logger.info("WebDriver已关闭")


# 添加pytest标记,方便测试过滤
@pytest.mark.web
class TestBaiduSearch:
    """
    百度搜索功能测试类
    包含打开百度首页、输入关键词搜索和验证搜索结果等测试用例
    """

    @pytest.fixture(scope = "class", autouse = True)
    def setup(self, web_driver):
        """
        测试类级别的初始化
        设置WebDriver和页面对象
        
        Args:
            web_driver: WebDriver实例 (从fixture获取)
        """
        logger.info("=" * 60)
        logger.info("开始执行百度搜索功能测试")
        logger.info("=" * 60)

        # 检查web_driver是否为None
        if web_driver is None:
            logger.error("WebDriver初始化失败,无法执行Web测试")
            pytest.skip("WebDriver初始化失败,跳过测试")

        # 保存driver到类变量
        self.driver = web_driver

        # 初始化百度首页页面类
        self.baidu_home_page = BaiduHomePage(web_driver)
        logger.info(self.baidu_home_page)

        # 加载测试数据
        self.test_data_path = os.path.join(
            config.DATA_DIR,
            "test_data",
            "web_test_data.yaml"
        )

        try:
            self.test_data = DataHandler.read_yaml(self.test_data_path)
            logger.info(f"成功加载测试数据: {self.test_data_path}")
        except Exception as e:
            logger.error(f"加载测试数据失败: {str(e)}")
            pytest.skip("无法加载测试数据,跳过测试")

        # 获取百度搜索测试数据
        self.search_data = self.test_data["test_baidu_search"]
        self.search_params = self.search_data["search_params"]
        self.expected = self.search_data["expected"]
        self.test_scenarios = self.search_data["test_scenarios"]

        # 测试环境信息
        # logger.info(f"当前测试环境: {config.ENV}")
        try:
            logger.info(f"浏览器类型: {web_driver.name}")
        except AttributeError:
            logger.warning("无法获取浏览器类型")
        logger.info(f"默认超时时间: {config.timeout.implicitly_wait}秒")

        yield

        logger.info("=" * 60)
        logger.info("百度搜索功能测试执行完成")
        logger.info("=" * 60)

    @pytest.fixture(autouse = True)
    def setup_class(self, request, setup):
        """
        每个测试用例执行前的设置
        确保每次测试都从百度首页开始
        """
        # 获取当前测试名称
        test_name = request.node.name if hasattr(request, 'node') else "unknown_test"

        logger.info("-" * 50)
        logger.info(f"开始执行测试用例: {test_name}")

        # 打开百度首页
        self.baidu_home_page.open_baidu_homepage()

        # 测试用例执行完成后的清理
        yield

        logger.info(f"测试用例执行完成: {test_name}")

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
        expected_title = self.expected["title"]

        # 验证页面标题
        assert expected_title in actual_title, \
            f"百度首页标题不正确: 期望包含'{expected_title}', 实际为'{actual_title}'"
        logger.info(f"页面标题验证通过: {actual_title}")

        # 验证搜索框元素
        search_box = self.baidu_home_page.find_search_box()
        assert search_box is not None, self.expected["error_messages"]["element_not_found"]
        logger.info("搜索框元素验证通过")

        # 验证搜索框的placeholder属性
        actual_placeholder = search_box.get_attribute("placeholder")
        expected_placeholder = self.expected["search_box_placeholder"]

        # 部分匹配,因为不同地区可能有所不同
        assert expected_placeholder in actual_placeholder or "百度" in actual_placeholder, \
            f"搜索框占位文本不正确: 期望包含'{expected_placeholder}', 实际为'{actual_placeholder}'"
        logger.info("搜索框占位文本验证通过")

        # 截图保存
        ScreenshotUtils().capture_screenshot(
            driver = self.driver,
            name = "百度首页加载成功截图"
        )

        logger.info("百度首页加载测试通过")

    @pytest.mark.smoke
    @pytest.mark.web
    def test_baidu_search_trae(self):
        """
        测试百度搜索"trae"关键字
        验证搜索流程和搜索结果
        """
        logger.info("执行百度搜索'trae'关键字测试")

        # 获取搜索关键词
        keyword = self.search_params["keyword"]
        timeout = self.search_params["timeout"]

        # 执行搜索
        search_success = self.baidu_home_page.perform_search(
            keyword = keyword,
            use_enter = False,  # 使用点击搜索按钮
            timeout = timeout
        )

        # 验证搜索操作是否成功
        assert search_success, "搜索操作执行失败"
        logger.info(f"搜索关键词 '{keyword}' 执行成功")

        # 等待搜索结果加载
        results_loaded = self.baidu_home_page.wait_for_search_results(timeout = timeout)
        assert results_loaded, "搜索结果加载失败"
        logger.info("搜索结果加载成功")

        # 截图保存搜索结果页面
        ScreenshotUtils().capture_screenshot(
            driver = self.driver,
            name = f"搜索关键词 '{keyword}' 结果截图"
        )

        # 获取并验证搜索结果数量
        result_count = self.baidu_home_page.get_search_result_count()
        min_count = self.expected["result_count_min"]

        if result_count is not None:
            assert result_count >= min_count, \
                f"搜索结果数量不足: 期望至少{min_count}个, 实际为{result_count}个"
            logger.info(f"搜索结果数量验证通过: {result_count}个")
        else:
            logger.warning("无法获取精确的搜索结果数量,跳过数量验证")

        # 验证搜索结果是否包含关键词
        results_contain_keyword = self.baidu_home_page.check_results_contain_keyword(keyword)
        assert results_contain_keyword, \
            f"搜索结果中未找到关键词 '{keyword}'"
        logger.info(f"搜索结果包含关键词 '{keyword}' 验证通过")

        # 验证页面标题是否包含关键词
        new_title = self.baidu_home_page.get_page_title()
        assert keyword in new_title, \
            f"搜索后页面标题不包含关键词: 标题='{new_title}', 关键词='{keyword}'"
        logger.info(f"搜索后页面标题验证通过: {new_title}")

        logger.info("百度搜索'trae'关键字测试通过")

    @pytest.mark.web
    def test_baidu_search_scenarios(self):
        """
        测试不同的搜索场景
        通过手动遍历测试不同的搜索关键词和配置
        """
        # 手动遍历非标准搜索场景
        scenarios = [s for s in self.search_params["test_scenarios"] if s["name"] != "standard_search"]
        for scenario in scenarios:
            scenario_name = scenario["name"]
            scenario_desc = scenario["description"]
            keyword = scenario["keyword"]
            validate_results = scenario["validate_results"]

            logger.info(f"执行搜索场景测试: {scenario_name} - {scenario_desc}")
            logger.info(f"使用关键词: '{keyword}'")

            # 执行搜索
            search_success = self.baidu_home_page.perform_search(
                keyword = keyword,
                use_enter = True,  # 使用回车键搜索
                timeout = self.search_params["timeout"]
            )

            # 验证搜索操作是否成功
            assert search_success, f"场景 '{scenario_name}' 搜索操作执行失败"

            # 如果需要验证结果
            if validate_results:
                # 等待搜索结果加载
                results_loaded = self.baidu_home_page.wait_for_search_results()
                assert results_loaded, "搜索结果加载失败"

                # 验证结果是否包含关键词
                if keyword:
                    results_contain_keyword = self.baidu_home_page.check_results_contain_keyword(keyword)
                    assert results_contain_keyword, f"结果中未找到关键词 '{keyword}'"
            else:
                # 对于空搜索等场景,验证是否有相应提示
                logger.info(f"场景 '{scenario_name}' 不需要验证搜索结果")

            # 截图保存测试场景结果
            scenario_filename = f"baidu_search_{scenario_name}"
            ScreenshotUtils().capture_screenshot(
                driver = self.driver,
                name = f"搜索场景 '{scenario_name}' 结果截图"
            )

            logger.info(f"搜索场景测试 '{scenario_name}' 通过")

    @pytest.mark.web
    def test_baidu_search_no_keyword(self):
        """
        测试不输入关键词直接搜索
        验证系统对空搜索的处理
        """
        logger.info("执行空关键词搜索测试")

        # 执行空关键词搜索
        search_success = self.baidu_home_page.perform_search(
            keyword = "",
            use_enter = False,
            timeout = self.search_params["timeout"]
        )

        # 验证搜索操作是否成功
        assert search_success, "空关键词搜索操作执行失败"

        # 对于空关键词搜索,百度通常不会跳转页面
        # 验证是否仍在首页
        current_url = self.baidu_home_page.get_current_url()
        assert "baidu.com" in current_url, \
            f"空关键词搜索后页面跳转不正确: {current_url}"

        logger.info("空关键词搜索测试通过")

    @pytest.mark.web
    def test_search_button_display(self):
        """
        测试搜索按钮显示和属性
        验证搜索按钮是否正确显示和可用
        """
        logger.info("验证搜索按钮显示和属性")

        # 查找搜索按钮
        search_button = self.driver.find_element(*BaiduHomePage.SEARCH_BUTTON)

        # 验证按钮是否可见
        assert search_button.is_displayed(), "搜索按钮不可见"

        # 验证按钮是否可用
        assert search_button.is_enabled(), "搜索按钮不可用"

        # 验证按钮的value属性（百度搜索按钮的文本）
        button_value = search_button.get_attribute("value")
        assert "百度一下" in button_value, \
            f"搜索按钮文本不正确: {button_value}"

        logger.info("搜索按钮属性验证通过")

    def teardown_test(self):
        """
        每个测试方法执行后的清理
        可以在这里添加错误截图等操作
        """
        import inspect
        test_method_name = inspect.currentframe().f_code.co_name
        logger.info(f"测试方法 {test_method_name} 执行完成")


# 为了支持参数化测试,需要在类级别访问test_scenarios
TestBaiduSearch.search_params = {
    "test_scenarios": [
        {"name": "standard_search", "description": "标准搜索", "keyword": "trae", "validate_results": True},
        {"name": "special_characters", "description": "特殊字符搜索", "keyword": "trae!@#", "validate_results": True},
        {"name": "multiple_words", "description": "多词搜索", "keyword": "trae ai platform", "validate_results": True}
    ]
}

if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])