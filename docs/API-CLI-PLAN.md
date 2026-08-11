# Full `python-dotenv` API and CLI parity plan

Status: implemented locally. This document is the implementation inventory for
behavioral parity with the frozen `python-dotenv==1.2.2` distribution,
including its Python API, import namespace, optional CLI, and IPython extension.
Linux source and release-wheel gates are recorded separately; cross-platform CI
remains a release condition.

## Source of truth and compatibility boundary

The Oracle is the pinned 1.2.2 source distribution and wheel, not the latest
upstream branch. The relevant implementation files are:

- `dotenv/main.py`: `DotEnv`, source selection, logging, mutation, discovery,
  `load_dotenv`, `dotenv_values`, `get_key`, `set_key`, `unset_key`, `rewrite`.
- `dotenv/__init__.py`: package exports, `load_ipython_extension`, and
  `get_cli_string`.
- `dotenv/cli.py` and `dotenv/__main__.py`: optional Click CLI and module entry
  point.
- `dotenv/ipython.py`: `%dotenv` magic and extension registration.

The corresponding upstream tests are the acceptance oracle:
`test_main.py`, `test_parser.py`, `test_variables.py`, `test_cli.py`,
`test_ipython.py`, `test_fifo_dotenv.py`, `test_is_interactive.py`,
`test_utils.py`, and `test_zip_imports.py`. The existing parser and interpolation
tests remain required; this plan adds the currently out-of-scope surfaces.

Full drop-in parity means that `from dotenv import ...`, `python -m dotenv`,
and the `dotenv` console script work with the same names, signatures, return
values, side effects, logs, exceptions, exit codes, and file-system behavior.
No secondary import namespace is part of the release contract; the candidate
must provide `dotenv` directly.

## Public package surface

`dotenv/__init__.py` must export the following names in `__all__`:

| Name | Required public behavior |
|---|---|
| `dotenv_values` | Parse and return an ordered mapping; preserve logging, FIFO, exact discovery, and parser recovery parity. |
| `load_dotenv` | Parse and set environment variables; default `override=False`; return `True` when the parsed mapping is non-empty (including a mapping containing only valueless keys), otherwise `False`. |
| `find_dotenv` | Search from the correct script/cwd/interactive/debugger/frozen context; optionally raise `IOError`. |
| `get_key` | Read one key, return its value or `None`, and emit upstream verbose logs. |
| `set_key` | Add or replace one key using quote/export options and atomic rewrite semantics. |
| `unset_key` | Remove one key while preserving all other source text and return the upstream tuple. |
| `get_cli_string` | Produce the exact shell command string used by the upstream utility. |
| `load_ipython_extension` | Lazily load and register the `%dotenv` magic without making IPython a core dependency. |

The package must also provide `dotenv.__version__`, `dotenv.__main__`,
`dotenv.main`, `dotenv.cli`, `dotenv.ipython`, `dotenv.parser`, and
`dotenv.variables` at the same import paths expected by 1.2.2 users. Private
helpers need not be source-identical, but observable behavior must match.

### Signatures to freeze

These signatures must be tested with `inspect.signature` and called using both
positional and keyword arguments:

```python
class DotEnv:
    def __init__(
        self,
        dotenv_path,
        stream=None,
        verbose=False,
        encoding=None,
        interpolate=True,
        override=True,
    ): ...

def dotenv_values(
    dotenv_path=None,
    stream=None,
    verbose=False,
    interpolate=True,
    encoding="utf-8",
): ...

def load_dotenv(
    dotenv_path=None,
    stream=None,
    verbose=False,
    override=False,
    interpolate=True,
    encoding="utf-8",
): ...

def find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=False): ...

def get_key(dotenv_path, key_to_get, encoding="utf-8"): ...

def set_key(
    dotenv_path, key_to_set, value_to_set, quote_mode="always",
    export=False, encoding="utf-8", follow_symlinks=False,
): ...

def unset_key(
    dotenv_path, key_to_unset, quote_mode="always",
    encoding="utf-8", follow_symlinks=False,
): ...

def get_cli_string(
    path=None, action=None, key=None, value=None, quote=None,
): ...
```

