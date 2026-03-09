# 编辑器运行配置指南

## 📋 概述

本指南详细说明如何在编辑器（PyCharm/IntelliJ IDEA）工具栏中配置和运行测试组件，替代命令行运行方式。

---

## 🛠️ 一、PyCharm/IntelliJ IDEA 配置

### 1.1 项目配置准备

#### 1.1.1 确认Python解释器

1. 打开 `File` → `Settings` (macOS: `PyCharm` → `Settings`)
2. 导航到 `Project: OmniTest` → `Python Interpreter`
3. 确认已选择正确的虚拟环境解释器
4. 如果没有，点击齿轮图标 → `Add` → 选择项目的虚拟环境

#### 1.1.2 配置项目结构

1. 打开 `File` → `Settings` → `Project: OmniTest` → `Project Structure`
2. 确保项目根目录已标记为 `Sources`（蓝色文件夹图标）
3. 点击 `OK` 保存

---

### 1.2 创建Appium服务启动配置

#### 1.2.1 Shell Script配置（启动Appium服务）

1. 点击右上角的 `Add Configuration...`（或 `Edit Configurations...`）
2. 点击左上角的 `+` 号
3. 选择 `Shell Script`
4. 配置如下：
    - **Name**: `Start Appium Servers`
    - **Script path**: 选择 `/Users/apple/duanyang/PyProduct/OmniTest/scripts/start_appium_servers.sh`
    - **Working directory**: `/Users/apple/duanyang/PyProduct/OmniTest`
    - **Execute in terminal**: ✅ 勾选（重要）
5. 点击 `OK` 保存

#### 1.2.2 验证Shell脚本执行权限

```bash
cd /Users/apple/duanyang/PyProduct/OmniTest/scripts
chmod +x start_appium_servers.sh
chmod +x start_parallel_env.sh
```

---

### 1.3 创建并行测试运行配置（灵活配置方案）

#### 1.3.1 方案一：按标记运行（最推荐，适用于所有新增测试）

**优点**：新增测试文件只需加 `@pytest.mark.parallel` 标记，无需新增配置！

1. 点击右上角的 `Add Configuration...`
2. 点击 `+` 号，选择 `Python tests` → `pytest`
3. 配置如下：

**基础配置：**

- **Name**: `All Parallel Tests (2 Workers)`
- **Target**: 选择 `Custom`（重要！不是 Script path）
- **Python interpreter**: 选择你的虚拟环境
- **Working directory**: `/Users/apple/duanyang/PyProduct/OmniTest`
- **Additional Arguments**: `-m parallel -n 2 -v`

**说明**：

- `-m parallel` 会运行所有标记了 `@pytest.mark.parallel` 的测试
- 无论新增多少测试文件，只要加了标记，都会被运行！

4. 点击 `OK` 保存

---

#### 1.3.2 方案二：按目录运行（适用于运行某个目录下的所有测试）

**优点**：可以灵活选择运行某个目录下的所有测试

**配置示例1：运行所有APP测试**

- **Name**: `All App Tests (2 Workers)`
- **Target**: 选择 `Script path`，填写：`cases/app`
- **Additional Arguments**: `-n 2 -v`

**配置示例2：运行所有API测试**

- **Name**: `All API Tests`
- **Target**: 选择 `Script path`，填写：`cases/api`
- **Additional Arguments**: `-v`

---

#### 1.3.3 方案三：按模块运行（适用于特定测试文件）

**优点**：针对特定文件进行调试

**配置示例**：

- **Name**: `Login Parallel Tests (2 Workers)`
- **Target**: 选择 `Script path`，填写：`cases/app/test_app_login_parallel_simple.py`
- **Additional Arguments**: `-m parallel -n 2 -v`

---

#### 1.3.4 方案四：按表达式运行（最高灵活性）

**优点**：可以使用复杂的pytest表达式筛选测试

**配置示例1：运行所有冒烟测试**

- **Name**: `All Smoke Tests`
- **Target**: `Custom`
- **Additional Arguments**: `-m smoke -v`

**配置示例2：运行APP冒烟测试**

- **Name**: `App Smoke Tests (2 Workers)`
- **Target**: `Custom`
- **Additional Arguments**: `-m "app and smoke" -n 2 -v`

**配置示例3：排除某个测试**

