from omni_test import OmniTest
from run import TestRunner, build_execution_request, execute_request
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

    def generate_report_index(self):
        self.calls.append(("generate_report_index", (), {}))
        return "index.html"

    def run_api_tests(self, test_dir = None, test_file = None, markers = None):
        self.calls.append(("run_api_tests", (test_dir, test_file, markers), {}))
        return self.exit_code

    def run_web_tests(self, test_dir = None, test_file = None, markers = None):
        self.calls.append(("run_web_tests", (test_dir, test_file, markers), {}))
        return self.exit_code

    def run_app_tests(self, test_dir = None, test_file = None, markers = None):
        self.calls.append(("run_app_tests", (test_dir, test_file, markers), {}))
        return self.exit_code

    def run_all_tests(self):
        self.calls.append(("run_all_tests", (), {}))
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
    assert_util.equals(sum(1 for name, _, _ in runner.calls if name == "clean_reports"), 1)


def test_api_failure_still_generates_report():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 1)
    ot.runner = runner
    ot.api(auto_clean = False, auto_report = True)
    report_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_allure_report"]
    index_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_report_index"]
    assert_util.equals(len(report_calls), 1)
    assert_util.equals(report_calls[0][2], {"serve": False, "wait_for_enter": False})
    assert_util.equals(len(index_calls), 1)


def test_web_failure_still_generates_report():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 1)
    ot.runner = runner
    ot.web(auto_clean = False, auto_report = True)
    report_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_allure_report"]
    index_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_report_index"]
    assert_util.equals(len(report_calls), 1)
    assert_util.equals(report_calls[0][2], {"serve": False, "wait_for_enter": False})
    assert_util.equals(len(index_calls), 1)


def test_app_failure_still_generates_report():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 1)
    ot.runner = runner
    ot.app(auto_clean = False, auto_report = True)
    report_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_allure_report"]
    index_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_report_index"]
    assert_util.equals(len(report_calls), 1)
    assert_util.equals(report_calls[0][2], {"serve": False, "wait_for_enter": False})
    assert_util.equals(len(index_calls), 1)


def test_api_invalid_target_does_not_generate_report():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 4)
    ot.runner = runner
    ot.api(auto_clean = False, auto_report = True)
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in runner.calls))
    assert_util.is_false(any(name == "generate_report_index" for name, _, _ in runner.calls))


def test_app_invalid_target_does_not_generate_report_and_sets_skip_reason():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 4)
    ot.runner = runner

    ot.app(auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_result.test_kind, "app")
    assert_util.equals(ot.last_result.exit_code, 4)
    assert_util.is_false(ot.last_result.report_generated)
    assert_util.equals(ot.last_result.report_skipped_reason, "invalid_test_target")
    assert_util.equals(runner.calls[0][0], "run_app_tests")
    assert_util.equals(sum(1 for name, _, _ in runner.calls if name == "run_app_tests"), 1)
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in runner.calls))
    assert_util.is_false(any(name == "generate_report_index" for name, _, _ in runner.calls))


def test_parallel_parameter_aliases():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner
    ot.parallel(workers = 3, html = True, auto_clean = False, auto_report = False)
    assert_util.equals(runner.parallel_args, (None, None, "parallel", 3, True))


def test_web_auto_clean_calls_clean_first():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner
    ot.web(auto_clean = True, auto_report = False)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_web_tests")
    assert_util.equals(sum(1 for name, _, _ in runner.calls if name == "clean_reports"), 1)


def test_app_auto_clean_calls_clean_first():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner
    ot.app(auto_clean = True, auto_report = False)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_app_tests")
    assert_util.equals(sum(1 for name, _, _ in runner.calls if name == "clean_reports"), 1)


def test_api_sets_last_result_and_legacy_fields():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner

    ot.api(test_dir = "smoke", test_file = "test_user.py", markers = "quick", auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_exit_code, 0)
    assert_util.equals(ot.last_error, None)
    assert_util.equals(ot.last_result.test_kind, "api")
    assert_util.equals(ot.last_result.exit_code, 0)
    assert_util.equals(ot.last_result.target["测试目录"], "smoke")
    assert_util.equals(ot.last_result.target["测试文件"], "test_user.py")
    assert_util.equals(ot.last_result.target["测试标记"], "quick")
    assert_util.is_true(ot.last_result.report_requested)
    assert_util.is_true(ot.last_result.report_generated)
    assert_util.equals(ot.last_result.report_skipped_reason, None)
    assert_util.equals(ot.last_result.report_info["report_generated"], True)
    assert_util.is_true("run_id" in ot.last_result.report_info)


