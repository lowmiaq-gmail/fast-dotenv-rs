from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_replacement_fleet import CheckFailure, audit_public, load_manifest


ROOT = Path(__file__).parents[1]
MANIFEST_PATH = ROOT / "reusable" / "replacement-fleet.json"


def public_payloads(manifest: dict) -> dict[str, dict]:
    payloads: dict[str, dict] = {}
    for package in manifest["packages"]:
        filename = f"{package['distribution'].replace('-', '_')}-{package['version']}-py3-none-any.whl"
        digest = "a" * 64
        payloads[
            f"https://pypi.org/pypi/{package['distribution']}/{package['version']}/json"
        ] = {
            "info": {"name": package["distribution"], "version": package["version"]},
            "urls": [
                {"filename": filename, "digests": {"sha256": digest}},
                {
                    "filename": f"{package['distribution'].replace('-', '_')}-{package['version']}.tar.gz",
                    "digests": {"sha256": "b" * 64},
                },
            ],
        }
        payloads[f"https://pypi.org/pypi/{package['upstream_distribution']}/json"] = {
            "info": {"version": package["upstream_version"]}
        }
        assets = [
            {"name": filename, "digest": f"sha256:{digest}"},
            {
                "name": f"{package['distribution'].replace('-', '_')}-{package['version']}.tar.gz",
                "digest": f"sha256:{'b' * 64}",
            },
            {"name": "SHA256SUMS", "digest": f"sha256:{'c' * 64}"},
        ]
        payloads[
            "https://api.github.com/repos/"
            f"{package['repository']}/releases/tags/{package['release_tag']}"
        ] = {
            "draft": False,
            "prerelease": False,
            "tag_name": package["release_tag"],
            "assets": assets,
        }
    return payloads


class ManifestTests(unittest.TestCase):
    def test_live_manifest_has_seven_unique_releases(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        self.assertEqual(len(manifest["packages"]), 7)
        self.assertEqual(
            len({package["distribution"] for package in manifest["packages"]}), 7
        )

    def test_duplicate_distribution_is_rejected(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        manifest["packages"][1]["distribution"] = manifest["packages"][0]["distribution"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CheckFailure, "duplicate distribution"):
                load_manifest(path)


class PublicAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(MANIFEST_PATH)
        self.payloads = public_payloads(self.manifest)

    def fetch(self, url: str) -> dict:
        return copy.deepcopy(self.payloads[url])

    def test_all_public_contracts_pass(self) -> None:
        results = audit_public(self.manifest, self.fetch)
        self.assertEqual(len(results), 7)
        self.assertEqual({item["status"] for item in results}, {"PASS"})

    def test_upstream_drift_fails_only_affected_library(self) -> None:
        package = self.manifest["packages"][0]
        url = f"https://pypi.org/pypi/{package['upstream_distribution']}/json"
        self.payloads[url]["info"]["version"] = "999.0.0"
        results = audit_public(self.manifest, self.fetch)
        failed = [item for item in results if item["status"] == "FAIL"]
        self.assertEqual([item["library"] for item in failed], [package["distribution"]])
        self.assertIn("upstream version drift", failed[0]["evidence"])

    def test_artifact_digest_mismatch_is_not_hidden(self) -> None:
        package = self.manifest["packages"][2]
        url = (
            "https://api.github.com/repos/"
            f"{package['repository']}/releases/tags/{package['release_tag']}"
        )
        self.payloads[url]["assets"][0]["digest"] = f"sha256:{'0' * 64}"
        results = audit_public(self.manifest, self.fetch)
        failed = [item for item in results if item["status"] == "FAIL"]
        self.assertEqual([item["library"] for item in failed], [package["distribution"]])
        self.assertIn("digest mismatch", failed[0]["evidence"])

    def test_missing_release_file_is_not_hidden(self) -> None:
        package = self.manifest["packages"][4]
        url = (
            "https://api.github.com/repos/"
            f"{package['repository']}/releases/tags/{package['release_tag']}"
        )
        self.payloads[url]["assets"].pop(0)
        results = audit_public(self.manifest, self.fetch)
        failed = [item for item in results if item["status"] == "FAIL"]
        self.assertEqual([item["library"] for item in failed], [package["distribution"]])
        self.assertIn("missing PyPI files", failed[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
