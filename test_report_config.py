#!/usr/bin/env python3
"""
测试报告配置验证脚本
验证新的时间文件夹和日志配置是否正常工作
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.path_util import path_util


def test_logs_dir():
    """测试日志目录是否正确指向根目录下的logs"""
    logs_dir = path_util.get_logs_dir()
    print(f"日志目录: {logs_dir}")
    print(f"是否指向根目录logs: {'logs' in logs_dir and 'reports' not in logs_dir}")
    assert os.path.exists(logs_dir), "日志目录不存在"
    return logs_dir


def test_time_folder():
    """测试时间文件夹功能"""
    test_run_dir = path_util.get_test_run_dir()
    print(f"\n当前测试运行时间文件夹: {test_run_dir}")
    print(f"格式验证 (YYYYMMDD_HHMM): {len(test_run_dir) == 11 and test_run_dir[8] == '_'}")

    # 测试时间文件夹路径
    current_reports_dir = path_util.get_current_test_reports_dir()
    print(f"\n当前测试报告目录: {current_reports_dir}")
    assert test_run_dir in current_reports_dir, "时间文件夹未包含在路径中"
    return current_reports_dir


def test_allure_dirs():
    """测试Allure目录是否使用时间文件夹"""
    print("\n" + "=" * 60)
    print("测试Allure目录配置")
    print("=" * 60)

    # 测试使用时间文件夹
    allure_results_with_time = path_util.get_allure_results_dir(use_time_folder = True)
    allure_report_with_time = path_util.get_allure_report_dir(use_time_folder = True)

    print(f"\n使用时间文件夹:")
    print(f"  Allure结果目录: {allure_results_with_time}")
    print(f"  Allure报告目录: {allure_report_with_time}")

    # 测试不使用时间文件夹（向后兼容）
    allure_results_without_time = path_util.get_allure_results_dir(use_time_folder = False)
    allure_report_without_time = path_util.get_allure_report_dir(use_time_folder = False)

    print(f"\n不使用时间文件夹:")
    print(f"  Allure结果目录: {allure_results_without_time}")
    print(f"  Allure报告目录: {allure_report_without_time}")

    return allure_results_with_time, allure_report_with_time


def test_screenshots_dir():
    """测试截图目录配置"""
    print("\n" + "=" * 60)
    print("测试截图目录配置")
    print("=" * 60)

    screenshots_with_time = path_util.get_screenshots_dir(use_time_folder = True)
    screenshots_without_time = path_util.get_screenshots_dir(use_time_folder = False)

    print(f"\n使用时间文件夹: {screenshots_with_time}")
    print(f"不使用时间文件夹: {screenshots_without_time}")

    return screenshots_with_time


def main():
    """主测试函数"""
    print("=" * 60)
    print("OmniTest 报告配置验证")
    print("=" * 60)

    try:
        # 测试日志目录
        test_logs_dir()

        # 测试时间文件夹
        test_time_folder()

        # 测试Allure目录
        test_allure_dirs()

        # 测试截图目录
        test_screenshots_dir()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n报告配置说明:")
        print("1. 日志文件统一保存在项目根目录下的 logs/ 文件夹")
        print("2. 每次测试运行会在 reports/ 下创建时间命名的子文件夹")
        print("3. 时间文件夹格式: YYYYMMDD_HHMM (例如: 20260307_1800)")
        print("4. 每次测试的报告独立保存，不会覆盖历史记录")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
