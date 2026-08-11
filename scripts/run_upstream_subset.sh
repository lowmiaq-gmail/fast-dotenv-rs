#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
upstream_tmp=$(mktemp -d "${TMPDIR:-/tmp}/python_dotenv_122.XXXXXX")
trap 'rm -rf -- "$upstream_tmp"' EXIT

sdist_url=$(curl -sSf https://pypi.org/pypi/python-dotenv/1.2.2/json \
  | jq -r '.urls[] | select(.packagetype=="sdist") | .url')
curl -sSf "$sdist_url" -o "$upstream_tmp/source.tar.gz"
tar --no-same-owner -xzf "$upstream_tmp/source.tar.gz" -C "$upstream_tmp"

PYTHONPATH="$repo_root/tests/upstream_shim:$repo_root/python" \
  python -m pytest -q \
  "$upstream_tmp/python_dotenv-1.2.2/tests/test_main.py" \
  -k dotenv_values
