# python-dotenv 1.2.2 完整兼容契约

> 本文件是 `fast-dotenv-rs` 完整 drop-in 替代品的行为基线。
> Source of truth 是 `python-dotenv==1.2.2` 的 sdist（项目：
> `theskumar/python-dotenv`，tag：`v1.2.2`），而不是仅凭 README 推测的 API。
> 本文件只记录契约，暂不声明当前 Rust 实现已经满足这些契约。

## 1. 完整替代的边界

完整替代必须同时满足以下三个层面：

1. `from dotenv import ...` 的导出符号、函数签名、返回类型和异常行为；
2. `dotenv.main`、`dotenv.parser`、`dotenv.variables`、`dotenv.cli`、
   `dotenv.ipython`、`dotenv.__main__` 等可被用户或测试直接导入的模块；
3. `dotenv` CLI、`python -m dotenv`、IPython `%dotenv` 扩展，以及文件、FIFO、
   `os.environ`、日志和原子改写等副作用。

兼容目标不是“能解析常见的 `KEY=value`”，而是对 1.2.2 的可观察行为逐项一致。
解析器的错误恢复、奇怪输入、顺序、日志文字和文件权限同样属于契约。

基线包信息：

| 项目 | 值 |
|---|---|
| 包名/版本 | `python-dotenv==1.2.2` |
| Python 要求 | `>=3.10` |
| 许可证 | BSD-3-Clause |
| CLI extra | `click>=5.0` |
| 控制台入口 | `dotenv = dotenv.__main__:cli` |
| `__version__` | `"1.2.2"` |

## 2. 模块和公开 API

### 2.1 `dotenv`（`dotenv/__init__.py`）

`__all__` 必须精确包含以下 8 个名字（顺序也保持一致）：

```python
[
    "get_cli_string", "load_dotenv", "dotenv_values", "get_key",
    "set_key", "unset_key", "find_dotenv", "load_ipython_extension",
]
```

```python
get_cli_string(
    path: Optional[str] = None,
    action: Optional[str] = None,
    key: Optional[str] = None,
    value: Optional[str] = None,
    quote: Optional[str] = None,
) -> str

load_dotenv(
    dotenv_path: Optional[StrPath] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    override: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> bool

dotenv_values(
    dotenv_path: Optional[StrPath] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> Dict[str, Optional[str]]

get_key(
    dotenv_path: StrPath,
    key_to_get: str,
    encoding: Optional[str] = "utf-8",
) -> Optional[str]

set_key(
    dotenv_path: StrPath,
    key_to_set: str,
    value_to_set: str,
    quote_mode: str = "always",
    export: bool = False,
    encoding: Optional[str] = "utf-8",
    follow_symlinks: bool = False,
) -> Tuple[Optional[bool], str, str]

unset_key(
    dotenv_path: StrPath,
    key_to_unset: str,
    quote_mode: str = "always",
    encoding: Optional[str] = "utf-8",
    follow_symlinks: bool = False,
) -> Tuple[Optional[bool], str]

find_dotenv(
    filename: str = ".env",
    raise_error_if_not_found: bool = False,
    usecwd: bool = False,
) -> str

load_ipython_extension(ipython: Any) -> None
```

`StrPath = Union[str, os.PathLike[str]]`。`dotenv_values` 实际返回保持插入顺序
的 `collections.OrderedDict`（其标注为 `Dict`）；`KEY` 的值是 `None`，`KEY=` 的值
是空字符串。`get_cli_string` 生成一个 shell 命令字符串：起始为 `dotenv`，按
`-q`、`-f`、action/key/value 顺序追加；含空格的 value 用双引号包裹，不做 shell
转义。空值参数会被省略。

### 2.2 `dotenv.main`

这是主要行为模块。以下名字虽然以下划线开头的辅助函数不是 `__all__`，但官方
测试和兼容实现会依赖它们的语义；实现时不得把它们错误地当成不存在。

