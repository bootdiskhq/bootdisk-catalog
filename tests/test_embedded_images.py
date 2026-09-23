import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from bootdisk_catalog.embedded_images import import_images
from bootdisk_catalog.catalog import Catalog

class EmbeddedImageTests(unittest.TestCase):
    def test_verified_resources_make_occurrences_not_semantic_claims(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'base').mkdir();(root/'resources').mkdir()
            parent={'path':'movie.dxr','size':100,'sha256':'a'*64}
            mp=root/'manifest.json';mp.write_text(json.dumps({'entries':[{'source_id':'Spil1'}],'file_inventory':[parent]}))
            ref='sha256:'+hashlib.sha256(mp.read_bytes()).hexdigest()
            item={'entry_source_id':'Spil1','kind':'screenshot','source_ref':{'manifest':ref,'entry':'Spil1'}}
            for i,(name,tag) in enumerate((('pixels','BITD'),('palette','CLUT'),('metadata','CASt'))):
                data=name.encode();sha=hashlib.sha256(data).hexdigest();(root/'resources'/sha).write_bytes(data)
                item[name]={'container':parent,'sha256':sha,'size':len(data),'offset':i*20,'resource_id':i,'tag':tag,'object_path':'resources/'+sha}
            report={'schema':'bootdisk-embedded-images-1','manifest':ref,'assets':[item]};rp=root/'images.json';rp.write_text(json.dumps(report))
            self.assertEqual(import_images(rp,mp,root/'base',root/'out'),1)
            c=Catalog.load(root/'out');self.assertEqual(len(c.records_of_type('artifact')),3)
            self.assertEqual(len(c.records_of_type('occurrence')),3)
            self.assertEqual(c.records_of_type('software'),())
            self.assertTrue(all(o['source_ref']['manifest']==ref for o in c.records_of_type('occurrence')))
            with self.assertRaisesRegex(ValueError,'new'):import_images(rp,mp,root/'base',root/'out')
            item['source_ref']['entry']='other';rp.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'reference mismatch'):import_images(rp,mp,root/'base',root/'bad')
            item['source_ref']['entry']='Spil1';rp.write_text(json.dumps(report))
            (root/item['pixels']['object_path']).write_bytes(b'xxxxxx')
            with self.assertRaisesRegex(ValueError,'changed'):import_images(rp,mp,root/'base',root/'bad')
            self.assertFalse((root/'bad').exists())
