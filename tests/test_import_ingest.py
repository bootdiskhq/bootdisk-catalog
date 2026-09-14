import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.import_ingest import IngestImportError, build_records, write_records


ARTIFACT_DIGEST = "a" * 64


class IngestImportTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.manifest_path = self.root / "ingest-manifest.json"
        self.output = self.root / "catalog"

    def tearDown(self):
        self.tempdir.cleanup()

    def manifest(self):
        return {
            "schema_version": "0.9",
            "entries": [
                {
                    "source_id": "K18",
                    "normalized": {"title": "Winamp 2.76"},
                    "files": {
                        "referenced": {
                            "installer": {
                                "path": "Tools/Winamp/winamp276_full.exe",
                                "exists": True,
                                "is_file": True,
                                "size": 1234567,
                                "sha256": ARTIFACT_DIGEST,
                            }
                        },
                        "discovered": {},
                    },
                }
            ],
        }

    def write_manifest(self, data=None):
        payload = self.manifest() if data is None else data
        self.manifest_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    def test_builds_artifact_and_occurrence_from_explicit_observation(self):
        self.write_manifest()
        manifest_digest = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()

        artifact, occurrence = build_records(
            self.manifest_path, "K18", "installer"
        )

        self.assertEqual(artifact["id"], f"artifact:sha256:{ARTIFACT_DIGEST}")
        self.assertEqual(artifact["size"], 1234567)
        self.assertEqual(
            occurrence["source_ref"],
            {
                "manifest": f"sha256:{manifest_digest}",
                "entry": "K18",
                "path": "Tools/Winamp/winamp276_full.exe",
            },
        )
        self.assertIn(manifest_digest, occurrence["id"])
        self.assertNotIn("Winamp", occurrence["id"])

    def test_write_records_emits_catalog_that_loader_accepts(self):
        self.write_manifest()

        artifact_path, occurrence_path = write_records(
            self.manifest_path, "K18", "installer", self.output
        )

        self.assertTrue(artifact_path.is_file())
        self.assertTrue(occurrence_path.is_file())
        catalog = Catalog.load(self.output)
        occurrences = catalog.occurrences_for_artifact(
            f"artifact:sha256:{ARTIFACT_DIGEST}"
        )
        self.assertEqual(len(occurrences), 1)

    def test_does_not_create_software_release_or_identification(self):
        self.write_manifest()
        write_records(self.manifest_path, "K18", "installer", self.output)

        catalog = Catalog.load(self.output)
        self.assertEqual(catalog.records_of_type("software"), ())
        self.assertEqual(catalog.records_of_type("software_release"), ())
        self.assertEqual(catalog.records_of_type("identification"), ())

    def test_rejects_unknown_entry(self):
        self.write_manifest()

        with self.assertRaisesRegex(IngestImportError, "entry not found"):
            build_records(self.manifest_path, "K999", "installer")

    def test_rejects_unknown_file_role(self):
        self.write_manifest()

        with self.assertRaisesRegex(IngestImportError, "file role not found"):
            build_records(self.manifest_path, "K18", "screenshot")

    def test_rejects_missing_file_observation(self):
        data = self.manifest()
        observation = data["entries"][0]["files"]["referenced"]["installer"]
        observation["exists"] = False
        self.write_manifest(data)

        with self.assertRaisesRegex(IngestImportError, "not a preserved regular file"):
            build_records(self.manifest_path, "K18", "installer")

    def test_manifest_identity_changes_when_evidence_document_changes(self):
        data = self.manifest()
        self.write_manifest(data)
        _, first = build_records(self.manifest_path, "K18", "installer")

        data["generator"] = {"name": "bootdisk-ingest", "version": "test"}
        self.write_manifest(data)
        _, second = build_records(self.manifest_path, "K18", "installer")

        self.assertNotEqual(
            first["source_ref"]["manifest"], second["source_ref"]["manifest"]
        )


if __name__ == "__main__":
    unittest.main()
