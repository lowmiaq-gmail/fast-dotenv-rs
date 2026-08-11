# 项目地图

这是仓库级导航入口，服务两类读者：

- 人：快速知道项目有什么、每份文档是干什么的、现在该看哪里。
- Agent：先缩小修改范围，再进入代码，不要全仓库无差别扫描。

详细行为属于源码、测试或对应 Source of Truth；本地图不复制实现细节。

## 先从哪里开始

| 你想知道什么 | 先看哪里 |
|---|---|
| 现在做到哪、下一步是什么 | `PROGRESS.md` |
| 项目为什么做、范围是什么 | `PROJECT.md` |
| Agent / 贡献者应该怎么工作 | `AGENTS.md` |
| 用户怎么安装和使用 | `README.md` / `README.zh-CN.md` |
| 上游行为到底要兼容什么 | `docs/UPSTREAM-CONTRACT.md` |
| 怎么证明兼容 | `docs/COMPATIBILITY.md` |
| 发布/推广进行到哪 | `docs/LAUNCH-STATUS.md` |
| 性能到底验证了什么 | `BENCHMARK.md` |

## 仓库树与职责

```text
fast-dotenv-rs/
├── PROJECT.md              # 项目目标、范围、成功标准
├── PROGRESS.md             # 当前进度、下一步、阻塞
├── PROJECT-MAP.md          # 人/Agent 的项目地图（本文件）
├── AGENTS.md               # 全仓库 Agent / 协作规则
├── README*.md              # 对外安装、使用、验收入口
├── BENCHMARK.md            # 性能证据及边界
├── FULL-RELEASE-REPORT.md  # 发布阶段证据报告；注意其时点
├── src/                    # Rust parser / interpolation / PyO3 核心
├── python/dotenv/          # Python drop-in 兼容层
├── tests/                  # 候选契约、smoke、benchmark
├── scripts/                # 可复现验证与发布辅助脚本
├── docs/                   # 行为契约、兼容性、发布状态和历史设计资料
│   └── AGENTS.md           # docs 局部文档地图与维护规则
├── reusable/               # 从首个库提取的可复用重写资产
├── assets/                 # README / social preview 等静态资产
├── licenses/               # 第三方许可证材料
└── .github/workflows/      # CI、wheel、release / monitoring 自动化
```

## 代码地图

### `src/`

- `lib.rs`：最小 PyO3 模块注册和 Rust/Python 数据边界。
- `parser.rs`：纯 Rust parser、interpolation engine 及 Rust unit tests。

如果修改 Rust 热路径，先看这里；不要把 Python 特有副作用逻辑硬搬进 Rust。

### `python/dotenv/`

- `main.py`：文件发现、环境变量 mutation、atomic rewrite、高层公开 API。
- `parser.py`：上游兼容 parser data model / compatibility layer。
- `variables.py`：上游兼容 interpolation objects / tokenization。
- `cli.py`、`__main__.py`：Click CLI、console/module entry point。
- `ipython.py`：`%dotenv` extension。

如果修改用户可观察的 Python 行为、CLI、IPython 或文件/环境副作用，主要从这里进入。

### `tests/`

- `test_dropin_contract.py`：namespace、signature、return contract、logging、environment、file mutation、CLI 等候选契约。
- `benchmark.py`：Oracle / candidate 隔离进程 benchmark，先做语义校验再计算 speedup。

### `scripts/`

- `run_upstream_full.sh`：固定 1.2.2 upstream source，并执行完整官方测试门禁。
- `run_differential.py`：deterministic、isolated Oracle / candidate differential gate。
- 其他脚本：按文件名和调用者判断发布、报告、验证职责；增加脚本前先检查是否已有等价能力。

### `.github/workflows/`

CI、wheel build、release、launch monitoring 等自动化入口。发布状态不要只看 workflow 文件本身，要看实际 run / release / public install 证据。

## 文档地图

### 项目级入口

| 文件 | 干什么 | 不负责什么 |
|---|---|---|
| `PROJECT.md` | 为什么做、范围、非目标、成功标准、SoT | 不记录流水账进度 |
| `PROGRESS.md` | 当前状态、最近完成、下一步、阻塞 | 不保存全部历史 |
| `PROJECT-MAP.md` | 目录、文档、修改路由 | 不复制源码 |
| `AGENTS.md` | Agent 读取顺序、执行与验证规则 | 不复制领域文档 |
| `README.md` / `README.zh-CN.md` | 对外安装、使用、CLI/IPython、快速验收 | 不作为内部项目进度 SoT |

### `docs/`

更细的文档职责和更新规则看 `docs/AGENTS.md`。

核心关系：

```text
UPSTREAM-CONTRACT.md
  └─ 定义：要兼容什么

COMPATIBILITY.md
  └─ 定义：怎么证明兼容

LAUNCH-STATUS.md
  └─ 定义：发布 / 推广领域当前状态

FULL-REWRITE-PLAN.md
  └─ 历史：当初怎么实施重写，不代表现在做到哪
```

其他 `API-CLI-PLAN.md`、`PARSER-GAP-PLAN.md`、`REUSE-AUDIT.md`、`PUBLISHING.md`、`RELEASE-NOTES-*`、`LAUNCH-SEO.md` 都是专项或历史资料，不应越级成为整个项目的当前进度入口。

## 常见修改路由

| 我要改什么 | 首先去哪里 | 同时检查 |
|---|---|---|
| Rust parser / interpolation | `src/` | parser / upstream / differential tests |
| `load_dotenv`、find/get/set/unset、文件与环境行为 | `python/dotenv/main.py` | `UPSTREAM-CONTRACT.md`、完整上游测试 |
| CLI | `python/dotenv/cli.py`、`__main__.py` | CLI upstream tests、打包 entry point |
| IPython | `python/dotenv/ipython.py` | upstream IPython tests |
| 公共兼容性承诺 | `docs/UPSTREAM-CONTRACT.md` | `COMPATIBILITY.md`、tests |
| 验收门禁 | `docs/COMPATIBILITY.md` / `scripts/` / CI | `AGENTS.md` 的验证要求 |
| 当前项目进度 | `PROGRESS.md` | 相关领域 SoT / 运行证据 |
| 发布状态 | `docs/LAUNCH-STATUS.md` | `PROGRESS.md`、实际 GitHub/PyPI/CI 证据 |
| 项目模块边界变化 | 源码 + `PROJECT-MAP.md` | `PROJECT.md`、相关测试 |

## 局部地图 / AGENTS 规则

不要给每个目录机械创建 `AGENTS.md` 或 `MAP.md`。

只有当目录出现多个独立职责、文档/文件数量明显增加，或者根地图已经不足以指导修改时，才增加局部地图。

当前：

- `docs/`：职责多、文档多，使用 `docs/AGENTS.md`。
- `src/`：结构简单，不需要局部 AGENTS。
- `python/dotenv/`：虽然文件较多，但职责在本地图已能明确导航，暂不额外增加；后续复杂度上升再拆。

## 地图维护规则

- 新增/删除核心目录或改变模块职责时更新本文件。
- 不要求每增加一个普通文件都更新地图。
- 如果地图与实际代码冲突，以实际代码为准，并修复地图漂移。