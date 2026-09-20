"""Loopback-only transport for the v1 curator adapter; no arbitrary file serving."""
from __future__ import annotations

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from .review import ReviewWorkspace, ReviewError, SCHEMA, key_id

STATIC = {
    'curate.html', 'curate.js', 'curate.css', 'curate-core.js', 'curate-adapter.js',
    'curate-live-adapter.js', 'styles.css', 'accessibility.css',
}
METHODS = {'getQueue', 'getEntry', 'saveDraft', 'defer', 'approve', 'undo', 'setResume'}
MAX_BODY = 2 * 1024 * 1024


class CuratorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, workspace, web_root, port=0, issues_path=None):
        self.workspace = ReviewWorkspace(workspace)
        state = self.workspace.read()
        manifests = {e['key']['manifest'] for e in state['entries'].values()}
        if len(manifests) != 1:
            raise ValueError('Choose a workspace containing exactly one manifest')
        self.manifest = manifests.pop()
        self.web_root = Path(web_root).resolve()
        for name in STATIC:
            path = self.web_root / name
            if not path.is_file() or path.is_symlink():
                raise ValueError(f'Missing or unsafe curator frontend file: {name}')
        self.issues = {}
        if issues_path:
            report = json.loads(Path(issues_path).read_text(encoding='utf-8'))
            if report.get('schema') != 'bootdisk-inspection-issues-v1':
                raise ValueError('Unknown inspection issue report schema')
            for item in report['entries']:
                identity = key_id(item['key'])
                if identity not in state['entries']:
                    raise ValueError('Inspection issue does not belong to this workspace')
                for issue in item['issues']:
                    if not isinstance(issue.get('message'), str) or not isinstance(issue.get('code'), str) or issue.get('field') is not None:
                        raise ValueError('Invalid source inspection issue')
                self.issues[identity] = item['issues']
        self.session_token = secrets.token_hex(32)
        super().__init__(('127.0.0.1', port), Handler)
        self.authority = f'127.0.0.1:{self.server_port}'
        self.origin = 'http://' + self.authority

    def augment(self, document):
        # Transport-only immutable inspection observations never change decisions.
        identity = key_id(document['key'])
        document['issues'].extend(json.loads(json.dumps(self.issues.get(identity, []))))
        return document


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_args):
        pass  # Do not put source claims, tokens or request bodies in access logs.

    def reply(self, status, body, content_type='application/json; charset=utf-8'):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def error(self, status, code, message):
        self.close_connection = True
        self.reply(status, dict(code=code, message=message, retryable=code in ('service_unavailable', 'write_failed'), field_errors={}, current_entry=None))

    def local_request(self):
        if self.headers.get('Host') != self.server.authority:
            self.error(403, 'service_unavailable', 'Ugyldig lokal vertsadresse.')
            return False
        if self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin'):
            self.error(403, 'service_unavailable', 'Forespørselen må komme fra kurateringssiden.')
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        path = urlsplit(self.path).path
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/curate.html?mode=local')
            self.end_headers()
            return
        if path == '/api/session':
            if self.headers.get('X-Bootdisk-Client') != SCHEMA:
                self.error(403, 'service_unavailable', 'Kurateringsklienten må identifisere seg.')
                return
            self.reply(200, dict(schema=SCHEMA, manifest=self.server.manifest, token=self.server.session_token))
            return
        name = path.removeprefix('/')
        if name not in STATIC:
            self.error(404, 'not_found', 'Siden finnes ikke i den lokale tjenesten.')
            return
        target = self.server.web_root / name
        if target.is_symlink() or target.resolve().parent != self.server.web_root:
            self.error(404, 'not_found', 'Filen kan ikke leses.')
            return
        content_type = {'html': 'text/html', 'js': 'text/javascript', 'css': 'text/css'}[target.suffix[1:]]
        try:
            body = target.read_bytes()
        except OSError:
            self.error(404, 'not_found', 'Filen kan ikke leses.')
            return
        self.reply(200, body, content_type + '; charset=utf-8')

    def do_POST(self):
        if not self.local_request():
            return
        if (self.headers.get('Origin') != self.server.origin
                or self.headers.get('X-Bootdisk-Client') != SCHEMA
                or not hmac.compare_digest(self.headers.get('X-Bootdisk-Token', ''), self.server.session_token)):
            self.error(403, 'service_unavailable', 'Ugyldig eller utløpt lokal økt. Last siden på nytt.')
            return
        method = urlsplit(self.path).path.removeprefix('/api/')
        if self.path != '/api/' + method or method not in METHODS:
            self.error(404, 'not_found', 'Ukjent kurateringshandling.')
            return
        if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
            self.error(400, 'validation_failed', 'Forespørselen må være JSON med kjent størrelse.')
            return
        try:
            length = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            self.error(413, 'validation_failed', 'Forespørselen er tom eller for stor.')
            return
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError('Incomplete request')
            request = json.loads(body)
            if not isinstance(request, dict):
                raise ValueError('Request must be an object')
        except (ValueError, UnicodeError, OSError):
            self.error(400, 'validation_failed', 'Ugyldig JSON-forespørsel.')
            return
        try:
            result = self.server.workspace.call(method, request)
            if method == 'getEntry':
                result = self.server.augment(result)
            elif method in ('saveDraft', 'defer', 'approve', 'undo'):
                result['entry'] = self.server.augment(result['entry'])
        except ReviewError as exc:
            if exc.payload.get('current_entry'):
                self.server.augment(exc.payload['current_entry'])
            self.reply(409 if 'conflict' in exc.payload['code'] else 422, exc.payload)
            return
        except (KeyError, TypeError, ValueError):
            self.error(400, 'validation_failed', 'Ugyldige felt i forespørselen.')
            return
        except Exception:
            logging.exception('Curator workspace operation failed')
            self.error(503, 'service_unavailable', 'Arbeidsområdet kunne ikke leses eller lagres.')
            return
        self.reply(200, result)

    def do_OPTIONS(self):
        self.error(403, 'service_unavailable', 'Tilgang fra andre nettsider er ikke tillatt.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Serve the local Bootdisk curator')
    parser.add_argument('workspace')
    parser.add_argument('--web-root', required=True)
    parser.add_argument('--port', type=int, default=8772)
    parser.add_argument('--issues', help='Optional hash-bound source inspection issue report')
    args = parser.parse_args(argv)
    with CuratorServer(args.workspace, args.web_root, args.port, args.issues) as server:
        print(f'Kuratering: {server.origin}/curate.html?mode=local', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
