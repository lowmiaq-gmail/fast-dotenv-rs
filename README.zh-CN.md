# fast-dotenv-rs

[English](README.md)

[![CI](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/workflows/ci.yml/badge.svg)](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/Rust-PyO3-orange.svg)](https://pyo3.rs/)
[![License](https://img.shields.io/badge/license-MIT%20AND%20BSD--3--Clause-green.svg)](LICENSE)

`fast-dotenv-rs` 是一个以 Rust/PyO3 加速的 `python-dotenv==1.2.2` 兼容发行版。
它的发行名是 `fast-dotenv-rs`，但运行时的导入路径和命令行接口保持上游不变：

> A fast Rust-backed drop-in replacement for `python-dotenv==1.2.2`, built with
> PyO3 and Maturin. It preserves the `dotenv` Python API, CLI, IPython extension,
> interpolation rules, and file mutation behavior.

```python
from dotenv import load_dotenv, dotenv_values
```

```bash
dotenv --help
python -m dotenv --help
```

For Python developers looking for a faster `.env` parser, the project keeps the familiar
`python-dotenv` interface while moving the CPU-heavy parsing core to Rust. Existing code keeps
using `from dotenv import load_dotenv`; the distribution name changes, not the runtime API.

## 为什么使用它

- **迁移成本低**：现有代码继续 `from dotenv import load_dotenv`，无需引入新的
  import namespace；
- **兼容性可验证**：完整运行 `python-dotenv==1.2.2` 官方测试，而不是只覆盖常见
  `KEY=value` 路径；
- **性能数据可复现**：候选与 Oracle 分进程执行，先验证返回值再计算加速倍数；
- **交付友好**：PyO3 + Maturin 构建 wheel，CI 覆盖 Linux、macOS 和 Windows。

项目主页：<https://github.com/lowmiaq-gmail/fast-dotenv-rs>

### 本地性能快照

Linux x86-64 / CPython 3.12 的隔离进程测试中，`dotenv_values()` 的三个内存解析
workload 为 **15.957×–88.609×**。计时前会先检查类型、顺序和值；这不是文件 I/O、
macOS/Windows 或全部业务场景的结论。完整输入、命令和限制见
[`BENCHMARK.md`](BENCHMARK.md)。

## 当前状态

这是公开源码的预发布版本；尚未发布到 PyPI，也尚未创建 GitHub Release。
本地 Linux x86-64 / CPython 3.12 的完整上游验收入口已经通过：

```text
218 passed, 1 skipped, 0 failed
```

唯一 skip 是上游 Linux/root 条件产生的；IPython 已安装，3 个上游 IPython 测试均
实际执行。[GitHub Actions CI #3](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31511953697)
还通过了 Linux Python 3.10/3.12 完整门禁、macOS arm64 wheel 的 219 个上游测试，
以及 Windows x86-64 wheel 的 169 passed / 50 个上游平台 skip。上述结论是构建、
安装和兼容性证据，不是 macOS/Windows 性能数据。

完整契约见 [`docs/UPSTREAM-CONTRACT.md`](docs/UPSTREAM-CONTRACT.md)，当前发布判定见
[`FULL-RELEASE-REPORT.md`](FULL-RELEASE-REPORT.md)。

## 安装

目前没有可供用户直接下载的 PyPI 包。请从源码构建：

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -U pip maturin
python -m pip install "click>=5" # 使用 dotenv CLI 时需要
maturin develop --release
```

构建 wheel：

```bash
maturin build --release --out wheelhouse
python -m pip install wheelhouse/*.whl
```

wheel 的安装名仍是 `fast-dotenv-rs`，但代码必须继续使用 `dotenv`。本项目不提供
另一个运行时 import 名；兼容性验收只认 `dotenv` 命名空间。

### 不要与 Oracle 同环境安装

`python-dotenv` 和本项目都提供顶层 `dotenv` 包及 `dotenv` 命令，不能在同一个环境
中并存。否则最后安装的包会覆盖前一个包，测试结果没有意义。对比或验收时必须
使用两个独立虚拟环境，或像仓库脚本一样对两个进程分别设置 `PYTHONPATH`：

```text
Oracle 环境：python-dotenv==1.2.2  -> import dotenv
候选环境：  fast-dotenv-rs         -> import dotenv
```

## API 和用法

顶层导出保持 `python-dotenv==1.2.2`：

```python
from dotenv import (
    dotenv_values, find_dotenv, get_cli_string, get_key,
    load_dotenv, load_ipython_extension, set_key, unset_key,
)
```

兼容表面还包括：

- `dotenv.main.DotEnv`、`rewrite`、`resolve_variables` 及文件/环境变量操作；
- `dotenv.parser` 的 `Binding`、`Original`、`Reader`、`Position` 和 parser 函数；
- `dotenv.variables` 的 `Atom`、`Literal`、`Variable` 和 `parse_variables`；
- `dotenv.cli` 的 `list`、`set`、`get`、`unset`、`run`；
- `dotenv.ipython` 的 `IPythonDotEnv` 和 `%dotenv` magic。

常规加载：

```python
from dotenv import dotenv_values, load_dotenv

load_dotenv()                         # 找到 .env 并写入 os.environ
config = dotenv_values(".env")       # 只解析，不改变 os.environ
config = dotenv_values(stream=...)    # 也支持文本 stream
```

上游行为包括插值、重复 key 顺序、`None` 与空字符串的区别、`override`、
`PYTHON_DOTENV_DISABLED`、日志、FIFO、编码、symlink、原子文件改写和异常传播。
不要只用 `KEY=value` 的 happy path 判断兼容性；完整签名、返回值和边界行为以
[`docs/UPSTREAM-CONTRACT.md`](docs/UPSTREAM-CONTRACT.md) 为准。

## CLI

安装 `click` 后，命令名不变：

```bash
dotenv list
dotenv list --format=json
dotenv set DATABASE_URL 'postgres://localhost/app'
dotenv get DATABASE_URL
dotenv unset DATABASE_URL
dotenv run -- python app.py
```

全局选项仍是 `-f/--file`、`-q/--quote`、`-e/--export` 和 `--version`；`run` 保留
`--override/--no-override`、命令参数透传、stdout/stderr 和退出码行为。

## IPython

安装 IPython 后：

```ipython
%load_ext dotenv
%dotenv
%dotenv path/to/.env
%dotenv -o -v
```

`-o` 覆盖已存在变量，`-v` 打开 verbose。没有安装 IPython 不影响普通 API 和 CLI；
但 IPython 验收项会按上游规则跳过，不能把 skip 当作通过。

## 验收

安装测试依赖后执行完整上游门禁：

```bash
python -m pip install "pytest>=8,<9" "click>=5" "ipython>=8"
bash scripts/run_upstream_full.sh
```

脚本会固定下载并校验 `python-dotenv==1.2.2` sdist 与官方测试文件，确认候选从
本项目 `python/` 导入，创建临时 console-script wrapper 供 CLI 子进程使用，并运行
整个官方测试目录。不能用 `-k` 过滤代替完整验收；只允许上游声明的平台 skip。

还应单独执行：

```bash
cargo test --all-targets
PYTHONPATH=python python -m pytest -q tests
PYTHONPATH=python python scripts/run_differential.py
```

完整 release gate 是：namespace/API、parser、文件与环境副作用、CLI/IPython、
完整上游测试、候选/Oracle 差分、安装 wheel 后测试，以及各 CI 平台 wheel 验证。
详见 [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)。

## 隔离 benchmark

benchmark 只在候选和 Oracle 分进程、分 `PYTHONPATH` 下运行：

```bash
python tests/benchmark.py --repeats 7 --warmup 2 --iterations 1000
```

它会校验两边返回类型、顺序和值，再报告中位数和 speedup。默认 workload 是小、
中、大的内存 stream 解析，不能代表文件 I/O、进程启动、真实应用启动或其他操作系统。
报告 benchmark 时必须同时记录 Python 版本、平台、wheel/源码状态、输入规模、
warmup、repeats、iterations 和原始结果；没有 macOS/Windows 实测数据时不得写成
跨平台性能结论。现有本地结果及限制见 [`BENCHMARK.md`](BENCHMARK.md)。

## 开发资料

- [`docs/UPSTREAM-CONTRACT.md`](docs/UPSTREAM-CONTRACT.md)：1.2.2 完整模块、签名、
  副作用和官方测试清单；
- [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)：发布兼容性矩阵和验收门禁；
- [`docs/REUSE-AUDIT.md`](docs/REUSE-AUDIT.md)：复用审计与许可证边界；
- [`docs/FULL-REWRITE-PLAN.md`](docs/FULL-REWRITE-PLAN.md)：工程实现与并行开发计划；
- [`FULL-RELEASE-REPORT.md`](FULL-RELEASE-REPORT.md)：当前本地证据、未完成平台门禁和发布判定。

## 许可证

Rust/PyO3 项目代码使用 MIT；与上游兼容层、测试和行为基线相关的 BSD-3-Clause
通知见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 和 `licenses/`。
