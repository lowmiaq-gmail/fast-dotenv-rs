#!/usr/bin/env python3
"""Run an isolated, deterministic python-dotenv 1.2.2 differential gate.

The parent process never imports ``dotenv``. Oracle and candidate workers get
disjoint PYTHONPATH values and return normalized JSON observations. A matching
module path, value, parser/variable structure, warning, exception, and
resolution result is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from io import StringIO
from typing import Any, Dict, List


ORACLE_SHA256 = "2c371a91fbd7ba082c2c1dc1f8bf89ca22564a087c2c287cd9b662adde799cf3"
ORACLE_METADATA_URL = "https://pypi.org/pypi/python-dotenv/1.2.2/json"


def _validate_oracle_source(path: pathlib.Path) -> pathlib.Path:
    root = path / "src" if (path / "src" / "dotenv").is_dir() else path
    version_file = root / "dotenv" / "version.py"
    if not version_file.is_file() or '__version__ = "1.2.2"' not in version_file.read_text(
        encoding="utf-8"
    ):
        raise RuntimeError(f"not a python-dotenv 1.2.2 source root: {root}")
    return root.resolve()


def _oracle_source(temp_root: pathlib.Path, configured: str | None) -> pathlib.Path:
    if configured:
        return _validate_oracle_source(pathlib.Path(configured))
    with urllib.request.urlopen(ORACLE_METADATA_URL) as response:
        metadata = json.load(response)
    sdists = [item for item in metadata["urls"] if item["packagetype"] == "sdist"]
    if len(sdists) != 1 or sdists[0]["digests"]["sha256"] != ORACLE_SHA256:
        raise RuntimeError("PyPI metadata does not match the pinned 1.2.2 sdist")
    archive = temp_root / "python-dotenv-1.2.2.tar.gz"
    with urllib.request.urlopen(sdists[0]["url"]) as response, archive.open("wb") as out:
        while block := response.read(1024 * 1024):
            out.write(block)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ORACLE_SHA256:
        raise RuntimeError("python-dotenv 1.2.2 sdist SHA-256 mismatch")
    root_name = "python_dotenv-1.2.2"
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if not members or any(
            member.name != root_name and not member.name.startswith(root_name + "/")
            for member in members
        ) or any(member.issym() or member.islnk() for member in members):
            raise RuntimeError("unsafe or unexpected sdist layout")
        if sys.version_info >= (3, 12):
            bundle.extractall(temp_root, filter="data")
        else:
            bundle.extractall(temp_root)
    return _validate_oracle_source(temp_root / root_name)


def _normalize_binding(binding: Any) -> Dict[str, Any]:
    return {
        "key": binding.key,
        "value": binding.value,
        "original": {"string": binding.original.string, "line": binding.original.line},
        "error": binding.error,
    }


def _normalize_atom(atom: Any) -> Dict[str, Any]:
    result = {"type": type(atom).__name__}
    for name in ("value", "name", "default"):
        if hasattr(atom, name):
            result[name] = getattr(atom, name)
    return result


def _exception(callable_: Any) -> Dict[str, Any]:
    try:
        value = callable_()
    except BaseException as exc:  # observations are compared, not swallowed
        return {
            "ok": False,
            "exception": {"type": type(exc).__name__, "args": list(exc.args)},
        }
    return {"ok": True, "value": value}


def _dotenv_observation(dotenv: Any, case: Dict[str, Any]) -> Dict[str, Any]:
    import logging

    os.environ.clear()
    os.environ.update(case.get("environment", {}))
    records: List[Dict[str, Any]] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(
                {"name": record.name, "level": record.levelname, "message": record.getMessage()}
            )

    logger = logging.getLogger("dotenv.main")
    handler = Capture()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        if case["kind"] == "boom_stream":
            class BoomStream:
                def read(self) -> str:
                    raise RuntimeError("boom")

            call = lambda: dotenv.dotenv_values(stream=BoomStream())
        else:
            call = lambda: dotenv.dotenv_values(
                stream=StringIO(case["text"]), interpolate=case.get("interpolate", True)
            )
        observed = _exception(call)
    finally:
        logger.removeHandler(handler)
    observed["logs"] = records
    if observed["ok"]:
        observed["value"] = {
            "type": type(observed["value"]).__name__,
            "items": list(observed["value"].items()),
        }
    return observed


def _worker(role: str, cases: Dict[str, Any]) -> None:
    import dotenv
    import dotenv.main as main
    from dotenv.parser import parse_stream
    from dotenv.variables import parse_variables

    module_file = str(pathlib.Path(dotenv.__file__).resolve())
    result: Dict[str, Any] = {"role": role, "module_file": module_file}
    result["dotenv"] = [_dotenv_observation(dotenv, case) for case in cases["dotenv"]]
    result["parser"] = [
        [_normalize_binding(binding) for binding in parse_stream(StringIO(text))]
        for text in cases["parser"]
    ]
    result["variables"] = [
        [_normalize_atom(atom) for atom in parse_variables(text)] for text in cases["variables"]
    ]
    resolved = []
    for case in cases["resolve"]:
        os.environ.clear()
        os.environ.update(case["environment"])
        resolved.append(
            list(main.resolve_variables(case["values"], override=case["override"]).items())
        )
    result["resolve"] = resolved
    print(json.dumps(result, ensure_ascii=False))


def _run_worker(role: str, source_root: pathlib.Path, cases: Dict[str, Any]) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    env["PYTHONNOUSERSITE"] = "1"
    process = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve()), "--worker", role],
        input=json.dumps(cases),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"{role} worker failed ({process.returncode}): {process.stderr}")
    if process.stderr:
        raise RuntimeError(f"{role} worker wrote stderr: {process.stderr}")
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{role} worker returned invalid JSON: {process.stdout!r}") from exc
    if result.get("role") != role:
        raise RuntimeError(f"worker role mismatch: expected {role}, got {result.get('role')}")
    return result


def _cases(seed: int, count: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    keys = ["A", "B", "NAME", "KEY_1", "x-y", "é"]
    values = ["", "plain", "two words", "hash#value", "${A}", "${MISSING:-fallback}", "héllo"]
    parser_cases = [
        "A=1\nB=two # comment\nEMPTY=\nNONE\n",
        "SINGLE='hello\\'world'\nDOUBLE=\"line\\nnext\"\n",
        "MULTI=\"one\ntwo\"\r\nCR=ok\rNEXT=2\n",
        'BROKEN="\nRECOVERED=yes\n',
    ]
    variable_cases = ["${A}", "pre${MISSING:-fallback}post", "$A", "${A}${B}", "${}"]
    formats = [
        lambda key, value: f"{key}={value}",
        lambda key, value: f" {key} = {value} ",
        lambda key, value: f"export {key}={value}",
        lambda key, value: f"{key}='{value}'",
        lambda key, value: f'{key}="{value}"',
        lambda key, _value: key,
    ]
    for _ in range(count):
        lines = []
        for _ in range(rng.randint(0, 8)):
            lines.append(
                "# comment"
                if rng.random() < 0.15
                else rng.choice(formats)(rng.choice(keys), rng.choice(values))
            )
        parser_cases.append(rng.choice(["\n", "\r\n", "\r"]).join(lines))
    dotenv_cases = [
        {"kind": "text", "text": text, "environment": {"A": "from-env"}}
        for text in parser_cases[:]
    ]
    dotenv_cases.extend(
        [
            {
                "kind": "text",
                "text": "BROKEN=\"\nRECOVERED=yes\n",
                "environment": {},
            },
            {"kind": "boom_stream", "environment": {}},
        ]
    )
    resolve_cases = [
        {
            "environment": {"A": "env-a", "B": "env-b"},
            "values": [["A", "file-a"], ["B", "${A}"], ["C", "${MISSING:-fallback}"]],
            "override": True,
        },
        {
            "environment": {"A": "env-a"},
            "values": [["A", "file-a"], ["B", "${A}"], ["NONE", None]],
            "override": False,
        },
    ]
    return {
        "parser": parser_cases,
        "variables": variable_cases,
        "dotenv": dotenv_cases,
        "resolve": resolve_cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=["oracle", "candidate"])
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--cases", type=int, default=10_000)
    parser.add_argument("--oracle-src")
    args = parser.parse_args()
    if args.worker:
        _worker(args.worker, json.load(sys.stdin))
        return 0
    if args.cases < 1:
        raise SystemExit("--cases must be positive")
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    cases = _cases(args.seed, args.cases)
    with tempfile.TemporaryDirectory(prefix="dotenv-diff-") as temp:
        oracle_root = _oracle_source(pathlib.Path(temp), args.oracle_src or os.environ.get("PYTHON_DOTENV_ORACLE_SRC"))
        candidate_root = repo_root / "python"
        oracle = _run_worker("oracle", oracle_root, cases)
        candidate = _run_worker("candidate", candidate_root, cases)
        if oracle["module_file"] == candidate["module_file"]:
            raise RuntimeError("Oracle and candidate imported the same module file")
        comparable = ["parser", "variables", "resolve", "dotenv"]
        mismatches = [name for name in comparable if oracle[name] != candidate[name]]
        if mismatches:
            raise RuntimeError(f"differential mismatch in: {', '.join(mismatches)}")
    print(
        f"isolated differential passed: seed={args.seed}, random_cases={args.cases}, "
        f"parser={len(cases['parser'])}, variables={len(cases['variables'])}, "
        f"resolve={len(cases['resolve'])}, dotenv={len(cases['dotenv'])}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"differential failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
