# 贡献指南

感谢愿意花时间参与 conf_base。无论是补文档、写示例、修 bug 还是提需求，都欢迎。

> English speakers: you are welcome too — issues and PRs in English are fine.

## 本地开发环境

```bash
git clone https://github.com/DashSalter/conf_base.git
cd conf_base

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

跑测试与类型检查：

```bash
pytest -q
mypy conf_base
```

## 提交前自检

一个 PR 合入前，下面三项必须全绿：

- [ ] `pytest -q` 全部通过（当前 167 个用例）
- [ ] `mypy conf_base` 无错误（`mypy.ini` 中 `strict = True`）
- [ ] 覆盖率不下降（当前 88%，CI 硬门槛 80%）

```bash
pytest --cov=conf_base --cov-report=term-missing
```

## 代码约定

- **零必需依赖**：优先标准库；第三方库只能放进 `extras_require`，不能进 `install_requires`
- **支持 Python 3.8+**：不要用 `match`、不要用运行时的 `X | Y` 注解（需要时用 `typing.Union` 或 `from __future__ import annotations`）
- **公共 API 必须有类型注解**，本项目按 mypy strict 维护
- **异常统一继承 `ConfBaseError`**，并多继承对应的内建异常（如 `ConfigKeyError` 同时是 `KeyError`）
- **写配置一律走 `ConfigFile` / `Section.batch()`**，不要在业务代码里直接 `open()` 写配置文件——原子替换、加锁、环境变量覆盖都在那一层
- **新增行为必须补测试**，并同步更新 `CHANGELOG.md` 的 `[Unreleased]` 段
- **配置类禁止相互继承**：这是架构约束（描述符与 `ConfigFile` 是类级绑定），`__init_subclass__` 会直接报错。需要复用就在多个类里重复声明配置项
- 标识符、路径、日志用英文；注释和文档用中文，保持与现有代码一致

## 分支与提交

1. fork 仓库，从 `master` 切出分支：`feature/xxx`、`fix/xxx`、`docs/xxx`
2. 一个 PR 只做一件事，避免混入无关格式化
3. 提交信息建议「动词 + 对象」，中英文均可，例如：
   - `修复 Windows 下 os.replace 偶发 PermissionError`
   - `feat: add transaction() context manager`

## 提 PR

- 按 `.github/PULL_REQUEST_TEMPLATE.md` 填写：动机、实现方式、测试情况、是否破坏兼容
- CI 会跑 Python 3.8–3.14 矩阵 + mypy strict + 覆盖率门槛，请等绿灯
- **破坏性变更先开 issue 讨论**，不要直接提 PR

## 提 Issue

- 用现有模板：`.github/ISSUE_TEMPLATE/` 下的 `bug_report` / `feature_request` / `question`
- 报 bug 请附：最小复现代码、Python 版本、conf_base 版本、操作系统
- 不确定是用法的，先用 `question` 模板，不会被打扰

## 两个平台

主开发在 GitHub（`DashSalter/conf_base`），Gitee（`kuangjianke/conf_base`）是镜像，两边自动同步。
PR / Issue 两边都收，处理顺序以 GitHub 优先。

## 不知道从哪开始？

看 [`ROADMAP.md`](ROADMAP.md) 里的「好上手的任务」一节，挑一个标了 `good first issue` 的直接开干，遇到卡点可以在 issue 里问。
