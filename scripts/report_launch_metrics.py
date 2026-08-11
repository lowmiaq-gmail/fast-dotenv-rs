#!/usr/bin/env python3
"""Report public distribution and adoption signals for fast-dotenv-rs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from typing import Any


REPOSITORY = "lowmiaq-gmail/fast-dotenv-rs"
PACKAGE = "fast-dotenv-rs"
VERSION = "0.1.0"
EXPECTED_DESCRIPTION = (
    "Fast Rust-backed drop-in replacement for python-dotenv 1.2.2, "
    "built with PyO3 and Maturin."
)
EXPECTED_HOMEPAGE = "https://pypi.org/project/fast-dotenv-rs/"
EXPECTED_TOPICS = {
    "configuration",
    "dotenv",
    "drop-in-replacement",
    "env-parser",
    "environment-variables",
    "maturin",
    "performance",
    "pyo3",
    "python",
    "python-dotenv",
    "python-extension",
    "rust",
}


def fetch_json(url: str, *, optional: bool = False) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json, application/json",
            "User-Agent": f"{PACKAGE}-launch-monitor",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        if optional:
            return {"available": False, "error": str(exc)}
        raise RuntimeError(f"could not fetch {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected an object from {url}")
    return payload


def collect() -> dict[str, Any]:
    repository = fetch_json(f"https://api.github.com/repos/{REPOSITORY}")
    release = fetch_json(
        f"https://api.github.com/repos/{REPOSITORY}/releases/tags/v{VERSION}"
    )
    package = fetch_json(f"https://pypi.org/pypi/{PACKAGE}/{VERSION}/json")
    downloads = fetch_json(
        f"https://pypistats.org/api/packages/{PACKAGE}/recent", optional=True
    )
    topics = set(repository.get("topics") or [])
    return {
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "repository": {
            "url": repository.get("html_url"),
            "description": repository.get("description"),
            "homepage": repository.get("homepage"),
            "topics": sorted(topics),
            "stars": repository.get("stargazers_count"),
            "forks": repository.get("forks_count"),
            "open_issues": repository.get("open_issues_count"),
            "subscribers": repository.get("subscribers_count"),
        },
        "release": {
            "url": release.get("html_url"),
            "tag": release.get("tag_name"),
            "prerelease": release.get("prerelease"),
            "assets": len(release.get("assets") or []),
        },
        "package": {
            "url": f"https://pypi.org/project/{PACKAGE}/{VERSION}/",
            "name": package.get("info", {}).get("name"),
            "version": package.get("info", {}).get("version"),
            "files": len(package.get("urls") or []),
        },
        "downloads": downloads,
        "discovery_gate": {
            "description_matches": repository.get("description") == EXPECTED_DESCRIPTION,
            "homepage_matches": repository.get("homepage") == EXPECTED_HOMEPAGE,
            "missing_topics": sorted(EXPECTED_TOPICS - topics),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    repository = report["repository"]
    release = report["release"]
    package = report["package"]
    gate = report["discovery_gate"]
    downloads = report["downloads"]
    if downloads.get("available") is False:
        download_text = f"unavailable ({downloads.get('error')})"
    else:
        data = downloads.get("data") or {}
        download_text = ", ".join(
            f"{key}={value}" for key, value in sorted(data.items())
        ) or "not reported yet"
    return "\n".join(
        [
            "# Launch metrics",
            "",
            f"Observed at: `{report['observed_at']}`",
            "",
            "| Surface | Public evidence |",
            "|---|---|",
            f"| Repository | [{REPOSITORY}]({repository['url']}) |",
            f"| GitHub release | [{release['tag']}]({release['url']}); "
            f"pre-release={release['prerelease']}; assets={release['assets']} |",
            f"| PyPI | [{package['name']} {package['version']}]({package['url']}); "
            f"files={package['files']} |",
            f"| Repository signals | stars={repository['stars']}; forks={repository['forks']}; "
            f"subscribers={repository['subscribers']}; open issues={repository['open_issues']} |",
            f"| PyPI downloads | {download_text} |",
            f"| Description gate | {gate['description_matches']} |",
            f"| Homepage gate | {gate['homepage_matches']} |",
            f"| Missing topics | {', '.join(gate['missing_topics']) or 'none'} |",
            "",
            "PyPI Stats updates daily and can be unavailable before a new project is indexed.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    parser.add_argument(
        "--strict-discovery",
        action="store_true",
        help="fail unless public GitHub description, homepage, and topics match",
    )
    args = parser.parse_args()
    try:
        report = collect()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_markdown(report))
    gate = report["discovery_gate"]
    if args.strict_discovery and (
        not gate["description_matches"]
        or not gate["homepage_matches"]
        or gate["missing_topics"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
