import unittest
import hashlib,base64
from bootdisk_catalog.late_dtx import fields
from bootdisk_catalog.catalog import CatalogError
class SelectorTests(unittest.TestCase):
 def test_no_claim_for_ordinary_entries(self):
  self.assertIsNone(fields({}, {'source_id':'K36'}))
 def test_foreign_bytes_cannot_claim_pixia(self):
  raw=b'[K36]\nTitel=Other';h=hashlib.sha256(raw).hexdigest()
  manifest={'source':{'dtx_file':{'sha256':h,'raw_base64':base64.b64encode(raw).decode()}},'file_inventory':[{'path':'K.DTX','sha256':h}]}
  with self.assertRaises(CatalogError):fields(manifest,{'source_id':'Flytter','evidence':{'physical_section':{'name':'K36','index':0}}})
