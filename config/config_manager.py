"""
-------------------------------------------------
File:           config_manager.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
配置管理模块,提供 YAML 配置加载、解析与管理能力.

核心特性:
- 线程安全懒加载单例
- 可追溯错误日志
- 支持 reload(path=None)
- 日志字段标准化
-------------------------------------------------
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
import traceback
from typing import Any, Dict, Optional, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

logger = logging.getLogger("OmniTest.Config")

__all__ = [
    "ConfigDict",
    "ConfigManager",
    "get_config_manager",
    "ensure_directories",
    "config",
    "config_manager",
]


class _ConfigLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra") or {}
        merged = {"module_name": __name__, **self.extra, **extra}
        kwargs["extra"] = merged
        return msg, kwargs


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
    配置管理器:从 YAML 加载配置并提供读取、覆盖与热重载能力.

    配置优先级(由高到低):
    - 环境变量(按既定前缀/规则)
    - 环境 YAML(如 test.yaml)
    - 默认 YAML(default.yaml)

    日志策略(由 LOG_LEVEL 或日志系统级别共同决定):
    - DEBUG:打印路径、耗时、异常堆栈与重试细节
    - INFO:仅打印"真正发生加载动作"的一次性摘要;reload 时打印带 [Reload] 的摘要
    - WARNING 及以上:仅在加载失败或校验不通过时输出
    """

    _DEFAULT_YAML_NAME = "default.yaml"
    _ENV_VAR_NAME = "OMNITEST_ENV"
    _MAX_DEBUG_KEYS = 500
    _LARGE_FILE_BYTES = 1024 * 1024

    def __init__(self, config_dir: Optional[str] = None, default_env: str = "test"):
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)))
        self.default_env = default_env
        self.env = os.environ.get(self._ENV_VAR_NAME, self.default_env)
        self._lock = threading.RLock()
        self._config: Dict[str, Any] = {}
        self._config_obj = ConfigDict({})
        self._load_successfully = False
        self._adapter = _ConfigLoggerAdapter(logger, {"config_alias": self.env})
        self._load(reload_flag = False, path_override = None)

    def reload(self, path: Optional[str] = None) -> bool:
        """
        运行时热重载配置.

        - 若 path 为目录:从该目录读取 default.yaml 与 {env}.yaml
        - 若 path 为文件:从该文件所在目录读取 default.yaml,同时将该文件视为环境配置文件
        - 成功:校验通过后再替换内部缓存
        - 失败:保持旧缓存并记录 WARNING
        """
        with self._lock:
            old_config = self._config
            old_obj = self._config_obj
            old_dir = self.config_dir
            try:
                self._load(reload_flag = True, path_override = path)
                return True
            except Exception as exc:
                self._config = old_config
                self._config_obj = old_obj
                self.config_dir = old_dir
                self._adapter.warning(
                    f"[Reload] 配置重载失败,已回滚 | env={self.env} | reason={type(exc).__name__}: {exc}",
                    extra = {"reload": "1"},
                )
                return False

    def _resolve_paths(self, path_override: Optional[str]) -> Tuple[str, str, str]:
        if not path_override:
            base_dir = self.config_dir
            default_path = os.path.join(base_dir, self._DEFAULT_YAML_NAME)
            env_path = os.path.join(base_dir, f"{self.env}.yaml")
            return base_dir, default_path, env_path

        abs_path = os.path.abspath(path_override)
        if os.path.isdir(abs_path):
            base_dir = abs_path
            default_path = os.path.join(base_dir, self._DEFAULT_YAML_NAME)
            env_path = os.path.join(base_dir, f"{self.env}.yaml")
            return base_dir, default_path, env_path

        base_dir = os.path.dirname(abs_path)
        default_path = os.path.join(base_dir, self._DEFAULT_YAML_NAME)
        env_path = abs_path
        return base_dir, default_path, env_path

    def _load(self, reload_flag: bool, path_override: Optional[str]) -> None:
        base_dir, default_path, env_path = self._resolve_paths(path_override)
        self.config_dir = base_dir

        extra = {"reload": "1" if reload_flag else "0"}
        default_ok = True
        env_ok = True
        try:
            default_cfg, _default_meta = self._read_yaml_file(default_path, alias = "default", reload_flag = reload_flag)
        except Exception:
            default_cfg = {}
            default_ok = False
            if reload_flag:
                raise

        try:
            env_cfg, _env_meta = self._read_yaml_file(env_path, alias = self.env, reload_flag = reload_flag)
        except Exception:
            env_cfg = {}
            env_ok = False
            if reload_flag:
                raise

        merged_config = self._merge_configs(default_cfg, env_cfg)
        self._override_with_env_vars(merged_config)
        self._validate_root_mapping(merged_config, source = "merged")

        self._config = merged_config
        self._config_obj = ConfigDict(self._config)
        self._load_successfully = True

        total_keys = self._count_keys(self._config)
        if logger.isEnabledFor(logging.DEBUG) and total_keys > self._MAX_DEBUG_KEYS:
            top_keys = list(self._config.keys())
            preview = top_keys[:50]
            suffix = "..." if len(top_keys) > 50 else ""
            self._adapter.debug(
                f"配置键数量摘要 | env={self.env} | total_keys={total_keys} | top_level_keys={preview}{suffix}",
                extra = extra,
            )

        if logger.isEnabledFor(logging.INFO) and (default_ok or env_ok):
            sources = [
                os.path.basename(default_path),
                os.path.basename(env_path),
            ]
            prefix = "[Reload] " if reload_flag else ""
            self._adapter.info(
                f"{prefix}配置加载摘要 | env={self.env} | dir={os.path.abspath(base_dir)} | sources={sources} | total_keys={total_keys}",
                extra = extra,
            )

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

    def _validate_root_mapping(self, config: Any, source: str) -> None:
        if config is None:
            return
        if not isinstance(config, dict):
            raise ValueError(f"{source} 配置根节点必须为 dict,实际为 {type(config).__name__}")

    def _count_keys(self, data: Any) -> int:
        if isinstance(data, dict):
            total = len(data)
            for value in data.values():
                total += self._count_keys(value)
            return total
        if isinstance(data, list):
            total = 0
            for item in data:
                total += self._count_keys(item)
            return total
        return 0

    def _read_yaml_file(self, path: str, alias: str, reload_flag: bool, attempts: int = 2) -> Tuple[
        Dict[str, Any], Dict[str, Any]]:
        abs_path = os.path.abspath(path)
        extra = {"reload": "1" if reload_flag else "0"}

        file_size = None
        try:
            if os.path.exists(abs_path):
                file_size = os.path.getsize(abs_path)
        except Exception:
            file_size = None

        last_exc: Optional[BaseException] = None
        for attempt in range(1, attempts + 1):
            start = time.perf_counter()
            try:
                with open(abs_path, "r", encoding = "utf-8") as f:
                    loaded = yaml.safe_load(f)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                if loaded is None:
                    loaded = {}
                self._validate_root_mapping(loaded, source = alias)

                if logger.isEnabledFor(logging.DEBUG):
                    self._adapter.debug(
                        f"读取配置文件成功 | alias={alias} | path={abs_path} | elapsed_ms={elapsed_ms} | size_bytes={file_size}",
                        extra = extra,
                    )
                    if file_size is not None and file_size > self._LARGE_FILE_BYTES:
                        self._adapter.debug(
                            f"大文件加载耗时 | alias={alias} | path={abs_path} | elapsed_ms={elapsed_ms} | size_bytes={file_size}",
                            extra = extra,
                        )

                return loaded, {"path": abs_path, "elapsed_ms": elapsed_ms, "size_bytes": file_size}
            except (FileNotFoundError, PermissionError, IsADirectoryError, OSError, yaml.YAMLError, ValueError) as exc:
                last_exc = exc
                if attempt < attempts and logger.isEnabledFor(logging.DEBUG):
                    self._adapter.debug(
                        f"读取配置文件失败,准备重试 | alias={alias} | path={abs_path} | attempt={attempt}/{attempts} | exc={type(exc).__name__}: {exc}",
                        extra = extra,
                    )
                    time.sleep(0.05)
                    continue

                self._log_load_error(abs_path = abs_path, alias = alias, exc = exc, attempts = attempts, extra = extra)
                raise

        self._log_load_error(abs_path = abs_path, alias = alias, exc = last_exc or RuntimeError("unknown"), attempts = attempts, extra = extra)
        raise last_exc or RuntimeError("unknown")

    def _log_load_error(self, abs_path: str, alias: str, exc: BaseException, attempts: int, extra: Dict[
        str, Any]) -> None:
        tb_line = self._extract_tb_line(exc)
        yaml_line, yaml_col = self._extract_yaml_mark(exc)
        hint = self._hint_for_exception(abs_path, exc)

        parts = [
            f"配置加载失败 | alias={alias}",
            f"path={abs_path}",
            f"exc_type={type(exc).__name__}",
            f"tb_line={tb_line}",
            f"yaml_line={yaml_line}",
            f"yaml_col={yaml_col}",
            f"attempts={attempts}",
            f"hint={hint}",
        ]
        self._adapter.error(" | ".join(parts), extra = extra, exc_info = logger.isEnabledFor(logging.DEBUG))

    def _extract_tb_line(self, exc: BaseException) -> Optional[int]:
        try:
            tb = exc.__traceback__
            if not tb:
                return None
            frames = traceback.extract_tb(tb)
            if not frames:
                return None
            return frames[-1].lineno
        except Exception:
            return None

    def _extract_yaml_mark(self, exc: BaseException) -> Tuple[Optional[int], Optional[int]]:
        if isinstance(exc, yaml.YAMLError) and hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            try:
                return int(exc.problem_mark.line) + 1, int(exc.problem_mark.column) + 1
            except Exception:
                return None, None
        return None, None

    def _hint_for_exception(self, abs_path: str, exc: BaseException) -> str:
        base_name = os.path.basename(abs_path)
        if isinstance(exc, FileNotFoundError):
            return f"文件不存在,请检查 {base_name} 是否被移动或未同步到 config 目录"
        if isinstance(exc, PermissionError):
            return f"权限不足,请检查 {base_name} 的读权限或运行用户权限"
        if isinstance(exc, IsADirectoryError):
            return f"路径指向目录,请检查配置路径是否误传为目录:{abs_path}"
        if isinstance(exc, yaml.YAMLError):
            return "YAML 语法错误,请检查缩进、冒号与列表符号是否正确"
        if isinstance(exc, ValueError):
            return "配置格式校验失败,请确保 YAML 根节点为映射(dict)"
        return "请检查路径、编码与 YAML 内容是否有效"

    def _override_with_env_vars(self, config: Dict[str, Any]) -> None:
        """
        使用环境变量覆盖配置
        支持嵌套配置,环境变量名格式: SECTION_KEY 或 SECTION__KEY(双下划线表示嵌套)

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

    def __getitem__(self, key: str) -> Any:
        return self._config[key]

    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        更新当前配置

        Args:
            updates: 要更新的配置
        """
        with self._lock:
            self._config = self._merge_configs(self._config, updates)
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

        # 从环境变量获取配置(优先级最高)
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
            # 尝试转换为小写并通过点号路径获取(支持驼峰转蛇形)
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
                        # 获取项目根目录(配置目录的父目录)
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


