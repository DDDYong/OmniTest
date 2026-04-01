import importlib
import sys
import threading

import pytest

from config.config_manager import ConfigDict, ConfigManager
from utils.path.path_util import PathUtil

path_util_module = importlib.import_module("utils.path.path_util")


def test_imports_and_api_surface():
    import omni_test
    import run

    assert hasattr(omni_test, "ot")
    assert hasattr(omni_test, "OmniTest")
    assert hasattr(omni_test, "ExecutionResult")
    assert hasattr(run, "ExecutionRequest")
    assert hasattr(run, "build_execution_request")
    assert hasattr(run, "execute_request")

    ot = omni_test.ot
    for name in ("clean", "api", "web", "app", "parallel", "performance", "all", "report"):
        assert hasattr(ot, name), name

    for name in (
        "clean_reports",
        "run_api_tests",
        "run_web_tests",
        "run_app_tests",
        "run_parallel_tests",
        "run_performance_tests",
        "run_all_tests",
        "generate_allure_report",
        "open_allure_report",
        "update_requirements",
        "add_package_to_requirements",
    ):
        assert hasattr(run.TestRunner, name), name


def test_cli_help_exits_zero(monkeypatch):
    import run

    monkeypatch.setattr(sys, "argv", ["run.py", "--help"])
    with pytest.raises(SystemExit) as exc:
        run.parse_arguments()
    assert exc.value.code == 0


def test_config_schema_validates_present_typed_keys_only():
    manager = ConfigManager.__new__(ConfigManager)

    manager._validate_schema({
        "log": {"dir": "./logs"},
        "mysql": {"default": {"host": "127.0.0.1"}},
    })


def test_config_schema_rejects_present_wrong_types():
    manager = ConfigManager.__new__(ConfigManager)

    with pytest.raises(ValueError):
        manager._validate_schema({"timeout": {"default": "30"}})


def test_get_config_value_returns_copy_for_mutable_values():
    manager = ConfigManager.__new__(ConfigManager)
    manager._config = {
        "mysql": {"default": {"host": "127.0.0.1", "port": 3306}},
        "items": ["a", "b"],
    }
    manager._config_obj = ConfigDict(manager._config)

    mysql_config = manager.get_config_value("mysql.default")
    items = manager.get_config_value("items")

    mysql_config["host"] = "mutated"
    items.append("c")

    assert manager._config["mysql"]["default"]["host"] == "127.0.0.1"
    assert manager._config["items"] == ["a", "b"]


def test_update_config_validates_before_assigning():
    manager = ConfigManager.__new__(ConfigManager)
    manager._lock = threading.RLock()
    manager._config = {"timeout": {"default": 30, "page_load": 60, "implicitly_wait": 10}}
    manager._config_obj = ConfigDict(manager._config)

    with pytest.raises(ValueError):
        manager.update_config({"timeout": {"default": "bad"}})

    assert manager._config == {"timeout": {"default": 30, "page_load": 60, "implicitly_wait": 10}}


def test_update_config_keeps_valid_merge_behavior():
    manager = ConfigManager.__new__(ConfigManager)
    manager._lock = threading.RLock()
    manager._config = {"timeout": {"default": 30, "page_load": 60, "implicitly_wait": 10}, "log": {"dir": "./logs"}}
    manager._config_obj = ConfigDict(manager._config)

    manager.update_config({"timeout": {"default": 15}})

    assert manager._config["timeout"] == {"default": 15, "page_load": 60, "implicitly_wait": 10}
    assert manager._config["log"] == {"dir": "./logs"}


def test_update_config_detaches_from_input_payload():
    manager = ConfigManager.__new__(ConfigManager)
    manager._lock = threading.RLock()
    manager._config = {"timeout": {"default": 30, "page_load": 60, "implicitly_wait": 10}}
    manager._config_obj = ConfigDict(manager._config)

    payload = {"custom": {"items": []}}
    manager.update_config(payload)
    payload["custom"]["items"].append("x")

    assert manager._config["custom"] == {"items": []}


def test_get_test_run_dir_is_stable_across_threads(monkeypatch):
    PathUtil._current_test_run_dir = None
    values = []

    class _FakeNow:
        def strftime(self, _format):
            return "20260331_1500"

    class _FakeDatetime:
        @staticmethod
        def now():
            return _FakeNow()

    monkeypatch.setattr(path_util_module, "datetime", _FakeDatetime)

    def worker():
        values.append(PathUtil.get_test_run_dir())

    threads = [threading.Thread(target = worker) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert set(values) == {"20260331_1500"}
