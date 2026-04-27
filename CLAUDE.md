# CLAUDE.md

本文档用于指导 Claude Code 在本仓库中工作。

## 基本沟通规则

- 默认使用中文回答，除非用户明确要求使用其他语言。
- 每次回答用户时称呼用户为“宝宝”。
- 用户的系统环境是 macOS，主要角色是软件测试工程师，主要编程语言是 Python。
- 如果需求不明确，先提出澄清问题，不要直接改代码。
- 在编写或修改代码前，先简要说明方案；涉及较大改动时需等待用户确认。
- 如果任务预计需要修改超过 3 个文件，先暂停并拆分为更小的任务。
- 每次用户纠正行为或规则后，应将新规则同步到 `CLAUDE.md`，除非用户明确不要修改。

## 工作方式

- 优先做最小、聚焦、可验证的改动。
- 优先修复根因，避免只做表面补丁。
- 不要修改与当前任务无关的文件、公共接口或目录结构。
- 不要顺手重构无关模块。
- 保持回答简洁、直接，代码风格与项目现有实现一致。
- 不要手动修改运行产物、测试报告或缓存目录。

## 项目概览

OmniTest 是一个 Python 自动化测试框架，支持：

- API 自动化测试
- Web UI 自动化测试
- App UI 自动化测试
- 性能测试

项目同时提供：

- 命令行入口：`run.py` / `main.py`
- 链式编程 API：`omni_test.py`

## 重要目录和文件

- `run.py`：主要 CLI 调度入口，同时承担向后兼容职责
- `main.py`：轻量入口
- `omni_test.py`：链式 API 门面
- `config/`：YAML 配置与配置管理
- `cases/api/`：API 测试用例
- `cases/web/`：基于 Selenium 的 Web 测试用例
- `cases/app/`：基于 Appium 的 App 测试用例
- `cases/performance/`：基于 Locust 的性能测试
- `utils/runner/`：核心测试执行逻辑
- `utils/reporting/`：Allure 报告生成逻辑
- `utils/path/path_util.py`：路径管理单一事实来源
- `tests/baseline/`：核心接口和导入契约的离线基线测试

## 架构规则

执行流程：

1. `run.py` 解析命令行参数并生成执行请求
2. 请求被分发到 runner / reporting 相关工具
3. 通过子进程运行 pytest 或 locust
4. 测试报告写入 `reports/` 下的时间戳目录

关键约束：

- `run.py` 应保持为兼容层，核心执行逻辑优先放在 `utils/runner/test_runner.py`
- `omni_test.py` 负责链式 API、执行请求封装和报告编排
- `PathUtil` 是运行路径、报告路径等路径逻辑的单一事实来源
- 无效测试目标时应返回退出码 `4`，并跳过报告生成

## 退出码规则

- `0`：测试成功
- `4`：无效测试目标，跳过报告生成
- 其他非零值：执行失败或测试失败，通常仍可生成报告

## 配置规则

配置优先级从高到低：

1. 运行时更新
2. 环境变量
3. `config/{OMNITEST_ENV}.yaml`
4. `config/default.yaml`

常见环境变量：

- `OMNITEST_ENV`
- `LOG_LEVEL`
- `LOG_CONFIG_PATH`
- `OMNITEST_USE_LOGGING_YAML`

修改配置系统时：

- 保持现有配置合并顺序
- 不破坏懒加载单例访问方式
- 保持 reload 失败回滚行为
- 尽量保持向后兼容

## 编码规则

- 新增能力前，优先复用 `utils/` 下已有工具。
- 不要无必要引入新的第三方依赖。
- 保持现有方法名、参数和链式 API 行为，除非任务明确要求改变。
- 日志风格应与项目共享 logger 保持一致。
- 注释要少而有用，不解释显而易见的代码。

## 测试规则

修改以下核心文件后，优先运行基线测试：

- `run.py`
- `omni_test.py`
- `config/config_manager.py`
- `utils/path/path_util.py`
- `utils/runner/test_runner.py`

基线测试命令：

```bash
pytest tests/baseline/test_baseline.py -v
```

修复 bug 时：

- 优先新增或更新一个能复现问题的测试
- 再用最小改动修复问题
- 持续验证直到相关测试通过

代码修改完成后，应说明：

- 可能出现的问题
- 建议补充的测试用例
- 已执行的验证命令

## 常用命令

```bash
# 创建并启用虚拟环境
python3 -m venv .venv && source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 可编辑安装，启用 omni-test / omni 命令
pip install -e .

# 运行基线测试
pytest tests/baseline/test_baseline.py -v

# 带覆盖率运行基线测试
pytest tests/baseline/ --cov=. --cov-report=term-missing

# CLI 示例
python run.py api
python run.py web
python run.py app
python run.py report
python run.py clean
```

## 避免无必要修改

- `.venv/`
- `venv`
- `reports/`
- `htmlcov/`
- `.pytest_cache/`
- `logs/`

## 交付要求

完成任务时，需要说明：

- 修改了哪些文件
- 为什么这样改
- 执行了哪些验证
- 是否存在风险、假设或后续建议
