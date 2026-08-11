#!/usr/bin/env bash
# Run the complete python-dotenv 1.2.2 upstream suite against this checkout.
#
# This is intentionally a source-test gate, not a subset/differential smoke test:
#   * the archive and every upstream test file are verified before execution;
#   * $repo_root/python is first on sys.path, even when python-dotenv is installed;
#   * a temporary `dotenv` executable makes CLI subprocess tests target the candidate;
#   * pytest's normal platform skips are preserved;
#   * an absent optional IPython dependency is reported as three omitted tests.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python}
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/fast_dotenv_upstream.XXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT

echo "[upstream] repository: $repo_root"
echo "[upstream] python: $($python_bin -c 'import sys; print(sys.executable)')"
echo "[upstream] version: $($python_bin -c 'import sys; print(sys.version.split()[0])')"

# Download through the active Python so the gate has no jq/curl dependency. The
# PyPI JSON digest is the source-of-truth for the immutable 1.2.2 sdist.
"$python_bin" - "$work_dir" <<'PY'
import hashlib
import json
import pathlib
import sys
import tarfile
import urllib.request
import warnings

destination = pathlib.Path(sys.argv[1])
metadata_url = "https://pypi.org/pypi/python-dotenv/1.2.2/json"
with urllib.request.urlopen(metadata_url) as response:
    metadata = json.load(response)

info = metadata.get("info", {})
if info.get("name") != "python-dotenv" or info.get("version") != "1.2.2":
    raise SystemExit("PyPI metadata is not python-dotenv==1.2.2")

sdists = [item for item in metadata.get("urls", []) if item.get("packagetype") == "sdist"]
if len(sdists) != 1:
    raise SystemExit(f"expected exactly one 1.2.2 sdist, found {len(sdists)}")
sdist = sdists[0]
expected_digest = sdist.get("digests", {}).get("sha256")
if not expected_digest:
    raise SystemExit("PyPI sdist has no SHA-256 digest")

archive = destination / "python-dotenv-1.2.2.tar.gz"
with urllib.request.urlopen(sdist["url"]) as response, archive.open("wb") as handle:
    while True:
        block = response.read(1024 * 1024)
        if not block:
            break
        handle.write(block)

actual_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
if actual_digest != expected_digest:
    raise SystemExit(
        "sdist SHA-256 mismatch: "
        f"expected {expected_digest}, got {actual_digest}"
    )

# Validate member paths before extraction. The upstream sdist is expected to
# have one fixed top-level directory; refusing anything else prevents a source
# archive/path mistake from silently changing the test suite.
root_name = "python_dotenv-1.2.2"
with tarfile.open(archive, "r:gz") as bundle:
    members = bundle.getmembers()
    if not members or any(
        member.name != root_name and not member.name.startswith(root_name + "/")
        for member in members
    ):
        raise SystemExit("sdist contains an unexpected top-level path")
    if any(member.issym() or member.islnk() for member in members):
        raise SystemExit("refusing an sdist containing symbolic/hard links")
    with warnings.catch_warnings():
        # Python 3.14 warns about the historical extractall default; paths and
        # links were checked above and this keeps the gate quiet on 3.12/3.13.
        warnings.simplefilter("ignore", DeprecationWarning)
        bundle.extractall(destination)

source = destination / root_name
expected_files = {
    "tests/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "tests/conftest.py": "1cc31c9f8e8b5e076780d7469c8f35ff8088e37a25be0bc7e07b68e593beb443",
    "tests/test_cli.py": "8f4f0871366080f813baf86df6c346a23c0a5543e718a3684d34560438afafae",
    "tests/test_fifo_dotenv.py": "b69ecca75f9eb3969aa2cc2d49f66006cccae02da472805a3b3ad4c9fca8f8de",
    "tests/test_ipython.py": "2d61ac43a07ad30bd5f0b23a8d30785bf1bb07f2238bc9ef344f65a181c85386",
    "tests/test_is_interactive.py": "2d4a6a5a4501bbd6c2860b39abeb9d5201a2de3d110347f74236098aa72f2a18",
    "tests/test_lib.py": "f75073c7317f7cda985b94531774578056519bf8dcb91aa7f3c60a7cf8872199",
    "tests/test_main.py": "4e638cc1ed2b9129b61ccdbfb89980bb79edbe08556659af67656365ed2a023e",
    "tests/test_parser.py": "42bab2235b43f5fe9283b3b16e7c099a16f137ec9f0b5afefd4c164f108eb130",
    "tests/test_utils.py": "82e06b9819adbc846b84717f9cc47ffff2dc99c77ebb0a22d93026326eac78a3",
    "tests/test_variables.py": "facea37ceaca30b761c2128fa754ec32c1e50333f2ac1776f7f8063018aaa6fc",
    "tests/test_zip_imports.py": "9224bd859309409c62848bac6564eec0793aa6dffa091c9965ec6c4644a8ef04",
}
for relative, expected in expected_files.items():
    path = source / relative
    if not path.is_file():
        raise SystemExit(f"official upstream test is missing: {relative}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"upstream test hash mismatch for {relative}: "
            f"expected {expected}, got {actual}"
        )

