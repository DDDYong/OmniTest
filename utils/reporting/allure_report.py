"""
-------------------------------------------------
File:           allure_report.py
Author:         duanyang
Date:           2026/03/24
-------------------------------------------------
Description:    
Allure 报告生成、服务化与打开逻辑
-------------------------------------------------
"""

import os
import shutil
import subprocess
import threading
import http.server
import socketserver
import socket

from utils.path import path_util
from utils.logger import logger


def generate_allure_report(serve: bool = True, wait_for_enter: bool = True) -> bool:
    """
    生成Allure报告(使用时间文件夹)
    
    Args:
        serve: 是否启动本地 HTTP 服务器来提供报告
        wait_for_enter: 启动服务器后是否阻塞等待用户按回车(通常 CLI 需要,编程 API 不需要)
        
    Returns:
        bool: 是否生成成功
    """
    logger.info("开始生成Allure报告...")

    # 获取当前测试运行的时间文件夹路径
    allure_results_dir = path_util.get_allure_results_dir(use_time_folder=True)
    allure_report_dir = path_util.get_allure_report_dir(use_time_folder=True)

    logger.info(f"Allure结果目录: {allure_results_dir}")
    logger.info(f"Allure报告目录: {allure_report_dir}")

    # 清理旧报告(当前时间文件夹下的)
    if os.path.exists(allure_report_dir):
        shutil.rmtree(allure_report_dir)

    # 构建allure命令
    cmd = ['allure', 'generate', allure_results_dir, '-o', allure_report_dir, '--clean']

    # 执行命令
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, cwd=path_util.get_project_root(), text=True)
        logger.info(f"Allure报告已生成: {allure_report_dir}")

        if serve:
            _serve_allure_report(allure_report_dir, wait_for_enter)
            
        return True
    except Exception as e:
        logger.error(f"生成Allure报告失败: {str(e)}")
        return False


def _serve_allure_report(report_dir: str, wait_for_enter: bool):
    """内部方法:启动本地 HTTP 服务"""
    try:
        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                return s.getsockname()[1]

        port = find_free_port()
        server_address = ('127.0.0.1', port)

        class ReportHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=report_dir, **kwargs)

        httpd = socketserver.TCPServer(server_address, ReportHandler)

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        report_url = f"http://{server_address[0]}:{server_address[1]}"
        logger.info(f"Allure报告HTTP服务已启动: {report_url}")
        logger.info(f"请在浏览器中打开以下链接查看报告: 🌐 {report_url}")
        
        if wait_for_enter:
            logger.info(f"按 Enter 键停止服务器...")
            input("")
            httpd.shutdown()
            httpd.server_close()
            logger.info("HTTP服务已停止.")
            
    except Exception as e:
        logger.error(f"启动报告服务失败: {str(e)}")


def open_allure_report() -> bool:
    """
    打开Allure报告(使用时间文件夹)
    
    Returns:
        bool: 是否打开成功
    """
    logger.info("开始打开Allure报告...")

    allure_report_dir = path_util.get_allure_report_dir(use_time_folder=True)

    if not os.path.exists(os.path.join(allure_report_dir, 'index.html')):
        logger.warning(f"Allure报告不存在: {allure_report_dir}, 请先生成报告")
        return False

    cmd = ['allure', 'open', allure_report_dir]

    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        subprocess.Popen(cmd, cwd=path_util.get_project_root())
        return True
    except Exception as e:
        logger.error(f"打开Allure报告失败: {str(e)}")
        return False
