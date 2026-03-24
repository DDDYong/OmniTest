# OmniTest 自动化测试框架

## 项目简介

OmniTest 是一个全面的自动化测试框架,支持 API、Web、APP 和性能测试,提供统一的命令行接口和编程 API,帮助测试团队高效地执行各种自动化测试任务。

### 主要特点

- **多类型测试支持**：集成 API、Web、APP 和性能测试于一体
- **统一命令行接口**：简洁的命令行操作方式
- **友好编程 API**：支持在 Python 代码中链式调用
- **丰富报告生成**：集成 Allure 报告,提供美观详细的测试报告
- **灵活配置管理**：支持环境配置、参数化和测试标记
- **数据驱动测试**：内置数据处理工具,支持多种数据源

## 配置与日志

### 环境变量

- `OMNITEST_ENV`：选择配置环境（如 `dev` / `test` / `prod`），对应加载 `config/{env}.yaml`
- `LOG_LEVEL`：动态控制日志级别（`DEBUG` / `INFO` / `WARNING` / `ERROR`），优先级高于配置文件
  - `LOG_LEVEL=DEBUG`：打印加载路径、重试细节与异常堆栈
  - `LOG_LEVEL=INFO`：仅打印真正发生加载动作的一行摘要（reload 会带 `[Reload]` 前缀）
  - `LOG_LEVEL>=WARNING`：仅在加载失败或配置校验不通过时输出
- 启用 logging.yaml（两种方式都支持）：
  - `LOG_CONFIG_PATH=/绝对路径/config/logging.yaml`
  - `OMNITEST_USE_LOGGING_YAML=1`（默认读取项目内置的 `config/logging.yaml`）

日志级别优先级（由高到低）：

- `LOG_LEVEL` 环境变量
- `config/{env}.yaml` 中的 `log.level`
- `logging.yaml` 中 logger/handler 的默认 level

### reload 用法

`ConfigManager` 支持运行时热更新配置（成功后替换缓存，失败回滚）：

```python
from config.config_manager import get_config_manager

cm = get_config_manager()
cm.reload()  # 使用当前 config_dir 重载
cm.reload("config")  # 指定目录重载（读取该目录下 default.yaml 与 {env}.yaml）
cm.reload("config/test.yaml")  # 指定文件重载（该文件视为环境配置文件）
```

### 日志模板示例

项目提供了示例配置 [logging.yaml](config/logging.yaml)，展示如何把
`config_alias/reload/module_name/lineno` 等字段注入到统一格式中。

## 项目结构

```text
OmniTest/
├── .trae/                  # Trae IDE 规则配置
├── cases/                  # 测试用例目录
│   ├── api/                # API 测试用例
│   ├── app/                # APP 测试用例
│   ├── performance/        # 性能测试用例
│   └── web/                # Web 测试用例
├── config/                 # 配置文件目录
├── data/                   # 测试数据与活动配置
├── scripts/                # 辅助脚本
├── tests/                  # 框架自身单元测试（离线基线等）
│   └── baseline/           # 离线基线测试
├── utils/                  # 核心工具类目录
│   ├── packaging/          # requirements 管理能力
│   ├── reporting/          # Allure 报告能力
│   └── runner/             # pytest/locust 执行器
├── .gitignore
├── PROJECT_OVERVIEW.md     # 项目全景文档
├── pyproject.toml          # PEP517 构建声明（与 setup.py 双轨）
├── README.md               # 项目主文档
├── conftest.py             # Pytest 全局配置
├── main.py                 # CLI 命令薄入口包装
├── omni_test.py            # 编程 API 统一入口
├── pytest.ini              # Pytest 配置文件
├── requirements.txt        # 依赖文件
├── run.py                  # CLI 核心运行器
└── setup.py                # 项目安装配置
```

## 安装配置

### 1. 环境要求

- Python 3.8 及以上
- 虚拟环境（推荐）
- 系统环境依赖：
  - Allure 命令行工具（用于报告生成）
  - WebDriver（用于 Web 测试）
  - Appium 服务（用于 APP 测试,可选）

### 2. 安装步骤

1. **克隆项目**

   ```bash
   git clone <项目地址>
   cd OmniTest
   ```

2. **创建虚拟环境**

   ```bash
   # 创建虚拟环境
   python3 -m venv .venv
   
   # 激活虚拟环境（MacOS/Linux）
   source .venv/bin/activate
   
   # 激活虚拟环境（Windows）
   .venv\Scripts\activate
   ```

