"""
-------------------------------------------------
File:           locust_base.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
Locust性能测试基础封装,提供性能测试的基础类和功能,包括任务集基类、用户基类和监听器等
-------------------------------------------------
"""
import json
import os
import time
from typing import Optional, Dict, Any, List

from locust import HttpUser, TaskSet, between, events

from config.config_manager import config
from utils.common_util import CommonUtils
from utils.file_util import DataHandler
from utils.logger_util import logger


class PerformanceBaseTaskSet(TaskSet):
    """
    性能测试任务集基类
    所有性能测试任务集都应继承此类
    """

    def __init__(self, parent):
        """
        初始化任务集
        
        Args:
            parent: 父类实例（通常是HttpUser）
        """
        super().__init__(parent)
        self.utils = CommonUtils()
        self.data_handler = DataHandler()
        self.user_data: Dict[str, Any] = {}
        self.results: List[Dict[str, Any]] = []

    def on_start(self):
        """
        用户开始执行任务前的初始化操作
        可以在这里进行登录、准备测试数据等操作
        """
        logger.info(f"用户 {self.parent.id} 开始执行任务")
        # 加载用户测试数据
        self._load_user_data()

    def on_stop(self):
        """
        用户停止执行任务后的清理操作
        可以在这里进行登出、保存测试结果等操作
        """
        logger.info(f"用户 {self.parent.id} 停止执行任务")
        # 保存测试结果
        if self.results:
            self._save_results()

    def _load_user_data(self):
        """
        加载用户测试数据
        从data目录加载对应的性能测试数据
        """
        try:
            # 获取当前类名作为数据文件名称
            class_name = self.__class__.__name__
            data_files = [
                os.path.join(config.DATA_DIR, f"performance_{class_name}.json"),
                os.path.join(config.DATA_DIR, f"performance_{class_name}.yaml"),
                os.path.join(config.DATA_DIR, f"performance_{class_name}.yml")
            ]

            # 尝试加载第一个存在的数据文件
            for data_file in data_files:
                if os.path.exists(data_file):
                    self.user_data = self.data_handler.load_data(data_file)
                    logger.info(f"已加载用户测试数据: {data_file}")
                    break
        except Exception as e:
            logger.error(f"加载用户测试数据失败: {str(e)}")

    def _save_results(self):
        """
        保存测试结果到文件
        """
        try:
            # 生成结果文件路径
            timestamp = self.utils.get_timestamp()
            results_dir = os.path.join(config.REPORT_DIR, "performance_results")
            os.makedirs(results_dir, exist_ok = True)

            # 保存结果
            result_file = os.path.join(results_dir, f"results_{timestamp}.json")
            with open(result_file, "w", encoding = "utf-8") as f:
                json.dump(self.results, f, ensure_ascii = False, indent = 2)

            logger.info(f"测试结果已保存到: {result_file}")
        except Exception as e:
            logger.error(f"保存测试结果失败: {str(e)}")

    def send_request(self, method: str, url: str, name: Optional[str] = None,
                     headers: Optional[Dict[str, str]] = None,
                     data: Optional[Any] = None,
                     json_data: Optional[Dict[str, Any]] = None,
                     params: Optional[Dict[str, Any]] = None,
                     expected_status: int = 200,
                     response_time_threshold: Optional[int] = None) -> Dict[str, Any]:
        """
        发送HTTP请求并记录响应时间和结果
        
        Args:
            method: 请求方法（GET, POST, PUT, DELETE等）
            url: 请求URL
            name: Locust统计中显示的请求名称
            headers: 请求头
            data: 请求数据（表单数据）
            json_data: JSON请求数据
            params: URL查询参数
            expected_status: 期望的HTTP状态码
            response_time_threshold: 响应时间阈值（毫秒）
            
        Returns:
            Dict[str, Any]: 包含请求结果的字典
        """
        start_time = time.time()
        result = {
            "method": method,
            "url": url,
            "name": name or url,
            "start_time": start_time,
            "timestamp": self.utils.get_timestamp(),
            "user_id": self.parent.id,
        }

        try:
            # 发送请求
            response = self.client.request(
                method = method,
                url = url,
                name = name,
                headers = headers,
                data = data,
                json = json_data,
                params = params,
                catch_response = True
            )

            # 计算响应时间
            response_time = int((time.time() - start_time) * 1000)
            result["response_time"] = response_time
            result["status_code"] = response.status_code

            # 验证响应状态码
            if response.status_code != expected_status:
                response.failure(f"期望状态码 {expected_status},实际状态码 {response.status_code}")
                result["success"] = False
                result["error"] = f"状态码不匹配: {response.status_code}"
            else:
                # 检查响应时间
                if response_time_threshold and response_time > response_time_threshold:
                    response.failure(f"响应时间超过阈值: {response_time}ms > {response_time_threshold}ms")
                    result["success"] = False
                    result["error"] = f"响应时间过长: {response_time}ms"
                else:
                    response.success()
                    result["success"] = True

            # 尝试解析JSON响应
            try:
                result["response_json"] = response.json()
            except (ValueError, TypeError):
                result["response_text"] = response.text[:500]  # 只保存部分文本避免过大

        except Exception as e:
            # 计算响应时间
            response_time = int((time.time() - start_time) * 1000)
            result["response_time"] = response_time
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"请求 {method} {url} 失败: {str(e)}")

        # 保存结果
        self.results.append(result)
        return result

    def get_request(self, url: str, name: Optional[str] = None,
                    headers: Optional[Dict[str, str]] = None,
                    params: Optional[Dict[str, Any]] = None,
                    expected_status: int = 200,
                    response_time_threshold: Optional[int] = None) -> Dict[str, Any]:
        """
        发送GET请求
        
        Args:
            url: 请求URL
            name: Locust统计中显示的请求名称
            headers: 请求头
            params: URL查询参数
            expected_status: 期望的HTTP状态码
            response_time_threshold: 响应时间阈值（毫秒）
            
        Returns:
            Dict[str, Any]: 包含请求结果的字典
        """
        return self.send_request(
            method = "GET",
            url = url,
            name = name,
            headers = headers,
            params = params,
            expected_status = expected_status,
            response_time_threshold = response_time_threshold
        )

    def post_request(self, url: str, name: Optional[str] = None,
                     headers: Optional[Dict[str, str]] = None,
                     data: Optional[Any] = None,
                     json_data: Optional[Dict[str, Any]] = None,
                     params: Optional[Dict[str, Any]] = None,
                     expected_status: int = 200,
                     response_time_threshold: Optional[int] = None) -> Dict[str, Any]:
        """
        发送POST请求
        
        Args:
            url: 请求URL
            name: Locust统计中显示的请求名称
            headers: 请求头
            data: 请求数据（表单数据）
            json_data: JSON请求数据
            params: URL查询参数
            expected_status: 期望的HTTP状态码
            response_time_threshold: 响应时间阈值（毫秒）
            
        Returns:
            Dict[str, Any]: 包含请求结果的字典
        """
        return self.send_request(
            method = "POST",
            url = url,
            name = name,
            headers = headers,
            data = data,
            json_data = json_data,
            params = params,
            expected_status = expected_status,
            response_time_threshold = response_time_threshold
        )

    def put_request(self, url: str, name: Optional[str] = None,
                    headers: Optional[Dict[str, str]] = None,
                    data: Optional[Any] = None,
                    json_data: Optional[Dict[str, Any]] = None,
                    params: Optional[Dict[str, Any]] = None,
                    expected_status: int = 200,
                    response_time_threshold: Optional[int] = None) -> Dict[str, Any]:
        """
        发送PUT请求
        
        Args:
            url: 请求URL
            name: Locust统计中显示的请求名称
            headers: 请求头
            data: 请求数据（表单数据）
            json_data: JSON请求数据
            params: URL查询参数
            expected_status: 期望的HTTP状态码
            response_time_threshold: 响应时间阈值（毫秒）
            
        Returns:
            Dict[str, Any]: 包含请求结果的字典
        """
        return self.send_request(
            method = "PUT",
            url = url,
            name = name,
            headers = headers,
            data = data,
            json_data = json_data,
            params = params,
            expected_status = expected_status,
            response_time_threshold = response_time_threshold
        )

    def delete_request(self, url: str, name: Optional[str] = None,
                       headers: Optional[Dict[str, str]] = None,
                       params: Optional[Dict[str, Any]] = None,
                       expected_status: int = 200,
                       response_time_threshold: Optional[int] = None) -> Dict[str, Any]:
        """
        发送DELETE请求
        
        Args:
            url: 请求URL
            name: Locust统计中显示的请求名称
            headers: 请求头
            params: URL查询参数
            expected_status: 期望的HTTP状态码
            response_time_threshold: 响应时间阈值（毫秒）
            
        Returns:
            Dict[str, Any]: 包含请求结果的字典
        """
        return self.send_request(
            method = "DELETE",
            url = url,
            name = name,
            headers = headers,
            params = params,
            expected_status = expected_status,
            response_time_threshold = response_time_threshold
        )

    def set_task_weight(self, task_name: str, weight: int):
        """
        设置任务权重
        
        Args:
            task_name: 任务方法名
            weight: 权重值
        """
        try:
            task_method = getattr(self, task_name)
            if hasattr(task_method, "weight"):
                task_method.weight = weight
                logger.info(f"已设置任务 {task_name} 的权重为 {weight}")
        except Exception as e:
            logger.error(f"设置任务权重失败: {str(e)}")

    def login(self, url: str, username: str, password: str,
              name: str = "login",
              headers: Optional[Dict[str, str]] = None,
              response_token_key: str = "token") -> Optional[str]:
        """
        执行登录操作
        
        Args:
            url: 登录URL
            username: 用户名
            password: 密码
            name: 请求名称
            headers: 请求头
            response_token_key: 响应中token的键名
            
        Returns:
            Optional[str]: 登录成功返回token,失败返回None
        """
        if not headers:
            headers = {"Content-Type": "application/json"}

        # 发送登录请求
        result = self.post_request(
            url = url,
            name = name,
            headers = headers,
            json_data = {"username": username, "password": password},
            expected_status = 200
        )

        # 提取token
        if result.get("success"):
            response_data = result.get("response_json", {})
            if response_token_key in response_data:
                token = response_data[response_token_key]
                # 保存token到父类,以便在后续请求中使用
                self.parent.token = token
                logger.info(f"用户 {self.parent.id} 登录成功")
                return token
            else:
                logger.error(f"登录响应中未找到token键: {response_token_key}")
        else:
            logger.error(f"用户 {self.parent.id} 登录失败: {result.get('error')}")

        return None

    def logout(self, url: str, name: str = "logout",
               headers: Optional[Dict[str, str]] = None) -> bool:
        """
        执行登出操作
        
        Args:
            url: 登出URL
            name: 请求名称
            headers: 请求头
            
        Returns:
            bool: 是否登出成功
        """
        if not headers:
            headers = {"Content-Type": "application/json"}

        # 如果有token,添加到请求头
        if hasattr(self.parent, "token") and self.parent.token:
            headers["Authorization"] = f"Bearer {self.parent.token}"

        # 发送登出请求
        result = self.post_request(
            url = url,
            name = name,
            headers = headers,
            expected_status = 200
        )

        # 清除token
        if hasattr(self.parent, "token"):
            delattr(self.parent, "token")

        return result.get("success", False)


