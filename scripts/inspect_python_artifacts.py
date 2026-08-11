#!/usr/bin/env python3
"""Audit release distributions before they leave CI.

The checks are intentionally dependency-free so the publishing job can consume
only immutable artifacts and never execute project or third-party build code.
"""

from __future__ import annotations

import argparse
import email.parser
import pathlib
import tarfile
import zipfile


TEXT_SUFFIXES = (".py", ".json", ".txt", ".md", ".toml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=pathlib.Path, required=True)
    parser.add_argument("--repository-root", type=pathlib.Path, required=True)
    parser.add_argument("--expected-name", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-wheels", type=int, required=True)
    parser.add_argument("--expected-sdists", type=int, required=True)
    parser.add_argument("--require-metadata-text", action="append", default=[])
    parser.add_argument("--forbid-metadata-text", action="append", default=[])
    return parser.parse_args()


def assert_safe_paths(names: list[str]) -> None:
    for name in names:
        path = pathlib.PurePosixPath(name)
        assert not path.is_absolute(), name
        assert ".." not in path.parts, name


def assert_metadata(
    raw: bytes,
    expected_name: str,
    expected_version: str,
    required_text: list[str],
    forbidden_text: list[str],
) -> None:
    metadata = email.parser.BytesParser().parsebytes(raw)
    assert metadata["Name"] == expected_name, metadata["Name"]
    assert metadata["Version"] == expected_version, metadata["Version"]
    decoded = raw.decode("utf-8", errors="replace")
    for value in required_text:
        assert value in decoded, f"required metadata text missing: {value!r}"
    for value in forbidden_text:
        assert value not in decoded, f"forbidden metadata text present: {value!r}"


def main() -> None:
    args = parse_args()
    artifact_dir = args.artifact_dir.resolve()
    repository_root = args.repository_root.resolve()
    wheels = sorted(artifact_dir.glob("*.whl"))
    sdists = sorted(artifact_dir.glob("*.tar.gz"))

    assert len(wheels) == args.expected_wheels, wheels
    assert len(sdists) == args.expected_sdists, sdists
    filenames = [path.name for path in [*wheels, *sdists]]
    assert len(filenames) == len(set(filenames)), filenames

    # Assemble generic build-root patterns at runtime so this auditor can itself
    # be shipped in an sdist without matching its own source text.
    slash = "/"
    backslash = "\\"
    forbidden_text = (
        str(repository_root),
        slash + "workspace" + slash,
        slash + "home" + slash + "runner" + slash + "work" + slash,
        backslash * 2 + "Users" + backslash * 2,
        "target" + slash + "debug",
        "target" + slash + "release",
    )

    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert_safe_paths(names)
            assert not any(
                name.endswith((".pyc", ".pyo"))
                or "/tests/" in f"/{name}"
                or "/target/" in f"/{name}"
                for name in names
            ), names
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            assert len(metadata_names) == 1, metadata_names
            assert_metadata(
                archive.read(metadata_names[0]),
                args.expected_name,
                args.expected_version,
                args.require_metadata_text,
                args.forbid_metadata_text,
            )
            for name in names:
                if name.endswith(TEXT_SUFFIXES) or "/sboms/" in f"/{name}":
                    text = archive.read(name).decode("utf-8", errors="ignore")
                    assert not any(value in text for value in forbidden_text), name

    for sdist in sdists:
        with tarfile.open(sdist, "r:gz") as archive:
            names = archive.getnames()
            assert_safe_paths(names)
            assert not any(
                "/target/" in f"/{name}"
                or "/.venv/" in f"/{name}"
                or "/__pycache__/" in f"/{name}"
                for name in names
            ), names
            metadata_members = [
                member for member in archive.getmembers() if member.name.endswith("/PKG-INFO")
            ]
            assert len(metadata_members) == 1, [member.name for member in metadata_members]
            metadata_file = archive.extractfile(metadata_members[0])
            assert metadata_file is not None
            assert_metadata(
                metadata_file.read(),
                args.expected_name,
                args.expected_version,
                args.require_metadata_text,
                args.forbid_metadata_text,
            )
            for member in archive.getmembers():
                if member.isfile() and member.name.endswith(TEXT_SUFFIXES):
                    extracted = archive.extractfile(member)
                    assert extracted is not None
                    text = extracted.read().decode("utf-8", errors="ignore")
                    assert not any(value in text for value in forbidden_text), member.name

    print(
        "artifact audit passed: "
        f"{len(wheels)} wheel(s), {len(sdists)} sdist(s), "
        f"{args.expected_name}=={args.expected_version}"
    )


if __name__ == "__main__":
    main()