3. **安装依赖**

   ```bash
   # 使用清华镜像源加速安装
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

4. **推荐：开发模式安装（可选）**

   ```bash
   pip install -e .
   ```

   - 说明：项目同时提供 `pyproject.toml`（PEP517 构建声明）与 `setup.py`（元信息/入口点），用于兼容可编辑安装。

5. **安装 Allure 命令行工具**

   - 参考 [Allure 官方文档](https://docs.qameta.io/allure/#_installing_a_commandline)
   - MacOS 可以使用 Homebrew: `brew install allure`
   - Windows 可以使用 Scoop: `scoop install allure`

## 使用指南

### 1. 命令行使用

OmniTest 提供了丰富的命令行接口,支持运行不同类型的测试。

如果已执行 `pip install -e .`，也可以直接使用入口命令：

```bash
omni-test --help
omni --help
```

#### 运行所有测试

```bash
python run.py all
```

#### 运行 API 测试

```bash
# 运行所有 API 测试
python run.py api

# 运行特定文件的 API 测试
python run.py api --file test_user_management.py

# 运行带标记的 API 测试
python run.py api --markers smoke
```

#### 运行 Web 测试

```bash
# 运行所有 Web 测试
python run.py web

# 运行特定目录的 Web 测试
python run.py web --dir auth

# 运行特定文件的 Web 测试
python run.py web --file test_login.py
```

#### 运行 APP 测试

```bash
# 运行所有 APP 测试
python run.py app

# 运行特定文件的 APP 测试
python run.py app --file test_android_app_launch.py

# 运行带标记的 APP 测试
python run.py app --markers smoke
```

#### 运行并行测试

```bash
# 运行并行测试（默认 2 个 worker）
python run.py parallel

# 运行指定数量的 worker
python run.py parallel --workers 3

# 运行并行测试并生成 HTML 报告
python run.py parallel --html

# 运行特定文件的并行测试
python run.py parallel --file test_app_login.py
```

#### 运行性能测试

```bash
# 运行性能测试
python run.py performance test_api_load.py \
  --users 200 \
  --spawn-rate 20 \
  --run-time 10m
```

#### 生成和查看报告

```bash
# 生成并打开报告
python run.py report

# 仅生成报告
python run.py report --generate

# 仅打开报告
python run.py report --open
```

#### 清理测试报告

```bash
python run.py clean
```

#### 包管理命令

```bash
# 更新 requirements.txt
python run.py package update-req

# 添加包到 requirements.txt
python run.py package add requests --version 2.31.0
```

### 2. 编程 API 使用

OmniTest 提供了简洁的编程 API,可以在 Python 代码中使用链式调用方式运行测试。

#### 基本用法

```python
from omni_test import ot

# 运行 API 测试
ot.api()

# 运行 Web 测试
ot.web()

# 运行所有测试并生成报告
ot.all()

# 链式调用
ot.clean().api().web().report()
```

### 编程 API 详细参考

#### OmniTest 类

`OmniTest` 类提供了以下方法：

##### `clean()`

清理测试报告目录。

```python
ot.clean()  # 清理报告目录
```

##### `api(test_dir=None, test_file=None, markers=None, auto_clean=True, auto_report=True)`

运行 API 测试。

参数：

- `test_dir`: 测试目录
- `test_file`: 测试文件
- `markers`: 测试标记
- `auto_clean`: 是否自动清理报告,默认为 True
- `auto_report`: 是否自动生成报告,默认为 True

说明：

- 当 `auto_report=True` 时，**测试失败也会生成报告**（用于定位失败原因）
- 仅当退出码为 `4`（测试目标无效）时跳过报告生成

返回：

- 返回实例本身以支持链式调用

```python
# 运行所有 API 测试
ot.api()

# 运行特定的 API 测试文件
ot.api(test_file="test_user.py")

# 运行带标记的 API 测试
ot.api(markers="smoke")

# 不自动清理报告
ot.api(auto_clean=False)

# 不自动生成报告
ot.api(auto_report=False)
```

##### `web(test_dir=None, test_file=None, markers=None, auto_clean=True, auto_report=True)`

运行 Web 测试。

参数与 `api()` 方法相同。

```python
# 运行所有 Web 测试
ot.web()

# 运行特定的 Web 测试文件
ot.web(test_file="test_login.py")

# 运行特定目录的 Web 测试
ot.web(test_dir="auth")
```

##### `app(test_dir=None, test_file=None, markers=None, auto_clean=True, auto_report=True)`

运行 App 测试。

参数与 `api()` 方法相同。

```python
# 运行所有 App 测试
ot.app()

