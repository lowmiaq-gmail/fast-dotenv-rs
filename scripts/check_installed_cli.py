#!/usr/bin/env python3
"""Verify module and console entry points belong to the active Python environment."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys


def check(command: list[str], version: str) -> None:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert version in result.stdout, (command, result.stdout, result.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    scripts_dir = pathlib.Path(sys.executable).parent
    entry = shutil.which("dotenv", path=str(scripts_dir))
    assert entry is not None, f"dotenv console script not found under {scripts_dir}"
    check([sys.executable, "-m", "dotenv", "--version"], args.version)
    check([entry, "--version"], args.version)
    print(f"installed module and console CLI passed: {entry}")


if __name__ == "__main__":
    main()
