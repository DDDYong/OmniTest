#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Allure报告路径配置的脚本
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_allure_config():
    """检查Allure报告路径配置"""
    print("=" * 80)
    print("检查Allure报告路径配置")
    print("=" * 80)

    # 1. 模拟PathUtil中的路径配置
    print("\n1. 模拟PathUtil中的Allure路径配置:")
    project_root = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(project_root, 'reports')
    allure_results_dir = os.path.join(reports_dir, 'allure-results')

    print(f"项目根目录: {project_root}")
    print(f"报告目录: {reports_dir}")
    print(f"Allure结果目录: {allure_results_dir}")
    print(f"Allure结果目录绝对路径: {os.path.abspath(allure_results_dir)}")

    # 2. 解析pytest.ini配置
    print("\n2. pytest.ini中的配置:")
    ini_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pytest.ini')
    if os.path.exists(ini_path):
        print(f"pytest.ini路径: {ini_path}")
        # 读取并解析pytest.ini文件
        try:
            with open(ini_path, 'r', encoding = 'utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('addopts'):
                        print(f"addopts配置: {line}")
                        if '--alluredir' in line:
                            import re
                            match = re.search(r'--alluredir=(\S+)', line)
                            if match:
                                allure_dir = match.group(1)
                                print(f"从pytest.ini中解析的Allure目录: {allure_dir}")
                                print(f"解析的Allure目录绝对路径: {os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), allure_dir))}")
        except Exception as e:
            print(f"读取pytest.ini失败: {e}")
    else:
        print("未找到pytest.ini文件")

    # 4. 检查当前工作目录
    print("\n4. 当前工作目录信息:")
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    print(f"当前工作目录绝对路径: {os.path.abspath(current_dir)}")

    # 5. 创建目录检查
    print("\n5. 目录存在性检查:")
    for dir_path in [reports_dir, allure_results_dir]:
        exists = os.path.exists(dir_path)
        print(f"目录 {dir_path}: {'存在' if exists else '不存在'}")

    # 6. 提供修复建议
    print("\n6. 修复建议:")
    print("- 修改conftest.py添加pytest_runtest_setup钩子来强制设置allure报告路径")
    print("- 修改run.py中使用绝对路径指定--alluredir")
    print("- 在pytest.ini中使用绝对路径指定--alluredir")
    print("- 检查是否有环境变量覆盖了配置")
    print("- 检查测试执行时的工作目录")

    # 7. 尝试创建一个实际的修复方案
    print("\n7. 修复方案示例:")
    # 提供修改run.py的建议代码
    print("修改run.py中的相关代码为:")
    print("import os")
    print("project_root = os.path.dirname(os.path.abspath(__file__))")
    print("allure_results_dir = os.path.join(project_root, 'reports', 'allure-results')")
    print("# 确保目录存在")
    print("os.makedirs(allure_results_dir, exist_ok=True)")
    print("# 使用绝对路径")
    print("cmd.extend(['--alluredir', allure_results_dir])")

    # 提供修改pytest.ini的建议
    print("\n修改pytest.ini的alluredir配置为:")
    abs_path_suggestion = os.path.join(project_root, 'reports', 'allure-results')
    print(f"--alluredir={abs_path_suggestion}")
    print("\n=" * 80)


if __name__ == "__main__":
    check_allure_config()