# 运行带标记的 App 测试
ot.app(markers="smoke")
```

##### `performance(test_file, users=100, spawn_rate=10, run_time='5m')`

运行性能测试。

参数：

- `test_file`: 测试文件（必需）
- `users`: 用户数量,默认为 100
- `spawn_rate`: 每秒生成的用户数,默认为 10
- `run_time`: 运行时间,默认为 '5m'

返回：

- 返回实例本身以支持链式调用

```python
# 运行性能测试
ot.performance("test_api_load.py")

# 自定义性能测试参数
ot.performance("test_api_load.py", users=200, spawn_rate=20, run_time='10m')
```

##### `all(auto_clean=True, auto_report=True)`

运行所有类型的测试。

参数：

- `auto_clean`: 是否自动清理报告,默认为 True
- `auto_report`: 是否自动生成报告,默认为 True

返回：

- 返回实例本身以支持链式调用

```python
# 运行所有测试
ot.all()
```

##### `report(generate=True, open=True)`

生成和/或打开 Allure 报告。

参数：

- `generate`: 是否生成报告,默认为 True
- `open`: 是否打开报告,默认为 True

返回：

- 返回实例本身以支持链式调用

```python
# 生成并打开报告
ot.report()

# 只生成报告
ot.report(open=False)

# 只打开报告
ot.report(generate=False)
```

##### `parallel()`

运行并行测试（默认基于 `@pytest.mark.parallel` 标记）。

签名参考：

```python
parallel(
    test_dir=None,
    test_file=None,
    markers="parallel",
    num_workers=2,
    html_report=False,
    workers=None,
    html=None,
    auto_clean=True,
    auto_report=True,
)
```

参数：

- `markers`: 默认为 `parallel`
- `num_workers`: worker 数量（等价别名：`workers`）
- `html_report`: 是否生成 HTML 报告（等价别名：`html`）
- 其他参数与 `api()` 类似

```python
from omni_test import ot

# 默认并行（2 workers），执行 cases/ 下标记为 parallel 的用例
ot.parallel()

# 指定 workers，并生成 HTML 报告
ot.parallel(workers=3, html=True)
```

##### `last_exit_code / last_error`

链式调用仍返回 `self`，同时可通过以下属性获取最后一次执行结果：

- `last_exit_code`: 最近一次 run 的退出码（0=成功；4=目标无效；其他为失败）
- `last_error`: 最近一次异常对象（无异常则为 None）

### 链式调用进阶

OmniTest 支持链式调用,可以在一行代码中执行多个操作：

```python
# 链式调用示例
from omni_test import ot

# 运行 API 测试,然后运行 Web 测试,最后生成报告
ot.api()\
   .web()\
   .report()

# 运行特定的 API 测试,然后运行特定的 Web 测试,但不自动生成报告
ot.api(test_file="test_user.py", auto_report=False)\
   .web(test_file="test_login.py", auto_report=False)\
   .report()  # 手动生成报告
```

### 自定义流程控制

可以手动控制测试流程,而不依赖默认行为：

```python
from omni_test import OmniTest

omni_test = OmniTest()

# 1. 清理报告目录
omni_test.clean()

# 2. 运行 API 测试,但不自动清理和生成报告
omni_test.api(auto_clean=False, auto_report=False)

# 3. 运行 Web 测试,但不自动清理和生成报告
omni_test.web(auto_clean=False, auto_report=False)

# 4. 手动生成和打开一个包含所有测试的报告
omni_test.report()
```

## 示例代码

可参考以下已存在的示例/测试文件：

- 编程 API 行为与参数映射示例：[test_omni_test_programmatic_api.py](cases/api/test_omni_test_programmatic_api.py)
- 离线基线回归示例：[test_baseline.py](tests/baseline/test_baseline.py)

### 与命令行接口的关系

`main.py` 文件同时保留了命令行功能,当直接运行该文件时,会调用 `run.py` 中的 `main()` 函数,因此以下两种方式等效：

```bash
# 通过 run.py 运行
python run.py api

# 通过 main.py 运行
python main.py api
```

## 测试用例编写

### 1. API 测试

API 测试用例存放在 `cases/api/` 目录下,使用 pytest 框架编写。

示例：

```python
import pytest
import requests

class TestUserManagement:
    def test_create_user(self):
        # 编写 API 测试代码
        response = requests.post("/api/users", json={"name": "test"})
        assert response.status_code == 201
```

### 2. Web 测试

Web 测试用例存放在 `cases/web/` 目录下,推荐使用 Page Object 模式。

页面对象示例：`cases/web/pages/login_page.py`

```python
from selenium.webdriver.common.by import By
from utils.web.web_base_page import WebBasePage

