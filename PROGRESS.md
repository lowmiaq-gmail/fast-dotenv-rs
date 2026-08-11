# 项目进度

> 这是“现在做到哪”的唯一项目级入口。它不是历史日志，也不复制每个领域的全部细节。
> 下次继续项目时，先看本文件，再按链接进入对应 Source of Truth。

最后整理：2026-08-12

## 一句话状态

核心重写、兼容性验证和跨平台构建已经完成；当前代码版本为 `0.1.1`，GitHub 已存在正式 `v0.1.1` Release。发布/推广相关旧文档存在状态漂移，因此本轮 Setup 先恢复项目入口和状态层级；PyPI `0.1.1` 的最终公网安装证据需按发布流程再次核验后再把整个 Launch 标为完成。

## 当前阶段

| 工作流 | 状态 | 当前依据 / 下一步 |
|---|---|---|
| Rust/PyO3 核心实现 | 完成 | `src/`、完整上游与差分验证证据 |
| Python drop-in 兼容层 | 完成 | `python/dotenv/`、`docs/UPSTREAM-CONTRACT.md` |
| 兼容性验收 | 完成 | `docs/COMPATIBILITY.md`、`FULL-RELEASE-REPORT.md` 中的测试证据 |
| Benchmark | 已有基线 | `BENCHMARK.md`；不得外推到未测试平台/业务 |
| GitHub 0.1.1 Release | 已确认 | GitHub `v0.1.1` 正式 Release 已存在并包含跨平台 wheel / sdist |
| PyPI 0.1.1 最终公网验收 | 待重新核验 | 用普通 `pip install fast-dotenv-rs==0.1.1` + 完整门禁核验；以公开 PyPI/CI 证据为准 |
| 外部推广 | 未作为完成项 | 以 `docs/LAUNCH-STATUS.md` 的渠道状态为准；不要把草稿当发布 |
| 项目 Setup / 可接管性 | 本轮已恢复 | `PROJECT.md`、`PROGRESS.md`、`PROJECT-MAP.md`、`AGENTS.md` |

## 最近完成

- 完成 `python-dotenv==1.2.2` 兼容重写主链和完整上游测试。
- 完成隔离 Oracle/Candidate 差分验证与 benchmark 基线。
- 完成 Linux、macOS、Windows 发布产物构建与相关验收。
- 修复 `0.1.0` 默认安装缺 Click 的发布问题，并推进到 `0.1.1`。
- GitHub 已生成正式 `v0.1.1` Release。
- 2026-08-12 使用 `project-setup adopt` 思路进行 dogfood，补齐项目入口、进度入口、人/Agent 地图，并开始消除旧计划与当前事实之间的文档漂移。

## 当前下一步

按优先级只保留真正未闭环的事项：

1. **核验 PyPI 0.1.1**：普通公网安装，不使用 `[cli]` extra，验证 `dotenv` CLI、导入、完整上游测试和产物版本。
2. **同步发布状态文档**：核验完成后更新 `docs/LAUNCH-STATUS.md` / `FULL-RELEASE-REPORT.md`，消除 `0.1.1` 仍“等待发布”的旧状态。
3. **决定外部推广范围**：只对明确授权的渠道执行；没有公开 URL 不记为完成。
4. **按既定检查点复盘采用情况**：不要为了“继续开发”而增加无需求功能。

## 阻塞 / 风险

- `docs/FULL-REWRITE-PLAN.md` 是历史实施计划，其中发布 checklist 已落后于当前 GitHub Release 事实；不要把它当当前进度。
- `docs/LAUNCH-STATUS.md` 与 `FULL-RELEASE-REPORT.md` 记录的是发布过程中的阶段状态，需在 PyPI 0.1.1 最终复验后统一刷新。
- 本项目与 `python-dotenv` 提供同名 `dotenv` namespace；Oracle 与候选不能在同一个环境中混装。
- 性能证据只覆盖 `BENCHMARK.md` 明确记录的环境与 workload。

## 继续工作时的读取顺序

人或 Agent 下次回来，按这个顺序：

1. `PROGRESS.md` — 现在做到哪、下一步是什么。
2. `PROJECT.md` — 项目目标、范围、成功标准。
3. `PROJECT-MAP.md` — 东西在哪里、改什么去哪里。
4. `AGENTS.md` — Agent / 贡献者执行规则。
5. 再按任务进入具体领域文档，例如兼容性看 `docs/COMPATIBILITY.md`，发布看 `docs/LAUNCH-STATUS.md`。

## 更新规则

- 每次完成一个会改变“下一步”的阶段性任务，更新本文件。
- 只保留：当前状态、最近完成、下一步、阻塞。
- 详细历史交给 Git、Release、Issue、领域文档，不在这里堆流水账。
- 如果本文件与代码、CI、公开发布证据冲突，先相信运行/公开证据，再立即修正本文件。