# 实际的配置管理器实例(私有变量)
_actual_config_manager: Optional[ConfigManager] = None
_actual_config_manager_lock = threading.RLock()


# 懒加载配置管理器实例
def get_config_manager(config_dir: Optional[str] = None, default_env: str = "test") -> ConfigManager:
    """
    懒加载获取配置管理器实例
    
    Returns:
        ConfigManager: 配置管理器实例
    """
    global _actual_config_manager
    if _actual_config_manager is None:
        with _actual_config_manager_lock:
            if _actual_config_manager is None:
                _actual_config_manager = ConfigManager(config_dir = config_dir, default_env = default_env)
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
        # cm.get_config_value("report.allure_report_dir", "./reports/allure-report"),
        # cm.get_config_value("report.allure_result_dir", "./reports/allure-results"),
        cm.get_config_value("screenshot.dir", "./reports/screenshots"),
    ]

    for dir_path in dirs_to_create:
        if dir_path:
            # 确保路径是绝对路径, 基于项目根目录
            if not os.path.isabs(dir_path):
                dir_path = os.path.abspath(os.path.join(project_root, dir_path))
            os.makedirs(dir_path, exist_ok = True)


# 向后兼容: 创建config实例(懒加载)
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

# 全局配置管理器实例(懒加载)
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
except Exception:
    # 如果在导入时调用失败, 忽略错误, 稍后在实际使用时再调用
    pass
