# fast-dotenv-rs-backend

This distribution contains only a Rust/PyO3 parser backend for an upstream
dotenv-compatible adapter. It installs `fast_dotenv_rs_backend`, exposes only
`parse_bindings(text)`, and deliberately does not install the top-level
`dotenv` package or a `dotenv` console script. It is intended to coexist with
the official `python-dotenv` distribution.
