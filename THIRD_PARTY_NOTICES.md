# Third-Party Notices and Provenance

This document records upstream material, runtime dependencies, and reuse candidates reviewed for the complete replacement. It is not a lockfile or a complete software bill of materials; inspect the final release dependency graph and artifacts before publication.

## Included runtime dependency

### PyO3

- Project: <https://github.com/PyO3/pyo3>
- Declared version range: `0.24`
- Use: Python extension bindings
- License: Apache-2.0 OR MIT

The release process must preserve notices required by the selected PyO3 license and by its resolved transitive dependencies.

## Compatibility Oracle and test provenance

### python-dotenv 1.2.2

- Project: <https://github.com/theskumar/python-dotenv/tree/v1.2.2>
- Distribution: <https://pypi.org/project/python-dotenv/>
- License: BSD-3-Clause
- Copyright notice in the 1.2.2 distribution: Copyright (c) 2014, Saurabh Kumar (python-dotenv), 2013, Ted Tieken (django-dotenv-rw), 2013, Jacob Kaplan-Moss (django-dotenv).

The pinned package remains the behavioral Oracle. Its Python-facing API,
filesystem, CLI, and IPython implementation is also used as the BSD-3-Clause
compatibility baseline while the CPU hot paths are replaced by Rust. Adapted
source and test material retains the complete license in
`licenses/python-dotenv-BSD-3-Clause.txt`; binary distributions must include
that notice as well.

The Rust parser is independently authored, but its behavior is verified against
the pinned upstream implementation and tests.

## Evaluated candidates not included

No source or binary from the following candidates is currently bundled, linked, vendored, or copied. They create no runtime dependency; their licenses are recorded so that any later ADAPT decision starts with an explicit review.

| Candidate | Recorded license | Inclusion status and caveat |
|---|---|---|
| [Talisberg/rusputyn](https://github.com/Talisberg/rusputyn) `python-dotenv-rs` | Repository root: MIT. Library README says BSD; library `Cargo.toml` omits a license field. | Not included. Do not copy until the conflicting metadata and exact copyright notice are resolved. |
| [`dotenvx/python-dotenvx`](https://github.com/dotenvx/python-dotenvx) 2.0.0 | BSD-3-Clause, copyright (c) 2024 Scott Motte | Not included. Released wheel was used only for black-box behavior comparison. |
| [`panzi/punktum`](https://github.com/panzi/punktum) | MIT | Not included. Consulted only as a multi-dialect parser reference. |
| [`dotenv-rs/dotenv`](https://github.com/dotenv-rs/dotenv) | MIT, copyright (c) 2014 Santiago Lapresta and contributors | Not included. Rejected as an implementation dependency because its API and interpolation precedence differ from the target. |

## Release checklist

Before a release, verify the resolved Cargo and Python dependency graphs, include all required license texts/notices in source and wheel artifacts, identify every copied or adapted upstream test, and update this file if any candidate changes from evaluation-only to included code. Maturin's generated Rust SBOM is disabled until it can be produced without embedding the local checkout path; artifact inspection must reject any absolute build-path leak.
