import pytest

from omni_test import OmniTest
from run import TestRunner
from utils import assert_util as AssertUtil
from utils.path import path_util

assert_util = AssertUtil()


class _FakeRunner:
    def __init__(self, exit_code = 0):
        self.exit_code = exit_code
        self.calls = []
        self.parallel_args = None

    def clean_reports(self):
        self.calls.append(("clean_reports", (), {}))

    def run_api_tests(self, test_dir = None, test_file = None, markers = None):
        self.calls.append(("run_api_tests", (test_dir, test_file, markers), {}))
        return self.exit_code

    def generate_allure_report(self, *args, **kwargs):
        self.calls.append(("generate_allure_report", args, kwargs))
        return True

    def open_allure_report(self):
        self.calls.append(("open_allure_report", (), {}))
        return True

    def run_parallel_tests(self, test_dir = None, test_file = None, markers = "parallel", num_workers = 2, html_report = False):
        self.parallel_args = (test_dir, test_file, markers, num_workers, html_report)
        self.calls.append(("run_parallel_tests", self.parallel_args, {}))
        return self.exit_code


def test_api_auto_clean_calls_clean_first():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner
    ot.api(auto_clean = True, auto_report = False)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_api_tests")


def test_api_failure_still_generates_report():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 1)
    ot.runner = runner
    ot.api(auto_clean = False, auto_report = True)
    assert_util.is_true(any(name == "generate_allure_report" for name, _, _ in runner.calls))


def test_api_invalid_target_does_not_generate_report():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 4)
    ot.runner = runner
    ot.api(auto_clean = False, auto_report = True)
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in runner.calls))


def test_parallel_parameter_aliases():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner
    ot.parallel(workers = 3, html = True, auto_clean = False, auto_report = False)
    assert_util.equals(runner.parallel_args, (None, None, "parallel", 3, True))


def test_run_parallel_defaults_to_cases_dir(monkeypatch):
    captured = {}

    def fake_run(cmd, cwd = None, text = None, **kwargs):
        captured["cmd"] = cmd

        class _R:
            returncode = 0

        return _R()

    # 由于重构,run.py 中不再直接包含 subprocess.run 的调用逻辑
    # 而是转调到了 utils.runner.test_runner,所以需要 mock 该模块
    monkeypatch.setattr("utils.runner.test_runner.subprocess.run", fake_run)

    exit_code = TestRunner.run_parallel_tests()
    assert_util.equals(exit_code, 0)
    assert_util.equals(captured["cmd"][3], path_util.get_cases_dir())
