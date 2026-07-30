#!/usr/bin/env python3
import base64, hashlib, json, zlib
from pathlib import Path
ROOT=Path('step3_extension_20_v1/human_review_working')
EXPECTED={
'2006-0077__d5877768ebe69914.annotation.json':'e1e35dbc664330134ca19dac8218770a02fd3d57',
'2007-0249__7a239ec5c306fa6d.annotation.json':'6c77c819eabab43685bd2a846408680ea73b1225',
'2008-0066__843fc74e8a4f44c0.annotation.json':'da5460912590a7f109d5fe21cae8b3f578dd053d',
'2009-0171__6edf8772870b3a19.annotation.json':'3e59e572612b410e25910792723bdd0664cc4a08',
'2010-0271__2db3e9f8dfdadc71.annotation.json':'706a41a3686a5bd14ba0332ebeb4671827b8b2d7'}
def blob_sha(data): return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def ptr(path): return [p.replace('~1','/').replace('~0','~') for p in path.lstrip('/').split('/')]
def apply(doc,op):
    parts=ptr(op['path']); cur=doc
    for p in parts[:-1]: cur=cur[int(p)] if isinstance(cur,list) else cur[p]
    k=int(parts[-1]) if isinstance(cur,list) else parts[-1]
    if op['op'] in ('add','replace'): cur[k]=op['value']
    elif op['op']=='remove': cur.pop(k)
    else: raise ValueError(op['op'])
payload=json.loads(zlib.decompress(base64.b64decode(Path('.github/first5_annotation_audit_payload.b64').read_text())))
for name,ops in payload.items():
    path=ROOT/name; raw=path.read_bytes(); actual=blob_sha(raw)
    if actual!=EXPECTED[name]: raise SystemExit(f'{name}: expected {EXPECTED[name]}, found {actual}')
    doc=json.loads(raw)
    for op in ops: apply(doc,op)
    path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
