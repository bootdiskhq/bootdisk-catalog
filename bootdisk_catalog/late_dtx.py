"""Replay the bounded quiz/duplicate-section selectors against original K.DTX."""
import base64,hashlib
from .catalog import CatalogError

def fields(manifest,entry):
    evidence=entry.get('evidence',{})
    if not ('quiz_menu' in evidence or 'physical_section' in evidence):return None
    from bootdisk_ingest.adapters.kcd.late_dtx import occurrences,PIXIA,QUIZ
    doc=manifest['source']['dtx_file'];raw=base64.b64decode(doc['raw_base64'],validate=True);digest=hashlib.sha256(raw).hexdigest()
    matches=[f for f in manifest['file_inventory'] if f['path'].casefold()=='k.dtx']
    if len(matches)!=1 or digest!=doc['sha256'] or digest!=matches[0]['sha256']:raise CatalogError('Invalid primary DTX evidence')
    blocks=occurrences(raw.decode('cp1252'));sid=entry['source_id']
    if 'quiz_menu' in evidence:
        if sid!='Quiz' or digest!='7466a4d886293f3d8ffeee052a77791fbe7e2bf7aae5334ffc1f89ddc0f21144':raise CatalogError('Unqualified quiz source')
        sources=[x for x in manifest['source']['supplemental_metadata'] if x.get('role')=='quiz_questions_and_answers']
        if len(sources)!=1 or hashlib.sha256(base64.b64decode(sources[0]['raw_base64'],validate=True)).hexdigest()!=QUIZ:raise CatalogError('Missing original quiz questions')
        section=blocks['Generelt'][0];title,desc='Quiz','QuizTekst'
    else:
        selectors={'Flytter':('K36',0),'K36':('K36',1),'K38':('K38',0),'K39':('K39',0),'K42':('K42',0)}
        if digest!=PIXIA or sid not in selectors:raise CatalogError('Unqualified repeated DTX section')
        name,i=selectors[sid]
        if evidence['physical_section']!={'name':name,'index':i}:raise CatalogError('Incorrect occurrence selector')
        section=blocks[name][i];title,desc='Titel','Global'
    if entry['raw']!=section or entry['normalized']['title']!=section[title] or entry['normalized']['description']!=section[desc]:raise CatalogError('DTX fields disagree with original section')
    return title,desc
