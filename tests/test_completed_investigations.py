import unittest
from bootdisk_catalog.completed_investigations import RECORDS, completed_investigation

class CompletedInvestigationsTests(unittest.TestCase):
    def test_exact_source_matches(self):
        for record in RECORDS:
            result = completed_investigation(record['manifest'], record['entry'])
            self.assertEqual(result['pattern'], 'documented_source_defect')
            self.assertTrue(result['explanation'])
            self.assertNotIn('selected_launch_target', result)
    def test_changed_manifest_reopens(self):
        for record in RECORDS:
            self.assertIsNone(completed_investigation('sha256:'+'0'*64, record['entry']))
    def test_other_entry_cannot_inherit(self):
        self.assertIsNone(completed_investigation(RECORDS[0]['manifest'], 'different'))
    def test_unique_keys_and_preserved_evidence(self):
        self.assertEqual(len(RECORDS), len({(r['manifest'],r['entry']) for r in RECORDS}))
        for r in RECORDS:
            self.assertTrue(r['source_checks'])
            self.assertEqual(r['entry'],r['finding']['entry'])

    def test_assessment_reopens_on_changed_bytes(self):
        import hashlib, json, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from test_source_readiness import SourceReadinessTests
        from bootdisk_catalog.source_readiness import assess_manifest
        manifest=SourceReadinessTests().manifest(['unresolved_warning_continue_launch'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.json';path.write_text(json.dumps(manifest))
            digest='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
            record={'manifest':digest,'entry':'K1','completed_at':'2026-10-16','explanation':'Kjent kildeavvik.'}
            with patch('bootdisk_catalog.completed_investigations.RECORDS',[record]):
                done=assess_manifest(path)['K1']
                self.assertEqual(done['machine_tasks'],[])
                self.assertIn('unresolved_warning_continue_launch',done['file_association']['issues'])
                self.assertFalse(done['file_association']['runtime_verified'])
                path.write_text(path.read_text()+'\n')
                self.assertIn('inspect_file_association',assess_manifest(path)['K1']['machine_tasks'])