- **Name**: `Parallel Tests (no invalid)`
- **Target**: `Custom`
- **Additional Arguments**: `-m "parallel and not invalid" -n 2 -v`

---

#### 1.3.5 推荐配置组合

建议创建以下几个配置，覆盖99%使用场景：

| 配置名称 | Target类型 | Target值 | Additional Arguments | 用途 |
|---------|-----------|---------|-------------------|------|
| All Parallel Tests (2 Workers) | Custom | - | `-m parallel -n 2 -v` | 日常并行测试（最常用）✅ |
| All Parallel Tests (3 Workers) | Custom | - | `-m parallel -n 3 -v` | 更多设备并行 |
| All App Tests | Script path | `cases/app` | `-n 2 -v` | 运行所有APP测试 |
| All Smoke Tests | Custom | - | `-m smoke -v` | 冒烟测试 |
| Login Parallel Tests (Debug) | Script path | `cases/app/test_app_login_parallel_simple.py` | `-m parallel -n 1 -v` | 调试特定文件 |

---

#### 1.3.6 创建不同Worker数量的配置

为方便使用，可以复制基础配置，修改Worker数量：

**配置1：2个Worker（推荐）**

- Name: `All Parallel Tests (2 Workers)`
- Additional Arguments: `-m parallel -n 2 -v`

**配置2：3个Worker**

- Name: `All Parallel Tests (3 Workers)`
- Additional Arguments: `-m parallel -n 3 -v`

**配置3：单Worker（调试用）**

- Name: `All Parallel Tests (1 Worker - Debug)`
- Additional Arguments: `-m parallel -n 1 -v`

---

### 1.4 创建带HTML报告的测试配置

1. 复制上面的 `All Parallel Tests (2 Workers)` 配置
2. 修改名称为：`All Parallel Tests (with HTML Report)`
3. 修改 `Additional Arguments` 为：
   ```
   -m parallel -n 2 -v --html=logs/report.html --self-contained-html
   ```
4. 点击 `OK` 保存

---

### 1.5 创建Allure报告配置

#### 1.5.1 生成Allure结果的测试配置

1. 新建pytest配置：
    - **Name**: `All Parallel Tests (Allure)`
    - **Target**: `Custom`
    - **Additional Arguments**: `-m parallel -n 2 -v --alluredir=reports/allure-results --clean-alluredir`
2. 保存配置

#### 1.5.2 创建Allure报告查看配置

1. 点击 `+` 号，选择 `Shell Script`
2. 配置：
    - **Name**: `View Allure Report`
    - **Script text**:
      ```bash
      cd /Users/apple/duanyang/PyProduct/OmniTest
      allure serve reports/allure-results
      ```
    - **Working directory**: `/Users/apple/duanyang/PyProduct/OmniTest`
    - **Execute in terminal**: ✅ 勾选
3. 保存配置

---

### 1.6 复合配置（一键启动+测试）

#### 1.6.1 使用Before Launch功能

1. 编辑 `All Parallel Tests (2 Workers)` 配置
2. 在 `Before launch` 区域点击 `+`
3. 选择 `Run Another Configuration`
4. 选择 `Start Appium Servers`
5. 勾选 `Open the run/debug tool window`
6. 点击 `OK` 保存

⚠️ **注意**：由于Appium服务需要持续运行，不建议直接在测试前自动启动，建议：

- 先手动运行 `Start Appium Servers`
- 等待服务启动完成
- 再运行测试配置

---

## 🎯 二、快速使用指南

### 2.1 日常测试流程

1. **启动Appium服务**
    - 选择 `Start Appium Servers` 配置
    - 点击运行按钮（绿色三角形）
    - 等待看到 "Appium server started" 消息

2. **运行并行测试**
    - 选择 `All Parallel Tests (2 Workers)` 配置（最常用！）
    - 点击运行按钮
    - 查看测试结果

3. **查看报告**（如果使用了HTML报告配置）
    - 在项目视图中找到 `logs/report.html`
    - 右键 → `Open in` → `Browser` → 选择浏览器

---

### 2.2 新增测试文件后的使用

**不需要新增配置！** 只需在新测试文件中添加标记：

```python
import pytest


@pytest.mark.app
@pytest.mark.parallel  # 必须添加这个标记！
class TestYourNewFeature:

    @pytest.mark.smoke
    def test_something(self, parallel_appium_driver):
        # 你的测试代码
        pass
```

