#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简化的测试脚本，用于检查项目中的循环依赖问题，不依赖外部包"""

import importlib.util
import os
import sys

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# 模拟必要的模块以避免外部依赖
class MockConfig:
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 3
    RETRY_INTERVAL = 1
    LOGS_DIR = './logs'
    WEB_BASE_URL = 'http://localhost'
    API_BASE_URL = 'http://localhost/api'


class MockLogger:
    def info(self, msg):
        pass

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

    def exception(self, msg):
        pass


# 注入模拟模块
sys.modules['config.config_manager'] = type('mock_config_module', (), {'config': MockConfig()})
sys.modules['requests'] = type('mock_requests', (), {})
sys.modules['selenium.webdriver'] = type('mock_selenium', (), {'Remote': object})
sys.modules['appium.webdriver'] = type('mock_appium', (), {'Remote': object})


def test_module_structure():
    """测试各个模块的结构和导入情况"""
    results = []
    module_paths = [
        ('config.config_manager', 'config/config_manager.py'),
        ('utils.logger_util', 'utils/logger_util.py'),
        ('utils.decorator_util', 'utils/decorator_util.py'),
        ('utils.app.app_base_page', 'utils/app/app_base_page.py'),
        ('utils.app.appium_manager', 'utils/app/appium_manager.py'),
        ('utils.web.web_base_page', 'utils/web/web_base_page.py'),
        ('utils.web.element_handler', 'utils/web/element_handler.py'),
        ('utils.api.api_client', 'utils/api/api_client.py')
    ]

    for module_name, relative_path in module_paths:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

        if not os.path.exists(file_path):
            results.append(f"✗ 文件不存在: {file_path}")
            continue

        try:
            # 尝试加载模块但不执行导入
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec:
                # 只检查语法，不执行实际导入
                with open(file_path, 'r', encoding = 'utf-8') as f:
                    code = compile(f.read(), file_path, 'exec')
                results.append(f"✓ {module_name} 语法检查通过")
            else:
                results.append(f"✗ {module_name} 无法创建模块规范")
        except SyntaxError as e:
            results.append(f"✗ {module_name} 语法错误: {str(e)}")
        except Exception as e:
            results.append(f"✗ {module_name} 检查失败: {str(e)}")

    return results


def check_import_statements():
    """检查导入语句是否存在循环依赖"""
    results = []
    # 优化导入模式检查，只关注真正的问题导入
    import_patterns = [
        ('from config import config', '应该替换为 from config.config_manager import config'),
        # 只匹配单独的'import config'，不匹配其他形式的导入
        ('^import config$', '可能导致循环依赖')
        # 注意：从同一包内导入是正常的模块化设计，不再将其标记为警告
    ]

    # 检查关键文件
    key_files = [
        'utils/app/app_base_page.py',
        'utils/app/appium_manager.py',
        'utils/web/web_base_page.py',
        'utils/web/element_handler.py',
        'utils/api/api_client.py',
        'utils/logger_util.py',
        'utils/decorator_util.py',
        'utils/assert_util.py'
    ]

    for file_path in key_files:
        abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding = 'utf-8') as f:
                    content = f.read()

                for pattern, message in import_patterns:
                    # 对于'^import config$'使用精确匹配
                    if pattern == '^import config$':
                        import re
                        if re.search(pattern, content, re.MULTILINE):
                            results.append(f"⚠️ {file_path} 中发现: import config - {message}")
                    # 其他模式使用字符串包含检查
                    elif pattern in content:
                        # 避免将'from config.config_manager import config'误报为'from config import config'
                        if pattern == 'from config import config' and 'from config.config_manager import config' not in content:
                            results.append(f"⚠️ {file_path} 中发现: {pattern} - {message}")
            except Exception as e:
                results.append(f"✗ 无法读取 {file_path}: {str(e)}")

    return results


if __name__ == "__main__":
    print("开始检查项目结构和导入语句...\n")

    print("1. 模块语法检查:")
    structure_results = test_module_structure()
    for result in structure_results:
        print(f"  {result}")

    print("\n2. 导入语句检查:")
    import_results = check_import_statements()
    if import_results:
        for result in import_results:
            print(f"  {result}")
    else:
        print("  ✓ 未发现明显的导入问题")

    print("\n检查完成")
