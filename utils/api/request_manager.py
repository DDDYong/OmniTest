"""
-------------------------------------------------
File:           request_manager.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
接口自动化请求管理器,提供统一的API请求处理、响应验证和结果分析功能,支持钩子函数和数据提取
-------------------------------------------------
"""
import json
from typing import Dict, Any, Optional, List, Callable

from utils.common_util import CommonUtils
from utils.decorator_util import log_function, exception_handler
from utils.logger_util import logger
from .api_client import ApiClient


class RequestManager:
    """
    请求管理器类,封装API客户端并提供额外的功能
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化请求管理器
        
        Args:
            base_url: 基础URL
        """
        self.api_client = ApiClient(base_url)
        self.utils = CommonUtils()
        self.pre_request_hooks: List[Callable] = []
        self.post_response_hooks: List[Callable] = []
        self.global_headers = {}
        self.test_data: Dict[str, Any] = {}

    def set_pre_request_hook(self, hook: Callable) -> None:
        """
        设置请求前钩子函数
        
        Args:
            hook: 钩子函数,接收请求参数作为参数
        """
        self.pre_request_hooks.append(hook)
        logger.info(f"已添加请求前钩子函数: {hook.__name__}")

    def set_post_response_hook(self, hook: Callable) -> None:
        """
        设置响应后钩子函数
        
        Args:
            hook: 钩子函数,接收响应对象作为参数
        """
        self.post_response_hooks.append(hook)
        logger.info(f"已添加响应后钩子函数: {hook.__name__}")

    def set_global_header(self, key: str, value: str) -> None:
        """
        设置全局请求头
        
        Args:
            key: 请求头名称
            value: 请求头值
        """
        self.global_headers[key] = value
        self.api_client.set_headers({key: value})
        logger.info(f"已设置全局请求头: {key}={value}")

    def set_global_headers(self, headers: Dict[str, str]) -> None:
        """
        设置多个全局请求头
        
        Args:
            headers: 请求头字典
        """
        self.global_headers.update(headers)
        self.api_client.set_headers(headers)
        logger.info(f"已设置多个全局请求头: {headers}")

    def set_auth_token(self, token: str, key: str = "Authorization", prefix: str = "Bearer ") -> None:
        """
        设置认证令牌
        
        Args:
            token: 认证令牌
            key: 请求头键名,默认为"Authorization"
            prefix: 令牌前缀,默认为"Bearer "
        """
        auth_header = {key: f"{prefix}{token}"}
        self.set_global_header(key, f"{prefix}{token}")
        self.test_data["auth_token"] = token
        logger.info(f"已设置认证令牌")

    def store_test_data(self, key: str, value: Any) -> None:
        """
        存储测试数据
        
        Args:
            key: 数据键名
            value: 数据值
        """
        self.test_data[key] = value
        logger.debug(f"已存储测试数据: {key}={value}")

    def get_test_data(self, key: str, default: Any = None) -> Any:
        """
        获取测试数据
        
        Args:
            key: 数据键名
            default: 默认值,如果键不存在则返回
            
        Returns:
            Any: 测试数据值
        """
        return self.test_data.get(key, default)

    @log_function
    def process_request(self, url: str, method: str, **kwargs) -> Dict[str, Any]:
        """
        处理API请求,包括钩子函数调用和响应处理
        
        Args:
            url: 请求URL
            method: 请求方法
            **kwargs: 其他请求参数
            
        Returns:
            Dict[str, Any]: 处理后的响应结果
        """
        # 准备请求数据
        request_data = {
            'url': url,
            'method': method,
            'kwargs': kwargs
        }

        # 执行请求前钩子
        for hook in self.pre_request_hooks:
            logger.info(f"执行请求前钩子: {hook.__name__}")
            hook(request_data)

        # 发送请求
        response = self.api_client.request(
            url = request_data['url'],
            method = request_data['method'],
            **request_data['kwargs']
        )

        # 执行响应后钩子
        for hook in self.post_response_hooks:
            logger.info(f"执行响应后钩子: {hook.__name__}")
            hook(response)

        # 处理响应
        result = self._process_response(response)

        # 记录响应结果摘要
        self._log_response_summary(result)

        return result

    def _process_response(self, response) -> Dict[str, Any]:
        """
        处理响应对象,提取有用信息
        
        Args:
            response: 响应对象
            
        Returns:
            Dict[str, Any]: 处理后的响应结果
        """
        result = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'cookies': dict(response.cookies),
            'url': response.url,
            'request_method': response.request.method,
            'request_headers': dict(response.request.headers),
            'elapsed': response.elapsed.total_seconds()
        }

        # 尝试解析JSON响应
        try:
            result['json'] = response.json()
            result['content_type'] = 'json'
        except (ValueError, json.JSONDecodeError):
            result['text'] = response.text
            result['content_type'] = 'text'

        # 获取响应大小
        result['content_length'] = len(response.content)

        return result

    def _log_response_summary(self, result: Dict[str, Any]) -> None:
        """
        记录响应摘要信息
        
        Args:
            result: 响应结果
        """
        status_code = result['status_code']
        elapsed = result['elapsed']
        content_type = result['content_type']
        content_length = result['content_length']

        # 根据状态码确定日志级别
        if 200 <= status_code < 300:
            logger.info(f"请求成功 - 状态码: {status_code}, 耗时: {elapsed:.4f}s, 内容类型: {content_type}, 大小: {content_length}字节")
        elif 300 <= status_code < 400:
            logger.warning(f"重定向 - 状态码: {status_code}, 耗时: {elapsed:.4f}s")
        elif 400 <= status_code < 500:
            logger.error(f"客户端错误 - 状态码: {status_code}, 耗时: {elapsed:.4f}s")
        else:
            logger.error(f"服务器错误 - 状态码: {status_code}, 耗时: {elapsed:.4f}s")

    def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送GET请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Dict[str, Any]: 响应结果
        """
        return self.process_request(url, 'GET', **kwargs)

    def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送POST请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Dict[str, Any]: 响应结果
        """
        return self.process_request(url, 'POST', **kwargs)

    def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送PUT请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Dict[str, Any]: 响应结果
        """
        return self.process_request(url, 'PUT', **kwargs)

    def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送DELETE请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Dict[str, Any]: 响应结果
        """
        return self.process_request(url, 'DELETE', **kwargs)

    def patch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送PATCH请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Dict[str, Any]: 响应结果
        """
        return self.process_request(url, 'PATCH', **kwargs)

    @exception_handler(default_value = False)
    def validate_response(self, result: Dict[str, Any],
                          expected_status_code: Optional[int] = None,
                          expected_content: Optional[Dict[str, Any]] = None) -> bool:
        """
        验证响应结果
        
        Args:
            result: 响应结果
            expected_status_code: 期望的状态码
            expected_content: 期望的响应内容
            
        Returns:
            bool: 是否验证通过
        """
        is_valid = True

        # 验证状态码
        if expected_status_code is not None:
            actual_status_code = result['status_code']
            if actual_status_code != expected_status_code:
                logger.error(f"状态码验证失败: 期望={expected_status_code}, 实际={actual_status_code}")
                is_valid = False
            else:
                logger.info(f"状态码验证通过: {actual_status_code}")

        # 验证响应内容
        if expected_content is not None and 'json' in result:
            for key, expected_value in expected_content.items():
                if key not in result['json']:
                    logger.error(f"响应中未找到键: {key}")
                    is_valid = False
                elif result['json'][key] != expected_value:
                    logger.error(f"值验证失败 - 键: {key}, 期望={expected_value}, 实际={result['json'][key]}")
                    is_valid = False
                else:
                    logger.info(f"值验证通过 - 键: {key}, 值: {expected_value}")

        return is_valid

    def extract_data_from_response(self, result: Dict[str, Any], json_path: str) -> Any:
        """
        从响应中提取数据
        
        Args:
            result: 响应结果
            json_path: JSON路径表达式
            
        Returns:
            Any: 提取的数据
        """
        if 'json' not in result:
            logger.error("响应不是JSON格式,无法提取数据")
            return None

        # 简单的JSON路径解析
        data = result['json']
        keys = json_path.strip('/').split('/')

        try:
            for key in keys:
                if isinstance(data, list) and key.isdigit():
                    data = data[int(key)]
                else:
                    data = data[key]
            logger.info(f"从响应中提取数据成功 - 路径: {json_path}, 值: {data}")
            return data
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"从响应中提取数据失败 - 路径: {json_path}, 错误: {str(e)}")
            return None

    def generate_test_case_data(self, template: Dict[str, Any], **replacements) -> Dict[str, Any]:
        """
        根据模板生成测试用例数据
        
        Args:
            template: 模板字典
            **replacements: 要替换的键值对
            
        Returns:
            Dict[str, Any]: 生成的测试数据
        """
        # 深度复制模板
        data = self.utils.deep_copy(template)

        # 替换数据
        for key, value in replacements.items():
            if key in data:
                data[key] = value
                logger.debug(f"已替换测试数据 - 键: {key}, 值: {value}")

        return data

    def close(self) -> None:
        """
        关闭请求管理器
        """
        self.api_client.close()
        logger.info("请求管理器已关闭")

    def __enter__(self) -> 'RequestManager':
        """
        支持上下文管理器协议
        
        Returns:
            RequestManager: 请求管理器实例
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        上下文管理器退出时关闭请求管理器
        """
        self.close()
