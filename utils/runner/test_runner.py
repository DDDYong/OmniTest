"""
-------------------------------------------------
File:           test_runner.py
Author:         duanyang
Date:           2026/03/24
-------------------------------------------------
Description:    
测试核心运行逻辑,负责解析目标与执行各类测试引擎.
-------------------------------------------------
"""

import difflib
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta

from utils.decorator import timing
from utils.logger import logger
from utils.path import path_util


INVALID_TEST_TARGET_EXIT_CODE = 4


def _suggest_close_matches(input_name: str, candidates: list, n: int = 3) -> list:
    try:
        return difflib.get_close_matches(input_name, candidates, n=n, cutoff=0.4)
    except Exception:
        return []


def resolve_test_target(base_dir: str, test_dir: str = None, test_file: str = None):
    if test_file:
        target_path = test_file if os.path.isabs(test_file) else os.path.join(base_dir, test_file)
        if os.path.isfile(target_path):
            return target_path, None

        suggestions = []
        if os.path.isdir(base_dir) and not os.path.isabs(test_file):
            try:
                file_candidates = [
                    name for name in os.listdir(base_dir)
                    if os.path.isfile(os.path.join(base_dir, name))
                ]
            except Exception:
                file_candidates = []

            if not test_file.endswith('.py'):
                py_name = f"{test_file}.py"
                if py_name in file_candidates:
                    suggestions.append(py_name)

            suggestions.extend([s for s in _suggest_close_matches(test_file, file_candidates) if s not in suggestions])

        err = f"测试文件不存在: {target_path}"
        if suggestions:
            err = f"{err}, 可选相近文件: {', '.join(suggestions)}"
        return None, err

    if test_dir:
        target_path = test_dir if os.path.isabs(test_dir) else os.path.join(base_dir, test_dir)
        if os.path.isdir(target_path):
            return target_path, None

        suggestions = []
        if os.path.isdir(base_dir) and not os.path.isabs(test_dir):
            try:
                dir_candidates = [
                    name for name in os.listdir(base_dir)
                    if os.path.isdir(os.path.join(base_dir, name))
                ]
            except Exception:
                dir_candidates = []
            suggestions = _suggest_close_matches(test_dir, dir_candidates)

        err = f"测试目录不存在: {target_path}"
        if suggestions:
            err = f"{err}, 可选相近目录: {', '.join(suggestions)}"
        return None, err

    if not os.path.isdir(base_dir):
        return None, f"测试目录不存在: {base_dir}"
    return base_dir, None


@timing
def execute_pytest(base_dir: str, test_dir: str = None, test_file: str = None, markers: str = None, extra_args: list = None) -> int:
    """通用 pytest 执行器"""
    target_path, err = resolve_test_target(base_dir, test_dir, test_file)
    if err:
        logger.error(err)
        return INVALID_TEST_TARGET_EXIT_CODE

    cmd = [sys.executable, '-m', 'pytest', target_path]
    if markers:
        cmd.extend(['-m', markers])
    if extra_args:
        cmd.extend(extra_args)

    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=path_util.get_project_root(), text=True)
        return result.returncode
    except Exception as e:
        logger.error(f"执行 pytest 失败: {str(e)}")
        return 1


def run_api_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
    logger.info("开始运行API测试...")
    logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")
    allure_dir = path_util.get_allure_results_dir(use_time_folder=True)
    logger.info(f"Allure报告结果目录设置为: {allure_dir}")
    return execute_pytest(path_util.get_api_cases_dir(), test_dir, test_file, markers, ['-v', '--alluredir', allure_dir])


def run_web_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
    logger.info("开始运行Web测试...")
    logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")
    allure_dir = path_util.get_allure_results_dir(use_time_folder=True)
    return execute_pytest(path_util.get_web_cases_dir(), test_dir, test_file, markers, ['-v', '--alluredir', allure_dir])


def run_app_tests(test_dir: str = None, test_file: str = None, markers: str = None) -> int:
    logger.info("开始运行APP测试...")
    logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")
    allure_dir = path_util.get_allure_results_dir(use_time_folder=True)
    return execute_pytest(path_util.get_app_cases_dir(), test_dir, test_file, markers, ['-v', '--alluredir', allure_dir])


def run_parallel_tests(test_dir: str = None, test_file: str = None, markers: str = 'parallel',
                       num_workers: int = 2, html_report: bool = False) -> int:
    logger.info(f"开始运行并行测试 (workers={num_workers})...")
    logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")

    allure_dir = path_util.get_allure_results_dir(use_time_folder=True)
    extra_args = ['-n', str(num_workers), '-v', '--alluredir', allure_dir]

    if html_report:
        # 将HTML报告保存到时间文件夹中
        html_report_path = os.path.join(path_util.get_current_test_reports_dir(), 'report_parallel.html')
        extra_args.extend(['--html', html_report_path, '--self-contained-html'])
        logger.info(f"HTML报告将保存到: {html_report_path}")

    return execute_pytest(path_util.get_cases_dir(), test_dir, test_file, markers, extra_args)


