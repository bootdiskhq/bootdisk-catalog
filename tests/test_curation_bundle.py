import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.curation_bundle import BUNDLE_SCHEMA, export_bundle, restore_bundle
from bootdisk_catalog.identify import IdentificationError, create_identification

ARTIFACT_DIGEST = "a" * 64
MANIFEST_DIGEST = "b" * 64
ARTIFACT_ID = f"artifact:sha256:{ARTIFACT_DIGEST}"


class CurationBundleTests(unittest.TestCase):
    def make_imported_catalog(self, root: Path) -> None:
        (root / "artifacts").mkdir(parents=True)
        (root / "occurrences").mkdir(parents=True)
        (root / "artifacts" / "artifact.json").write_text(json.dumps({"schema":"bootdisk-catalog-0.1","type":"artifact","id":ARTIFACT_ID,"sha256":ARTIFACT_DIGEST,"size":123}) + "\n")
        (root / "occurrences" / "occurrence.json").write_text(json.dumps({"schema":"bootdisk-catalog-0.1","type":"occurrence","id":f"occurrence:{MANIFEST_DIGEST}:K37:installer","artifact_id":ARTIFACT_ID,"source_ref":{"manifest":f"sha256:{MANIFEST_DIGEST}","entry":"K37","path":"WinAmp/setup.exe"}}) + "\n")

    def test_round_trip_preserves_semantics_but_not_reproducible_import_records(self):
        with tempfile.TemporaryDirectory() as source_name, tempfile.TemporaryDirectory() as target_name:
            source, target = Path(source_name), Path(target_name)
            self.make_imported_catalog(source)
            self.make_imported_catalog(target)
            create_identification(source, artifact_id=ARTIFACT_ID, entry="K37", software_id="software:winamp", software_name="Winamp", release_id="release:winamp:2.76", version="2.76", evidence_field="normalized.title", evidence_value="WinAmp 2.76")
            bundle = export_bundle(Catalog.load(source))
            self.assertEqual(bundle["schema"], BUNDLE_SCHEMA)
            self.assertEqual({record["type"] for record in bundle["records"]}, {"software", "software_release", "identification"})
            self.assertNotIn("artifact", {record["type"] for record in bundle["records"]})
            self.assertEqual(restore_bundle(target, bundle), 3)
            restored = Catalog.load(target)
            self.assertEqual(restored.record("software:winamp")["name"], "Winamp")
            self.assertEqual(len(restored.records_of_type("artifact")), 1)

    def test_restore_refuses_conflicting_semantic_record(self):
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            self.make_imported_catalog(root)
            (root / "software").mkdir()
            (root / "software" / "software_winamp.json").write_text(json.dumps({"schema":"bootdisk-catalog-0.1","type":"software","id":"software:winamp","name":"Wrong name"}) + "\n")
            bundle = {"schema": BUNDLE_SCHEMA, "catalog_schema":"bootdisk-catalog-0.1", "records":[{"schema":"bootdisk-catalog-0.1","type":"software","id":"software:winamp","name":"Winamp"}]}
            with self.assertRaises(IdentificationError):
                restore_bundle(root, bundle)


if __name__ == "__main__":
    unittest.main()
