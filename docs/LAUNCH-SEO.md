# Launch and discovery plan

## 目标

让真正需要“更快 `.env` 解析且不愿修改现有 `python-dotenv` 调用”的 Python 开发者，
能够发现、信任、安装并持续使用本项目。SEO 不是关键词数量竞赛；完整漏斗是：

```text
搜索/推荐曝光 → 仓库访问 → 看懂兼容边界 → 安装 → 上游测试通过 → 真实项目采用
```

仓库 Star 只是中间信号，不是最终成功指标。北极星指标是下游项目的有效安装和留存。

## 搜索意图与落地内容

| 用户意图 | 自然查询 | 首要落地证据 |
|---|---|---|
| 找替代品 | `python-dotenv alternative` | drop-in API、迁移示例 |
| 找性能方案 | `fast dotenv parser python` | 可复现 benchmark 与限制 |
| 找 Rust 实现 | `rust dotenv parser pyo3` | Rust/PyO3 架构、wheel |
| 避免改代码 | `python-dotenv drop-in replacement` | `dotenv` namespace 和 CLI 兼容 |
| 验证可靠性 | `python-dotenv compatible implementation` | 完整上游测试结果与来源 |

这些词应自然出现在标题、简介、README 首屏和 PyPI metadata，不重复堆叠。

## GitHub 发布配置

仓库描述：

```text
Fast Rust-backed drop-in replacement for python-dotenv 1.2.2, built with PyO3 and Maturin.
```

Topics（发布时一次配置，不超过 GitHub 的 20 个上限）：

```text
dotenv
python-dotenv
rust
python
pyo3
maturin
environment-variables
env-parser
python-extension
drop-in-replacement
performance
configuration
```

发布后将 [`assets/social-preview.png`](../assets/social-preview.png) 配置为 social
preview。文件为 1280×640 PNG、低于 1 MB；图片只表达项目名、兼容对象和技术路径，
不写未经多平台验证的夸张性能数字。

## 发布门禁

实时完成状态和每项公共证据统一记录在 [`LAUNCH-STATUS.md`](LAUNCH-STATUS.md)。
只有公开端点、站点设置和获准渠道都有可复查证据时，才允许标记 `LAUNCH_COMPLETE`；
本地草稿、图片文件或尚未运行的工作流均不计为推广完成。

1. 公开仓库存在，默认分支为 `main`，README、许可证、第三方通知可访问；
2. GitHub Actions 的 Linux、macOS、Windows wheel 构建和安装验证通过；
3. release wheel 在独立环境中再次通过完整上游测试；
4. PyPI 名称、Trusted Publishing 和 `0.1.1` 正式发布已完成；
5. PyPI 页面上的描述、项目链接、许可证和安装命令实际可用；
6. GitHub Release 必须为 formal release；不得把 Linux 单机 benchmark 外推成跨平台性能结论。

## 首发内容资产

### 一句话

```text
fast-dotenv-rs keeps the python-dotenv API and CLI, but moves .env parsing to a verified Rust core.
```

### 短帖

```text
I built fast-dotenv-rs, a Rust/PyO3 drop-in replacement for python-dotenv 1.2.2.
Existing `from dotenv import load_dotenv` calls stay unchanged. The candidate passes the full
upstream suite locally (218 passed, 1 platform skip) and includes isolated, reproducible
benchmarks. I am looking for real-world compatibility reports before calling it stable.
```

### 目标社区顺序

1. GitHub Release 和 PyPI：承接搜索与安装，必须先完成；
2. Python/Rust 开发者社区：征集兼容性和真实 workload，不只宣传速度；
3. Hacker News / Reddit 等技术社区：用实现、验证方法和失败边界讲故事；
4. 中文渠道：知乎、掘金、V2EX，发布完整迁移与 benchmark 复现过程；
5. 向使用 `python-dotenv` 的开源项目提交可选 benchmark/兼容报告；未经维护者同意，
   不做批量 PR 或垃圾推广。

## 验收指标

每周记录，不用 Star 代替使用：

| 层级 | 指标 | 30 天初始判定 |
|---|---|---|
| 发现 | GitHub/PyPI 搜索曝光、来源页访问 | 能被核心查询找到，来源可解释 |
| 理解 | README 访问到安装页/文档的点击 | 安装与兼容入口可见 |
| 采用 | PyPI 独立下载、下游仓库引用 | 出现非作者环境的真实安装 |
| 质量 | 兼容性 issue、CI 平台通过率 | P0/P1 兼容问题有复现和响应 |
| 留存 | 版本间重复下载、真实项目持续引用 | 不只在首发日产生一次流量 |

第 14 天复盘查询覆盖、README 转化和安装阻力；第 30 天决定继续、改定位或停止。
如果只有访问和 Star、没有真实安装，优先排查分发、信任和替换成本，不继续堆宣传。
仓库的 `Launch monitoring` 工作流每周采集一次公共基线；PyPI Stats 对新包可能暂时
无数据且按日更新，这种情况记录为“尚未索引”，不能虚构为零下载或推广成功。

## 事实来源

- GitHub 官方建议 README 解释项目用途、价值、上手和求助入口；
- GitHub Topics 用于按用途、领域、社区和语言发现仓库；
- Python Packaging metadata 的 `description`、`keywords`、`classifiers`、`urls` 会进入
  包索引元数据；
- 搜索标题和摘要应清晰、独特、符合页面内容，关键词堆叠会降低质量。