@timing
def run_performance_tests(test_file: str, users: int = 100, spawn_rate: int = 10, run_time: str = '5m') -> int:
    logger.info("开始运行性能测试...")
    test_path = os.path.join(path_util.get_performance_cases_dir(), test_file)
    cmd = [
        'locust', '-f', test_path,
        '--users', str(users), '--spawn-rate', str(spawn_rate), '--run-time', run_time,
        '--headless', '--html', os.path.join(path_util.get_reports_dir(), 'locust_report.html')
    ]
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=path_util.get_project_root(), text=True)
        return result.returncode
    except Exception as e:
        logger.error(f"运行性能测试失败: {str(e)}")
        return 1


def run_all_tests() -> int:
    logger.info("开始运行所有测试...")
    logger.info(f"测试报告将保存到: {path_util.get_current_test_reports_dir()}")
    allure_dir = path_util.get_allure_results_dir(use_time_folder=True)

    cmd = [
        sys.executable, '-m', 'pytest',
        path_util.get_cases_dir(),
        '-v', '--alluredir', allure_dir
    ]
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=path_util.get_project_root(), text=True)
        return result.returncode
    except Exception as e:
        logger.error(f"运行所有测试失败: {str(e)}")
        return 1


def clean_reports(days_to_keep: int = 7) -> None:
    """
    清理测试报告
    1. 清理旧的报告文件夹（超过指定天数）
    2. 压缩历史报告以节省空间
    3. 保留最新的报告

    Args:
        days_to_keep: 保留多少天的报告，默认7天
    """
    logger.info("开始清理测试报告...")

    reports_dir = path_util.get_reports_dir()
    if not os.path.exists(reports_dir):
        logger.info("报告目录不存在，无需清理")
        return

    current_time = datetime.now()
    cutoff_date = current_time - timedelta(days = days_to_keep)

    # 遍历报告目录
    for item in os.listdir(reports_dir):
        item_path = os.path.join(reports_dir, item)

        # 检查是否为时间格式的文件夹
        if os.path.isdir(item_path):
            try:
                # 解析文件夹名称为日期时间
                folder_date = datetime.strptime(item, "%Y%m%d_%H%M")

                # 如果文件夹超过保留天数
                if folder_date < cutoff_date:
                    logger.info(f"清理旧报告: {item}")
                    shutil.rmtree(item_path)
                else:
                    # 压缩历史报告以节省空间
                    zip_path = f"{item_path}.zip"
                    if not os.path.exists(zip_path):
                        logger.info(f"压缩报告: {item}")
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root, _, files in os.walk(item_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, item_path)
                                    zipf.write(file_path, arcname)
            except ValueError:
                # 不是时间格式的文件夹，跳过
                pass

    logger.info("报告清理完成")


def generate_report_index() -> str:
    """
    生成报告索引页面
    创建一个HTML文件，列出所有历史报告

    Returns:
        str: 索引页面路径
    """
    logger.info("生成报告索引页面...")

    reports_dir = path_util.get_reports_dir()
    index_path = os.path.join(reports_dir, "index.html")

    # 收集所有报告
    reports = []
    for item in os.listdir(reports_dir):
        item_path = os.path.join(reports_dir, item)
        if os.path.isdir(item_path):
            try:
                # 解析文件夹名称为日期时间
                folder_date = datetime.strptime(item, "%Y%m%d_%H%M")
                reports.append({
                    "name": item,
                    "date": folder_date.strftime("%Y-%m-%d %H:%M"),
                    "path": item,
                    "type": "folder"
                })
            except ValueError:
                pass
        elif item.endswith(".zip"):
            try:
                # 解析压缩文件名称为日期时间
                folder_name = item[:-4]  # 移除.zip后缀
                folder_date = datetime.strptime(folder_name, "%Y%m%d_%H%M")
                reports.append({
                    "name": item,
                    "date": folder_date.strftime("%Y-%m-%d %H:%M"),
                    "path": item,
                    "type": "zip"
                })
            except ValueError:
                pass

    # 按日期排序，最新的在前
    reports.sort(key = lambda x: x["date"], reverse = True)

    # 生成HTML内容
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>测试报告索引</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #f5f5f5; }}
            a {{ color: #0066cc; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>测试报告索引</h1>
        <table>
            <tr>
                <th>报告名称</th>
                <th>生成时间</th>
                <th>类型</th>
                <th>操作</th>
            </tr>
    """

    for report in reports:
        if report["type"] == "folder":
            allure_report_path = os.path.join(report["path"], "allure-report", "index.html")
            if os.path.exists(os.path.join(reports_dir, allure_report_path)):
                link = f"<a href='{allure_report_path}' target='_blank'>查看报告</a>"
            else:
                link = "报告未生成"
        else:
            link = f"<a href='{report['path']}' download>下载压缩包</a>"

        html_content += f"""
            <tr>
                <td>{report['name']}</td>
                <td>{report['date']}</td>
                <td>{report['type']}</td>
                <td>{link}</td>
            </tr>
        """

    html_content += f"""
        </table>
    </body>
    </html>
    """

    # 写入索引文件
    with open(index_path, 'w', encoding = 'utf-8') as f:
        f.write(html_content)

    logger.info(f"报告索引页面已生成: {index_path}")
    return index_path
