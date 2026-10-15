import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from bootdisk_catalog.automatic_identification import build_bundle, corroborated_name
from bootdisk_catalog.catalog import Catalog
from bootdisk_catalog.curation_bundle import restore_bundle
from bootdisk_catalog.import_ingest import import_manifest
from bootdisk_catalog.presentation import presentation_projection

class AutomaticIdentificationTests(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.source=self.root/'source';self.source.mkdir();self.payload=b'never executed'
  (self.source/'Setup.exe').write_bytes(self.payload)
  self.file=dict(path='Setup.exe',exists=True,is_file=True,size=len(self.payload),sha256=hashlib.sha256(self.payload).hexdigest())
  self.entry=dict(source_id='I10',normalized=dict(title='Dimension 4'),raw=dict(Global='Dimension 4 synkroniserer klokken.'),issues=[],files=dict(referenced=dict(installer=self.file),discovered={}))
  self.manifest=self.root/'manifest.json';self.catalog=self.root/'catalog'
 def prepare(self,entries=None):
  self.manifest.write_text(json.dumps(dict(schema_version='0.8',entries=entries or [self.entry],file_inventory=[dict(path=self.file.get('resolved_path',self.file['path']),size=self.file['size'],sha256=self.file['sha256'])])))
  import_manifest(self.manifest,self.catalog);self.ref='sha256:'+hashlib.sha256(self.manifest.read_bytes()).hexdigest()
 def run_rule(self,**kwargs):return build_bundle(Catalog.load(self.catalog),self.manifest,self.source,eligible_entries=['I10'],**kwargs)
 def test_projection_unknowns_and_repeat_preserves(self):
  self.prepare();b,a=self.run_rule();self.assertEqual(a['entries'][0]['state'],'interpreted');restore_bundle(self.catalog,b)
  c=presentation_projection(Catalog.load(self.catalog),self.manifest)[0];s=c['software'][0]
  self.assertEqual(c['curation_status'],'identified');self.assertEqual((s['status'],s['version'],s['distribution_kind']),('interpreted','unknown','unknown'))
  self.assertEqual(c['source_context']['description']['value'],self.entry['raw']['Global']);self.assertEqual(self.run_rule()[1]['entries'][0]['state'],'preserved')
 def test_deterministic_readonly(self):
  self.prepare();before={str(p):p.read_bytes() for p in self.catalog.rglob('*.json')};self.assertEqual(self.run_rule(),self.run_rule());self.assertEqual(before,{str(p):p.read_bytes() for p in self.catalog.rglob('*.json')})
 def test_hash_mismatch(self):
  self.prepare();(self.source/'Setup.exe').write_bytes(b'changed');b,a=self.run_rule();self.assertEqual(b['records'],[]);self.assertEqual(a['entries'][0]['state'],'inspecting')
 def test_protect_draft(self):
  self.prepare();b,a=self.run_rule(protected_entries=[(self.ref,'I10')]);self.assertEqual(b['records'],[]);self.assertEqual(a['entries'][0]['state'],'preserved')
 def test_source_issue(self):
  self.entry['issues']=['conflicting_launch_targets'];self.prepare();self.assertEqual(self.run_rule()[0]['records'],[])
 def test_name_alone(self):
  self.entry['raw']['Global']='Et klokkeprogram.';self.prepare();self.assertEqual(self.run_rule()[0]['records'],[])
 def test_multiple_launches(self):
  self.entry['files']['referenced']['other']=copy.deepcopy(self.file);self.prepare();self.assertEqual(self.run_rule()[0]['records'],[])
 def test_boundaries(self):
  self.assertFalse(corroborated_name('Paint','PaintShop'));self.assertTrue(corroborated_name('Dimension 4','Med DIMENSION 4 blir klokken riktig.'));self.assertFalse(corroborated_name('4','4 programmer'))
 def test_symlink(self):
  self.prepare();(self.source/'Setup.exe').unlink();other=self.root/'other';other.write_bytes(self.payload);(self.source/'Setup.exe').symlink_to(other);self.assertEqual(self.run_rule()[0]['records'],[])
 def test_shared_bytes_do_not_merge(self):
  other=copy.deepcopy(self.entry);other['source_id']='I11';other['normalized']['title']='Other Name';other['raw']['Global']='Other Name er et annet program.';self.prepare([self.entry,other])
  b,a=build_bundle(Catalog.load(self.catalog),self.manifest,self.source,eligible_entries=['I10','I11']);self.assertEqual(len([r for r in b['records'] if r['type']=='software']),2);restore_bundle(self.catalog,b)
  self.assertEqual([c['software'][0]['software_name'] for c in presentation_projection(Catalog.load(self.catalog),self.manifest)],['Dimension 4','Other Name'])

 def test_resolved_case_path_is_bound_to_original_occurrence(self):
  self.file['resolved_path']='SETUP.EXE'
  (self.source/'Setup.exe').rename(self.source/'SETUP.EXE')
  self.prepare()
  self.assertEqual(self.run_rule()[1]['entries'][0]['state'],'interpreted')

 def test_cli_snapshot_preserves_inputs_and_refuses_overwrite(self):
  from bootdisk_catalog.automatic_identification import main
  self.prepare();scope=self.root/'scope.json';scope.write_text('["I10"]')
  state=self.root/'review.json';state.write_text(json.dumps(dict(schema='bootdisk-review-workspace-v1',entries={})))
  output=self.root/'candidate';args=[str(self.catalog),'--manifest',str(self.manifest),'--source',str(self.source),'--entries',str(scope),'--review-state',str(state),'--output',str(output)]
  before={str(p):p.read_bytes() for p in self.catalog.rglob('*.json')}
  self.assertEqual(main(args),0);self.assertEqual(len(Catalog.load(output/'catalog').records_of_type('identification')),1)
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.catalog.rglob('*.json')})
  with self.assertRaises(SystemExit):main(args)
