# fast-dotenv-rs-backend

This distribution contains only a Rust/PyO3 parser backend for an upstream
dotenv-compatible adapter. It installs `fast_dotenv_rs_backend`, exposes only
`parse_bindings(text)`, and deliberately does not install the top-level
`dotenv` package or a `dotenv` console script. It is intended to coexist with
the official `python-dotenv` distribution.

Adapters must validate these markers before using the binding:

```python
BACKEND_CONTRACT == "fast-dotenv-rs.backend.binding"
BACKEND_CONTRACT_VERSION == 1
```

The versioned contract returns only `(key, value, original.string,
original.line, error)` records from `parse_bindings(text)`.