class LoginPage(WebBasePage):
    USERNAME_INPUT = (By.ID, "username")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-btn")
    
    def login(self, username, password):
        self.input_text(self.USERNAME_INPUT, username)
        self.input_text(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)
```

测试用例示例：`cases/web/test_login.py`

```python
import pytest
from cases.web.pages.login_page import LoginPage

class TestLogin:
    def test_successful_login(self, browser):
        login_page = LoginPage(browser)
        login_page.navigate("https://example.com/login")
        login_page.login("test_user", "password123")
        assert login_page.is_logged_in()
```

### 3. APP 测试

APP 测试用例存放在 `cases/app/` 目录下,同样推荐使用 Page Object 模式。

#### 元素定位工具

APP 自动化测试中，元素定位可以使用以下工具：

1. **uiautomatorviewer**：Android SDK 自带的元素定位工具

   ```bash
   uiauto.dev
   ```

2. **weditor**：基于 Python 的 UI 查看器，支持 Android 和 iOS

   ```bash
   weditor
   ```

#### 测试前准备

在运行 APP 测试前，需要先启动 Appium 服务：

```bash
appium --address 127.0.0.1 --port 4723 --log-level info
```

确保 Appium 服务正常运行后，再执行测试用例。

### 4. 性能测试

性能测试用例存放在 `cases/performance/` 目录下,使用 Locust 框架编写。

### 5. 并行测试

并行测试是一种提高测试执行效率的方法，适用于大规模测试场景。在 OmniTest 中，您可以通过以下方式运行并行测试：

1. 在测试用例上添加 `@pytest.mark.parallel` 标记
2. 使用 `python run.py parallel` 命令运行

并行测试会自动分配测试用例到多个 worker 进程中执行，显著减少测试执行时间。

## 配置管理

OmniTest 提供了灵活强大的配置管理系统,支持 YAML 配置文件、环境变量和属性化访问,配置文件位于 `config/` 目录下：

- `default.yaml`：默认配置文件,包含所有环境共享的基础配置
- `test.yaml`：测试环境的 YAML 格式配置文件
- `prod.yaml`：生产环境的 YAML 格式配置文件
- `config_manager.py`：配置管理器核心实现
- `__init__.py`：配置模块初始化文件

### 配置系统核心组件

#### ConfigManager 类

ConfigManager 是配置系统的核心类,负责加载、解析和管理配置：

- 自动加载默认配置和环境特定配置
- 支持环境变量覆盖配置值
- 提供属性化访问（点号访问）配置的能力
- 配置缓存和实时更新机制
- 支持多种数据库和服务的配置管理

#### ConfigDict 类

ConfigDict 是一个特殊的字典类,用于实现配置的属性化访问：

- 支持通过点号（`.`）访问嵌套配置项
- 保持与字典接口的兼容性
- 自动将嵌套字典转换为 ConfigDict 对象
- 提供配置值的类型转换和默认值支持

### YAML 配置文件结构

配置文件使用 YAML 格式,支持多层嵌套：

```yaml
# 日志配置
log:
  dir: ./logs
  level: INFO
  rotation: daily

# 报告配置
report:
  dir: ./reports
  format: html
  auto_open: true

# 超时配置
timeout:
  page_load: 30
  implicitly_wait: 10
  command: 5

# 重试配置
retry:
  default_count: 3
  interval: 2

# 截图配置
screenshot:
  dir: ./screenshots
  format: png

# 数据库配置
mysql:
  default:
    host: localhost
    port: 3306
    user: test_user
    password: test_password
    database: test_db

# Redis配置
redis:
  default:
    host: localhost
    port: 6379
    password:
    db: 0
```

### 使用配置系统

#### 导入配置实例

```python
# 从配置管理器导入全局配置实例
from config.config_manager import config
```

#### 访问配置项

可以通过点号访问或字典方式访问配置项：

```python
# 属性化访问（推荐）
log_level = config.log.level
page_timeout = config.timeout.page_load
mysql_host = config.mysql.default.host

# 字典方式访问
log_level = config['log']['level']
page_timeout = config['timeout']['page_load']
```

#### 环境变量使用

环境变量可以覆盖 YAML 配置文件中的值,支持以下格式：

- 顶级配置：`SECTION_KEY`
- 嵌套配置：`SECTION__KEY`（双下划线表示嵌套）

例如,要覆盖 MySQL 主机配置：

```bash
# 设置环境变量
export MYSQL_HOST=test-db.example.com

