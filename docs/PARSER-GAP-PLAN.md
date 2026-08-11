# python-dotenv 1.2.2 解析器差距与完整替代计划

文档版本：v1.0
基线：`python-dotenv==1.2.2`，tag `v1.2.2`。通过路径：`src/dotenv/parser.py`、`src/dotenv/variables.py`、`src/dotenv/main.py` 以及 `tests/test_parser.py`、`tests/test_variables.py`。
状态：已实现并通过完整上游套件与隔离差分门禁。本文保留为 parser 设计与验收记录。

目标：将 `fast-dotenv-rs` 解析器扩展为可以支撑完整 `python-dotenv` 替代品的兼容性底座。

本文件是实现计划和验收契约，不是实现代码。其他 Agent 正在并行处理完整 API、发布和仓库工作；本文件只负责解析器/变量解析边界，避免多个 Agent 同时改动 `src/parser.rs` 造成冲突。

## 1. 结论先行

当前 Rust 代码的 `parse_and_resolve()` 能覆盖一部分 `dotenv_values()` 常见输入，但它把解析、错误丢弃、行切分、变量解析、重复键折叠混在一个最终结果函数中：

```text
输入文本
  -> physical_lines（丢失原始行终止符）
  -> parse_binding（只保留成功的 key/value）
  -> interpolate_value（手写扫描）
  -> 重复键折叠
  -> Vec<(String, Option<String>)>
```

上游的真实契约是两层：

```text
Reader/Position
  -> parse_stream() -> Iterator[Binding]
                         ├─ key/value
                         ├─ Original(string, line)
                         └─ error

main.py
  -> 过滤 Binding.key is not None
  -> 对 error 记录 warning
  -> resolve_variables(raw_values, override)
  -> OrderedDict / load / get / set / unset 等 API
```

完整替代的最低架构要求：

1. Rust 核心必须先产生**逐条 Binding**，不能直接只返回折叠后的 map。
2. `Original.string` 必须保留上游看到的原始片段，包括原始 `CR`、`LF`、`CRLF`、多行内容和末尾换行；否则 `set_key()`、`unset_key()` 无法保持文件内容。
3. Rust 负责确定性、CPU 密集的扫描、语法、转义和变量 token 化；Python facade 负责 Python 文件/stream/异常/logging/环境变量/`OrderedDict`/环境写回契约。
4. 任何“更宽松”或“更聪明”的解析行为都不能直接视为兼容。上游奇怪行为也是兼容性的一部分。

## 2. Source of Truth 与当前实现边界

冻结的上游文件：