def test_api_invalid_target_sets_report_skip_reason():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 4)
    ot.runner = runner

    ot.api(auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_result.exit_code, 4)
    assert_util.is_false(ot.last_result.report_generated)
    assert_util.equals(ot.last_result.report_skipped_reason, "invalid_test_target")


def test_api_exception_sets_last_result_error():
    ot = OmniTest()

    class _BoomRunner(_FakeRunner):
        def run_api_tests(self, test_dir = None, test_file = None, markers = None):
            raise RuntimeError("boom")

    ot.runner = _BoomRunner()

    result = ot.api(auto_clean = False, auto_report = True)

    assert_util.equals(result, ot)
    assert isinstance(ot.last_error, RuntimeError)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.test_kind, "api")
    assert_util.equals(ot.last_result.exit_code, None)
    assert_util.equals(ot.last_result.report_skipped_reason, "runner_exception")


def test_parallel_last_result_records_normalized_options():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner

    ot.parallel(workers = 3, html = True, auto_clean = False, auto_report = False)

    assert_util.equals(ot.last_result.test_kind, "parallel")
    assert_util.equals(ot.last_result.target["worker数量"], 3)
    assert_util.equals(ot.last_result.target["HTML报告"], True)
    assert_util.is_false(ot.last_result.report_requested)


def test_web_sets_last_result_and_legacy_fields():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner

    ot.web(test_dir = "smoke", test_file = "test_page.py", markers = "quick", auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_exit_code, 0)
    assert_util.equals(ot.last_error, None)
    assert_util.equals(ot.last_result.test_kind, "web")
    assert_util.equals(ot.last_result.exit_code, 0)
    assert_util.equals(ot.last_result.target["测试目录"], "smoke")
    assert_util.equals(ot.last_result.target["测试文件"], "test_page.py")
    assert_util.equals(ot.last_result.target["测试标记"], "quick")
    assert_util.is_true(ot.last_result.report_requested)
    assert_util.is_true(ot.last_result.report_generated)
    assert_util.equals(ot.last_result.report_skipped_reason, None)


def test_web_invalid_target_does_not_generate_report_and_sets_skip_reason():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 4)
    ot.runner = runner

    ot.web(auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_result.test_kind, "web")
    assert_util.equals(ot.last_result.exit_code, 4)
    assert_util.is_false(ot.last_result.report_generated)
    assert_util.equals(ot.last_result.report_skipped_reason, "invalid_test_target")
    assert_util.equals(runner.calls[0][0], "run_web_tests")
    assert_util.equals(sum(1 for name, _, _ in runner.calls if name == "run_web_tests"), 1)
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in runner.calls))
    assert_util.is_false(any(name == "generate_report_index" for name, _, _ in runner.calls))


def test_web_cleanup_failure_short_circuits_execution():
    ot = OmniTest()

    class _CleanupBoomRunner(_FakeRunner):
        def clean_reports(self):
            self.calls.append(("clean_reports", (), {}))
            raise RuntimeError("cleanup boom")

    ot.runner = _CleanupBoomRunner(exit_code = 0)

    ot.web(auto_clean = True, auto_report = True)

    assert_util.equals(ot.last_result.test_kind, "web")
    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.report_skipped_reason, "cleanup_failed")
    assert_util.equals(ot.runner.calls[0][0], "clean_reports")
    assert_util.equals(sum(1 for name, _, _ in ot.runner.calls if name == "clean_reports"), 1)
    assert_util.is_false(any(name == "run_web_tests" for name, _, _ in ot.runner.calls))
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in ot.runner.calls))


def test_app_cleanup_failure_short_circuits_execution():
    ot = OmniTest()

    class _CleanupBoomRunner(_FakeRunner):
        def clean_reports(self):
            self.calls.append(("clean_reports", (), {}))
            raise RuntimeError("cleanup boom")

    ot.runner = _CleanupBoomRunner(exit_code = 0)

    ot.app(auto_clean = True, auto_report = True)

    assert_util.equals(ot.last_result.test_kind, "app")
    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.report_skipped_reason, "cleanup_failed")
    assert_util.equals(ot.runner.calls[0][0], "clean_reports")
    assert_util.equals(sum(1 for name, _, _ in ot.runner.calls if name == "clean_reports"), 1)
    assert_util.is_false(any(name == "run_app_tests" for name, _, _ in ot.runner.calls))
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in ot.runner.calls))


