"""
-------------------------------------------------
File:           common_util.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:    
通用工具模块,提供项目中常用的工具函数和辅助方法,如时间处理、随机数据生成、文件操作等
-------------------------------------------------
"""
import hashlib
import json
import os
import random
import re
import string
import time
from datetime import datetime, timedelta

from utils.logger_util import logger


class CommonUtils:
    """通用工具类"""

    @staticmethod
    def sleep(seconds):
        """
        睡眠指定秒数
        
        Args:
            seconds: 睡眠秒数
        """
        time.sleep(seconds)

    @staticmethod
    def current_time(format_str = "%Y-%m-%d %H:%M:%S"):
        """
        获取当前时间
        
        Args:
            format_str: 时间格式
            
        Returns:
            str: 当前时间字符串
        """
        return datetime.now().strftime(format_str)

    @staticmethod
    def current_day():
        """
        获取当前日期（day）
        
        Returns:
            int: 当前日期的天数（1-31）
        """
        return datetime.now().day

    @staticmethod
    def current_month():
        """
        获取当前月份（month）
        
        Returns:
            int: 当前月份（1-12）
        """
        return datetime.now().month

    @staticmethod
    def current_year():
        """
        获取当前年份（year）
        
        Returns:
            int: 当前年份
        """
        return datetime.now().year

    @staticmethod
    def current_date(format_str = "%Y-%m-%d"):
        """
        获取当前日期（不含时间）
        
        Args:
            format_str: 日期格式, 默认为"YYYY-MM-DD"
            
        Returns:
            str: 当前日期字符串
        """
        return datetime.now().strftime(format_str)

    @staticmethod
    def format_time(dt, format_str = "%Y-%m-%d %H:%M:%S"):
        """
        格式化时间
        
        Args:
            dt: datetime对象
            format_str: 时间格式
            
        Returns:
            str: 格式化后的时间字符串
        """
        return dt.strftime(format_str)

    @staticmethod
    def parse_time(time_str, format_str = "%Y-%m-%d %H:%M:%S"):
        """
        解析时间字符串
        
        Args:
            time_str: 时间字符串
            format_str: 时间格式
            
        Returns:
            datetime: datetime对象
        """
        return datetime.strptime(time_str, format_str)

    @staticmethod
    def get_now_time_delta(days = 0, hours = 0, minutes = 0, seconds = 0):
        """
        获取时间增量
        计算当前时间加上指定的时间增量

        Args:
            days: 天数
            hours: 小时数
            minutes: 分钟数
            seconds: 秒数
            
        Returns:
            datetime: 计算后的datetime对象
        """
        return datetime.now() + timedelta(
            days = days, hours = hours, minutes = minutes, seconds = seconds
        )

    @staticmethod
    def get_time_delta(datetime_obj, days = 0, hours = 0, minutes = 0, seconds = 0):
        """
        获取时间增量
        计算指定时间增量

        Args:
            datetime_obj: 基准时间
            days: 天数
            hours: 小时数
            minutes: 分钟数
            seconds: 秒数

        Returns:
            datetime: 计算后的datetime对象
        """
        return datetime_obj + timedelta(
            days = days, hours = hours, minutes = minutes, seconds = seconds
        )

    @staticmethod
    def generate_random_string(length = 10, use_digits = True, use_uppercase = True, use_lowercase = True):
        """
        生成随机字符串
        
        Args:
            length: 字符串长度
            use_digits: 是否包含数字
            use_uppercase: 是否包含大写字母
            use_lowercase: 是否包含小写字母
            
        Returns:
            str: 随机字符串
        """
        chars = ''
        if use_digits:
            chars += string.digits
        if use_uppercase:
            chars += string.ascii_uppercase
        if use_lowercase:
            chars += string.ascii_lowercase

        if not chars:
            raise ValueError("至少需要包含一种字符类型")

        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def generate_random_number(min_val = 0, max_val = 1000):
        """
        生成随机数字
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            int: 随机数字
        """
        return random.randint(min_val, max_val)

    @staticmethod
    def generate_random_email(domain = "example.com"):
        """
        生成随机邮箱
        
        Args:
            domain: 邮箱域名
            
        Returns:
            str: 随机邮箱
        """
        username = CommonUtils.generate_random_string(8)
        return f"{username}@{domain}"

    @staticmethod
    def md5(text):
        """
        计算MD5哈希值
        
        Args:
            text: 要计算的文本
            
        Returns:
            str: MD5哈希值
        """
        if isinstance(text, str):
            text = text.encode('utf-8')
        return hashlib.md5(text).hexdigest()

    @staticmethod
    def sha256(text):
        """
        计算SHA256哈希值
        
        Args:
            text: 要计算的文本
            
        Returns:
            str: SHA256哈希值
        """
        if isinstance(text, str):
            text = text.encode('utf-8')
        return hashlib.sha256(text).hexdigest()

    @staticmethod
    def is_json(data):
        """
        检查字符串是否为有效的JSON
        
        Args:
            data: 要检查的数据
            
        Returns:
            bool: 是否为有效JSON
        """
        if not isinstance(data, str):
            return False
        try:
            json.loads(data)
            return True
        except ValueError:
            return False

    @staticmethod
    def safe_json_loads(data, default = None):
        """
        安全地解析JSON字符串
        
        Args:
            data: JSON字符串
            default: 解析失败时返回的默认值
            
        Returns:
            dict/list: 解析后的数据或默认值
        """
        try:
            return json.loads(data)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_json_dumps(data, default = None):
        """
        安全地序列化JSON
        
        Args:
            data: 要序列化的数据
            default: 序列化失败时返回的默认值
            
        Returns:
            str: 序列化后的JSON字符串或默认值
        """
        try:
            return json.dumps(data, ensure_ascii = False, default = str)
        except Exception:
            return default

    @staticmethod
    def extract_by_regex(pattern, text, group = 1):
        """
        使用正则表达式提取内容
        
        Args:
            pattern: 正则表达式模式
            text: 要匹配的文本
            group: 要提取的组号
            
        Returns:
            str: 提取的内容或None
        """
        match = re.search(pattern, text)
        if match:
            return match.group(group)
        return None

    @staticmethod
    def is_valid_email(email):
        """
        验证邮箱格式是否正确
        
        Args:
            email: 邮箱地址
            
        Returns:
            bool: 是否为有效邮箱
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_phone(phone):
        """
        验证手机号格式是否正确（中国大陆）
        
        Args:
            phone: 手机号码
            
        Returns:
            bool: 是否为有效手机号
        """
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, str(phone)))

    @staticmethod
    def file_exists(file_path):
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否存在
        """
        return os.path.isfile(file_path)

    @staticmethod
    def folder_exists(folder_path):
        """
        检查文件夹是否存在
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            bool: 文件夹是否存在
        """
        return os.path.isdir(folder_path)

    @staticmethod
    def ensure_folder_exists(folder_path):
        """
        确保文件夹存在,如果不存在则创建
        
        Args:
            folder_path: 文件夹路径
        """
        # 获取项目根目录（common_util.py的父目录的父目录）
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 如果是相对路径, 则基于项目根目录解析
        if not os.path.isabs(folder_path):
            folder_path = os.path.abspath(os.path.join(project_root, folder_path))

        os.makedirs(folder_path, exist_ok = True)

    @staticmethod
    def get_file_size(file_path):
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            int: 文件大小（字节）
        """
        if not os.path.isfile(file_path):
            return 0
        return os.path.getsize(file_path)

    @staticmethod
    def get_filename(file_path):
        """
        获取文件名（不含扩展名）
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件名
        """
        return os.path.splitext(os.path.basename(file_path))[0]

    @staticmethod
    def get_file_extension(file_path):
        """
        获取文件扩展名
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件扩展名（不含点）
        """
        return os.path.splitext(file_path)[1].lstrip('.')

    @staticmethod
    def retry(func, max_retries = 3, delay = 2, exceptions = (Exception,)):
        """
        重试装饰器
        
        Args:
            func: 要重试的函数
            max_retries: 最大重试次数
            delay: 重试间隔（秒）
            exceptions: 捕获的异常类型
            
        Returns:
            function: 装饰后的函数
        """

        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.info(f"尝试 {attempt + 1}/{max_retries} 失败: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            logger.error(f"达到最大重试次数 {max_retries},函数 {func.__name__} 执行失败")
            raise last_exception

        return wrapper


# 创建工具类实例
util = CommonUtils()
