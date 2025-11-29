"""
-------------------------------------------------
File:           usage_example.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
OmniTest框架编程API使用示例
-------------------------------------------------
"""

# 导入OmniTest框架
from main import OmniTest, ot
# 导入logger
from utils.logger_util import logger


def example_basic_usage():
    """基本用法示例"""
    logger.info("\n=== 基本用法示例 ===")
    
    # 创建OmniTest实例
    omni_test = OmniTest()
    
    # 运行API测试
    omni_test.api()
    
    # 运行特定的Web测试文件
    omni_test.web(test_file="test_login.py")
    
    # 运行带标记的App测试
    omni_test.app(markers="smoke")
    
    # 运行性能测试
    # omni_test.performance("test_api_load.py", users=200)
    
    # 生成并打开报告
    omni_test.report()


def example_chain_calls():
    """链式调用示例"""
    logger.info("\n=== 链式调用示例 ===")
    
    # 使用链式调用
    ot.api(test_file="test_user.py")\
       .web(test_dir="auth", markers="critical")\
       .report(open=False)
    
    # 只清理报告
    ot.clean()
    
    # 只运行测试不生成报告
    ot.web(test_dir="checkout", auto_report=False)


def example_custom_options():
    """自定义选项示例"""
    logger.info("\n=== 自定义选项示例 ===")
    
    # 不自动清理报告,手动控制流程
    omni_test = OmniTest()
    omni_test.clean()  # 先清理
    omni_test.api(auto_clean=False)  # 运行API测试但不自动清理
    omni_test.web(auto_clean=False)  # 运行Web测试但不自动清理
    omni_test.report()  # 生成并打开一个包含所有测试的报告


def example_all_tests():
    """运行所有测试示例"""
    logger.info("\n=== 运行所有测试示例 ===")
    
    # 运行所有类型的测试
    ot.all()


def example_report_only():
    """只生成或只打开报告示例"""
    logger.info("\n=== 报告相关操作示例 ===")
    
    # 只生成报告
    ot.report(open=False)
    
    # 只打开报告
    ot.report(generate=False)


if __name__ == "__main__":
    # 运行各种示例
    example_basic_usage()
    example_chain_calls()
    example_custom_options()
    # example_all_tests()  # 取消注释以运行所有测试
    # example_report_only()  # 取消注释以测试报告功能