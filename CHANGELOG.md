# Changelog

## 0.1.0 — pre-release

本版本已发布到 PyPI，并创建 GitHub pre-release。发行名为 `fast-dotenv-rs`；安装后
仍使用上游兼容的 `dotenv` import 和 `dotenv` CLI。

### 已完成

- 提供完整的 `dotenv` 顶层 API：`load_dotenv`、`dotenv_values`、`find_dotenv`、
  `get_key`、`set_key`、`unset_key`、`get_cli_string` 和 IPython 扩展入口；
- 提供 `dotenv.main`、`dotenv.parser`、`dotenv.variables`、`dotenv.cli`、
  `dotenv.ipython`、`dotenv.__main__` 和 `dotenv.version` 兼容模块；
- 覆盖 parser、变量插值、文件/stream、编码、FIFO、symlink、原子改写、日志、
  环境变量、副作用、CLI 和 IPython 的 `python-dotenv==1.2.2` 行为契约；
- 增加完整上游验收入口 `scripts/run_upstream_full.sh`，固定校验官方 sdist、测试
  文件来源和 SHA-256，并防止已安装 Oracle 混入候选测试；
- 增加候选/Oracle 进程隔离的 benchmark 规则，比较返回值和顺序后才计算 speedup；
- 保留 BSD-3-Clause 上游通知及项目 MIT 代码的许可证边界。

### 当前证据和限制

- Linux x86-64 / CPython 3.12 本地完整上游门禁：`218 passed, 1 skipped, 0 failed`；
- IPython 已安装，上游 IPython 模块的 3 个测试均实际执行；唯一 skip 为上游平台条件；
- 固定种子隔离差分通过 10,000 个随机案例，且 Oracle/Candidate 模块路径不同；
- Linux release wheel 在 fresh venv 中通过无 Click 基础导入、CLI 和完整上游套件；
- GitHub Actions CI #3 的 Linux Python 3.10/3.12、macOS arm64、Windows x86-64
  四个矩阵任务全部通过；macOS 为 219 passed，Windows 为 169 passed / 50 平台 skip；
- 正式发布流水线构建并审计了 Linux x86-64、Linux ARM64、macOS Intel、macOS
  Apple Silicon、Windows x86-64 五个 wheel 和一个 sdist；
- Trusted Publishing 上传成功，五个平台随后从公共 PyPI 回装并通过完整上游套件；
- GitHub pre-release 包含相同的六个发布产物和 `SHA256SUMS`；
- `python-dotenv==1.2.2` 与本项目不能在同一个环境安装，必须用独立 Oracle 环境做
  对比，否则顶层 `dotenv` 包和 CLI 会相互覆盖。

### 发布证据

- PyPI：<https://pypi.org/project/fast-dotenv-rs/0.1.0/>
- GitHub Release：<https://github.com/lowmiaq-gmail/fast-dotenv-rs/releases/tag/v0.1.0>
- 发布流水线：<https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31520894781>
