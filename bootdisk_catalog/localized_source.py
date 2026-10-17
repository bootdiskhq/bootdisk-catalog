"""Bind Norwegian title variants to the exact preserved primary DTX document."""
import base64
import configparser
import hashlib


def localized_title(manifest, entry):
    raw = entry.get('raw', {})
    keys = sorted(k for k, v in raw.items() if k.casefold() == 'titelno' and isinstance(v, str) and v.strip())
    if not keys:
        return None
    try:
        if len({raw[k].strip() for k in keys}) != 1:
            return None
        field = keys[0]
        source = manifest['source'];document = source['dtx_file']
        data = base64.b64decode(document['raw_base64'], validate=True)
        parser = configparser.ConfigParser(interpolation=None, strict=False);parser.optionxform = str
        parser.read_string(data.decode('cp1252'))
        section = dict(parser[entry['source_id']])
        path = document.get('resolved_path', document['path'])
        files = [f for f in manifest['file_inventory'] if f['path'] == path]
        if not (len(files) == 1 and document['sha256'] == files[0]['sha256'] == hashlib.sha256(data).hexdigest()
                and document['size'] == files[0]['size'] == len(data)
                and section == source['sections'][entry['source_id']] == raw
                and raw[field].strip() == entry['normalized']['title']):
            return None
        return {'field': 'raw/' + field, 'value': raw[field].strip(), 'original': raw[field]}
    except (KeyError, ValueError, TypeError, UnicodeError, configparser.Error):
        return None
