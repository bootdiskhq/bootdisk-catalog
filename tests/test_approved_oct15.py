"""Approval must preserve source scope, uncertainty and deferred entries."""
import json
from pathlib import Path
import unittest
from bootdisk_catalog.catalog import Catalog, LoadedRecord, SCHEMA
from bootdisk_catalog.curate import _identifications_for_source
R=Path(__file__).resolve().parents[1]
class ApprovedRoundTests(unittest.TestCase):
 def test_scope_uncertainty_and_binding(self):
  bundle=json.loads((R/'data/curation/approved-2026-10-15.json').read_text())
  audit=json.loads((R/'data/curation/approved-2026-10-15-audit.json').read_text())
  records=bundle['records'];ids=[r for r in records if r['type']=='identification']
  stubs=[dict(schema=SCHEMA,type='artifact',id=a,sha256=a.split(':')[-1],size=0) for a in sorted({r['artifact_id'] for r in ids})]
  cat=Catalog([LoadedRecord(r,R/'fixture') for r in records+stubs])
  self.assertEqual(len(ids),88);self.assertEqual(len(audit['deferred']),23)
  self.assertEqual(sum(r['version']=='unknown' for r in audit['entries']),14)
  self.assertEqual(sum(r['inferred'] for r in audit['entries']),9)
  for row in audit['entries']:
   key=row['key'];matches=_identifications_for_source(cat,key['manifest'],key['entry'])
   self.assertEqual([r['id'] for r in matches],[row['identification_id']])
   ident=matches[0];self.assertEqual(ident['artifact_id'],'artifact:sha256:'+row['launch_sha256'])
   self.assertEqual(ident['evidence'][0]['kind'],'interpreted' if row['inferred'] else 'observed')
   self.assertEqual(cat.release_for_identification(ident['id'])['version'],row['version'])
   self.assertEqual(ident['distribution_kind'],'trial' if row['name']=='SuperCat' else 'unknown')
   for ev in ident['evidence']:
    self.assertEqual({k:ev['source_ref'][k] for k in key},key)
  for row in audit['deferred']:
   self.assertEqual(_identifications_for_source(cat,row['key']['manifest'],row['key']['entry']),[])
  self.assertTrue(all(r['version']=='unknown' for r in audit['entries'] if r['name'] in ('Ad-aware','Google Toolbar for IE','FileDuster','Monitors Matter CheckScreen')))
  self.assertEqual(next(r['version'] for r in audit['entries'] if r['name']=='WebWasher' and r['medium']=='kcd-8-2001'),'3.0 beta 3')
  self.assertEqual(next(r['version'] for r in audit['entries'] if r['name']=='Interscope BlackBox' and r['medium']=='kcd-9-2000'),'3.0')
