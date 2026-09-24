import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog.catalog import CatalogError
from bootdisk_catalog.presentation import source_context, presentation_projection
from test_presentation import PresentationProjectionTests


class ToolsContextTests(unittest.TestCase):
    def fixture(self, norwegian=True):
        raw = b'[I1]\nNavn=Tool\nInstruksNo=Original omtale\nSpil=Ja\n'
        fields = {'Navn': 'Tool', 'InstruksNo': 'Original omtale', 'Spil': 'Ja'}
        if not norwegian:
            raw = raw.replace(b'InstruksNo', b'InstruksDK')
            fields['InstruksDK'] = fields.pop('InstruksNo')
        file = dict(path='TOOLS.DTX', sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
        binding = dict(path=file['path'], sha256=file['sha256'], section='I1')
        return dict(entries=[dict(source_id='I1', raw=fields, evidence=dict(metadata_source=binding,
                    description_tools=dict(**binding, field='InstruksNo', language='nb-NO', text='Original omtale' if norwegian else None)))],
                    file_inventory=[file], source=dict(supplemental_metadata=[dict(**file,
                    resolved_path='TOOLS.DTX', encoding='cp1252', raw_base64=base64.b64encode(raw).decode(), sections={'I1': fields})]))

    def project(self, manifest):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'manifest.json'
            path.write_text(json.dumps(manifest))
            return source_context(path)['I1']

    def test_original_text_bound_to_exact_source_and_not_a_classification(self):
        result = self.project(self.fixture())
        self.assertEqual(result['description']['value'], 'Original omtale')
        self.assertEqual(result['description']['source_ref']['pointer'], '/entries/0/evidence/description_tools/text')
        self.assertEqual(result['menu_groups']['value'], [])

    def test_missing_norwegian_text_has_no_language_or_rtf_fallback(self):
        m = self.fixture(norwegian=False)
        m['entries'][0]['evidence']['description_rtf'] = {'text': 'Not the Tools source'}
        self.assertIsNone(self.project(m)['description'])

    def test_forged_text_bytes_or_binding_are_rejected(self):
        for change in ('text', 'bytes', 'section', 'inventory', 'raw'):
            with self.subTest(change=change):
                m = self.fixture()
                if change == 'text': m['entries'][0]['evidence']['description_tools']['text'] = 'Invented'
                if change == 'bytes': m['source']['supplemental_metadata'][0]['raw_base64'] = 'AA=='
                if change == 'section': m['entries'][0]['evidence']['metadata_source']['section'] = 'I2'
                if change == 'inventory': m['file_inventory'][0]['size'] += 1
                if change == 'raw': m['entries'][0]['raw']['InstruksNo'] = 'Invented'
                with self.assertRaises(CatalogError): self.project(m)


class ExpansionTests(PresentationProjectionTests):
    def expanded(self):
        old = json.loads(self.manifest_path.read_text())
        old['entries'].append(dict(source_id='I1', normalized=dict(title='New source')))
        path = self.workspace/'expanded.json'
        path.write_text(json.dumps(old))
        return path

    def test_old_decisions_keep_binding_and_new_entry_remains_pending(self):
        from bootdisk_catalog import Catalog
        catalog = Catalog.load(self.root)
        before = {p: p.read_bytes() for p in self.root.rglob('*.json')}
        cards = presentation_projection(catalog, self.expanded(), previous_manifest=self.manifest_path)
        self.assertEqual(cards[0]['curation_status'], 'identified')
        self.assertEqual(cards[0]['decision_source']['manifest'], 'sha256:'+hashlib.sha256(self.manifest_path.read_bytes()).hexdigest())
        self.assertNotEqual(cards[0]['decision_source'], cards[0]['source_context']['key'])
        self.assertEqual(cards[2]['curation_status'], 'pending')
        self.assertEqual(cards[2]['software'], [])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*.json')})

    def test_changed_old_source_or_duplicate_id_is_rejected(self):
        from bootdisk_catalog import Catalog
        for change in ('entry', 'inventory', 'duplicate', 'metadata'):
            with self.subTest(change=change):
                path = self.expanded(); m = json.loads(path.read_text())
                if change == 'entry': m['entries'][0]['normalized']['title'] = 'Changed'
                if change == 'inventory': m['file_inventory'] = [dict(path='changed')]
                if change == 'duplicate': m['entries'][-1]['source_id'] = 'K1'
                if change == 'metadata':
                    old = json.loads(self.manifest_path.read_text()); old['source'] = {'sha256': 'old'}
                    self.manifest_path.write_text(json.dumps(old)); m['source'] = {'sha256': 'new'}
                path.write_text(json.dumps(m))
                with self.assertRaises(CatalogError):
                    presentation_projection(Catalog.load(self.root), path, previous_manifest=self.manifest_path)
