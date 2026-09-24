import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bootdisk_catalog.first_pass import first_pass, prepare_first_pass, render_report, main, STATUSES, STAGES
from bootdisk_catalog.intake import build_candidates, prepare_intake
from bootdisk_catalog.import_ingest import IngestImportError
from test_intake import fixture, encoded, snapshot


def analyze(m):
    raw = encoded(m)
    return first_pass(raw, encoded(build_candidates(raw)))


def fields(result):
    return {f['field']: f for f in result['entries'][0]['fields']}


class FirstPassTests(unittest.TestCase):
    def test_exact_original_description_and_bound_category_suggestion(self):
        m = fixture(); m['entries'][0]['normalized']['categories'] = ['games']
        r = analyze(m); f = fields(r)
        self.assertEqual(f['description']['proposed'], '  Original omtale\r\n')
        self.assertEqual(f['content_kind']['proposed'], 'game')
        self.assertEqual(f['description']['status'], 'candidate')
        for field in f.values():
            for evidence in field['evidence']:
                ref = evidence['source_ref']; value = m
                self.assertEqual(ref['manifest'], r['input']['manifest'])
                for part in ref['pointer'].split('/')[1:]:
                    value = value[int(part)] if isinstance(value, list) else value[part]
                self.assertEqual(value, evidence['value'])
        self.assertEqual(r['summary']['automatic_decisions'], 0)
        self.assertEqual(r['summary']['human_exceptions'], 0)
        self.assertEqual(r['entries'][0]['stage'], 'inspecting')

    def test_no_year_launcher_or_demo_keyword_inference(self):
        m = fixture();m['entries'][0]['normalized']['title'] = 'Example 2000 version 3.5 Freeware'
        m['entries'][0]['evidence']['description_source']['text']['cp1252_view'] = 'This full tool can create a demo for Another Product 7.0.'
        second = copy.deepcopy(m['entries'][0]);second['source_id'] = 'K2D1';second['normalized']['title'] = 'Different product';m['entries'].append(second)
        r = analyze(m)
        for row in r['entries']:
            f = {x['field']: x for x in row['fields']}
            for name in ['identity','version','distribution_kind']:
                self.assertIsNone(f[name]['proposed'])
            self.assertFalse(row['requires_human'])
        self.assertNotEqual(r['entries'][0]['key'],r['entries'][1]['key'])

    def test_broad_mixed_and_unknown_groups_are_not_claims(self):
        for groups in [[],['programs'],['school'],['games','programs'],['Games']]:
            with self.subTest(groups=groups):
                m=fixture();m['entries'][0]['normalized']['categories']=groups
                f=fields(analyze(m))['content_kind']
                self.assertEqual(f['status'],'inspect');self.assertIsNone(f['proposed'])

    def test_source_conflicts_stop_suggestions_without_forcing_human_review(self):
        for issue in ['conflicting_launch_targets','unknown_future_issue','missing_launch_file']:
            with self.subTest(issue=issue):
                m=fixture();m['entries'][0]['issues']=[issue];m['entries'][0]['normalized']['categories']=['games']
                r=analyze(m); f=fields(r)
                self.assertEqual(f['identity']['status'],'conflict')
                self.assertEqual(f['description']['status'],'conflict')
                self.assertFalse(any(x['status']=='candidate' for x in f.values()))
                self.assertIn('resolve_source_issues',[t['code'] for t in r['entries'][0]['tasks']])
                self.assertEqual(r['summary']['human_exceptions'],0)

    def test_missing_reference_without_issue_code_still_blocks_suggestions(self):
        m=fixture();e=m['entries'][0];e['normalized']['categories']=['games']
        e['files']['referenced']['direct_1']={'path':'Missing.exe','exists':False}
        e['files']['inventory_refs']=[]
        r=analyze(m)
        self.assertEqual(fields(r)['identity']['status'],'conflict')
        self.assertEqual(fields(r)['description']['status'],'conflict')
        self.assertIn('resolve_missing_files',[t['code'] for t in r['entries'][0]['tasks']])
        self.assertFalse(any(f['status']=='candidate' for f in r['entries'][0]['fields']))

    def test_missing_and_blank_descriptions_are_unknown_with_machine_work(self):
        for value in [None, '', ' \r\n']:
            m=fixture()
            m['entries'][0]['evidence']['description_source']=None if value is None else {'text':{'cp1252_view':value}}
            r=analyze(m);f=fields(r)['description']
            self.assertEqual(f['status'],'retain_unknown');self.assertIsNone(f['proposed'])
            self.assertIn('inspect_description',[t['code'] for t in r['entries'][0]['tasks']])

    def test_changed_candidates_and_human_decisions_are_rejected(self):
        raw=encoded(fixture());c=build_candidates(raw)
        for mutate in [lambda d:d['candidates'][0].update(decision={'actor':'human'}),
                       lambda d:d['candidates'][0]['claims'].update(version='2.0'),
                       lambda d:d['candidates'][0]['observations']['title'].update(value='edited')]:
            edited=copy.deepcopy(c);mutate(edited)
            with self.assertRaisesRegex(IngestImportError,'differs from its manifest'):
                first_pass(raw,encoded(edited))
        with self.assertRaisesRegex(IngestImportError,'invalid candidates JSON'):
            first_pass(raw,b'{')

    def test_unsupported_schema_is_explicit(self):
        m=fixture();m['schema_version']='0.9'
        with self.assertRaisesRegex(IngestImportError,'supports only'):
            first_pass(encoded(m),b'{}')

    def test_reproducible_rules_summary_and_changed_input_identity(self):
        m=fixture();a=analyze(m);self.assertEqual(a,analyze(m))
        self.assertEqual(sum(a['summary']['field_status_counts'].values()),5)
        self.assertEqual(set(a['summary']['field_status_counts']),set(STATUSES))
        self.assertEqual(set(a['summary']['stage_counts']),set(STAGES))
        self.assertEqual(a['summary']['machine_tasks'],len(a['entries'][0]['tasks']))
        m['entries'][0]['normalized']['title']='Changed';b=analyze(m)
        self.assertNotEqual(a['entries'][0]['key'],b['entries'][0]['key'])

    def test_source_markup_is_inert_in_report(self):
        m=fixture();m['entries'][0]['normalized']['title']='<script>bad</script>\n# heading'
        report=render_report(analyze(m))
        self.assertIn('\n    <script>bad</script>\n    # heading\n',report)
        self.assertNotIn('\n# heading\n',report)

    def test_fixture_counts_and_future_states_are_explicit(self):
        d=json.loads((Path(__file__).resolve().parents[1]/'docs/fixtures/automation-queue-v1.json').read_text())
        self.assertTrue(d['fixture'])
        self.assertEqual({r['stage'] for r in d['entries']},set(STAGES))
        self.assertEqual(d['summary']['human_exceptions'],sum(r['requires_human'] for r in d['entries']))
        for status in STATUSES:
            self.assertEqual(d['summary']['field_status_counts'][status],sum(f['status']==status for r in d['entries'] for f in r['fields']))


class FirstPassFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.manifest=self.root/'source.json'
        self.manifest.write_bytes(encoded(fixture()));self.intake=self.root/'intake'
        prepare_intake(self.manifest,self.intake);self.output=self.root/'result'

    def test_repeat_and_parallel_retries_preserve_inputs_and_output(self):
        before=snapshot(self.intake)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b=list(pool.map(lambda _:prepare_first_pass(self.intake,self.output),range(2)))
        self.assertEqual(a,b);old=snapshot(self.output)
        times={p:p.stat().st_mtime_ns for p in self.output.rglob('*')}
        prepare_first_pass(self.intake,self.output)
        self.assertEqual(old,snapshot(self.output));self.assertEqual(before,snapshot(self.intake))
        self.assertEqual(times,{p:p.stat().st_mtime_ns for p in self.output.rglob('*')})

    def test_existing_workspace_or_edited_result_is_never_overwritten(self):
        self.output.mkdir();(self.output/'review-state.json').write_text('{"draft":"human work"}')
        before=snapshot(self.output)
        with self.assertRaisesRegex(IngestImportError,'refusing to replace'):
            prepare_first_pass(self.intake,self.output)
        self.assertEqual(before,snapshot(self.output))
        with self.assertRaisesRegex(IngestImportError,'outside the intake'):
            prepare_first_pass(self.intake,self.intake/'nested')

    def test_symlink_inputs_outputs_and_lock_are_rejected(self):
        (self.intake/'foreign').symlink_to(self.manifest)
        with self.assertRaises(IngestImportError):prepare_first_pass(self.intake,self.output)
        (self.intake/'foreign').unlink();self.output.symlink_to(self.intake,target_is_directory=True)
        with self.assertRaises(IngestImportError):prepare_first_pass(self.intake,self.output)
        self.output.unlink();lock=self.root/'.result.first-pass.lock';lock.symlink_to(self.manifest)
        before=self.manifest.read_bytes()
        with self.assertRaises(OSError):prepare_first_pass(self.intake,self.output)
        self.assertEqual(before,self.manifest.read_bytes())

    def test_failed_publication_leaves_no_partial_result(self):
        with patch('bootdisk_catalog.first_pass.os.rename',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):prepare_first_pass(self.intake,self.output)
        self.assertFalse(self.output.exists());self.assertEqual(list(self.root.glob('.first-pass-*')),[])

    def test_cli_error_is_explicit_and_writes_nothing(self):
        (self.intake/'candidates.json').write_text('{}')
        with self.assertRaises(SystemExit) as error:main([str(self.intake),'--output',str(self.output)])
        self.assertEqual(error.exception.code,2);self.assertFalse(self.output.exists())
