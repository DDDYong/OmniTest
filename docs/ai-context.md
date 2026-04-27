# OmniTest AI Context

本文件用于给 AI 编码助手补上下文。处理非 trivial 任务时，应先阅读本文件，再结合 `AGENTS.md`、实际代码和测试入口制定计划。

## 1. 架构地图

- 入口层：`run.py` / `main.py` 是 CLI 入口，`omni_test.py` 是链式 API 入口。
- 调度层：核心执行逻辑在 `utils/runner/test_runner.py`，报告生成在 `utils/reporting/`，依赖与打包辅助在 `utils/packaging/`。
- 配置层：`config/config_manager.py` 负责配置加载、合并、环境变量覆盖、reload 与单例访问。
- 路径层：`utils/path/path_util.py` 是运行路径、报告路径等路径逻辑的单一事实来源。
- 用例层：`cases/api/`、`cases/web/`、`cases/app/`、`cases/performance/` 分别承载不同类型测试。
- 回归层：`tests/baseline/` 用于验证导入、入口和对外接口契约，优先用于核心模块变更后的快速回归。

## 2. 遇到任务时先判断什么

- 是 CLI 行为问题，还是链式 API 问题；优先区分 `run.py` / `main.py` 与 `omni_test.py`。
- 是执行流程问题，还是配置、路径、报告问题；对应先看 `utils/runner/`、`config/`、`utils/path/`、`utils/reporting/`。
- 是具体用例问题，还是框架基础设施问题；不要把用例层问题和框架层问题混在一起修。

## 3. 先看哪些文件

- 改 CLI 或运行行为：先看 `run.py`、`utils/runner/test_runner.py`。
- 改链式 API：先看 `omni_test.py`。
- 改配置系统：先看 `config/config_manager.py`、`config/default.yaml`、`config/{env}.yaml`。
- 改路径或报告输出：先看 `utils/path/path_util.py`、`utils/reporting/allure_report.py`。
- 改整体架构理解：再看 `PROJECT_OVERVIEW.md` 和 `README.md`，但最终以代码为准。

## 4. 当前稳定约定

- `run.py` 保持兼容层定位，核心执行逻辑优先放在 `utils/runner/test_runner.py`。
- `omni_test.py` 保持链式调用体验，链式方法应返回实例本身。
- `PathUtil` 负责运行路径和报告路径等路径逻辑，是单一事实来源。
- 报告目录约定保持为 `reports/YYYYMMDD_HHMM/`。
- 无效测试目标时保持退出码 `4`，并跳过报告生成。
- 配置合并顺序、reload 失败回滚和懒加载单例访问方式不应被破坏。

## 5. 已知坑与易错点

- 不要手动修改 `reports/`、`htmlcov/`、`.pytest_cache/`、`logs/`、`.venv/`、`venv/` 等运行产物或环境目录。
- 配置相关改动容易同时影响 CLI、API 与测试基线；先跑最小相关验证，再扩大范围。
- 看起来属于 `run.py` 的问题，很多实际根因在 `utils/runner/test_runner.py`、`utils/path/path_util.py` 或
  `config/config_manager.py`。
- 对外接口、返回码、目录约定和报告行为有兼容性要求，不要为局部问题破坏整体体验。

## 6. 常用验证命令

```bash
pytest tests/baseline/test_baseline.py -v
pytest tests/baseline/ --cov=. --cov-report=term-missing

python run.py api
python run.py web
python run.py app
python run.py report
python run.py clean
```

## 7. 文档维护规则

- 若任务暴露了新的稳定约定、常见坑或推荐验证方式，优先更新本文件。
- 若任务改变了架构边界、核心不变量或项目级约束，再同步更新 `AGENTS.md` 或 `PROJECT_OVERVIEW.md`。