# 在 Python 中可以直接访问更新后的值
print(config.mysql.default.host)  # 输出: test-db.example.com
```

#### 动态更新配置

```python
# 动态更新配置值
config.update_config({'timeout': {'page_load': 60}})

# 或直接设置属性
config.timeout.page_load = 60
```

### 配置优先级

配置优先级从高到低：

1. 运行时通过 `update_config()` 方法设置的值
2. 直接通过属性赋值修改的值
3. 环境变量（格式：SECTION_KEY 或 SECTION__KEY）
4. 环境特定配置文件（如 test.yaml）中的值
5. 默认配置文件（default.yaml）中的值

### 最佳实践

1. **统一访问模式**：优先使用属性化访问（`config.section.key`）而非字典访问
2. **配置分组**：将相关配置组织在同一个部分下,提高可读性
3. **默认值处理**：为可能缺失的配置项提供合理的默认值
4. **敏感信息**：避免在配置文件中硬编码密码等敏感信息,使用环境变量
5. **配置验证**：在应用启动时验证关键配置项是否存在和有效
6. **路径配置**：使用相对路径时,系统会自动转换为绝对路径

### 配置辅助方法

ConfigManager 提供了专门的方法来获取常用服务的配置：

```python
# 获取 MySQL 配置
mysql_config = config.get_mysql_config()

# 获取 Redis 配置
redis_config = config.get_redis_config()

# 获取 SSH 配置
ssh_config = config.get_ssh_config()
```

## 测试数据格式

OmniTest 支持多种测试数据格式,包括 JSON 和 YAML,测试数据文件位于 `data/test_data/` 目录下。

### YAML 测试数据

YAML 格式的测试数据提供了更易读的结构,适合复杂的嵌套测试数据。

#### 数据文件示例 (api_test_data.yaml)

```yaml
# API测试数据 - YAML格式
test_user_registration:
  valid_data:
    username: testuser123
    email: testuser123@example.com
    password: Test@123456
  invalid_data:
    missing_username:
      email: testuser123@example.com
      password: Test@123456
  expected:
    status_code: 201
```

#### 加载 YAML 测试数据

```python
from utils.file_util import FileHandler

test_data = FileHandler.get_test_data("test_data/api_test_data.yaml")
valid_data = test_data["test_user_registration"]["valid_data"]
```

## 测试报告

OmniTest 使用 Allure 生成测试报告,报告包含：

- 测试结果概览
- 详细的测试步骤
- 失败测试的截图和日志
- 测试执行时间统计
- 图表可视化

报告默认生成在 `reports/<YYYYMMDD_HHMM>/allure-report/` 目录下（按每次执行的时间文件夹隔离）。

## 常见问题

### 1. 报告生成失败

确保已正确安装 Allure 命令行工具,并将其添加到系统环境变量中。

### 2. Web 测试浏览器问题

- 确保已下载对应浏览器版本的 WebDriver
- 或将 WebDriver 路径配置到环境变量中
- 或使用 webdriver-manager 自动管理

### 3. APP 测试连接问题

确保已启动 Appium 服务,并且设备连接正常。

## 项目维护

### 更新依赖

```bash
# 手动更新依赖
pip install --upgrade -r requirements.txt

# 使用命令行工具更新 requirements.txt
python run.py package update-req
```

### 运行代码检查

```bash
# 运行 flake8 检查
flake8 .

# 运行 black 格式化
black .
```

### 添加新依赖

```bash
# 使用命令行工具添加新依赖
python run.py package add requests --version 2.31.0
```

## 贡献指南

欢迎贡献代码和提出建议！请遵循以下规范：

1. Fork 项目仓库
2. 创建功能分支
3. 提交代码
4. 运行测试确保通过
5. 提交 Pull Request

## 许可证

[MIT License](LICENSE)

## 联系方式

作者：duanyang

---

## 变更日志

### 2026-03-24（v1.0.0）

- 拆分 `run.py`：核心执行/报告/依赖管理分别迁移到 `utils/runner`、`utils/reporting`、`utils/packaging`
- 强化编程 API：新增 `parallel()`、对齐 CLI 报告策略（失败也生成报告，目标无效退出码 4 例外）、增加 `last_exit_code/last_error`
- 并行默认目录调整：默认在全 `cases/` 目录按 `@pytest.mark.parallel` 执行
- 引入 `pyproject.toml`：启用 PEP517 构建声明，保留 `setup.py` 双轨以便回滚
- 新增离线基线测试：覆盖导入与关键接口契约，便于稳定回归
