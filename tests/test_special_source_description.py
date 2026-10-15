import copy,json,tempfile,unittest
from pathlib import Path
from bootdisk_catalog.catalog import CatalogError
from bootdisk_catalog.presentation import source_context

class SpecialDescriptionTests(unittest.TestCase):
 def setUp(self):
  fields={'Speciel':'PC-ens driftsutgifter','SpecielTekst':'Original tekst\r\nBevar mellomrom. '}
  file={'path':'K.DTX','size':123,'sha256':'a'*64}
  self.manifest={'source':{'sections':{'Generelt':fields}},'file_inventory':[file],
    'entries':[{'source_id':'Special','raw':dict(fields),'normalized':{'title':fields['Speciel']},
      'evidence':{'metadata_section':'Generelt','title_field':'Speciel','description_field':'SpecielTekst','metadata_container':dict(file)}}]}
 def context(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'manifest.json';p.write_text(json.dumps(self.manifest));return source_context(p)['Special']
 def test_preserves_exact_source_and_pointer(self):
  d=self.context()['description'];self.assertEqual(d['value'],self.manifest['source']['sections']['Generelt']['SpecielTekst']);self.assertEqual(d['source_ref']['pointer'],'/entries/0/raw/SpecielTekst')
 def test_changed_entry_text_rejected(self):
  self.manifest['entries'][0]['raw']['SpecielTekst']='Rewritten'
  with self.assertRaises(CatalogError):self.context()
 def test_changed_title_rejected(self):
  self.manifest['entries'][0]['normalized']['title']='Other'
  with self.assertRaises(CatalogError):self.context()
 def test_container_mismatch_rejected(self):
  self.manifest['entries'][0]['evidence']['metadata_container']['sha256']='b'*64
  with self.assertRaises(CatalogError):self.context()
 def test_no_evidence_does_not_promote_special_text(self):
  self.manifest['entries'][0]['evidence']={};self.assertIsNone(self.context()['description'])
