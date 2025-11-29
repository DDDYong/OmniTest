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
import shutil
import subprocess
import sys

# 确保项目根目录在sys.path中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入项目模块
from utils.path_util import path_util
from utils.logger_util import logger
from utils.decorator_util import timing


class TestRunner:
    """
    测试运行器类
    提供不同类型测试的运行功能
    """

    @staticmethod
    def clean_reports() -> None:
        """
        清理测试报告目录
        """
        # 清理allure结果目录
        allure_results_dir = path_util.get_allure_results_dir()
        if os.path.exists(allure_results_dir):
            for file in os.listdir(allure_results_dir):
                file_path = os.path.join(allure_results_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        # 清理截图目录
        screenshots_dir = path_util.get_screenshots_dir()
        if os.path.exists(screenshots_dir):
            for file in os.listdir(screenshots_dir):
                file_path = os.path.join(screenshots_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        logger.info("测试报告目录已清理")

    @staticmethod
    @timing
    def run_api_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
        """
        运行API测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            
        Returns:
            int: 测试执行的退出代码
        """
        logger.info("开始运行API测试...")

        # 构建pytest命令
        cmd = [sys.executable, '-m', 'pytest']

        # 添加测试路径
        if test_file:
            cmd.append(os.path.join(path_util.get_api_cases_dir(), test_file))
        elif test_dir:
            cmd.append(os.path.join(path_util.get_api_cases_dir(), test_dir))
        else:
            cmd.append(path_util.get_api_cases_dir())

        # 添加标记
        if markers:
            cmd.extend(['-m', markers])

        # 添加通用参数
        cmd.extend(['-v', '--alluredir', path_util.get_allure_results_dir()])

        # 执行测试
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd = path_util.get_project_root(), text = True)
            return result.returncode
        except Exception as e:
            logger.error(f"运行API测试失败: {str(e)}")
            return 1

    @staticmethod
    @timing
    def run_web_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
        """
        运行Web测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            
        Returns:
            int: 测试执行的退出代码
        """
        logger.info("开始运行Web测试...")

        # 构建pytest命令
        cmd = [sys.executable, '-m', 'pytest']

        # 添加测试路径
        if test_file:
            cmd.append(os.path.join(path_util.get_web_cases_dir(), test_file))
        elif test_dir:
            cmd.append(os.path.join(path_util.get_web_cases_dir(), test_dir))
        else:
            cmd.append(path_util.get_web_cases_dir())

        # 添加标记
        if markers:
            cmd.extend(['-m', markers])

        # 添加通用参数
        cmd.extend(['-v', '--alluredir', path_util.get_allure_results_dir()])

        # 执行测试
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd = path_util.get_project_root(), text = True)
            return result.returncode
        except Exception as e:
            logger.error(f"运行Web测试失败: {str(e)}")
            return 1

    @staticmethod
    @timing
    def run_app_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
        """
        运行APP测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            
        Returns:
            int: 测试执行的退出代码
        """
        logger.info("开始运行APP测试...")

        # 构建pytest命令
        cmd = [sys.executable, '-m', 'pytest']

        # 添加测试路径
        if test_file:
            cmd.append(os.path.join(path_util.get_app_cases_dir(), test_file))
        elif test_dir:
            cmd.append(os.path.join(path_util.get_app_cases_dir(), test_dir))
        else:
            cmd.append(path_util.get_app_cases_dir())

        # 添加标记
        if markers:
            cmd.extend(['-m', markers])

        # 添加通用参数
        cmd.extend(['-v', '--alluredir', path_util.get_allure_results_dir()])

        # 执行测试
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd = path_util.get_project_root(), text = True)
            return result.returncode
        except Exception as e:
            logger.error(f"运行APP测试失败: {str(e)}")
            return 1

    @staticmethod
    @timing
    def run_performance_tests(test_file: str, users: int = 100, spawn_rate: int = 10, run_time: str = '5m') -> int:
        """
        运行性能测试
        
        Args:
            test_file: 测试文件
            users: 用户数量
            spawn_rate: 每秒生成的用户数
            run_time: 运行时间
            
        Returns:
            int: 测试执行的退出代码
        """
        logger.info("开始运行性能测试...")

        # 构建locust命令
        test_path = os.path.join(path_util.get_performance_cases_dir(), test_file)
        cmd = [
            'locust',
            '-f', test_path,
            '--users', str(users),
            '--spawn-rate', str(spawn_rate),
            '--run-time', run_time,
            '--headless',
            '--html', os.path.join(path_util.get_reports_dir(), 'locust_report.html')
        ]

        # 执行测试
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd = path_util.get_project_root(), text = True)
            return result.returncode
        except Exception as e:
            logger.error(f"运行性能测试失败: {str(e)}")
            return 1

    @staticmethod
    def run_all_tests() -> int:
        """
        运行所有测试
        
        Returns:
            int: 测试执行的退出代码
        """
        logger.info("开始运行所有测试...")

        # 构建pytest命令
        cmd = [
            sys.executable, '-m', 'pytest',
            path_util.get_cases_dir(),
            '-v', '--alluredir', path_util.get_allure_results_dir()
        ]

        # 执行测试
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd = path_util.get_project_root(), text = True)
            return result.returncode
        except Exception as e:
            logger.error(f"运行所有测试失败: {str(e)}")
            return 1

    @staticmethod
    def generate_allure_report() -> bool:
        """
        生成Allure报告
        
        Returns:
            bool: 是否生成成功
        """
        logger.info("开始生成Allure报告...")

        # 清理旧报告
        if os.path.exists(path_util.get_allure_report_dir()):
            shutil.rmtree(path_util.get_allure_report_dir())

        # 构建allure命令
        cmd = ['allure', 'generate', path_util.get_allure_results_dir(), '-o', path_util.get_allure_report_dir(),
               '--clean']

        # 执行命令
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            subprocess.run(cmd, check = True, cwd = path_util.get_project_root(), text = True)
            logger.info(f"Allure报告已生成: {path_util.get_allure_report_dir()}")
            return True
        except Exception as e:
            logger.error(f"生成Allure报告失败: {str(e)}")
            return False

    @staticmethod
    def open_allure_report() -> bool:
        """
        打开Allure报告
        
        Returns:
            bool: 是否打开成功
        """
        logger.info("开始打开Allure报告...")

        # 检查报告是否存在
        if not os.path.exists(os.path.join(path_util.get_allure_report_dir(), 'index.html')):
            logger.warning("Allure报告不存在,请先生成报告")
            return False

        # 构建allure命令
        cmd = ['allure', 'open', path_util.get_allure_report_dir()]

        # 执行命令
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            subprocess.Popen(cmd, cwd = path_util.get_project_root())
            return True
        except Exception as e:
            logger.error(f"打开Allure报告失败: {str(e)}")
            return False


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

    return parser.parse_args()