```python
StrPath = Union[str, os.PathLike[str]]

class DotEnv:
    def __init__(
        self,
        dotenv_path: Optional[StrPath],
        stream: Optional[IO[str]] = None,
        verbose: bool = False,
        encoding: Optional[str] = None,
        interpolate: bool = True,
        override: bool = True,
    ) -> None: ...

    def dict(self) -> Dict[str, Optional[str]]: ...
    def parse(self) -> Iterator[Tuple[str, Optional[str]]]: ...
    def set_as_environment_variables(self) -> bool: ...
    def get(self, key: str) -> Optional[str]: ...
    def _get_stream(self) -> Iterator[IO[str]]: ...  # context manager

def with_warn_for_invalid_lines(
    mappings: Iterator[Binding],
) -> Iterator[Binding]: ...

def get_key(dotenv_path: StrPath, key_to_get: str,
            encoding: Optional[str] = "utf-8") -> Optional[str]: ...

def rewrite(path: StrPath, encoding: Optional[str],
            follow_symlinks: bool = False
            ) -> Iterator[Tuple[IO[str], IO[str]]]: ...  # context manager

def set_key(dotenv_path: StrPath, key_to_set: str, value_to_set: str,
            quote_mode: str = "always", export: bool = False,
            encoding: Optional[str] = "utf-8",
            follow_symlinks: bool = False
            ) -> Tuple[Optional[bool], str, str]: ...

def unset_key(dotenv_path: StrPath, key_to_unset: str,
              quote_mode: str = "always", encoding: Optional[str] = "utf-8",
              follow_symlinks: bool = False
              ) -> Tuple[Optional[bool], str]: ...

def resolve_variables(values: Iterable[Tuple[str, Optional[str]]],
                      override: bool
                      ) -> Mapping[str, Optional[str]]: ...

def find_dotenv(filename: str = ".env",
                raise_error_if_not_found: bool = False,
                usecwd: bool = False) -> str: ...

def load_dotenv(dotenv_path: Optional[StrPath] = None,
                stream: Optional[IO[str]] = None,
                verbose: bool = False, override: bool = False,
                interpolate: bool = True,
                encoding: Optional[str] = "utf-8") -> bool: ...

def dotenv_values(dotenv_path: Optional[StrPath] = None,
                  stream: Optional[IO[str]] = None,
                  verbose: bool = False, interpolate: bool = True,
                  encoding: Optional[str] = "utf-8"
                  ) -> Dict[str, Optional[str]]: ...

def _load_dotenv_disabled() -> bool: ...
def _walk_to_root(path: str) -> Iterator[str]: ...
def _is_file_or_fifo(path: StrPath) -> bool: ...
```

`DotEnv` 构造后公开属性是 `dotenv_path`, `stream`, `verbose`, `encoding`,
`interpolate`, `override`，以及缓存属性 `_dict`。`dict()` 首次解析后缓存结果；
`parse()` 逐条产生 `(key, value)`，忽略注释、空行和无 key 的无效 binding；
`set_as_environment_variables()` 遇空 mapping 返回 `False`，否则设置非-`None` 值
并返回 `True`；`override=False` 时不覆盖已有环境变量。`get()` 未找到时返回
`None`，`verbose=True` 记录 warning。

`load_dotenv()` 在两项输入均为 `None` 时调用 `find_dotenv()`；默认不覆盖已有环境
变量；`interpolate` 控制 `${...}` 展开。若 `PYTHON_DOTENV_DISABLED` 的值
（大小写折叠）是 `1,true,t,yes,y`，直接记录 debug 并返回 `False`，不读取文件或
stream。它改变 `os.environ`，但不删除变量。

`dotenv_values()` 默认 `override=True` 解析变量且不改变 `os.environ`；路径和 stream
均提供时，存在的普通文件/FIFO优先使用路径，否则使用 stream。缺失输入返回空的
`OrderedDict`；`verbose=True` 记录缺失文件 info。读取错误、编码错误和 stream 的
异常向调用者传播。

`find_dotenv()` 从调用脚本目录（交互式、debugger、frozen 或 `usecwd=True` 时从
当前工作目录）逐级向根目录搜索普通文件或 FIFO。起始路径不存在时
`_walk_to_root` 抛 `IOError("Starting path not found")`；未找到时默认返回 `""`，
`raise_error_if_not_found=True` 抛 `IOError("File not found")`。脚本目录推导需兼容
zip import、`__main__` 没有 `__file__` 和被删除的 cwd。

`set_key()` 使用临时文件后 `os.replace` 原子替换；默认不跟随 symlink，
`follow_symlinks=True` 才先 `realpath`。支持 `quote_mode`=`always|auto|never`，
其他值抛 `ValueError("Unknown quote_mode: ...")`；`auto` 在 value 非字母数字时加
单引号；单引号自身写成 `\\'`；`export=True` 写 `export KEY=value`。返回
`(True, key_to_set, value_to_set)`，新文件可被创建，存在的普通文件 mode 必须保留。

