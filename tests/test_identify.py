import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.identify import IdentificationError, create_identification


ARTIFACT_DIGEST = "a" * 64
MANIFEST_DIGEST = "b" * 64
ARTIFACT_ID = f"artifact:sha256:{ARTIFACT_DIGEST}"


class IdentificationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "artifacts").mkdir()
        (self.root / "occurrences").mkdir()

        (self.root / "artifacts" / "artifact.json").write_text(
            json.dumps(
                {
                    "schema": "bootdisk-catalog-0.1",
                    "type": "artifact",
                    "id": ARTIFACT_ID,
                    "sha256": ARTIFACT_DIGEST,
                    "size": 123,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "occurrences" / "occurrence.json").write_text(
            json.dumps(
                {
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
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def identify(self):
        return create_identification(
            self.root,
            artifact_id=ARTIFACT_ID,
            entry="K37",
            software_id="software:winamp",
            software_name="Winamp",
            release_id="release:winamp:2.76",
            version="2.76",
            evidence_field="normalized.title",
            evidence_value="WinAmp 2.76",
        )

    def test_creates_software_release_and_evidence_bearing_identification(self):
        software, release, identification = self.identify()

        self.assertEqual(software["id"], "software:winamp")
        self.assertEqual(release["software_id"], "software:winamp")
        self.assertEqual(identification["artifact_id"], ARTIFACT_ID)
        self.assertEqual(identification["status"], "curated")
        self.assertEqual(
            identification["evidence"][0]["source_ref"],
            {"manifest": f"sha256:{MANIFEST_DIGEST}", "entry": "K37"},
        )

        catalog = Catalog.load(self.root)
        self.assertEqual(
            catalog.artifacts_for_release("release:winamp:2.76")[0]["id"],
            ARTIFACT_ID,
        )
        self.assertEqual(
            catalog.releases_for_software("software:winamp")[0]["version"], "2.76"
        )

    def test_is_idempotent_for_the_same_interpretation(self):
        first = self.identify()
        second = self.identify()
        self.assertEqual(first, second)
        catalog = Catalog.load(self.root)
        self.assertEqual(len(catalog.records_of_type("software")), 1)
        self.assertEqual(len(catalog.records_of_type("software_release")), 1)
        self.assertEqual(len(catalog.records_of_type("identification")), 1)

    def test_rejects_identification_without_matching_occurrence(self):
        with self.assertRaisesRegex(IdentificationError, "no occurrence"):
            create_identification(
                self.root,
                artifact_id=ARTIFACT_ID,
                entry="K999",
                software_id="software:winamp",
                software_name="Winamp",
                release_id="release:winamp:2.76",
                version="2.76",
                evidence_field="normalized.title",
                evidence_value="WinAmp 2.76",
            )


if __name__ == "__main__":
    unittest.main()
