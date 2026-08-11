# fast-dotenv-rs 0.1.0

First public alpha release of the Rust-backed drop-in replacement for
`python-dotenv==1.2.2`.

## Compatibility evidence

- complete pinned upstream suite passes without selection filters;
- deterministic 10,000-case Oracle/candidate differential gate passes;
- release wheels are built, installed, and retested natively on Linux x86-64,
  Linux arm64, macOS Apple Silicon, macOS Intel, and Windows x86-64;
- the source distribution is rebuilt into a wheel and installed before publish;
- after Trusted Publishing, every advertised platform installs the public PyPI
  package and reruns the complete upstream suite before this pre-release is created.

Install the candidate distribution while keeping the upstream import contract:

```bash
pip install "fast-dotenv-rs[cli]==0.1.0"
```

```python
from dotenv import load_dotenv

load_dotenv()
```

The distribution name is `fast-dotenv-rs`; the import namespace and CLI remain
`dotenv`. Do not install `python-dotenv` and `fast-dotenv-rs` in the same Python
environment because both distributions intentionally provide that namespace.