`DotEnv` methods required by existing callers are `dict()`, `parse()`,
`set_as_environment_variables()`, and `get(key)`. `_get_stream()` remains an
internal context manager but its path/FIFO/stream/missing-file behavior is part
of the observable contract through the public methods.

## Shared source-selection and parser behavior

All APIs using `DotEnv` must share one source-selection implementation:

1. If both path and stream are absent, call `find_dotenv()` with its default
   arguments.
2. A regular file or FIFO path takes precedence over a supplied stream.
3. If the path is unavailable and a stream exists, parse the stream.
4. Otherwise parse an empty stream; `verbose=True` emits exactly the
   `dotenv.main` INFO message from upstream.
5. Use the requested encoding for files and propagate decoding/read failures.

The parser contract remains the frozen 1.2.2 grammar: ordered bindings, empty
versus valueless keys, quotes/escapes/comments/export, multiline values, LF,
CRLF and CR, malformed-line warning with starting line number and recovery,
Unicode, and `${NAME}` / `${NAME:-default}` interpolation. `dotenv_values`
uses `override=True` resolution; `load_dotenv` uses its `override` argument
only when writing to `os.environ`. No API may silently broaden or narrow the
Oracle grammar.

Required shared tests include:

- exact `OrderedDict` type and insertion order;
- duplicate keys and sequential self/reference resolution;
- environment snapshot and no mutation for `dotenv_values`;
- `None` bindings omitted from environment writes;
- invalid-line warning logger name, level, message, starting line, and recovery;
- missing-file verbose logging and call count;
- regular file, `PathLike`, text stream, FIFO, missing path, encoding, and
  path-over-stream precedence;
- zip-import callers and a missing current working directory;
- no panic or process corruption on arbitrary valid UTF-8 input.

## `DotEnv`, loading, and discovery

### `DotEnv.dict()` and `parse()`

`parse()` yields `(key, value)` pairs for valid bindings, warns on malformed
statements, and skips mappings whose key is `None`. `dict()` caches the
resulting `OrderedDict`; interpolation is controlled by `interpolate` and
resolution honors the `override` ordering rules. Empty mappings remain
observable as empty mappings rather than falsey cache ambiguity.

### `load_dotenv()`

Implement the complete mutation contract:

- `override=False` by default: existing `os.environ` values win.
- `override=True`: values from the dotenv file win.
- Do not write a key whose resolved value is `None`.
- Return `False` only for an empty parsed mapping. A non-empty mapping returns
  `True` even when every binding is valueless; `None` bindings themselves are
  never written to `os.environ`.
- If `PYTHON_DOTENV_DISABLED` case-folds to `1`, `true`, `t`, `yes`, or `y`,
  do not read or mutate the file, return `False`, and emit the exact upstream
  DEBUG message. False-y spellings (`0`, `false`, `f`, `no`, `n`, empty) do not
  disable loading.
- A dotenv file may define `PYTHON_DOTENV_DISABLED`; that file-defined value
  must not disable the load already in progress.
- Preserve path/stream/encoding/FIFO/discovery behavior and logger semantics.

### `find_dotenv()`

Match the upstream search context and errors:

- `usecwd=True` starts at `os.getcwd()`.
- Interactive mode starts at cwd when `sys.ps1`, `sys.ps2`, or a `__main__`
  module without `__file__` is present.
- Debugger mode (`sys.gettrace() is not None`) and frozen applications start at
  cwd.
- Normal script mode starts at the first existing caller filename outside the
  dotenv implementation; zip-import frames must not cause an exception.
- Walk parent directories through the root, accepting regular files and FIFOs.
- Return the first matching path, `""` when not found, or raise `IOError("File
  not found")` when `raise_error_if_not_found=True`.
- A missing starting path raises the upstream `IOError("Starting path not
  found")` behavior where applicable.

Acceptance comes from `test_main.py`, `test_is_interactive.py`, and
`test_zip_imports.py`, including all mocked interactive/debugger contexts and
both zip-import scenarios.

## Key access and file mutation

### `get_key()`