def test_app_sets_last_result_and_legacy_fields():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner

    ot.app(test_dir = "smoke", test_file = "test_app.py", markers = "quick", auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_exit_code, 0)
    assert_util.equals(ot.last_error, None)
    assert_util.equals(ot.last_result.test_kind, "app")
    assert_util.equals(ot.last_result.exit_code, 0)
    assert_util.equals(ot.last_result.target["测试目录"], "smoke")
    assert_util.equals(ot.last_result.target["测试文件"], "test_app.py")
    assert_util.equals(ot.last_result.target["测试标记"], "quick")
    assert_util.is_true(ot.last_result.report_requested)
    assert_util.is_true(ot.last_result.report_generated)
    assert_util.equals(ot.last_result.report_skipped_reason, None)


def test_all_auto_clean_calls_clean_first():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner
    ot.all(auto_clean = True, auto_report = False)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_all_tests")
    assert_util.equals(sum(1 for name, _, _ in runner.calls if name == "clean_reports"), 1)


def test_all_keeps_report_generation_on_exit_code_four():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 4)
    ot.runner = runner

    ot.all(auto_clean = False, auto_report = True)

    report_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_allure_report"]
    index_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_report_index"]

    assert_util.equals(ot.last_result.test_kind, "all")
    assert_util.equals(ot.last_result.exit_code, 4)
    assert_util.equals(dict(ot.last_result.target), {})
    assert_util.is_true(ot.last_result.report_requested)
    assert_util.is_true(ot.last_result.report_generated)
    assert_util.equals(ot.last_result.report_skipped_reason, None)
    assert_util.equals(runner.calls[0][0], "run_all_tests")
    assert_util.equals(len(report_calls), 1)
    assert_util.equals(report_calls[0][2], {"serve": False, "wait_for_enter": False})
    assert_util.equals(len(index_calls), 1)


def test_all_cleanup_failure_short_circuits_execution():
    ot = OmniTest()

    class _CleanupBoomRunner(_FakeRunner):
        def clean_reports(self):
            self.calls.append(("clean_reports", (), {}))
            raise RuntimeError("cleanup boom")

    ot.runner = _CleanupBoomRunner(exit_code = 0)

    ot.all(auto_clean = True, auto_report = True)

    assert_util.equals(ot.last_result.test_kind, "all")
    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.report_skipped_reason, "cleanup_failed")
    assert_util.equals(ot.runner.calls[0][0], "clean_reports")
    assert_util.is_false(any(name == "run_all_tests" for name, _, _ in ot.runner.calls))
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in ot.runner.calls))


def test_all_report_failure_preserves_exit_code():
    ot = OmniTest()

    class _ReportBoomRunner(_FakeRunner):
        def generate_allure_report(self, *args, **kwargs):
            raise RuntimeError("report boom")

    ot.runner = _ReportBoomRunner(exit_code = 0)
    ot.all(auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_exit_code, 0)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.exit_code, 0)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.report_generated, False)
    assert_util.equals(ot.last_result.report_skipped_reason, "report_generation_failed")


def test_web_exception_sets_last_result_error():
    ot = OmniTest()

    class _BoomRunner(_FakeRunner):
        def run_web_tests(self, test_dir = None, test_file = None, markers = None):
            raise RuntimeError("boom")

    ot.runner = _BoomRunner()

    result = ot.web(auto_clean = False, auto_report = True)

    assert_util.equals(result, ot)
    assert isinstance(ot.last_error, RuntimeError)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.test_kind, "web")
    assert_util.equals(ot.last_result.exit_code, None)
    assert_util.equals(ot.last_result.report_skipped_reason, "runner_exception")


def test_app_exception_sets_last_result_error():
    ot = OmniTest()

    class _BoomRunner(_FakeRunner):
        def run_app_tests(self, test_dir = None, test_file = None, markers = None):
            raise RuntimeError("boom")

    ot.runner = _BoomRunner()

    result = ot.app(auto_clean = False, auto_report = True)

    assert_util.equals(result, ot)
    assert isinstance(ot.last_error, RuntimeError)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.test_kind, "app")
    assert_util.equals(ot.last_result.exit_code, None)
    assert_util.equals(ot.last_result.report_skipped_reason, "runner_exception")