class PerformanceBaseUser(HttpUser):
    """
    性能测试用户基类
    所有性能测试用户都应继承此类
    """
    # 设置等待时间范围（用户执行任务之间的等待时间）
    wait_time = between(1, 3)  # 默认在1-3秒之间随机等待

    def __init__(self, environment):
        """
        初始化用户
        
        Args:
            environment: Locust环境对象
        """
        super().__init__(environment)
        self.id = f"user_{id(self)}"
        self.token = None
        self.start_time = time.time()

    def on_start(self):
        """
        用户开始执行任务前的初始化操作
        可以在这里设置通用的请求头、环境变量等
        """
        logger.info(f"用户 {self.id} 初始化完成")

        # 设置默认请求头
        self.client.headers.update({
            "User-Agent": "OmniTest-Locust-Performance-Test",
            "Accept": "application/json"
        })

    def on_stop(self):
        """
        用户停止执行任务后的清理操作
        """
        # 计算用户执行时间
        execution_time = time.time() - self.start_time
        logger.info(f"用户 {self.id} 执行完成,总执行时间: {execution_time:.2f}秒")

    def set_wait_time(self, min_wait: float, max_wait: float):
        """
        设置任务间的等待时间范围
        
        Args:
            min_wait: 最小等待时间（秒）
            max_wait: 最大等待时间（秒）
        """
        self.wait_time = between(min_wait, max_wait)
        logger.info(f"已设置等待时间范围: {min_wait}-{max_wait}秒")


