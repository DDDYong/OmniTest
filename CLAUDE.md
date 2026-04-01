# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniTest is a comprehensive automated testing framework supporting API, Web, App, and performance tests. It provides
both a CLI runner (`run.py`) and a chainable programmatic API (`omni_test.py`).

## Setup

```bash
# Create and activate venv
python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Install in editable mode (enables omni-test / omni CLI entry points)
pip install -e .

# Install Allure CLI (required for reports)
brew install allure
```

## Running Tests

```bash
# Run the full offline baseline suite (no external dependencies)
pytest tests/baseline/test_baseline.py -v

# Run a single test by name
pytest tests/baseline/test_baseline.py::test_imports_and_api_surface -v

# Run with coverage
pytest tests/baseline/ --cov=. --cov-report=term-missing

# Run all API / Web / App tests via CLI
python run.py api
python run.py web
python run.py app

# Run a specific file or filter by marker
python run.py api --file test_user_management.py
python run.py api --markers smoke

# Parallel tests (requires @pytest.mark.parallel on cases)
python run.py parallel --workers 3

# Performance tests (requires locust)
python run.py performance test_api_load.py --users 200 --spawn-rate 20 --run-time 10m

# Generate and view Allure report
python run.py report

# Clean old reports (keeps last 7 days)
python run.py clean
```

## Programmatic API

```python
from omni_test import ot          # global singleton
from omni_test import OmniTest    # new instance

# Chainable calls; each method returns self
ot.clean().api().web().report()
ot.api(test_file="test_user.py", markers="smoke", auto_report=False)

# Exit-code introspection after chain
print(ot.last_exit_code)   # 0 = pass, 4 = invalid target, other = failure
print(ot.last_error)       # Exception or None
```

## Architecture

### Execution pipeline

```
run.py / main.py          CLI entry – argparse → ExecutionRequest (frozen dataclass)
omni_test.py              Programmatic API – OmniTest wraps ExecutionRequest + reports
run.py::execute_request   Dispatches command to TestRunner static methods
utils/runner/test_runner  Core pytest / locust subprocess execution; path resolution
utils/reporting/          Allure report generation & report-index HTML
utils/packaging/          requirements.txt management
```

**TestRunner** (`run.py`) is a thin backward-compatibility facade; all real logic lives in
`utils/runner/test_runner.py`, `utils/reporting/allure_report.py`, and `utils/packaging/requirements_manager.py`.

### Exit code conventions

- `0` – all tests passed
- `4` (`INVALID_TEST_TARGET_EXIT_CODE`) – test file/dir not found; report generation is **skipped**
- Other non-zero – test failures; report is still generated

### Configuration system (`config/`)

`ConfigManager` loads YAML configs with this merge priority (high → low):

1. Runtime `update_config()` / attribute assignment
2. Environment variables (prefixes: `API_`, `WEB_`, `DB_`, `SSH_`, `LOG_`, `REPORT_`, `MYSQL_`, `REDIS_`; nested with
   `__`)
3. `config/{OMNITEST_ENV}.yaml` (env var `OMNITEST_ENV`, default `test`)
4. `config/default.yaml`

Access pattern: `from config.config_manager import config` then `config.log.level`, `config.mysql.default.host`, etc.

`get_config_manager()` returns a thread-safe lazy singleton. `config` and `config_manager` module-level names are lazy
proxy objects.

Runtime hot-reload with rollback on failure:

```python
from config.config_manager import get_config_manager
get_config_manager().reload()             # reload from current dir
get_config_manager().reload("config/test.yaml")  # reload from specific file
```

### Path management (`utils/path/path_util.py`)

`PathUtil` is the single source of truth for all directory paths. Reports are stored under `reports/YYYYMMDD_HHMM/` (one
timestamped folder per test run). The run timestamp is initialized once per process (thread-safe lazy singleton on
`PathUtil._current_test_run_dir`).

### Test cases (`cases/`)

| Directory            | Test type               | Base class / tool                                 |
|----------------------|-------------------------|---------------------------------------------------|
| `cases/api/`         | API (requests + pytest) | direct `requests` calls                           |
| `cases/web/`         | Web (Selenium)          | `utils/web/web_base_page.py`, Page Object pattern |
| `cases/app/`         | App (Appium)            | `utils/app/app_base_page.py`, Page Object pattern |
| `cases/performance/` | Performance (Locust)    | `utils/performance/locust_base.py`                |

### Utilities (`utils/`)

| Package               | Purpose                                                                        |
|-----------------------|--------------------------------------------------------------------------------|
| `utils/api/`          | HTTP client + request manager                                                  |
| `utils/web/`          | Selenium element handler, WebBasePage                                          |
| `utils/app/`          | Appium manager, AppBasePage                                                    |
| `utils/db/`           | MySQL + Redis clients (config via `get_mysql_config()` / `get_redis_config()`) |
| `utils/assert/`       | Custom assertion helpers                                                       |
| `utils/screenshot/`   | Screenshot capture                                                             |
| `utils/notification/` | Notification integration                                                       |
| `utils/decorator/`    | `@timing` decorator and others                                                 |
| `utils/file/`         | FileHandler for JSON/YAML test data                                            |
| `utils/logger/`       | Shared `logger` instance                                                       |

### Offline baseline tests (`tests/baseline/`)

`test_baseline.py` validates import contracts and key interfaces without network or file-system dependencies. Run these
first when modifying core modules (`omni_test.py`, `run.py`, `config/config_manager.py`, `utils/path/path_util.py`).

## Environment Variables

| Variable                      | Effect                                                      |
|-------------------------------|-------------------------------------------------------------|
| `OMNITEST_ENV`                | Config environment (`test` / `prod`), default `test`        |
| `LOG_LEVEL`                   | Override log level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `LOG_CONFIG_PATH`             | Absolute path to custom `logging.yaml`                      |
| `OMNITEST_USE_LOGGING_YAML=1` | Use built-in `config/logging.yaml`                          |

## Linting / Formatting

```bash
black .
flake8 .
```