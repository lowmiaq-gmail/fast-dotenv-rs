# Full python-dotenv replacement plan

> **文档状态：历史实施计划。**
>
> 本文件记录完整重写阶段当时的实施路径和 checklist，不再承担“当前做到哪”的职责。
> 当前项目进度统一看仓库根目录 `PROGRESS.md`；当前发布/推广状态看 `docs/LAUNCH-STATUS.md`。
> 如果本文件的未完成项与实际代码、CI、GitHub Release 或其他公开证据冲突，以实际证据为准，不要重新执行已经完成的工作。

## Source of truth

- Oracle: `python-dotenv==1.2.2` from the official PyPI sdist.
- Public import contract: existing applications continue to use `import dotenv`
  and `from dotenv import ...`.
- Distribution under development: `fast-dotenv-rs`.
- Correctness precedes acceleration. A faster result that differs in return
  values, order, logging, exceptions, file effects, CLI output, or exit status
  is a failed replacement.

## Definition of complete

The project is complete only when all of these gates pass together:

1. **Namespace gate** — the wheel provides the `dotenv` package, `python -m
   dotenv`, and the `dotenv` console command without requiring
   `python-dotenv`.
2. **API gate** — public functions, classes, modules, call signatures,
   defaults, return values, and `__all__` match 1.2.2.
3. **Parser gate** — `Binding`, `Original`, line numbers, malformed-line
   recovery, quotes, escapes, comments, LF/CRLF/CR, interpolation, and stream
   exceptions match the Oracle.
4. **Filesystem gate** — files, FIFO inputs, encodings, atomic rewrites, file
   modes, symlinks, and missing paths match the Oracle.
5. **Environment gate** — override ordering, `None` values, repeated keys,
   default discovery, and `PYTHON_DOTENV_DISABLED` match the Oracle.
6. **Integration gate** — CLI and IPython behavior, stdout/stderr, and exit
   codes match the Oracle.
7. **Upstream gate** — the complete 1.2.2 test suite passes with no project
   deselection or project-added xfail. Only upstream platform skips are
   accepted. The current source contains 216 collected tests without IPython
   and three additional IPython tests.
8. **Differential gate** — generated and curated cases compare ordered values,
   exceptions, logs, environment mutations, and file bytes with zero
   unexplained differences.
9. **Wheel gate** — installed release wheels pass tests on supported Linux,
   macOS, and Windows runners.
10. **Value gate** — installed-wheel benchmarks show a repeatable gain on
    representative CPU-bound parsing workloads. No performance claim is made
    before this gate passes.

## Architecture

- Reuse the BSD-3-Clause upstream Python implementation as the behavioral
  reference for filesystem discovery, atomic file editing, CLI, and IPython.
- Implement the parser and interpolation hot paths in Rust/PyO3.
- Keep a thin Python compatibility facade for Python-specific behavior such as
  logging, frame inspection, file handles, permissions, and environment
  mutation.
- Preserve upstream-compatible `dotenv.parser` and `dotenv.variables` objects
  while their work is backed by Rust.
- Keep Oracle and candidate in separate test environments so the identical
  `dotenv` namespace cannot mask one implementation with the other.

## Sequenced build checklist

- [x] **1. Lock the upstream contract**
  - Build: inventory modules, symbols, signatures, side effects, CLI/IPython,
    and every upstream test.
  - Verify: contract documents cover all files under the 1.2.2 `src/dotenv`
    and `tests` directories.

- [x] **2. Establish a correct drop-in baseline**
  - Build: provide the complete `dotenv` namespace and upstream-compatible
    Python behavior before replacing hot paths.
  - Verify: the full upstream suite passes against the candidate package.

- [x] **3. Replace parser data model and grammar with Rust**
  - Build: emit complete binding records including original text, start line,
    key, value, and error state.
  - Verify: every upstream parser test plus malformed and arbitrary UTF-8
    differential cases passes.

- [x] **4. Replace variable parsing and resolution with Rust**
  - Build: preserve `Literal`, `Variable`, `parse_variables`, sequential
    resolution, and override precedence.
  - Verify: upstream variable and environment matrix tests pass.

- [x] **5. Complete file and environment APIs**
  - Build: `DotEnv`, `dotenv_values`, `load_dotenv`, `find_dotenv`, `get_key`,
    `set_key`, `unset_key`, `rewrite`, FIFO, encoding, permissions, symlinks,
    logging, and disabled loading.
  - Verify: upstream main, FIFO, interactive, and zip-import tests pass.

- [x] **6. Complete CLI and IPython compatibility**
  - Build: console entry point, `python -m dotenv`, list/get/set/unset/run,
    output formats, command execution, exit codes, and `%dotenv` magic.
  - Verify: all CLI and IPython tests pass in isolated environments.

- [x] **7. Build the differential and fuzz gates**
  - Build: two-environment Oracle/candidate runner, generated grammar corpus,
    filesystem fixtures, log/exception capture, and Rust no-panic fuzz input.
  - Verify: zero unexplained differences and no panic.

- [x] **8. Package and test release wheels**
  - Build: Maturin abi3 wheels, console script, licenses/notices, SBOM, CI
    artifacts, and installed-wheel test jobs. Linux fresh-wheel validation is complete.
  - Verify: public CI #3 passed Linux Python 3.10/3.12, macOS arm64, and Windows x86-64.

- [x] **9. Benchmark without weakening compatibility**
  - Build: installed-wheel benchmarks for small, medium, and large files,
    interpolation, file input, and stream input.
  - Verify: raw timings, environment, variance, and speedups are recorded.

- [x] **10. Extract reusable project machinery**
  - Build: API inventory tool, Oracle harness, differential runner, repository
    template, wheel matrix, release gates, and a reusable Rust-rewrite skill.
  - Verify: the installed `rewrite-python-with-rust` skill passed a read-only
    forward test against `tomli==2.4.1` without dotenv-specific hard-coding.

- [ ] **11. Publish only after all gates are green**
  - Build: create the public repository, fill description/topics, push `main`,
    and run CI.
  - Verify: the public commit matches the locally accepted commit and all
    required remote checks pass.

> 上面的第 11 项保留原始历史记录，不再用于判断当前状态。当前状态请看 `PROGRESS.md`。

## Parallel execution lanes

- **Lane A — Contract:** upstream API/test inventory and compatibility matrix.
- **Lane B — Rust core:** parser, variables, fuzzing, and performance.
- **Lane C — Python surface:** filesystem APIs, logging, CLI, and IPython.
- **Lane D — Release:** dual-environment tests, wheel CI, licenses, SBOM, and
  benchmark reporting.

Lanes may work concurrently only after the contract is locked. Integration and
publication gates remain sequential because they consume all prior results.
