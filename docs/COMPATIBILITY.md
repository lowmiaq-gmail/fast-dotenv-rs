# 完整兼容性与发布门禁

本项目的目标是：在发行包名改为 `fast-dotenv-rs` 的同时，保持
`python-dotenv==1.2.2` 的运行时接口不变。用户代码继续使用 `dotenv`，而不是因为
底层改用 Rust 就改成另一个 import 路径。

```python
from dotenv import load_dotenv, dotenv_values, find_dotenv
```

```bash
dotenv list
python -m dotenv run -- python app.py
```

## 1. 版本和证据边界

| 项目 | 当前结论 |
|---|---|
| 行为 Oracle | 官方 `python-dotenv==1.2.2` sdist/wheel |
| 候选发行名 | `fast-dotenv-rs` |
| 候选运行时命名空间 | `dotenv` |
| 本地已验证 | Linux x86-64、CPython 3.12、完整上游目录：218 passed、1 skipped、0 failed |
| IPython 条件 | IPython 已安装，3 个上游 IPython 测试均实际执行；唯一 skip 为上游平台条件 |
| macOS/Windows | CI #3 wheel 构建、安装、CLI 与上游套件通过；macOS 219 passed，Windows 169 passed / 50 平台 skip |
| PyPI/GitHub | `0.1.1` 已由 immutable release workflow 完成五平台普通公网安装、完整上游套件和 formal Release last；PyPI 与 GitHub Release 的 5 wheels + sdist SHA256 完全一致 |

跨平台 CI 是当前候选版本的构建与兼容证据，不是对所有 Python 版本或真实应用
workload 性能的推断。完整测试的原始来源、hash、模块和签名见
[`UPSTREAM-CONTRACT.md`](UPSTREAM-CONTRACT.md)。

## 2. 兼容性矩阵

状态含义：

- **LOCAL-VERIFIED**：在本地 Linux 候选环境有可复现证据；
- **CI-VERIFIED**：公开 CI 的指定平台 wheel 已构建、安装并通过对应门禁；
- **CI-PENDING**：实现或测试入口存在，但对应平台/安装 wheel 尚未有本地或远程证据；
- **RELEASE-BLOCKER**：缺少该证据时不得发布“完整替代”或跨平台性能结论。

| 区域 | 当前状态 | 验收证据 |
|---|---|---|
| `dotenv` 顶层 import 与 `__all__` | LOCAL-VERIFIED | 完整上游 suite 的 API、main、CLI 导入 |
| 函数签名、默认值、参数顺序 | LOCAL-VERIFIED | 上游测试 + `docs/UPSTREAM-CONTRACT.md` |
| `DotEnv`、`dotenv_values`、`load_dotenv` | LOCAL-VERIFIED | `tests/test_main.py` |
| `find_dotenv`、zip import、交互/调试器发现 | LOCAL-VERIFIED | `test_main.py`、`test_is_interactive.py`、`test_zip_imports.py` |
| `get_key`、`set_key`、`unset_key`、原子 rewrite | LOCAL-VERIFIED | `test_main.py` |
| parser binding、行号、错误恢复、quotes/escapes/换行 | LOCAL-VERIFIED | `test_parser.py` |
| `${NAME}`、`${NAME:-default}`、override 顺序 | LOCAL-VERIFIED | `test_variables.py`、`test_main.py` |
| `os.environ` 修改、disabled flag、日志和异常 | LOCAL-VERIFIED | `test_main.py` 及差分门禁 |
| FIFO、权限、symlink、编码 | LOCAL-VERIFIED（受平台 skip 约束） | `test_fifo_dotenv.py`、`test_main.py` |
| CLI `list/set/get/unset/run`、输出/退出码 | LOCAL-VERIFIED | `test_cli.py` + 临时 console-script wrapper |
| `python -m dotenv` | LOCAL-VERIFIED | CLI 入口与上游 subprocess 测试 |
| IPython `%dotenv` | LOCAL-VERIFIED | 3 项上游 IPython 测试均实际执行 |
| Linux release wheel 安装后验证 | LOCAL-VERIFIED | fresh venv 仅安装候选 wheel；base import、CLI、完整上游 suite 通过 |
| macOS release wheel | CI-VERIFIED | CI #3：arm64 wheel、安装、CLI、219 个上游测试 |
| Windows release wheel | CI-VERIFIED | CI #3：x86-64 wheel、安装、CLI、169 passed / 50 平台 skip |
| 隔离 benchmark | LOCAL-VERIFIED（仅当前 Linux 数据） | 候选/Oracle 分进程、同 workload 原始数据 |

