# fast-dotenv-rs

[![CI](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/workflows/ci.yml/badge.svg)](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/Rust-PyO3-orange.svg)](https://pyo3.rs/)
[![License](https://img.shields.io/badge/license-MIT%20AND%20BSD--3--Clause-green.svg)](LICENSE)

A fast Rust-backed drop-in replacement for `python-dotenv==1.2.2`, built with
PyO3 and Maturin. It preserves the `dotenv` Python API, CLI, IPython extension,
interpolation rules, and file mutation behavior.

[中文说明](README.zh-CN.md)

```python
from dotenv import dotenv_values, load_dotenv

load_dotenv()
config = dotenv_values(".env")
```

The distribution is named `fast-dotenv-rs`, but existing application code keeps
importing `dotenv`.

## Why this project

- **Low migration cost:** keep `from dotenv import load_dotenv` and the `dotenv` CLI.
- **Verifiable compatibility:** run the complete pinned `python-dotenv==1.2.2`
  upstream suite, not only basic `KEY=value` examples.
- **Reproducible performance evidence:** compare candidate and Oracle in isolated
  processes and validate values, types, and ordering before timing.
- **Cross-platform packaging:** build abi3 wheels with PyO3 and Maturin.

## Status

This is a public pre-release source repository. It has not yet been published to
PyPI and no GitHub Release has been created.

[GitHub Actions CI #3](https://github.com/lowmiaq-gmail/fast-dotenv-rs/actions/runs/31511953697)
passed all four jobs:

| Platform | Python | Installed-wheel verification |
|---|---:|---|
| Linux x86-64 | 3.10 and 3.12 | Rust gates, project tests, 10,000-case differential gate, full upstream suite, artifact audit |
| macOS arm64 | 3.12 | wheel install, CLI, 219 upstream tests passed |
| Windows x86-64 | 3.12 | wheel install, CLI, 169 passed / 50 upstream platform skips |

The local Linux x86-64 / CPython 3.12 upstream result is:

```text
218 passed, 1 skipped, 0 failed
```

The single Linux skip is an upstream platform/root condition. IPython was installed,
so all three upstream IPython tests ran.

## Installation

There is no PyPI package yet. Build from source:

```bash
git clone https://github.com/lowmiaq-gmail/fast-dotenv-rs.git
cd fast-dotenv-rs
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -U pip maturin
python -m pip install "click>=5" # optional, required for the CLI
maturin develop --release
```

Build a wheel:

```bash
maturin build --release --out wheelhouse
python -m pip install wheelhouse/*.whl
```

### Do not install the Oracle in the same environment

Both `python-dotenv` and this project provide the top-level `dotenv` package and
the `dotenv` command. Installing both in one environment causes the last installed
distribution to overwrite the other. Use separate virtual environments for
candidate/Oracle comparisons.

## Compatible surface

Top-level exports match `python-dotenv==1.2.2`:

```python
from dotenv import (
    dotenv_values, find_dotenv, get_cli_string, get_key,
    load_dotenv, load_ipython_extension, set_key, unset_key,
)
```

The compatibility surface also includes:

- `dotenv.main.DotEnv`, `rewrite`, and `resolve_variables`;
- parser `Binding`, `Original`, `Reader`, `Position`, and parser functions;
- variable `Atom`, `Literal`, `Variable`, and `parse_variables`;
- CLI `list`, `set`, `get`, `unset`, and `run`;
- `dotenv.ipython.IPythonDotEnv` and the `%dotenv` magic.

See [`docs/UPSTREAM-CONTRACT.md`](docs/UPSTREAM-CONTRACT.md) for signatures,
return values, logging, exceptions, filesystem effects, and environment behavior.

## CLI

```bash
dotenv list
dotenv list --format=json
dotenv set DATABASE_URL 'postgres://localhost/app'
dotenv get DATABASE_URL
dotenv unset DATABASE_URL
dotenv run -- python app.py
python -m dotenv --version
```

## Reproduce the compatibility gates

```bash
python -m pip install "pytest>=8,<9" "click>=5" "ipython>=8"
cargo test --all-targets
PYTHONPATH=python python -m pytest -q tests
bash scripts/run_upstream_full.sh
PYTHONPATH=python python scripts/run_differential.py
```

The upstream runner pins and verifies the official `python-dotenv==1.2.2` sdist
and every upstream test fixture hash. It also checks that the candidate, not an
installed Oracle, owns the imported `dotenv` namespace.

## Benchmark snapshot

On one Linux x86-64 / CPython 3.12 machine, isolated-process `dotenv_values()`
in-memory parsing workloads measured **15.957×–88.609×** faster. The harness checks
the return type, item order, and values before timing.

```bash
python tests/benchmark.py --repeats 7 --warmup 2 --iterations 1000
```

These numbers do not represent file I/O, process startup, macOS, Windows, or every
application workload. See [`BENCHMARK.md`](BENCHMARK.md) for inputs, raw context,
and limitations.

## Documentation

- [`FULL-RELEASE-REPORT.md`](FULL-RELEASE-REPORT.md) — current evidence and remaining release gates;
- [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) — compatibility matrix;
- [`docs/UPSTREAM-CONTRACT.md`](docs/UPSTREAM-CONTRACT.md) — pinned upstream contract;
- [`docs/REUSE-AUDIT.md`](docs/REUSE-AUDIT.md) — reuse and license audit;
- [`docs/LAUNCH-SEO.md`](docs/LAUNCH-SEO.md) — launch, discovery, and adoption plan.

## License

Rust/PyO3 project code is MIT licensed. BSD-3-Clause notices for the upstream
compatibility baseline are recorded in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
and [`licenses/`](licenses/).
