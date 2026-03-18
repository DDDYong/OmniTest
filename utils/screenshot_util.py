"""
-------------------------------------------------
File:           screenshot_util.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
截图工具模块,提供Web和APP自动化中的截图功能,包括页面截图、元素截图和页面源码保存等功能
-------------------------------------------------
"""
import os
import time
from datetime import datetime

from config.config_manager import config
from utils.common_util import CommonUtils
from utils.logger_util import logger


class ScreenshotUtils:
    """截图工具类"""

    def __init__(self):
        """初始化截图工具"""
        # 直接使用已导入的config
        # 确保截图目录存在
        CommonUtils.ensure_folder_exists(config.SCREENSHOT_DIR)

    def capture_screenshot(self, driver, name = None):
        """
        捕获截图
        
        Args:
            driver: WebDriver或AppiumDriver实例
            name: 截图名称,如果为None则自动生成
            
        Returns:
            str: 截图文件路径
        """
        # 生成截图名称
        if name is None:
            timestamp = int(time.time())
            name = f"screenshot_{timestamp}"

        # 确保名称不包含扩展名
        if not name.endswith('.png'):
            name = f"{name}.png"

        # 生成截图路径
        screenshot_path = os.path.join(config.SCREENSHOT_DIR, name)

        try:
            # 执行截图
            driver.save_screenshot(screenshot_path)
            logger.info(f"截图成功: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None

    def capture_element_screenshot(self, element, name = None):
        """
        捕获元素截图
        
        Args:
            element: WebElement实例
            name: 截图名称,如果为None则自动生成
            
        Returns:
            str: 截图文件路径
        """
        # 生成截图名称
        if name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            name = f"element_screenshot_{timestamp}"

        # 确保名称不包含扩展名
        if not name.endswith('.png'):
            name = f"{name}.png"

        # 直接使用已导入的config
        # 生成截图路径
        screenshot_path = os.path.join(config.SCREENSHOT_DIR, name)

        try:
            # 执行截图
            element.screenshot(screenshot_path)
            logger.info(f"元素截图成功: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"元素截图失败: {str(e)}")
            return None

    def capture_page_source(self, driver, name = None):
        """
        捕获页面源码
        
        Args:
            driver: WebDriver实例
            name: 文件名,如果为None则自动生成
            
        Returns:
            str: 页面源码文件路径
        """
        # 生成文件名
        if name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            name = f"page_source_{timestamp}"

        # 确保名称不包含扩展名
        if not name.endswith('.html'):
            name = f"{name}.html"

        # 直接使用已导入的config
        # 生成文件路径
        source_path = os.path.join(config.SCREENSHOT_DIR, name)

        try:
            # 获取页面源码
            page_source = driver.page_source
            # 写入文件
            with open(source_path, 'w', encoding = 'utf-8') as f:
                f.write(page_source)
            logger.info(f"页面源码保存成功: {source_path}")
            return source_path
        except Exception as e:
            logger.error(f"页面源码保存失败: {str(e)}")
            return None


# 注意: 不再在模块级别创建实例, 避免导入时的循环依赖问题
# 使用时请手动初始化: screenshot_utils = ScreenshotUtils()
