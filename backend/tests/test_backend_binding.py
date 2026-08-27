from fast_dotenv_rs_backend import (
    BACKEND_CONTRACT,
    BACKEND_CONTRACT_VERSION,
    parse_bindings,
)
from fast_dotenv_rs_backend import _core


def test_binding_payload_preserves_upstream_fields() -> None:
    assert parse_bindings(
        "FIRST=one\n# comment\nBROKEN=\"\nRECOVERED=yes\nNONE\n"
    ) == [
        ("FIRST", "one", "FIRST=one\n", 1, False),
        (None, None, "# comment\n", 2, False),
        (None, None, 'BROKEN="\n', 3, True),
        ("RECOVERED", "yes", "RECOVERED=yes\n", 4, False),
        ("NONE", None, "NONE\n", 5, False),
    ]


def test_backend_module_does_not_expose_high_level_or_resolved_api() -> None:
    assert _core.parse_bindings is parse_bindings
    assert not hasattr(_core, "parse_text")
    assert not hasattr(_core, "parse_resolved")
    assert not hasattr(_core, "parse_variable_atoms")


def test_backend_contract_marker_is_strict_and_explicit() -> None:
    assert BACKEND_CONTRACT == "fast-dotenv-rs.backend.binding"
    assert BACKEND_CONTRACT_VERSION == 1
    assert _core.BACKEND_CONTRACT == BACKEND_CONTRACT
    assert _core.BACKEND_CONTRACT_VERSION == BACKEND_CONTRACT_VERSION
