"""
-------------------------------------------------
File:           appium_manager.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
App自动化Appium管理器,负责启动Appium服务和管理驱动,提供设备连接和会话管理功能
-------------------------------------------------
"""
import os
import subprocess
import time
from typing import Optional, Dict, Any, List

from appium import webdriver
from appium.webdriver.appium_service import AppiumService
from appium.webdriver.webdriver import WebDriver as AppiumDriver

from utils.file import FileHandler
from utils.logger import logger


class AppiumManager:
    """
    Appium管理器类
    """

    def __init__(self, host: str = None, port: int = None, timeout: int = None):
        """
        初始化Appium管理器

        Args:
            host: Appium服务主机地址
            port: Appium服务端口
            timeout: 超时时间
        """
        self.appium_service: Optional[AppiumService] = None
        self.driver: Optional[AppiumDriver] = None
        self.service_address: Optional[str] = host
        self.service_port: Optional[int] = port
        self.timeout: Optional[int] = timeout
        self.start_time: Optional[float] = None

    def check_server_status(self, host: str = None, port: int = None) -> bool:
        """
        检查Appium服务器状态
        
        Args:
            host: Appium服务主机地址
            port: Appium服务端口
            
        Returns:
            bool: 服务器是否可用
        """
        import requests

        if host is None:
            host = self.service_address or '127.0.0.1'
        if port is None:
            port = self.service_port or 4723

        test_urls = [
            f"http://{host}:{port}/status"
        ]

        for server_url in test_urls:
            try:
                logger.info(f"检查Appium服务器状态: {server_url}")
                response = requests.get(server_url, timeout = 5)
                if response.status_code == 200:
                    logger.info(f"Appium服务器状态检查通过: {server_url}")
                    return True
                else:
                    logger.warning(f"Appium服务器状态检查失败,状态码: {response.status_code}")
            except Exception as e:
                logger.debug(f"Appium服务器状态检查失败: {str(e)}")

        logger.error("所有Appium服务器状态检查URL都失败")
        return False

    def start_appium_service(self, host: str = '127.0.0.1', port: int = 4723,
                             log_file: Optional[str] = None,
                             override_server_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        启动Appium服务
        
        Args:
            host: 主机地址
            port: 端口
            log_file: 日志文件路径
            override_server_config: 覆盖的服务器配置
            
        Returns:
            bool: 是否启动成功
        """

        if log_file is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(project_root, 'logs')
            os.makedirs(log_dir, exist_ok = True)
            log_file = os.path.join(log_dir, f"appium/appium_server_{port}.log")

        os.makedirs(os.path.dirname(log_file), exist_ok = True)

        logger.info(f"正在启动Appium服务: {host}:{port}")

        self.appium_service = AppiumService()

        service_args = [
            '--address', host,
            '--port', str(port),
            '--log-level', 'info',
            '--log', log_file,
            '--relaxed-security'
        ]

        try:
            self.appium_service.start(
                args = service_args,
                override_server_config = override_server_config
            )

            time.sleep(3)

            if self.appium_service.is_running:
                self.service_address = host
                self.service_port = port
                self.start_time = time.time()
                logger.info(f"Appium服务启动成功: {host}:{port}, 日志文件: {log_file}")
                return True
            else:
                logger.error("Appium服务启动失败")
                return False
        except Exception as e:
            logger.error(f"启动Appium服务时发生错误: {str(e)}")
            return False

    def stop_appium_service(self) -> bool:
        """
        停止Appium服务
        
        Returns:
            bool: 是否停止成功
        """
        if self.appium_service and self.appium_service.is_running:
            try:
                self.appium_service.stop()
                logger.info(f"Appium服务已停止: {self.service_address}:{self.service_port}")
                self.service_address = None
                self.service_port = None
                self.start_time = None
                return True
            except Exception as e:
                logger.error(f"停止Appium服务时发生错误: {str(e)}")
                return False
        else:
            logger.warning("Appium服务未运行")
            return True

    def is_service_running(self) -> bool:
        """
        检查Appium服务是否正在运行
        
        Returns:
            bool: 服务是否运行
        """
        return self.appium_service is not None and self.appium_service.is_running

    def _prepare_device(self, desired_caps: Dict[str, Any]) -> bool:
        """
        准备设备, 确保UIAutomation能够正常连接

        Args:
            desired_caps: 期望的能力配置

        Returns:
            bool: 是否准备成功
        """
        try:
            # 获取设备UDID
            udid = desired_caps.get('udid')
            if not udid:
                logger.warning("未指定设备UDID, 跳过设备准备")
                return True

            logger.info(f"准备设备 {udid}...")

            # 1. 确保设备屏幕是打开的
            logger.info("检查设备屏幕状态...")
            subprocess.run(["adb", "shell", "input", "keyevent", "26"], capture_output = True, text = True)
            time.sleep(1)

            # 2. 解锁屏幕(如果需要)
            logger.info("尝试解锁屏幕...")
            subprocess.run(["adb", "shell", "input", "keyevent", "82"], capture_output = True, text = True)
            time.sleep(1)

            # 3. 检查UIAutomator2服务状态
            logger.info("检查UIAutomator2服务状态...")
            # 停止可能运行的UIAutomator2服务
            subprocess.run(["adb", "shell", "am", "force-stop",
                            "io.appium.uiautomator2.server"], capture_output = True, text = True)
            subprocess.run(["adb", "shell", "am", "force-stop",
                            "io.appium.uiautomator2.server.test"], capture_output = True, text = True)
            time.sleep(2)

            # 4. 清除UIAutomator2缓存
            logger.info("清除UIAutomator2缓存...")
            subprocess.run(["adb", "shell", "pm", "clear",
                            "io.appium.uiautomator2.server"], capture_output = True, text = True)
            subprocess.run(["adb", "shell", "pm", "clear",
                            "io.appium.uiautomator2.server.test"], capture_output = True, text = True)
            time.sleep(2)

            logger.info("设备准备完成")
            return True
        except Exception as e:
            logger.error(f"准备设备时发生错误: {str(e)}")
            return False

    def create_driver(self, desired_caps: Dict[str, Any], host: Optional[str] = None, port: Optional[
        int] = None) -> AppiumDriver:
        """
        创建Appium驱动 - 简化版, 不做任何清理操作

        Args:
            desired_caps: 期望的能力配置
            host: Appium服务主机地址
            port: Appium服务端口

        Returns:
            AppiumDriver: Appium驱动实例
        """
        if host is None:
            host = self.service_address or '127.0.0.1'
        if port is None:
            port = self.service_port or 4723

        server_url = f"http://{host}:{port}"

        logger.info(f"正在创建Appium驱动: {server_url}")
        logger.debug(f"期望能力配置: {desired_caps}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试创建驱动 (尝试 {attempt + 1}/{max_retries})")

                # 在每次尝试前准备设备
                self._prepare_device(desired_caps)
                
                from appium.options.common import AppiumOptions

                options = AppiumOptions()
                for key, value in desired_caps.items():
                    options.set_capability(key, value)

                # 添加一些额外的能力配置来避免UIAutomation连接问题
                if desired_caps.get('platformName') == 'Android':
                    options.set_capability('disableWindowAnimation', True)
                    options.set_capability('skipUnlock', True)

                self.driver = webdriver.Remote(command_executor = server_url, options = options)

                if 'implicit_wait' not in desired_caps:
                    self.driver.implicitly_wait(10)

                logger.info("Appium驱动创建成功")
                return self.driver
            except Exception as e:
                logger.error(f"创建Appium驱动时发生错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = 3 + attempt * 2
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error("达到最大重试次数, 创建驱动失败")
                    raise
        raise RuntimeError("创建 Appium 驱动失败: 所有重试均已耗尽")

    def quit_driver(self) -> bool:
        """
        退出Appium驱动

        Returns:
            bool: 是否退出成功
        """
        if self.driver:
            try:
                # 检查会话是否仍然有效
                if hasattr(self.driver, 'session_id') and self.driver.session_id:
                    self.driver.quit()
                    logger.info("Appium驱动已退出")
                    self.driver = None
                    return True
                else:
                    logger.info("Appium会话已终止, 无需再次关闭")
                    self.driver = None
                    return True
            except Exception as e:
                logger.warning(f"退出Appium驱动时发生错误(会话可能已终止): {str(e)}")
                self.driver = None
                return True
        else:
            logger.warning("驱动未初始化")
            return True

    def get_android_driver(self, app_path: Optional[str] = None,
                           app_package: Optional[str] = None,
                           app_activity: Optional[str] = None,
                           device_name: Optional[str] = None,
                           platform_version: Optional[str] = None,
                           udid: Optional[str] = None,
                           additional_caps: Optional[Dict[str, Any]] = None) -> AppiumDriver:
        """
        获取Android设备的驱动

        Args:
            app_path: APK文件路径
            app_package: 应用包名
            app_activity: 应用活动
            device_name: 设备名称
            platform_version: 平台版本
            udid: 设备UDID
            additional_caps: 额外的能力配置

        Returns:
            AppiumDriver: Appium驱动实例
        """
        desired_caps = {
            'platformName': 'Android',
            'automationName': 'UiAutomator2',
            'deviceName': device_name or 'Android Device',
            'newCommandTimeout': 3600,
            'noReset': False,
            'fullReset': False,
            'unicodeKeyboard': True,
            'resetKeyboard': True,
        }

        if platform_version:
            desired_caps['platformVersion'] = platform_version

        if udid:
            desired_caps['udid'] = udid

        if app_path:
            desired_caps['app'] = app_path
        elif app_package and app_activity:
            desired_caps['appPackage'] = app_package
            desired_caps['appActivity'] = app_activity
        else:
            logger.error("必须提供app_path 或 app_package+app_activity")
            raise ValueError("必须提供app_path 或 app_package+app_activity")

        if additional_caps:
            desired_caps.update(additional_caps)

        return self.create_driver(desired_caps)

    def get_ios_driver(self, app_path: Optional[str] = None,
                       bundle_id: Optional[str] = None,
                       device_name: Optional[str] = None,
                       platform_version: Optional[str] = None,
                       udid: Optional[str] = None,
                       xcode_org_id: Optional[str] = None,
                       xcode_signing_id: Optional[str] = None,
                       additional_caps: Optional[Dict[str, Any]] = None) -> AppiumDriver:
        """
        获取iOS设备的驱动

        Args:
            app_path: IPA文件路径
            bundle_id: 应用Bundle ID
            device_name: 设备名称
            platform_version: 平台版本
            udid: 设备UDID
            xcode_org_id: Xcode组织ID
            xcode_signing_id: Xcode签名ID
            additional_caps: 额外的能力配置

        Returns:
            AppiumDriver: Appium驱动实例
        """
        desired_caps = {
            'platformName': 'iOS',
            'automationName': 'XCUITest',
            'deviceName': device_name or 'iPhone Simulator',
            'newCommandTimeout': 3600,
            'noReset': False,
            'fullReset': False,
        }

        if platform_version:
            desired_caps['platformVersion'] = platform_version

        if udid:
            desired_caps['udid'] = udid

        if app_path:
            desired_caps['app'] = app_path
        elif bundle_id:
            desired_caps['bundleId'] = bundle_id
        else:
            logger.error("必须提供app_path 或 bundle_id")
            raise ValueError("必须提供app_path 或 bundle_id")

        if xcode_org_id:
            desired_caps['xcodeOrgId'] = xcode_org_id
        if xcode_signing_id:
            desired_caps['xcodeSigningId'] = xcode_signing_id

        if additional_caps:
            desired_caps.update(additional_caps)

        return self.create_driver(desired_caps)

    def get_driver(self) -> Optional[AppiumDriver]:
        """
        获取当前驱动

        Returns:
            Optional[AppiumDriver]: 当前驱动实例
        """
        return self.driver

    def is_driver_initialized(self) -> bool:
        """
        检查驱动是否已初始化

        Returns:
            bool: 驱动是否已初始化
        """
        return self.driver is not None

    @staticmethod
    def get_connected_devices() -> Dict[str, list]:
        """
        获取已连接的设备列表

        Returns:
            Dict[str, list]: {"android": [...], "ios": [...]} 格式的设备列表
        """
        devices = {
            "android": [],
            "ios": []
        }

        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output = True,
                text = True,
                check = False
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n')[1:]:
                    if line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) <= 2 and parts[1] == 'device':
                            devices["android"].append(parts[0])

                logger.info(f"找到 {len(devices['android'])} 个Android设备")
        except Exception as e:
            logger.error(f"获取Android设备列表时发生错误: {str(e)}")

        try:
            result = subprocess.run(
                ["idevice_id", "-l"],
                capture_output = True,
                text = True,
                check = False
            )

            if result.returncode == 0:
                ios_devices = result.stdout.strip().split('\n')
                ios_devices = [device for device in ios_devices if device.strip()]
                devices["ios"] = ios_devices
                logger.info(f"找到 {len(devices['ios'])} 个iOS设备")
        except Exception as e:
            logger.warning(f"获取iOS设备列表时发生错误(可能需要安装libimobiledevice): {str(e)}")

        return devices

    def reset_app(self) -> bool:
        """
        重置应用

        Returns:
            bool: 是否重置成功
        """
        if not self.driver:
            logger.error("驱动未初始化,无法重置应用")
            return False

        try:
            logger.info("重置应用")
            self.driver.reset()
            return True
        except Exception as e:
            logger.error(f"重置应用时发生错误: {str(e)}")
            return False

    def launch_app(self, app_package: str = None, app_activity: str = None) -> bool:
        """
        启动应用

        Args:
            app_package: 应用包名
            app_activity: 应用活动名

        Returns:
            bool: 是否启动成功
        """
        try:
            logger.info("启动应用")

            if not app_package or not app_activity:
                logger.error("无法获取应用包名和活动名")
                return False

            # 尝试使用start_activity方法
            if self.driver:
                try:
                    logger.info(f"使用 start_activity 启动应用: {app_package}/{app_activity}")
                    self.driver.start_activity(app_package, app_activity)
                    return True
                except Exception as e:
                    logger.warning(f"start_activity 方法失败: {str(e)}")

            # 尝试使用adb命令
            try:
                logger.info(f"使用 adb 命令启动应用: {app_package}/{app_activity}")
                adb_command = f"adb shell am start -n {app_package}/{app_activity}"
                result = subprocess.run(adb_command, shell = True, capture_output = True, text = True)
                if result.returncode == 0:
                    logger.info("通过 adb 命令成功启动应用")
                    time.sleep(3)
                    return True
                else:
                    logger.warning(f"adb 命令执行失败: {result.stderr}")
            except Exception as e:
                logger.warning(f"adb 命令启动失败: {str(e)}")

            # 尝试重新创建驱动
            try:
                desired_caps = {
                    'platformName': 'Android',
                    'automationName': 'UiAutomator2',
                    'deviceName': 'Android Device',
                    'appPackage': app_package,
                    'appActivity': app_activity,
                    'noReset': False,
                    'fullReset': False,
                    'unicodeKeyboard': True,
                    'resetKeyboard': True,
                    'newCommandTimeout': 3600
                }

                self.driver = self.create_driver(desired_caps)
                logger.info("通过重新创建驱动成功启动应用")
                return True
            except Exception as e:
                logger.error(f"重新创建驱动时发生错误: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"启动应用时发生错误: {str(e)}")
            return False

    def close_app(self) -> bool:
        """
        关闭应用
        
        Returns:
            bool: 是否关闭成功
        """
        if not self.driver:
            logger.error("驱动未初始化,无法关闭应用")
            return False

        try:
            logger.info("关闭应用")
            self.driver.close_app()
            return True
        except Exception as e:
            logger.error(f"关闭应用时发生错误: {str(e)}")
            return False

    @staticmethod
    def load_device_pool(config_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        从配置文件加载设备池配置
        
        Args:
            config_path: 配置文件路径, 默认为 data/config/parallel_devices.yaml
            
        Returns:
            List[Dict[str, Any]]: 设备池配置列表
        """
        if config_path is None:
            config_path = "config/parallel_devices.yaml"

        test_data = FileHandler().read_yaml(config_path)
        return test_data.get("parallel_devices", [])

    @staticmethod
    def get_app_config_for_device(device: Dict[str, Any], config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        根据设备获取应用配置
        
        Args:
            device: 设备配置字典
            config_path: 配置文件路径, 默认为 data/config/app_config.yaml
            
        Returns:
            Dict[str, Any]: 应用配置字典
        """
        if config_path is None:
            config_path = "config/app_config.yaml"

        test_data = FileHandler().read_yaml(config_path)
        app_config = test_data["android_app_test"].copy()

        app_config["device_capabilities"]["deviceName"] = device["device_id"]
        app_config["device_capabilities"]["udid"] = device["device_id"]
        app_config["device_capabilities"]["systemPort"] = device["system_port"]
        app_config["appium_server"]["port"] = device["appium_port"]

        if "mjpeg_server_port" in device:
            app_config["device_capabilities"]["mjpegServerPort"] = device["mjpeg_server_port"]

        if "additional_caps" in device:
            for key, value in device["additional_caps"].items():
                app_config["device_capabilities"][key] = value

        return app_config

    @staticmethod
    def get_device_for_worker(device_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        根据pytest-xdist worker id获取对应的设备
        
        Args:
            device_pool: 设备池配置列表
            
        Returns:
            Dict[str, Any]: 分配给当前worker的设备配置
        """
        import os

        worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

        if worker_id != "master":
            worker_num = int(worker_id.replace("gw", ""))
            device_idx = worker_num % len(device_pool)
            return device_pool[device_idx]
        else:
            return device_pool[0]
