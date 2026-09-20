"""Transactional local review workspace; no HTTP server or browser state.

One atomic snapshot contains the graph, drafts, events and retry receipts. The
original imported catalog remains untouched. Export is an explicit projection.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from .catalog import Catalog, LoadedRecord, REQUIRED_FIELDS, CONTENT_KINDS, IDENTIFICATION_DISTRIBUTION_KINDS
from .identify import apply_review_claims

SCHEMA = 'bootdisk-curator-v1'
WORKSPACE_SCHEMA = 'bootdisk-review-workspace-v1'
FIELDS = {'identity', 'version', 'content_kind', 'distribution_kind', 'description'}


class ReviewError(Exception):
    def __init__(self, code, message, *, fields=None, current=None):
        super().__init__(message)
        self.payload = dict(code=code, message=message, retryable=code == 'write_failed',
                            field_errors=fields or {}, current_entry=current)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def graph(records):
    return Catalog(LoadedRecord(r, Path('<review>')) for r in records)


def token():
    return uuid.uuid4().hex


def key_id(key):
    if (not isinstance(key, dict) or set(key) != {'manifest', 'entry'}
            or not isinstance(key['manifest'], str)
            or not re.fullmatch(r'sha256:[0-9a-f]{64}', key['manifest'])
            or not isinstance(key['entry'], str) or not re.fullmatch(r'K[0-9]+', key['entry'])):
        raise ReviewError('validation_failed', 'Ugyldig kildepost.')
    return key['manifest'] + '/' + key['entry']


def validate_claims(draft, entry, *, approving=False):
    errors = {}
    if not isinstance(draft, dict) or set(draft) != {'claims'} or not isinstance(draft['claims'], dict) or set(draft['claims']) != FIELDS:
        raise ReviewError('validation_failed', 'Alle fem tolkningsfelt må være med.')
    evidence = {e['id']: e for e in entry['evidence']}
    for field, claim in draft['claims'].items():
        if not isinstance(claim, dict) or set(claim) != {'value', 'assessment', 'evidence_ids', 'reason'}:
            errors[field] = 'Ugyldig feltstruktur.'
            continue
        value = claim['value']
        valid = isinstance(value, str) and (bool(value.strip()) or not approving)
        if field == 'identity':
            valid = (isinstance(value, dict) and set(value) == {'software_id', 'name'}
                     and isinstance(value['name'], str) and (bool(value['name'].strip()) or not approving)
                     and (value['software_id'] is None or isinstance(value['software_id'], str)))
        elif field == 'description':
            valid = (isinstance(value, dict) and set(value) == {'language', 'text'}
                     and value['language'] == 'nb-NO' and isinstance(value['text'], str) and (bool(value['text'].strip()) or not approving))
        elif field == 'content_kind':
            valid = isinstance(value, str) and value in CONTENT_KINDS
        elif field == 'distribution_kind':
            valid = isinstance(value, str) and value in IDENTIFICATION_DISTRIBUTION_KINDS
        if not valid or claim['assessment'] not in ('accepted', 'unresolved') or not isinstance(claim['reason'], str):
            errors[field] = 'Ugyldig verdi eller vurdering.'
            continue
        refs = claim['evidence_ids']
        if not isinstance(refs, list) or any(not isinstance(i, str) or i not in evidence for i in refs):
            errors[field] = 'Kildebelegget finnes ikke på denne posten.'
            continue
        for ref in refs:
            if any(evidence[ref]['source_ref'].get(k) != v for k, v in entry['key'].items()):
                errors[field] = 'Kildebelegget tilhører en annen kildepost.'
        # Drafts allow incomplete typing; acceptance is deliberately stricter.
        if approving:
            if claim['assessment'] == 'unresolved' and not claim['reason'].strip():
                errors[field] = 'Forklar hva som fortsatt er uavklart.'
            if claim['assessment'] == 'accepted' and not refs:
                errors[field] = 'En godkjent påstand trenger kildebelegg.'
            if field in ('version', 'distribution_kind') and value == 'unknown' and claim['assessment'] != 'unresolved':
                errors[field] = 'Ukjent skal beholdes som uavklart.'
            prior = (entry['accepted'] or {}).get('claims', {}).get(field)
            if claim['assessment'] == 'accepted' and (not prior or prior['value'] != value or prior['assessment'] != 'accepted') and not claim['reason'].strip():
                errors[field] = 'Begrunn den nye påstanden med valgt kildebelegg.'
    if approving and not errors:
        for field in classification_review_fields(dict(entry, draft=draft)):
            errors[field] = 'Velg kildebelegg og forklar hvordan det støtter vurderingen. Lisens alene fastslår ikke distribusjonsutgaven.'
    if errors:
        raise ReviewError('validation_failed', 'Kontroller feltene før lagring.', fields=errors)


def classification_review_fields(entry):
    if not entry.get('classification_evidence_v1'):
        return []
    return [field for field in ('content_kind', 'distribution_kind')
            if entry['draft']['claims'][field]['assessment'] == 'accepted'
            and (not entry['draft']['claims'][field]['reason'].strip()
                 or not entry['draft']['claims'][field]['evidence_ids'])]


def add_source_evidence(entry, source):
    """Add immutable observations, never infer an edition or alter a user's claim."""
    observations = [
        ('normalized.categories', category) for category in source['normalized'].get('categories', [])
    ]
    license_value = source.get('raw', {}).get('Licens') or source['normalized'].get('license')
    if license_value:
        observations.append(('raw.Licens', license_value))
    description = source['normalized'].get('description')
    if description:
        observations.append(('normalized.description', description))
    for field, value in observations:
        item = dict(source_ref=deepcopy(entry['key']), field=field, observation=value)
        item['id'] = 'e:' + hashlib.sha256(canonical(item).encode()).hexdigest()
        if item not in entry['evidence']:
            entry['evidence'].append(item)
    entry['classification_evidence_v1'] = True


