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
from typing import Optional, Dict, Any

from appium import webdriver
from appium.webdriver.appium_service import AppiumService
from appium.webdriver.webdriver import WebDriver as AppiumDriver

from utils.logger_util import logger


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

        # 如果没有指定服务地址,使用默认值
        if host is None:
            host = self.service_address or '127.0.0.1'
        if port is None:
            port = self.service_port or 4723

        # 尝试不同的URL路径
        test_urls = [
            f"http://{host}:{port}/wd/hub/status",
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
        # 延迟导入避免循环依赖
        from config.config_manager import config

        # 如果没有指定日志文件,使用配置文件中的路径
        if log_file is None:
            log_file = os.path.join(config.LOGS_DIR, "appium_server.log")

        # 确保日志目录存在
        os.makedirs(os.path.dirname(log_file), exist_ok = True)

        logger.info(f"正在启动Appium服务: {host}:{port}")

        # 创建Appium服务对象
        self.appium_service = AppiumService()

        # 配置服务参数
        service_args = [
            '--address', host,
            '--port', str(port),
            '--log-level', 'info',
            '--log', log_file,
            '--relaxed-security'  # 增加安全性,允许更多操作
        ]

        # 启动服务
        try:
            self.appium_service.start(
                args = service_args,
                override_server_config = override_server_config
            )

            # 等待服务启动
            time.sleep(3)

            # 检查服务是否启动成功
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
                # 重置服务信息
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

    # @retry(max_retries = 3, delay = 1)
    def create_driver(self, desired_caps: Dict[str, Any],
                      host: Optional[str] = None,
                      port: Optional[int] = None) -> AppiumDriver:
        """
        创建Appium驱动
        
        Args:
            desired_caps: 期望的能力配置
            host: Appium服务主机地址
            port: Appium服务端口
            
        Returns:
            AppiumDriver: Appium驱动实例
        """
        # 延迟导入避免循环依赖

        # 记录实际使用的重试配置
        logger.debug(f"驱动创建使用重试配置")

        # 如果没有指定服务地址,使用已启动的服务或默认值
        if host is None:
            host = self.service_address or '127.0.0.1'
        if port is None:
            port = self.service_port or 4723

        # 构建Appium服务器URL
        # 尝试不同的路径格式
        server_url = f"http://{host}:{port}"

        logger.info(f"正在创建Appium驱动: {server_url}")
        logger.debug(f"期望能力配置: {desired_caps}")

        try:
            # 创建驱动 - 使用新的参数名称
            from appium.options.common import AppiumOptions

            # 创建 AppiumOptions 对象并设置能力
            options = AppiumOptions()
            for key, value in desired_caps.items():
                options.set_capability(key, value)

            # 使用 options 参数创建驱动
            self.driver = webdriver.Remote(command_executor = server_url, options = options)

            # 设置隐式等待
            if 'implicit_wait' not in desired_caps:
                self.driver.implicitly_wait(10)

            logger.info("Appium驱动创建成功")
            return self.driver
        except Exception as e:
            logger.error(f"创建Appium驱动时发生错误: {str(e)}")
            raise

    def quit_driver(self) -> bool:
        """
        退出驱动
        
        Returns:
            bool: 是否退出成功
        """
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Appium驱动已退出")
                self.driver = None
                return True
            except Exception as e:
                logger.error(f"退出Appium驱动时发生错误: {str(e)}")
                return False
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
        # 准备默认的期望能力
        desired_caps = {
            'platformName': 'Android',
            'automationName': 'UiAutomator2',  # 使用UiAutomator2
            'deviceName': device_name or 'Android Device',
            'newCommandTimeout': 3600,  # 设置命令超时时间为1小时
            'noReset': False,  # 每次启动都重置应用
            'fullReset': False,  # 不执行完全重置
            'unicodeKeyboard': True,  # 使用Unicode键盘
            'resetKeyboard': True,  # 重置键盘
        }

        # 添加平台版本
        if platform_version:
            desired_caps['platformVersion'] = platform_version

        # 添加设备UDID
        if udid:
            desired_caps['udid'] = udid

        # 添加应用信息 - 二选一：app路径 或 package+activity
        if app_path:
            desired_caps['app'] = app_path
        elif app_package and app_activity:
            desired_caps['appPackage'] = app_package
            desired_caps['appActivity'] = app_activity
        else:
            logger.error("必须提供app_path 或 app_package+app_activity")
            raise ValueError("必须提供app_path 或 app_package+app_activity")

        # 添加额外的能力配置
        if additional_caps:
            desired_caps.update(additional_caps)

        # 创建驱动
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
        # 准备默认的期望能力
        desired_caps = {
            'platformName': 'iOS',
            'automationName': 'XCUITest',  # 使用XCUITest
            'deviceName': device_name or 'iPhone Simulator',
            'newCommandTimeout': 3600,  # 设置命令超时时间为1小时
            'noReset': False,  # 每次启动都重置应用
            'fullReset': False,  # 不执行完全重置
        }

        # 添加平台版本
        if platform_version:
            desired_caps['platformVersion'] = platform_version

        # 添加设备UDID
        if udid:
            desired_caps['udid'] = udid

        # 添加应用信息 - 二选一：app路径 或 bundle_id
        if app_path:
            desired_caps['app'] = app_path
        elif bundle_id:
            desired_caps['bundleId'] = bundle_id
        else:
            logger.error("必须提供app_path 或 bundle_id")
            raise ValueError("必须提供app_path 或 bundle_id")

        # 添加Xcode配置
        if xcode_org_id:
            desired_caps['xcodeOrgId'] = xcode_org_id
        if xcode_signing_id:
            desired_caps['xcodeSigningId'] = xcode_signing_id

        # 添加额外的能力配置
        if additional_caps:
            desired_caps.update(additional_caps)

        # 创建驱动
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

        # 获取Android设备
        try:
            # 使用adb命令获取设备
            result = subprocess.run(
                ["adb", "devices"],
                capture_output = True,
                text = True,
                check = False
            )

            # 解析结果
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n')[1:]:  # 跳过第一行
                    if line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) >= 2 and parts[1] == 'device':
                            devices["android"].append(parts[0])

                logger.info(f"找到 {len(devices['android'])} 个Android设备")
        except Exception as e:
            logger.error(f"获取Android设备列表时发生错误: {str(e)}")

        # 获取iOS设备
        try:
            # 使用idevice_id命令获取iOS设备（需要安装libimobiledevice）
            result = subprocess.run(
                ["idevice_id", "-l"],
                capture_output = True,
                text = True,
                check = False
            )

            # 解析结果
            if result.returncode == 0:
                ios_devices = result.stdout.strip().split('\n')
                ios_devices = [device for device in ios_devices if device.strip()]
                devices["ios"] = ios_devices
                logger.info(f"找到 {len(devices['ios'])} 个iOS设备")
        except Exception as e:
            logger.warning(f"获取iOS设备列表时发生错误（可能需要安装libimobiledevice）: {str(e)}")

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

    def launch_app(self) -> bool:
        """
        启动应用
        
        Returns:
            bool: 是否启动成功
        """
        if not self.driver:
            logger.error("驱动未初始化,无法启动应用")
            return False

        try:
            logger.info("启动应用")
            self.driver.launch_app()
            return True
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