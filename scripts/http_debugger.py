"""
-------------------------------------------------
File:           http_debugger.py
Author:         duanyang
Date:           2025/12/29
-------------------------------------------------
Description:
This file contains the http_debugger module, which...
-------------------------------------------------
"""
import json
import time
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin

import requests


class HTTPDebugger:
    """
    HTTP请求调试工具类
    """

    def __init__(self, base_url: str = ""):
        """
        初始化调试器

        Args:
            base_url: 基础域名，可选
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.last_response = None
        self.request_history = []

    def set_base_url(self, base_url: str):
        """设置基础域名"""
        self.base_url = base_url
        print(f"✅ 基础域名已设置为: {base_url}")

    def set_default_headers(self, headers: Dict[str, str]):
        """设置默认请求头"""
        self.session.headers.update(headers)
        print(f"✅ 默认请求头已设置: {headers}")

    def send_request(self,
                     method: str,
                     endpoint: str,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Union[Dict[str, Any], str]] = None,
                     json_data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     timeout: int = 30,
                     verify_ssl: bool = True) -> Optional[requests.Response]:
        """
        发送HTTP请求

        Args:
            method: 请求方法 (GET, POST, PUT, DELETE, PATCH)
            endpoint: 接口路径
            params: URL参数
            data: 表单数据
            json_data: JSON数据
            headers: 请求头
            timeout: 超时时间(秒)
            verify_ssl: 是否验证SSL证书

        Returns:
            requests.Response对象或None
        """
        # 构建完整URL
        if self.base_url and not endpoint.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, endpoint)
        else:
            url = endpoint

        # 准备请求参数
        request_kwargs = {
            'timeout': timeout,
            'verify': verify_ssl
        }

        if params:
            request_kwargs['params'] = params

        if data:
            request_kwargs['data'] = data

        if json_data:
            request_kwargs['json'] = json_data

        if headers:
            # 临时更新请求头
            original_headers = self.session.headers.copy()
            self.session.headers.update(headers)

        # 记录请求信息
        request_info = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'method': method.upper(),
            'url': url,
            'params': params,
            'data': data,
            'json': json_data,
            'headers': headers or {}
        }

        try:
            print(f"\n🚀 发送请求...")
            print(f"📋 方法: {method.upper()}")
            print(f"🔗 URL: {url}")

            if params:
                print(f"📊 URL参数: {params}")
            if data:
                print(f"📝 表单数据: {data}")
            if json_data:
                print(f"📦 JSON数据: {json_data}")
            if headers:
                print(f"📋 请求头: {headers}")

            # 发送请求
            start_time = time.time()
            response = self.session.request(method.upper(), url, **request_kwargs)
            end_time = time.time()

            # 计算请求耗时
            duration = round((end_time - start_time) * 1000, 2)

            # 记录响应信息
            request_info.update({
                'response_status': response.status_code,
                'response_time_ms': duration,
                'response_headers': dict(response.headers),
                'response_content': response.text[:1000]  # 只记录前1000字符
            })

            self.last_response = response
            self.request_history.append(request_info)

            # 显示响应结果
            self._display_response(response, duration)

            return response

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
            request_info['error'] = str(e)
            self.request_history.append(request_info)
            return None

        finally:
            # 恢复原始请求头
            if headers:
                self.session.headers.clear()
                self.session.headers.update(original_headers)

    def _display_response(self, response: requests.Response, duration: float):
        """显示响应结果"""
        print(f"\n✅ 请求完成!")
        print(f"⏱️  耗时: {duration}ms")
        print(f"📊 状态码: {response.status_code}")
        print(f"📋 响应头:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")

        print(f"\n📄 响应内容:")
        try:
            # 尝试解析JSON
            json_data = response.json()
            print(json.dumps(json_data, indent = 2, ensure_ascii = False))
        except:
            # 如果不是JSON，显示文本内容
            content = response.text
            if len(content) > 1000:
                print(content[:1000] + "...")
            else:
                print(content)

    def get(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """发送GET请求"""
        return self.send_request('GET', endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """发送POST请求"""
        return self.send_request('POST', endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """发送PUT请求"""
        return self.send_request('PUT', endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """发送DELETE请求"""
        return self.send_request('DELETE', endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """发送PATCH请求"""
        return self.send_request('PATCH', endpoint, **kwargs)

    def show_history(self):
        """显示请求历史"""
        if not self.request_history:
            print("📜 暂无请求历史")
            return

        print(f"\n📜 请求历史 (共{len(self.request_history)}条):")
        for i, req in enumerate(self.request_history, 1):
            print(f"\n{i}. {req['timestamp']}")
            print(f"   {req['method']} {req['url']}")
            print(f"   状态码: {req.get('response_status', 'N/A')}")
            print(f"   耗时: {req.get('response_time_ms', 'N/A')}ms")
            if 'error' in req:
                print(f"   ❌ 错误: {req['error']}")

    def clear_history(self):
        """清空请求历史"""
        self.request_history.clear()
        print("🗑️  请求历史已清空")

    def get_last_response(self) -> Optional[requests.Response]:
        """获取最后一次响应"""
        return self.last_response


if __name__ == "__main__":
    # 创建调试器实例
    debugger = HTTPDebugger()

    debugger.set_base_url("http://test.api.whwxkj.cn")

    debugger.set_default_headers({
        "Content-Type": "application/json"
    })

    debugger.get("/api/dict/links", headers = {"sign": "sK/E4IYbjcN2wZV9DVXJaQ=="})

    debugger.show_history()
