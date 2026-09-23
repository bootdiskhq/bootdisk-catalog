"""Import embedded image byte occurrences; no software identities or approvals."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from .catalog import Catalog, SCHEMA
from .import_ingest import _records_for_observation


def require(condition,message):
    if not condition:raise ValueError(message)


def import_images(images_path,manifest_path,catalog_root,output):
    images_path=Path(images_path);raw=images_path.read_bytes();report=json.loads(raw)
    manifest_raw=Path(manifest_path).read_bytes();manifest=json.loads(manifest_raw)
    digest=hashlib.sha256(manifest_raw).hexdigest();report_digest=hashlib.sha256(raw).hexdigest()
    require(report.get('schema')=='bootdisk-embedded-images-1' and report.get('manifest')=='sha256:'+digest,'image manifest mismatch')
    inventory={f['path']:f for f in manifest['file_inventory']};entries={e['source_id'] for e in manifest['entries']}
    Catalog.load(Path(catalog_root))
    records={}
    for path in Path(catalog_root).rglob('*.json'):
        r=json.loads(path.read_text());records[r['id']]=r
    seen=set()
    for item in report['assets']:
        entry,kind=item['entry_source_id'],item['kind']
        require(entry in entries and kind in ('icon','screenshot') and (entry,kind) not in seen,'unknown/duplicate image entry')
        seen.add((entry,kind))
        require(item.get('source_ref')=={'manifest':'sha256:'+digest,'entry':entry},'image source reference mismatch')
        for part,tag in (('pixels','BITD'),('palette','CLUT'),('metadata','CASt')):
            resource=item[part];parent=resource['container'];source=inventory.get(parent['path'])
            require(source is not None and all(source[k]==parent[k] for k in ('size','sha256')),'image container mismatch')
            sha=resource['sha256'];size=resource['size'];offset=resource['offset']
            require(isinstance(sha,str) and re.fullmatch('[0-9a-f]{64}',sha) and type(size) is int and size>=0,'invalid image identity')
            require(type(offset) is int and offset>=0 and offset+size<=parent['size'] and resource.get('tag')==tag,'invalid image range/type')
            require(resource.get('object_path')=='resources/'+sha,'invalid image object path')
            path=(images_path.parent/resource['object_path']).resolve()
            require(path.is_relative_to(images_path.parent.resolve()) and path.is_file() and path.stat().st_size==size,'missing image bytes')
            require(hashlib.sha256(path.read_bytes()).hexdigest()==sha,'image bytes changed')
            observed_path=parent['path']+'#'+tag+':'+str(resource['resource_id'])
            artifact,occurrence=_records_for_observation(report_digest,entry,'embedded-'+kind+'-'+part,{'sha256':sha,'size':size,'path':observed_path})
            occurrence['source_ref'].update({'manifest':'sha256:'+digest,'image_manifest':'sha256:'+report_digest,
                'container_sha256':parent['sha256'],'offset':offset,'size':size,'resource_id':resource['resource_id']})
            for record in (artifact,occurrence):
                require(record['id'] not in records or records[record['id']]==record,'conflicting catalog record')
                records[record['id']]=record
    output=Path(output).absolute();require(not output.exists() and not output.is_symlink(),'output must be new')
    require(not output.resolve().is_relative_to(Path(catalog_root).resolve()), 'output must be outside existing catalog')
    output.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.image-catalog-',dir=output.parent))
    try:
        for key,record in records.items():
            (stage/(hashlib.sha256(key.encode()).hexdigest()+'.json')).write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        Catalog.load(stage);os.rename(stage,output)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return len(seen)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('images');p.add_argument('manifest');p.add_argument('catalog');p.add_argument('--output',required=True)
    a=p.parse_args();print('image associations:',import_images(a.images,a.manifest,a.catalog,a.output))
if __name__=='__main__':main()
