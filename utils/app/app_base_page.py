"""
-------------------------------------------------
File:           app_base_page.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
App自动化基础页面类,实现POM模式的页面基类功能,提供元素定位、操作和等待等通用方法
-------------------------------------------------
"""
import time
from typing import Optional, List, Any

from appium.webdriver.webdriver import WebDriver as AppiumDriver
from selenium.webdriver.common.by import By

# 定义MobileBy作为By的别名,保持兼容性
MobileBy = By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotVisibleException,
    ElementNotInteractableException
)
from utils.logger_util import logger
from utils.decorator_util import retry
from utils.common_util import CommonUtils


# 导入移至函数内部避免循环依赖


class AppBasePage:
    """
    APP自动化页面基类
    所有APP页面类都应该继承此类
    """

    def __init__(self, driver: AppiumDriver):
        """
        初始化页面类
        
        Args:
            driver: Appium驱动实例
        """
        self.driver = driver
        self.utils = CommonUtils()
        self.screenshot_utils = screenshot_utils

    # 元素定位相关方法
    def find_element(self, by: str, value: str, timeout: Optional[int] = None) -> Any:
        """
        查找单个元素
        
        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）,默认使用配置文件中的值
            
        Returns:
            Any: 找到的元素
        """
        timeout = timeout or config.DEFAULT_TIMEOUT
        logger.info(f"查找元素: {by}={value}, 超时时间: {timeout}秒")

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"成功找到元素: {by}={value}")
            return element
        except TimeoutException:
            logger.error(f"超时: 未找到元素 {by}={value}")
            # 失败时截图
            self.screenshot_utils.capture_screenshot(
                driver = self.driver,
                filename = f"element_not_found_{self.utils.get_timestamp()}",
                description = f"Failed to find element: {by}={value}"
            )
            raise NoSuchElementException(f"未找到元素: {by}={value}")
        except Exception as e:
            logger.error(f"查找元素时发生错误: {str(e)}")
            raise

    def find_elements(self, by: str, value: str, timeout: Optional[int] = None) -> List[Any]:
        """
        查找多个元素
        
        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）,默认使用配置文件中的值
            
        Returns:
            List[Any]: 找到的元素列表
        """
        timeout = timeout or config.DEFAULT_TIMEOUT
        logger.info(f"查找多个元素: {by}={value}, 超时时间: {timeout}秒")

        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            logger.debug(f"成功找到 {len(elements)} 个元素: {by}={value}")
            return elements
        except TimeoutException:
            logger.warning(f"超时: 未找到元素 {by}={value},返回空列表")
            return []
        except Exception as e:
            logger.error(f"查找多个元素时发生错误: {str(e)}")
            return []

    def find_element_by_id(self, id_value: str, timeout: Optional[int] = None) -> Any:
        """
        通过ID查找元素
        
        Args:
            id_value: 元素ID
            timeout: 超时时间（秒）
            
        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.ID, id_value, timeout)

    def find_element_by_xpath(self, xpath: str, timeout: Optional[int] = None) -> Any:
        """
        通过XPath查找元素
        
        Args:
            xpath: XPath表达式
            timeout: 超时时间（秒）
            
        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.XPATH, xpath, timeout)

    def find_element_by_android_uiautomator(self, uiautomator: str, timeout: Optional[int] = None) -> Any:
        """
        通过Android UiAutomator查找元素
        
        Args:
            uiautomator: UiAutomator表达式
            timeout: 超时时间（秒）
            
        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.ANDROID_UIAUTOMATOR, uiautomator, timeout)

    def find_element_by_ios_predicate(self, predicate: str, timeout: Optional[int] = None) -> Any:
        """
        通过iOS Predicate查找元素
        
        Args:
            predicate: Predicate表达式
            timeout: 超时时间（秒）
            
        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.IOS_PREDICATE, predicate, timeout)

    def find_element_by_accessibility_id(self, accessibility_id: str, timeout: Optional[int] = None) -> Any:
        """
        通过Accessibility ID查找元素
        
        Args:
            accessibility_id: Accessibility ID
            timeout: 超时时间（秒）
            
        Returns:
            Any: 找到的元素
        """
        return self.find_element(MobileBy.ACCESSIBILITY_ID, accessibility_id, timeout)

    # 元素操作相关方法
    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def click(self, element: Any, description: Optional[str] = None) -> None:
        """
        点击元素
        
        Args:
            element: 要点击的元素
            description: 元素描述（用于日志）
        """
        desc = description or "元素"
        logger.info(f"点击 {desc}")

        try:
            # 确保元素可见
            WebDriverWait(self.driver, config.DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable(element)
            )

            # 点击元素
            element.click()
            logger.debug(f"成功点击 {desc}")
        except (ElementNotVisibleException, ElementNotInteractableException):
            logger.error(f"无法点击 {desc}: 元素不可见或不可交互")
            # 尝试滚动到元素并点击
            self.scroll_to_element(element)
            element.click()
            logger.debug(f"滚动后成功点击 {desc}")
        except Exception as e:
            logger.error(f"点击 {desc} 时发生错误: {str(e)}")
            # 失败时截图
            self.screenshot_utils.capture_screenshot(
                driver = self.driver,
                filename = f"click_failed_{self.utils.get_timestamp()}",
                description = f"Failed to click {desc}"
            )
            raise

    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def input_text(self, element: Any, text: str, description: Optional[str] = None,
                   clear_first: bool = True) -> None:
        """
        在输入框中输入文本
        
        Args:
            element: 输入框元素
            text: 要输入的文本
            description: 元素描述（用于日志）
            clear_first: 是否先清空输入框
        """
        desc = description or "输入框"
        logger.info(f"在 {desc} 中输入文本: {'***' if self._is_sensitive_info(text) else text}")

        try:
            # 确保元素可见且可交互
            WebDriverWait(self.driver, config.DEFAULT_TIMEOUT).until(
                EC.visibility_of(element)
            )

            # 清空输入框
            if clear_first:
                element.clear()
                # 有时候clear()不能完全清空,再点击一次
                element.click()
                # 对于Android,可以使用keyevent
                if self.driver.capabilities['platformName'].lower() == 'android':
                    self.driver.keyevent(123)  # END键
                    self.driver.keyevent(67)  # DEL键,多按几次确保清空

            # 输入文本
            element.send_keys(text)
            logger.debug(f"成功在 {desc} 中输入文本")
        except Exception as e:
            logger.error(f"在 {desc} 中输入文本时发生错误: {str(e)}")
            # 失败时截图
            self.screenshot_utils.capture_screenshot(
                driver = self.driver,
                filename = f"input_failed_{self.utils.get_timestamp()}",
                description = f"Failed to input text in {desc}"
            )
            raise

    def get_text(self, element: Any, description: Optional[str] = None) -> str:
        """
        获取元素文本
        
        Args:
            element: 元素
            description: 元素描述（用于日志）
            
        Returns:
            str: 元素文本
        """
        desc = description or "元素"
        logger.info(f"获取 {desc} 的文本")

        try:
            text = element.text
            logger.debug(f"成功获取 {desc} 的文本: {text}")
            return text
        except Exception as e:
            logger.error(f"获取 {desc} 的文本时发生错误: {str(e)}")
            raise

    def is_element_displayed(self, by: str, value: str, timeout: Optional[int] = None) -> bool:
        """
        检查元素是否可见
        
        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）
            
        Returns:
            bool: 元素是否可见
        """
        timeout = timeout or config.DEFAULT_TIMEOUT
        logger.info(f"检查元素是否可见: {by}={value}")

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            logger.debug(f"元素 {by}={value} 可见")
            return True
        except (TimeoutException, NoSuchElementException):
            logger.debug(f"元素 {by}={value} 不可见或不存在")
            return False

    def is_element_enabled(self, element: Any, description: Optional[str] = None) -> bool:
        """
        检查元素是否可用
        
        Args:
            element: 元素
            description: 元素描述（用于日志）
            
        Returns:
            bool: 元素是否可用
        """
        desc = description or "元素"
        logger.info(f"检查 {desc} 是否可用")

        try:
            enabled = element.is_enabled()
            logger.debug(f"{desc} {'可用' if enabled else '不可用'}")
            return enabled
        except Exception as e:
            logger.error(f"检查 {desc} 是否可用时发生错误: {str(e)}")
            raise

    # 页面操作相关方法
    def scroll_to_element(self, element: Any, max_swipes: int = 5) -> None:
        """
        滚动到元素可见
        
        Args:
            element: 目标元素
            max_swipes: 最大滑动次数
        """
        logger.info("滚动到元素可见")

        for _ in range(max_swipes):
            try:
                if element.is_displayed():
                    logger.debug("元素已可见")
                    return

                # 根据平台执行滚动
                if self.driver.capabilities['platformName'].lower() == 'android':
                    self.driver.swipe(500, 1500, 500, 1000, 800)  # 向上滑动
                else:  # iOS
                    self.driver.execute_script("mobile: scroll", {
                        'direction': 'down'
                    })

                time.sleep(0.5)
            except Exception as e:
                logger.error(f"滚动时发生错误: {str(e)}")

        logger.warning(f"达到最大滚动次数 {max_swipes},元素可能仍然不可见")

    def scroll_down(self, percentage: int = 80) -> None:
        """
        向下滚动页面
        
        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("down", percentage)

    def scroll_up(self, percentage: int = 80) -> None:
        """
        向上滚动页面
        
        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("up", percentage)

    def scroll_left(self, percentage: int = 80) -> None:
        """
        向左滚动页面
        
        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("left", percentage)

    def scroll_right(self, percentage: int = 80) -> None:
        """
        向右滚动页面
        
        Args:
            percentage: 滚动距离百分比（0-100）
        """
        self._swipe("right", percentage)

    def _swipe(self, direction: str, percentage: int = 80) -> None:
        """
        滑动页面
        
        Args:
            direction: 滑动方向（up, down, left, right）
            percentage: 滚动距离百分比（0-100）
        """
        logger.info(f"{direction} 滑动页面 {percentage}%")

        # 获取屏幕尺寸
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = size['height'] // 2

        # 计算滑动距离
        swipe_percentage = percentage / 100

        # 根据方向设置终点坐标
        if direction == "up":
            end_y = int(start_y * (1 - swipe_percentage))
            self.driver.swipe(start_x, start_y, start_x, end_y, 800)
        elif direction == "down":
            end_y = int(start_y * (1 + swipe_percentage))
            self.driver.swipe(start_x, start_y, start_x, end_y, 800)
        elif direction == "left":
            end_x = int(start_x * (1 - swipe_percentage))
            self.driver.swipe(start_x, start_y, end_x, start_y, 800)
        elif direction == "right":
            end_x = int(start_x * (1 + swipe_percentage))
            self.driver.swipe(start_x, start_y, end_x, start_y, 800)
        else:
            raise ValueError(f"无效的滑动方向: {direction}")

        time.sleep(0.5)  # 等待滑动完成

    def get_current_activity(self) -> str:
        """
        获取当前活动（Android）或页面（iOS）
        
        Returns:
            str: 当前活动名称
        """
        platform = self.driver.capabilities['platformName'].lower()

        if platform == 'android':
            activity = self.driver.current_activity
            logger.info(f"当前Android活动: {activity}")
            return activity
        else:  # iOS
            context = self.driver.current_context
            logger.info(f"当前iOS上下文: {context}")
            return context

    def get_package(self) -> str:
        """
        获取当前包名（Android）
        
        Returns:
            str: 包名
        """
        if self.driver.capabilities['platformName'].lower() == 'android':
            package = self.driver.current_package
            logger.info(f"当前包名: {package}")
            return package
        else:
            logger.warning("get_package() 方法仅适用于Android平台")
            return ""

    def press_back(self) -> None:
        """
        按返回键
        """
        logger.info("按返回键")
        self.driver.back()

    def press_home(self) -> None:
        """
        按Home键
        """
        logger.info("按Home键")
        self.driver.press_keycode(3) if self.driver.capabilities['platformName'].lower() == 'android' else \
            self.driver.execute_script("mobile: pressButton", {"name": "home"})

    def press_menu(self) -> None:
        """
        按菜单键
        """
        logger.info("按菜单键")
        self.driver.press_keycode(82) if self.driver.capabilities['platformName'].lower() == 'android' else \
            self.driver.execute_script("mobile: pressButton", {"name": "menu"})

    def hide_keyboard(self, key_name: Optional[str] = None) -> None:
        """
        隐藏键盘
        
        Args:
            key_name: 用于关闭键盘的键名（如"Done"）
        """
        logger.info("隐藏键盘")

        try:
            if key_name:
                self.driver.hide_keyboard(key_name = key_name)
            else:
                self.driver.hide_keyboard()
        except Exception as e:
            logger.warning(f"隐藏键盘时发生错误（可能键盘已隐藏）: {str(e)}")

    def tap_screen(self, x: int, y: int, duration: Optional[int] = None) -> None:
        """
        点击屏幕指定坐标
        
        Args:
            x: X坐标
            y: Y坐标
            duration: 点击持续时间（毫秒）
        """
        logger.info(f"点击屏幕坐标: ({x}, {y})")

        if duration:
            self.driver.tap([(x, y)], duration)
        else:
            self.driver.tap([(x, y)])

    # 等待相关方法
    def wait_for_activity(self, activity: str, timeout: int = 10) -> bool:
        """
        等待活动启动
        
        Args:
            activity: 要等待的活动名称
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否在超时时间内启动
        """
        logger.info(f"等待活动启动: {activity}, 超时时间: {timeout}秒")

        if self.driver.capabilities['platformName'].lower() == 'android':
            result = self.driver.wait_activity(activity, timeout)
            logger.debug(f"活动启动等待结果: {'成功' if result else '失败'}")
            return result
        else:
            logger.warning("wait_for_activity() 方法仅适用于Android平台")
            return False

    @retry(max_retries = 3, delay = 1)  # 使用默认值避免循环依赖
    def wait_for_element(self, by: str, value: str, timeout: Optional[int] = None) -> bool:
        """
        等待元素出现
        
        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否在超时时间内出现
        """
        timeout = timeout or config.DEFAULT_TIMEOUT
        logger.info(f"等待元素出现: {by}={value}, 超时时间: {timeout}秒")

        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"元素 {by}={value} 已出现")
            return True
        except TimeoutException:
            logger.debug(f"超时: 元素 {by}={value} 未出现")
            return False

    def wait_for_element_disappear(self, by: str, value: str, timeout: Optional[int] = None) -> bool:
        """
        等待元素消失
        
        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否在超时时间内消失
        """
        timeout = timeout or config.DEFAULT_TIMEOUT
        logger.info(f"等待元素消失: {by}={value}, 超时时间: {timeout}秒")

        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((by, value))
            )
            logger.debug(f"元素 {by}={value} 已消失")
            return True
        except TimeoutException:
            logger.debug(f"超时: 元素 {by}={value} 未消失")
            return False

    # 应用操作相关方法
    def close_app(self) -> None:
        """
        关闭应用
        """
        logger.info("关闭应用")
        self.driver.close_app()

    def launch_app(self) -> None:
        """
        启动应用
        """
        logger.info("启动应用")
        self.driver.launch_app()

    def reset_app(self) -> None:
        """
        重置应用
        """
        logger.info("重置应用")
        self.driver.reset()

    def terminate_app(self, app_id: str) -> bool:
        """
        终止应用
        
        Args:
            app_id: 应用ID（包名或Bundle ID）
            
        Returns:
            bool: 是否成功终止
        """
        logger.info(f"终止应用: {app_id}")
        result = self.driver.terminate_app(app_id)
        logger.debug(f"应用终止结果: {'成功' if result else '失败'}")
        return result

    def activate_app(self, app_id: str) -> bool:
        """
        激活应用
        
        Args:
            app_id: 应用ID（包名或Bundle ID）
            
        Returns:
            bool: 是否成功激活
        """
        logger.info(f"激活应用: {app_id}")
        result = self.driver.activate_app(app_id)
        logger.debug(f"应用激活结果: {'成功' if result else '失败'}")
        return result

    def is_app_installed(self, app_id: str) -> bool:
        """
        检查应用是否已安装
        
        Args:
            app_id: 应用ID（包名或Bundle ID）
            
        Returns:
            bool: 是否已安装
        """
        logger.info(f"检查应用是否已安装: {app_id}")
        result = self.driver.is_app_installed(app_id)
        logger.debug(f"应用安装状态: {'已安装' if result else '未安装'}")
        return result

    def install_app(self, app_path: str) -> None:
        """
        安装应用
        
        Args:
            app_path: 应用安装包路径
        """
        logger.info(f"安装应用: {app_path}")
        self.driver.install_app(app_path)

    def remove_app(self, app_id: str) -> None:
        """
        卸载应用
        
        Args:
            app_id: 应用ID（包名或Bundle ID）
        """
        logger.info(f"卸载应用: {app_id}")
        self.driver.remove_app(app_id)

    # 辅助方法
    def _is_sensitive_info(self, text: str) -> bool:
        """
        检查文本是否包含敏感信息（如密码）
        
        Args:
            text: 要检查的文本
            
        Returns:
            bool: 是否包含敏感信息
        """
        sensitive_patterns = ['password', 'pwd', 'token', 'secret', 'key']
        # 检查参数名或描述中是否包含敏感词
        caller_frame = self.utils.get_caller_info()
        caller_args = caller_frame.f_locals if caller_frame else {}

        for arg_name, arg_value in caller_args.items():
            if any(pattern in arg_name.lower() for pattern in sensitive_patterns):
                return True

        return False

    def capture_screenshot(self, filename: Optional[str] = None, description: Optional[str] = None) -> str:
        """
        截取当前屏幕
        
        Args:
            filename: 截图文件名（不含路径和扩展名）
            description: 截图描述
            
        Returns:
            str: 截图文件路径
        """
        return self.screenshot_utils.capture_screenshot(
            driver = self.driver,
            filename = filename or f"app_screenshot_{self.utils.get_timestamp()}",
            description = description
        )

    def take_screenshot(self, save_path: Optional[str] = None) -> str:
        """
        快速截图方法（兼容性方法）
        
        Args:
            save_path: 保存路径
            
        Returns:
            str: 截图文件路径
        """
        return self.capture_screenshot(save_path)
