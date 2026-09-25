"""Project supplementary RTF observations without changing decisions or evidence."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from .catalog import CatalogError


def project(manifest_path, observations_path):
    raw = Path(manifest_path).read_bytes(); manifest = json.loads(raw)
    ref = 'sha256:' + hashlib.sha256(raw).hexdigest()
    observation_bytes = Path(observations_path).read_bytes(); observations = json.loads(observation_bytes)
    observation_ref = 'sha256:' + hashlib.sha256(observation_bytes).hexdigest()
    if observations.get('schema') != 'bootdisk-rtf-observations-1' or observations.get('manifest') != ref:
        raise CatalogError('RTF observations belong to another manifest')
    entries = {e['source_id']: (i, e) for i, e in enumerate(manifest['entries'])}
    result, seen = [], set()
    for doc in observations['documents']:
        key = doc['key']; entry_id = key.get('entry')
        if key.get('manifest') != ref or entry_id not in entries or entry_id in seen:
            raise CatalogError('invalid or duplicate RTF source binding')
        seen.add(entry_id)
        position, entry = entries[entry_id]
        file = entry.get('files', {}).get('discovered', {}).get('description_rtf', {})
        inventory = [f for f in manifest.get('file_inventory', []) if f.get('path') == doc.get('path')]
        try: data = base64.b64decode(doc['raw_base64'], validate=True)
        except (ValueError, TypeError) as exc: raise CatalogError('invalid RTF bytes') from exc
        if not (file.get('exists') and len(inventory) == 1 and len(data) <= 1024 * 1024
                and doc['pointer'] == f'/entries/{position}/files/discovered/description_rtf'
                and doc['path'] == file.get('resolved_path', file.get('path'))
                and doc.get('method') == 'rtf-ansi-text-terminal-nul-1'
                and all(doc.get(k) == file.get(k) == inventory[0].get(k) for k in ('sha256', 'size'))
                and hashlib.sha256(data).hexdigest() == doc['sha256'] and len(data) == doc['size']
                and (doc.get('text') is None or isinstance(doc['text'], str))):
            raise CatalogError('RTF observation differs from preserved source')
        result.append({**doc, 'observation_manifest': observation_ref})
    return {'schema': 'bootdisk-source-documents-1', 'manifest': ref, 'documents': result,
            'issues': observations.get('issues', [])}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('observations');a=p.parse_args()
    print(json.dumps(project(a.manifest,a.observations),ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