# 自定义监听器
class PerformanceTestListener:
    """
    性能测试监听器
    用于监听Locust事件并执行相应操作
    """

    def __init__(self):
        """
        初始化监听器
        """
        # 注册事件处理函数
        events.test_start.add_listener(self.on_test_start)
        events.test_stop.add_listener(self.on_test_stop)
        events.request_success.add_listener(self.on_request_success)
        events.request_failure.add_listener(self.on_request_failure)
        events.user_error.add_listener(self.on_user_error)
        events.spawning_complete.add_listener(self.on_spawning_complete)

        # 统计数据
        self.stats = {
            "start_time": None,
            "stop_time": None,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0,
            "min_response_time": float("inf"),
            "max_response_time": 0,
            "request_errors": {}
        }

    def on_test_start(self, environment, **kwargs):
        """
        测试开始事件处理
        
        Args:
            environment: Locust环境对象
            **kwargs: 其他参数
        """
        self.stats["start_time"] = time.time()
        logger.info("性能测试开始")

        # 输出测试配置信息
        if environment.parsed_options:
            logger.info(f"测试配置: 用户数={environment.parsed_options.num_users}, "
                        f"生成率={environment.parsed_options.spawn_rate}, "
                        f"运行时间={environment.parsed_options.run_time or '未指定'}")

    def on_test_stop(self, environment, **kwargs):
        """
        测试停止事件处理
        
        Args:
            environment: Locust环境对象
            **kwargs: 其他参数
        """
        self.stats["stop_time"] = time.time()
        logger.info("性能测试停止")

        # 计算测试总时间
        total_time = self.stats["stop_time"] - self.stats["start_time"]

        # 计算平均响应时间
        avg_response_time = 0
        if self.stats["successful_requests"] > 0:
            avg_response_time = self.stats["total_response_time"] / self.stats["successful_requests"]

        # 计算成功率
        success_rate = 0
        if self.stats["total_requests"] > 0:
            success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100

        # 输出测试总结
        logger.info("=" * 80)
        logger.info("性能测试总结")
        logger.info(f"总执行时间: {total_time:.2f}秒")
        logger.info(f"总请求数: {self.stats['total_requests']}")
        logger.info(f"成功请求数: {self.stats['successful_requests']}")
        logger.info(f"失败请求数: {self.stats['failed_requests']}")
        logger.info(f"请求成功率: {success_rate:.2f}%")
        logger.info(f"平均响应时间: {avg_response_time:.2f}ms")
        logger.info(f"最小响应时间: {self.stats['min_response_time']}ms")
        logger.info(f"最大响应时间: {self.stats['max_response_time']}ms")

        # 输出错误统计
        if self.stats["request_errors"]:
            logger.info("错误统计:")
            for error, count in self.stats["request_errors"].items():
                logger.info(f"  {error}: {count}次")

        logger.info("=" * 80)

        # 保存测试报告
        self._save_test_report(total_time, avg_response_time, success_rate)

    def on_request_success(self, request_type, name, response_time, response_length, **kwargs):
        """
        请求成功事件处理
        
        Args:
            request_type: 请求类型（GET, POST等）
            name: 请求名称
            response_time: 响应时间（毫秒）
            response_length: 响应长度
            **kwargs: 其他参数
        """
        # 更新统计数据
        self.stats["total_requests"] += 1
        self.stats["successful_requests"] += 1
        self.stats["total_response_time"] += response_time

        # 更新最小和最大响应时间
        if response_time < self.stats["min_response_time"]:
            self.stats["min_response_time"] = response_time
        if response_time > self.stats["max_response_time"]:
            self.stats["max_response_time"] = response_time

    def on_request_failure(self, request_type, name, response_time, exception, **kwargs):
        """
        请求失败事件处理
        
        Args:
            request_type: 请求类型（GET, POST等）
            name: 请求名称
            response_time: 响应时间（毫秒）
            exception: 异常信息
            **kwargs: 其他参数
        """
        # 更新统计数据
        self.stats["total_requests"] += 1
        self.stats["failed_requests"] += 1

        # 更新错误统计
        error_msg = str(exception)
        if error_msg not in self.stats["request_errors"]:
            self.stats["request_errors"][error_msg] = 0
        self.stats["request_errors"][error_msg] += 1

    def on_user_error(self, user_instance, exception, tb, **kwargs):
        """
        用户错误事件处理
        
        Args:
            user_instance: 用户实例
            exception: 异常信息
            tb: 堆栈跟踪
            **kwargs: 其他参数
        """
        logger.error(f"用户错误: {str(exception)}")

    def on_spawning_complete(self, environment, **kwargs):
        """
        用户生成完成事件处理
        
        Args:
            environment: Locust环境对象
            **kwargs: 其他参数
        """
        logger.info(f"所有用户生成完成,总用户数: {environment.runner.user_count}")

    def _save_test_report(self, total_time, avg_response_time, success_rate):
        """
        保存测试报告
        
        Args:
            total_time: 测试总时间
            avg_response_time: 平均响应时间
            success_rate: 成功率
        """
        try:
            # 创建报告目录
            report_dir = os.path.join(config.REPORT_DIR, "performance")
            os.makedirs(report_dir, exist_ok = True)

            # 生成报告文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(report_dir, f"performance_report_{timestamp}.json")

            # 构建报告数据
            report_data = {
                "timestamp": timestamp,
                "total_time": round(total_time, 2),
                "total_requests": self.stats["total_requests"],
                "successful_requests": self.stats["successful_requests"],
                "failed_requests": self.stats["failed_requests"],
                "success_rate": round(success_rate, 2),
                "avg_response_time": round(avg_response_time, 2),
                "min_response_time": self.stats["min_response_time"],
                "max_response_time": self.stats["max_response_time"],
                "request_errors": self.stats["request_errors"]
            }

            # 保存报告
            with open(report_file, "w", encoding = "utf-8") as f:
                json.dump(report_data, f, ensure_ascii = False, indent = 2)

            logger.info(f"性能测试报告已保存: {report_file}")
        except Exception as e:
            logger.error(f"保存测试报告失败: {str(e)}")