矩阵中的 LOCAL-VERIFIED 不表示“测试过之后所有未来变更仍兼容”；每个发布候选都要
重新执行 release gate。

## 3. API、CLI 和 IPython 约束

必须保持以下顶层导出：

```text
get_cli_string, load_dotenv, dotenv_values, get_key,
set_key, unset_key, find_dotenv, load_ipython_extension
```

同时必须提供 `dotenv.main`、`dotenv.parser`、`dotenv.variables`、`dotenv.cli`、
`dotenv.ipython`、`dotenv.__main__` 和 `dotenv.version`。具体类、签名、返回类型、
日志文字、异常和文件/环境副作用不在这里重复；以
[`UPSTREAM-CONTRACT.md`](UPSTREAM-CONTRACT.md) 为唯一详细契约。

CLI 的 `-f/--file`、`-q/--quote`、`-e/--export`、`--version`、`list`、`set`、`get`、
`unset`、`run` 必须保持上游参数解析、stdout/stderr、退出码和 command flag 透传。
IPython 必须提供 `%load_ext dotenv` 和 `%dotenv [PATH]`，包括 `-o`、`-v` 和找不到
文件时的行为。

## 4. 正式验收流程

### 4.1 环境隔离

候选与 Oracle 不能在同一 Python 环境共存：两者都会提供顶层 `dotenv` 包和 `dotenv`
命令。验收必须满足：

```text
Oracle 进程：python-dotenv==1.2.2 的 source/wheel
候选进程：  fast-dotenv-rs wheel 或本项目 python/ 源码
```

仓库提供的上游入口负责下载、校验和隔离：

```bash
python -m pip install "pytest>=8,<9" "click>=5"  # IPython gate 另装 ipython
bash scripts/run_upstream_full.sh
```

脚本必须确认候选 `dotenv.__file__` 位于本项目 `python/`，并让 CLI subprocess 使用
候选 console-script wrapper；任何导入 Oracle、官方测试 hash 不符或 pytest 失败都
返回非零。不能用 `-k`、删除测试或项目自定义 xfail 把失败变成通过。

### 4.2 通过条件

完整候选的通过条件是合取关系：

1. Rust `cargo test`、格式和 lint 通过；
2. 上游 1.2.2 全部测试收集并运行；只允许上游明确的操作系统/可选依赖 skip；
3. 无 IPython 时必须明示少 3 项；正式 Linux 本地记录必须包含已执行的 3 项 IPython 测试；
4. 候选与 Oracle 对返回类型、值、顺序、异常类型/文字、日志、环境快照、文件 bytes、
   权限、CLI stdout/stderr/退出码做差分，不能有未解释差异；
5. 从 release wheel 安装到 fresh venv 后重复 namespace、API、CLI 和上游门禁；
6. Linux、macOS、Windows 及项目声明的 Python 版本都有 CI wheel 证据；
7. 许可证、上游 BSD-3-Clause 通知和发行元数据可追溯。

## 5. Benchmark 规则

性能不是兼容性的替代品。benchmark 必须：

- 在两个独立子进程中运行 Oracle 与候选，父进程不先 import 任一 `dotenv`；
- 使用完全相同的输入、warmup、iterations、repeats 和 Python 版本；
- 先比较返回类型、ordered items 和结果，再计算中位数 speedup；
- 记录平台、架构、Python、输入字节数、workload、原始样本和是否 release wheel；
- 明确区分 stream 解析、文件 I/O、进程启动和真实应用启动；
- 没有 macOS/Windows 实测时，不输出跨平台性能结论；
- 不允许为了 speedup 删除日志、异常、文件副作用或兼容分支。

命令和当前 Linux 限制见 [`../BENCHMARK.md`](../BENCHMARK.md)。

## 6. 发布判定

当前判定：**RELEASE COMPLETE。** `0.1.0` 历史发布证据绑定
[workflow #31520894781](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31520894781)
及 [v0.1.0](https://github.com/lowmiaq-gmail/fast-dotenv-rs/releases/tag/v0.1.0)；该 Release
后续已转为 formal，但旧流水线通过 `[cli]` extra 安装，不能证明基础包 CLI。
`0.1.1` 已由 [workflow #31528136044](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31528136044)
从同一 immutable artifact set 在五个平台以普通安装方式复验，并在最后创建
[formal GitHub Release](https://github.com/lowmiaq-gmail/fast-dotenv-rs/releases/tag/v0.1.1)。
[发布后监控 #31528544319](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31528544319)
也已通过。
