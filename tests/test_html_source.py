import unittest,tempfile,copy
from pathlib import Path
from bootdisk_catalog.html_source import validate_html
from bootdisk_catalog.catalog import CatalogError
try:
 from bootdisk_ingest.adapters.kcd.html_menu import parse_disc
 from bootdisk_ingest.inventory import build_inventory
except ImportError:parse_disc=None

@unittest.skipIf(parse_disc is None,'HTML evidence validation requires Ingest checkout')
class HtmlSourceTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
  for p in ['scripts','html','topical/01']:(root/p).mkdir(parents=True)
  (root/'scripts/cdindex.js').write_text('''var cdindex = new Array();cdindex[0] = { 'title':"Sample", 'url':'html/topical01.html', 'category':'topical' };''')
  (root/'html/topical01.html').write_text('''<meta content="charset=iso-8859-1"><div id="content"><h1>Sample</h1><ul class="softwaredetails"></ul><p class="softwaredesc">Original.</p><img class="softwareimage" src="../topical/01/image.jpg"><a href="../topical/01/setup.exe">Install</a></div>''')
  (root/'topical/01/image.jpg').write_bytes(b'image');(root/'topical/01/setup.exe').write_bytes(b'never execute')
  inv=build_inventory(root);self.m=parse_disc(root,inv);self.m['file_inventory']=inv['files'];self.e=self.m['entries'][0]
 def test_bound_source(self):self.assertEqual(validate_html(self.m,self.e)['title'],'Sample')
 def test_forged_description(self):
  self.e['evidence']['html_menu']['observation']['description']='Invented'
  with self.assertRaises(CatalogError):validate_html(self.m,self.e)
 def test_modified_source_bytes(self):
  self.m['source']['documents']['html/topical01.html']['raw_base64']='eA=='
  with self.assertRaises(CatalogError):validate_html(self.m,self.e)
 def test_asset_from_other_entry(self):
  self.e['files']['discovered']['screenshot']['path']='other/image.jpg'
  with self.assertRaises(CatalogError):validate_html(self.m,self.e)
 def test_wrong_index_position(self):
  self.e['evidence']['html_menu']['index_position']=-1
  with self.assertRaises(CatalogError):validate_html(self.m,self.e)
 def test_missing_file_not_invented(self):
  self.e['files']['referenced']['link_1']['exists']=False
  with self.assertRaises(CatalogError):validate_html(self.m,self.e)
