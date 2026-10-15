"""Conservative source-attributed machine interpretations, never human approvals.

The CD's name and prose corroborate its explicit launch association. This rule
identifies what the CD says it links to, not the installed payload or its version.
"""
from __future__ import annotations
import hashlib
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata

from .catalog import SCHEMA
from .curate import _identifications_for_source, _load_manifest
from .presentation import source_context

RULE = 'cd-source-identity-1'
MAX_FILE = 64 * 1024 * 1024


def _fold(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def corroborated_name(title, description):
    if not isinstance(title, str) or not isinstance(description, str):
        return False
    name = _fold(title)
    if len(name) < 4 or not any(c.isalpha() for c in name):
        return False
    if any(ord(c) < 32 for c in title):
        return False
    # Whole-name match: "Paint" must not match "PaintShop".
    return bool(re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', _fold(description)))


def verified_launch(root, observation, inventory):
    """Read only; never execute an installer or accept a cache as verification."""
    if observation.get('exists') is not True:
        return None
    relative = observation.get('resolved_path', observation.get('path'))
    if not isinstance(relative, str) or not relative or '\\' in relative or '\0' in relative:
        return None
    path = PurePosixPath(relative)
    if path.is_absolute() or any(p in ('', '.', '..') for p in relative.split('/')):
        return None
    if path.suffix.casefold() not in ('.exe', '.com'):
        return None
    matches = [f for f in inventory if f.get('path') == relative]
    if len(matches) != 1 or any(matches[0].get(k) != observation.get(k) for k in ('sha256', 'size')):
        return None
    size = observation.get('size')
    if type(size) is not int or not 0 < size <= MAX_FILE:
        return None
    target = Path(root).resolve()
    for part in path.parts:
        target /= part
        if target.is_symlink():
            return None
    try:
        if not stat.S_ISREG(target.stat().st_mode):
            return None
        with target.open('rb') as stream:
            data = stream.read(MAX_FILE + 1)
    except OSError:
        return None
    if len(data) != size or hashlib.sha256(data).hexdigest() != observation.get('sha256'):
        return None
    return dict(path=relative, sha256=observation['sha256'], size=size)


def build_bundle(catalog, manifest_path, source_root, *, eligible_entries, protected_entries=()):
    """Return deterministic records and an audit; inputs are never mutated.

    eligible_entries is an explicit scope, e.g. pending public entries. The caller
    must also supply draft/decision protection keys from its review workspace.
    Existing source interpretations are always preserved, even if not curated.
    Apply the bundle only to a new catalog snapshot using restore_bundle.
    """
    manifest, ref = _load_manifest(Path(manifest_path))
    contexts = source_context(manifest_path)
    entries = manifest['entries']
    if len({e['source_id'] for e in entries}) != len(entries):
        raise ValueError('duplicate source entry')
    scope = set(eligible_entries)
    if scope - {e['source_id'] for e in entries}:
        raise ValueError('unknown eligible entry')
    protected = set(protected_entries)
    records, audit = [], []
    for index, entry in enumerate(entries):
        source_id = entry['source_id']
        if source_id not in scope:
            continue
        key = dict(manifest=ref, entry=source_id)
        row = dict(key=key, actor='machine', rule=RULE, state='inspecting')
        audit.append(row)
        if (ref, source_id) in protected or _identifications_for_source(catalog, ref, source_id):
            row.update(state='preserved', reason='existing_decision_or_draft')
            continue
        if entry.get('issues'):
            row['reason'] = 'source_issues_require_machine_inspection'
            continue
        context = contexts[source_id]
        description = context.get('description')
        title = entry.get('normalized', {}).get('title')
        if not description or not corroborated_name(title, description['value']):
            row['reason'] = 'name_not_corroborated_by_original_description'
            continue
        references = entry.get('files', {}).get('referenced', {})
        if len(references) != 1:
            row['reason'] = 'launch_not_unique'
            continue
        launch = verified_launch(source_root, next(iter(references.values())), manifest['file_inventory'])
        if launch is None:
            row['reason'] = 'launch_bytes_unverified_or_unsupported'
            continue
        artifact = 'artifact:sha256:' + launch['sha256']
        occurrences = catalog.occurrences_for_artifact(artifact)
        if not any(o['source_ref'].get('manifest') == ref and o['source_ref'].get('entry') == source_id
                   and o['source_ref'].get('path') in (launch['path'], next(iter(references.values()))['path']) for o in occurrences):
            row['reason'] = 'catalog_occurrence_missing'
            continue
        token = hashlib.sha256((RULE + '\n' + ref + '\n' + source_id).encode()).hexdigest()
        sid, rid, iid = 'software:auto-' + token, 'release:auto-' + token, 'identification:auto-' + token
        evidence = [dict(kind='interpreted', source_ref=key, field='automatic_source_identity', value=dict(
            actor='machine', rule=RULE, basis='CD title repeated in original description and one verified launch file',
            scope='source-attributed identity; installed payload and version not established',
            title=title, title_pointer=f'/entries/{index}/normalized/title', description=description, launch=launch))]
        records.extend([
            dict(schema=SCHEMA, type='software', id=sid, name=title),
            dict(schema=SCHEMA, type='software_release', id=rid, software_id=sid, version='unknown'),
            dict(schema=SCHEMA, type='identification', id=iid, artifact_id=artifact,
                 software_release_id=rid, status='interpreted', distribution_kind='unknown', evidence=evidence),
        ])
        row.update(state='interpreted', reason='corroborated_cd_source', identification_id=iid, name=title, launch=launch)
    return (dict(schema='bootdisk-catalog-curation-0.1', catalog_schema=SCHEMA,
                 records=sorted(records, key=lambda r: r['id'])),
            dict(schema='bootdisk-automatic-identification-audit-1', actor='machine', rule=RULE,
                 manifest=ref, entries=audit))


def main(argv=None):
    """Create a new, reversible candidate snapshot; never edit the source catalog."""
    import argparse
    import json
    import shutil
    import tempfile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--entries', required=True, type=Path, help='JSON array of eligible source IDs')
    parser.add_argument('--review-state', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    from .catalog import Catalog
    from .curation_bundle import restore_bundle
    output = args.output.resolve()
    for source in (args.catalog.resolve(), args.source.resolve()):
        if output == source or source in output.parents:
            parser.error('output must be outside the input catalog and source media')
    if output.exists():
        parser.error('output already exists; preserve it and choose a new snapshot')
    state_raw = args.review_state.read_bytes()
    state = json.loads(state_raw)
    if state.get('schema') != 'bootdisk-review-workspace-v1':
        parser.error('unsupported review workspace')
    protected = {(e['key']['manifest'], e['key']['entry']) for e in state['entries'].values()}
    eligible = json.loads(args.entries.read_bytes())
    if not isinstance(eligible, list) or any(not isinstance(e, str) for e in eligible):
        parser.error('entries must be a JSON array of strings')
    bundle, audit = build_bundle(Catalog.load(args.catalog), args.manifest, args.source,
                                eligible_entries=eligible, protected_entries=protected)
    audit['review_state_sha256'] = hashlib.sha256(state_raw).hexdigest()
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.auto-identify-') as temp:
        candidate = Path(temp)/'snapshot'
        candidate.mkdir()
        shutil.copytree(args.catalog, candidate/'catalog')
        restore_bundle(candidate/'catalog', bundle)
        for name, document in [('bundle.json', bundle), ('audit.json', audit)]:
            (candidate/name).write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
        if args.review_state.read_bytes() != state_raw:
            raise ValueError('review state changed during preparation; retry on current state')
        candidate.rename(output)
    print(f"Automatic interpretations: {sum(e['state'] == 'interpreted' for e in audit['entries'])}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
