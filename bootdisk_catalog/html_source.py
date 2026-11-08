"""Validate HTML observations against preserved page and menu-index bytes."""
import base64
import hashlib
from .catalog import CatalogError

def validate_html(manifest, entry):
    if manifest.get('schema_version')!='kcd-html-1':return None
    try:
        from bootdisk_ingest.adapters.kcd.html_menu import index_rows, parse_page, METHOD
        docs=manifest['source']['documents']
        def raw(path):
            doc=docs[path];data=base64.b64decode(doc['raw_base64'],validate=True)
            matches=[f for f in manifest['file_inventory'] if f['path']==path]
            if len(matches)!=1 or doc['path']!=path or doc['encoding']!='cp1252' or doc.get('declared_encoding')!='iso-8859-1' or doc['size']!=len(data) or doc['sha256']!=hashlib.sha256(data).hexdigest() or any(doc[k]!=matches[0][k] for k in ('size','sha256')):raise ValueError('HTML bytes/inventory mismatch')
            return data
        evidence=entry['evidence']['html_menu'];position=evidence['index_position']
        if type(position) is not int or position<0 or evidence['method']!=METHOD:raise ValueError('Invalid HTML selector')
        row=index_rows(raw('scripts/cdindex.js'))[position]
        if evidence['page']!=row['url']:raise ValueError('HTML page/index mismatch')
        observed=parse_page(raw(row['url']),row)
        if observed!=evidence['observation'] or entry['raw']!={'html_title':observed['title'],'html_description':observed['description']}:raise ValueError('HTML observation mismatch')
        if any(entry['normalized'].get(k)!=observed[k] for k in ('title','description','license')) or entry['normalized']['categories']!=[observed['category']]:raise ValueError('HTML normalization mismatch')
        refs=entry['files']['referenced']
        if [r['path'] for r in refs.values()]!=observed['references'] or entry['files']['discovered']['screenshot']['path']!=observed['image']:
            raise ValueError('HTML file references differ from source')
        for record in list(refs.values())+[entry['files']['discovered']['screenshot']]:
            matches=[f for f in manifest['file_inventory'] if f['path']==record.get('resolved_path',record['path'])]
            if record.get('exists'):
                if len(matches)!=1 or any(record.get(k)!=matches[0][k] for k in ('sha256','size')):raise ValueError('HTML asset/inventory mismatch')
            elif matches:raise ValueError('HTML file incorrectly reported missing')
        return observed
    except (ImportError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise CatalogError('Invalid HTML source evidence: '+str(exc)) from exc
