import copy
import unittest
from bootdisk_catalog.payload_identification import qualify

def member(name='Dimension 4',version='4.2.1005',filename='D4.___'):
 return dict(name=filename,sha256='a'*64,size=20,status='read',inspection=dict(status='observed',observations=[dict(field='StringFileInfo/040904b0/'+field,value=value) for field,value in [('ProductName',name),('ProductVersion',version),('FileDescription',name)]]))
class PayloadIdentityTests(unittest.TestCase):
 def test_actual_product(self):
  result,reason=qualify('Dimension 4',[member()]);self.assertEqual(result['version'],'4.2.1005');self.assertEqual(result['name'],'Dimension 4')
 def test_framework_does_not_identify_product(self):self.assertIsNone(qualify('NVmax',[member('Microsoft Windows NT Operating System')])[0])
 def test_installer_not_product(self):self.assertIsNone(qualify('Dimension 4',[member(filename='setup.exe')])[0])
 def test_conflicting_versions(self):self.assertEqual(qualify('Dimension 4',[member(),member(version='4.3')])[1],'conflicting_product_members')
 def test_version_language_conflict(self):
  m=member();m['inspection']['observations'].append(dict(field='StringFileInfo/041404b0/ProductVersion',value='9.0'));self.assertIsNone(qualify('Dimension 4',[m])[0])
 def test_nul_and_warning(self):
  m=member();m['inspection']['observations'][0]['warning']='embedded_nul';self.assertIsNone(qualify('Dimension 4',[m])[0])
 def test_word_boundaries(self):self.assertIsNone(qualify('Paint',[member('PaintShop')])[0])
 def test_product_version_in_title(self):
  r,_=qualify('BlackBox 4.0',[member('Interscope BlackBox','4.0','ibbx.exe')]);self.assertEqual(r['name'],'BlackBox')
 def test_comma_tuple_preserved_semantics(self):self.assertEqual(qualify('LastQuit',[member('LastQuit Application','1, 0, 0, 1','LastQuit.exe')])[0]['version'],'1.0.0.1')
 def test_file_version_not_product_version(self):
  m=member();m['inspection']['observations'][1]['field']='StringFileInfo/040904b0/FileVersion';self.assertIsNone(qualify('Dimension 4',[m])[0])

 def test_real_batch_records_keep_machine_actor_and_exact_source_scope(self):
  import json
  from pathlib import Path
  from bootdisk_catalog.catalog import Catalog, LoadedRecord, SCHEMA
  root=Path(__file__).resolve().parents[1]/'data/automatic/2026-10-15-payload'
  bundle=json.loads((root/'bundle.json').read_text());audit=json.loads((root/'audit.json').read_text())
  ids=[r for r in bundle['records'] if r['type']=='identification'];self.assertEqual(len(ids),7);self.assertEqual(audit['source_interpretations_superseded'],4)
  stubs=[dict(schema=SCHEMA,type='artifact',id=r['artifact_id'],sha256=r['artifact_id'].split(':')[-1],size=r['evidence'][0]['value']['container_size']) for r in ids]
  Catalog(LoadedRecord(r,root/'fixture') for r in bundle['records']+stubs)
  for r in ids:
   self.assertEqual(r['distribution_kind'],'unknown');self.assertEqual(r['evidence'][0]['value']['actor'],'machine')
   self.assertEqual(r['evidence'][0]['value']['rule'],'payload-product-identity-1')
  self.assertEqual(next(x['version'] for x in audit['entries'] if x['name']=='Dimension 4'),'4.2.1005')
