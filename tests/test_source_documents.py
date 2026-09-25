import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from bootdisk_catalog.source_documents import project
from bootdisk_catalog.catalog import CatalogError

class SourceDocumentTests(unittest.TestCase):
    def test_exact_manifest_and_file_binding_required_without_graph_writes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw=b'{\\rtf1 Text}';digest=hashlib.sha256(raw).hexdigest()
            file={'path':'No.rtf','exists':True,'sha256':digest,'size':len(raw)}
            m=root/'m.json';m.write_text(json.dumps({'entries':[{'source_id':'K1','files':{'discovered':{'description_rtf':file}}}],'file_inventory':[file]}));before=m.read_bytes()
            ref='sha256:'+hashlib.sha256(before).hexdigest()
            doc={'key':{'manifest':ref,'entry':'K1'},'path':'No.rtf','pointer':'/entries/0/files/discovered/description_rtf','sha256':digest,'size':len(raw),'raw_base64':base64.b64encode(raw).decode(),'method':'rtf-ansi-text-terminal-nul-1','text':'Text'}
            obs={'schema':'bootdisk-rtf-observations-1','manifest':ref,'documents':[doc]};p=root/'o.json';p.write_text(json.dumps(obs))
            self.assertEqual(project(m,p)['documents'][0]['text'],'Text');self.assertEqual(m.read_bytes(),before)
            for field,value in [('path','Elsewhere.rtf'),('raw_base64','AA=='),('pointer','/entries/1/files/discovered/description_rtf')]:
                old=doc[field];doc[field]=value;p.write_text(json.dumps(obs))
                with self.assertRaises(CatalogError):project(m,p)
                doc[field]=old
            obs['manifest']='sha256:'+'a'*64;p.write_text(json.dumps(obs))
            with self.assertRaises(CatalogError):project(m,p)
