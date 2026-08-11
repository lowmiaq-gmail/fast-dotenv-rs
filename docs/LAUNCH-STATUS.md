# 发布与推广状态

这是发布 / 推广领域的当前状态 Source of Truth。

它只回答：工程、分发、Owned channel、外部推广和监控分别做到哪。
整个项目下一步仍统一看仓库根目录 `PROGRESS.md`。

最后核对：2026-08-12

## 当前状态

| 领域 | 状态 | 当前证据 / 说明 |
|---|---|---|
| Engineering | `ENGINEERING_COMPLETE` | 固定 `python-dotenv==1.2.2` 的完整上游套件、差分验证和跨平台构建证据已形成。 |
| Distribution | `DISTRIBUTION_COMPLETE` | [release workflow 31528136044](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31528136044) 通过五平台普通公网安装与完整上游套件，并最后创建 [formal v0.1.1](https://github.com/lowmiaq-gmail/fast-dotenv-rs/releases/tag/v0.1.1)；[PyPI 0.1.1](https://pypi.org/project/fast-dotenv-rs/0.1.1/) 的 5 wheels + sdist 与 Release SHA256 完全一致。 |
| Owned-channel launch | `OWNED_SURFACES_COMPLETE` | GitHub API 已验证 description、homepage/topics；Settings 页面已验证 social preview。 |
| External community launch | `NOT_APPROVED` | 没有明确授权并验证公开 URL 的外部渠道，不计作发布完成。草稿不等于发布。 |
| Monitoring | `MONITORING_COMPLETE` | [post-release run 31528544319](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31528544319) 已针对发布 commit `f254fdf1740db263a7f6f84049e60d8d5bfb8737` 成功。 |

## Distribution 终验证据

1. 由同一 immutable artifact set 发布 5 个 wheel 与 1 个 sdist；
2. release workflow 在 Linux x86-64/ARM64、macOS Intel/Apple Silicon、Windows x86-64
   普通安装基础包并运行完整上游套件；
3. 正式 GitHub Release 在所有公网回装 lane 成功后最后创建；
4. 独立 fresh macOS arm64 venv 显式使用官方 `https://pypi.org/simple` 普通安装，
   version、import、API、`python -m dotenv` 与真实 `dotenv` console script 均通过，且
   没有 `direct_url.json`；
5. 本机默认 pip 镜像首次仍只暴露 `0.1.0`，保留为镜像传播/缓存差异，不将它隐藏，
   也不误写为官方 PyPI 索引失败。

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
