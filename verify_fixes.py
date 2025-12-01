#!/usr/bin/env python3
"""
验证修复脚本
简单检查修复后的文件语法是否正确
"""

import ast
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 需要验证的文件列表
files_to_verify = [
    'cases/web/test_baidu_search.py',
    'cases/web/pages/baidu_home_page.py'
]


def verify_file_syntax(file_path):
    """验证文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding = 'utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, f"✓ {file_path} 语法正确"
    except SyntaxError as e:
        return False, f"✗ {file_path} 语法错误: {e}"
    except Exception as e:
        return False, f"✗ {file_path} 读取错误: {e}"


def main():
    print("开始验证修复后的文件...")
    success = True

    for file in files_to_verify:
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file)
        if os.path.exists(full_path):
            result, message = verify_file_syntax(full_path)
            print(message)
            if not result:
                success = False
        else:
            print(f"✗ {file} 文件不存在")
            success = False

    # 检查修复的关键问题
    print("\n检查关键修复项:")

    # 1. 检查百度首页元素定位器是否正确
    try:
        with open('cases/web/pages/baidu_home_page.py', 'r', encoding = 'utf-8') as f:
            content = f.read()
        if 'SEARCH_BOX = (By.ID, "kw")' in content and 'SEARCH_BUTTON = (By.ID, "su")' in content:
            print("✓ 百度首页元素定位器已修复")
        else:
            print("✗ 百度首页元素定位器未正确修复")
            success = False
    except Exception as e:
        print(f"✗ 检查元素定位器失败: {e}")
        success = False

    # 2. 检查pytest.current_test问题是否修复
    try:
        with open('cases/web/test_baidu_search.py', 'r', encoding = 'utf-8') as f:
            content = f.read()
        if 'pytest.current_test' not in content:
            print("✓ pytest.current_test问题已修复")
        else:
            print("✗ pytest.current_test问题未修复")
            success = False
    except Exception as e:
        print(f"✗ 检查pytest.current_test修复失败: {e}")
        success = False

    # 3. 检查导入顺序是否正确
    try:
        with open('cases/web/test_baidu_search.py', 'r', encoding = 'utf-8') as f:
            lines = f.readlines()
        # 找到sys.path.insert的位置
        insert_pos = None
        for i, line in enumerate(lines):
            if 'sys.path.insert' in line:
                insert_pos = i
                break

        # 找到pytest导入的位置
        pytest_import_pos = None
        for i, line in enumerate(lines):
            if 'import pytest' in line:
                pytest_import_pos = i
                break

        if insert_pos is not None and pytest_import_pos is not None and insert_pos < pytest_import_pos:
            print("✓ 导入顺序已修复")
        else:
            print("✗ 导入顺序未正确修复")
            success = False
    except Exception as e:
        print(f"✗ 检查导入顺序修复失败: {e}")
        success = False

    print("\n验证完成!")
    if success:
        print("🎉 所有修复验证通过!")
        return 0
    else:
        print("❌ 部分修复验证失败，请检查以上错误。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