# 创建全局监听器实例
listener = PerformanceTestListener()


class LocustMaster:
    """
    Locust主控类
    用于在代码中控制Locust测试的运行
    """

    @staticmethod
    def run_locust(file_path: str, users: int = 10, spawn_rate: int = 1,
                   run_time: Optional[str] = None, host: Optional[str] = None,
                   headless: bool = True, web_port: int = 8089,
                   csv_file: Optional[str] = None,
                   html_file: Optional[str] = None):
        """
        运行Locust测试
        
        Args:
            file_path: Locust测试文件路径
            users: 用户数
            spawn_rate: 用户生成速率
            run_time: 运行时间,格式如 "1m", "30s"
            host: 测试目标主机
            headless: 是否以无头模式运行
            web_port: Web界面端口
            csv_file: CSV结果文件前缀
            html_file: HTML报告文件路径
        """
        import sys
        from locust.main import main

        # 构建命令行参数
        args = [sys.argv[0], file_path]

        if headless:
            args.extend(["--headless"])

        if host:
            args.extend(["--host", host])

        args.extend(["--users", str(users)])
        args.extend(["--spawn-rate", str(spawn_rate)])

        if run_time:
            args.extend(["--run-time", run_time])

        if web_port != 8089:
            args.extend(["--web-port", str(web_port)])

        if csv_file:
            args.extend(["--csv", csv_file])

        if html_file:
            args.extend(["--html", html_file])

        # 保存原始的sys.argv
        original_argv = sys.argv
        try:
            # 替换sys.argv
            sys.argv = args
            # 运行Locust
            logger.info(f"开始运行Locust测试: {file_path}")
            main()
        finally:
            # 恢复原始的sys.argv
            sys.argv = original_argv