def test_api_exception_clears_stale_last_exit_code():
    ot = OmniTest()
    healthy_runner = _FakeRunner(exit_code = 0)
    ot.runner = healthy_runner
    ot.api(auto_clean = False, auto_report = False)
    assert_util.equals(ot.last_exit_code, 0)

    class _BoomRunner(_FakeRunner):
        def run_api_tests(self, test_dir = None, test_file = None, markers = None):
            raise RuntimeError("boom")

    ot.runner = _BoomRunner()
    ot.api(auto_clean = False, auto_report = False)

    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)


def test_api_report_failure_preserves_exit_code():
    ot = OmniTest()

    class _ReportBoomRunner(_FakeRunner):
        def generate_allure_report(self, *args, **kwargs):
            raise RuntimeError("report boom")

    ot.runner = _ReportBoomRunner(exit_code = 0)
    ot.api(auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_exit_code, 0)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.exit_code, 0)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.report_generated, False)
    assert_util.equals(ot.last_result.report_skipped_reason, "report_generation_failed")


def test_api_false_report_result_still_generates_index():
    ot = OmniTest()

    class _FalseReportRunner(_FakeRunner):
        def generate_allure_report(self, *args, **kwargs):
            self.calls.append(("generate_allure_report", args, kwargs))
            return False

    ot.runner = _FalseReportRunner(exit_code = 0)
    ot.api(auto_clean = False, auto_report = True)

    report_calls = [(name, args, kwargs) for name, args, kwargs in ot.runner.calls if name == "generate_allure_report"]
    index_calls = [(name, args, kwargs) for name, args, kwargs in ot.runner.calls if name == "generate_report_index"]

    assert_util.equals(len(report_calls), 1)
    assert_util.equals(len(index_calls), 1)
    assert_util.equals(ot.last_exit_code, 0)
    assert_util.equals(ot.last_error, None)
    assert_util.equals(ot.last_result.report_generated, False)
    assert_util.equals(ot.last_result.report_skipped_reason, None)


def test_web_exception_clears_stale_last_exit_code():
    ot = OmniTest()
    healthy_runner = _FakeRunner(exit_code = 0)
    ot.runner = healthy_runner
    ot.web(auto_clean = False, auto_report = False)
    assert_util.equals(ot.last_exit_code, 0)

    class _BoomRunner(_FakeRunner):
        def run_web_tests(self, test_dir = None, test_file = None, markers = None):
            raise RuntimeError("boom")

    ot.runner = _BoomRunner()
    ot.web(auto_clean = False, auto_report = False)

    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)


def test_app_exception_clears_stale_last_exit_code():
    ot = OmniTest()
    healthy_runner = _FakeRunner(exit_code = 0)
    ot.runner = healthy_runner
    ot.app(auto_clean = False, auto_report = False)
    assert_util.equals(ot.last_exit_code, 0)

    class _BoomRunner(_FakeRunner):
        def run_app_tests(self, test_dir = None, test_file = None, markers = None):
            raise RuntimeError("boom")

    ot.runner = _BoomRunner()
    ot.app(auto_clean = False, auto_report = False)

    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)


def test_web_report_failure_preserves_exit_code():
    ot = OmniTest()

    class _ReportBoomRunner(_FakeRunner):
        def generate_allure_report(self, *args, **kwargs):
            raise RuntimeError("report boom")

    ot.runner = _ReportBoomRunner(exit_code = 0)
    ot.web(auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_exit_code, 0)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.exit_code, 0)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.report_generated, False)
    assert_util.equals(ot.last_result.report_skipped_reason, "report_generation_failed")


def test_app_report_failure_preserves_exit_code():
    ot = OmniTest()

    class _ReportBoomRunner(_FakeRunner):
        def generate_allure_report(self, *args, **kwargs):
            raise RuntimeError("report boom")

    ot.runner = _ReportBoomRunner(exit_code = 0)
    ot.app(auto_clean = False, auto_report = True)

    assert_util.equals(ot.last_exit_code, 0)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.exit_code, 0)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.report_generated, False)
    assert_util.equals(ot.last_result.report_skipped_reason, "report_generation_failed")