def main():
    """
    主函数
    """
    # 解析命令行参数
    args = parse_arguments()

    # 初始化运行器
    runner = TestRunner()

    # 处理不同命令
    if args.command == 'all':
        runner.clean_reports()
        exit_code = runner.run_all_tests()
        if exit_code == 0:
            runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'api':
        runner.clean_reports()
        exit_code = runner.run_api_tests(args.dir, args.file, args.markers)
        if exit_code == 0:
            runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'web':
        runner.clean_reports()
        exit_code = runner.run_web_tests(args.dir, args.file, args.markers)
        if exit_code == 0:
            runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'app':
        runner.clean_reports()
        exit_code = runner.run_app_tests(args.dir, args.file, args.markers)
        if exit_code == 0:
            runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'performance':
        exit_code = runner.run_performance_tests(args.file, args.users, args.spawn_rate, args.run_time)
        sys.exit(exit_code)

    elif args.command == 'report':
        if args.generate or not args.open:
            runner.generate_allure_report()
        if args.open or not args.generate:
            runner.open_allure_report()
        sys.exit(0)

    elif args.command == 'clean':
        runner.clean_reports()
        sys.exit(0)

    else:
        # 如果没有指定命令,显示帮助信息
        # 导入logger
        from utils.logger_util import logger

        logger.info("请指定要执行的命令")
        logger.info("使用方法示例:")
        logger.info(f"  python {os.path.basename(__file__)} api                 # 运行所有API测试")
        logger.info(f"  python {os.path.basename(__file__)} web --file test_login.py  # 运行特定Web测试")
        logger.info(f"  python {os.path.basename(__file__)} app --markers smoke     # 运行冒烟测试")
        logger.info(f"  python {os.path.basename(__file__)} performance test_api.py --users 500  # 运行性能测试")
        logger.info(f"  python {os.path.basename(__file__)} report             # 生成并打开报告")
        logger.info(f"  python {os.path.basename(__file__)} clean              # 清理测试报告")
        sys.exit(1)


if __name__ == '__main__':
    main()
