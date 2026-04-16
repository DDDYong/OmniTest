"""
-------------------------------------------------
File:           run.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
OmniTest项目入口文件,提供命令行接口运行不同类型的测试,包括API、Web、App和性能测试
-------------------------------------------------
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional

# 确保项目根目录在sys.path中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入拆分后的核心模块
from utils.runner import test_runner
from utils.reporting import allure_report
from utils.packaging import requirements_manager
from utils.logger import logger


@dataclass(frozen = True)
class ExecutionRequest:
    command: str
    test_dir: Optional[str] = None
    test_file: Optional[str] = None
    markers: Optional[str] = None
    num_workers: int = 2
    html_report: bool = False
    users: int = 100
    spawn_rate: int = 10
    run_time: str = '5m'
    auto_clean: bool = True
    auto_report: bool = True
    report_generate: bool = True
    report_open: bool = True
    package_name: Optional[str] = None
    package_version: Optional[str] = None


def execute_request(request: "ExecutionRequest", runner: "TestRunner", include_side_effects: bool = True) -> int:
    invalid_code = getattr(TestRunner, 'INVALID_TEST_TARGET_EXIT_CODE', 4)

    if request.command == 'all':
        if include_side_effects and request.auto_clean:
            runner.clean_reports()
        exit_code = runner.run_all_tests()
        if include_side_effects and request.auto_report:
            runner.generate_allure_report()
            runner.generate_report_index()
        return exit_code

    if request.command == 'api':
        if include_side_effects and request.auto_clean:
            runner.clean_reports()
        exit_code = runner.run_api_tests(request.test_dir, request.test_file, request.markers)
        if include_side_effects and request.auto_report and exit_code != invalid_code:
            runner.generate_allure_report()
            runner.generate_report_index()
        return exit_code

    if request.command == 'web':
        if include_side_effects and request.auto_clean:
            runner.clean_reports()
        exit_code = runner.run_web_tests(request.test_dir, request.test_file, request.markers)
        if include_side_effects and request.auto_report and exit_code != invalid_code:
            runner.generate_allure_report()
            runner.generate_report_index()
        return exit_code

    if request.command == 'app':
        if include_side_effects and request.auto_clean:
            runner.clean_reports()
        exit_code = runner.run_app_tests(request.test_dir, request.test_file, request.markers)
        if include_side_effects and request.auto_report and exit_code != invalid_code:
            runner.generate_allure_report()
            runner.generate_report_index()
        return exit_code

    if request.command == 'parallel':
        if include_side_effects and request.auto_clean:
            runner.clean_reports()
        exit_code = runner.run_parallel_tests(
            request.test_dir,
            request.test_file,
            request.markers,
            request.num_workers,
            request.html_report,
        )
        if include_side_effects and request.auto_report and exit_code != invalid_code:
            runner.generate_allure_report()
            runner.generate_report_index()
        return exit_code

    if request.command == 'performance':
        return runner.run_performance_tests(request.test_file, request.users, request.spawn_rate, request.run_time)

    if request.command == 'report':
        if include_side_effects and request.report_generate:
            runner.generate_allure_report()
            runner.generate_report_index()
        if include_side_effects and request.report_open:
            runner.open_allure_report()
        return 0

    if request.command == 'clean':
        if include_side_effects:
            runner.clean_reports()
        return 0

    if request.command == 'package-update-req':
        success = runner.update_requirements()
        return 0 if success else 1

    if request.command == 'package-add':
        success = runner.add_package_to_requirements(request.package_name, request.package_version)
        return 0 if success else 1

    raise ValueError(f'不支持的命令: {request.command}')


def build_execution_request(args: argparse.Namespace) -> Optional[ExecutionRequest]:
    if args.command == 'all':
        return ExecutionRequest(command = 'all')
    if args.command == 'api':
        return ExecutionRequest(command = 'api', test_dir = args.dir, test_file = args.file, markers = args.markers)
    if args.command == 'web':
        return ExecutionRequest(command = 'web', test_dir = args.dir, test_file = args.file, markers = args.markers)
    if args.command == 'app':
        return ExecutionRequest(command = 'app', test_dir = args.dir, test_file = args.file, markers = args.markers)
    if args.command == 'parallel':
        return ExecutionRequest(
            command = 'parallel',
            test_dir = args.dir,
            test_file = args.file,
            markers = args.markers,
            num_workers = args.workers,
            html_report = args.html,
        )
    if args.command == 'performance':
        return ExecutionRequest(
            command = 'performance',
            test_file = args.file,
            users = args.users,
            spawn_rate = args.spawn_rate,
            run_time = args.run_time,
            auto_clean = False,
            auto_report = False,
        )
    if args.command == 'report':
        return ExecutionRequest(
            command = 'report',
            auto_clean = False,
            auto_report = False,
            report_generate = args.generate or not args.open,
            report_open = args.open or not args.generate,
        )
    if args.command == 'clean':
        return ExecutionRequest(command = 'clean', auto_clean = False, auto_report = False)
    if args.command == 'package':
        if args.pkg_command == 'update-req':
            return ExecutionRequest(command = 'package-update-req', auto_clean = False, auto_report = False)
        if args.pkg_command == 'add':
            return ExecutionRequest(
                command = 'package-add',
                auto_clean = False,
                auto_report = False,
                package_name = args.package,
                package_version = args.version,
            )
    return None

class TestRunner:
    """
    为了向后兼容保留的测试运行器类.
    所有实际逻辑已拆分至 utils/runner, utils/reporting, utils/packaging 中.
    """
    INVALID_TEST_TARGET_EXIT_CODE = test_runner.INVALID_TEST_TARGET_EXIT_CODE

    @staticmethod
    def clean_reports(days_to_keep: int = 7) -> None:
        """
        清理测试报告

        Args:
            days_to_keep: 保留多少天的报告，默认7天
        """
        test_runner.clean_reports(days_to_keep)
        logger.info("新测试报告目录已准备好(保留历史报告)")

    @staticmethod
    def generate_report_index() -> str:
        """
        生成报告索引页面

        Returns:
            str: 索引页面路径
        """
        return test_runner.generate_report_index()

    @staticmethod
    def run_api_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
        return test_runner.run_api_tests(test_dir, test_file, markers)

    @staticmethod
    def run_web_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
        return test_runner.run_web_tests(test_dir, test_file, markers)

    @staticmethod
    def run_app_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
        return test_runner.run_app_tests(test_dir, test_file, markers)

    @staticmethod
    def run_parallel_tests(test_dir: str = None, test_file: str = None, markers: str = 'parallel',
                           num_workers: int = 2, html_report: bool = False) -> int:
        return test_runner.run_parallel_tests(test_dir, test_file, markers, num_workers, html_report)

    @staticmethod
    def run_performance_tests(test_file: str, users: int = 100, spawn_rate: int = 10, run_time: str = '5m') -> int:
        return test_runner.run_performance_tests(test_file, users, spawn_rate, run_time)

    @staticmethod
    def run_all_tests() -> int:
        return test_runner.run_all_tests()

    @staticmethod
    def generate_allure_report(serve: bool = True, wait_for_enter: bool = True) -> bool:
        return allure_report.generate_allure_report(serve, wait_for_enter)

    @staticmethod
    def open_allure_report() -> bool:
        return allure_report.open_allure_report()

    @staticmethod
    def update_requirements() -> bool:
        return requirements_manager.update_requirements()

    @staticmethod
    def add_package_to_requirements(package_name: str, version: str = None) -> bool:
        return requirements_manager.add_package_to_requirements(package_name, version)



def parse_arguments():
    """
    解析命令行参数

    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description = 'OmniTest 自动化测试运行器')

    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest = 'command', help = '可用命令')

    # 所有测试命令
    parser_all = subparsers.add_parser('all', help = '运行所有测试')

    # API测试命令
    parser_api = subparsers.add_parser('api', help = '运行API测试')
    parser_api.add_argument('--dir', help = 'API测试目录')
    parser_api.add_argument('--file', help = 'API测试文件')
    parser_api.add_argument('--markers', help = '测试标记')

    # Web测试命令
    parser_web = subparsers.add_parser('web', help = '运行Web测试')
    parser_web.add_argument('--dir', help = 'Web测试目录')
    parser_web.add_argument('--file', help = 'Web测试文件')
    parser_web.add_argument('--markers', help = '测试标记')

    # APP测试命令
    parser_app = subparsers.add_parser('app', help = '运行APP测试')
    parser_app.add_argument('--dir', help = 'APP测试目录')
    parser_app.add_argument('--file', help = 'APP测试文件')
    parser_app.add_argument('--markers', help = '测试标记')

    # 并行测试命令
    parser_parallel = subparsers.add_parser('parallel', help = '运行并行测试')
    parser_parallel.add_argument('--dir', help = '测试目录')
    parser_parallel.add_argument('--file', help = '测试文件')
    parser_parallel.add_argument('--markers', default = 'parallel', help = '测试标记 (默认: parallel)')
    parser_parallel.add_argument('--workers', '-n', type = int, default = 2, help = 'Worker数量 (默认: 2)')
    parser_parallel.add_argument('--html', action = 'store_true', help = '生成HTML报告')

    # 性能测试命令
    parser_perf = subparsers.add_parser('performance', help = '运行性能测试')
    parser_perf.add_argument('file', help = '性能测试文件')
    parser_perf.add_argument('--users', type = int, default = 100, help = '用户数量')
    parser_perf.add_argument('--spawn-rate', type = int, default = 10, help = '每秒生成的用户数')
    parser_perf.add_argument('--run-time', default = '5m', help = '运行时间')

    # 报告命令
    parser_report = subparsers.add_parser('report', help = '生成并打开报告')
    parser_report.add_argument('--generate', action = 'store_true', help = '只生成报告')
    parser_report.add_argument('--open', action = 'store_true', help = '只打开报告')

    # 清理命令
    parser_clean = subparsers.add_parser('clean', help = '清理测试报告')

    # 包管理命令
    parser_pkg = subparsers.add_parser('package', help = '包管理命令')
    pkg_subparsers = parser_pkg.add_subparsers(dest = 'pkg_command', help = '包管理子命令')

    # 更新 requirements 命令
    pkg_subparsers.add_parser('update-req', help = '更新 requirements.txt')

    # 添加包命令
    parser_add = pkg_subparsers.add_parser('add', help = '添加包到 requirements.txt')
    parser_add.add_argument('package', help = '包名')
    parser_add.add_argument('--version', help = '指定版本号')

    return parser.parse_args()