然后直接运行 `All Parallel Tests (2 Workers)` 配置，新测试会自动被包含！


---

### 2.3 工具栏快捷方式

#### 2.3.1 添加配置到收藏

1. 点击运行配置下拉框
2. 点击星形图标（⭐）将常用配置添加到收藏
3. 这样可以快速切换常用配置

#### 2.3.2 创建运行分组

1. 打开 `Edit Configurations...`
2. 点击左上角的文件夹图标（Create folder）
3. 命名为 `Parallel Tests`
4. 将所有并行测试相关配置拖入该文件夹
5. 点击 `OK` 保存

---

## 🔧 三、常见问题解决

### 3.1 pytest配置无法识别

**问题**：运行配置时提示 "No pytest runner found"

**解决方法**：

1. 打开 `File` → `Settings` → `Tools` → `Python Integrated Tools`
2. 在 `Testing` 区域，将 `Default test runner` 设置为 `pytest`
3. 点击 `OK` 保存

### 3.2 ModuleNotFoundError

**问题**：运行测试时提示找不到模块

**解决方法**：

1. 确认项目根目录已标记为 Sources Root
2. 右键点击项目根目录 → `Mark Directory as` → `Sources Root`
3. 重新运行测试

### 3.3 端口被占用

**问题**：Appium服务启动失败，提示端口已被占用

**解决方法**：

1. 打开终端，运行：
   ```bash
   lsof -ti :4723 | xargs kill -9 2>/dev/null
   lsof -ti :4724 | xargs kill -9 2>/dev/null
   ```
2. 重新启动Appium服务

### 3.4 测试运行但没有输出

**问题**：点击运行后没有任何输出

**解决方法**：

1. 编辑运行配置
2. 点击 `Modify options`
3. 勾选 `Emulate terminal in output console`
4. 重新运行

---

## 📱 四、调试配置

### 4.1 创建调试配置

1. 复制现有的测试运行配置
2. 修改名称为：`Debug Parallel App Login Tests`
3. （可选）将Worker数量改为1，便于调试：
    - Additional Arguments: `-m parallel -n 1 -v`
4. 点击调试按钮（虫子图标）开始调试

### 4.2 断点设置

1. 在代码中点击行号左侧设置断点
2. 启动调试配置
3. 测试执行到断点时会暂停
4. 使用调试工具栏控制执行流程

---

## 🎨 五、界面优化建议

### 5.1 自定义工具栏

1. 右键点击工具栏空白处
2. 选择 `Customize Menus and Toolbars`
3. 导航到 `Main Toolbar`
4. 点击 `+` 添加常用操作
5. 点击 `OK` 保存

### 5.2 快捷键配置

1. 打开 `File` → `Settings` → `Keymap`
2. 搜索 `pytest`
3. 为常用操作设置快捷键，例如：
    - 运行测试：`Ctrl+Shift+F10`
    - 调试测试：`Ctrl+Shift+F9`

---

## 📊 六、运行结果查看

### 6.1 测试结果面板

- 绿色 ✅：通过
- 红色 ❌：失败
- 黄色 ⚠️：跳过
- 蓝色 ℹ️：信息

### 6.2 日志查看

1. 点击底部的 `Run` 标签
2. 查看控制台输出
3. 可以使用过滤器查找特定内容

---

## ✅ 七、配置检查清单

在开始使用前，请确认：

- [ ] Python解释器已正确配置
- [ ] 项目根目录已标记为Sources Root
- [ ] Shell脚本有执行权限
- [ ] pytest已设置为默认测试运行器
- [ ] 已创建至少一个测试运行配置
- [ ] 已创建Appium服务启动配置
- [ ] 虚拟环境已激活
- [ ] 所有依赖已安装

---

---

## 🔌 九、与 run.py 结合使用

项目中已有一个功能强大的 `run.py` 测试运行器，它提供了统一的命令行接口来运行各类测试。我们可以在编辑器中配置使用 `run.py`
来运行并行测试！

### 9.1 run.py 并行测试功能概述

`run.py` 已添加 `parallel` 子命令，支持：