`unset_key()` 对不存在路径或不存在的 key 记录 warning，并返回 `(None, key)`；成功
返回 `(True, key)`。保留其余原始文本（注释、空白、换行和无效行），同样使用原子
rewrite、默认不跟随 symlink。

### 2.3 `dotenv.parser`

```python
def make_regex(string: str, extra_flags: int = 0) -> Pattern[str]: ...

class Original(NamedTuple):
    string: str
    line: int

class Binding(NamedTuple):
    key: Optional[str]
    value: Optional[str]
    original: Original
    error: bool

class Position:
    def __init__(self, chars: int, line: int) -> None: ...
    @classmethod
    def start(cls) -> "Position": ...
    def set(self, other: "Position") -> None: ...
    def advance(self, string: str) -> None: ...

class Error(Exception): ...

class Reader:
    def __init__(self, stream: IO[str]) -> None: ...
    def has_next(self) -> bool: ...
    def set_mark(self) -> None: ...
    def get_marked(self) -> Original: ...
    def peek(self, count: int) -> str: ...
    def read(self, count: int) -> str: ...
    def read_regex(self, regex: Pattern[str]) -> Sequence[str]: ...

def decode_escapes(regex: Pattern[str], string: str) -> str: ...
def parse_key(reader: Reader) -> Optional[str]: ...
def parse_unquoted_value(reader: Reader) -> str: ...
def parse_value(reader: Reader) -> str: ...
def parse_binding(reader: Reader) -> Binding: ...
def parse_stream(stream: IO[str]) -> Iterator[Binding]: ...
```

`Reader` 一次性读取整个 text stream，位置以字符数和物理行号计算；`read` 或
`read_regex` 无匹配时抛内部 `Error`，`parse_binding` 捕获它并消费到行尾，返回
`Binding(None, None, original, True)`，解析继续而不是 fail-fast。

语法必须保留这些 1.2.2 细节：空白/注释、可选 `export`、未引号或单引号 key、
未引号/单引号/双引号 value、带引号多行 value、LF/CRLF/CR；未引号 value 中只有
前置空白的 `#` 才开始 comment（`a=b#c` 中 `#c` 是值）；single quote 仅解码
`\\`、`\\'`，double quote 解码 `\\`、`\\'`、`\\"`、`\\a`、`\\b`、`\\f`、`\\n`、
`\\r`、`\\t`、`\\v`。非法行由 `with_warn_for_invalid_lines` 按原始起始行号记录
warning。

### 2.4 `dotenv.variables`

```python
class Atom(metaclass=ABCMeta):
    def __ne__(self, other: object) -> bool: ...
    @abstractmethod
    def resolve(self, env: Mapping[str, Optional[str]]) -> str: ...

class Literal(Atom):
    def __init__(self, value: str) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
    def resolve(self, env: Mapping[str, Optional[str]]) -> str: ...

class Variable(Atom):
    def __init__(self, name: str, default: Optional[str]) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
    def resolve(self, env: Mapping[str, Optional[str]]) -> str: ...

def parse_variables(value: str) -> Iterator[Atom]: ...
```

仅识别 `${NAME}` 和 `${NAME:-default}`，bare `$NAME` 保持 literal。缺失变量默认
为空字符串；`None` 也解析为空字符串。`parse_variables` 返回 Literal/Variable
对象的 iterator，保留片段顺序、对象 equality/repr/hash 行为。

### 2.5 `dotenv.cli` 与 `dotenv.__main__`

CLI 依赖 `click>=5.0`，入口是 `dotenv.__main__:cli`，而 `__main__.py` 也必须支持
`python -m dotenv`。

```python
def enumerate_env() -> Optional[str]: ...
def stream_file(path: os.PathLike) -> Iterator[IO[str]]: ...  # context manager
def run_command(command: List[str], env: Dict[str, str]) -> None: ...
```

`cli` 是 Click Group（不是普通函数 API），全局选项为：

| 选项 | 默认值 | 作用 |
|---|---|---|
| `-f/--file` | 当前目录 `.env` | env 文件路径 |
| `-q/--quote` | `always` | `always`, `never`, `auto` |
| `-e/--export` | `False` | set 时写 `export` |
| `--version` | `1.2.2` | 打印版本 |

子命令及行为：