Use `DotEnv(dotenv_path, verbose=True, encoding=encoding).get(key_to_get)`.
Return the stored string, `None` for valueless/missing keys, and emit the
upstream INFO message for a missing file plus WARNING for a missing key.
Encoding and `PathLike` behavior must match `dotenv_values`.

### `rewrite()` safety contract

Implement the upstream context manager with these invariants:

- `follow_symlinks=False` rewrites the symlink path itself, leaving an existing
  target untouched; `True` resolves the target first.
- Open the source before creating the destination; close the source if `lstat`
  fails.
- Create a temporary file in the destination directory, with text mode and the
  requested encoding, so replacement is same-filesystem and atomic.
- Preserve regular-file mode bits; newly created files use the upstream
  temporary-file permissions.
- On successful completion, `os.replace()` installs the destination.
- On any write/replace failure, remove the temporary file and re-raise the
  original error; never leave a partial target.
- Missing source files are treated as an empty source for `set_key`, while
  permission and other I/O errors propagate.

Acceptance: `test_main.py` mode, missing-file, permission, symlink,
follow-symlink, lstat-close, atomic replacement, encoding, and error-path
tests. Add crash/failure-injection tests for temporary-file cleanup and target
integrity.

### `set_key()`

Match exact return `(True, key_to_set, value_to_set)` on success and
`(None, key_to_set, value_to_set)` only where upstream returns failure. Reject
unknown quote modes with `ValueError("Unknown quote_mode: ...")`.

- `quote_mode="always"`: single-quote and escape single quotes.
- `quote_mode="auto"`: quote values that are not alphanumeric.
- `quote_mode="never"`: write the raw value.
- `export=True`: prefix the written binding with `export `.
- Replace only matching bindings; preserve comments, invalid source text,
  unrelated bindings, blank lines, and missing final newlines.
- Append a newline when needed before a new binding.
- Create a missing file and preserve encoding/mode semantics through `rewrite`.

### `unset_key()`

Return `(True, key)` after removing matching bindings while preserving all
other source text. For a missing file or absent key, return `(None, key)` and
emit the exact upstream WARNING. Honor encoding, symlink policy, quote-mode
signature compatibility, atomic rewrite, and no-follow default.

## `get_cli_string()` utility

Implement the exact string-building behavior tested by upstream `test_utils.py`:

- no arguments: `dotenv`;
- optional `-q <quote>` and `-f <path>` before the action;
- action/key/value ordering for `list`, `get`, and `set`;
- values containing spaces are double-quoted;
- values without spaces are passed unchanged;
- preserve upstream handling of falsey values and unescaped shell metacharacters
  (this helper creates a command string; it is not a shell sanitizer).

## CLI and module entry point

### Packaging

Restore the exact optional packaging surface from the 1.2.2 metadata:

```toml
[project.optional-dependencies]
cli = ["click>=5.0"]

[project.scripts]
dotenv = "dotenv.__main__:cli"
```

The base package must import without Click. `dotenv.cli` may fail with the
upstream installation guidance only when a user explicitly invokes the CLI
without the `cli` extra. IPython remains a lazy optional dependency, as in the
upstream module; loading the core package must not import IPython.

`python -m dotenv` must invoke the same `cli` object as the console script.
The `--version` output must report the package version.

### Global options

The Click group must provide:

- `-f/--file`: default `${cwd}/.env`, `click.Path(file_okay=True)`;
- `-q/--quote`: `always`, `never`, or `auto`, default `always`;
- `-e/--export`: boolean, default false;
- `--version`;
- the group help text and command parsing behavior from 1.2.2.

`stream_file()` must print `Error opening env file: ...` to stderr and exit 2
for an unreadable, missing, or non-file path.

### Commands and acceptance behavior

