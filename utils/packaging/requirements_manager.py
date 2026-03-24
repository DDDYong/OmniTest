"""
-------------------------------------------------
File:           requirements_manager.py
Author:         duanyang
Date:           2026/03/24
-------------------------------------------------
Description:    
项目依赖管理工具
-------------------------------------------------
"""

import os
import subprocess

from utils.path import path_util
from utils.logger import logger


def update_requirements() -> bool:
    """更新requirements.txt文件,保留原有的注释结构"""
    logger.info("开始更新 requirements.txt ...")
    req_file = os.path.join(path_util.get_project_root(), 'requirements.txt')

    # 获取当前的依赖包列表
    try:
        result = subprocess.run(
            ['pip', 'freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        current_packages = result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        logger.error(f"获取当前依赖失败: {e}")
        return False

    # 解析当前包及其版本
    package_dict = {}
    for pkg in current_packages:
        if '==' in pkg:
            name, version = pkg.split('==', 1)
            package_dict[name.lower()] = pkg

    if not os.path.exists(req_file):
        logger.warning(f"文件不存在: {req_file},将创建新文件")
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(current_packages))
        logger.info("requirements.txt 创建成功!")
        return True

    # 读取现有文件内容
    with open(req_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 更新文件内容
    new_lines = []
    updated_count = 0
    for line in lines:
        stripped_line = line.strip()
        # 保留空行和注释
        if not stripped_line or stripped_line.startswith('#'):
            new_lines.append(line)
            continue

        # 解析包名
        if '==' in stripped_line:
            pkg_name = stripped_line.split('==')[0].strip().lower()
        elif '>=' in stripped_line:
            pkg_name = stripped_line.split('>=')[0].strip().lower()
        else:
            pkg_name = stripped_line.lower()

        # 如果在当前环境中找到该包,则使用新版本
        if pkg_name in package_dict:
            new_pkg = package_dict[pkg_name]
            if new_pkg != stripped_line:
                logger.info(f"更新依赖: {stripped_line} -> {new_pkg}")
                updated_count += 1
            new_lines.append(f"{new_pkg}\n")
            # 从字典中移除已处理的包
            del package_dict[pkg_name]
        else:
            # 如果环境中没有,保留原样
            new_lines.append(line)

    # 写入更新后的内容
    with open(req_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    logger.info(f"requirements.txt 更新完成!共更新 {updated_count} 个依赖.")
    return True


def add_package_to_requirements(package_name: str, version: str = None) -> bool:
    """添加新的依赖包到requirements.txt中"""
    req_file = os.path.join(path_util.get_project_root(), 'requirements.txt')
    
    pkg_str = f"{package_name}=={version}" if version else package_name
    logger.info(f"准备添加依赖: {pkg_str}")
    
    # 尝试安装包
    try:
        cmd = ['pip', 'install', pkg_str]
        logger.info(f"执行命令: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"安装依赖失败: {e}")
        return False
        
    # 更新 requirements.txt
    if os.path.exists(req_file):
        with open(req_file, 'a', encoding='utf-8') as f:
            # 确保在新行添加
            f.write(f"\n{pkg_str}\n")
        logger.info(f"已将 {pkg_str} 追加到 requirements.txt")
    else:
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write(f"{pkg_str}\n")
        logger.info(f"已创建 requirements.txt 并添加 {pkg_str}")
        
    # 同步更新整个文件以确保版本正确
    return update_requirements()
