"""Stable regression checks for the candidate ``dotenv`` namespace.

These tests deliberately import only the checkout under test.  They must run
with ``PYTHONPATH=python`` and never use an installed python-dotenv package as
an Oracle.
"""

from __future__ import annotations

import inspect
import logging
import os
import subprocess
import sys
from collections import OrderedDict
from io import StringIO
from pathlib import Path

import pytest

import dotenv
import dotenv.main as dotenv_main
from dotenv import get_cli_string
from dotenv.parser import Binding, Original, Position, Reader, parse_binding, parse_stream
from dotenv.variables import Literal, Variable, parse_variables


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "python"


def _assert_signature(obj, names, defaults):
    signature = inspect.signature(obj)
    assert list(signature.parameters) == list(names)
    assert [signature.parameters[name].default for name in names] == list(defaults)


def test_candidate_namespace_and_exports():
    assert Path(dotenv.__file__).resolve().is_relative_to(SOURCE_ROOT / "dotenv")
    assert dotenv.__all__ == [
        "get_cli_string",
        "load_dotenv",
        "dotenv_values",
        "get_key",
        "set_key",
        "unset_key",
        "find_dotenv",
        "load_ipython_extension",
    ]
    for name in dotenv.__all__:
        assert callable(getattr(dotenv, name))


def test_public_signatures_and_defaults():
    _assert_signature(
        dotenv.dotenv_values,
        ["dotenv_path", "stream", "verbose", "interpolate", "encoding"],
        [None, None, False, True, "utf-8"],
    )
    _assert_signature(
        dotenv.load_dotenv,
        ["dotenv_path", "stream", "verbose", "override", "interpolate", "encoding"],
        [None, None, False, False, True, "utf-8"],
    )
    _assert_signature(
        dotenv.find_dotenv,
        ["filename", "raise_error_if_not_found", "usecwd"],
        [".env", False, False],
    )
    _assert_signature(dotenv.get_key, ["dotenv_path", "key_to_get", "encoding"], [inspect.Parameter.empty, inspect.Parameter.empty, "utf-8"])
    _assert_signature(
        dotenv.set_key,
        ["dotenv_path", "key_to_set", "value_to_set", "quote_mode", "export", "encoding", "follow_symlinks"],
        [inspect.Parameter.empty, inspect.Parameter.empty, inspect.Parameter.empty, "always", False, "utf-8", False],
    )
    _assert_signature(
        dotenv.unset_key,
        ["dotenv_path", "key_to_unset", "quote_mode", "encoding", "follow_symlinks"],
        [inspect.Parameter.empty, inspect.Parameter.empty, "always", "utf-8", False],
    )
    _assert_signature(
        dotenv.load_ipython_extension,
        ["ipython"],
        [inspect.Parameter.empty],
    )
    _assert_signature(
        get_cli_string,
        ["path", "action", "key", "value", "quote"],
        [None, None, None, None, None],
    )
    _assert_signature(
        dotenv_main.DotEnv,
        ["dotenv_path", "stream", "verbose", "encoding", "interpolate", "override"],
        [inspect.Parameter.empty, None, False, None, True, True],
    )


def test_parser_and_variables_signatures():
    _assert_signature(Original, ["string", "line"], [inspect.Parameter.empty] * 2)
    _assert_signature(Binding, ["key", "value", "original", "error"], [inspect.Parameter.empty] * 4)
    _assert_signature(Position, ["chars", "line"], [inspect.Parameter.empty] * 2)
    _assert_signature(Reader, ["stream"], [inspect.Parameter.empty])
    _assert_signature(parse_binding, ["reader"], [inspect.Parameter.empty])
    _assert_signature(parse_stream, ["stream"], [inspect.Parameter.empty])
    _assert_signature(Literal, ["value"], [inspect.Parameter.empty])
    _assert_signature(Variable, ["name", "default"], [inspect.Parameter.empty] * 2)
    _assert_signature(parse_variables, ["value"], [inspect.Parameter.empty])


def test_dotenv_values_ordered_mapping_and_interpolation():
    values = dotenv.dotenv_values(
        stream=StringIO("FIRST=one\nSECOND=${FIRST}\nNONE\nFIRST=last\n")
    )
    assert type(values) is OrderedDict
    assert list(values.items()) == [
        ("FIRST", "last"),
        ("SECOND", "one"),
        ("NONE", None),
    ]


def test_logging_for_missing_and_invalid_input(caplog, tmp_path):
    logger = logging.getLogger("dotenv.main")
    missing = tmp_path / "missing.env"
    with caplog.at_level(logging.INFO, logger=logger.name):
        assert dotenv.dotenv_values(dotenv_path=missing, verbose=True) == {}
    assert [record.getMessage() for record in caplog.records] == [
        f"python-dotenv could not find configuration file {missing}."
    ]

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=logger.name):
        result = dotenv.dotenv_values(stream=StringIO('BROKEN="\nRECOVERED=yes\n'))
    assert result == {"RECOVERED": "yes"}
    assert [record.getMessage() for record in caplog.records] == [
        "python-dotenv could not parse statement starting at line 1"
    ]


def test_load_override_and_disabled_environment(monkeypatch):
    monkeypatch.setenv("EXISTING", "from-environment")
    source = StringIO("EXISTING=from-file\nNEW=created\nNONE\n")
    assert dotenv.load_dotenv(stream=source, override=False) is True
    assert os.environ["EXISTING"] == "from-environment"
    assert os.environ["NEW"] == "created"
    assert "NONE" not in os.environ

    monkeypatch.setenv("EXISTING", "from-environment")
    assert dotenv.load_dotenv(
        stream=StringIO("EXISTING=from-file\n"), override=True
    ) is True
    assert os.environ["EXISTING"] == "from-file"

    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "YES")
    monkeypatch.delenv("DISABLED_VALUE", raising=False)
    assert dotenv.load_dotenv(stream=StringIO("DISABLED_VALUE=x\n")) is False
    assert "DISABLED_VALUE" not in os.environ


def test_set_get_unset_and_cli_string(tmp_path):
    path = tmp_path / ".env"
    assert dotenv.set_key(path, "SECRET", "a b") == (True, "SECRET", "a b")
    assert path.read_text() == "SECRET='a b'\n"
    assert dotenv.get_key(path, "SECRET") == "a b"
    assert dotenv.unset_key(path, "SECRET") == (True, "SECRET")
    assert path.read_text() == ""

    assert get_cli_string() == "dotenv"
    assert get_cli_string(path="/etc/.env", action="set", key="SECRET", value="a b", quote="always") == (
        'dotenv -q always -f /etc/.env set SECRET "a b"'
    )


def test_module_and_cli_imports_in_candidate_environment():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["PYTHONNOUSERSITE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "dotenv", "--version"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "0.1.0" in result.stdout

    from dotenv.cli import cli

    assert callable(cli)
