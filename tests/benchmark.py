"""Isolated Oracle-vs-candidate benchmark for dotenv_values().

The parent process never imports either package. Each worker gets an exact
PYTHONPATH containing only its implementation, so adding the candidate
``dotenv`` namespace cannot turn the Oracle comparison into a self-comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from io import StringIO
from typing import Any, Dict, Iterable, List, Tuple


ORACLE_VERSION = "1.2.2"
ORACLE_SDIST_SHA256 = "2c371a91fbd7ba082c2c1dc1f8bf89ca22564a087c2c287cd9b662adde799cf3"
ORACLE_METADATA_URL = "https://pypi.org/pypi/python-dotenv/1.2.2/json"


def make_payload(lines: int) -> str:
    body = ["# generated benchmark"]
    body.extend(f"KEY_{index}=value_{index}" for index in range(lines - 2))
    body.append("EXPANDED=${KEY_0:-fallback}")
    return "\n".join(body) + "\n"


def _validate_oracle_source(path: pathlib.Path) -> pathlib.Path:
    """Return the import root for a checked-out/extracted 1.2.2 sdist."""
    root = path / "src" if (path / "src" / "dotenv").is_dir() else path
    version_file = root / "dotenv" / "version.py"
    if not version_file.is_file() or '__version__ = "1.2.2"' not in version_file.read_text(
        encoding="utf-8"
    ):
        raise RuntimeError(f"not a python-dotenv==1.2.2 source root: {root}")
    return root.resolve()


def _download_oracle_source(temp_root: pathlib.Path) -> pathlib.Path:
    """Download and hash-check the immutable 1.2.2 source distribution."""
    with urllib.request.urlopen(ORACLE_METADATA_URL) as response:
        metadata = json.load(response)
    sdists = [
        item
        for item in metadata.get("urls", [])
        if item.get("packagetype") == "sdist"
    ]
    if len(sdists) != 1 or sdists[0].get("digests", {}).get("sha256") != ORACLE_SDIST_SHA256:
        raise RuntimeError("PyPI metadata does not match the pinned python-dotenv 1.2.2 sdist")

    archive = temp_root / "python-dotenv-1.2.2.tar.gz"
    with urllib.request.urlopen(sdists[0]["url"]) as response, archive.open("wb") as handle:
        while block := response.read(1024 * 1024):
            handle.write(block)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != ORACLE_SDIST_SHA256:
        raise RuntimeError(f"sdist SHA-256 mismatch: expected {ORACLE_SDIST_SHA256}, got {digest}")

    expected_root = "python_dotenv-1.2.2"
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if not members or any(
            member.name != expected_root
            and not member.name.startswith(expected_root + "/")
            for member in members
        ):
            raise RuntimeError("sdist contains an unexpected top-level path")
        if any(member.issym() or member.islnk() for member in members):
            raise RuntimeError("refusing an sdist containing symbolic/hard links")
        if sys.version_info >= (3, 12):
            bundle.extractall(temp_root, filter="data")
        else:
            bundle.extractall(temp_root)
    return _validate_oracle_source(temp_root / expected_root)


def _resolve_oracle_source(temp_root: pathlib.Path) -> pathlib.Path:
    configured = os.environ.get("PYTHON_DOTENV_ORACLE_SRC")
    if configured:
        return _validate_oracle_source(pathlib.Path(configured))
    return _download_oracle_source(temp_root)


def _worker(role: str, repeats: int, warmup: int, workloads: List[Dict[str, Any]]) -> None:
    """Run one side of the benchmark and emit exactly one JSON document."""
    import dotenv  # imported only inside the isolated worker

    module_file = pathlib.Path(dotenv.__file__).resolve()
    results: List[Dict[str, Any]] = []
    for workload in workloads:
        payload = workload["payload"]
        iterations = workload["iterations"]
        for _ in range(warmup):
            dotenv.dotenv_values(stream=StringIO(payload))

        samples: List[float] = []
        for _ in range(repeats):
            started = time.perf_counter_ns()
            for _ in range(iterations):
                dotenv.dotenv_values(stream=StringIO(payload))
            samples.append((time.perf_counter_ns() - started) / iterations)

        checked = dotenv.dotenv_values(stream=StringIO(payload))
        results.append(
            {
                "label": workload["label"],
                "samples_ns": samples,
                "result_type": type(checked).__name__,
                "items": list(checked.items()),
            }
        )
    print(
        json.dumps(
            {"role": role, "module_file": str(module_file), "results": results},
            ensure_ascii=False,
        )
    )


def _run_worker(
    role: str,
    python_root: pathlib.Path,
    repeats: int,
    warmup: int,
    workloads: List[Dict[str, Any]],
) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(python_root)
    env["PYTHONNOUSERSITE"] = "1"
    command = [
        sys.executable,
        str(pathlib.Path(__file__).resolve()),
        "--worker",
        role,
        "--repeats",
        str(repeats),
        "--warmup",
        str(warmup),
    ]
    process = subprocess.run(
        command,
        input=json.dumps(workloads),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"{role} worker failed with exit {process.returncode}:\n"
            f"stdout={process.stdout}\nstderr={process.stderr}"
        )
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{role} worker did not return JSON: {process.stdout!r}; stderr={process.stderr!r}"
        ) from exc
    if result.get("role") != role or process.stderr:
        raise RuntimeError(f"unexpected {role} worker output: {result!r}; stderr={process.stderr!r}")
    return result


def _summarize(
    oracle: Dict[str, Any], candidate: Dict[str, Any]
) -> Iterable[Tuple[str, int, int, float, float, float]]:
    oracle_results = oracle["results"]
    candidate_results = candidate["results"]
    if len(oracle_results) != len(candidate_results):
        raise RuntimeError("Oracle and candidate returned different workload counts")
    for oracle_result, candidate_result in zip(oracle_results, candidate_results):
        if oracle_result["label"] != candidate_result["label"]:
            raise RuntimeError("Oracle and candidate workload labels differ")
        if oracle_result["result_type"] != candidate_result["result_type"]:
            raise RuntimeError("Oracle and candidate return types differ")
        if oracle_result["items"] != candidate_result["items"]:
            raise RuntimeError(
                f"Oracle and candidate values differ for {oracle_result['label']}"
            )
        oracle_median = statistics.median(oracle_result["samples_ns"])
        candidate_median = statistics.median(candidate_result["samples_ns"])
        if candidate_median <= 0:
            raise RuntimeError("candidate benchmark produced a non-positive duration")
        yield (
            oracle_result["label"],
            len(make_payload(next(w["lines"] for w in WORKLOAD_SPECS if w["label"] == oracle_result["label"]))),
            oracle_result["samples_ns"].__len__(),
            oracle_median,
            candidate_median,
            oracle_median / candidate_median,
        )


WORKLOAD_SPECS = [
    {"label": "20 lines", "lines": 20},
    {"label": "1,000 lines", "lines": 1_000},
    {"label": "~100 KB", "lines": 5_000},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=1_000)
    parser.add_argument("--worker", choices=["oracle", "candidate"])
    args, _unknown = parser.parse_known_args()

    if args.worker:
        workloads = json.load(sys.stdin)
        _worker(args.worker, args.repeats, args.warmup, workloads)
        return

    if args.repeats < 1 or args.warmup < 0 or args.iterations < 1:
        raise SystemExit("--repeats and --iterations must be positive; --warmup cannot be negative")

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    candidate_root = repo_root / "python"
    if not (candidate_root / "dotenv" / "__init__.py").is_file():
        raise SystemExit(f"candidate dotenv source is missing: {candidate_root}")

    workloads: List[Dict[str, Any]] = []
    for spec in WORKLOAD_SPECS:
        payload = make_payload(spec["lines"])
        workloads.append(
            {
                "label": spec["label"],
                "lines": spec["lines"],
                "payload": payload,
                "iterations": max(3, args.iterations * 20 // spec["lines"]),
            }
        )

    with tempfile.TemporaryDirectory(prefix="fast-dotenv-benchmark-") as temp_dir:
        oracle_root = _resolve_oracle_source(pathlib.Path(temp_dir))
        oracle = _run_worker("oracle", oracle_root, args.repeats, args.warmup, workloads)
        candidate = _run_worker(
            "candidate", candidate_root, args.repeats, args.warmup, workloads
        )
        if oracle["module_file"] == candidate["module_file"]:
            raise RuntimeError("Oracle and candidate workers imported the same module file")

        print("| workload | bytes | repeats | oracle median | candidate median | speedup |")
        print("|---|---:|---:|---:|---:|---:|")
        for label, byte_count, repeats, oracle_ns, candidate_ns, speedup in _summarize(
            oracle, candidate
        ):
            print(
                f"| {label} | {byte_count:,} | {repeats:,} | "
                f"{oracle_ns / 1_000:.3f} us | {candidate_ns / 1_000:.3f} us | "
                f"{speedup:.3f}x |"
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
