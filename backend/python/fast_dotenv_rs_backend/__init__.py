"""Backend-only parser binding; no top-level ``dotenv`` facade is installed."""

from ._core import BACKEND_CONTRACT, BACKEND_CONTRACT_VERSION, parse_bindings

__all__ = ["BACKEND_CONTRACT", "BACKEND_CONTRACT_VERSION", "parse_bindings"]
