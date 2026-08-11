# Full release report

## 判定

当前项目是一个**未发布的预发布候选**。目标是作为
`python-dotenv==1.2.2` 的完整 drop-in replacement 使用：发行名为
`fast-dotenv-rs`，运行时仍为 `dotenv` import、`dotenv` CLI 和 `%dotenv`。

当前证据支持：Linux x86-64 / CPython 3.12 上候选实现通过完整上游验收入口。
当前证据不支持：macOS/Windows wheel 已通过、PyPI/GitHub 已发布、所有应用 workload
都有加速，或任何未记录平台的结果。

## 已验证证据

| 门禁 | 结果 | 证据边界 |
|---|---|---|
| 上游来源 | 通过 | `python-dotenv==1.2.2` 官方 sdist、PyPI digest、12 个测试/fixture hash |
| 候选 namespace | 通过 | 上游测试进程确认从项目 `python/` 导入 `dotenv` |
| 完整上游测试 | `218 passed, 1 skipped, 0 failed` | 本地 Linux x86-64 / CPython 3.12；唯一 skip 为上游平台条件 |
| IPython | 通过 | 3 个上游 IPython 测试均实际执行 |
| parser / variables | 通过 | 完整上游 parser、variables 和 main 测试路径 |
| 文件/环境副作用 | 通过 | load/find/get/set/unset、编码、FIFO/symlink、日志和环境相关上游案例 |
| CLI | 通过 | `list/set/get/unset/run`、参数透传、输出和退出码；临时 wrapper 保留 `argv[0]=dotenv` |
| `python -m dotenv` | 通过 | 上游入口和 CLI 行为验证 |
| 隔离差分 | 通过 | seed `20260811`；10,000 个随机案例；Oracle/Candidate 不同进程和模块路径 |
| 本地 benchmark | 通过 | 3 个输入规模，语义先校验；本机中位数提速 15.957×–88.609× |
| Linux wheel | 通过 | fresh venv 仅安装候选 wheel；基础 import 无 Click；完整上游套件再次 218 passed、1 skipped |
| macOS wheel | 待 CI | 没有本地或远程通过证据 |
| Windows wheel | 待 CI | 没有本地或远程通过证据 |
| PyPI/GitHub 发布 | 未发布 | 本报告不提供虚构的下载地址或 release 链接 |

## 如何复现

候选与 `python-dotenv` 不能装在同一个环境中，因为两边都提供顶层 `dotenv` 包和
`dotenv` 命令。建议在干净环境中安装测试工具，再运行：

```bash
python -m pip install "pytest>=8,<9" "click>=5"
# 需要 IPython 全量项时再安装：
python -m pip install "ipython>=8"
bash scripts/run_upstream_full.sh
```

脚本会自动创建并清理临时目录，下载并校验官方 sdist，验证测试文件 hash，确认候选
优先于已安装包，并使用等价 console-script launcher 运行 CLI 测试。完整运行不得改成
`-k` 子集；只允许上游已有的 platform/optional-dependency skips。

项目自身的 Rust 和 Python 检查：

```bash
cargo test --all-targets
PYTHONPATH=python python -m pytest -q tests
PYTHONPATH=python python scripts/run_differential.py
```

## API 覆盖

当前目标覆盖 `dotenv` 顶层导出：

```text
get_cli_string, load_dotenv, dotenv_values, get_key,
set_key, unset_key, find_dotenv, load_ipython_extension
```

并覆盖 `dotenv.main`、`dotenv.parser`、`dotenv.variables`、`dotenv.cli`、
`dotenv.ipython`、`dotenv.__main__`、`dotenv.version`。完整签名、返回值、日志、异常、
环境和文件副作用见 [`docs/UPSTREAM-CONTRACT.md`](docs/UPSTREAM-CONTRACT.md)。

## Benchmark 证据边界

benchmark 必须在候选与 Oracle 的隔离子进程中执行，不能在同一个父进程先后 import 两
个同名 `dotenv`。命令：

```bash
python tests/benchmark.py --repeats 7 --warmup 2 --iterations 1000
```

结果先检查返回类型和值顺序，再报告中位数；必须记录输入规模、原始样本、平台、
Python 版本和 wheel/源码状态。当前 [`BENCHMARK.md`](BENCHMARK.md) 的数据只代表其
记录的 Linux 环境和内存 stream workload，不代表文件 I/O、启动延迟、macOS、Windows
或任何真实业务，也不应直接写成跨平台营销数字。

## 发布前剩余工作

1. 在 macOS 和 Windows CI 构建并安装 wheel，至少重复 namespace、import 和 CLI smoke；
2. 对 release wheel 运行隔离 benchmark，保存原始结果，不将本地单机数据外推；
3. 核对许可证、版本、README、CHANGELOG、artifact hash 和最终发布仓库地址；
4. 所有门禁完成后，才可以创建公开 GitHub Release 或上传 PyPI。

## 相关文档

- [`README.md`](README.md)：安装、使用、CLI、IPython 和快速验收；
- [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)：兼容性矩阵和正式发布门禁；
- [`docs/UPSTREAM-CONTRACT.md`](docs/UPSTREAM-CONTRACT.md)：上游完整契约与测试来源；
- [`BENCHMARK.md`](BENCHMARK.md)：当前 benchmark 原始背景与限制；
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)：BSD-3-Clause 上游通知。
