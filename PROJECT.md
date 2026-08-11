# 项目说明

## 项目目标

`fast-dotenv-rs` 是 `python-dotenv==1.2.2` 的 Rust/PyO3 加速兼容实现。目标是在不改变现有 `dotenv` Python 导入路径、CLI、IPython 扩展和关键行为契约的前提下，把 CPU 密集的解析与插值核心迁移到 Rust，并提供可验证、可发布的跨平台 wheel。

## 解决的问题

`python-dotenv` 的解析核心由 Python 实现。本项目尝试在保持完整兼容性的前提下提高 CPU 密集解析场景的性能，同时避免用户修改业务代码的导入方式。

## 用户

- 已经使用 `python-dotenv`、希望降低迁移成本的 Python 开发者。
- 需要稳定 `.env` 解析、CLI 或 IPython 行为的应用和工具链。
- 需要可复现兼容性与性能证据的维护者。

## 当前范围

- 保持 `python-dotenv==1.2.2` 的 `dotenv` 命名空间和公开行为契约。
- Rust/PyO3 实现解析与插值热点路径。
- Python 兼容层保留文件、环境变量、日志、CLI、IPython 等 Python 特有行为。
- 通过上游完整测试、差分测试、wheel 安装测试和 benchmark 进行验证。
- 通过 Maturin 构建并发布跨平台 wheel / sdist。

## 非目标

- 不引入新的运行时 import namespace 代替 `dotenv`。
- 不为了性能牺牲返回值、顺序、异常、日志、文件副作用、CLI 输出或退出码兼容性。
- 不把尚未实测的平台性能推断为已验证结论。
- 不在本项目内重新设计 `python-dotenv` 的公共 API。

## 关键约束

- 行为 Oracle 固定为官方 `python-dotenv==1.2.2`。
- 正确性优先于加速。
- Oracle 与候选实现必须隔离，避免同名 `dotenv` 包互相覆盖。
- Rust crate 当前版本与构建约束以 `Cargo.toml` 为准；Python 打包与发布配置以仓库实际配置和 CI 为准。

## 成功标准

完整完成标准以 `docs/UPSTREAM-CONTRACT.md`、`docs/COMPATIBILITY.md` 与公开发布证据为准。高层要求包括：

1. `dotenv` namespace / API / CLI / IPython 与上游契约一致。
2. 完整上游测试和差分测试无未解释差异。
3. 支持平台的安装 wheel 通过验收。
4. 性能结论有可复现 benchmark 证据。
5. 发布状态有公开、可检查的证据。

## 当前状态

当前正式代码版本为 `0.1.1`。GitHub 已存在正式 `v0.1.1` Release；更细的工程、分发、推广与监控状态请始终查看 `PROGRESS.md` 和其引用的领域状态文件，不要从旧实施计划推断当前进度。

## Source of Truth

| 问题 | Source of Truth |
|---|---|
| 项目为什么存在、范围是什么 | `PROJECT.md` |
| 我现在做到哪、下一步做什么 | `PROGRESS.md` |
| 人/Agent 应从哪里开始读、改哪里 | `PROJECT-MAP.md` |
| Agent 工作规则 | `AGENTS.md` |
| 用户安装与使用 | `README.md` / `README.zh-CN.md` |
| 上游公开行为契约 | `docs/UPSTREAM-CONTRACT.md` |
| 兼容性与验收边界 | `docs/COMPATIBILITY.md` |
| 当前发布/推广状态 | `docs/LAUNCH-STATUS.md` |
| 历史完整重写方案 | `docs/FULL-REWRITE-PLAN.md` |
| 性能证据 | `BENCHMARK.md` |
| 发布证据 | `FULL-RELEASE-REPORT.md`、GitHub Release、PyPI/CI 公开记录 |

如果这些来源互相矛盾，优先使用实际代码、构建配置、测试/CI 与公开运行证据，并修正文档漂移。