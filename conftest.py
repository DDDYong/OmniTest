"""
-------------------------------------------------
File:           conftest.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
OmniTest项目测试配置文件,提供测试夹具(fixtures)和测试前后的准备清理工作,支持API、Web、App和性能测试
-------------------------------------------------
"""
import os
import sys
from datetime import datetime

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config_manager import config
from utils.logger_util import logger
from utils.common_util import CommonUtils
from utils.file_util import DataHandler
from utils.api.api_client import ApiClient
from utils.api.request_manager import RequestManager
from utils.app.appium_manager import AppiumManager


# 测试夹具（fixtures）
@pytest.fixture(scope = "session")
def project_root():
    """
    项目根目录
    
    Returns:
        str: 项目根目录路径
    """
    return config.ROOT_DIR


@pytest.fixture(scope = "session")
def utils():
    """
    通用工具实例
    
    Returns:
        CommonUtils: 通用工具实例
    """
    return CommonUtils()


@pytest.fixture(scope = "session")
def data_handler():
    """
    数据处理工具实例
    
    Returns:
        DataHandler: 数据处理工具实例
    """
    return DataHandler()


@pytest.fixture(scope = "session")
def api_client():
    """
    API客户端实例
    
    Returns:
        ApiClient: API客户端实例
    """
    client = ApiClient()
    logger.info("API客户端初始化完成")
    yield client
    client.close()
    logger.info("API客户端已关闭")


@pytest.fixture(scope = "session")
def request_manager(api_client):
    """
    请求管理器实例
    
    Args:
        api_client: API客户端实例
        
    Returns:
        RequestManager: 请求管理器实例
    """
    manager = RequestManager(api_client)
    logger.info("请求管理器初始化完成")
    yield manager
    logger.info("请求管理器已关闭")


@pytest.fixture(scope = "session")
def appium_manager():
    """
    Appium管理器实例
    
    Yields:
        AppiumManager: Appium管理器实例
    """
    manager = AppiumManager()
    logger.info("Appium管理器初始化完成")
    yield manager
    # 确保清理资源
    if manager.driver:
        manager.quit_driver()
    if manager.is_service_running():
        manager.stop_appium_service()
    logger.info("Appium管理器资源已清理")


# WebDriver夹具需要在测试文件中根据具体浏览器类型实现
# 这里只提供基础的fixture结构
@pytest.fixture(scope = "function")
def setup_teardown(request):
    """
    测试用例级别的setup和teardown
    每个测试用例执行前后都会调用
    """
    # 获取测试用例信息
    test_name = request.node.name
    test_module = request.node.module.__name__
    test_class = request.node.cls.__name__ if request.node.cls else ""

    # 构建完整的测试用例名称
    if test_class:
        full_test_name = f"{test_module}.{test_class}.{test_name}"
    else:
        full_test_name = f"{test_module}.{test_name}"

    logger.info(f"开始执行测试用例: {full_test_name}")

    # 记录测试开始时间
    start_time = datetime.now()

    # 测试前准备
    # 可以在这里添加一些通用的测试前准备工作

    yield  # 测试用例执行

    # 测试后清理
    # 计算测试执行时间
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 获取测试结果
    test_result = "通过" if request.node.rep_call.passed else "失败"
    if hasattr(request.node, 'rep_setup') and request.node.rep_setup.failed:
        test_result = "setup失败"
    elif hasattr(request.node, 'rep_teardown') and request.node.rep_teardown.failed:
        test_result = "teardown失败"

    logger.info(f"测试用例 {full_test_name} 执行{test_result},耗时: {duration:.2f}秒")