| Command | Required behavior |
|---|---|
| `dotenv list` | Read the file; output sorted keys. `--format simple` prints `KEY=value`; `json` prints sorted, indented JSON; `shell` shell-quotes values; `export` prefixes `export `. Skip `None` values. |
| `dotenv get KEY` | Print a truthy stored value and exit 0; missing/empty/None values exit 1; file errors exit 2. |
| `dotenv set KEY VALUE` | Call `set_key` with global quote/export options; print `KEY=VALUE`; return 1 if the mutation reports failure. |
| `dotenv unset KEY` | Call `unset_key`; print `Successfully removed KEY`; return 1 when not removed. |
| `dotenv run [--override/--no-override] COMMAND ...` | Require an existing file and command; load non-`None` values, optionally preserve existing process values, and replace/launch the process with the merged environment. |

`run` must preserve command flags and arguments after the command boundary,
return the child exit status on Windows, and use `os.execvpe` on POSIX. Missing
file and missing command errors must retain Click's expected exit status and
stderr text. The full command matrix is in upstream `test_cli.py`.

## IPython extension

`dotenv.ipython` must lazily depend on IPython and provide an
`IPythonDotEnv` magic class. Register `%dotenv` through
`load_ipython_extension(ipython)`.

Required syntax and behavior:

```text
%load_ext dotenv
%dotenv [-o|--override] [-v|--verbose] [dotenv_path=.env]
```

Resolve the requested path with `find_dotenv(path, True, True)`. If no file is
found, print `cannot find .env file` and return. Otherwise call
`load_dotenv(path, verbose=..., override=...)`. Verify both override modes and
new-variable loading with the upstream `test_ipython.py` suite, while keeping
IPython absent from the base install.

## Implementation sequencing

1. **Namespace and packaging:** add the `dotenv` package exports, version,
   module entry point, console-script metadata, and optional `cli` dependency;
   add import/signature tests before wiring mutation.
2. **Shared Python orchestration:** extract a single `DotEnv` facade around the
   Rust parser, implementing exact source selection, FIFO detection, logs,
   ordered resolution, and environment snapshot/write policy.
3. **Discovery and loading:** implement `find_dotenv`, `load_dotenv`, disabled
   environment handling, interactive/debugger/frozen/zip contexts, and their
   tests.
4. **Safe mutation:** implement `rewrite`, `set_key`, `unset_key`, and
   `get_key`; verify atomic replacement, mode preservation, cleanup on errors,
   symlink policy, permissions, encodings, and source-text preservation.
5. **Utility and CLI:** implement `get_cli_string`, Click group/options,
   `list/get/set/unset/run`, module execution, exit statuses, and subprocess
   environment behavior.
6. **IPython:** add lazy `%dotenv` integration and optional-dependency tests.
7. **Release gate:** run the complete pinned upstream suite plus project-owned
   differential tests against installed wheels on Linux, macOS, and Windows;
   verify base install, `[cli]` install, `python -m dotenv`, and a clean CLI
   subprocess environment.

## Acceptance gate

The feature is complete only when all of the following are true:

- `dotenv` imports and exports match 1.2.2 without a namespace shim.
- All relevant upstream tests pass without a namespace shim:
  `test_main.py`, `test_parser.py`, `test_variables.py`, `test_cli.py`,
  `test_ipython.py`, `test_fifo_dotenv.py`, `test_is_interactive.py`,
  `test_utils.py`, and `test_zip_imports.py`.
- Differential tests compare values, ordered types, exceptions, logger name /
  level / message / count, environment side effects, file contents, modes,
  symlink targets, temporary-file cleanup, exit codes, stdout, and stderr.
- Base installation works without Click or IPython; `[cli]` installation adds
  the `dotenv` command; `python -m dotenv` and the console script agree.
- Release wheels are tested from fresh environments on every advertised OS and
  architecture, with no reliance on `maturin develop` or repository source
  imports.
- BSD-3-Clause attribution for any materially adapted upstream code or tests is
  retained in `THIRD_PARTY_NOTICES.md`; no full-compatibility claim is made
  until this gate is green.

## Explicit non-goals for this plan

This plan does not add new dotenv dialects, encryption/decryption, secret
management, shell-language execution, or behavior from a newer upstream
version. It does not authorize silently replacing unrelated installed
`dotenv` packages, changing the pinned 1.2.2 Oracle, or claiming performance
parity before compatibility and wheel gates pass.
