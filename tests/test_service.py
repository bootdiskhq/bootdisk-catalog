import http.client
import json
from pathlib import Path
import threading
import unittest

import test_review
from bootdisk_catalog.service import CuratorServer, STATIC


class ServiceTests(unittest.TestCase):
    def setUp(self):
        test_review.ReviewTests.setUp(self)
        web = self.root / 'web'
        web.mkdir()
        for name in STATIC:
            (web / name).write_text('test static content')
        (web / 'private.json').write_text('never serve')
        report = self.root / 'issues.json'
        report.write_text(json.dumps({'schema':'bootdisk-inspection-issues-v1','entries':[
            {'key':self.key,'issues':[{'code':'read_permission_denied','field':None,'message':'Recorded issue'}]}]}))
        self.server = CuratorServer(self.workspace.root, web, issues_path=report)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, payload=None, headers=None):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        defaults = {'Origin':self.server.origin,'X-Bootdisk-Client':'bootdisk-curator-v1',
                    'X-Bootdisk-Token':self.server.session_token,'Content-Type':'application/json'}
        defaults.update(headers or {})
        client.request(method, path, None if payload is None else json.dumps(payload), defaults)
        response = client.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        client.close()
        return result

    def test_access_boundary_and_closed_static_files(self):
        self.assertEqual(self.request('GET','/api/session')[0],200)
        for path in ['/review-state.json','/private.json','/../private.json','/tests/fixtures/curator-fixtures-v1.json']:
            self.assertEqual(self.request('GET',path)[0],404)
        self.assertEqual(self.request('GET','/api/session',headers={'X-Bootdisk-Client':''})[0],403)
        self.assertEqual(self.request('GET','/api/session',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('GET','/curate.html',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
        for headers in [{'Origin':'https://evil.example'},{'X-Bootdisk-Token':'bad'}]:
            self.assertEqual(self.request('POST','/api/getEntry',{'key':self.key},headers)[0],403)
        self.assertEqual(self.request('OPTIONS','/api/saveDraft')[0],403)
        status,headers,_ = self.request('GET','/curate.html')
        self.assertEqual(status,200)
        self.assertEqual(headers['X-Frame-Options'],'DENY')
        self.assertNotIn('Access-Control-Allow-Origin',headers)

    def test_http_draft_approve_retry_undo_and_restart(self):
        def call(method,payload):
            status,_,body=self.request('POST','/api/'+method,payload)
            self.assertEqual(status,200,body)
            return json.loads(body)
        e=call('getEntry',{'key':self.key})
        self.assertIn('Recorded issue',[i['message'] for i in e['issues']])
        draft=e['draft']; draft['claims']['description']['value']['text']='CPU-Z beskriver prosessoren.'
        draft['claims']['description']['reason']='Omtalen beskriver prosessorinformasjon.'
        saved=call('saveDraft',{'key':self.key,'expected_revision':e['revision'],'operation_id':'save','draft':draft})
        request={'key':self.key,'expected_revision':saved['entry']['revision'],'operation_id':'approve'}
        approved=call('approve',request)
        self.assertEqual(call('approve',request),approved)
        self.assertEqual(approved['entry']['history'][-1]['kind'],'approve')
        undone=call('undo',{'key':self.key,'expected_revision':approved['entry']['revision'],
                            'operation_id':'undo','decision_id':approved['decision_id']})
        self.assertEqual(undone['entry']['accepted'],e['accepted'])
        self.assertEqual(undone['entry']['draft'],draft)
        # New workspace instance is used by a new service; disk state is sufficient.
        with CuratorServer(self.workspace.root,self.server.web_root) as restarted:
            restored=restarted.workspace.call('getEntry',{'key':self.key})
            self.assertEqual(restored['history'][-1]['kind'],'undo')
            self.assertEqual(restored['draft'],draft)
        status,_,body=self.request('POST','/api/saveDraft',{'key':self.key,'expected_revision':e['revision'],'operation_id':'stale','draft':draft})
        self.assertEqual(status,409)
        self.assertEqual(json.loads(body)['code'],'revision_conflict')

    def test_malformed_requests_do_not_write(self):
        before=self.workspace.path.read_bytes()
        self.assertEqual(self.request('POST','/api/approve',[])[0],400)
        self.assertEqual(self.request('POST','/api/getEntry',{})[0],422)
        self.assertEqual(self.request('POST','/api/export',{})[0],404)
        self.assertEqual(self.workspace.path.read_bytes(),before)
