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

1. Open **Actions → Release to PyPI → Run workflow** on `main`.
2. Keep version `0.1.0` and enable `confirm_release`.
3. Watch every job through `Create verified GitHub pre-release`.
4. Verify the public endpoints:
   - `https://pypi.org/project/fast-dotenv-rs/0.1.0/`
   - `https://github.com/lowmiaq-gmail/fast-dotenv-rs/releases/tag/v0.1.0`

For future versions, update both version files, changelog, release notes, and the
explicit version gate in `.github/workflows/release.yml` before dispatching.
