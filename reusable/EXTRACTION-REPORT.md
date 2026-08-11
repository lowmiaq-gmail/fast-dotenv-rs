# Reusable asset extraction

This is the first dogfood extraction. It separates production-line assets from
dotenv-specific code so the next rewrite does not clone hidden assumptions.

## Reuse unchanged

- Gate order: Reuse → Correctness → Packaging → Value → Evidence.
- Repository maps, changelog, benchmark evidence and full release report.
- PyO3 abi3 + Maturin mixed-project layout.
- Release-wheel fresh-environment smoke test pattern.
- Oracle differential-test structure and deterministic generated corpus pattern.
- Cross-platform CI stages and the rule that packaged wheels, not only editable
  builds, must be tested.
- Dependency-free artifact inspector (`scripts/inspect_python_artifacts.py`):
  cardinality, filename uniqueness, metadata name/version, archive path safety,
  build leakage, and unwanted test/bytecode checks.
- Fail-closed Trusted Publishing topology: parallel native wheel lanes, isolated
  sdist lane, immutable artifact collection, OIDC-only publish job, public-index
  reinstall gates, checksums, and GitHub release creation last.
- Claim policy: no fixed speedup, “drop-in,” or “100% compatible” before gates.

## Parameterize for each project

- Upstream repository, version/tag, source hashes, license and supported Python.
- Public API slice, import namespace, signatures and declared exclusions.
- Oracle installation command and selected upstream test command.
- Benchmark workloads, minimum useful speedup and real downstream scenario.
- Wheel targets and architecture matrix.
- Registry project name, GitHub owner/repository, workflow filename, release
  environment, release-note path, version gate, and final release type.

## Never generalize

- `src/parser.rs`: python-dotenv grammar and interpolation quirks.
- `python/dotenv/`: dotenv path/stream/environment behavior and public contract.
- Dotenv fixtures, logging rules, FIFO behavior and default-file discovery.
- Measured speedup numbers.

## Candidate Skill contract

The reusable Skill should eventually accept:

```text
project=<new repository name>
upstream=<repository or package>
upstream_version=<frozen version>
target_contract=<complete replacement or explicitly scoped accelerator>
mode=audit|build|verify|release|extract
```

Fixed outputs:

```text
REUSE-AUDIT.md
UPSTREAM-CONTRACT.md
COMPATIBILITY.md
isolated differential runner
BENCHMARK.md
FULL-RELEASE-REPORT.md
CI evidence
Go | Adjust | No-Go
```

The reusable `rewrite-python-with-rust` skill has been installed, structurally
validated, and forward-tested on a read-only `tomli==2.4.1` reuse audit. It
correctly rejected existing accelerators as complete replacements and produced
the pinned contract and release gates without dotenv-specific assumptions. Its
workflow deliberately labels unrun platforms as pending until CI proves them.
