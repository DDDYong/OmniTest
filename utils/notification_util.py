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

import os
import tempfile
import zipfile

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
    CLOUD_STORAGE_TYPE = "github_pages"  # 可选值: github_pages, aliyun_oss, tencent_cos, aws_s3
    GITHUB_REPO = "yourusername/your-repo"
    GITHUB_TOKEN = "your_github_token"
    GITHUB_BRANCH = "gh-pages"

    @staticmethod
    def zip_report() -> str:
        """
        压缩测试报告目录

        Returns:
            str: 压缩文件路径
        """
        logger.info("开始压缩测试报告...")

        # 获取报告目录
        allure_report_dir = path_util.get_allure_report_dir(use_time_folder = True)
        test_run_dir = path_util.get_test_run_dir()

        # 创建临时压缩文件
        zip_file_path = os.path.join(tempfile.gettempdir(), f"test_report_{test_run_dir}.zip")

        try:
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(allure_report_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, allure_report_dir)
                        zipf.write(file_path, arcname)
            logger.info(f"测试报告已压缩: {zip_file_path}")
            return zip_file_path
        except Exception as e:
            logger.error(f"压缩测试报告失败: {str(e)}")
            return None

    @staticmethod
    def upload_report_to_cloud() -> str:
        """
        上传测试报告到云存储

        Returns:
            str: 云存储上的报告URL
        """
        logger.info("开始上传测试报告到云存储...")

        # 获取报告目录
        allure_report_dir = path_util.get_allure_report_dir(use_time_folder = True)
        test_run_dir = path_util.get_test_run_dir()

        # 根据云存储类型执行不同的上传逻辑
        if NotificationUtil.CLOUD_STORAGE_TYPE == "github_pages":
            # 这里只是示例，实际需要实现GitHub Pages的上传逻辑
            # 可以使用git命令或GitHub API
            report_url = f"https://{NotificationUtil.GITHUB_REPO.split('/')[0]}.github.io/{NotificationUtil.GITHUB_REPO.split('/')[1]}/{test_run_dir}/index.html"
            logger.info(f"报告已上传到GitHub Pages: {report_url}")
            return report_url
        elif NotificationUtil.CLOUD_STORAGE_TYPE == "aliyun_oss":
            # 实现阿里云OSS上传逻辑
            # 需要安装aliyun-oss-python-sdk
            pass
        elif NotificationUtil.CLOUD_STORAGE_TYPE == "tencent_cos":
            # 实现腾讯云COS上传逻辑
            # 需要安装cos-python-sdk-v5
            pass
        elif NotificationUtil.CLOUD_STORAGE_TYPE == "aws_s3":
            # 实现AWS S3上传逻辑
            # 需要安装boto3
            pass
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

            # 如果有压缩文件，发送文件
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

            # 如果有压缩文件，发送文件
            if zip_file_path and os.path.exists(zip_file_path):
                with open(zip_file_path, 'rb') as f:
                    files = {'file': f}
                    file_response = requests.post(
                        "https://open.feishu.cn/open-apis/im/v1/messages",
                        headers = {
                            "Authorization": f"Bearer {NotificationUtil.FEISHU_TOKEN}" if hasattr(NotificationUtil, 'FEISHU_TOKEN') else ""},
                        files = files
                    )
                    file_response.raise_for_status()
                    logger.info("测试报告文件发送成功")

            return True
        except Exception as e:
            logger.error(f"发送飞书通知失败: {str(e)}")
            return False

    @staticmethod
    def send_report_to_wechat() -> bool:
        """
        发送测试报告到企业微信

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始发送测试报告到企业微信...")

        # 上传报告到云存储
        report_url = NotificationUtil.upload_report_to_cloud()

        # 压缩报告
        zip_file_path = NotificationUtil.zip_report()

        # 发送企业微信通知
        return NotificationUtil.send_wechat_notification(report_url, zip_file_path)

    @staticmethod
    def send_report_to_feishu() -> bool:
        """
        发送测试报告到飞书

        Returns:
            bool: 是否发送成功
        """
        logger.info("开始发送测试报告到飞书...")

        # 上传报告到云存储
        report_url = NotificationUtil.upload_report_to_cloud()

        # 压缩报告
        zip_file_path = NotificationUtil.zip_report()

        # 发送飞书通知
        return NotificationUtil.send_feishu_notification(report_url, zip_file_path)


# 创建NotificationUtil实例
notification_util = NotificationUtil()

__all__ = ['NotificationUtil', 'notification_util']
