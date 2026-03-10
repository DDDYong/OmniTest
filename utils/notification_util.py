"""
-------------------------------------------------
File:           notification_util.py
Author:         duanyang
Date:           2026/03/09
-------------------------------------------------
Description:    
通知工具模块,提供企业微信和飞书的通知功能
-------------------------------------------------
"""

import json
import os
import shutil
import smtplib
import subprocess
import tempfile
import zipfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from utils.logger_util import logger
from utils.path_util import path_util


class NotificationUtil:
    """通知工具类"""

    # 企业微信配置
    WECHAT_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_WEBHOOK_KEY"

    # 飞书配置
    FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/29fdb473-482f-4771-b92b-de1baf03f415"

    # 云存储配置
    CLOUD_STORAGE_TYPE = "github_pages"
    GITHUB_REPO = "DDDYong/OmniTest"
    GITHUB_TOKEN = "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"
    GITHUB_BRANCH = "gh-pages"
    # SSH配置
    USE_SSH = True  # 是否使用SSH协议
    GITHUB_SSH_URL = "git@github.com:DDDYong/OmniTest.git"  # SSH URL

    # 邮件配置
    SMTP_SERVER = "smtp.qq.com"  # SMTP服务器地址
    SMTP_PORT = 587  # SMTP服务器端口
    SMTP_USER = "2979735103@qq.com"  # 发件人邮箱
    SMTP_PASSWORD = "bvzmqhriyjgpddcb"  # 发件人邮箱密码
    RECIPIENT_EMAIL = "duanyang@guangyu.ltd"  # 企业微信邮箱

    @staticmethod
    def get_test_summary() -> dict:
        """
        获取测试摘要信息

        Returns:
            dict: 测试摘要字典
        """
        try:
            # 尝试从allure-results目录中读取测试结果
            allure_results_dir = path_util.get_allure_results_dir(use_time_folder = True)
            summary_file = os.path.join(allure_results_dir, "summary.json")

            logger.info(f"尝试读取摘要文件: {summary_file}")

            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding = 'utf-8') as f:
                    summary = json.load(f)

                # 提取测试统计信息
                statistic = summary.get('statistic', {})
                result = {
                    'total': statistic.get('total', 0),
                    'passed': statistic.get('passed', 0),
                    'failed': statistic.get('failed', 0),
                    'broken': statistic.get('broken', 0),
                    'skipped': statistic.get('skipped', 0),
                    'duration': statistic.get('duration', 0),
                    'has_data': True
                }

                # 计算通过率
                if result['total'] > 0:
                    result['pass_rate'] = round((result['passed'] / result['total']) * 100, 2)
                else:
                    result['pass_rate'] = 0

                logger.info(f"测试摘要获取成功: {result}")
                return result
            else:
                logger.warning(f"摘要文件不存在: {summary_file}")
                return {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'broken': 0,
                    'skipped': 0,
                    'duration': 0,
                    'pass_rate': 0,
                    'has_data': False
                }
        except Exception as e:
            logger.error(f"获取测试摘要失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'broken': 0,
                'skipped': 0,
                'duration': 0,
                'pass_rate': 0,
                'has_data': False
            }

    @staticmethod
    def get_test_summary_html(summary: dict = None) -> str:
        """
        获取测试摘要HTML

        Args:
            summary: 测试摘要字典，如果为None则自动获取

        Returns:
            str: 测试摘要HTML
        """
        if summary is None:
            summary = NotificationUtil.get_test_summary()

        if not summary.get('has_data', False):
            return "<p style='color: orange;'>⚠️ 测试摘要信息不可用（可能测试未正常执行完成）</p>"

        # 判断测试结果状态
        if summary['failed'] > 0 or summary['broken'] > 0:
            status_color = 'red'
            status_text = '❌ 部分测试失败'
        elif summary['total'] == 0:
            status_color = 'gray'
            status_text = '⚠️ 没有执行测试'
        else:
            status_color = 'green'
            status_text = '✅ 所有测试通过'

        # 构建HTML摘要
        html = f"""
        <div style="margin: 20px 0;">
            <h3 style="color: {status_color}; margin-bottom: 15px;">📊 测试摘要 - {status_text}</h3>
            <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 600px;">
                <tr style="background-color: #f5f5f5;">
                    <th style="text-align: left; padding: 10px;">指标</th>
                    <th style="text-align: center; padding: 10px;">数量</th>
                    <th style="text-align: center; padding: 10px;">占比</th>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>总用例数</strong></td>
                    <td style="text-align: center; padding: 10px; font-size: 18px; font-weight: bold;">{summary['total']}</td>
                    <td style="text-align: center; padding: 10px;">100%</td>
                </tr>
                <tr>
                    <td style="padding: 10px; color: green;"><strong>✅ 通过</strong></td>
                    <td style="text-align: center; padding: 10px; color: green; font-weight: bold;">{summary['passed']}</td>
                    <td style="text-align: center; padding: 10px;">{summary['pass_rate']}%</td>
                </tr>
                <tr>
                    <td style="padding: 10px; color: red;"><strong>❌ 失败</strong></td>
                    <td style="text-align: center; padding: 10px; color: red; font-weight: bold;">{summary['failed']}</td>
                    <td style="text-align: center; padding: 10px;">{round((summary['failed'] / summary['total'] * 100) if summary['total'] > 0 else 0, 2)}%</td>
                </tr>
                <tr>
                    <td style="padding: 10px; color: orange;"><strong>⚠️ 损坏</strong></td>
                    <td style="text-align: center; padding: 10px; color: orange; font-weight: bold;">{summary['broken']}</td>
                    <td style="text-align: center; padding: 10px;">{round((summary['broken'] / summary['total'] * 100) if summary['total'] > 0 else 0, 2)}%</td>
                </tr>
                <tr>
                    <td style="padding: 10px; color: gray;"><strong>⏭️ 跳过</strong></td>
                    <td style="text-align: center; padding: 10px; color: gray; font-weight: bold;">{summary['skipped']}</td>
                    <td style="text-align: center; padding: 10px;">{round((summary['skipped'] / summary['total'] * 100) if summary['total'] > 0 else 0, 2)}%</td>
                </tr>
            </table>
            <p style="margin-top: 10px; color: #666;">
                ⏱️ 测试执行时长: {round(summary['duration'] / 1000, 2)} 秒
            </p>
        </div>
        """
        return html

    @staticmethod
    def send_email_notification(zip_file_path: str = None, report_url: str = None) -> bool:
        """
        发送邮件通知

        Args:
            zip_file_path: 压缩文件路径
            report_url: 云存储上的报告URL

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始发送邮件通知...")

        test_run_dir = path_util.get_test_run_dir()
        test_summary = NotificationUtil.get_test_summary()

        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = NotificationUtil.SMTP_USER
            msg["To"] = NotificationUtil.RECIPIENT_EMAIL

            # 根据测试结果设置邮件主题
            if test_summary.get('failed', 0) > 0 or test_summary.get('broken', 0) > 0:
                status_emoji = "❌"
                status_text = "测试失败"
            elif test_summary.get('total', 0) == 0:
                status_emoji = "⚠️"
                status_text = "无测试执行"
            else:
                status_emoji = "✅"
                status_text = "测试通过"

            msg["Subject"] = f"{status_emoji} {status_text} - 测试报告通知 - {test_run_dir}"

            # 构建邮件正文
            test_summary_html = NotificationUtil.get_test_summary_html(test_summary)

            # 构建报告访问说明
            access_instructions = ""
            if report_url:
                access_instructions += f"""
                <div style="background-color: #e8f4ff; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h4 style="margin-top: 0; color: #0066cc;">🌐 方案一：在线访问（推荐）</h4>
                    <p>直接点击以下链接访问完整的可视化测试报告：</p>
                    <p style="font-size: 16px; font-weight: bold;">
                        <a href="{report_url}" target="_blank" style="color: #0066cc; text-decoration: underline;">
                            📊 点击查看完整测试报告
                        </a>
                    </p>
                    <p style="color: #666; font-size: 12px;">* 报告已上传至云存储，支持在线查看所有测试细节和图表</p>
                </div>
                """

            access_instructions += f"""
            <div style="background-color: #fff9e6; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h4 style="margin-top: 0; color: #cc8800;">📦 方案二：本地访问</h4>
                <p><strong>重要提示：</strong>Allure报告是单页Web应用，需要通过HTTP服务器访问，直接打开index.html可能无法正常显示！</p>
                <ol style="margin-left: 20px; padding-left: 0;">
                    <li style="margin: 10px 0;">下载邮件附件 <strong>test_report_{test_run_dir}.zip</strong></li>
                    <li style="margin: 10px 0;">解压该压缩文件到本地文件夹</li>
                    <li style="margin: 10px 0;">
                        <strong>方式A：使用Python启动本地服务器（推荐）</strong>
                        <div style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; font-family: monospace; margin: 5px 0;">
                            cd 解压后的文件夹路径<br>
                            python -m http.server 8000
                        </div>
                        然后在浏览器访问：<code>http://localhost:8000</code>
                    </li>
                    <li style="margin: 10px 0;">
                        <strong>方式B：使用Allure命令行</strong>
                        <div style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; font-family: monospace; margin: 5px 0;">
                            allure serve 解压后的文件夹路径
                        </div>
                    </li>
                </ol>
                <p style="color: #cc0000; font-weight: bold;">⚠️ 不要直接双击打开index.html文件，这会导致JavaScript被浏览器阻止，报告无法显示！</p>
            </div>
            """

            # 完整邮件正文
            body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                    h3 {{ color: #555; }}
                    .info-box {{ background-color: #f0f7ff; border-left: 4px solid #0066cc; padding: 15px; margin: 15px 0; }}
                    .warning {{ color: #cc0000; }}
                    a {{ color: #0066cc; }}
                </style>
            </head>
            <body>
                <h2>📋 自动化测试报告</h2>

                <div class="info-box">
                    <p><strong>🕐 测试时间</strong>: {test_run_dir}</p>
                    <p><strong>📁 测试批次</strong>: {test_run_dir}</p>
                </div>

                {test_summary_html}

                <h3>🔍 查看完整测试报告</h3>

                {access_instructions}

                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    此邮件由OmniTest自动化测试框架自动发送，请勿直接回复
                </p>
            </body>
            </html>
            """

            msg.attach(MIMEText(body, "html", "utf-8"))

            # 添加附件
            if zip_file_path and os.path.exists(zip_file_path):
                logger.info(f"添加邮件附件: {zip_file_path}")
                with open(zip_file_path, "rb") as f:
                    attach = MIMEApplication(f.read())
                    attach.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename = os.path.basename(zip_file_path)
                    )
                    msg.attach(attach)
            else:
                logger.warning("压缩文件不存在，邮件将不包含附件")

            # 发送邮件
            with smtplib.SMTP(NotificationUtil.SMTP_SERVER, NotificationUtil.SMTP_PORT) as server:
                server.starttls()
                server.login(NotificationUtil.SMTP_USER, NotificationUtil.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info("邮件通知发送成功")
            return True
        except Exception as e:
            logger.error(f"发送邮件通知失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def zip_report(include_results: bool = False) -> str | None:
        """
        压缩测试报告目录

        Args:
            include_results: 是否包含allure-results目录

        Returns:
            str: 压缩文件路径
        """
        logger.info("开始压缩测试报告...")

        test_run_dir = path_util.get_test_run_dir()

        # 获取报告目录
        allure_report_dir = path_util.get_allure_report_dir(use_time_folder = True)
        allure_results_dir = path_util.get_allure_results_dir(use_time_folder = True)

        logger.info(f"Allure报告目录: {allure_report_dir}")
        logger.info(f"Allure结果目录: {allure_results_dir}")

        # 创建临时压缩文件
        zip_file_path = os.path.join(tempfile.gettempdir(), f"test_report_{test_run_dir}.zip")

        try:
            file_count = 0
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 压缩allure-report目录
                if os.path.exists(allure_report_dir):
                    logger.info(f"正在压缩allure-report目录...")
                    for root, _, files in os.walk(allure_report_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("allure-report", os.path.relpath(file_path, allure_report_dir))
                            zipf.write(file_path, arcname)
                            file_count += 1
                    logger.info(f"allure-report目录压缩完成，共 {file_count} 个文件")
                else:
                    logger.warning(f"allure-report目录不存在: {allure_report_dir}")

                # 压缩allure-results目录
                if include_results and os.path.exists(allure_results_dir):
                    logger.info(f"正在压缩allure-results目录...")
                    results_count = 0
                    for root, _, files in os.walk(allure_results_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("allure-results", os.path.relpath(file_path, allure_results_dir))
                            zipf.write(file_path, arcname)
                            results_count += 1
                    file_count += results_count
                    logger.info(f"allure-results目录压缩完成，共 {results_count} 个文件")

            # 验证压缩文件
            if os.path.exists(zip_file_path):
                file_size = os.path.getsize(zip_file_path)
                logger.info(f"测试报告已压缩: {zip_file_path}")
                logger.info(f"压缩文件大小: {file_size / 1024 / 1024:.2f} MB")
                logger.info(f"总计包含 {file_count} 个文件")

                # 验证压缩文件内容
                with zipfile.ZipFile(zip_file_path, 'r') as zipf:
                    file_list = zipf.namelist()
                    logger.info(f"压缩包内容: {file_list[:10]}...")  # 只显示前10个文件

                return zip_file_path
            else:
                logger.error("压缩文件创建失败")
                return None
        except Exception as e:
            logger.error(f"压缩测试报告失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def send_report_via_email(upload_to_cloud: bool = True) -> bool:
        """
        通过邮件发送测试报告（支持云存储）

        Args:
            upload_to_cloud: 是否先上传到云存储

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始通过邮件发送测试报告...")

        report_url = None

        # 先尝试上传到云存储
        if upload_to_cloud:
            logger.info("尝试上传报告到云存储...")
            report_url = NotificationUtil.upload_report_to_cloud()
            if report_url:
                logger.info(f"报告已上传到云存储: {report_url}")
            else:
                logger.warning("上传到云存储失败，将只发送压缩包")

        # 压缩报告（包含allure-results以便可以重新生成报告）
        zip_file_path = NotificationUtil.zip_report(include_results = True)

        # 发送邮件
        return NotificationUtil.send_email_notification(zip_file_path, report_url)

    @staticmethod
    def upload_report_to_cloud() -> str | None:
        """
        上传测试报告到云存储

        Returns:
            str: 云存储上的报告URL
        """
        logger.info("开始上传测试报告到云存储...")

        # 获取报告目录
        allure_report_dir = path_util.get_allure_report_dir(use_time_folder = True)
        test_run_dir = path_util.get_test_run_dir()

        logger.info(f"报告目录: {allure_report_dir}")
        logger.info(f"测试运行目录: {test_run_dir}")

        # 检查报告目录是否存在
        if not os.path.exists(allure_report_dir):
            logger.error(f"报告目录不存在: {allure_report_dir}")
            return None

        # 检查index.html文件是否存在
        index_html_path = os.path.join(allure_report_dir, "index.html")
        if not os.path.exists(index_html_path):
            logger.error(f"index.html文件不存在: {index_html_path}")
            return None

        # 根据云存储类型执行不同的上传逻辑
        if NotificationUtil.CLOUD_STORAGE_TYPE == "github_pages":
            try:
                # GitHub Pages的上传逻辑
                # 创建临时目录
                temp_dir = tempfile.mkdtemp()
                logger.info(f"创建临时目录: {temp_dir}")

                # 克隆GitHub仓库（带重试机制）
                clone_success = False

                # 尝试使用HTTP协议
                if not NotificationUtil.USE_SSH:
                    logger.info("尝试使用HTTP协议克隆仓库...")
                    repo_url = f"https://{NotificationUtil.GITHUB_TOKEN}@github.com/{NotificationUtil.GITHUB_REPO}.git"

                    # 设置环境变量禁用HTTP2
                    env = os.environ.copy()
                    env["GIT_HTTP_VERSION"] = "HTTP/1.1"
                    env["GIT_CURL_VERBOSE"] = "1"
                    env["GIT_SSL_NO_VERIFY"] = "1"  # 禁用SSL验证（仅用于测试）

                    # 重试克隆
                    max_retries = 3
                    retry_count = 0

                    while retry_count < max_retries and not clone_success:
                        try:
                            # 清理临时目录
                            if os.path.exists(temp_dir):
                                logger.info(f"清理临时目录: {temp_dir}")
                                shutil.rmtree(temp_dir)
                                os.makedirs(temp_dir)

                            clone_cmd = ["git", "clone", repo_url, temp_dir]
                            logger.info(f"执行命令: {' '.join(clone_cmd)}")

                            result = subprocess.run(
                                clone_cmd,
                                capture_output = True,
                                text = True,
                                env = env,
                                timeout = 60  # 设置60秒超时
                            )
                            if result.returncode == 0:
                                clone_success = True
                                logger.info("使用HTTP协议克隆仓库成功")
                            else:
                                retry_count += 1
                                logger.warning(f"使用HTTP协议克隆仓库失败 (尝试 {retry_count}/{max_retries}): {result.stderr}")
                                if retry_count < max_retries:
                                    logger.info("等待3秒后重试...")
                                    import time
                                    time.sleep(3)
                        except subprocess.TimeoutExpired:
                            retry_count += 1
                            logger.warning(f"使用HTTP协议克隆仓库超时 (尝试 {retry_count}/{max_retries})")
                            if retry_count < max_retries:
                                logger.info("等待3秒后重试...")
                                import time
                                time.sleep(3)
                        except Exception as e:
                            retry_count += 1
                            logger.warning(f"使用HTTP协议克隆仓库异常 (尝试 {retry_count}/{max_retries}): {str(e)}")
                            if retry_count < max_retries:
                                logger.info("等待3秒后重试...")
                                import time
                                time.sleep(3)

                # 如果HTTP协议失败，尝试使用SSH协议
                if not clone_success:
                    logger.info("HTTP协议克隆失败，尝试使用SSH协议...")

                    # 重试克隆
                    max_retries = 3
                    retry_count = 0

                    while retry_count < max_retries and not clone_success:
                        try:
                            # 清理临时目录
                            if os.path.exists(temp_dir):
                                logger.info(f"清理临时目录: {temp_dir}")
                                shutil.rmtree(temp_dir)
                                os.makedirs(temp_dir)

                            clone_cmd = ["git", "-c", "core.StrictHostKeyChecking=no", "clone",
                                         NotificationUtil.GITHUB_SSH_URL, temp_dir]
                            logger.info(f"执行命令: {' '.join(clone_cmd)}")

                            result = subprocess.run(
                                clone_cmd,
                                capture_output = True,
                                text = True,
                                timeout = 60  # 设置60秒超时
                            )
                            if result.returncode == 0:
                                clone_success = True
                                logger.info("使用SSH协议克隆仓库成功")
                            else:
                                retry_count += 1
                                logger.warning(f"使用SSH协议克隆仓库失败 (尝试 {retry_count}/{max_retries}): {result.stderr}")
                                if retry_count < max_retries:
                                    logger.info("等待3秒后重试...")
                                    import time
                                    time.sleep(3)
                        except subprocess.TimeoutExpired:
                            retry_count += 1
                            logger.warning(f"使用SSH协议克隆仓库超时 (尝试 {retry_count}/{max_retries})")
                            if retry_count < max_retries:
                                logger.info("等待3秒后重试...")
                                import time
                                time.sleep(3)
                        except Exception as e:
                            retry_count += 1
                            logger.warning(f"使用SSH协议克隆仓库异常 (尝试 {retry_count}/{max_retries}): {str(e)}")
                            if retry_count < max_retries:
                                logger.info("等待3秒后重试...")
                                import time
                                time.sleep(3)

                if not clone_success:
                    logger.error("克隆仓库失败，已尝试HTTP和SSH协议")
                    return None

                # 检查gh-pages分支是否存在
                branch_check_cmd = ["git", "branch", "-a"]
                branch_result = subprocess.run(branch_check_cmd, cwd = temp_dir, capture_output = True, text = True)
                logger.info(f"所有分支: {branch_result.stdout}")

                # 切换到gh-pages分支
                checkout_cmd = ["git", "checkout", NotificationUtil.GITHUB_BRANCH]
                logger.info(f"执行命令: {' '.join(checkout_cmd)}")
                checkout_result = subprocess.run(checkout_cmd, cwd = temp_dir, capture_output = True, text = True)
                if checkout_result.returncode != 0:
                    # 如果分支不存在，创建新分支
                    logger.warning(f"切换分支失败，尝试创建新分支: {checkout_result.stderr}")
                    create_branch_cmd = ["git", "checkout", "-b", NotificationUtil.GITHUB_BRANCH]
                    create_result = subprocess.run(create_branch_cmd, cwd = temp_dir, capture_output = True, text = True)
                    if create_result.returncode != 0:
                        logger.error(f"创建分支失败: {create_result.stderr}")
                        return None

                # 创建测试运行目录
                target_dir = os.path.join(temp_dir, test_run_dir)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                    logger.info(f"创建目录: {target_dir}")

                # 复制报告文件
                copy_cmd = ["cp", "-r", os.path.join(allure_report_dir, "."), target_dir]
                logger.info(f"执行命令: {' '.join(copy_cmd)}")
                copy_result = subprocess.run(copy_cmd, capture_output = True, text = True)
                if copy_result.returncode != 0:
                    logger.error(f"复制文件失败: {copy_result.stderr}")
                    return None

                # 检查复制是否成功
                target_index_html = os.path.join(target_dir, "index.html")
                if not os.path.exists(target_index_html):
                    logger.error(f"复制失败，目标文件不存在: {target_index_html}")
                    return None

                # 提交和推送更改
                git_add_cmd = ["git", "add", "."]
                logger.info(f"执行命令: {' '.join(git_add_cmd)}")
                add_result = subprocess.run(git_add_cmd, cwd = temp_dir, capture_output = True, text = True)
                if add_result.returncode != 0:
                    logger.error(f"git add失败: {add_result.stderr}")
                    return None

                git_commit_cmd = ["git", "commit", "-m", f"Update test report: {test_run_dir}"]
                logger.info(f"执行命令: {' '.join(git_commit_cmd)}")
                commit_result = subprocess.run(git_commit_cmd, cwd = temp_dir, capture_output = True, text = True)
                if commit_result.returncode != 0:
                    logger.error(f"git commit失败: {commit_result.stderr}")
                    if "nothing to commit" in commit_result.stderr:
                        logger.info("没有更改，继续推送")
                    else:
                        return None

                git_push_cmd = ["git", "push", "origin", NotificationUtil.GITHUB_BRANCH]
                logger.info(f"执行命令: {' '.join(git_push_cmd)}")
                push_result = subprocess.run(git_push_cmd, cwd = temp_dir, capture_output = True, text = True)
                if push_result.returncode != 0:
                    logger.error(f"git push失败: {push_result.stderr}")
                    return None

                # 生成报告URL
                report_url = f"https://{NotificationUtil.GITHUB_REPO.split('/')[0]}.github.io/{NotificationUtil.GITHUB_REPO.split('/')[1]}/{test_run_dir}/index.html"
                logger.info(f"报告已上传到GitHub Pages: {report_url}")
                return report_url
            except Exception as e:
                logger.error(f"上传报告到GitHub Pages失败: {str(e)}")
                return None
        elif NotificationUtil.CLOUD_STORAGE_TYPE == "aliyun_oss":
            return None
        elif NotificationUtil.CLOUD_STORAGE_TYPE == "tencent_cos":
            return None
        elif NotificationUtil.CLOUD_STORAGE_TYPE == "aws_s3":
            return None
        else:
            logger.error("不支持的云存储类型")
            return None

    @staticmethod
    def send_wechat_notification(report_url: str = None, zip_file_path: str = None) -> bool:
        """
        发送企业微信通知

        Args:
            report_url: 云存储上的报告URL
            zip_file_path: 压缩文件路径

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始发送企业微信通知...")

        # 构建消息内容
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## 测试报告通知\n" +
                           f"**测试时间**: {path_util.get_test_run_dir()}\n" +
                           f"**测试结果**: 测试已完成\n"
            }
        }

        # 如果有报告URL，添加到消息中
        if report_url:
            message["markdown"]["content"] += f"**报告链接**: [查看报告]({report_url})\n"

        try:
            # 发送消息
            response = requests.post(NotificationUtil.WECHAT_WEBHOOK_URL, json = message)
            response.raise_for_status()
            logger.info("企业微信通知发送成功")

            # 有压缩文件，发送文件
            if zip_file_path and os.path.exists(zip_file_path):
                with open(zip_file_path, 'rb') as f:
                    files = {'media': f}
                    params = {'key': NotificationUtil.WECHAT_WEBHOOK_URL.split('key=')[1]}
                    file_response = requests.post(
                        "https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media",
                        params = params,
                        files = files
                    )
                    file_response.raise_for_status()
                    logger.info("测试报告文件发送成功")

            return True
        except Exception as e:
            logger.error(f"发送企业微信通知失败: {str(e)}")
            return False

    @staticmethod
    def send_feishu_notification(report_url: str = None, zip_file_path: str = None) -> bool:
        """
        发送飞书通知

        Args:
            report_url: 云存储上的报告URL
            zip_file_path: 压缩文件路径

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始发送飞书通知...")

        # 构建消息内容
        message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**测试时间**: {path_util.get_test_run_dir()}",
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": "**测试结果**: 测试已完成",
                            "tag": "lark_md"
                        }
                    }
                ],
                "header": {
                    "title": {
                        "content": "测试报告通知",
                        "tag": "plain_text"
                    }
                }
            }
        }

        # 如果有报告URL，添加到消息中
        if report_url:
            message["card"]["elements"].append({
                "tag": "div",
                "text": {
                    "content": f"**报告链接**: [查看报告]({report_url})",
                    "tag": "lark_md"
                }
            })

        try:
            # 发送消息
            response = requests.post(NotificationUtil.FEISHU_WEBHOOK_URL, json = message)
            response.raise_for_status()
            logger.info("飞书通知发送成功")

            return True
        except Exception as e:
            logger.error(f"发送飞书通知失败: {str(e)}")
            return False

    @staticmethod
    def send_report_to_wechat(upload_to_cloud: bool = True) -> bool:
        """
        发送测试报告到企业微信

        Args:
            upload_to_cloud: 是否先上传到云存储

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始发送测试报告到企业微信...")

        report_url = None

        # 先尝试上传到云存储
        if upload_to_cloud:
            report_url = NotificationUtil.upload_report_to_cloud()

        # 压缩报告（包含allure-results）
        zip_file_path = NotificationUtil.zip_report(include_results = True)

        # 发送企业微信通知
        return NotificationUtil.send_wechat_notification(report_url, zip_file_path)

    @staticmethod
    def send_report_to_feishu(upload_to_cloud: bool = True) -> bool:
        """
        发送测试报告到飞书

        Args:
            upload_to_cloud: 是否先上传到云存储

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始发送测试报告到飞书...")

        report_url = None

        # 先尝试上传到云存储
        if upload_to_cloud:
            report_url = NotificationUtil.upload_report_to_cloud()

        # 压缩报告（包含allure-results）
        zip_file_path = NotificationUtil.zip_report(include_results = True)

        # 发送飞书通知
        return NotificationUtil.send_feishu_notification(report_url, zip_file_path)


notification_util = NotificationUtil()

__all__ = ['NotificationUtil', 'notification_util']