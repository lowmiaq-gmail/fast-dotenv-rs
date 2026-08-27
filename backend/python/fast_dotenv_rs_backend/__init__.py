"""Backend-only parser binding; no top-level ``dotenv`` facade is installed."""

from ._core import parse_bindings

__all__ = ["parse_bindings"]
