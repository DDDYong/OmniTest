"""
-------------------------------------------------
File:           path_util.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
路径管理工具,提供项目相关的路径管理功能,包括获取各目录路径、文件路径操作和目录创建等功能
-------------------------------------------------
"""

import os
from datetime import datetime


class PathUtil:
    """项目路径管理类"""

    # 存储当前测试运行的时间文件夹名称
    _current_test_run_dir = None

    @staticmethod
    def get_test_run_dir() -> str:
        """
        获取当前测试运行的时间文件夹名称（格式: YYYYMMDD_HHMM）

        Returns:
            str: 时间文件夹名称
        """
        if PathUtil._current_test_run_dir is None:
            PathUtil._current_test_run_dir = datetime.now().strftime("%Y%m%d_%H%M")
        return PathUtil._current_test_run_dir

    @staticmethod
    def set_test_run_dir(dir_name: str) -> None:
        """
        设置当前测试运行的时间文件夹名称

        Args:
            dir_name: 时间文件夹名称
        """
        PathUtil._current_test_run_dir = dir_name

    @staticmethod
    def get_project_root() -> str:
        """
        获取项目根目录路径
        
        Returns:
            str: 项目根目录的绝对路径
        """
        # 获取当前文件所在目录
        current_path = os.path.dirname(os.path.abspath(__file__))
        # 向上两级目录即为项目根目录
        project_root = os.path.dirname(current_path)
        return project_root

    @staticmethod
    def get_config_dir() -> str:
        """
        获取配置目录路径
        
        Returns:
            str: 配置目录的绝对路径
        """
        return os.path.join(PathUtil.get_project_root(), 'config')

    @staticmethod
    def get_utils_dir() -> str:
        """
        获取工具目录路径
        
        Returns:
            str: 工具目录的绝对路径
        """
        return os.path.join(PathUtil.get_project_root(), 'utils')

    @staticmethod
    def get_data_dir() -> str:
        """
        获取数据目录路径
        
        Returns:
            str: 数据目录的绝对路径
        """
        return os.path.join(PathUtil.get_project_root(), 'data')

    @staticmethod
    def get_cases_dir() -> str:
        """
        获取测试用例目录路径
        
        Returns:
            str: 测试用例目录的绝对路径
        """
        return os.path.join(PathUtil.get_project_root(), 'cases')

    @staticmethod
    def get_reports_dir() -> str:
        """
        获取测试报告目录路径
        如果目录不存在则创建
        
        Returns:
            str: 测试报告目录的绝对路径
        """
        reports_dir = os.path.join(PathUtil.get_project_root(), 'reports')
        PathUtil.ensure_dir_exists(reports_dir)
        return reports_dir

    @staticmethod
    def get_api_cases_dir() -> str:
        """
        获取API测试用例目录路径
        
        Returns:
            str: API测试用例目录的绝对路径
        """
        return os.path.join(PathUtil.get_cases_dir(), 'api')

    @staticmethod
    def get_web_cases_dir() -> str:
        """
        获取Web测试用例目录路径
        
        Returns:
            str: Web测试用例目录的绝对路径
        """
        return os.path.join(PathUtil.get_cases_dir(), 'web')

    @staticmethod
    def get_app_cases_dir() -> str:
        """
        获取App测试用例目录路径
        
        Returns:
            str: App测试用例目录的绝对路径
        """
        return os.path.join(PathUtil.get_cases_dir(), 'app')

    @staticmethod
    def get_performance_cases_dir() -> str:
        """
        获取性能测试用例目录路径
        
        Returns:
            str: 性能测试用例目录的绝对路径
        """
        return os.path.join(PathUtil.get_cases_dir(), 'performance')

    @staticmethod
    def get_current_test_reports_dir() -> str:
        """
        获取当前测试运行的报告目录路径（带时间文件夹）
        如果目录不存在则创建
        
        Returns:
            str: 当前测试报告目录的绝对路径
        """
        test_run_dir = PathUtil.get_test_run_dir()
        current_reports_dir = os.path.join(PathUtil.get_reports_dir(), test_run_dir)
        PathUtil.ensure_dir_exists(current_reports_dir)
        return current_reports_dir

    @staticmethod
    def get_allure_results_dir(use_time_folder: bool = True) -> str:
        """
        获取Allure报告结果目录路径
        如果目录不存在则创建
        
        Args:
            use_time_folder: 是否使用时间文件夹, 默认为True
            
        Returns:
            str: Allure报告结果目录的绝对路径
        """
        if use_time_folder:
            allure_dir = os.path.join(PathUtil.get_current_test_reports_dir(), 'allure-results')
        else:
            allure_dir = os.path.join(PathUtil.get_reports_dir(), 'allure-results')
        PathUtil.ensure_dir_exists(allure_dir)
        return allure_dir

    @staticmethod
    def get_allure_report_dir(use_time_folder: bool = True) -> str:
        """
        获取Allure报告目录路径
        如果目录不存在则创建
        
        Args:
            use_time_folder: 是否使用时间文件夹, 默认为True
            
        Returns:
            str: Allure报告目录的绝对路径
        """
        if use_time_folder:
            report_dir = os.path.join(PathUtil.get_current_test_reports_dir(), 'allure-report')
        else:
            report_dir = os.path.join(PathUtil.get_reports_dir(), 'allure-report')
        PathUtil.ensure_dir_exists(report_dir)
        return report_dir

    @staticmethod
    def get_screenshots_dir(use_time_folder: bool = True) -> str:
        """
        获取截图目录路径
        如果目录不存在则创建
        
        Args:
            use_time_folder: 是否使用时间文件夹, 默认为True
            
        Returns:
            str: 截图目录的绝对路径
        """
        if use_time_folder:
            screenshots_dir = os.path.join(PathUtil.get_current_test_reports_dir(), 'screenshots')
        else:
            screenshots_dir = os.path.join(PathUtil.get_reports_dir(), 'screenshots')
        PathUtil.ensure_dir_exists(screenshots_dir)
        return screenshots_dir

    @staticmethod
    def get_logs_dir() -> str:
        """
        获取日志目录路径（统一使用项目根目录下的logs文件夹）
        如果目录不存在则创建
        
        Returns:
            str: 日志目录的绝对路径
        """
        project_root = PathUtil.get_project_root()
        logs_dir = os.path.join(project_root, 'logs')
        PathUtil.ensure_dir_exists(logs_dir)
        return logs_dir

    @staticmethod
    def ensure_dir_exists(directory: str) -> None:
        """
        确保目录存在,如果不存在则创建
        
        Args:
            directory: 目录路径
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def get_file_path(directory: str, filename: str) -> str:
        """
        获取文件的完整路径
        
        Args:
            directory: 目录路径
            filename: 文件名
            
        Returns:
            str: 文件的完整路径
        """
        return os.path.join(directory, filename)

    @staticmethod
    def get_config_file_path(filename: str = 'config.py') -> str:
        """
        获取配置文件的完整路径
        
        Args:
            filename: 配置文件名,默认为'config.py'
            
        Returns:
            str: 配置文件的完整路径
        """
        return PathUtil.get_file_path(PathUtil.get_config_dir(), filename)

    @staticmethod
    def get_data_file_path(filename: str) -> str:
        """
        获取数据文件的完整路径
        
        Args:
            filename: 数据文件名
            
        Returns:
            str: 数据文件的完整路径
        """
        return PathUtil.get_file_path(PathUtil.get_data_dir(), filename)

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        标准化路径
        
        Args:
            path: 路径字符串
            
        Returns:
            str: 标准化后的路径
        """
        return os.path.normpath(os.path.abspath(path))

    @staticmethod
    def is_file_exists(file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否存在
        """
        return os.path.isfile(file_path)

    @staticmethod
    def is_dir_exists(dir_path: str) -> bool:
        """
        检查目录是否存在
        
        Args:
            dir_path: 目录路径
            
        Returns:
            bool: 目录是否存在
        """
        return os.path.isdir(dir_path)

    @staticmethod
    def join_path(*paths) -> str:
        """
        连接多个路径部分
        
        Args:
            *paths: 路径部分
            
        Returns:
            str: 连接后的完整路径
        """
        return os.path.join(*paths)


# 创建PathUtil实例
path_util = PathUtil()

__all__ = ['PathUtil', 'path_util']
