"""
-------------------------------------------------
File:           config_manager.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
配置管理模块,提供配置加载、解析和管理功能
-------------------------------------------------
"""
import os
import sys
from typing import Dict, Any

from utils.logger_util import logger

# 延迟导入yaml模块
yaml = None

try:
    import yaml

    logger.info("✅ yaml模块导入成功")
except ImportError:
    logger.warning("⚠️ yaml模块未安装，将使用空配置")


    # 创建mock yaml模块
    class MockYaml:
        @staticmethod
        def safe_load(file_obj):
            logger.error("❌ yaml模块未安装，无法加载配置文件")
            return {}

        @staticmethod
        def dump(data, file_obj, **kwargs):
            logger.error("❌ yaml模块未安装，无法保存配置文件")


    yaml = MockYaml()


class ConfigDict(dict):
    """支持属性访问的字典类"""

    def __init__(self, config_dict = None):
        if config_dict is None:
            config_dict = {}
        self._config = config_dict  # 存储原始字典,方便调试和访问
        super().__init__(config_dict)

    def __getattr__(self, name):
        if name == '_config':
            return self._config
        if name in self:
            value = self[name]
            # 递归将嵌套字典转换为ConfigDict
            if isinstance(value, dict):
                return ConfigDict(value)
            return value
        raise AttributeError(f"'ConfigDict' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name == '_config':
            object.__setattr__(self, name, value)
        else:
            self[name] = value

    def to_dict(self):
        """将ConfigDict对象转换回普通字典"""
        result = {}
        for key, value in self.items():
            if isinstance(value, ConfigDict):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result


class ConfigManager:
    """
    配置管理器类,用于从YAML文件加载配置并提供配置管理功能
    支持多环境配置管理,配置优先级：环境变量 > YAML文件 > 默认值
    """

    def __init__(self, config_dir: str = None, default_env: str = "test"):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录,如果不指定则使用默认目录
            default_env: 默认环境名称
        """
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
        )
        self.default_env = default_env
        self.env = os.environ.get("OMNITEST_ENV", self.default_env)
        self.config_cache: Dict[str, Dict[str, Any]] = {}
        self._load_all_configs()
        # 创建配置对象用于属性访问
        self._config_obj = ConfigDict(self._config)

    def _load_all_configs(self) -> None:
        """
        加载所有配置：默认配置和环境特定配置
        并应用配置优先级规则
        """
        # 先加载默认配置
        default_config = self._load_file_config("default")

        # 再加载环境特定配置
        env_config = self._load_file_config(self.env)

        # 合并配置：默认配置 -> 环境特定配置
        merged_config = self._merge_configs(default_config, env_config)

        # 应用环境变量覆盖
        self._override_with_env_vars(merged_config)

        # 保存到缓存
        self.config_cache[self.env] = merged_config

        # 设置为当前配置
        self._config = merged_config
        # 更新配置对象
        self._config_obj = ConfigDict(self._config)

    def _load_file_config(self, env: str) -> Dict[str, Any]:
        """
        从YAML文件加载配置

        Args:
            env: 环境名称

        Returns:
            Dict[str, Any]: 加载的配置字典
        """
        # 检查缓存
        if env in self.config_cache:
            return self.config_cache[env].copy()

        # 构建配置文件路径
        config_file = os.path.join(self.config_dir, f"{env}.yaml")

        # 如果文件不存在,返回空字典
        if not os.path.exists(config_file):
            logger.warning(f"配置文件不存在: {config_file}")
            return {}

        # 加载配置文件
        try:
            with open(config_file, "r", encoding = "utf-8") as f:
                config = yaml.safe_load(f) or {}

            logger.info(f"成功加载配置文件: {config_file}")
            return config
        except yaml.YAMLError as e:
            logger.error(f"加载YAML配置文件失败: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件时发生错误: {str(e)}")
            return {}

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个配置字典

        Args:
            base: 基础配置字典
            override: 覆盖配置字典

        Returns:
            Dict[str, Any]: 合并后的配置字典
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = self._merge_configs(result[key], value)
            else:
                # 直接覆盖
                result[key] = value

        return result

    def _override_with_env_vars(self, config: Dict[str, Any]) -> None:
        """
        使用环境变量覆盖配置
        支持嵌套配置,环境变量名格式：SECTION_KEY 或 SECTION__KEY（双下划线表示嵌套）

        Args:
            config: 要被覆盖的配置字典
        """
        for key, value in os.environ.items():
            # 跳过不是配置相关的环境变量
            if not self._is_config_env_var(key):
                continue

            # 处理嵌套配置
            if "__" in key:
                parts = key.split("__")
                section = parts[0].lower()
                nested_key = "__".join(parts[1:]).lower()

                # 如果section不存在,创建它
                if section not in config:
                    config[section] = {}

                # 设置嵌套值
                self._set_nested_value(config[section], nested_key, value)
            else:
                # 顶级配置
                config[key.lower()] = value

    def _is_config_env_var(self, env_var: str) -> bool:
        """
        判断是否为配置相关的环境变量

        Args:
            env_var: 环境变量名

        Returns:
            bool: 是否为配置相关的环境变量
        """
        # 配置相关的环境变量前缀
        prefixes = ["API_", "WEB_", "DB_", "SSH_", "LOG_", "REPORT_", "MYSQL_", "REDIS_"]

        # 检查是否以配置前缀开头
        for prefix in prefixes:
            if env_var.startswith(prefix):
                return True

        # 特殊配置项
        special_vars = ["TEST_ENV", "ENV", "DEBUG"]
        if env_var in special_vars:
            return True

        return False

    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any) -> None:
        """
        设置嵌套配置值

        Args:
            config: 配置字典
            key_path: 键路径,使用双下划线分隔
            value: 要设置的值
        """
        keys = key_path.split("__")
        current = config

        # 遍历键路径,创建嵌套结构
        for i, key in enumerate(keys[:-1]):
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # 设置最终值
        final_key = keys[-1]
        # 尝试类型转换
        current[final_key] = self._convert_value(value)

    def _convert_value(self, value: str) -> Any:
        """
        将字符串值转换为适当的类型

        Args:
            value: 字符串值

        Returns:
            Any: 转换后的值
        """
        # 尝试转换为布尔值
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # 尝试转换为整数
        try:
            return int(value)
        except ValueError:
            pass

        # 尝试转换为浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 保持字符串
        return value

    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值,支持嵌套键路径

        Args:
            key_path: 键路径,使用点号分隔,如 "db.host"
            default: 默认值

        Returns:
            Any: 配置值,如果不存在则返回默认值
        """
        keys = key_path.split(".")
        current = self._config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            logger.debug(f"未找到配置项: {key_path},使用默认值")
            return default

    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        更新当前配置

        Args:
            updates: 要更新的配置
        """
        self._config = self._merge_configs(self._config, updates)
        self.config_cache[self.env] = self._config
        # 更新配置对象
        self._config_obj = ConfigDict(self._config)

    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """
        保存配置到YAML文件

        Args:
            config: 要保存的配置,如果不指定则使用当前配置

        Returns:
            bool: 是否保存成功
        """
        if config is None:
            config = self._config

        config_file = os.path.join(self.config_dir, f"{self.env}.yaml")

        try:
            with open(config_file, "w", encoding = "utf-8") as f:
                yaml.dump(config, f, default_flow_style = False,
                    allow_unicode = True, sort_keys = False)
            logger.info(f"配置已保存到: {config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False

    def get_mysql_config(self, custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取MySQL配置

        Args:
            custom_config: 自定义配置,用于覆盖默认配置

        Returns:
            Dict[str, Any]: MySQL配置字典
        """
        # 从YAML配置获取MySQL默认配置
        config = self.get_config_value("mysql.default", {})

        # 从环境变量获取配置（优先级最高）
        env_config = {
            "host": os.environ.get("MYSQL_HOST"),
            "port": os.environ.get("MYSQL_PORT"),
            "user": os.environ.get("MYSQL_USER"),
            "password": os.environ.get("MYSQL_PASSWORD"),
            "db": os.environ.get("MYSQL_DATABASE"),
            "charset": os.environ.get("MYSQL_CHARSET")
        }

        # 过滤掉None值
        env_config = {k: v for k, v in env_config.items() if v is not None}
        config.update(env_config)

        # 应用自定义配置
        if custom_config:
            config.update(custom_config)

        # 确保端口是整数
        if "port" in config:
            config["port"] = int(config["port"])

        return config

    def get_ssh_config(self, custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取SSH配置

        Args:
            custom_config: 自定义配置,用于覆盖默认配置

        Returns:
            Dict[str, Any]: SSH配置字典
        """
        # 从YAML配置获取SSH默认配置
        config = self.get_config_value("ssh.default", {})

        # 从环境变量获取配置
        # 处理布尔值配置
        env_use_ssh = os.environ.get("SSH_USE_SSH") or os.environ.get("USE_SSH")
        if env_use_ssh is not None:
            config["use_ssh"] = env_use_ssh.lower() == "true"

        # 处理字符串配置
        env_ssh_host = os.environ.get("SSH_HOST")
        if env_ssh_host is not None:
            config["ssh_host"] = env_ssh_host

        # 处理用户名
        env_ssh_username = os.environ.get("SSH_USERNAME") or os.environ.get("SSH_USER")
        if env_ssh_username is not None:
            config["ssh_username"] = env_ssh_username

        # 处理其他配置项
        for key, env_key in [
            ("ssh_password", "SSH_PASSWORD"),
            ("ssh_key_file", "SSH_KEY_FILE"),
            ("local_bind_address", "SSH_LOCAL_BIND"),
        ]:
            env_value = os.environ.get(env_key)
            if env_value is not None:
                config[key] = env_value

        # 处理端口配置
        port_mapping = [
            ("local_bind_port", "SSH_LOCAL_PORT", "LOCAL_BIND_PORT"),
            ("ssh_port", "SSH_PORT"),
            ("local_mysql_port", "SSH_LOCAL_MYSQL_PORT"),
            ("local_redis_port", "SSH_LOCAL_REDIS_PORT"),
        ]

        for config_key, *env_keys in port_mapping:
            for env_key in env_keys:
                env_value = os.environ.get(env_key)
                if env_value is not None:
                    try:
                        config[config_key] = int(env_value)
                        break
                    except (ValueError, TypeError):
                        pass

        # 应用自定义配置
        if custom_config:
            config.update(custom_config)

        return config

    def get_redis_config(self, custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取Redis配置

        Args:
            custom_config: 自定义配置,用于覆盖默认配置

        Returns:
            Dict[str, Any]: Redis配置字典
        """
        # 从YAML配置获取Redis默认配置
        config = self.get_config_value("redis.default", {})

        # 从环境变量获取配置
        env_config = {
            "host": os.environ.get("REDIS_HOST"),
            "port": os.environ.get("REDIS_PORT"),
            "db": os.environ.get("REDIS_DB"),
            "password": os.environ.get("REDIS_PASSWORD")
        }

        # 过滤掉None值并应用
        env_config = {k: v for k, v in env_config.items() if v is not None}
        config.update(env_config)

        # 应用自定义配置
        if custom_config:
            config.update(custom_config)

        # 确保端口和数据库是整数
        if "port" in config:
            config["port"] = int(config["port"])
        if "db" in config:
            config["db"] = int(config["db"])

        return config

    def __getattr__(self, name: str) -> Any:
        """
        提供属性访问方式获取配置
        支持直接访问配置项,如 config.LOG_DIR
        也支持通过get_config_value访问嵌套配置
        """
        try:
            return getattr(self._config_obj, name)
        except AttributeError:
            # 尝试转换为小写并通过点号路径获取（支持驼峰转蛇形）
            snake_case_name = self._camel_to_snake(name)
            try:
                return getattr(self._config_obj, snake_case_name)
            except AttributeError:
                # 对于特殊路径的支持
                special_mappings = {
                    'LOG_DIR': 'log.dir',
                    'DATA_DIR': 'data.dir',
                    'TEST_DATA_DIR': 'data.test_data_dir',
                    'REPORT_DIR': 'report.dir',
                    'ALLURE_REPORT_DIR': 'report.allure_report_dir',
                    'ALLURE_RESULT_DIR': 'report.allure_result_dir',
                    'SCREENSHOT_DIR': 'screenshot.dir',
                    'PAGE_LOAD_TIMEOUT': 'timeout.page_load',
                    'IMPLICITLY_WAIT': 'timeout.implicitly_wait',
                    'DEFAULT_RETRY_COUNT': 'retry.default_count',
                    'RETRY_INTERVAL': 'retry.interval',
                }
                # 路径相关的配置项
                path_configs = {
                    'LOG_DIR', 'DATA_DIR', 'TEST_DATA_DIR',
                    'REPORT_DIR', 'ALLURE_REPORT_DIR',
                    'ALLURE_RESULT_DIR', 'SCREENSHOT_DIR'
                }

                if name in special_mappings:
                    value = self.get_config_value(special_mappings[name])
                    # 如果是路径配置项且值是相对路径, 则转换为绝对路径
                    if name in path_configs and isinstance(value, str) and value.startswith('./'):
                        # 获取项目根目录（配置目录的父目录）
                        project_root = os.path.dirname(self.config_dir)
                        # 转换为绝对路径
                        return os.path.abspath(os.path.join(project_root, value))
                    return value

                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _camel_to_snake(self, name: str) -> str:
        """
        将驼峰命名转换为蛇形命名

        Args:
            name: 驼峰命名的字符串

        Returns:
            str: 蛇形命名的字符串
        """
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append('_')
            result.append(char.lower())
        return ''.join(result)

    def __str__(self) -> str:
        """
        返回配置的字符串表示
        """
        return f"ConfigManager(env='{self.env}', config_keys={list(self._config.keys())})"


# 实际的配置管理器实例（私有变量）
_actual_config_manager = None


# 懒加载配置管理器实例
def get_config_manager():
    """
    懒加载获取配置管理器实例
    
    Returns:
        ConfigManager: 配置管理器实例
    """
    global _actual_config_manager
    if _actual_config_manager is None:
        _actual_config_manager = ConfigManager()
    return _actual_config_manager


# 确保必要的目录存在
def ensure_directories():
    """
    确保必要的目录存在
    """
    # 懒加载获取配置管理器实例
    cm = get_config_manager()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    dirs_to_create = [
        cm.get_config_value("log.dir", "./logs"),
        cm.get_config_value("data.dir", "./data"),
        cm.get_config_value("data.test_data_dir", "./data/test_data"),
        cm.get_config_value("report.dir", "./reports"),
        cm.get_config_value("report.allure_report_dir", "./reports/allure-report"),
        cm.get_config_value("report.allure_result_dir", "./reports/allure-results"),
        cm.get_config_value("screenshot.dir", "./reports/screenshots"),
    ]

    for dir_path in dirs_to_create:
        if dir_path:
            # 确保路径是绝对路径, 基于项目根目录
            if not os.path.isabs(dir_path):
                dir_path = os.path.abspath(os.path.join(project_root, dir_path))
            os.makedirs(dir_path, exist_ok = True)


# 向后兼容：创建config实例（懒加载）
class LazyConfigProxy:
    """懒加载配置代理类"""

    def __getattr__(self, name):
        """获取属性时懒加载配置管理器实例"""
        cm = get_config_manager()
        return getattr(cm, name)

    def __getitem__(self, key):
        """获取项时懒加载配置管理器实例"""
        cm = get_config_manager()
        return cm[key]

    def __call__(self):
        """调用时返回配置管理器实例"""
        return get_config_manager()


# 创建懒加载配置实例
config = LazyConfigProxy()

# 全局配置管理器实例（懒加载）
# 直接使用ConfigManager实例, 不再使用LazyConfigManager包装
config_manager = None


# 确保在第一次访问时初始化
class LazyConfigManagerProxy:
    """懒加载配置管理器代理类"""

    def __getattr__(self, name):
        """获取属性时懒加载配置管理器实例"""
        # 获取配置管理器实例
        cm = get_config_manager()
        # 返回实例的属性
        return getattr(cm, name)

    def __call__(self):
        """调用时返回配置管理器实例"""
        return get_config_manager()


# 替换全局配置管理器实例为代理对象
config_manager = LazyConfigManagerProxy()

# 在模块加载完成后, 延迟调用ensure_directories
try:
    # 仅在主线程中调用, 避免在导入时执行
    if __name__ == '__main__' or not hasattr(sys, 'argv'):
        ensure_directories()
except:
    # 如果在导入时调用失败, 忽略错误, 稍后在实际使用时再调用
    pass