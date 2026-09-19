import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.curation_bundle import restore_bundle


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = REPOSITORY_ROOT / "data" / "curation" / "kcd15-2001.json"
EXPECTED_IDENTIFICATION_ID = (
    "identification:"
    "97e260274a5258dae047c0f6294ee1da53b50d22a3f5e588e41da8b23aef5f04"
)


class ReferenceCurationTests(unittest.TestCase):
    def test_kcd15_2001_bundle_restores_winamp_after_catalog_rebuild(self):
        bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
        records_by_type = {}
        for record in bundle["records"]:
            records_by_type.setdefault(record["type"], []).append(record)

        self.assertEqual(bundle["schema"], "bootdisk-catalog-curation-0.1")
        self.assertEqual(bundle["catalog_schema"], "bootdisk-catalog-0.1")
        self.assertEqual(
            set(records_by_type),
            {"software", "software_release", "identification", "description"},
        )

        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            (root / "artifacts").mkdir()
            (root / "occurrences").mkdir()
            for identification in records_by_type["identification"]:
                artifact_id = identification["artifact_id"]
                artifact_digest = artifact_id.removeprefix("artifact:sha256:")
                source_ref = identification["evidence"][0]["source_ref"]
                manifest_digest = source_ref["manifest"].removeprefix("sha256:")
                entry = source_ref["entry"]
                (root / "artifacts" / f"{entry}.json").write_text(
                    json.dumps(
                        {
                            "schema": "bootdisk-catalog-0.1",
                            "type": "artifact",
                            "id": artifact_id,
                            "sha256": artifact_digest,
                            "size": 1,
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (root / "occurrences" / f"{entry}.json").write_text(
                    json.dumps(
                        {
                            "schema": "bootdisk-catalog-0.1",
                            "type": "occurrence",
                            "id": f"occurrence:{manifest_digest}:{entry}:installer",
                            "artifact_id": artifact_id,
                            "source_ref": {
                                "manifest": source_ref["manifest"],
                                "entry": entry,
                            },
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            self.assertEqual(restore_bundle(root, bundle), 28)
            restored = Catalog.load(root)

        self.assertEqual(
            restored.record(EXPECTED_IDENTIFICATION_ID)["id"],
            EXPECTED_IDENTIFICATION_ID,
        )
        self.assertEqual(restored.record("software:winamp")["name"], "Winamp")
        self.assertEqual(
            restored.record("release:winamp:2.76")["version"],
            "2.76",
        )
        self.assertEqual(
            restored.record(EXPECTED_IDENTIFICATION_ID)["status"],
            "curated",
        )
        descriptions = restored.descriptions_for_subject("release:winamp:2.76")
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(descriptions[0]["language"], "nb-NO")
        self.assertIn("K37", descriptions[0]["text"])
        self.assertEqual(restored.record("software:winzip")["name"], "WinZip")
        self.assertEqual(
            restored.record("release:acrobat-reader:5.0")["version"], "5.0"
        )
        self.assertEqual(
            restored.record("software:internet-explorer")["name"],
            "Internet Explorer",
        )
        self.assertEqual(
            restored.record("release:1st-page:2000")["version"], "2000"
        )
        self.assertEqual(
            restored.record("release:avg-antivirus:6.0")["version"], "6.0"
        )
        self.assertEqual(
            restored.record("release:xnview:1.21")["version"], "1.21"
        )
        self.assertIn(
            "pakke filer",
            restored.descriptions_for_subject("release:winzip:8.0")[0]["text"],
        )


if __name__ == "__main__":
    unittest.main()
