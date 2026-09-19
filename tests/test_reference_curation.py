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
            self.assertEqual(by_entry['K12']['status'], 'interpreted')
            self.assertEqual(by_entry['K12']['software_release_id'], 'release:ice-breaker:unknown')
