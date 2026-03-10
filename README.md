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

## 项目结构

```
OmniTest/
├── .gitignore              # Git 忽略文件
├── README_API.md           # API 文档
├── activate_existing_venv.sh # 激活虚拟环境脚本
├── cases/                  # 测试用例目录
│   ├── api/                # API 测试用例
│   │   └── test_user_management.py
│   ├── app/                # APP 测试用例
│   │   ├── pages/          # APP 页面对象
│   │   └── test_android_app_launch.py
│   ├── performance/        # 性能测试用例
│   └── web/                # Web 测试用例
│       ├── pages/          # Web 页面对象
│       └── test_baidu_search.py
├── config/                 # 配置文件目录
│   ├── config.py           # 配置文件
│   └── env.py              # 环境配置
├── conftest.py             # Pytest 配置文件
├── data/                   # 测试数据目录
│   ├── templates/          # 数据模板
│   └── test_data/          # 测试数据文件
├── examples/               # 使用示例
│   └── usage_example.py    # 示例代码
├── hooks/                  # 测试钩子
├── main.py                 # 主入口文件
├── omni_test.py            # OmniTest API 模块
├── pytest.ini              # Pytest 配置
├── requirements.txt        # 依赖文件
├── run.py                  # 运行测试的核心模块
└── utils/                  # 工具类目录
    ├── api/                # API 测试工具
    ├── app/                # APP 测试工具
    ├── db/                 # 数据库工具
    ├── performance/        # 性能测试工具
    └── web/                # Web 测试工具
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

4. **安装 Allure 命令行工具**

    - 参考 [Allure 官方文档](https://docs.qameta.io/allure/#_installing_a_commandline)
    - MacOS 可以使用 Homebrew: `brew install allure`
    - Windows 可以使用 Scoop: `scoop install allure`

## 使用指南

### 1. 命令行使用

OmniTest 提供了丰富的命令行接口,支持运行不同类型的测试。

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
python run.py performance test_api_load.py --users 200 --spawn-rate 20 --run-time 10m
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

# 运行所有测试并生成报告
ot.all()

# 链式调用
ot.clean().api().web().report()
```

#### 高级用法

```python
from omni_test import ot

# 运行特定的 API 测试文件
ot.api(test_file="test_user_management.py")

# 运行带标记的 Web 测试,不自动清理和报告
ot.web(markers="smoke", auto_clean=False, auto_report=False)

# 运行性能测试
ot.performance("test_api_load.py", users=200, spawn_rate=20, run_time="10m")

# 生成报告但不打开
ot.report(open=False)

# 运行并行测试
ot.parallel(workers = 3, html = True)
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
# 从配置模块导入全局配置实例
from config import config
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
# API 测试数据
test_user_registration:
  test_data:
    username: testuser123
    email: test@example.com
    password: Password123
  expected_result:
    status_code: 201
    response_message: User registered successfully

# 测试场景列表
test_scenarios:
  - name: valid_registration
    description: 有效的用户注册测试
    test_data:
      username: valid_user
      password: SecurePass123
    expected:
      success: true
      user_id: >0
```

#### 加载 YAML 测试数据

```python
import yaml

def load_test_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 使用测试数据
test_data = load_test_data('data/test_data/api_test_data.yaml')

# 获取特定测试场景的数据
scenario_data = test_data['test_scenarios'][0]
```

## 测试报告

OmniTest 使用 Allure 生成测试报告,报告包含：

- 测试结果概览
- 详细的测试步骤
- 失败测试的截图和日志
- 测试执行时间统计
- 图表可视化

报告默认生成在 `reports/allure-report/` 目录下。

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

**版本：v1.2.0**
**更新日期：2026/03/10**

### 更新日志

- 重构配置系统,实现 ConfigManager 和 ConfigDict 核心类
- 新增 default.yaml 作为基础配置文件
- 实现配置的属性化访问（点号访问）功能
- 优化配置加载逻辑,支持环境变量覆盖配置
- 添加配置缓存和实时更新机制
- 支持多层嵌套配置的无缝访问
- 改进数据库和Redis配置结构,支持多实例配置
- 提供配置系统的完整测试用例
- 新增并行测试功能,支持多进程并行执行测试
- 新增包管理命令,支持更新和添加依赖
- 优化报告生成机制,使用时间文件夹管理报告
- 改进命令行接口,支持更多参数和选项
- 增强配置系统的健壮性和灵活性