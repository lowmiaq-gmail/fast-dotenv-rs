# docs/AGENTS.md

本文件只补充 `docs/` 目录的局部规则。全仓库规则仍以根目录 `AGENTS.md` 为准。

## 这个目录的职责

`docs/` 保存项目的工程证据、兼容性契约、发布状态和历史实施资料。

这里最容易出现的问题不是“缺文档”，而是：

- 多份文档描述同一个状态；
- 历史计划被误读成当前状态；
- 发布阶段变化后旧文档没有同步；
- Agent 看到一个旧 checklist 就继续执行已经完成的工作。

因此进入本目录前先看根 `PROGRESS.md` 和 `PROJECT-MAP.md`。

## 文档地图

| 文件 | 用途 | 当前角色 |
|---|---|---|
| `UPSTREAM-CONTRACT.md` | 固定 `python-dotenv==1.2.2` 的模块、API、行为、副作用与测试来源 | 行为契约 SoT |
| `COMPATIBILITY.md` | 兼容性矩阵、正式验收门禁 | 验证 SoT |
| `LAUNCH-STATUS.md` | 工程、分发、Owned channel、外部推广、监控状态 | 发布/推广领域状态 SoT；需与公开证据保持同步 |
| `REUSE-AUDIT.md` | 重写前的复用审计、许可证与借鉴边界 | 设计依据 |
| `FULL-REWRITE-PLAN.md` | 完整重写的历史实施计划与 checklist | 历史文档；不是当前进度 SoT |
| `API-CLI-PLAN.md` | API/CLI 实现阶段的详细计划 | 历史/专项设计资料 |
| `PARSER-GAP-PLAN.md` | parser 差距分析和补齐方案 | 历史/专项设计资料 |
| `PUBLISHING.md` | 发布操作与流程说明 | 发布操作说明 |
| `RELEASE-NOTES-0.1.0.md` | 0.1.0 发布说明 | 历史版本记录 |
| `RELEASE-NOTES-0.1.1.md` | 0.1.1 发布说明 | 当前版本发布记录 |
| `LAUNCH-SEO.md` | 推广/SEO 计划或材料 | 推广计划；不能把草稿等同于已发布 |

## 状态冲突处理

如果：

- 历史计划写“未完成”；
- 但代码、CI、GitHub Release、PyPI 或其他公开证据已经完成；

则：

1. 以实际证据为准；
2. 更新根 `PROGRESS.md`；
3. 给历史文档加清晰标记，避免它继续承担当前状态职责；
4. 如果领域 SoT 本身过期，则更新领域 SoT；
5. 不要为了保持旧 checklist 一致而重新执行已完成工作。

## 更新规则

- 行为/API 变化 → 优先检查 `UPSTREAM-CONTRACT.md`。
- 验收方式、支持边界变化 → 优先检查 `COMPATIBILITY.md`。
- 发布/推广/监控状态变化 → 优先检查 `LAUNCH-STATUS.md` 和根 `PROGRESS.md`。
- 只修改真正受影响的文档。
- 不新建一个新的 `STATUS-2.md`、`FINAL-PLAN.md` 等平行状态文件来绕开旧文档。

## 语言

面向项目维护者的说明优先使用清晰中文；公共用户文档可按受众保留英文或中英双语。技术标识、命令、API 名称保持原样。