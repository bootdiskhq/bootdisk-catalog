"""Validate a calendar title against preserved J.DTX and its inventory hash."""
import base64
import configparser
import hashlib
from .catalog import CatalogError


def validate_calendar(manifest, entry):
    claim = entry.get('evidence', {}).get('calendar_metadata')
    if claim is None:
        return False
    try:
        matches = [s for s in manifest['source']['supplemental_metadata']
                   if s.get('resolved_path', s.get('path')) == claim['path']]
        if len(matches) != 1:raise ValueError('ambiguous calendar source')
        source = matches[0]
        raw = base64.b64decode(source['raw_base64'], validate=True)
        parser = configparser.ConfigParser(interpolation=None);parser.optionxform=str
        parser.read_string(raw.decode('cp1252'))
        fields = dict(parser[entry['source_id']])
        files = [f for f in manifest['file_inventory'] if f['path'] == claim['path']]
        if not (len(files) == 1 and not parser.defaults() and source['encoding'] == 'cp1252'
                and source['size'] == len(raw) == files[0]['size']
                and source['sha256'] == claim['sha256'] == files[0]['sha256'] == hashlib.sha256(raw).hexdigest()
                and claim['section'] == entry['source_id'] and claim['title_field'] == 'Titel'
                and source['sections'][entry['source_id']] == fields == entry['raw']
                and fields['Titel'].strip() == entry['normalized']['title']):
            raise ValueError('calendar binding mismatch')
    except (ValueError, KeyError, TypeError, UnicodeError, configparser.Error) as exc:
        raise CatalogError('Calendar source does not match preserved metadata') from exc
    return True
