import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.curation_bundle import restore_bundle, export_bundle
from bootdisk_catalog.import_ingest import import_manifest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'data/curation/kcd15-2001.json'
FIXTURE = ROOT / 'tests/fixtures/kcd15-2001-observations.json'


class ReferenceCurationTests(unittest.TestCase):
    def test_all_entries_restore_over_reconstructed_packages(self):
        bundle = json.loads(BUNDLE.read_text())
        with tempfile.TemporaryDirectory() as directory:
            import_manifest(FIXTURE, directory)
            self.assertEqual(restore_bundle(directory, bundle), 156)
            catalog = Catalog.load(directory)
            self.assertEqual(export_bundle(catalog), bundle)
            identities = catalog.records_of_type('identification')
            by_entry = {r['evidence'][0]['source_ref']['entry']:r for r in identities}
            expected = {e['source_id'] for e in json.loads(FIXTURE.read_text())['entries']}
            self.assertEqual(set(by_entry), expected)
            self.assertEqual(len(identities), 39)
            self.assertEqual(len(catalog.records_of_type('package')), 39)
            self.assertEqual(catalog.record('release:winamp:2.76')['version'], '2.76')
            self.assertEqual(catalog.record('release:mutant-xpiders:1.5')['version'], '1.5')
            self.assertEqual(catalog.record('software:outlookskolen')['content_kind'], 'course')
            self.assertEqual(catalog.record('software:larabie-fonts-kcd15-2001')['content_kind'], 'font_collection')
            self.assertEqual(by_entry['K1']['distribution_kind'], 'demo')
            self.assertEqual(by_entry['K20']['distribution_kind'], 'demo')
            self.assertEqual(by_entry['K17']['distribution_kind'], 'trial')
            self.assertEqual(by_entry['K22']['distribution_kind'], 'trial')
            self.assertEqual(by_entry['K14']['distribution_kind'], 'unknown')
            self.assertEqual(by_entry['K14']['software_release_id'], 'release:workpace:unknown')
            self.assertNotEqual(by_entry['K5']['package_id'], by_entry['K17']['package_id'])
            self.assertNotIn('artifact_id', by_entry['K5'])
            self.assertEqual(by_entry['K12']['status'], 'curated')
            self.assertEqual(by_entry['K12']['software_release_id'], 'release:ice-breaker:1.2.1')

    def test_payload_review_retains_uncertainty_and_distinct_versions(self):
        records = json.loads(BUNDLE.read_text())["records"]
        identities = [r for r in records if r["type"] == "identification"]
        by_entry = {r["evidence"][0]["source_ref"]["entry"]: r for r in identities}
        self.assertEqual(sum(r["status"] == "curated" for r in identities), 35)
        self.assertEqual({e for e, r in by_entry.items() if r["status"] == "interpreted"},
                         {"K4", "K6", "K9", "K19"})
        self.assertEqual(by_entry["K23"]["software_release_id"], "release:cpu-z:1.10")
        self.assertEqual(by_entry["K11"]["software_release_id"], "release:font-xplorer-lite:1.2.2")
        for entry in ["K3", "K10", "K11", "K12", "K18", "K23", "K26", "K40"]:
            self.assertEqual(by_entry[entry]["distribution_kind"], "unknown")
            self.assertTrue(any(e["field"] == "payload_observation" for e in by_entry[entry]["evidence"]))