- [`parser.py` v1.2.2](https://raw.githubusercontent.com/theskumar/python-dotenv/v1.2.2/src/dotenv/parser.py)
- [`variables.py` v1.2.2](https://raw.githubusercontent.com/theskumar/python-dotenv/v1.2.2/src/dotenv/variables.py)
- [`main.py` v1.2.2](https://raw.githubusercontent.com/theskumar/python-dotenv/v1.2.2/src/dotenv/main.py)
- [`tests/test_parser.py` v1.2.2](https://raw.githubusercontent.com/theskumar/python-dotenv/v1.2.2/tests/test_parser.py)
- [`tests/test_variables.py` v1.2.2](https://raw.githubusercontent.com/theskumar/python-dotenv/v1.2.2/tests/test_variables.py)

当前实现事实（以本仓库 `src/parser.rs`、`src/lib.rs` 和 `python/dotenv/` 为准）：

- Rust 导出只有 `parse_text(text, interpolate, environment)`，返回 `Vec<(String, Option<String>)>`。
- 没有导出的 Binding/Original/error/line 结构。
- `physical_lines()` 将 `CR`、`CRLF` 归一为逻辑换行，不能保留 `Original.string`。
- 空行、注释、非法行被直接丢弃，Python facade 没有上游的 invalid-line warning。
- facade 目前只导出 `dotenv_values()`；没有 `load_dotenv()`、`find_dotenv()`、`get_key()`、`set_key()`、`unset_key()`、CLI 和 IPython 入口。
- facade 的默认 `.env` 查找已由完整上游 `find_dotenv()` 行为覆盖。
- 当前功能测试覆盖的是最终 `dotenv_values()` 结果，不足以证明逐条 parser 契约。

## 3. 目标职责划分

| 能力 | 目标实现位置 | 原因 | 禁止的偷懒方式 |
|---|---|---|---|
| Reader、位置推进、物理行/换行识别 | Rust | 解析热点；需同时保留源片段和起始行 | 先 `split('\n')` 再猜原文 |
| `Binding(key, value, original, error)` | Rust 内部结构；必要字段通过测试 hook 暴露 | 语法解析的完整中间结果 | 只返回 map |
| 逐条 parse_stream 顺序 | Rust | 与上游迭代顺序及恢复点一致 | 遇错直接终止 |
| key/value/quote/comment/export 语法 | Rust | 确定性 CPU 热路径 | 用 Python 正则作为生产 parser |
| 转义解码 | Rust | 避免 Python 循环；语义必须与上游白名单一致 | 使用 Rust 通用 `unescape` 猜规则 |
| `${...}` token 化及单个变量 resolve | Rust | 可测试、可复用、避免字符串扫描开销 | 扩展为未定义的 `$NAME` 语法 |
| `parse_variables()` 的 Python 类对象（若完整 API 需要） | Python facade 或兼容层 | 上游类不是主公开 API；需要先核对调用者 | 无证据就宣称公开兼容 |
| warning logger、日志文案、日志级别 | Python facade | 必须使用 Python logging 体系 | Rust stderr/println |
| stream.read()、非文本 stream 类型错误 | Python facade | Python 对象协议和异常类型属于 facade 契约 | Rust 接收未知 Python 对象 |
| 文件打开、encoding、PathLike | Python facade | Python IO/异常/平台语义 | Rust 自行复制 Python open 语义 |
| FIFO 检测、打开和阻塞行为 | Python facade + OS 检测；Rust 只解析读取文本 | `main.py` 的 `_is_file_or_fifo()` 是 API 行为 | 将 FIFO 当不存在文件 |
| `os.environ` 快照、override 规则、环境写回 | Python facade | 进程全局状态必须显式可控 | Rust 隐式读取进程环境 |
| `OrderedDict`、重复键折叠 | Python facade（或 Rust 保序 pairs） | 返回类型/顺序是 Python API 契约 | 用无序 HashMap 直接返回 |
| find_dotenv 的调用栈/交互/debugger/zip/frozen 规则 | Python facade | 完全依赖 Python runtime | 以当前 cwd fallback 冒充完整兼容 |
| set/unset 的原文重写、symlink、mode | Python facade；依赖 Binding.original | 文件保真和安全策略属于上层 | 重新序列化整个 AST |

## 4. 解析语法逐项差距

下表的“验收 fixture”要求同时运行：

1. 上游 `parse_stream(StringIO(text))`；
2. Rust parser debug/test hook；
3. 对外 `dotenv_values(stream=StringIO(text))`；
4. 对需要写文件的场景，再运行 `set_key`/`unset_key`。

比较 Binding 时必须比较 `key`、`value`、`error`、`original.string`、`original.line`；比较最终 API 时比较类型、顺序、值、异常和日志。

| 类别 | python-dotenv 1.2.2 语义 | 当前实现 | 目标归属 | 精确验收 |
|---|---|---|---|---|
| 空输入 | `parse_stream("") == []` | 结果为空，表面一致 | Rust | `test_parse_empty` |
| 空白/空行 | 空行会产出 `Binding(None,None,error=False)`，原文和换行属于 binding；最终 dict 过滤掉 | 空行直接丢弃 | Rust | `"\n\n"`：1 条 binding，`Original.string="\n\n"`，`line=1`；`dotenv_values` 仍为 `{}` |
| 注释 | `# a=b` 是非错误 binding，原文保留 | 丢弃 | Rust + facade 过滤 | `# a=b\nA=1`：comment binding 后 A line=2，verbose 不告警 |
| unquoted key | `([^=\#\s]+)`；key 可包含 `[`、`%`、`$` 等 | 基本一致 | Rust | `a=b`、`[=b`、`uglyKey[%$=...` |
| single-quoted key | 只支持 `'([^']+)'`，去掉引号 | 基本支持 | Rust | `"'a'=b"` => key `a`，原文含引号 |
| double-quoted key | 不被当作 quoted key；引号属于 unquoted key 的字符 | 当前有专门 quoted 判断，需锁定行为 | Rust | `"\"A\"=1"` 必须 key=`\"A\"`（不是 `A`） |
| `export` | 只有后面跟空白时才是前缀；`export_a` 是普通 key；单独 `export` 是无值 key | 大致一致 | Rust | `export a=b`、` export 'a'=b`、`export_a=1`、`export` |
| key 后空白 | key 与 `=` 间的 `[^S\r\n]*` 被忽略 | 基本支持 | Rust | ` a = b ` => key `a`, value `b` |
| 无等号变量 | `a` => value `None` | 支持 | Rust | `no_value_var` |
| 空值 | `a=`、`a=\n` => value `""` | 支持 | Rust | `a=\nb=c` |
| unquoted value | 读取至物理行末；只去尾部空白和“空白后 #”注释；值内部空白保留 | 基本支持 | Rust | `a=b c`、`a=b\tc`、`a=b  c`、`a=b\u00a0 c`、`a=b c ` |
| `#` 规则 | `a=b#c` => `b#c`；`a=b #c`/tab 后 => `b` | 支持但需上游逐例锁定 | Rust | 三个 exact fixtures |
| `A= # comment` | 1.2.2 解析为 value `"# comment"`，因为 `#` 紧跟 `=`，不是空白后注释的 value 情形 | 当前测试已标记但需完整 parser gate | Rust | `HASH= # value` 必须 value=`# value`，无 error |
| single-quoted value | 只解码 `\\` 和 `\\'`；`\\n` 保持两个字符 | 部分支持 | Rust | `a='b\\nc'` => `b\\nc`；`a='b\\'c'` => `b'c` |
| double-quoted value | 解码 `\\`, `\\'`, `\\"`, `\\a\\b\\f\\n\\r\\t\\v`；其他反斜杠保持 | 部分支持 | Rust | 逐个 escape fixture；未知 `\\q` 保持 `\\q` |
| quoted value 内 `#` | `#` 是值内容，不是注释 | 支持 | Rust | `A="x # y"`、`A='x # y'` |
| quoted value 尾部 | 关闭引号后只允许空白、comment、行终止；其他字符导致 error | 支持基本路径 | Rust | `A="x" trailing` => error 并恢复 |
| multiline quoted value | 单/双引号均可跨物理行；值内实际换行保留为 `\n` | 支持成功值，但丢失原文 | Rust | `a="b\nc"` 与 `a='b\nc'` 的 value/original/line |
| multiline escaped newline | double quote 的 `\\n` 是一个换行字符；single quote 的 `\\n` 是字面量 | 部分支持 | Rust | 上游 `test_parser` 对 `a="b\\nc"`、`a='b\\nc'` |
| Unicode | Python regex Unicode；非 ASCII key/value 合法（key 仍不能含 whitespace） | Rust UTF-8 基本支持 | Rust | `a=à`、`a="à"`；含 Unicode 空白的 key/value |
| 非法 key/行 | 例如 `a: b`：Binding key/value 为 None，error=True，原文从起点到恢复边界 | 当前静默丢失 | Rust + facade | 见第 6 节错误恢复矩阵 |
| 未闭合 quote | 失败 binding，不吞掉下一行合法 binding；warning 行号为起始行 | 当前用启发式恢复，不能产出 error/original | Rust + facade | `a="\nb=c`：error line 1，随后 `b=c` line 2 |
| 原文保留 | `Original.string` 是从 mark 到 parser 消费结束的精确子串 | 当前 `physical_lines` 丢 CR/CRLF 且不保留 comments/blank | Rust | 所有 Binding fixture 都比较原文；set/unset 回写字节级相等（目标行除外） |

### 4.1 上游 parser 测试必须完整移植

不能只选“正常配置文件”样例。`tests/test_parser.py` 的参数化表是逐项验收基线，至少要保留以下全部类别：

- `""`、`a=b`、`'a'=b`、`[=b`、空白包围、`export`；
- 注释、行尾注释、无空格的 `#`、tab 和 Unicode 不间断空格；
- 单/双引号、单/双引号内空格和 `#`；
- `export_a`、`export port`、无值变量；
- 实际多行、转义多行、单引号反斜杠、双引号全部白名单转义；
- Unicode 值；
- `a: b` 非法行；
- LF、bare CR、CRLF；
- 末尾换行/多个空行；
- 未闭合双引号后的恢复；
- comment 后恢复、多行 binding 后的行号；
- `uglyKey[%$` 这种非传统但上游接受的 key。

验收命令（实现 parser debug hook 后）：

```bash
pytest -q tests/test_upstream_parser_differential.py
cargo test parser
```

测试应从固定的 `python-dotenv==1.2.2` Oracle 运行，而不是只比较人工预写 expected；预写 expected 仅用于定位差异。

## 5. Binding / Original / Position 契约

上游结构：

```python
class Original(NamedTuple):
    string: str  # 从 mark 到本 binding 消费终点的原始文本
    line: int    # 1-based 起始物理行

class Binding(NamedTuple):
    key: Optional[str]
    value: Optional[str]
    original: Original
    error: bool
```

Rust 建议内部等价结构（名称可调整，但字段语义不可调整）：

```rust
struct Original {
    source: String,
    line: usize, // 1-based
}

struct Binding {
    key: Option<String>,
    value: Option<String>,
    original: Original,
    error: bool,
}
```

Position 的兼容要求：

- 初始 `chars=0, line=1`。
- 每次读取的 newline 模式 `\n`、`\r`、`\r\n` 都使 line 加 1；`\r\n` 只加 1。
- `Original.line` 是 mark 时的 line，不是 binding 结束行。
- Python 的 `len(str)` 按 Unicode code point 计数；Rust 内部可以用 byte offset 做切片，但不可以把 byte offset 暴露为 Python 的字符位置。
- `Original.string` 必须是原始输入的精确子串，不能把 `\r` 归一为 `\n`。

精确验收：

```text
输入："a=b\r\nc=d"
Binding 1: key=a, value=b, error=False,
           original.string="a=b\r\n", original.line=1
Binding 2: key=c, value=d, error=False,
           original.string="c=d", original.line=2

输入："# c\na=\"b\nc\"\nd=e\n"
Binding 1: key=None, value=None, error=False,
           original.string="# c\n", line=1
Binding 2: key=a, value="b\nc", error=False,
           original.string="a=\"b\nc\"\n", line=2
Binding 3: key=d, value=e, error=False,
           original.string="d=e\n", line=4
```

这些字段可以通过仅测试用的 `_debug_parse_bindings(text)` 暴露；不要求把上游 `Binding` 作为稳定公开 Python API，除非完整替代的兼容清单明确承诺它。

## 6. 错误恢复、warning 与行号

上游 `parse_binding()` 是非 fail-fast 解析：

1. 在 binding 起点设置 mark。
2. 任一 regex/read 失败，读取 `_rest_of_line`，直到 `\r`、`\n`、`\r\n` 或输入末尾。
3. 返回 `Binding(None, None, original, error=True)`。
4. 下一次迭代从下一物理行继续。
5. `main.with_warn_for_invalid_lines()` 对每个 error 记录一次：

```text
WARNING dotenv.main:
python-dotenv could not parse statement starting at line <N>
```

实现归属：

- Rust：决定 error、消费到哪里、Original 和起始 line；绝不能吞掉后续合法 binding。
- Python facade：调用 `logging.getLogger("dotenv.main")`（或与完整兼容模块一致的 logger 名），对 error binding 逐条 warning；`dotenv_values`、`load_dotenv`、`set_key`、`unset_key` 都共享该行为。

错误恢复矩阵：

| 输入 | 第一条结果 | 下一条结果 | warning |
|---|---|---|---|
| `a: b\nB=2` | error=True, line=1, original=`a: b\n` | `B=2`, line=2 | 1 次，line 1 |
| `A="\nB=2\n` | error=True, line=1, original=`A="\n` | `B=2`, line=2 | 1 次，line 1 |
| `A="x" trailing\nB=2` | error=True，消费第一行 | `B=2` | 1 次，line 1 |
| `A="x" # c\nB=2` | 成功 | `B=2` | 0 次 |
| `# c\nB=2` | comment binding，error=False | `B=2`, line=2 | 0 次 |
| `A=1\rB=2` | 成功 original=`A=1\r`, line 1 | `B=2`, line 2 | 0 次 |

Python 验收：使用 `caplog` 比较 logger 名、level、消息、调用次数和行号；`verbose=False` 也不能静默 invalid line，因为上游 invalid-line warning 与 missing-file verbose 日志是两个契约。

## 7. CR/LF 与原始文本契约

必须区分两件事：解析器识别换行，和 Python 打开文本文件时的 newline 转换。

### 7.1 parser 直接接收字符串/stream

当 `parse_stream(StringIO(text))` 接收原始字符串时：

- `\n`、`\r`、`\r\n` 都是换行；
- `\r\n` 只增加一行；
- `Original.string` 必须保留实际输入的换行字节（Python str 中对应的字符）；
- multiline value 的 value 仍保留实际换行字符，而不是删除或统一；
- 最后无换行的 binding 仍要产出；
- 只含空行的输入也要按照上游 binding 消费规则保留 Original。

### 7.2 文件路径

Python `open(path, encoding=...)` 的 newline 行为属于 facade；Rust 接收已经读出的 `str`。因此：

- 不要在 Rust 再做一次 CRLF 归一；
- UTF-16/其他 encoding 的解码异常必须由 Python 原样抛出；
- `encoding=None` 的默认行为要与上游 `open(..., encoding=None)` 一致；
- stream.read() 返回的 str 不经过文件 newline 转换。

验收 fixture：对同一个逻辑内容分别使用 LF、CRLF、bare CR 的 `StringIO`，比较 Binding 全字段；再用路径和 `encoding="utf-16"` 比较最终 API 和异常。

## 8. 变量解析与插值差距

上游 `variables.py` 的唯一匹配模式是：

```regex
\$\{ (?P<name>[^\}:]*) (:- (?P<default>[^\}]*) )? \}
```

也就是说，必须严格满足：

- 只展开 `${NAME}` 和 `${NAME:-default}`；
- bare `$NAME` 保持字面量；
- name 可以为空、可以包含除 `:`、`}` 外的字符；
- default 可以为空、可以包含 `:`，但不能包含 `}`；
- 不匹配的 `${...`、`${A:B}`、`${A` 保持原文；
- 变量 token 以 Literal/Variable 顺序拼接；
- Variable.resolve：环境值为 `None` 时变成空字符串；缺失变量使用 default，否则空字符串。

当前 `interpolate_value()` 的普通样例大致一致，但它没有显式复刻 token grammar，无法保证所有边界和未来组合。应改成 Rust 的 `parse_variables` + `resolve_atoms`，并以 Oracle differential 为门禁。

### 8.1 resolve 优先级

`dotenv_values()` 使用 `override=True`：对每一条 raw binding，resolve 时环境映射为：

```text
os.environ 先放入
本文件已经解析并 resolve 的 new_values 再覆盖
```

因此：

- 之前文件值优先于进程环境；
- 当前文件中的 `KEY`（value=None）在引用时是存在但 resolve 为空字符串，并且会遮蔽环境值；
- value=None 自身保持 None，不被插值改成空字符串；
- `interpolate=False` 完全不解析变量。

`load_dotenv(override=False)` 的优先级相反：文件先放入、环境后覆盖；这必须由 Python facade 传入显式 `override`，不能把 `dotenv_values` 的规则硬编码成所有 API 的规则。

### 8.2 插值精确验收表

| 输入 | 环境 | `interpolate=True` 期望 |
|---|---|---|
| `A=${X}` | `X=env` | `A=env` |
| `A=$X` | `X=env` | `A=$X` |
| `A=${X:-d}` | X 缺失 | `A=d` |
| `A=${X:-}` | X 缺失 | `A=""` |
| `A=${X:Y}` | `X=env` | 保持 `${X:Y}` |
| `A=${X:-a:b}` | X 缺失 | `A=a:b` |
| `A=${}` | 无 | `A=""` |
| `A=${X` | 无 | 保持 `${X` |
| `A=one\nB=${A}` | 环境 A=env | `A=one, B=one` |
| `A=one\nB=${A}\nA=two\nC=${A}` | 环境 A=env | `A=two, B=one, C=two`（A 的插入位置仍在首条） |
| `NONE\nX=${NONE:-fallback}` | 环境 NONE=env | `NONE=None, X=""` |
| 任意上述 | 任意 | `interpolate=False` 时保留 raw literal |

验收文件：`tests/test_variables_differential.py`（token/resolve debug hook）和 `tests/test_compat.py`（最终 OrderedDict）。必须覆盖上游 `tests/test_variables.py` 的所有参数化案例；不得只验证 `${NAME}`。

## 9. 重复键、顺序和 None/空字符串

上游 `resolve_variables()` 是顺序迭代并写入普通 dict；`OrderedDict` 保留首次插入位置，重复键更新值：

```text
DUP=first
A=${DUP}
DUP=second
B=${DUP}
```

期望：

```python
OrderedDict([
    ("DUP", "second"),
    ("A", "first"),
    ("B", "second"),
])
```

注意：`A` 的结果不会因为后面 DUP 更新而回算；解析是单次、顺序、即时 resolve。当前 Rust 的 `previous` 与 first-position update 方向正确，但必须移到 Binding pipeline 后再验证 error/comment/duplicate 的交互。

精确验收：

- 重复键保留首次位置；
- `None` 与 `""` 不相等且类型和值分别保持；
- 重复的 `KEY`、`KEY=`、`KEY=${OTHER}` 之间按上游顺序解析；
- invalid binding 不进入 previous/new_values；
- comment/blank 不改变顺序和变量环境；
- `interpolate=False` 仍折叠重复键，但不替换 value。

## 10. FIFO、stream 与异常契约

### 10.1 FIFO

上游 `main._is_file_or_fifo(path)` 接受普通文件或 Unix FIFO：

- `os.path.isfile(path)` 为真，或 `os.stat(path)` 的 mode 是 FIFO；
- FIFO 路径优先于 stream（只要 path 被识别为 file/FIFO）；
- 打开 FIFO 的阻塞/读取错误由 Python IO 传播；
- 不存在、目录、不可 stat 的路径被视为不可用输入；若有 stream 则 fallback 到 stream，否则空输入并按 verbose 规则记录 missing-file info。

实现归属：Python facade 做 `is_file_or_fifo`、open 和 stream 选择；Rust 不直接 `stat` 或打开路径。

Unix 验收（Linux/macOS CI）：

1. `os.mkfifo(path)`；后台 writer 写入 `A=1\n` 后关闭；`dotenv_values(dotenv_path=path)` 得到 `A=1`。
2. `dotenv_path=fifo, stream=StringIO("B=2")`：验证 FIFO 优先，结果为 A。
3. 目录路径 + stream：验证使用 stream；目录路径且无 stream：验证空结果/verbose 日志。
4. FIFO writer 提前关闭、权限错误：比较异常类型；禁止死循环或吞异常。

### 10.2 text stream

上游假设 stream 具有 `.read()` 并返回 `str`：

- `StringIO` 正常；
- `.read()` 返回 bytes 或其他对象时，后续 parser 的 Python 行为必须由 differential 锁定；完整替代应优先给出明确 `TypeError`，并在兼容测试中与 Oracle 对齐；
- `.read()` 自身抛出的异常必须原样传播；
- stream 非 `None` 时不要关闭调用方拥有的 stream；
- `dotenv_path` 可用时 path 优先于 stream；path 不可用时才 fallback stream；
- 同一个已读 stream 第二次调用的 EOF 行为与上游一致（通常返回空 mapping）。

验收 fixture：自定义 `read()` 计数/抛错对象，检查调用次数、异常类型、stream 是否被关闭、path/stream 优先级。

### 10.3 文件 encoding/路径异常

Python facade 验收：

- `PathLike` 与 `str` 同结果；
- `encoding="utf-16"` 读写与 Oracle 一致；
- 非法字节触发同类 `UnicodeDecodeError`；
- 不存在文件：结果空；`verbose=True` 记录
  `python-dotenv could not find configuration file <path>.`；
- `verbose=False` 不记录 missing-file info，但 invalid line warning 仍独立存在。

## 11. 完整 parser 验收门禁

实现 Agent 完成后，必须按以下顺序验收；任何一项未通过都不能声称“完整 python-dotenv 替代”：

1. **上游 parser 原样测试**：将 v1.2.2 `tests/test_parser.py` 参数化测试完整带入，或建立等价 Oracle differential；逐条比较 Binding 全字段。
2. **上游 variables 原样测试**：完整带入 `tests/test_variables.py`；比较 token 结构/resolve 结果。
3. **Rust 单元测试**：覆盖每个 regex/扫描分支、所有换行、转义、恢复和随机 UTF-8；不得 panic。
4. **Python differential**：`dotenv_values` 的类型、顺序、值、日志、异常、环境副作用与 Oracle 完全一致。
5. **原文回写测试**：对含注释、空行、CRLF、bare CR、多行、非法行的文件执行 `set_key`/`unset_key`，断言未修改 binding 的原文完全保留。
6. **FIFO/平台测试**：Unix FIFO 必须执行；Windows 需明确 skip 原因，不得把未执行伪装为 pass。
7. **安装 wheel 测试**：在干净环境安装 release wheel 后重复第 2～6 项，不只用 `maturin develop`。

建议命令：

```bash
python -m pytest -q tests/test_upstream_parser_differential.py tests/test_variables_differential.py
python -m pytest -q tests/test_compat.py tests/test_signature.py
cargo test --all-targets
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
```

测试报告必须记录：Oracle 版本/来源、测试数量、失败 fixture 的完整输入（必要时 repr）、candidate 与 Oracle 的结构化 diff、平台、Python/Rust 版本。

## 12. 完成定义与禁止宣称

### Parser 子系统完成定义

- Binding/Original/error/line 结构已实现并有 debug/test hook；
- 上游 parser/variables 全量测试通过；
- 所有表格中的当前差距均关闭，或在兼容性文档中明确标为不支持；
- invalid line warning、missing-file verbose 日志、FIFO、stream read/encoding 异常均有 differential 证据；
- set/unset 原文回写测试通过；
- release wheel 测试通过。

### 在完成前禁止的说法

- “100% 兼容 python-dotenv”；
- “drop-in replacement”；
- “完整替代品”；
- 未限定输入规模、平台和安装方式的固定加速倍数。

在 parser gate 未通过前，README 只能写“Rust-backed `dotenv_values` implementation / compatibility work in progress”。完整替代的最终 claim 必须由完整 API、CLI/IPython、文件修改、查找路径和发布 wheel 的总体验收共同支撑。
