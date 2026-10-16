import base64,copy,hashlib,unittest
from bootdisk_catalog.calendar_source import validate_calendar
from bootdisk_catalog.source_readiness import title_evidence
from bootdisk_catalog.catalog import CatalogError

class CalendarSourceTests(unittest.TestCase):
    def fixture(self):
        raw=b'[J1]\nTitel=Calendar\nFolder=01\n';sha=hashlib.sha256(raw).hexdigest();fields={'Titel':'Calendar','Folder':'01'}
        source={'path':'J.DTX','encoding':'cp1252','sha256':sha,'size':len(raw),'raw_base64':base64.b64encode(raw).decode(),'sections':{'J1':fields}}
        m={'schema_version':'0.9','source':{'supplemental_metadata':[source]},'file_inventory':[{'path':'J.DTX','size':len(raw),'sha256':sha}]}
        e={'source_id':'J1','raw':fields,'normalized':{'title':'Calendar'},'evidence':{'calendar_metadata':{'path':'J.DTX','sha256':sha,'section':'J1','title_field':'Titel'}}}
        return m,e
    def test_bound_title(self):
        m,e=self.fixture();self.assertTrue(validate_calendar(m,e));self.assertEqual(title_evidence(m,e)['value'],'Calendar')
    def test_altered_raw_fields_rejected(self):
        m,e=self.fixture();e=copy.deepcopy(e);e['raw']['Titel']='Other'
        with self.assertRaises(CatalogError):validate_calendar(m,e)
    def test_cross_source_rejected(self):
        m,e=self.fixture();e['evidence']['calendar_metadata']['section']='J2'
        with self.assertRaises(CatalogError):validate_calendar(m,e)
    def test_wrong_inventory_hash_rejected(self):
        m,e=self.fixture();m['file_inventory'][0]['sha256']='0'*64
        with self.assertRaises(CatalogError):validate_calendar(m,e)