# 钩子函数：记录测试结果
@pytest.hookimpl(tryfirst = True, hookwrapper = True)
def pytest_runtest_makereport(item, call):
    """
    记录测试执行结果的钩子函数
    用于在setup_teardown fixture中获取测试结果
    """
    # 执行原始钩子
    outcome = yield
    # 获取测试报告
    report = outcome.get_result()

    # 将测试报告存储在item上,以便在fixture中使用
    # 分别记录setup、call、teardown三个阶段的结果
    setattr(item, f"rep_{report.when}", report)

    # 如果测试失败,捕获截图（根据测试类型）
    if report.when == "call" and report.failed:
        # 检查是否是web测试或app测试
        if hasattr(item.cls, "driver"):
            # Web或App测试,尝试截图
            try:
                driver = item.cls.driver
                if driver:
                    # 生成截图文件名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    test_name = item.nodeid.replace("/", "_").replace(":", "_")
                    filename = f"{test_name}_{timestamp}"

                    # 保存截图
                    screenshot_path = screenshot_utils.capture_screenshot(
                        driver = driver,
                        filename = filename,
                        description = f"Failed test: {item.nodeid}"
                    )

                    # 将截图路径添加到allure报告中
                    import allure
                    allure.attach.file(
                        screenshot_path,
                        name = f"Screenshot_{timestamp}",
                        attachment_type = allure.attachment_type.PNG
                    )

                    logger.info(f"测试失败截图已保存: {screenshot_path}")
            except Exception as e:
                logger.error(f"捕获测试失败截图时发生错误: {str(e)}")

    # 记录测试结果到日志
    if report.when == "call":
        logger.info(
            f"测试结果: {item.nodeid} - "
            f"{'通过' if report.passed else '失败' if report.failed else '跳过'} - "
            f"耗时: {report.duration:.2f}秒"
        )


# 钩子函数：测试收集完成
@pytest.hookimpl(tryfirst = True)
def pytest_collection_modifyitems(items, config):
    """
    测试收集完成后的钩子函数
    可以用来重新排序测试用例、过滤测试用例等
    """
    # 获取命令行中的标记
    mark = config.getoption("-m")
    if mark:
        logger.info(f"执行带标记的测试: {mark}")

    # 计算不同类型的测试用例数量
    api_count = sum(1 for item in items if "api" in [mark.name for mark in item.iter_markers()])
    web_count = sum(1 for item in items if "web" in [mark.name for mark in item.iter_markers()])
    app_count = sum(1 for item in items if "app" in [mark.name for mark in item.iter_markers()])
    performance_count = sum(1 for item in items if "performance" in [mark.name for mark in item.iter_markers()])
    smoke_count = sum(1 for item in items if "smoke" in [mark.name for mark in item.iter_markers()])

    logger.info(
        f"测试用例收集完成: "
        f"总计 {len(items)} 个, "
        f"API测试 {api_count} 个, "
        f"Web测试 {web_count} 个, "
        f"APP测试 {app_count} 个, "
        f"性能测试 {performance_count} 个, "
        f"冒烟测试 {smoke_count} 个"
    )


