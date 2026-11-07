"""Typed APC raw-index adapter; producer provenance is recorded in the manifest.

source_hash belongs to an APC entity and is NOT necessarily a file digest.
Only explicitly declared content hashes may establish file freshness.
"""
import re


def terms(value, maximum=40):
    if isinstance(value,str):value=[value]
    if not isinstance(value,list) or any(not isinstance(v,str) for v in value):
        raise ValueError('Terms must be strings or arrays of strings')
    values=list(dict.fromkeys(v.strip() for v in value if v.strip()))
    if len(values)>maximum or any(len(v)>500 for v in values):
        raise ValueError('Term capacity exceeded; metadata was not truncated')
    return values


def document(doc):
    if not isinstance(doc,dict):raise ValueError('Document must be an object')
    kind=doc.get('entity_type','file')
    if kind!='file':raise ValueError('Unsupported entity type: '+str(kind))
    path=doc.get('path_or_route',doc.get('path',''))
    if not isinstance(path,str):raise ValueError('File path must be a string')
    content_hash=doc.get('content_hash')
    if doc.get('source_hash_kind')=='file_sha256':content_hash=doc.get('source_hash')
    if content_hash is not None and (not isinstance(content_hash,str) or not re.fullmatch('[a-fA-F0-9]{64}',content_hash)):
        raise ValueError('Invalid file SHA256')
    raw_terms=terms(doc.get('raw_terms',[]),160)
    notes='\n'.join(raw_terms)
    if len(notes)>6000:raise ValueError('Raw term capacity exceeded')
    return path,content_hash.lower() if content_hash else None,{
        'aliases':terms(doc.get('aliases',[])), 'tags':terms(doc.get('keywords',[])),
        'notes':notes,'must_not_break':terms(doc.get('must_not_break',[]))}, {
        'entity_type':kind,'entity_id':doc.get('entity_id'),
        'entity_hash':doc.get('source_hash'),'file_hash_verified':bool(content_hash),
        'confidence':'imported_metadata_not_verified_code_fact'}
