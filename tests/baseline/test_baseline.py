import sys

import pytest


def test_imports_and_api_surface():
    import omni_test
    import run

    assert hasattr(omni_test, "ot")
    assert hasattr(omni_test, "OmniTest")

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
