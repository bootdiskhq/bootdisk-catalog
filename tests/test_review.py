from copy import deepcopy
import hashlib
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bootdisk_catalog.catalog import Catalog
from bootdisk_catalog.curation_bundle import restore_bundle, export_bundle
from bootdisk_catalog.import_ingest import import_manifest
from bootdisk_catalog.review import ReviewWorkspace, ReviewError

ROOT = Path(__file__).resolve().parents[1]


def racing_save(root, request, barrier, output):
    barrier.wait()
    try:
        output.put(ReviewWorkspace(root).call('saveDraft', request)['operation_id'])
    except ReviewError as error:
        output.put(error.payload['code'])


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        manifest = ROOT / 'tests/fixtures/kcd15-2001-observations.json'
        self.manifest = 'sha256:' + hashlib.sha256(manifest.read_bytes()).hexdigest()
        catalog = self.root / 'catalog'
        import_manifest(manifest, catalog)
        bundle = json.loads((ROOT / 'data/curation/kcd15-2001.json').read_text())
        # This metadata-only test manifest has its own digest, distinct from media.
        for r in bundle['records']:
            for e in r.get('evidence', []):
                e['source_ref']['manifest'] = self.manifest
        restore_bundle(catalog, bundle)
        self.catalog = catalog
        self.workspace = ReviewWorkspace(self.root / 'review')
        self.assertEqual(self.workspace.initialize(catalog, manifest), 39)
        self.key = dict(manifest=self.manifest, entry='K23')

    def get(self, key=None):
        return self.workspace.call('getEntry', dict(key=key or self.key))

    def request(self, op='op1', key=None, **extra):
        e = self.get(key)
        return dict(key=e['key'], expected_revision=e['revision'], operation_id=op, **extra)

    def assert_error(self, code, callback):
        with self.assertRaises(ReviewError) as caught:
            callback()
        self.assertEqual(caught.exception.payload['code'], code)
        return caught.exception.payload

    def test_queue_and_resume_restart(self):
        q = self.workspace.call('getQueue', dict(manifest=self.manifest, filter='pending'))
        self.assertEqual(len(q['items']), 39)
        self.assertEqual(q['items'][0]['key']['entry'], 'K1')
        self.assertEqual(len(self.workspace.call('getQueue', dict(manifest=self.manifest, filter='open_fields'))['items']), 36)
        self.workspace.call('setResume', dict(key=self.key))
        other = ReviewWorkspace(self.workspace.root)
        self.assertEqual(other.call('getQueue', dict(manifest=self.manifest, filter='all'))['resume_key'], self.key)

    def test_draft_is_durable_and_not_exported(self):
        draft = self.get()['draft']
        draft['claims']['description']['value']['text'] = ''
        self.workspace.call('saveDraft', self.request(draft=draft))
        self.assertEqual(ReviewWorkspace(self.workspace.root).call('getEntry', dict(key=self.key))['draft'], draft)
        self.assert_error('validation_failed', lambda: self.workspace.call('approve', self.request('approve')))
        export = self.root / 'export'
        self.workspace.export_catalog(export)
        self.assertEqual(export_bundle(Catalog.load(export)), export_bundle(Catalog.load(self.catalog)))

    def test_approve_corrected_prose_updates_graph_and_undo_preserves_draft(self):
        before = self.get()['accepted']
        draft = self.get()['draft']
        draft['claims']['description']['value']['text'] = 'CPU-Z viser opplysninger om prosessoren.'
        draft['claims']['description']['reason'] = 'Beskrivelsen støttes av den opprinnelige omtalen.'
        self.workspace.call('saveDraft', self.request(draft=draft))
        receipt = self.workspace.call('approve', self.request('approve'))
        self.assertEqual(receipt['entry']['queue_state'], 'reviewed')
        exported = self.root / 'after'
        self.workspace.export_catalog(exported)
        descriptions = Catalog.load(exported).records_of_type('description')
        self.assertTrue(any(r['text'] == draft['claims']['description']['value']['text'] for r in descriptions))
        draft['claims']['description']['value']['text'] = 'Ny uferdig tekst'
        self.workspace.call('saveDraft', self.request('draft2', draft=draft))
        undone = self.workspace.call('undo', self.request('undo', decision_id=receipt['decision_id']))
        self.assertEqual(undone['entry']['accepted'], before)
        self.assertEqual(undone['entry']['draft'], draft)
        self.assertEqual(undone['entry']['queue_state'], 'pending')
        self.assertEqual(len(self.workspace.read()['events']), 4)
        self.workspace.export_catalog(self.root / 'undone')
        self.assertEqual(export_bundle(Catalog.load(self.root / 'undone')), export_bundle(Catalog.load(self.catalog)))

    def test_idempotency_precedes_revision_and_reuse_rejected(self):
        request = self.request()
        receipt = self.workspace.call('approve', request)
        self.assertEqual(self.workspace.call('approve', request), receipt)
        self.assertEqual(len(self.workspace.read()['events']), 1)
        self.assert_error('operation_id_reused', lambda: self.workspace.call('defer', dict(request, reason='Senere')))
        conflict = self.assert_error('revision_conflict', lambda: self.workspace.call('approve', dict(request, operation_id='new')))
        self.assertEqual(conflict['current_entry'], self.get())

    def test_defer_retains_draft_and_reason(self):
        draft = self.get()['draft']
        self.workspace.call('saveDraft', self.request(draft=draft))
        self.workspace.call('defer', self.request('skip', reason='Undersøk mer senere'))
        self.assertEqual(self.get()['draft'], draft)
        self.assertEqual(self.get()['defer_reason'], 'Undersøk mer senere')
        self.assertEqual(self.workspace.read()['events'][-1]['reason'], 'Undersøk mer senere')
        self.assertEqual(len(self.workspace.call('getQueue', dict(manifest=self.manifest, filter='deferred'))['items']), 1)

    def test_failed_replace_keeps_previous_state_and_retry_can_commit(self):
        before = self.workspace.path.read_bytes()
        request = self.request()
        with patch('bootdisk_catalog.review.os.replace', side_effect=OSError('disk failure')):
            self.assert_error('write_failed', lambda: self.workspace.call('approve', request))
        self.assertEqual(self.workspace.path.read_bytes(), before)
        self.workspace.call('approve', request)
        self.assertEqual(len(self.workspace.read()['events']), 1)

    def test_uncertain_receipt_after_replace_is_safely_retried(self):
        request = self.request()
        import os
        real = os.fsync
        calls = []
        def fail_directory(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError('directory sync interrupted')
            return real(fd)
        with patch('bootdisk_catalog.review.os.fsync', side_effect=fail_directory):
            self.assert_error('write_failed', lambda: self.workspace.call('approve', request))
        receipt = self.workspace.call('approve', request)
        self.assertEqual(receipt['entry']['queue_state'], 'reviewed')
        self.assertEqual(len(self.workspace.read()['events']), 1)

    def test_foreign_evidence_and_unsupported_promotion_rejected(self):
        draft = self.get()['draft']
        draft['claims']['identity']['evidence_ids'] = ['made-up-source']
        self.assert_error('validation_failed', lambda: self.workspace.call('saveDraft', self.request(draft=draft)))
        draft = self.get()['draft']
        draft['claims']['version']['value'] = '9.99'
        self.workspace.call('saveDraft', self.request(draft=draft))
        self.assert_error('validation_failed', lambda: self.workspace.call('approve', self.request('approve')))

    def test_provisional_identity_is_not_promoted_by_review(self):
        key = dict(self.key, entry='K4')
        receipt = self.workspace.call('approve', self.request(key=key))
        self.assertEqual(receipt['entry']['accepted']['identification_status'], 'interpreted')
        self.assertIn('identity', next(r for r in self.workspace.call('getQueue', dict(manifest=self.manifest, filter='open_fields'))['items'] if r['key'] == key)['open_fields'])

    def test_new_version_uses_server_id_and_undo_conflicts_after_other_decision(self):
        draft = self.get()['draft']
        draft['claims']['version'].update(value='1.10-test', reason='Synthetic test of a human-reviewed version change.')
        self.workspace.call('saveDraft', self.request(draft=draft))
        receipt = self.workspace.call('approve', self.request('approve'))
        self.assertTrue(any(r['type'] == 'software_release' and r['version'] == '1.10-test' for r in self.workspace.read()['records']))
        other_key = dict(self.key, entry='K4')
        other_draft = self.get(other_key)['draft']
        other_draft['claims']['description']['value']['text'] = 'Changed test description'
        other_draft['claims']['description']['reason'] = 'Test of another semantic change.'
        self.workspace.call('saveDraft', self.request('other-draft', key=other_key, draft=other_draft))
        self.workspace.call('approve', self.request('other', key=other_key))
        self.assert_error('undo_conflict', lambda: self.workspace.call('undo', self.request('undo', decision_id=receipt['decision_id'])))

    def test_backup_restore_preserves_history_receipts_and_resume(self):
        request = self.request()
        receipt = self.workspace.call('approve', request)
        self.workspace.call('setResume', dict(key=self.key))
        backup = self.root / 'backup.json'
        self.workspace.backup(backup)
        restored = ReviewWorkspace(self.root / 'restored')
        restored.restore(backup)
        self.assertEqual(restored.read(), self.workspace.read())
        self.assertEqual(restored.call('approve', request), receipt)
        self.assert_error('validation_failed', lambda: restored.restore(backup))

    def test_competing_processes_cannot_overwrite_revision(self):
        ctx = multiprocessing.get_context('spawn')
        barrier = ctx.Barrier(2)
        output = ctx.Queue()
        draft = self.get()['draft']
        requests = [self.request(op, draft=draft) for op in ('first', 'second')]
        workers = [ctx.Process(target=racing_save, args=(self.workspace.root, r, barrier, output)) for r in requests]
        for w in workers: w.start()
        for w in workers:
            w.join(20)
            self.assertEqual(w.exitcode, 0)
        values = [output.get(timeout=2), output.get(timeout=2)]
        self.assertEqual(values.count('revision_conflict'), 1)
        self.assertEqual(len(self.workspace.read()['events']), 1)

    def test_shared_software_edit_rejected_without_partial_write(self):
        state = self.workspace.read()
        ident = next(r for r in state['records'] if r['type'] == 'identification' and r['software_release_id'] == 'release:cpu-z:1.10')
        other = next(r for r in state['records'] if r['type'] == 'identification' and r['id'] != ident['id'])
        other['software_release_id'] = ident['software_release_id']
        self.workspace.write(state)
        draft = self.get()['draft']
        draft['claims']['content_kind'].update(value='game', reason='Synthetic conflict test')
        self.workspace.call('saveDraft', self.request(draft=draft))
        before = self.workspace.path.read_bytes()
        self.assert_error('shared_record_conflict', lambda: self.workspace.call('approve', self.request('approve')))
        self.assertEqual(self.workspace.path.read_bytes(), before)

    def test_unknown_version_cannot_be_certified(self):
        draft = self.get()['draft']
        draft['claims']['version'].update(value='unknown', assessment='accepted', reason='Wrong assessment')
        self.workspace.call('saveDraft', self.request(draft=draft))
        self.assert_error('validation_failed', lambda: self.workspace.call('approve', self.request('approve')))

    def test_original_catalog_untouched_and_initialization_never_overwrites(self):
        before = export_bundle(Catalog.load(self.catalog))
        self.workspace.call('approve', self.request())
        self.assertEqual(export_bundle(Catalog.load(self.catalog)), before)
        self.assert_error('validation_failed', lambda: self.workspace.initialize(self.catalog, ROOT / 'tests/fixtures/kcd15-2001-observations.json'))
