"""Validate the approved round without shipping original CD bytes."""
import json
from pathlib import Path
import unittest
from bootdisk_catalog.catalog import Catalog, LoadedRecord, SCHEMA
from bootdisk_catalog.curate import _identifications_for_source

ROOT = Path(__file__).resolve().parents[1]
class WorkshopRoundTests(unittest.TestCase):
    def test_approved_source_bindings_and_graph(self):
        bundle = json.loads((ROOT/'data/curation/workshop-2026-09-29.json').read_text())
        audit = json.loads((ROOT/'data/curation/workshop-2026-09-29-audit.json').read_text())
        records = bundle['records']
        identifiers = {r['id']: r for r in records if r['type']=='identification'}
        self.assertEqual(len(identifiers), 50)
        self.assertEqual(len(audit['entries']), 50)
        self.assertEqual(audit['unresolved_entries'], 110)
        self.assertEqual(len(audit['source_issues']), 2)
        # Original artifacts are imported locally. Minimal graph stubs here test
        # relationship integrity, not original sizes or possession of CD bytes.
        hashes = {r['artifact_id'].split(':')[-1] for r in identifiers.values()}
        stubs = [{'schema':SCHEMA,'type':'artifact','id':'artifact:sha256:'+h,
                  'sha256':h,'size':0} for h in hashes]
        catalog = Catalog([LoadedRecord(r, ROOT/'fixture') for r in records+stubs])
        keys = set()
        for row in audit['entries']:
            key = row['key']
            pair = (key['manifest'],key['entry'])
            self.assertNotIn(pair, keys)
            keys.add(pair)
            matches = _identifications_for_source(catalog,*pair)
            self.assertEqual([r['id'] for r in matches], [row['identification_id']])
            ident = matches[0]
            self.assertEqual(ident['artifact_id'],'artifact:sha256:'+row['launch_sha256'])
            self.assertNotIn('package_id',ident)
            release = catalog.release_for_identification(ident['id'])
            self.assertEqual(release['version'],row['version'])
            self.assertEqual(ident['distribution_kind'],'trial' if row['edition_note']=='trial' else 'unknown')
            observed = ident['evidence'][0]
            self.assertEqual(observed['source_ref']['path'],row['source_path'])
            self.assertEqual(observed['value']['sha256'],row['source_sha256'])
            self.assertTrue(observed['value']['quote'].strip())
        for issue in audit['source_issues']:
            self.assertEqual(_identifications_for_source(catalog,issue['key']['manifest'],issue['key']['entry']),[])
        self.assertEqual(_identifications_for_source(catalog,'sha256:'+'0'*64,audit['entries'][0]['key']['entry']),[])
