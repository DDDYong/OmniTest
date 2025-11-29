# OmniTest 框架 API 使用指南

本文档介绍如何通过 Python 代码直接使用 OmniTest 框架运行测试,而不仅限于命令行。

## 快速开始

### 基本用法

通过 Python 代码导入并使用 OmniTest 框架：

```python
from omni_test import ot

# 运行 API 测试
ot.api()

# 运行 Web 测试
ot.web()

# 运行 App 测试
ot.app()

# 生成并打开报告
ot.report()
```

### 创建新实例

也可以创建一个新的 OmniTest 实例：

```python
from omni_test import OmniTest

# 创建新实例
omni_test = OmniTest()

# 运行 API 测试
omni_test.api()
```

## API 参考

### OmniTest 类

`OmniTest` 类提供了以下方法：

#### `clean()`

清理测试报告目录。

```python
ot.clean()  # 清理报告目录
```

#### `api(test_dir=None, test_file=None, markers=None, auto_clean=True, auto_report=True)`

运行 API 测试。

参数：

- `test_dir`: 测试目录
- `test_file`: 测试文件
- `markers`: 测试标记
- `auto_clean`: 是否自动清理报告,默认为 True
- `auto_report`: 是否自动生成报告,默认为 True

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

#### `web(test_dir=None, test_file=None, markers=None, auto_clean=True, auto_report=True)`

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

#### `app(test_dir=None, test_file=None, markers=None, auto_clean=True, auto_report=True)`

运行 App 测试。

参数与 `api()` 方法相同。

```python
# 运行所有 App 测试
ot.app()

# 运行带标记的 App 测试
ot.app(markers="smoke")
```

#### `performance(test_file, users=100, spawn_rate=10, run_time='5m')`

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

#### `all(auto_clean=True, auto_report=True)`

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

#### `report(generate=True, open=True)`

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

## 链式调用

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

## 自定义流程控制

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

详细的使用示例请查看 `examples/usage_example.py` 文件。

```bash
python examples/usage_example.py
```

## 与命令行接口的关系

`main.py` 文件同时保留了命令行功能,当直接运行该文件时,会调用 `run.py` 中的 `main()` 函数,因此以下两种方式等效：

```bash
# 通过 run.py 运行
python run.py api

# 通过 main.py 运行
python main.py api
```

## 注意事项

1. 确保 Python 版本兼容项目要求
2. 运行 App 测试前,请确保已正确配置 Appium
3. 运行性能测试前,请确保已安装 Locust
4. 生成和查看 Allure 报告前,请确保已安装 Allure 命令行工具