pyproject = (source / "pyproject.toml").read_text(encoding="utf-8")
if 'name = "python-dotenv"' not in pyproject or 'requires-python = ">=3.10"' not in pyproject:
    raise SystemExit("sdist pyproject.toml is not the expected 1.2.2 source")

print(f"[upstream] verified sdist: {archive.name} ({actual_digest})")
print(f"[upstream] verified source tests: {len(expected_files)} files")
PY

source_root="$work_dir/python_dotenv-1.2.2"
if [[ ${CANDIDATE_PYTHONPATH+x} ]]; then
    candidate_pythonpath=$CANDIDATE_PYTHONPATH
else
    candidate_pythonpath="$repo_root/python"
    if [[ -n "${PYTHONPATH:-}" ]]; then
        candidate_pythonpath="$candidate_pythonpath:$PYTHONPATH"
    fi
fi
candidate_expected_root=${CANDIDATE_EXPECTED_ROOT:-$repo_root/python}

# Fail before pytest if the candidate namespace is absent or if sys.path would
# select an installed Oracle. This check is deliberately done in a fresh process.
candidate_path=$(PYTHONPATH="$candidate_pythonpath" "$python_bin" - <<'PY'
import dotenv
print(getattr(dotenv, "__file__", ""))
PY
)
if ! "$python_bin" - "$candidate_path" "$candidate_expected_root" <<'PY'
import pathlib
import sys

candidate = pathlib.Path(sys.argv[1]).resolve()
expected_root = pathlib.Path(sys.argv[2]).resolve()
try:
    candidate.relative_to(expected_root)
except ValueError:
    raise SystemExit(1)
PY
then
    echo "[upstream] ERROR: imported dotenv from '$candidate_path'" >&2
    echo "[upstream] expected the candidate under '$candidate_expected_root/'" >&2
    exit 1
fi
echo "[upstream] candidate import: $candidate_path"

# The upstream CLI tests invoke `dotenv` as a subprocess. Put a temporary
# console-script-equivalent launcher first in PATH so an installed
# python-dotenv executable cannot satisfy those tests accidentally. Calling
# `python -m dotenv` is intentionally avoided: Click derives its program name
# from argv[0], and that form reports "python -m dotenv" instead of "dotenv".
bin_dir="$work_dir/bin"
mkdir -p "$bin_dir"
"$python_bin" - "$bin_dir/dotenv" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
path.write_text(
    "#!" + sys.executable + "\n"
    "import sys\n"
    "from dotenv.__main__ import cli\n"
    "sys.argv[0] = 'dotenv'\n"
    "sys.exit(cli())\n",
    encoding="utf-8",
)
path.chmod(0o755)
PY

# test_run_with_command_flags uses `printenv --version` only as a sentinel to
# prove that `--version` reaches the child process. GNU printenv supports that
# flag; BSD printenv on macOS rejects it before candidate behavior can be
# assessed. Keep the complete upstream test selected and provide a transparent
# compatibility fixture only when the host command lacks the sentinel flag.
# All ordinary printenv calls still delegate to the host executable.
host_printenv=$(command -v printenv)
if ! "$host_printenv" --version >/dev/null 2>&1; then
    "$python_bin" - "$bin_dir/printenv" "$host_printenv" <<'PY'
import pathlib
import shlex
import sys

path = pathlib.Path(sys.argv[1])
host_printenv = shlex.quote(sys.argv[2])
path.write_text(
    "#!/bin/sh\n"
    "if [ \"$#\" -eq 1 ] && [ \"$1\" = \"--version\" ]; then\n"
    "  printf '%s\\n' 'printenv (cross-platform upstream test fixture)'\n"
    "  exit 0\n"
    "fi\n"
    f"exec {host_printenv} \"$@\"\n",
    encoding="utf-8",
)
path.chmod(0o755)
PY
    echo "[upstream] host printenv lacks --version; installed a transparent test fixture."
fi

old_path=${PATH:-}
PATH="$bin_dir:$old_path" \
PYTHONPATH="$candidate_pythonpath" \
PYTHONNOUSERSITE=1 \
"$python_bin" -m pytest -q "$source_root/tests"

if "$python_bin" -c 'import IPython' >/dev/null 2>&1; then
    echo "[upstream] IPython available: the 3 IPython tests were eligible to run."
else
    echo "[upstream] WARNING: IPython is unavailable; upstream test_ipython.py skips exactly 3 tests." >&2
    echo "[upstream] WARNING: this run is 216 core tests, not a claimed 219-test run." >&2
fi

echo "[upstream] full python-dotenv 1.2.2 suite passed (platform skips preserved)."