# 钩子函数：测试会话开始
@pytest.hookimpl(tryfirst = True)
def pytest_sessionstart(session):
    """
    测试会话开始时的钩子函数
    """
    # 确保所有必要的目录存在
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))

    # 使用绝对路径替代配置属性
    data_dir = os.path.join(project_root, 'data')
    log_dir = os.path.join(project_root, 'logs')
    report_dir = os.path.join(project_root, 'reports')

    directories = [
        log_dir,
        report_dir,
        data_dir
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok = True)
            logger.info(f"创建目录: {directory}")

    logger.info("=" * 80)
    logger.info(f"测试会话开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"项目名称: OmniTest")
    logger.info(f"环境: test")  # 使用默认环境值，避免config属性错误
    logger.info("=" * 80)


# 钩子函数：测试会话结束
@pytest.hookimpl(trylast = True)
def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束时的钩子函数
    """
    logger.info("=" * 80)
    logger.info(f"测试会话结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"退出状态: {exitstatus}")

    # 统计测试结果
    test_stats = {
        "总用例数": session.testscollected,
        "失败": session.testsfailed if session.testsfailed is not None else 0,
        "跳过": session.skippedcount if hasattr(session, 'skippedcount') else 0
    }

    # 重新计算通过的用例数
    test_stats["通过"] = test_stats["总用例数"] - test_stats["失败"] - test_stats["跳过"]

    # 记录统计信息
    logger.info("测试结果统计:")
    for key, value in test_stats.items():
        logger.info(f"  {key}: {value}")

    # 计算通过率
    if test_stats["总用例数"] > 0:
        pass_rate = (test_stats["通过"] / test_stats["总用例数"]) * 100
        logger.info(f"测试通过率: {pass_rate:.2f}%")

    logger.info("=" * 80)


# 钩子函数：添加自定义命令行参数
def pytest_addoption(parser):
    """
    添加自定义命令行参数
    """
    # 环境参数
    parser.addoption(
        "--env",
        action = "store",
        default = "dev",
        choices = ["dev", "test", "staging", "prod"],
        help = "指定测试环境: dev(默认), test, staging, prod"
    )

    # 浏览器参数（Web测试）
    parser.addoption(
        "--browser",
        action = "store",
        default = "chrome",
        choices = ["chrome", "firefox", "edge", "safari"],
        help = "指定浏览器: chrome(默认), firefox, edge, safari"
    )

    # 设备类型参数（App测试）
    parser.addoption(
        "--device",
        action = "store",
        default = "android",
        choices = ["android", "ios"],
        help = "指定设备类型: android(默认), ios"
    )

    # Appium服务参数
    parser.addoption(
        "--appium-host",
        action = "store",
        default = "127.0.0.1",
        help = "Appium服务主机地址"
    )

    parser.addoption(
        "--appium-port",
        action = "store",
        default = "4723",
        type = int,
        help = "Appium服务端口"
    )

    # 是否启用Appium服务
    parser.addoption(
        "--start-appium",
        action = "store_true",
        default = False,
        help = "自动启动Appium服务"
    )

    # 性能测试参数
    parser.addoption(
        "--concurrency",
        action = "store",
        default = "1",
        type = int,
        help = "Locust并发用户数"
    )


@pytest.fixture(scope = "session")
def env(request):
    """
    测试环境
    
    Args:
        request: pytest request对象
        
    Returns:
        str: 环境名称
    """
    env_name = request.config.getoption("--env")
    logger.info(f"当前测试环境: {env_name}")
    return env_name


@pytest.fixture(scope = "session")
def browser(request):
    """
    浏览器类型
    
    Args:
        request: pytest request对象
        
    Returns:
        str: 浏览器名称
    """
    browser_name = request.config.getoption("--browser")
    logger.info(f"当前浏览器: {browser_name}")
    return browser_name


@pytest.fixture(scope = "session")
def device_type(request):
    """
    设备类型
    
    Args:
        request: pytest request对象
        
    Returns:
        str: 设备类型
    """
    device = request.config.getoption("--device")
    logger.info(f"当前设备类型: {device}")
    return device


@pytest.fixture(scope = "session")
def appium_server(request):
    """
    Appium服务器配置
    
    Args:
        request: pytest request对象
        
    Returns:
        tuple: (host, port)
    """
    host = request.config.getoption("--appium-host")
    port = request.config.getoption("--appium-port")
    logger.info(f"Appium服务器: {host}:{port}")
    return (host, port)


@pytest.fixture(scope = "session")
def start_appium(request):
    """
    是否自动启动Appium服务
    
    Args:
        request: pytest request对象
        
    Returns:
        bool: 是否启动
    """
    return request.config.getoption("--start-appium")


@pytest.fixture(scope = "session")
def concurrency(request):
    """
    Locust并发用户数
    
    Args:
        request: pytest request对象
        
    Returns:
        int: 并发用户数
    """
    return request.config.getoption("--concurrency")


# 测试跳过相关的fixture
@pytest.fixture(scope = "function")
def skip_if_not_api(request):
    """
    如果不是API测试,则跳过
    """
    if "api" not in request.node.keywords:
        pytest.skip("此测试仅适用于API测试")


@pytest.fixture(scope = "function")
def skip_if_not_web(request):
    """
    如果不是Web测试,则跳过
    """
    if "web" not in request.node.keywords:
        pytest.skip("此测试仅适用于Web测试")


@pytest.fixture(scope = "function")
def skip_if_not_app(request):
    """
    如果不是App测试,则跳过
    """
    if "app" not in request.node.keywords:
        pytest.skip("此测试仅适用于App测试")


# 测试数据相关的fixture
@pytest.fixture(scope = "function")
def test_data(request, data_handler):
    """
    根据测试用例名称自动加载对应的测试数据
    数据文件应该放在data目录下,命名格式为：模块名_类名_方法名.json/yaml
    
    Args:
        request: pytest request对象
        data_handler: 数据处理工具实例
        
    Returns:
        dict: 测试数据,如果没有找到数据文件则返回空字典
    """
    # 获取测试用例信息
    module_name = request.module.__name__.split(".")[-1]
    class_name = request.cls.__name__ if request.cls else ""
    method_name = request.node.name.split("[")[0]  # 去除参数化部分

    # 构建可能的数据文件路径
    possible_filenames = []

    if class_name:
        # 类方法格式: 模块名_类名_方法名
        possible_filenames.append(f"{module_name}_{class_name}_{method_name}")
        # 另一种格式: 类名_方法名
        possible_filenames.append(f"{class_name}_{method_name}")
    else:
        # 函数格式: 模块名_方法名
        possible_filenames.append(f"{module_name}_{method_name}")
        # 另一种格式: 方法名
        possible_filenames.append(f"{method_name}")

    # 支持的数据格式
    extensions = [".json", ".yaml", ".yml"]

    # 尝试加载数据
    for filename in possible_filenames:
        for ext in extensions:
            try:
                data_path = os.path.join(config.DATA_DIR, filename + ext)
                if os.path.exists(data_path):
                    data = data_handler.load_data(data_path)
                    logger.info(f"已加载测试数据: {data_path}")
                    return data
            except Exception as e:
                logger.debug(f"加载数据文件 {filename}{ext} 失败: {str(e)}")

    # 如果没有找到数据文件,返回空字典
    logger.debug(f"未找到测试数据文件: {module_name}_{class_name}_{method_name}")
    return {}


# 错误处理相关的fixture
@pytest.fixture(scope = "function")
def handle_api_errors():
    """
    处理API相关错误的fixture
    """
    try:
        yield
    except Exception as e:
        logger.error(f"API测试执行过程中发生错误: {str(e)}")
        # 可以在这里添加额外的错误处理逻辑
        raise


@pytest.fixture(scope = "function")
def handle_web_errors():
    """
    处理Web相关错误的fixture
    """
    try:
        yield
    except Exception as e:
        logger.error(f"Web测试执行过程中发生错误: {str(e)}")
        # 可以在这里添加额外的错误处理逻辑
        raise


@pytest.fixture(scope = "function")
def handle_app_errors():
    """
    处理App相关错误的fixture
    """
    try:
        yield
    except Exception as e:
        logger.error(f"App测试执行过程中发生错误: {str(e)}")
        # 可以在这里添加额外的错误处理逻辑
        raise


# 自定义标记相关的处理
@pytest.fixture(autouse = True)
def handle_smoke_tests(request):
    """
    处理冒烟测试标记
    可以在这里添加冒烟测试特有的处理逻辑
    """
    if "smoke" in request.node.keywords:
        logger.info(f"执行冒烟测试: {request.node.nodeid}")
    yield


# 测试报告相关的fixture
@pytest.fixture(scope = "function")
def allure_environment(request, env, browser, device_type):
    """
    设置Allure报告的环境信息
    
    Args:
        request: pytest request对象
        env: 环境
        browser: 浏览器
        device_type: 设备类型
    """
    import allure

    # 设置环境信息
    allure.environment(
        环境 = env,
        浏览器 = browser if browser else "N/A",
        设备类型 = device_type if device_type else "N/A",
        项目 = config.PROJECT_NAME,
        测试时间 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    yield
