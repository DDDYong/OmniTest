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
import sys
import subprocess

from utils.path import path_util
from utils.logger import logger
from utils.decorator import timing


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
        html_report_path = os.path.join(path_util.get_logs_dir(), 'report_parallel.html')
        extra_args.extend(['--html', html_report_path, '--self-contained-html'])
        
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
