import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog, CatalogError
from bootdisk_catalog.view import format_software_view, software_view


ARTIFACT_DIGEST = "a" * 64
MANIFEST_DIGEST = "b" * 64
ARTIFACT_ID = f"artifact:sha256:{ARTIFACT_DIGEST}"


class SoftwareViewTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

        records = {
            "software/winamp.json": {
                "schema": "bootdisk-catalog-0.1",
                "type": "software",
                "id": "software:winamp",
                "name": "Winamp",
            },
            "releases/winamp-2.76.json": {
                "schema": "bootdisk-catalog-0.1",
                "type": "software_release",
                "id": "release:winamp:2.76",
                "software_id": "software:winamp",
                "version": "2.76",
            },
            "artifacts/artifact.json": {
                "schema": "bootdisk-catalog-0.1",
                "type": "artifact",
                "id": ARTIFACT_ID,
                "sha256": ARTIFACT_DIGEST,
                "size": 2229552,
            },
            "occurrences/occurrence.json": {
                "schema": "bootdisk-catalog-0.1",
                "type": "occurrence",
                "id": f"occurrence:{MANIFEST_DIGEST}:K37:installer",
                "artifact_id": ARTIFACT_ID,
                "source_ref": {
                    "manifest": f"sha256:{MANIFEST_DIGEST}",
                    "entry": "K37",
                    "path": "WinAmp/WinAmp276_full.exe",
                },
            },
            "identifications/identification.json": {
                "schema": "bootdisk-catalog-0.1",
                "type": "identification",
                "id": "identification:" + "c" * 64,
                "artifact_id": ARTIFACT_ID,
                "software_release_id": "release:winamp:2.76",
                "status": "curated",
                "evidence": [
                    {
                        "kind": "observed",
                        "source_ref": {
                            "manifest": f"sha256:{MANIFEST_DIGEST}",
                            "entry": "K37",
                        },
                        "field": "normalized.title",
                        "value": "WinAmp 2.76",
                    }
                ],
            },
        }

        for relative_path, record in records.items():
            path = self.root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

        self.catalog = Catalog.load(self.root)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_projects_software_release_artifact_and_occurrence(self):
        view = software_view(self.catalog, "software:winamp")

        self.assertEqual(view["name"], "Winamp")
        self.assertEqual(view["releases"][0]["version"], "2.76")
        self.assertEqual(view["releases"][0]["artifacts"][0]["id"], ARTIFACT_ID)
        self.assertEqual(
            view["releases"][0]["artifacts"][0]["occurrences"][0]["source_ref"][
                "entry"
            ],
            "K37",
        )

    def test_formats_human_readable_catalog_view(self):
        output = format_software_view(software_view(self.catalog, "software:winamp"))

        self.assertIn("Software:\n  Winamp (software:winamp)", output)
        self.assertIn("Release:\n  2.76 (release:winamp:2.76)", output)
        self.assertIn(f"Artifact:\n  {ARTIFACT_ID}", output)
        self.assertIn("entry: K37", output)
        self.assertIn("path:  WinAmp/WinAmp276_full.exe", output)

    def test_rejects_non_software_root_id(self):
        with self.assertRaisesRegex(CatalogError, "expected software"):
            software_view(self.catalog, ARTIFACT_ID)


if __name__ == "__main__":
    unittest.main()