def main():
    """
    主函数
    """
    # 解析命令行参数
    args = parse_arguments()

    # 初始化运行器
    runner = TestRunner()

    request = build_execution_request(args)
    if request is not None:
        sys.exit(execute_request(request, runner))

    else:
        # 如果没有指定命令,显示帮助信息
        # 导入logger
        from utils.logger import logger

        logger.info("请指定要执行的命令")
        logger.info("使用方法示例:")
        logger.info(f"  python {os.path.basename(__file__)} api                 # 运行所有API测试")
        logger.info(f"  python {os.path.basename(__file__)} web --file test_login.py  # 运行特定Web测试")
        logger.info(f"  python {os.path.basename(__file__)} app --markers smoke     # 运行冒烟测试")
        logger.info(f"  python {os.path.basename(__file__)} parallel              # 运行并行测试 (2 workers)")
        logger.info(f"  python {os.path.basename(__file__)} parallel --workers 3  # 运行并行测试 (3 workers)")
        logger.info(f"  python {os.path.basename(__file__)} parallel --html       # 运行并行测试并生成HTML报告")
        logger.info(f"  python {os.path.basename(__file__)} parallel --file test_app_login.py  # 运行特定App测试")
        logger.info(f"  python {os.path.basename(__file__)} performance test_api.py --users 500  # 运行性能测试")
        logger.info(f"  python {os.path.basename(__file__)} report             # 生成并打开报告")
        logger.info(f"  python {os.path.basename(__file__)} clean              # 清理测试报告")
        logger.info(f"  python {os.path.basename(__file__)} package update-req  # 更新 requirements.txt")
        logger.info(f"  python {os.path.basename(__file__)} package add requests --version 2.31.0  # 添加指定包")
        sys.exit(1)


if __name__ == '__main__':
    main()
