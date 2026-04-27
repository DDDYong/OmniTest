# AGENTS.md

## 作用范围

本文件适用于整个仓库。若子目录下存在更深层级的 `AGENTS.md`，则以更深层级文件为准。

## 基本沟通规则

- 默认使用中文回答，除非用户明确要求使用其他语言。
- 每次回答用户时称呼用户为“宝宝”。
- 用户的系统环境是 macOS，主要角色是软件测试工程师，主要编程语言是 Python。
- 如果需求不明确，先提出澄清问题，不要直接修改代码。
- 在编写或修改代码前，先简要说明方案；涉及较大改动时需等待用户确认。
- 如果任务预计需要修改超过 3 个文件，先暂停并拆分为更小的任务。
- 每次用户纠正行为或规则后，应将新规则同步到 `AGENTS.md`，除非用户明确不要修改。

## 任务启动顺序

- 对非 trivial 任务，先阅读 `docs/ai-context.md`，再结合本文件与相关代码制定计划。
- 若 `docs/ai-context.md`、`PROJECT_OVERVIEW.md` 与实际代码不一致，以当前代码和本文件约束为准，并在交付时指出文档偏差。

## 项目背景

OmniTest 是一个 Python 自动化测试框架，支持：

- API 自动化测试
- Web UI 自动化测试
- App UI 自动化测试
- 性能测试

项目入口：

- `run.py` / `main.py`：命令行入口
- `omni_test.py`：链式编程 API

重要目录：

- `cases/api/`
- `cases/web/`
- `cases/app/`
- `cases/performance/`
- `config/`
- `utils/runner/`
- `utils/reporting/`
- `utils/path/`
- `tests/baseline/`

## 修改策略

- 只做完成当前任务所需的最小合理改动。
- 优先修复根因，不堆叠临时补丁。
- 不要在解决具体问题时顺手重构无关模块。
- 尽量保持 CLI 行为和公开 API 向后兼容。
- 不要重命名稳定接口，除非任务明确要求。
- 不要手动修改生成产物、测试报告或缓存目录。

## OmniTest 专用规则

- 将 `utils/runner/test_runner.py` 视为核心执行逻辑所在位置。
- 将 `utils/path/path_util.py` 视为运行路径和报告路径的单一事实来源。
- 保持报告目录约定：`reports/YYYYMMDD_HHMM/`。
- 保持无效测试目标行为：退出码为 `4`，并跳过报告生成。
- 保持 `config/config_manager.py` 的配置合并顺序和懒加载单例访问方式。
- 保持 `omni_test.py` 的链式调用体验，每个链式方法应返回实例本身。

## 代码风格

- 遵循相邻文件已有的 Python 代码风格。
- 新增工具前，优先复用 `utils/` 下已有能力。
- 不要无必要引入新的第三方依赖。
- 保持函数和类职责清晰，避免过度抽象。
- 注释要少而有用，不解释显而易见的代码。

## 测试规则

修改核心模块后，优先运行：

```bash
pytest tests/baseline/test_baseline.py -v
```

核心模块包括：

- `run.py`
- `omni_test.py`
- `config/config_manager.py`
- `utils/path/path_util.py`
- `utils/runner/test_runner.py`

修复 bug 时：

- 优先新增或更新能复现问题的回归测试。
- 再用最小改动修复问题。
- 从最小相关测试开始验证，再考虑更大范围测试。
- 不要尝试修复无关失败测试。

代码修改完成后，需要列出：

- 可能出现的问题
- 建议覆盖的测试用例
- 已执行或建议执行的验证命令

## 常用命令

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -e .

pytest tests/baseline/test_baseline.py -v
pytest tests/baseline/ --cov=. --cov-report=term-missing

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

## 最终回复要求

- 总结修改内容和原因。
- 列出执行过的验证。
- 说明风险、假设或后续建议。
- 如果写了代码，额外列出可能问题和建议测试用例。