| 参数 | 说明 | 默认值 |
|-----|------|-------|
| `--dir` | 指定测试目录 | - |
| `--file` | 指定测试文件 | - |
| `--markers` | 测试标记 | `parallel` |
| `--workers, -n` | Worker数量 | `2` |
| `--html` | 生成HTML报告 | `False` |

### 9.2 配置使用 run.py 的运行配置

#### 9.2.1 基础配置（使用run.py运行并行测试）

1. 点击右上角的 `Add Configuration...`
2. 点击 `+` 号，选择 `Python`（注意：不是 pytest！）
3. 配置如下：

**基础配置：**

- **Name**: `Run Parallel Tests (run.py)`
- **Script path**: 选择项目根目录下的 `run.py`
- **Parameters**: `parallel`
- **Python interpreter**: 选择你的虚拟环境
- **Working directory**: `/Users/apple/duanyang/PyProduct/OmniTest`

4. 点击 `OK` 保存

#### 9.2.2 多种Worker数量配置

**配置1：2个Worker（默认）**

- Name: `Run Parallel Tests (2 workers)`
- Parameters: `parallel`

**配置2：3个Worker**

- Name: `Run Parallel Tests (3 workers)`
- Parameters: `parallel --workers 3`

**配置3：单Worker（调试）**

- Name: `Run Parallel Tests (1 worker - Debug)`
- Parameters: `parallel --workers 1`

**配置4：带HTML报告**

- Name: `Run Parallel Tests (with HTML report)`
- Parameters: `parallel --html`

#### 9.2.3 高级配置（指定标记/文件/目录）

**指定标记运行**

- Name: `Run Parallel Smoke Tests`
- Parameters: `parallel --markers "parallel and smoke"`

**指定文件运行**

- Name: `Run Login Parallel Tests`
- Parameters: `parallel --file test_app_login_parallel_simple.py`

**指定目录运行**

- Name: `Run All App Parallel Tests`
- Parameters: `parallel --dir cases/app`

### 9.3 run.py 的其他有用命令

除了并行测试，`run.py` 还提供了其他有用的命令，可以在编辑器中配置：

| 命令 | 说明 | 配置示例 |
|-----|------|---------|
| `api` | 运行API测试 | Parameters: `api --markers smoke` |
| `web` | 运行Web测试 | Parameters: `web` |
| `app` | 运行APP测试 | Parameters: `app` |
| `all` | 运行所有测试 | Parameters: `all` |
| `report` | 生成并打开Allure报告 | Parameters: `report` |
| `clean` | 清理测试报告 | Parameters: `clean` |

### 9.4 推荐的 run.py 配置组合

建议创建以下配置，覆盖常用场景：

| 配置名称 | Parameters | 用途 |
|---------|-----------|------|
| `Run Parallel Tests` | `parallel` | 日常并行测试 ✅ |
| `Run Parallel Tests (3 workers)` | `parallel --workers 3` | 更多设备并行 |
| `Run Parallel Tests (HTML)` | `parallel --html` | 带HTML报告 |
| `Run All App Tests` | `app` | 所有APP测试 |
| `Generate Allure Report` | `report` | 生成报告 |
| `Clean Reports` | `clean` | 清理报告 |

### 9.5 使用 run.py 的优势

使用 `run.py` 相比直接使用 pytest 的优势：

1. **统一接口**：所有测试类型使用同一套命令格式
2. **自动清理**：自动清理旧报告
3. **自动生成报告**：测试通过后自动生成Allure报告
4. **参数友好**：更简洁的命令行参数
5. **可扩展性**：方便添加新的测试类型和功能

### 9.6 快速开始（使用 run.py）

1. **启动Appium服务**
    - 选择 `Start Appium Servers` 配置
    - 点击运行

2. **运行并行测试**
    - 选择 `Run Parallel Tests` 配置
    - 点击运行
    - 查看测试结果

3. **查看Allure报告**
    - 选择 `Generate Allure Report` 配置
    - 点击运行
    - 或使用命令：`allure serve reports/allure-results`

---

## 📚 十、参考文档

- [PyCharm官方文档：测试](https://www.jetbrains.com/help/pycharm/testing.html)
- [pytest官方文档](https://docs.pytest.org/)
- [pytest-xdist文档](https://pypi.org/project/pytest-xdist/)
- [项目run.py脚本](../run.py) - 查看完整的命令行接口
