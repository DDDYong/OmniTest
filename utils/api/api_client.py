"""
-------------------------------------------------
File:           api_client.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
接口自动化客户端封装,提供基础的HTTP请求方法和通用功能,支持各种HTTP方法、重试机制和请求/响应日志记录
-------------------------------------------------
"""
import json
from typing import Dict, Any, Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 直接导入配置, 使用懒加载代理
from config.config_manager import config
from utils.decorator_util import retry, timing
from utils.logger_util import logger


class ApiClient:
    """
    API客户端类,封装HTTP请求方法
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        初始化API客户端
        
        Args:
            base_url: 基础URL,默认为配置文件中的API_BASE_URL
            timeout: 请求超时时间（秒）,默认为配置文件中的DEFAULT_TIMEOUT
        """
        # 使用默认值避免依赖不存在的配置属性
        self.base_url = base_url or getattr(config, 'API_BASE_URL', 'http://test.api.whwxkj.cn')
        self.timeout = timeout or getattr(config, 'DEFAULT_TIMEOUT', 30)
        self.session = self._create_session()
        self.headers = {}
        self.cookies = {}
        self.auth = None

    def _create_session(self) -> requests.Session:
        """
        创建并配置requests会话
        
        Returns:
            requests.Session: 配置好的会话对象
        """
        session = requests.Session()

        # 配置重试策略, 使用默认值避免依赖不存在的配置属性
        retry_strategy = Retry(
            total = getattr(config, 'DEFAULT_RETRY_COUNT', 3),
            backoff_factor = 0.3,
            status_forcelist = [500, 502, 503, 504],
            allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
        )

        # 挂载适配器到会话
        adapter = HTTPAdapter(max_retries = retry_strategy, pool_connections = 50, pool_maxsize = 100)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 设置默认超时
        session.timeout = self.timeout

        return session

    def set_base_url(self, base_url: str) -> None:
        """
        设置基础URL
        
        Args:
            base_url: 基础URL
        """
        self.base_url = base_url
        logger.info(f"API客户端基础URL已设置为: {base_url}")

    def set_headers(self, headers: Dict[str, str]) -> None:
        """
        设置请求头
        
        Args:
            headers: 请求头字典
        """
        self.headers.update(headers)
        logger.debug(f"API客户端请求头已更新: {headers}")

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """
        设置Cookies
        
        Args:
            cookies: Cookies字典
        """
        self.cookies.update(cookies)
        logger.debug(f"API客户端Cookies已更新: {cookies}")

    def set_auth(self, auth: Any) -> None:
        """
        设置认证信息
        
        Args:
            auth: 认证信息,通常是(username, password)元组或其他认证对象
        """
        self.auth = auth
        logger.debug(f"API客户端认证信息已设置")

    def _prepare_request(self, url: str, method: str, **kwargs) -> Dict[str, Any]:
        """
        准备请求参数
        
        Args:
            url: 请求URL
            method: 请求方法
            **kwargs: 其他请求参数
            
        Returns:
            Dict[str, Any]: 准备好的请求参数
        """
        # 处理URL
        if not url.startswith(('http://', 'https://')):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"

        # 准备请求参数
        request_kwargs = {
            'url': url,
            'headers': {**self.headers, **kwargs.get('headers', {})},
            'cookies': {**self.cookies, **kwargs.get('cookies', {})},
            'timeout': kwargs.get('timeout', self.timeout),
            'auth': kwargs.get('auth', self.auth)
        }

        # 处理请求体
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            if 'json' in kwargs:
                request_kwargs['json'] = kwargs['json']
                # 如果没有指定Content-Type,自动设置为application/json
                if 'Content-Type' not in request_kwargs['headers']:
                    request_kwargs['headers']['Content-Type'] = 'application/json'
            elif 'data' in kwargs:
                request_kwargs['data'] = kwargs['data']
            elif 'files' in kwargs:
                request_kwargs['files'] = kwargs['files']

        # 处理查询参数
        if 'params' in kwargs:
            request_kwargs['params'] = kwargs['params']

        # 处理其他参数
        other_kwargs = ['allow_redirects', 'proxies', 'verify', 'cert']
        for key in other_kwargs:
            if key in kwargs:
                request_kwargs[key] = kwargs[key]

        return request_kwargs

    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖, 实际值会在函数内部记录
    @timing
    def request(self, url: str, method: str, **kwargs) -> Response:
        """
        发送HTTP请求
        
        Args:
            url: 请求URL
            method: 请求方法
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        method = method.upper()
        logger.info(f"准备发送{method}请求到 {url}")

        # 使用已导入的config记录日志
        logger.debug(f"请求使用重试配置: max_retries={config.DEFAULT_RETRY_COUNT}, delay={config.RETRY_INTERVAL}")

        # 准备请求参数
        request_kwargs = self._prepare_request(url, method, **kwargs)

        # 记录请求信息
        logger.debug(f"请求信息: method={method}, url={request_kwargs['url']}")
        logger.debug(f"请求头: {request_kwargs['headers']}")

        if 'params' in request_kwargs:
            logger.debug(f"查询参数: {request_kwargs['params']}")

        if method in ['POST', 'PUT', 'PATCH']:
            if 'json' in request_kwargs:
                logger.debug(f"请求体(JSON): {request_kwargs['json']}")
            elif 'data' in request_kwargs:
                logger.debug(f"请求体(DATA): {request_kwargs['data']}")

        # 发送请求
        try:
            response = self.session.request(method, **request_kwargs)

            # 记录响应信息
            logger.info(f"收到响应: status_code={response.status_code}")
            logger.debug(f"响应头: {response.headers}")

            # 尝试记录响应体
            try:
                response_json = response.json()
                logger.debug(f"响应体(JSON): {response_json}")
            except (ValueError, json.JSONDecodeError):
                response_text = response.text[:500] + ('...' if len(response.text) > 500 else '')
                logger.debug(f"响应体(TEXT): {response_text}")

            return response

        except Exception as e:
            logger.error(f"请求失败: {str(e)}")
            raise

    def get(self, url: str, **kwargs) -> Response:
        """
        发送GET请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        return self.request(url, 'GET', **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        """
        发送POST请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        return self.request(url, 'POST', **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        """
        发送PUT请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        return self.request(url, 'PUT', **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        """
        发送DELETE请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        return self.request(url, 'DELETE', **kwargs)

    def patch(self, url: str, **kwargs) -> Response:
        """
        发送PATCH请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        return self.request(url, 'PATCH', **kwargs)

    def head(self, url: str, **kwargs) -> Response:
        """
        发送HEAD请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        return self.request(url, 'HEAD', **kwargs)

    def options(self, url: str, **kwargs) -> Response:
        """
        发送OPTIONS请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response: HTTP响应对象
        """
        return self.request(url, 'OPTIONS', **kwargs)

    def close(self) -> None:
        """
        关闭会话
        """
        if hasattr(self, 'session'):
            self.session.close()
            logger.info("API客户端会话已关闭")

    def __enter__(self) -> 'ApiClient':
        """
        支持上下文管理器协议
        
        Returns:
            ApiClient: API客户端实例
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        上下文管理器退出时关闭会话
        """
        self.close()
