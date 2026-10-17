import base64
import copy
import hashlib
import unittest
from bootdisk_catalog.source_readiness import title_evidence


class LocalizedSourceTests(unittest.TestCase):
    def fixture(self, field='TitelNO'):
        raw = {'Titel': 'Common', field: ' Norsk ', 'TitelDK': 'Dansk'}
        data = ('[K1]\n' + ''.join(k+'='+v+'\n' for k,v in raw.items())).encode()
        # ConfigParser strips surrounding whitespace from values.
        raw[field] = 'Norsk'
        file = {'path':'K.DTX','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        entry = {'source_id':'K1','raw':raw,'normalized':{'title':'Norsk'}}
        return {'schema_version':'0.9','source':{'dtx_file':dict(file,raw_base64=base64.b64encode(data).decode()),
                'sections':{'K1':copy.deepcopy(raw)}},'file_inventory':[file],'entries':[entry]}, entry

    def test_title_points_to_exact_norwegian_field(self):
        for field in ('TitelNO','TitelNo','titelno'):
            m,e=self.fixture(field)
            self.assertEqual(title_evidence(m,e)['field'],'raw/'+field)

    def test_changed_normalized_raw_and_section_do_not_override_bytes(self):
        m,e=self.fixture();e['normalized']['title']='Invented';e['raw']['TitelNO']='Invented'
        m['source']['sections']['K1']['TitelNO']='Invented'
        self.assertIsNone(title_evidence(m,e))

    def test_changed_preserved_bytes_do_not_override_inventory(self):
        m,e=self.fixture();m['source']['dtx_file']['raw_base64']=base64.b64encode(b'[K1]\nTitelNO=Invented').decode()
        self.assertIsNone(title_evidence(m,e))

    def test_foreign_or_generic_title_cannot_replace_present_norwegian_title(self):
        for title in ('Dansk','Common'):
            m,e=self.fixture();e['normalized']['title']=title
            self.assertIsNone(title_evidence(m,e))
