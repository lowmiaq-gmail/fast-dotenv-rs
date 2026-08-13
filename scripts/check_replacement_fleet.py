#!/usr/bin/env python3
"""Verify public lifecycle health for the released Python-to-Rust fleet."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable
import urllib.error
import urllib.request
import venv


DEFAULT_MANIFEST = Path(__file__).parents[1] / "reusable" / "replacement-fleet.json"
PUBLIC_INDEX = "https://pypi.org/simple"
REQUIRED_PACKAGE_FIELDS = {
    "distribution",
    "version",
    "repository",
    "release_tag",
    "upstream_distribution",
    "upstream_version",
    "import_name",
    "native_module",
    "smoke",
    "fallback_wheel",
}


class CheckFailure(RuntimeError):
    """A deterministic lifecycle gate failed."""


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise CheckFailure("manifest schema_version must be 1")
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not packages:
        raise CheckFailure("manifest packages must be a non-empty list")
    distributions: set[str] = set()
    repositories: set[str] = set()
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            raise CheckFailure(f"packages[{index}] must be an object")
        missing = REQUIRED_PACKAGE_FIELDS - package.keys()
        if missing:
            raise CheckFailure(
                f"packages[{index}] missing fields: {', '.join(sorted(missing))}"
            )
        distribution = package["distribution"]
        repository = package["repository"]
        if distribution in distributions:
            raise CheckFailure(f"duplicate distribution: {distribution}")
        if repository in repositories:
            raise CheckFailure(f"duplicate repository: {repository}")
        distributions.add(distribution)
        repositories.add(repository)
    if len(packages) != 7:
        raise CheckFailure(f"expected the seven released libraries, found {len(packages)}")
    return manifest


def fetch_json(url: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json, application/json",
        "User-Agent": "fast-dotenv-rs-fleet-lifecycle-monitor",
    }
    token = os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise CheckFailure(f"expected JSON object from {url}")
            return payload
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
    raise CheckFailure(f"could not fetch {url}: {last_error}")


def result(library: str, gate: str, status: str, evidence: str) -> dict[str, str]:
    return {
        "library": library,
        "gate": gate,
        "status": status,
        "evidence": evidence,
    }


def audit_public(
    manifest: dict[str, Any],
    fetcher: Callable[[str], dict[str, Any]] = fetch_json,
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for package in manifest["packages"]:
        distribution = package["distribution"]
        try:
            pypi = fetcher(
                f"https://pypi.org/pypi/{distribution}/{package['version']}/json"
            )
            latest_upstream = fetcher(
                f"https://pypi.org/pypi/{package['upstream_distribution']}/json"
            )
            release = fetcher(
                "https://api.github.com/repos/"
                f"{package['repository']}/releases/tags/{package['release_tag']}"
            )

            info = pypi.get("info") or {}
            if info.get("name", "").lower() != distribution.lower():
                raise CheckFailure(f"PyPI name mismatch: {info.get('name')!r}")
            if info.get("version") != package["version"]:
                raise CheckFailure(f"PyPI version mismatch: {info.get('version')!r}")
            urls = pypi.get("urls") or []
            if not urls:
                raise CheckFailure("PyPI release has no files")
            pypi_files = {
                item["filename"]: item.get("digests", {}).get("sha256") for item in urls
            }
            if any(not digest for digest in pypi_files.values()):
                raise CheckFailure("a PyPI file is missing SHA256")
            if not any(name.endswith(".whl") for name in pypi_files):
                raise CheckFailure("PyPI release has no wheel")
            if not any(name.endswith(".tar.gz") for name in pypi_files):
                raise CheckFailure("PyPI release has no sdist")

            if release.get("draft") is not False or release.get("prerelease") is not False:
                raise CheckFailure("GitHub Release is draft or prerelease")
            if release.get("tag_name") != package["release_tag"]:
                raise CheckFailure(f"GitHub tag mismatch: {release.get('tag_name')!r}")
            release_assets = {
                item.get("name"): item.get("digest") for item in release.get("assets") or []
            }
            missing_assets = sorted(set(pypi_files) - set(release_assets))
            if missing_assets:
                raise CheckFailure(
                    "GitHub Release missing PyPI files: " + ", ".join(missing_assets)
                )
            digest_mismatches = sorted(
                name
                for name, digest in pypi_files.items()
                if release_assets.get(name) != f"sha256:{digest}"
            )
            if digest_mismatches:
                raise CheckFailure(
                    "PyPI/GitHub digest mismatch: " + ", ".join(digest_mismatches)
                )
            if "SHA256SUMS" not in release_assets:
                raise CheckFailure("GitHub Release is missing SHA256SUMS")

            upstream_latest = (latest_upstream.get("info") or {}).get("version")
            if upstream_latest != package["upstream_version"]:
                raise CheckFailure(
                    "upstream version drift: frozen="
                    f"{package['upstream_version']} latest={upstream_latest}"
                )
            results.append(
                result(
                    distribution,
                    "public-contract",
                    "PASS",
                    f"{len(pypi_files)} PyPI files match GitHub Release digests; "
                    f"upstream remains {upstream_latest}",
                )
            )
        except (CheckFailure, KeyError, TypeError) as exc:
            results.append(result(distribution, "public-contract", "FAIL", str(exc)))
    return results


def venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run_command(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True)
    if check and completed.returncode != 0:
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        raise CheckFailure(f"command failed ({completed.returncode}): {' '.join(command)}\n{output}")
    return completed


def create_venv(root: Path) -> Path:
    venv.EnvBuilder(with_pip=True, clear=True).create(root)
    python = venv_python(root)
    run_command([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    return python


def install_fleet(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory(prefix="replacement-fleet-install-") as temp:
        python = create_venv(Path(temp) / "venv")
        requirements = [
            f"{package['distribution']}=={package['version']}"
            for package in manifest["packages"]
        ]
        try:
            run_command(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--index-url",
                    PUBLIC_INDEX,
                    "--only-binary=:all:",
                    *requirements,
                ]
            )
            run_command([str(python), "-m", "pip", "check"])
            completed = run_command(
                [str(python), str(Path(__file__)), "installed-smoke", str(manifest_path)]
            )
            evidence = completed.stdout.strip() or "installed smoke passed"
            return [result("fleet", "fresh-public-install", "PASS", evidence)]
        except CheckFailure as exc:
            return [result("fleet", "fresh-public-install", "FAIL", str(exc))]


def installed_smoke(manifest: dict[str, Any]) -> None:
    for package in manifest["packages"]:
        observed = importlib.metadata.version(package["distribution"])
        if observed != package["version"]:
            raise CheckFailure(
                f"{package['distribution']} version mismatch: {observed}"
            )
        module = importlib.import_module(package["import_name"])
        if importlib.util.find_spec(package["native_module"]) is None:
            raise CheckFailure(
                f"{package['distribution']} did not install native module "
                f"{package['native_module']}"
            )
        smoke = package["smoke"]
        if smoke == "dotenv":
            import io

            if module.dotenv_values(stream=io.StringIO("FLEET=ok\n")) != {"FLEET": "ok"}:
                raise CheckFailure("dotenv smoke mismatch")
        elif smoke == "rfc3339_validator":
            if not module.validate_rfc3339("2026-08-13T00:00:00Z"):
                raise CheckFailure("rfc3339 validator smoke mismatch")
        elif smoke == "roman":
            if module.toRoman(42) != "XLII" or module.fromRoman("XLII") != 42:
                raise CheckFailure("roman smoke mismatch")
        elif smoke == "base58":
            encoded = module.b58encode(b"fleet")
            if module.b58decode(encoded) != b"fleet":
                raise CheckFailure("base58 smoke mismatch")
        elif smoke == "iso8601":
            parsed = module.parse_date("2026-08-13T00:00:00Z")
            if parsed.isoformat() != "2026-08-13T00:00:00+00:00":
                raise CheckFailure("iso8601 smoke mismatch")
        elif smoke == "mdurl":
            encoded = module.encode("https://example.com/a b")
            if module.decode(encoded) != "https://example.com/a b":
                raise CheckFailure("mdurl smoke mismatch")
        elif smoke == "semver":
            if str(module.Version.parse("1.2.3-rc.1")) != "1.2.3-rc.1":
                raise CheckFailure("semver smoke mismatch")
        else:
            raise CheckFailure(f"unknown smoke id: {smoke}")
    print(f"seven native imports and API smokes passed on Python {sys.version.split()[0]}")


def check_fallbacks(manifest: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="replacement-fleet-fallback-") as temp:
        root = Path(temp)
        tools_python = create_venv(root / "tools")
        for package in manifest["packages"]:
            expected = package["fallback_wheel"]
            if expected is None:
                results.append(
                    result(
                        package["distribution"],
                        "fallback-selection",
                        "SKIP",
                        "manifest declares native-only release",
                    )
                )
                continue
            destination = root / package["distribution"]
            destination.mkdir()
            try:
                run_command(
                    [
                        str(tools_python),
                        "-m",
                        "pip",
                        "download",
                        "--index-url",
                        PUBLIC_INDEX,
                        "--only-binary=:all:",
                        "--no-deps",
                        "--platform",
                        "manylinux2014_i686",
                        "--python-version",
                        "3.12",
                        "--implementation",
                        "cp",
                        "--abi",
                        "cp312",
                        "--dest",
                        str(destination),
                        f"{package['distribution']}=={package['version']}",
                    ]
                )
                selected = sorted(path.name for path in destination.iterdir())
                if selected != [expected]:
                    raise CheckFailure(
                        f"expected {expected}, selected {', '.join(selected) or 'nothing'}"
                    )
                results.append(
                    result(
                        package["distribution"],
                        "fallback-selection",
                        "PASS",
                        f"unsupported i686 target selected {expected}",
                    )
                )
            except CheckFailure as exc:
                results.append(
                    result(package["distribution"], "fallback-selection", "FAIL", str(exc))
                )
    return results


def check_real_consumer(manifest: dict[str, Any]) -> list[dict[str, str]]:
    consumer = manifest["real_consumer"]
    with tempfile.TemporaryDirectory(prefix="replacement-fleet-consumer-") as temp:
        python = create_venv(Path(temp) / "venv")
        try:
            run_command(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--index-url",
                    PUBLIC_INDEX,
                    f"{consumer['replacement_distribution']}=={consumer['replacement_version']}",
                ]
            )
            run_command(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--index-url",
                    PUBLIC_INDEX,
                    "--no-deps",
                    f"{consumer['distribution']}=={consumer['version']}",
                ]
            )
            smoke = run_command(
                [
                    str(python),
                    "-c",
                    "from markdown_it import MarkdownIt; "
                    "html=MarkdownIt().render('[fleet](https://example.com/a%20b)'); "
                    "assert '<a href=\"https://example.com/a%20b\">fleet</a>' in html; "
                    "import mdurl._native",
                ]
            )
            pip_check = run_command([str(python), "-m", "pip", "check"], check=False)
            resolver_output = (pip_check.stdout + pip_check.stderr).strip()
            expected = consumer["expected_resolver_limitation"]
            if pip_check.returncode == 0 or expected not in resolver_output:
                raise CheckFailure(
                    "expected the documented resolver limitation, observed: "
                    f"returncode={pip_check.returncode} output={resolver_output!r}"
                )
            evidence = (
                f"{consumer['distribution']} {consumer['version']} rendered through "
                f"the native mdurl backend; pip check reproduced {expected!r}"
            )
            if smoke.stdout.strip():
                evidence += f"; {smoke.stdout.strip()}"
            return [result("fast-mdurl-rs", "real-consumer", "PASS", evidence)]
        except CheckFailure as exc:
            return [result("fast-mdurl-rs", "real-consumer", "FAIL", str(exc))]


def render(results: list[dict[str, str]]) -> str:
    lines = [
        "# Replacement fleet lifecycle",
        "",
        f"Observed at: `{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}`",
        "",
        "| Library | Gate | Status | Evidence |",
        "|---|---|---|---|",
    ]
    for item in results:
        evidence = item["evidence"].replace("\n", " ").replace("|", "\\|")
        lines.append(
            f"| {item['library']} | {item['gate']} | {item['status']} | {evidence} |"
        )
    return "\n".join(lines)


def write_report(path: Path | None, command: str, results: list[dict[str, str]]) -> None:
    if path is None:
        return
    payload = {
        "schema_version": 1,
        "command": command,
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "status": "FAIL" if any(item["status"] == "FAIL" for item in results) else "PASS",
        "results": results,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("public", "install", "fallback", "consumer", "installed-smoke"),
    )
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = load_manifest(args.manifest)
        if args.command == "public":
            results = audit_public(manifest)
        elif args.command == "install":
            results = install_fleet(manifest, args.manifest.resolve())
        elif args.command == "fallback":
            results = check_fallbacks(manifest)
        elif args.command == "consumer":
            results = check_real_consumer(manifest)
        else:
            installed_smoke(manifest)
            return 0
    except (CheckFailure, OSError, json.JSONDecodeError) as exc:
        print(f"lifecycle monitor configuration failure: {exc}", file=sys.stderr)
        return 2
    print(render(results))
    write_report(args.report, args.command, results)
    return 1 if any(item["status"] == "FAIL" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
