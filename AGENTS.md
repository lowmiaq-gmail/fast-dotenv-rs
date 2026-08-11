# AGENTS.md

这是本仓库的人类协作与 Coding Agent 接管入口。

目标不是重复全部项目文档，而是告诉下一位执行者：先读什么、以什么为准、改什么去哪里、改完怎么验证。

## 进入项目后的读取顺序

1. `PROGRESS.md` — 当前做到哪、下一步、阻塞。
2. `PROJECT.md` — 项目目标、范围、非目标、成功标准。
3. `PROJECT-MAP.md` — 目录与文档地图，以及常见修改应该去哪里。
4. 与当前任务直接相关的领域文档。
5. 最后再读具体源码和测试。

不要一上来全仓库无差别扫描；先通过上述地图缩小范围。

## Source of Truth 优先级

明确需求
>
实际代码、运行结果、测试和 CI
>
构建/依赖/发布配置
>
当前状态文档
>
设计/计划文档
>
推测

发生冲突时，不得为了保持旧文档而否定实际运行证据。应修正文档漂移。

## 当前项目关键 SoT

| 问题 | 文件 |
|---|---|
| 现在做到哪 | `PROGRESS.md` |
| 为什么做、范围是什么 | `PROJECT.md` |
| 目录/文档/修改地图 | `PROJECT-MAP.md` |
| 用户怎么安装使用 | `README.md` / `README.zh-CN.md` |
| 上游行为契约 | `docs/UPSTREAM-CONTRACT.md` |
| 兼容性和验证门禁 | `docs/COMPATIBILITY.md` |
| 发布/推广状态 | `docs/LAUNCH-STATUS.md` |
| 性能证据 | `BENCHMARK.md` |

`docs/FULL-REWRITE-PLAN.md` 是历史实施计划，不是当前进度 SoT。

## 修改原则

- Reuse first：先找已有实现、已有测试、已有脚本、已有文档。
- 最小修改：只改当前任务需要的范围，不顺手大重构。
- 正确性优先于性能。
- 不改变 `dotenv` 公开 namespace，除非明确的新需求改变了项目目标。
- 不把 Oracle 与候选包安装进同一个测试环境。
- 不把未测试平台或 workload 的性能推断成已验证结论。
- 能用测试/工具执行的规则，不再写一份平行文字规则。

## 修改路由

- Rust parser / interpolation 热路径 → `src/`
- Python drop-in 行为、文件/环境操作 → `python/dotenv/`
- CLI / `python -m dotenv` → `python/dotenv/cli.py`、`python/dotenv/__main__.py`
- IPython → `python/dotenv/ipython.py`
- 候选契约 / smoke / benchmark → `tests/`
- Oracle / upstream / differential 验证脚本 → `scripts/`
- 行为契约 / 兼容性 / 发布说明 → `docs/`
- CI / 发布 workflow → `.github/workflows/`

更详细导航看 `PROJECT-MAP.md`。

## 完成一个改动前必须做

根据改动类型运行最相关的最小验证，并在需要发布/兼容性结论时运行完整门禁。

常用验证入口：

```bash
cargo test --all-targets
PYTHONPATH=python python -m pytest -q tests
PYTHONPATH=python python scripts/run_differential.py
bash scripts/run_upstream_full.sh
```

不要用局部 happy-path 测试代替完整兼容性结论。

## 文档同步规则

如果改动影响以下任一项：

- 项目范围
- 上游兼容契约
- 模块职责
- 公共 API / CLI
- 发布模型
- 主要依赖
- 验证方法
- 当前阶段或下一步

检查是否需要同步：

- `PROJECT.md`
- `PROGRESS.md`
- `PROJECT-MAP.md`
- `docs/UPSTREAM-CONTRACT.md`
- `docs/COMPATIBILITY.md`
- `docs/LAUNCH-STATUS.md`

只更新受影响的文档，不批量重写。

## 交接要求

任务结束时至少说明：

1. 改了什么。
2. 为什么改。
3. 实际跑了哪些验证。
4. 还有什么没完成 / 被阻塞。
5. 如果下一步发生变化，更新 `PROGRESS.md`。

## 子目录 AGENTS 规则

根 `AGENTS.md` 对全仓库生效。

只有当某个子目录已经复杂到根地图不足以指导工作时，才增加局部 `AGENTS.md`。局部文件只能补充该目录特有规则，不能复制根文件。

当前 `docs/` 文档职责较多，因此允许 `docs/AGENTS.md`；简单目录不创建。