| 子命令 | 参数 | 成功输出/副作用 | 失败行为 |
|---|---|---|---|
| `list` | `--format simple\|json\|shell\|export` | 读取并列出键；json 为排序、2 空格缩进；shell/export 用 `shlex.quote` | 文件打开失败 stderr `Error opening env file: ...`，退出 2 |
| `set` | `KEY VALUE` | 调 `set_key`，输出 `KEY=VALUE` | 失败退出 1；路径/权限错误传播为 CLI 错误 |
| `get` | `KEY` | 存在且 truthy 时输出 value | 不存在、空值或文件错误退出 1/2 |
| `unset` | `KEY` | 调 `unset_key`，输出 `Successfully removed KEY` | key/文件不存在退出 1 |
| `run` | `COMMAND [ARGS...]`、`--override/--no-override` | 将 dotenv 值合并到环境后替换当前进程执行 | 缺 command 输出 `No command given.` 退出 1；文件不存在为 Click 参数错误 |

`run` 必须允许 command 自身的 flags（`allow_extra_args=True`、
`allow_interspersed_args=False`、`ignore_unknown_options=True`），默认 override；
Unix 使用 `os.execvpe`，Windows 使用 `Popen` 后以子进程 return code 退出。默认不跟随
symlink 的说明也属于 CLI 行为。`stream_file` 打开失败打印 stderr 并 `sys.exit(2)`。

CLI 兼容还要求 `dotenv --help`、`dotenv --version` 的 Click 参数解析、退出码和
错误格式可被自动化脚本依赖。

### 2.6 `dotenv.ipython`

```python
class IPythonDotEnv(Magics):
    def dotenv(self, line) -> None: ...

def load_ipython_extension(ipython) -> None: ...
```

加载 `%load_ext dotenv` 后注册 `IPythonDotEnv`，提供 `%dotenv [PATH]` magic。参数为
`-o/--override`（覆盖已有变量）、`-v/--verbose`（提高 verbosity）和可选 path，
默认 `.env`。它先调用 `find_dotenv(path, True, True)`，找不到时打印
`cannot find .env file` 并返回；找到后调用 `load_dotenv(..., override=..., verbose=...)`。
缺少 IPython 依赖时，安装包本身仍可使用，只有测试/扩展加载应按上游方式失败或跳过。

### 2.7 `dotenv.version`

Oracle 的 `dotenv.version.__version__` 为 `1.2.2`。候选发行版返回自身版本
`0.1.0`，这是为区分实现而保留的唯一显式版本标识差异；API、CLI 和行为契约仍冻结到
Oracle 1.2.2。

## 3. 副作用、日志和异常契约

| 场景 | 可观察行为 |
|---|---|
| `load_dotenv` 禁用 | `PYTHON_DOTENV_DISABLED` 为 `1/true/t/yes/y`（casefold）时 debug：`python-dotenv: .env loading disabled by PYTHON_DOTENV_DISABLED environment variable`，返回 `False` |
| 缺失文件且 verbose | info：`python-dotenv could not find configuration file <path or .env>.` |
| 非法 binding | warning：`python-dotenv could not parse statement starting at line <N>`，继续解析 |
| `DotEnv.get` 未找到 | verbose 时 warning：`Key <key> not found in <dotenv_path>.` |
| `unset_key` 文件不存在 | warning：`Can't delete from <path> - it doesn't exist.`，返回 `(None,key)` |
| `unset_key` key 不存在 | warning：`Key <key> not removed from <path> - key doesn't exist.`，返回 `(None,key)` |
| `find_dotenv` 起始路径不存在 | `IOError("Starting path not found")` |
| `find_dotenv` 未找到且 raise | `IOError("File not found")` |
| `set_key` 非法 quote | `ValueError("Unknown quote_mode: <mode>")` |
| 文件/编码/stream 失败 | 原始 `OSError`、`UnicodeError`、stream 异常传播；不得吞掉或改成空结果 |
| `PYTHON_DOTENV_DISABLED` | 只影响 `load_dotenv`，不影响 `dotenv_values`、`get_key`、CLI list/get |
| 环境变量 | `dotenv_values` 不修改 `os.environ`；`load_dotenv` 只写入有 value 的键，不删除键；`override=False` 保留原值 |
| 文件改写 | `set_key`/`unset_key` 临时文件 + `os.replace`；成功保留普通文件 mode，失败清理临时文件；默认不跟随 symlink |

变量解析是逐条顺序的：`override=True` 时文件中此前已经解析的 key 覆盖 process
environment；`override=False` 时 process environment 优先。重复 key 更新 value
但保留首次插入位置。所有返回 mapping 的顺序必须稳定。

## 4. 上游权威测试与数量

