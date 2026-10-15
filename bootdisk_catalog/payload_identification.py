"""Strict identity rule for freshly decoded executable version resources.

Callers must verify the container against its manifest, decode members with a
bounded archive reader and obtain observations from those exact member bytes.
This pure rule never treats installer framework metadata as product evidence.
"""
import re
import unicodedata
from pathlib import PurePosixPath

RULE = 'payload-product-identity-1'

def fold(value):
    return ' '.join(unicodedata.normalize('NFC', value).casefold().split())

def contains(text, name):
    return bool(re.search(r'(?<!\w)' + re.escape(fold(name)) + r'(?!\w)', fold(text)))

def qualify(title, members):
    """Return one nonconflicting product interpretation, or a machine-work reason."""
    candidates = []
    for member in members:
        if member.get('status') != 'read' or member.get('inspection', {}).get('status') != 'observed':
            continue
        filename = PurePosixPath(member['name']).name.casefold()
        if not filename.endswith(('.exe', '.___')) or any(x in filename for x in ('setup', 'install', 'uninst')):
            continue
        observations = member['inspection']['observations']
        fields = {field: [o for o in observations if o['field'].endswith('/' + field)]
                  for field in ('ProductName', 'ProductVersion', 'FileDescription')}
        if any(not values for values in fields.values()):
            continue
        if any(o.get('warning') or '\0' in o['value'] for values in fields.values() for o in values):
            continue
        values = {field: {o['value'].strip() for o in obs} for field, obs in fields.items()}
        if any(len(v) != 1 for v in values.values()):
            # A matching member with contradictory language resources is not usable.
            if any(contains(n, title) for n in values['ProductName']):
                return None, 'conflicting_member_resources'
            continue
        product, version, description = (next(iter(values[f])) for f in fields)
        name = title.strip()
        if version and name.endswith(' ' + version):
            name = name[:-len(version)-1]
        if len(name) < 4 or not any(c.isalpha() for c in name):
            continue
        if not contains(product, name) or not contains(description, name):
            continue
        if any(x in fold(product) for x in ('installshield', 'operating system', 'setup for', 'visual basic', 'self-extractor')):
            continue
        # Numeric product versions only; never use FileVersion or framework versions.
        if not re.fullmatch(r'\d+(?:[.,]\s*\d+){1,3}', version) or not any(c in '123456789' for c in version):
            return None, 'product_version_requires_inspection'
        normalized_version = re.sub(r',\s*', '.', version)
        candidates.append(dict(name=name, product_name=product, version=normalized_version,
                               member=member['name'], member_sha256=member['sha256'],
                               member_size=member['size'], observations=[o for values in fields.values() for o in values]))
    if not candidates:
        return None, 'no_matching_product_member'
    identities = {(fold(c['name']), fold(c['product_name']), c['version']) for c in candidates}
    if len(identities) != 1:
        return None, 'conflicting_product_members'
    return dict(name=candidates[0]['name'], version=candidates[0]['version'], evidence=candidates), 'qualified_product_metadata'
