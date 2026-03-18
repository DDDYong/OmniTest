#!/usr/bin/env python3
"""
OmniTest自动化测试框架 - 安装配置文件
"""
import os

from setuptools import setup, find_packages

# 读取项目根目录下的README.md文件
with open(os.path.join(os.path.dirname(__file__), 'README.md'), 'r', encoding = 'utf-8') as f:
    long_description = f.read()

# 读取项目根目录下的requirements.txt文件
with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), 'r', encoding = 'utf-8') as f:
    requirements = f.read().splitlines()

# 过滤掉空行和注释行
requirements = [req for req in requirements if req and not req.startswith('#')]

setup(
    # 项目名称
    name = 'omni-test',
    # 项目版本
    version = '1.0.0',
    # 项目描述
    description = 'OmniTest自动化测试框架, 支持API、Web、App和性能测试',
    # 详细描述（从README.md读取）
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    # 项目URL
    url = 'https://gitee.com/duanyang/omni-test',
    # 作者信息
    author = 'duanyang',
    author_email = 'duanyang@example.com',
    # 许可证
    license = 'MIT',
    # 项目分类
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Testers',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    # 项目关键字
    keywords = 'automation testing api web app performance',
    # 项目根目录
    package_dir = {'': '.'},
    # 自动发现所有包
    packages = find_packages(include = ['config', 'utils', 'cases', 'scripts']),
    # 包含的数据文件
    include_package_data = True,
    # 安装依赖
    install_requires = requirements,
    # 额外的开发依赖
    extras_require = {
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'flake8>=6.0.0',
            'black>=24.0.0',
            'isort>=5.12.0',
            'mypy>=1.7.0',
        ],
    },
    # 入口点
    entry_points = {
        'console_scripts': [
            'omni-test=run:run_main',
            'omni=run:run_main',
        ],
    },
    # Python版本要求
    python_requires = '>=3.8',
    # 项目数据文件
    data_files = [
        ('config', ['config/default.yaml', 'config/test.yaml', 'config/prod.yaml']),
    ],
    # 项目URLs
    project_urls = {
        'Bug Reports': 'https://github.com/duanyang/omni-test/issues',
        'Source': 'https://github.com/duanyang/omni-test',
    },
)
