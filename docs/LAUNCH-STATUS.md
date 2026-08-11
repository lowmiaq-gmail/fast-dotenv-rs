# Public launch status

This file is the source of truth for launch completion. Engineering, package distribution,
public discovery, external promotion, and monitoring are tracked separately.

## Current state — 2026-08-11

| State | Result | Evidence or blocker |
|---|---|---|
| Engineering | `ENGINEERING_COMPLETE` | Full pinned upstream suite and isolated differential tests pass. |
| Distribution | `BLOCKED_0_1_1` | [PyPI 0.1.0](https://pypi.org/project/fast-dotenv-rs/0.1.0/) 普通安装 CLI 失败；[GitHub v0.1.0](https://github.com/lowmiaq-gmail/fast-dotenv-rs/releases/tag/v0.1.0) 已提升为 formal 但不能改变 wheel 元数据。等待 `0.1.1` 五平台普通公网安装与 formal Release last。 |
| Owned-channel launch | `OWNED_SURFACES_COMPLETE` | GitHub API 已验证 description、homepage 和 12 个 topics；Settings 页面已验证 social preview 存在。 |
| External community launch | `NOT_APPROVED` | No external account/channel has been selected or authenticated. Draft copy is not counted as publication. |
| Monitoring | `READY_FOR_0_1_1_REVERIFY` | 元数据修复后的 run 31526891482 已成功；发布后仍需以 `0.1.1` 再运行一次。 |

## Required evidence before `LAUNCH_COMPLETE`

- GitHub public API returns the intended description, PyPI homepage, and all intended topics.
- The repository Settings page visibly shows `assets/social-preview.png` as the social preview.
- The launch-monitor workflow succeeds and records GitHub, release, PyPI, and download signals.
- Every explicitly approved external channel has a public post URL, or is excluded from scope.

## Review checkpoints

| Checkpoint | Date | Required review |
|---|---|---|
| Baseline | 2026-08-11 | Distribution URLs, discovery surfaces, downloads, stars/forks/issues, search visibility. |
| Day 14 | 2026-08-25 | Query coverage, README/install friction, compatibility reports, non-author downloads. |
| Day 30 | 2026-09-10 | Adoption/retention evidence and continue/reposition/stop decision. |

Run the same public snapshot locally with:

```bash
python scripts/report_launch_metrics.py --strict-discovery
```
