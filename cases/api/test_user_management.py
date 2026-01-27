"""
-------------------------------------------------
File:           test_user_management.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
API测试样例 - 用户管理功能测试
包括用户注册、登录、获取用户信息和更新用户信息等测试场景
-------------------------------------------------
"""
import json
import os
# 添加项目根目录到Python路径
import sys
from typing import Dict, Any

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger_util import logger
from utils.api.api_client import ApiClient
from utils.api.request_manager import RequestManager
from utils.common_util import CommonUtils


class TestUserManagement:
    """
    用户管理功能测试类
    包含用户注册、登录、获取和更新用户信息的测试用例
    """

    @pytest.fixture(scope = "class", autouse = True)
    def setup_class(self):
        """
        测试类级别的初始化
        设置API客户端和请求管理器
        """
        logger.info("=" * 60)
        logger.info("开始执行用户管理功能测试")
        logger.info("=" * 60)

        # 初始化API客户端
        self.api_client = ApiClient()

        # 初始化请求管理器
        self.request_manager = RequestManager()

        # 初始化通用工具
        self.utils = CommonUtils()

        # 使用os模块构建路径, 避免依赖config.DATA_DIR
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.test_data_path = os.path.join(
            self.project_root,
            "data",
            "test_data",
            "api_test_data.json"
        )

        try:
            with open(self.test_data_path, 'r', encoding = 'utf-8') as f:
                self.test_data = json.load(f)
            logger.info(f"成功加载测试数据: {self.test_data_path}")
        except Exception as e:
            logger.error(f"加载测试数据失败: {str(e)}")
            pytest.skip("无法加载测试数据,跳过测试")

        # 测试环境信息
        logger.info(f"当前测试环境: test")  # 使用默认环境值, 避免config属性错误
        logger.info(f"API基础URL: {self.api_client.base_url}")

        yield

        logger.info("=" * 60)
        logger.info("用户管理功能测试执行完成")
        logger.info("=" * 60)

        # 清理测试资源
        self.api_client.close()

    @pytest.mark.smoke
    @pytest.mark.api
    def test_user_registration_success(self):
        """
        测试用户注册功能 - 成功场景
        使用有效数据进行用户注册
        """
        logger.info("\n开始测试: 用户注册成功场景")

        # 获取测试数据
        reg_data = self.test_data["test_user_registration"]["valid_data"]
        expected = self.test_data["test_user_registration"]["expected"]

        # 添加时间戳到用户名,确保唯一性
        unique_username = f"{reg_data['username']}_{self.utils.get_timestamp()}"
        test_payload = reg_data.copy()
        test_payload["username"] = unique_username

        # 记录发送的数据
        logger.info(f"发送数据: {test_payload}")

        # 发送请求
        endpoint = "/api/v1/users/register"
        response = self.api_client.post(
            endpoint = endpoint,
            json = test_payload,
            headers = {"Content-Type": "application/json"}
        )

        # 记录响应
        logger.info(f"响应状态码: {response.status_code}")
        logger.info(f"响应内容: {response.text}")

        # 验证响应
        assert response.status_code == expected["status_code"], \
            f"期望状态码: {expected['status_code']}, 实际状态码: {response.status_code}"

        # 解析响应JSON
        response_json = response.json()

        # 验证响应内容
        assert "message" in response_json, "响应中缺少message字段"

        # 存储用户信息供后续测试使用
        if "user_id" in response_json:
            self.request_manager.store_test_data("registered_user_id", response_json["user_id"])

        self.request_manager.store_test_data("registered_username", unique_username)
        self.request_manager.store_test_data("registered_password", reg_data["password"])

        logger.info("测试通过: 用户注册成功场景")

    @pytest.mark.api
    def test_user_registration_invalid_data(self):
        """
        测试用户注册功能 - 无效数据场景
        测试缺少必填字段、无效邮箱格式和弱密码
        """
        logger.info("\n开始测试: 用户注册无效数据场景")

        # 获取测试数据
        invalid_data = self.test_data["test_user_registration"]["invalid_data"]
        error_codes = self.test_data["test_user_registration"]["expected"]["error_codes"]

        # 测试场景列表
        test_scenarios = [
            (
                "缺少用户名",
                invalid_data["missing_username"],
                error_codes["missing_required_field"]
            ),
            (
                "无效邮箱格式",
                invalid_data["invalid_email"],
                error_codes["invalid_email_format"]
            ),
            (
                "弱密码",
                invalid_data["weak_password"],
                error_codes["password_too_weak"]
            )
        ]

        # 遍历测试场景
        for scenario_name, payload, expected_error in test_scenarios:
            logger.info(f"测试子场景: {scenario_name}")
            logger.info(f"发送数据: {payload}")

            # 发送请求
            endpoint = "/api/v1/users/register"
            response = self.api_client.post(
                endpoint = endpoint,
                json = payload,
                headers = {"Content-Type": "application/json"}
            )

            # 记录响应
            logger.info(f"响应状态码: {response.status_code}")

            # 验证响应状态码 (应为400 Bad Request)
            assert response.status_code == 400, \
                f"期望状态码: 400, 实际状态码: {response.status_code}"

            # 解析响应JSON
            response_json = response.json()

            # 验证错误码
            assert "error_code" in response_json, "响应中缺少error_code字段"

            logger.info(f"子场景 '{scenario_name}' 测试通过")

        logger.info("测试通过: 用户注册无效数据场景")

    @pytest.mark.smoke
    @pytest.mark.api
    def test_user_login_success(self):
        """
        测试用户登录功能 - 成功场景
        使用之前注册的用户凭据进行登录
        """
        logger.info("\n开始测试: 用户登录成功场景")

        # 获取测试数据
        login_data = {
            "username": self.request_manager.get_test_data("registered_username"),
            "password": self.request_manager.get_test_data("registered_password")
        }
        expected = self.test_data["test_user_login"]["expected"]

        # 检查是否有注册的用户信息
        if not login_data["username"]:
            logger.warning("没有找到注册的用户信息,使用默认测试账号")
            login_data = self.test_data["test_user_login"]["valid_credentials"]

        logger.info(f"发送登录数据: {login_data}")

        # 发送登录请求
        endpoint = "/api/v1/users/login"
        response = self.api_client.post(
            endpoint = endpoint,
            json = login_data,
            headers = {"Content-Type": "application/json"}
        )

        # 记录响应
        logger.info(f"响应状态码: {response.status_code}")
        logger.info(f"响应内容: {response.text}")

        # 验证响应状态码
        assert response.status_code == expected["status_code"], \
            f"期望状态码: {expected['status_code']}, 实际状态码: {response.status_code}"

        # 解析响应JSON
        response_json = response.json()

        # 验证响应内容
        assert "token" in response_json, "响应中缺少token字段"

        # 存储认证令牌供后续测试使用
        auth_token = response_json["token"]
        self.request_manager.store_test_data("auth_token", auth_token)

        # 设置全局请求头,包含认证令牌
        self.request_manager.add_global_header("Authorization", f"Bearer {auth_token}")

        logger.info("测试通过: 用户登录成功场景")

    @pytest.mark.api
    def test_get_user_info(self):
        """
        测试获取用户信息功能
        使用认证令牌获取当前用户信息
        """
        logger.info("\n开始测试: 获取用户信息")

        # 获取认证令牌
        auth_token = self.request_manager.get_test_data("auth_token")

        # 如果没有认证令牌,先执行登录
        if not auth_token:
            logger.info("没有认证令牌,先执行登录")
            self.test_user_login_success()
            auth_token = self.request_manager.get_test_data("auth_token")

        # 发送请求获取用户信息
        endpoint = "/api/v1/users/me"
        response = self.api_client.get(
            endpoint = endpoint,
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )

        # 记录响应
        logger.info(f"响应状态码: {response.status_code}")

        # 验证响应状态码
        expected_status = self.test_data["test_get_user_info"]["expected_status_code"]
        assert response.status_code == expected_status, \
            f"期望状态码: {expected_status}, 实际状态码: {response.status_code}"

        # 解析响应JSON
        response_json = response.json()

        # 验证响应中包含所有必需字段
        expected_fields = self.test_data["test_get_user_info"]["expected_fields"]
        for field in expected_fields:
            assert field in response_json, f"用户信息中缺少必需字段: {field}"

        # 验证用户名匹配
        registered_username = self.request_manager.get_test_data("registered_username")
        if registered_username:
            assert response_json["username"] == registered_username, \
                f"用户名不匹配: 期望={registered_username}, 实际={response_json['username']}"

        logger.info("测试通过: 获取用户信息")

    @pytest.mark.api
    def test_update_user_info(self):
        """
        测试更新用户信息功能
        使用认证令牌更新当前用户的邮箱和手机号
        """
        logger.info("\n开始测试: 更新用户信息")

        # 获取认证令牌
        auth_token = self.request_manager.get_test_data("auth_token")

        # 如果没有认证令牌,先执行登录
        if not auth_token:
            logger.info("没有认证令牌,先执行登录")
            self.test_user_login_success()
            auth_token = self.request_manager.get_test_data("auth_token")

        # 获取更新测试数据
        update_data = self.test_data["test_update_user_info"]["update_data"]
        expected = self.test_data["test_update_user_info"]["expected"]

        # 添加时间戳到邮箱,确保唯一性
        unique_email = f"updated_{self.utils.get_timestamp()}@example.com"
        test_payload = update_data.copy()
        test_payload["email"] = unique_email

        logger.info(f"发送更新数据: {test_payload}")

        # 发送更新请求
        endpoint = "/api/v1/users/me"
        response = self.api_client.put(
            endpoint = endpoint,
            json = test_payload,
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )

        # 记录响应
        logger.info(f"响应状态码: {response.status_code}")
        logger.info(f"响应内容: {response.text}")

        # 验证响应状态码
        assert response.status_code == expected["status_code"], \
            f"期望状态码: {expected['status_code']}, 实际状态码: {response.status_code}"

        # 解析响应JSON
        response_json = response.json()

        # 验证响应消息
        assert "message" in response_json, "响应中缺少message字段"

        # 验证邮箱已更新
        # 重新获取用户信息进行验证
        get_response = self.api_client.get(
            endpoint = endpoint,
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )

        get_response_json = get_response.json()
        assert get_response_json["email"] == unique_email, \
            f"邮箱未更新: 期望={unique_email}, 实际={get_response_json['email']}"

        logger.info("测试通过: 更新用户信息")

    @pytest.mark.api
    def test_request_manager_hooks_demo(self):
        """
        演示请求管理器的钩子函数功能
        展示如何使用请求前和请求后的钩子函数处理请求和响应
        """
        logger.info("\n开始测试: 请求管理器钩子函数演示")

        # 定义请求前钩子函数
        def pre_request_hook(request_params: Dict[str, Any]) -> Dict[str, Any]:
            """
            请求前钩子函数
            可以修改请求参数
            """
            logger.info("执行请求前钩子函数")
            # 添加自定义头部
            if "headers" not in request_params:
                request_params["headers"] = {}
            request_params["headers"]["X-Test-Hook"] = "pre_request"
            return request_params

        # 定义请求后钩子函数
        def post_request_hook(response: Any, request_params: Dict[str, Any]) -> Any:
            """
            请求后钩子函数
            可以处理响应
            """
            logger.info("执行请求后钩子函数")
            logger.info(f"响应状态码: {response.status_code}")
            return response

        # 设置钩子函数
        self.request_manager.set_pre_request_hook(pre_request_hook)
        self.request_manager.set_post_request_hook(post_request_hook)

        # 使用请求管理器发送请求
        endpoint = "/api/v1/users/me"
        auth_token = self.request_manager.get_test_data("auth_token")

        if not auth_token:
            logger.warning("没有认证令牌,使用健康检查端点替代")
            endpoint = "/api/v1/health"

        response = self.request_manager.send_request(
            method = "GET",
            endpoint = endpoint,
            headers = {
                "Authorization": f"Bearer {auth_token}" if auth_token else "",
                "Content-Type": "application/json"
            }
        )

        # 验证响应
        assert response is not None, "请求管理器返回None"

        # 清除钩子函数
        self.request_manager.clear_hooks()

        logger.info("测试通过: 请求管理器钩子函数演示")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])
