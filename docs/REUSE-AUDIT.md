# Reuse Audit

Audit date: 2026-08-10  
Compatibility baseline: [`python-dotenv==1.2.2`](https://github.com/theskumar/python-dotenv/tree/v1.2.2)  
Candidate scope: complete `dotenv` namespace, CLI, IPython integration and file/environment behavior

## Capability Registry recheck — 2026-08-12

Targeted `skill.sh find` and `skill.sh route` queries plus exact SSOT/consumer text searches did
not find the previously claimed `rewrite-python-with-rust` Skill. The claim in
`reusable/EXTRACTION-REPORT.md` is therefore **MISSING / STALE CLAIM**, not runtime evidence.
No replacement Skill is created in this release. The remediation directly reuses the verified
repository assets in `reusable/EXTRACTION-REPORT.md`, the isolated upstream/differential runners,
artifact inspector, CI matrix and immutable-release topology.

## Decision vocabulary

- **REUSE** — adopt directly; its tested behavior satisfies the frozen target.
- **ADAPT** — reuse is possible only behind a compatibility layer and after differential tests.
- **REFERENCE** — study tests, parser structure, packaging, or CI; do not import its behavior as truth.
- **REJECT** — do not add as an implementation dependency or compatibility base.

Only `python-dotenv==1.2.2` source and tests are the compatibility Oracle. A parser that handles `.env` files is not automatically a `python-dotenv` replacement.

## Candidate decisions

| Candidate | Evidence | API and semantic fit | Tests, release, license | Decision |
|---|---|---|---|---|
| [Talisberg/rusputyn `python-dotenv-rs`](https://github.com/Talisberg/rusputyn/tree/master/libraries/python-dotenv-rs) | Rust/PyO3 source and one test module are present. README says PyPI publication is planned. | Import is `dotenv_rs`, and its `dotenv_values` accepts content rather than the 1.2.2 path/stream signature. README simultaneously claims full compatibility and lists interpolation and multiline values as planned. | No verified release wheel. Repository root is MIT, while the library README says BSD and `Cargo.toml` has no license field. | **REFERENCE** only. License metadata and compatibility claims are inconsistent. |
| [`dotenvx/python-dotenvx`](https://github.com/dotenvx/python-dotenvx) | PyPI [`python-dotenvx==2.0.0`](https://pypi.org/project/python-dotenvx/) was released 2026-07-29 with CPython 3.8 abi3 wheels for Windows x86-64, Linux x86-64/aarch64, and macOS x86-64/arm64. | Exposes `dotenvx.dotenv_values`, not `dotenv.dotenv_values`. Adds decryption and dotenvx semantics. A black-box comparison found differences for bare `$VAR`, `A= # comment`, double-quoted keys, and recovery after an unterminated quote. | Repository has GitHub workflows and one Python test module. BSD-3-Clause. PyPI has wheels but no 2.0.0 sdist. | **ADAPT**, conditional on a compatibility wrapper and zero-difference Oracle suite. No code is adopted. |
| [`panzi/punktum`](https://github.com/panzi/punktum) | Rust-native multi-dialect parser with a `PythonDotenv` dialect, tests, and 159 repository commits at audit time. | No Python binding or `dotenv_values` API. The author explicitly warns that it is work in progress, not maintained, and that dialect behavior can differ. | MIT. Repository tests are useful as adversarial grammar ideas, not as the target suite. | **REFERENCE** for dialect fixtures and parser edge cases. |
| [`dotenv-rs/dotenv`](https://github.com/dotenv-rs/dotenv) | Published Rust crate with Rust tests; upstream README describes it as a v0.x implementation. | Rust API mutates the process environment. It expands both `$VAR` and `${VAR}`, and process environment values override local values. Those rules conflict with `python-dotenv==1.2.2` `dotenv_values()`. No Python binding. | MIT. Original project has been effectively superseded by the maintained `dotenvy` fork. | **REJECT** as an implementation dependency. |

## Verified `python-dotenvx` differences

The following cases were executed against the released Linux wheel for `python-dotenvx==2.0.0` and the released `python-dotenv==1.2.2` wheel. They prove “same feature” is not “drop-in compatible.”

| Input | `python-dotenv==1.2.2` | `python-dotenvx==2.0.0` |
|---|---|---|
| `A=$HOME` | literal `$HOME` | expands the environment value |
| `A= # comment` | `{"A": "# comment"}` | `{"A": ""}` |
| `"A"=1` | key is the literal string `"A"` | binding omitted |
| Unterminated quoted value followed by `NEXT=2` | invalid line skipped; `NEXT` retained | following line absorbed into the quoted value |

## User-supplied `antonmedv/fable-rs` reference

The supplied URL is <https://github.com/antonmedv/fable-rs>. During the final audit,
the repository contents could not be retrieved and `fable-rs` was not present in the
current public repository listing for [`antonmedv`](https://github.com/antonmedv?tab=repositories).
It may have been renamed, removed, made private, or the original URL may contain a typo.

Therefore this project does **not** claim to copy its layout, code, CI, benchmarks, or
release workflow. Reusing an inaccessible repository by assumption would defeat the reuse
audit. If a readable archive or corrected URL becomes available, re-audit its license,
commit, module boundary, tests, benchmark isolation and wheel workflow before adopting any
part of it.

## Final reuse decision

The complete replacement remains a clean Rust implementation using PyO3 and the frozen
upstream behavior as Oracle. The BSD-3-Clause Python facade is adapted from the pinned
upstream implementation with attribution. No source from the four alternative candidates
is copied or linked. Their public behavior and test ideas may be used only to design
adversarial fixtures until a separately reviewed ADAPT decision is recorded.

## Re-audit triggers

Re-run this audit before adopting candidate code, changing the upstream baseline, adding another public API, or publishing a full-compatibility claim. A candidate may move to REUSE only after its import path, signature, return type and order, parsing, interpolation, logging, exceptions, FIFO behavior, wheel matrix, and license all pass the project gates.
