# Publishing fast-dotenv-rs

The release workflow is manual and fail-closed. It publishes only after five
native wheel lanes and one sdist lane pass, then reinstalls the public PyPI package
on all five platforms before creating the GitHub pre-release.

## One-time PyPI Trusted Publisher setup

Sign in to PyPI, open **Publishing**, and add a pending GitHub publisher with the
following exact values:

| Field | Value |
|---|---|
| PyPI project name | `fast-dotenv-rs` |
| GitHub owner | `lowmiaq-gmail` |
| Repository | `fast-dotenv-rs` |
| Workflow | `release.yml` |
| Environment | `pypi` |

The pending publisher does not reserve the name. Run the release immediately
after adding it. No API token or repository secret is used.

## Release

1. Freeze README, changelog, release notes, version, URLs, and installation command in
   their post-release wording. Remove `not published`, `no PyPI package yet`, and
   source-only installation placeholders before building.
2. Build the sdist and wheel, then inspect their embedded `PKG-INFO` and `METADATA`.
   The artifact audit must find `fast-dotenv-rs[cli]==<version>` and reject stale
   pre-release wording. Repository files alone are not sufficient evidence.
3. Open **Actions → Release to PyPI → Run workflow** on `main`.
4. Keep version `0.1.0` and enable `confirm_release`.
5. Watch every job through `Create verified GitHub pre-release`.
6. Verify the public endpoints and compare their metadata with the audited artifacts:
   - `https://pypi.org/project/fast-dotenv-rs/0.1.0/`
   - `https://github.com/lowmiaq-gmail/fast-dotenv-rs/releases/tag/v0.1.0`

PyPI preserves the first uploaded metadata for a release. A README commit made after the
upload does not update that release's long description. Do not delete, replace, or yank a
working release solely to correct prose; carry the correction into the next normal patch
release.

For future versions, update both version files, changelog, release notes, and the
explicit version gate in `.github/workflows/release.yml` before dispatching.
