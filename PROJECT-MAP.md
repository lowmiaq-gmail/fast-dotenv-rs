# Project map

This file is the repository-level navigation map. Detailed behavior belongs in
the nearest source file or evidence document; this map does not duplicate it.

| Path | Responsibility |
|---|---|
| `src/` | Rust parsing, interpolation and PyO3 binding |
| `python/dotenv/` | Drop-in-compatible `python-dotenv` namespace and Python-specific behavior |
| `tests/` | Candidate contract, packaging smoke and isolated benchmark |
| `docs/` | Upstream pin, reuse decisions and declared compatibility boundary |
| `reusable/` | Dogfood extraction and future Skill contract |
| `scripts/` | Reproducible verification helpers |
| `.github/workflows/` | Cross-platform build and verification gates |

## Recursive maps

### `src/`

- `lib.rs`: minimal PyO3 module registration and Rust/Python data boundary.
- `parser.rs`: pure Rust parser and interpolation engine plus Rust unit tests.

### `python/dotenv/`

- `main.py`: file discovery, environment mutation, atomic rewrite, and public
  high-level API.
- `parser.py`: upstream-compatible parser data model and compatibility layer.
- `variables.py`: upstream-compatible interpolation objects and tokenization.
- `cli.py`, `__main__.py`: optional Click CLI and module/console entry point.
- `ipython.py`: `%dotenv` extension.

### `tests/`

- `test_dropin_contract.py`: candidate-only namespace, signatures, return-contract,
  logging, environment, file mutation and CLI checks.
- `benchmark.py`: separate-process Oracle/candidate comparison with semantic checks.

### `scripts/`

- `run_upstream_full.sh`: immutable 1.2.2 source and full official-suite gate.
- `run_differential.py`: deterministic, isolated Oracle/candidate differential gate.
