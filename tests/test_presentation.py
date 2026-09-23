import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.presentation import presentation_projection


SCHEMA = "bootdisk-catalog-0.1"
DIGEST = "a" * 64
ARTIFACT_ID = f"artifact:sha256:{DIGEST}"


class PresentationProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.root = self.workspace / "catalog"
        self.root.mkdir()
        self.manifest_path = self.workspace / "ingest.json"

        manifest = {
            "entries": [
                {"source_id": "K1", "normalized": {"title": "Program One 1.0"}},
                {"source_id": "K2", "normalized": {"title": "Unreviewed Program"}},
            ]
        }
        raw = json.dumps(manifest, indent=2).encode("utf-8") + b"\n"
        self.manifest_path.write_bytes(raw)
        manifest_ref = f"sha256:{hashlib.sha256(raw).hexdigest()}"

        self._write("artifacts/a.json", {
            "schema": SCHEMA, "type": "artifact", "id": ARTIFACT_ID,
            "sha256": DIGEST, "size": 123,
        })
        for entry in ("K1", "K2"):
            self._write(f"occurrences/{entry}.json", {
                "schema": SCHEMA, "type": "occurrence",
                "id": f"occurrence:{manifest_ref[7:]}:{entry}:installer",
                "artifact_id": ARTIFACT_ID,
                "source_ref": {"manifest": manifest_ref, "entry": entry, "path": f"{entry}/Setup.exe"},
            })
        self._write("software/one.json", {
            "schema": SCHEMA, "type": "software", "id": "software:one", "name": "Program One",
        })
        self._write("releases/one.json", {
            "schema": SCHEMA, "type": "software_release", "id": "release:one:1.0",
            "software_id": "software:one", "version": "1.0",
        })
        self._write("identifications/one.json", {
            "schema": SCHEMA, "type": "identification", "id": f"identification:{'c' * 64}",
            "artifact_id": ARTIFACT_ID, "software_release_id": "release:one:1.0", "status": "curated",
            "distribution_kind": "demo",
            "evidence": [{
                "kind": "observed",
                "source_ref": {"manifest": manifest_ref, "entry": "K1"},
                "field": "normalized.title", "value": "Program One 1.0",
            }],
        })
        for status in ("curated", "draft"):
            self._write(f"descriptions/{status}.json", {
                "schema": SCHEMA, "type": "description",
                "id": f"description:release:one:1.0:nb-NO:{status}",
                "subject_id": "release:one:1.0", "language": "nb-NO",
                "text": f"{status.capitalize()} description.", "status": status,
                "evidence": [{
                    "kind": "curated",
                    "source_ref": {"manifest": manifest_ref, "entry": "K1"},
                    "field": "normalized.title", "value": "Program One 1.0",
                }],
            })

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, relative_path, record):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    def test_projection_keeps_editorial_context_separate_from_semantic_identity(self):
        cards = presentation_projection(Catalog.load(self.root), self.manifest_path)

        self.assertEqual(cards[0]["entry"], "K1")
        self.assertEqual(cards[0]["editorial_title"], "Program One 1.0")
        self.assertEqual(cards[0]["curation_status"], "identified")
        self.assertEqual(cards[0]["software"][0]["software_id"], "software:one")
        self.assertEqual(cards[0]["software"][0]["software_name"], "Program One")
        self.assertEqual(cards[0]["software"][0]["version"], "1.0")
        self.assertEqual(cards[0]["software"][0]["distribution_kind"], "demo")
        self.assertEqual(
            cards[0]["software"][0]["descriptions"],
            [{
                "description_id": "description:release:one:1.0:nb-NO:curated",
                "language": "nb-NO",
                "text": "Curated description.",
            }],
        )

    def test_pending_entry_has_source_occurrences_without_invented_software(self):
        cards = presentation_projection(Catalog.load(self.root), self.manifest_path)

        self.assertEqual(cards[1]["entry"], "K2")
        self.assertEqual(cards[1]["curation_status"], "pending")
        self.assertEqual(cards[1]["software"], [])
        self.assertEqual(cards[1]["occurrences"][0]["path"], "K2/Setup.exe")

class OriginalSourceTests(unittest.TestCase):
    def test_original_wording_is_preserved_without_claim_or_language(self):
        from bootdisk_catalog.presentation import source_context
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.json'
            raw = {'entries': [{'source_id': 'K1', 'raw': {'Global': '  Original\r\ntekst. '},
                                'normalized': {'description': 'Rewritten', 'categories': ['Spil']}}]}
            path.write_text(json.dumps(raw))
            source = source_context(path)['K1']
            self.assertEqual(source['description']['value'], '  Original\r\ntekst. ')
            self.assertEqual(source['description']['source_ref']['pointer'], '/entries/0/raw/Global')
            self.assertNotIn('language', source['description'])
            self.assertEqual(source['key']['manifest'], 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest())

    def test_no_normalized_description_fallback(self):
        from bootdisk_catalog.presentation import source_context
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.json'
            path.write_text(json.dumps({'entries': [{'source_id': 'K1', 'normalized': {'description': 'Do not publish as original'}}]}))
            self.assertIsNone(source_context(path)['K1']['description'])

    def test_director_original_and_conflicts_are_observations(self):
        from test_intake import fixture
        from bootdisk_catalog.import_ingest import import_manifest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'manifest.json'
            manifest = fixture()
            manifest['entries'][0]['issues'] = ['conflicting_launch_targets']
            path.write_text(json.dumps(manifest))
            import_manifest(path, root / 'catalog')
            card = presentation_projection(Catalog.load(root / 'catalog'), path)[0]
            self.assertEqual(card['curation_status'], 'pending')
            self.assertEqual(card['software'], [])
            self.assertEqual(card['source_context']['description']['value'], '  Original omtale\r\n')
            self.assertEqual(card['source_context']['issues']['value'], ['conflicting_launch_targets'])
            self.assertEqual(card['source_context']['preservation_scope'], 'launch_files_only')


if __name__ == "__main__":
    unittest.main()
