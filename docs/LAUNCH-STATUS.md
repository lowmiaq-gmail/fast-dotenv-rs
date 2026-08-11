# 发布与推广状态

这是发布 / 推广领域的当前状态 Source of Truth。

它只回答：工程、分发、Owned channel、外部推广和监控分别做到哪。
整个项目下一步仍统一看仓库根目录 `PROGRESS.md`。

最后核对：2026-08-12

## 当前状态

| 领域 | 状态 | 当前证据 / 说明 |
|---|---|---|
| Engineering | `ENGINEERING_COMPLETE` | 固定 `python-dotenv==1.2.2` 的完整上游套件、差分验证和跨平台构建证据已形成。 |
| GitHub Release | `V0_1_1_RELEASE_CONFIRMED` | GitHub 已存在正式 `v0.1.1` Release，并包含 macOS Intel/Apple Silicon、Linux x86-64/ARM64、Windows x86-64 wheel 和 sdist。 |
| PyPI distribution | `REVERIFY_PUBLIC_0_1_1` | 旧 `0.1.0` 普通安装 CLI 缺 Click 的问题已推动版本升级到 `0.1.1`；在把整个 Distribution 判为完成前，仍应以普通公网 `pip install fast-dotenv-rs==0.1.1` + 完整验收的最新可复现证据做一次最终核验。 |
| Owned-channel launch | `OWNED_SURFACES_COMPLETE` | 仓库 description、homepage/topics、social preview 等 Owned surfaces 已完成过验证；如果后续修改，应重新检查。 |
| External community launch | `NOT_APPROVED` | 没有明确授权并验证公开 URL 的外部渠道，不计作发布完成。草稿不等于发布。 |
| Monitoring | `READY_FOR_REVERIFY` | 发布/采用监控能力已存在；最终状态应以 `0.1.1` 的公开分发和后续 checkpoint 数据重新核验。 |

## 为什么这里没有直接写 LAUNCH_COMPLETE

本轮 `project-setup adopt` dogfood 发现旧发布文档存在明显状态漂移：历史计划仍写“等待发布”，但 GitHub `v0.1.1` 正式 Release 已经存在。

因此状态判定遵循：

实际公开证据 / CI / 安装结果
>
当前状态文档
>
历史计划

在 PyPI `0.1.1` 普通公网安装与完整门禁被最新证据明确核验之前，保持保守状态，不从旧文档或记忆推断完成。

## 完成 Distribution 前的最小核验

1. 在干净环境普通安装：

```bash
python -m pip install "fast-dotenv-rs==0.1.1"
```

2. 不使用 `[cli]` extra，确认：

```bash
dotenv --version
python -m dotenv --help
python -c "import dotenv; print(dotenv.__file__)"
```

3. 对安装产物运行发布要求的完整兼容性门禁，而不是仅 smoke test。
4. 核对安装版本、wheel/sdist、GitHub Release 和 CI 指向同一正式版本。
5. 证据成立后再将 Distribution 标为完成，并同步根 `PROGRESS.md` 与需要更新的发布报告。

## 外部推广完成规则

只有满足以下条件之一才算该渠道完成：

- 已明确选择该渠道并获得发布授权，且存在可访问的公开帖子 URL；或
- 明确决定该渠道不在范围内。

仅有文案草稿、待登录页面或计划项不能记为完成。

## Review checkpoints

| Checkpoint | Date | Required review |
|---|---|---|
| Baseline | 2026-08-12 起 | Distribution URLs、公开安装、GitHub Release、downloads、stars/forks/issues、search visibility。 |
| Day 14 | 2026-08-25 | Query coverage、README/install friction、compatibility reports、non-author downloads。 |
| Day 30 | 2026-09-10 | Adoption/retention evidence，以及 continue / reposition / stop 决策。 |

现有监控入口如仍适用，可使用：

```bash
python scripts/report_launch_metrics.py --strict-discovery
```

如果脚本、API 或公开页面与本文件冲突，以实际证据为准并更新本文件。