测试来源：`python-dotenv-1.2.2` sdist 的 `tests/`；不要只复制“看起来相关”的少量
文件。下面的 SHA-256 用于确认测试没有被悄悄改动。

| 文件 | 原始 test 函数 | pytest 收集数（无 IPython） | 覆盖范围 | SHA-256 |
|---|---:|---:|---|---|
| `tests/test_cli.py` | 25 | 39 | list/get/set/unset/run、quote/export、路径、退出码 | `8f4f0871366080f813baf86df6c346a23c0a5543e718a3684d34560438afafae` |
| `tests/test_fifo_dotenv.py` | 1 | 1 | FIFO 输入（Unix） | `b69ecca75f9eb3969aa2cc2d49f66006cccae02da472805a3b3ad4c9fca8f8de` |
| `tests/test_ipython.py` | 3 | 0* | `%dotenv`；依赖 IPython | `2d61ac43a07ad30bd5f0b23a8d30785bf1bb07f2238bc9ef344f65a181c85386` |
| `tests/test_is_interactive.py` | 10 | 10 | `find_dotenv` 交互/脚本/debugger 分支 | `2d4a6a5a4501bbd6c2860b39abeb9d5201a2de3d110347f74236098aa72f2a18` |
| `tests/test_main.py` | 41 | 114 | main API、改写、环境、插值、编码、symlink | `4e638cc1ed2b9129b61ccdbfb89980bb79edbe08556659af67656365ed2a023e` |
| `tests/test_parser.py` | 1 | 43 | 全部 parser grammar/错误恢复/换行/escape | `42bab2235b43f5fe9283b3b16e7c099a16f137ec9f0b5afefd4c164f108eb130` |
| `tests/test_utils.py` | 1 | 1 | `get_cli_string` | `82e06b9819adbc846b84717f9cc47ffff2dc99c77ebb0a22d93026326eac78a3` |
| `tests/test_variables.py` | 1 | 6 | `Literal`/`Variable`/变量 tokenizer | `facea37ceaca30b761c2128fa754ec32c1e50333f2ac1776f7f8063018aaa6fc` |
| `tests/test_zip_imports.py` | 2 | 2 | zip import 和无 env 文件时发现逻辑 | `9224bd859309409c62848bac6564eec0793aa6dffa091c9965ec6c4644a8ef04` |
| `tests/test_lib.py` | 0 | 0 | CLI subprocess helpers（被其他测试调用） | `f75073c7317f7cda985b94531774578056519bf8dcb91aa7f3c60a7cf8872199` |

上述环境下核心 suite 总计 **216 collected tests**。`test_ipython.py` 使用
`pytest.importorskip("IPython")`；安装 IPython 后应额外收集并运行 3 个测试，因此
完整依赖满足时总量是 **219 tests**（Windows 上其中若干 case 按上游 `skipif` 跳过）。
此外，`conftest.py` 的 `cli` 隔离文件系统 fixture 和 `dotenv_path` 空文件 fixture
也是测试契约的一部分，SHA-256 为
`1cc31c9f8e8b5e076780d7469c8f35ff8088e37a25be0bc7e07b68e593beb443`。

### 完整替代的测试门禁

1. 在 Oracle 环境运行上述原始 suite，并记录平台、Python、Click、IPython 版本。
2. 将同一 suite 的 import 目标切换为候选 `dotenv` 命名空间；不能只运行自写 smoke
   tests，也不能把失败测试删除或标记成预期失败。
3. 无 IPython 时必须明确记录 `216`；带 IPython 时必须达到 `219` collected，除去
   上游明确的 platform skips。
4. 另行执行 candidate-vs-Oracle 差分测试，比较值、类型、顺序、异常类型/文字、日志
   level/文字、环境快照、文件内容/换行/权限、CLI stdout/stderr/退出码。
5. README 的“drop-in/完整替代”只可在这套 gate 全绿且 release wheel 上复测后使用。
   其他 import 别名或少量自写测试不能作为完整替代的证据。

## 5. 复用和版本冻结规则

实现可复用既有 Rust parser，但 Python facade 必须补齐 `dotenv` 命名空间和以上所有
模块。不得把 `dotenv` 与原 Oracle 同时安装时的 import 偶然性当作兼容性证据。

本契约冻结到 `1.2.2`。上游升级时必须重新获取 sdist、重新核对模块/签名/测试数量和
hash，生成新的版本化契约与差分报告；不得静默跟踪上游 `main`。
