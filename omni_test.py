"""
-------------------------------------------------
File:           omni_test.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
OmniTest自动化测试框架的API接口模块,提供简洁的编程API接口来运行各类测试
-------------------------------------------------
"""

import os
import sys

# 确保项目根目录在sys.path中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入TestRunner类
from run import TestRunner
# 导入日志工具
from utils.logger_util import logger


class OmniTest:
    """
    OmniTest框架的主要API类
    提供简洁的编程接口来运行各类测试
    """

    def __init__(self):
        """初始化OmniTest实例"""
        self.runner = TestRunner()

    def clean(self):
        """清理测试报告目录"""

        logger.info("=" * 60)
        logger.info("开始清理测试报告和截图")
        try:
            self.runner.clean_reports()
            logger.info("测试报告和截图清理完成")
        except Exception as e:
            logger.error(f"清理测试报告失败: {str(e)}", exc_info = True)
        logger.info("=" * 60)
        return self

    def api(self, test_dir = None, test_file = None, markers = None, auto_clean = True, auto_report = True):
        """
        运行API测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告
            
        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """

        logger.info("=" * 60)
        logger.info("开始执行API测试")
        logger.info(f"测试目录: {test_dir}")
        logger.info(f"测试文件: {test_file}")
        logger.info(f"测试标记: {markers}")
        logger.info(f"自动清理: {auto_clean}")
        logger.info(f"自动报告: {auto_report}")
        logger.info("=" * 60)

        # 清理测试报告
        if auto_clean:
            logger.info("执行自动清理报告操作")
            self.clean()
        else:
            logger.info("跳过自动清理报告")

        # 运行API测试
        logger.info(f"正在运行API测试 - 开始执行测试用例")
        try:
            exit_code = self.runner.run_api_tests(test_dir, test_file, markers)
            logger.info("API测试执行完成")

            # 生成报告
            if exit_code == 0 and auto_report:
                logger.info("准备自动生成测试报告")
                self.runner.generate_allure_report()
            elif exit_code != 0:
                logger.warning(f"API测试失败,退出码: {exit_code},跳过报告生成")
            else:
                logger.info("跳过自动生成报告")
        except Exception as e:
            logger.error(f"API测试执行失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self

    def web(self, test_dir = None, test_file = None, markers = None, auto_clean = True, auto_report = True):
        """
        运行Web测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告
            
        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """

        logger.info("=" * 60)
        logger.info("开始执行Web测试")
        logger.info(f"测试目录: {test_dir}")
        logger.info(f"测试文件: {test_file}")
        logger.info(f"测试标记: {markers}")
        logger.info(f"自动清理: {auto_clean}")
        logger.info(f"自动报告: {auto_report}")
        logger.info("=" * 60)

        # 清理测试报告
        if auto_clean:
            logger.info("执行自动清理报告操作")
            self.clean()
        else:
            logger.info("跳过自动清理报告")

        # 运行Web测试
        logger.info(f"正在运行Web测试 - 开始执行浏览器自动化测试")
        try:
            exit_code = self.runner.run_web_tests(test_dir, test_file, markers)
            logger.info("Web测试执行完成")

            # 生成报告
            if exit_code == 0 and auto_report:
                logger.info("准备自动生成测试报告")
                self.runner.generate_allure_report()
            elif exit_code != 0:
                logger.warning(f"Web测试失败,退出码: {exit_code},跳过报告生成")
            else:
                logger.info("跳过自动生成报告")
        except Exception as e:
            logger.error(f"Web测试执行失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self

    def app(self, test_dir = None, test_file = None, markers = None, auto_clean = True, auto_report = True):
        """
        运行App测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告
            
        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        logger.info("=" * 60)
        logger.info("开始执行App测试")
        logger.info(f"测试目录: {test_dir}")
        logger.info(f"测试文件: {test_file}")
        logger.info(f"测试标记: {markers}")
        logger.info(f"自动清理: {auto_clean}")
        logger.info(f"自动报告: {auto_report}")
        logger.info("=" * 60)

        # 清理测试报告
        if auto_clean:
            logger.info("执行自动清理报告操作")
            self.clean()
        else:
            logger.info("跳过自动清理报告")

        # 运行App测试
        logger.info(f"正在运行App测试 - 开始执行测试用例")
        try:
            exit_code = self.runner.run_app_tests(test_dir, test_file, markers)
            logger.info("App测试执行完成")

            # 生成报告
            if exit_code == 0 and auto_report:
                logger.info("准备自动生成测试报告")
                self.runner.generate_allure_report()
            elif exit_code != 0:
                logger.warning(f"App测试失败,退出码: {exit_code},跳过报告生成")
            else:
                logger.info("跳过自动生成报告")
        except Exception as e:
            logger.error(f"App测试执行失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self

    def performance(self, test_file, users = 100, spawn_rate = 10, run_time = '5m'):
        """
        运行性能测试
        
        Args:
            test_file: 测试文件
            users: 用户数量
            spawn_rate: 每秒生成的用户数
            run_time: 运行时间
            
        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        logger.info("=" * 60)
        logger.info("开始执行性能测试")
        logger.info(f"测试文件: {test_file}")
        logger.info(f"用户数量: {users}")
        logger.info(f"每秒生成用户数: {spawn_rate}")
        logger.info(f"运行时间: {run_time}")
        logger.info("=" * 60)

        try:
            logger.info("正在启动性能测试")
            self.runner.run_performance_tests(test_file, users, spawn_rate, run_time)
            logger.info("性能测试执行完成")
        except Exception as e:
            logger.error(f"性能测试执行失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self

    def all(self, auto_clean = True, auto_report = True):
        """
        运行所有测试
        
        Args:
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告
            
        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        logger.info("=" * 60)
        logger.info("开始执行所有测试")
        logger.info(f"自动清理: {auto_clean}")
        logger.info(f"自动报告: {auto_report}")
        logger.info("=" * 60)

        # 清理测试报告
        if auto_clean:
            logger.info("执行自动清理报告操作")
            self.clean()
        else:
            logger.info("跳过自动清理报告")

        # 运行所有测试
        logger.info("正在运行所有测试套件")
        try:
            exit_code = self.runner.run_all_tests()
            logger.info(f"所有测试执行完成,退出码: {exit_code}")

            # 生成报告
            if exit_code == 0 and auto_report:
                logger.info("准备自动生成测试报告")
                self.runner.generate_allure_report()
            elif exit_code != 0:
                logger.warning(f"测试失败,退出码: {exit_code},跳过报告生成")
            else:
                logger.info("跳过自动生成报告")
        except Exception as e:
            logger.error(f"运行所有测试失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self

    def report(self, generate = True, open = True):
        """
        生成和/或打开Allure报告
        
        Args:
            generate: 是否生成报告
            open: 是否打开报告
            
        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """

        logger.info("=" * 60)
        logger.info("测试报告操作")
        logger.info(f"生成报告: {generate}")
        logger.info(f"打开报告: {open}")
        logger.info("=" * 60)

        try:
            if generate:
                logger.info("开始生成Allure报告")
                self.runner.generate_allure_report()
                logger.info("Allure报告生成完成")

            if open:
                logger.info("开始打开Allure报告")
                self.runner.open_allure_report()
                logger.info("Allure报告已打开")

            logger.info("测试报告操作完成")
        except Exception as e:
            logger.error(f"生成/打开测试报告失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self


# 创建全局实例以便直接导入使用
ot = OmniTest()