def test_api_cleanup_failure_short_circuits_execution():
    ot = OmniTest()

    class _CleanupBoomRunner(_FakeRunner):
        def clean_reports(self):
            raise RuntimeError("cleanup boom")

    ot.runner = _CleanupBoomRunner(exit_code = 0)

    ot.api(auto_clean = True, auto_report = True)

    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)
    assert isinstance(ot.last_result.error, RuntimeError)
    assert_util.equals(ot.last_result.report_generated, False)
    assert_util.equals(ot.last_result.report_skipped_reason, "cleanup_failed")
    assert_util.is_false(any(name == "run_api_tests" for name, _, _ in ot.runner.calls))
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in ot.runner.calls))


def test_clean_updates_last_result_state():
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner

    ot.clean()

    assert_util.equals(ot.last_exit_code, 0)
    assert_util.equals(ot.last_error, None)
    assert_util.equals(ot.last_result.test_kind, "clean")
    assert_util.equals(ot.last_result.exit_code, 0)
    assert_util.equals(ot.last_result.report_generated, False)


def test_report_failure_updates_last_result_state():
    ot = OmniTest()

    class _OpenBoomRunner(_FakeRunner):
        def open_allure_report(self):
            raise RuntimeError("open boom")

    ot.runner = _OpenBoomRunner(exit_code = 0)

    ot.report(generate = False, open = True)

    assert_util.equals(ot.last_exit_code, None)
    assert isinstance(ot.last_error, RuntimeError)
    assert_util.equals(ot.last_result.test_kind, "report")
    assert_util.equals(ot.last_result.report_skipped_reason, "report_operation_failed")


def test_report_info_does_not_create_dirs_when_report_not_generated(monkeypatch):
    ot = OmniTest()
    runner = _FakeRunner(exit_code = 0)
    ot.runner = runner

    called = {"create_dirs": None}
    original = path_util.get_current_run_context

    def fake_get_current_run_context(create_dirs = True):
        called["create_dirs"] = create_dirs
        return original(create_dirs = create_dirs)

    monkeypatch.setattr(path_util, "get_current_run_context", fake_get_current_run_context)

    ot.api(auto_clean = False, auto_report = False)

    assert_util.equals(called["create_dirs"], False)


def test_build_execution_request_for_parallel():
    class _Args:
        command = "parallel"
        dir = "api"
        file = "test_demo.py"
        markers = "parallel"
        workers = 4
        html = True

    request = build_execution_request(_Args())
    assert_util.equals(request.command, "parallel")
    assert_util.equals(request.test_dir, "api")
    assert_util.equals(request.test_file, "test_demo.py")
    assert_util.equals(request.num_workers, 4)
    assert_util.equals(request.html_report, True)


def test_execute_request_for_api_keeps_invalid_target_skip():
    runner = _FakeRunner(exit_code = 4)

    class _Request:
        command = "api"
        test_dir = None
        test_file = None
        markers = None
        auto_clean = True
        auto_report = True

    exit_code = execute_request(_Request(), runner)
    assert_util.equals(exit_code, 4)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_api_tests")
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in runner.calls))


def test_execute_request_for_web_keeps_invalid_target_skip():
    runner = _FakeRunner(exit_code = 4)

    class _Request:
        command = "web"
        test_dir = None
        test_file = None
        markers = None
        auto_clean = True
        auto_report = True

    exit_code = execute_request(_Request(), runner)
    assert_util.equals(exit_code, 4)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_web_tests")
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in runner.calls))


def test_execute_request_for_app_keeps_invalid_target_skip():
    runner = _FakeRunner(exit_code = 4)

    class _Request:
        command = "app"
        test_dir = None
        test_file = None
        markers = None
        auto_clean = True
        auto_report = True

    exit_code = execute_request(_Request(), runner)
    assert_util.equals(exit_code, 4)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_app_tests")
    assert_util.is_false(any(name == "generate_allure_report" for name, _, _ in runner.calls))


def test_execute_request_for_all_keeps_report_generation():
    runner = _FakeRunner(exit_code = 4)

    class _Request:
        command = "all"
        auto_clean = True
        auto_report = True

    exit_code = execute_request(_Request(), runner)
    report_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_allure_report"]
    index_calls = [(name, args, kwargs) for name, args, kwargs in runner.calls if name == "generate_report_index"]

    assert_util.equals(exit_code, 4)
    assert_util.equals(runner.calls[0][0], "clean_reports")
    assert_util.equals(runner.calls[1][0], "run_all_tests")
    assert_util.equals(len(report_calls), 1)
    assert_util.equals(report_calls[0][2], {})
    assert_util.equals(len(index_calls), 1)


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
