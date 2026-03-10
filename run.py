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
        清理测试报告目录（不清理历史报告，只确保新报告目录是干净的）
        """
        logger.info("新测试报告目录已准备好（保留历史报告）")

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
        logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")

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

        # 添加通用参数 - 使用时间文件夹
        allure_dir = path_util.get_allure_results_dir(use_time_folder = True)
        cmd.extend(['-v', '--alluredir', allure_dir])
        logger.info(f"Allure报告结果目录设置为: {allure_dir}")

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
        logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")

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

        # 添加通用参数 - 使用时间文件夹
        cmd.extend(['-v', '--alluredir', path_util.get_allure_results_dir(use_time_folder = True)])

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
        logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")

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

        # 添加通用参数 - 使用时间文件夹
        cmd.extend(['-v', '--alluredir', path_util.get_allure_results_dir(use_time_folder = True)])

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
    def run_parallel_tests(test_dir: str = None, test_file: str = None, markers: str = 'parallel',
                           num_workers: int = 2, html_report: bool = False) -> int:
        """
        运行并行测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记，默认为 'parallel'
            num_workers: worker数量，默认为2
            html_report: 是否生成HTML报告
            
        Returns:
            int: 测试执行的退出代码
        """
        logger.info(f"开始运行并行测试 (workers={num_workers})...")
        logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")

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

        # 添加并行参数
        cmd.extend(['-n', str(num_workers)])

        # 添加通用参数（使用时间文件夹）
        cmd.extend(['-v', '--alluredir', path_util.get_allure_results_dir(use_time_folder = True)])

        # 添加HTML报告（如果需要）
        if html_report:
            html_report_path = os.path.join(path_util.get_logs_dir(), 'report_parallel.html')
            cmd.extend(['--html', html_report_path, '--self-contained-html'])

        # 执行测试
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd = path_util.get_project_root(), text = True)
            return result.returncode
        except Exception as e:
            logger.error(f"运行并行测试失败: {str(e)}")
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
        logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")

        # 构建pytest命令
        cmd = [
            sys.executable, '-m', 'pytest',
            path_util.get_cases_dir(),
            '-v', '--alluredir', path_util.get_allure_results_dir(use_time_folder = True)
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
        生成Allure报告（使用时间文件夹）
        
        Returns:
            bool: 是否生成成功
        """
        logger.info("开始生成Allure报告...")

        # 获取当前测试运行的时间文件夹路径
        allure_results_dir = path_util.get_allure_results_dir(use_time_folder = True)
        allure_report_dir = path_util.get_allure_report_dir(use_time_folder = True)

        logger.info(f"Allure结果目录: {allure_results_dir}")
        logger.info(f"Allure报告目录: {allure_report_dir}")

        # 清理旧报告（当前时间文件夹下的）
        if os.path.exists(allure_report_dir):
            shutil.rmtree(allure_report_dir)

        # 构建allure命令
        cmd = ['allure', 'generate', allure_results_dir, '-o', allure_report_dir,
               '--clean']

        # 执行命令
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            subprocess.run(cmd, check = True, cwd = path_util.get_project_root(), text = True)
            logger.info(f"Allure报告已生成: {allure_report_dir}")
            return True
        except Exception as e:
            logger.error(f"生成Allure报告失败: {str(e)}")
            return False

    @staticmethod
    def update_requirements() -> bool:
        """
        更新 requirements.txt 文件，保留注释信息

        Returns:
            bool: 是否更新成功
        """
        logger.info("开始更新 requirements.txt...")

        try:
            # 读取当前文件，保存注释
            comments = []
            requirements_path = os.path.join(path_util.get_project_root(), 'requirements.txt')

            try:
                with open(requirements_path, 'r', encoding = 'utf-8') as f:
                    for line in f:
                        if line.strip().startswith('#'):
                            comments.append(line)
                        else:
                            break  # 只保留文件头部的注释
            except FileNotFoundError:
                logger.info("requirements.txt 文件不存在，将创建新文件")

            # 获取当前环境的所有包
            result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'],
                capture_output = True, text = True, cwd = path_util.get_project_root())

            if result.returncode != 0:
                logger.error(f"获取包列表失败: {result.stderr}")
                return False

            # 写入 requirements.txt
            with open(requirements_path, 'w', encoding = 'utf-8') as f:
                # 写回注释
                for comment in comments:
                    f.write(comment)
                if comments and not comments[-1].endswith('\n'):
                    f.write('\n')

                # 写新的依赖
                f.write(result.stdout)

            logger.info(f"requirements.txt 已更新: {requirements_path}")
            return True

        except Exception as e:
            logger.error(f"更新 requirements.txt 失败: {str(e)}")
            return False

    @staticmethod
    def add_package_to_requirements(package_name: str, version: str = None) -> bool:
        """
        手动添加单个包到 requirements.txt
        
        Args:
            package_name: 包名
            version: 版本号（可选）
            
        Returns:
            bool: 是否添加成功
        """;
        logger.info(f"添加包到 requirements.txt: {package_name}")

        try:
            requirements_path = os.path.join(path_util.get_project_root(), 'requirements.txt')

            # 读取现有内容
            with open(requirements_path, 'r', encoding = 'utf-8') as f:
                lines = f.readlines()

            # 构造新的包条目
            if version:
                package_entry = f"{package_name}=={version}\n"
            else:
                package_entry = f"{package_name}\n"

            # 检查是否已存在
            package_exists = any(line.strip().startswith(package_name) for line in lines)

            if package_exists:
                logger.warning(f"包 {package_name} 已存在于 requirements.txt 中")
                return False

            # 添加到文件末尾
            lines.append(package_entry)

            # 写回文件
            with open(requirements_path, 'w', encoding = 'utf-8') as f:
                f.writelines(lines)

            logger.info(f"包 {package_name} 已添加到 requirements.txt")
            return True

        except Exception as e:
            logger.error(f"添加包到 requirements.txt 失败: {str(e)}")
            return False
    
    @staticmethod
    def open_allure_report() -> bool:
        """
        打开Allure报告（使用时间文件夹）
        
        Returns:
            bool: 是否打开成功
        """
        logger.info("开始打开Allure报告...")

        # 获取当前测试运行的时间文件夹路径
        allure_report_dir = path_util.get_allure_report_dir(use_time_folder = True)

        # 检查报告是否存在
        if not os.path.exists(os.path.join(allure_report_dir, 'index.html')):
            logger.warning(f"Allure报告不存在: {allure_report_dir}, 请先生成报告")
            return False

        # 构建allure命令
        cmd = ['allure', 'open', allure_report_dir]

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

    # 处理不同命令
    if args.command == 'all':
        runner.clean_reports()
        exit_code = runner.run_all_tests()
        runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'api':
        runner.clean_reports()
        exit_code = runner.run_api_tests(args.dir, args.file, args.markers)
        runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'web':
        runner.clean_reports()
        exit_code = runner.run_web_tests(args.dir, args.file, args.markers)
        runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'app':
        runner.clean_reports()
        exit_code = runner.run_app_tests(args.dir, args.file, args.markers)
        runner.generate_allure_report()
        sys.exit(exit_code)

    elif args.command == 'parallel':
        runner.clean_reports()
        exit_code = runner.run_parallel_tests(
            args.dir, args.file, args.markers, args.workers, args.html)
        runner.generate_allure_report()
        # 发送测试报告到企微/邮箱/飞书
        # notification_util.send_report_via_email()
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

    elif args.command == 'package':
        if args.pkg_command == 'update-req':
            success = runner.update_requirements()
            sys.exit(0 if success else 1)
        elif args.pkg_command == 'add':
            success = runner.add_package_to_requirements(args.package, args.version)
            sys.exit(0 if success else 1)

    else:
        # 如果没有指定命令,显示帮助信息
        # 导入logger
        from utils.logger_util import logger

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