def refresh_issues(entry):
    issues = [i for i in entry['issues'] if i['field'] is None]
    for field in classification_review_fields(entry):
        issues.append(dict(code='classification_review_required', field=field,
                           message='Tidligere Belagt-vurdering må kontrolleres: velg relevant kildebelegg og begrunn sammenhengen.'))
    codes = {'identity': 'identity_provisional', 'version': 'version_unknown', 'distribution_kind': 'distribution_unknown'}
    for field, claim in entry['draft']['claims'].items():
        if claim['assessment'] == 'unresolved':
            issues.append(dict(code=codes.get(field, 'claim_unresolved'), field=field, message=claim['reason']))
    entry['issues'] = issues


class ReviewWorkspace:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / 'review-state.json'

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / '.review.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def read(self):
        state = json.loads(self.path.read_text(encoding='utf-8'))
        if state.get('schema') != WORKSPACE_SCHEMA:
            raise ReviewError('validation_failed', 'Ukjent arbeidsområdeformat.')
        graph(state['records'])
        return state

    def write(self, state):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root, delete=False) as f:
                temporary = Path(f.name)
                f.write(canonical(state) + '\n')
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError as exc:
            raise ReviewError('write_failed', 'Lagring kunne ikke bekreftes. Prøv samme operasjon igjen.') from exc
        finally:
            if temporary and temporary.exists():
                temporary.unlink()

    def initialize(self, catalog_root, manifest_path):
        """Seed a new isolated workspace from an imported, already identified disc."""
        catalog_root = Path(catalog_root).resolve()
        if self.root.resolve() == catalog_root or catalog_root in self.root.resolve().parents:
            raise ReviewError('validation_failed', 'Arbeidsområdet må ligge utenfor katalogen.')
        raw = Path(manifest_path).read_bytes()
        manifest = json.loads(raw)
        digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
        catalog = Catalog.load(catalog_root)
        records = [deepcopy(r) for kind in REQUIRED_FIELDS for r in catalog.records_of_type(kind)]
        inventory = {f['path']: f for f in manifest['file_inventory']}
        entries = {}
        for source in manifest['entries']:
            key = dict(manifest=digest, entry=source['source_id'])
            candidates = [r for r in catalog.records_of_type('identification') if any(
                all(e['source_ref'].get(k) == v for k, v in key.items()) for e in r['evidence'])]
            if len(candidates) != 1:
                raise ReviewError('validation_failed', 'Første versjon krever én tolkning per kildepost.')
            ident = candidates[0]
            release = catalog.record(ident['software_release_id'])
            software = catalog.record(release['software_id'])
            descriptions = [r for r in catalog.records_of_type('description') if r['subject_id'] == release['id'] and r['language'] == 'nb-NO']
            if len(descriptions) != 1:
                raise ReviewError('validation_failed', 'Kildeposten trenger én norsk beskrivelse.')
            desc = descriptions[0]
            target_field = 'package_id' if 'package_id' in ident else 'artifact_id'
            target = dict(kind='package' if target_field == 'package_id' else 'artifact', id=ident[target_field])
            if target['kind'] == 'package' and target['id'] != 'package:sha256:' + source['content_identity']['manifest_sha256']:
                raise ReviewError('validation_failed', 'Pakken samsvarer ikke med manifestet.')
            if target['kind'] == 'artifact' and not any(r['artifact_id'] == target['id'] and all(r['source_ref'].get(k) == v for k, v in key.items()) for r in catalog.records_of_type('occurrence')):
                raise ReviewError('validation_failed', 'Filen mangler kildeobservasjon.')
            evidence = []
            for e in ident['evidence'] + desc['evidence']:
                if not all(e['source_ref'].get(k) == v for k, v in key.items()):
                    continue
                item = dict(source_ref=e['source_ref'], field=e['field'], observation=e['value'])
                item['id'] = 'e:' + hashlib.sha256(canonical(item).encode()).hexdigest()
                if item not in evidence:
                    evidence.append(item)
            refs = [e['id'] for e in evidence]
            def claim(value, known=True):
                return dict(value=value, assessment='accepted' if known else 'unresolved', evidence_ids=refs,
                            reason='' if known else 'Ikke fastslått av tilgjengelig kildebelegg.')
            claims = dict(identity=claim(dict(software_id=software['id'], name=software['name']), ident['status'] == 'curated'),
                          version=claim(release['version'], release['version'] != 'unknown'),
                          content_kind=claim(software.get('content_kind', 'application'), 'content_kind' in software),
                          distribution_kind=claim(ident.get('distribution_kind', 'unknown'), ident.get('distribution_kind', 'unknown') != 'unknown'),
                          description=claim(dict(language='nb-NO', text=desc['text']), desc['status'] == 'curated'))
            entry = dict(schema=SCHEMA, key=key, revision=token(), queue_state='pending',
                         source=dict(title=source['normalized']['title'], description=source['normalized']['description'], target=target,
                                     members=[inventory[p] for p in source['files']['inventory_refs']]),
                         accepted=dict(identification_status=ident['status'], claims=deepcopy(claims)),
                         draft=dict(claims=claims), proposals=[], evidence=evidence, issues=[], undo=None, defer_reason=None)
            add_source_evidence(entry, source)
            refresh_issues(entry)
            entries[key_id(key)] = entry
        with self.locked():
            if self.path.exists():
                raise ReviewError('validation_failed', 'Arbeidsområdet finnes allerede.')
            self.write(dict(schema=WORKSPACE_SCHEMA, records=records, entries=entries, events=[], operations={}, resume={}))
        return len(entries)

    def enrich_sources(self, manifest_path):
        """Idempotent, locked migration with an exact pre-migration backup.

        Revisions invalidate stale browser writes. Drafts, accepted claims, records,
        decisions, receipts and resume position are not rewritten.
        """
        raw = Path(manifest_path).read_bytes()
        digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
        sources = {s['source_id']: s for s in json.loads(raw)['entries']}
        with self.locked():
            state = self.read()
            if any(e['key']['manifest'] != digest or e['key']['entry'] not in sources
                   for e in state['entries'].values()):
                raise ReviewError('validation_failed', 'Manifestet tilhører ikke dette arbeidsområdet.')
            changed = 0
            for entry in state['entries'].values():
                if entry.get('classification_evidence_v1'):
                    continue
                add_source_evidence(entry, sources[entry['key']['entry']])
                refresh_issues(entry)
                entry['revision'] = token()
                changed += 1
            if changed:
                backup = self.root / ('before-source-evidence-' + token() + '.json')
                with backup.open('xb') as f:
                    f.write(self.path.read_bytes())
                    f.flush()
                    os.fsync(f.fileno())
                self.write(state)
            return dict(updated=changed)

    @staticmethod
    def document(state, entry):
        result = deepcopy(entry)
        result['defer_reason'] = entry.get('defer_reason')
        result['history'] = [dict(kind=e['method'], decision_id=e['id'], at=e['timestamp'],
                                  reason=e.get('reason'), actor=e['actor'],
                                  previous_claims=(e['before'].get('accepted') or {}).get('claims'),
                                  new_claims=(e['after'].get('accepted') or {}).get('claims'))
                             for e in state['events'] if e['key'] == entry['key']
                             and e['method'] in ('approve', 'defer', 'undo')]
        return result

    def call(self, method, request, *, actor='local-curator'):
        with self.locked():
            state = self.read()
            if method == 'getQueue':
                mode = request.get('filter', 'pending')
                if mode not in ('pending', 'deferred', 'open_fields', 'all'):
                    raise ReviewError('validation_failed', 'Ukjent køfilter.')
                items = []
                for e in state['entries'].values():
                    if e['key']['manifest'] != request['manifest']:
                        continue
                    fields = [f for f, c in e['draft']['claims'].items() if c['assessment'] == 'unresolved']
                    fields.extend(f for f in classification_review_fields(e) if f not in fields)
                    if mode not in ('all', 'open_fields') and e['queue_state'] != mode or mode == 'open_fields' and not fields:
                        continue
                    items.append(dict(key=e['key'], title=e['source']['title'], queue_state=e['queue_state'],
                                      identification_status=e['accepted']['identification_status'], open_fields=fields))
                items.sort(key=lambda i: int(i['key']['entry'][1:]))
                return dict(schema=SCHEMA, items=items, resume_key=state['resume'].get(request['manifest']))
            entry_id = key_id(request.get('key'))
            if entry_id not in state['entries']:
                raise ReviewError('validation_failed', 'Ukjent kildepost.')
            entry = state['entries'][entry_id]
            if method == 'getEntry':
                return self.document(state, entry)
            if method == 'setResume':
                state['resume'][entry['key']['manifest']] = entry['key']
                self.write(state)
                return dict(schema=SCHEMA, resume_key=entry['key'])
            if method not in ('saveDraft', 'defer', 'approve', 'undo'):
                raise ReviewError('validation_failed', 'Ukjent handling.')
            op = request.get('operation_id')
            if not isinstance(op, str) or not op.strip() or len(op) > 200:
                raise ReviewError('validation_failed', 'Operasjons-ID mangler.')
            fingerprint = canonical(dict(method=method, request=request, actor=actor))
            previous = state['operations'].get(op)
            if previous:
                if previous['request'] != fingerprint:
                    raise ReviewError('operation_id_reused', 'Operasjons-ID er allerede brukt med annet innhold.')
                return deepcopy(previous['receipt'])
            if request.get('expected_revision') != entry['revision']:
                raise ReviewError('revision_conflict', 'Posten er endret siden du åpnet den.', current=self.document(state, entry))
            before = deepcopy(entry)
            records_before = deepcopy(state['records'])
            decision_id = None
            if method == 'saveDraft':
                validate_claims(request.get('draft'), entry)
                entry['draft'] = deepcopy(request['draft'])
                refresh_issues(entry)
            elif method == 'defer':
                reason = request.get('reason')
                if not isinstance(reason, str) or not reason.strip():
                    raise ReviewError('validation_failed', 'Oppgi hvorfor posten utsettes.')
                entry['queue_state'] = 'deferred'
                entry['defer_reason'] = reason
            elif method == 'approve':
                validate_claims(entry['draft'], entry, approving=True)
                try:
                    state['records'], claims = apply_review_claims(state['records'], entry)
                except ValueError as exc:
                    raise ReviewError('shared_record_conflict', str(exc)) from exc
                graph(state['records'])
                entry['accepted'] = dict(identification_status='curated' if claims['identity']['assessment'] == 'accepted' else 'interpreted', claims=claims)
                entry['draft'] = dict(claims=deepcopy(claims))
                entry['queue_state'] = 'reviewed'
                entry['defer_reason'] = None
                decision_id = token()
                entry['undo'] = dict(decision_id=decision_id, label='Angre siste godkjenning')
            else:
                undo = entry['undo']
                if not undo or request.get('decision_id') != undo['decision_id']:
                    raise ReviewError('undo_conflict', 'Denne beslutningen kan ikke angres nå.')
                event = next(e for e in state['events'] if e['id'] == undo['decision_id'])
                # Conservative: another semantic decision needs a fresh dependency review.
                if state['records'] != event['records_after']:
                    raise ReviewError('undo_conflict', 'Katalogen er endret etter beslutningen.')
                state['records'] = deepcopy(event['records_before'])
                entry['accepted'] = deepcopy(event['before']['accepted'])
                entry['undo'] = None
                entry['queue_state'] = 'pending'
                decision_id = token()
            entry['revision'] = token()
            refresh_issues(entry)
            # Events include draft/defer reasons too; undo points only to decisions.
            state['events'].append(dict(id=decision_id or token(), method=method, key=entry['key'], actor=actor,
                                        timestamp=datetime.now(timezone.utc).isoformat(), reason=request.get('reason'),
                                        before=before, after=deepcopy(entry),
                                        records_before=records_before if decision_id else None,
                                        records_after=deepcopy(state['records']) if decision_id else None))
            receipt = dict(schema=SCHEMA, operation_id=op, entry=self.document(state, entry), decision_id=decision_id)
            state['operations'][op] = dict(request=fingerprint, receipt=receipt)
            self.write(state)
            return receipt

    def export_catalog(self, destination):
        """Export only approved graph records to a new directory, atomically."""
        destination = Path(destination)
        with self.locked():
            records = self.read()['records']
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise ReviewError('validation_failed', 'Eksportmålet finnes allerede.')
            with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
                stage = Path(temporary) / 'catalog'
                stage.mkdir()
                for r in records:
                    name = hashlib.sha256(r['id'].encode()).hexdigest() + '.json'
                    (stage / name).write_text(canonical(r) + '\n', encoding='utf-8')
                Catalog.load(stage)
                os.rename(stage, destination)
        return len(records)

    def backup(self, destination):
        with self.locked():
            state = self.read()
            with Path(destination).open('x', encoding='utf-8') as f:
                f.write(canonical(state) + '\n')
                f.flush()
                os.fsync(f.fileno())

    def restore(self, source):
        state = json.loads(Path(source).read_text(encoding='utf-8'))
        if state.get('schema') != WORKSPACE_SCHEMA:
            raise ReviewError('validation_failed', 'Ukjent sikkerhetskopiformat.')
        graph(state['records'])
        for identity, e in state['entries'].items():
            if identity != key_id(e['key']):
                raise ReviewError('validation_failed', 'Ugyldig kildepost i sikkerhetskopi.')
            validate_claims(e['draft'], e)
        with self.locked():
            if self.path.exists():
                raise ReviewError('validation_failed', 'Gjenoppretting krever nytt arbeidsområde.')
            self.write(state)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local review workspace (development)')
    parser.add_argument('workspace', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('catalog'); init.add_argument('manifest')
    sub.add_parser('enrich-sources').add_argument('manifest')
    call = sub.add_parser('call'); call.add_argument('method'); call.add_argument('request', type=Path)
    for name in ('export', 'backup', 'restore'):
        sub.add_parser(name).add_argument('path', type=Path)
    args = parser.parse_args(argv)
    workspace = ReviewWorkspace(args.workspace)
    try:
        if args.command == 'init': result = workspace.initialize(args.catalog, args.manifest)
        elif args.command == 'enrich-sources': result = workspace.enrich_sources(args.manifest)
        elif args.command == 'call': result = workspace.call(args.method, json.loads(args.request.read_text()))
        elif args.command == 'export': result = workspace.export_catalog(args.path)
        elif args.command == 'backup': result = workspace.backup(args.path)
        else: result = workspace.restore(args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ReviewError as exc:
        print(json.dumps(exc.payload, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
