#!/usr/bin/env python3
import base64, hashlib, json, zlib
from pathlib import Path
ROOT=Path('step3_extension_20_v1/human_review_working')
EXPECTED={
'2019-0188__1d1f6357de0f3352.annotation.json':'ceb7604ef5330641a3834bd17838006c11b852f5',
'2020-0016__5c6e21ab23447af0.annotation.json':'7aa583ce4d91e3db4075f46fae2ad948293f1964',
'2021-0221__8aaaf372db377584.annotation.json':'bde133877984ad99b927b816e6ccff074f91f2be',
'2021-0286__a36d7f18af6e7a27.annotation.json':'9bf1a70b142fc9cfb74a1348fd06aa2573fb2007',
'2022-0058__772cd84a0961a452.annotation.json':'980a1e07c1f9bc321628f70089768cb02a274c05',
'2023-0057__e17febf10e432eb9.annotation.json':'ed08e84ddae90d6c2b8dfebd343fd284bea28e85',
'2024-0001__dc59a5a0114b782d.annotation.json':'d5cd889579109a5884327265d0dba48f8777a594',
'2025-0138__5762b029d7edbc0c.annotation.json':'27070b3d0c2492787741a01526c53b60b315e10f',
'2025-0181__b0e89b78cd668c9e.annotation.json':'caa474d0cc76e098f3e1262162f89a8487945445',
'2026-0100__34edf2d1b2e65515.annotation.json':'5b27f99f2ed91da065cec68661dfc7e941d58807'}
def blob_sha(data): return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def ptr(path): return [p.replace('~1','/').replace('~0','~') for p in path.lstrip('/').split('/')]
def apply(doc,op):
    parts=ptr(op['path']); cur=doc
    for p in parts[:-1]: cur=cur[int(p)] if isinstance(cur,list) else cur[p]
    k=int(parts[-1]) if isinstance(cur,list) else parts[-1]
    if op['op'] in ('add','replace'): cur[k]=op['value']
    elif op['op']=='remove': cur.pop(k)
    else: raise ValueError(op['op'])
parts=sorted(Path('.github/rest10_chunks').glob('part*'))
if [p.name for p in parts] != [f'part{i:02d}' for i in range(14)]: raise SystemExit('Payload chunk set mismatch')
text=''.join(p.read_text().strip() for p in parts)
if hashlib.sha256(text.encode()).hexdigest()!='4b7fbb4e2c5b10df807a60f09fe3b4d5946f526d5de0c98e91a235bdf07a5932': raise SystemExit('Payload SHA-256 mismatch')
payload=json.loads(zlib.decompress(base64.b64decode(text)))
if set(payload)!=set(EXPECTED): raise SystemExit('Payload target set mismatch')
for name,ops in payload.items():
    path=ROOT/name; raw=path.read_bytes(); actual=blob_sha(raw)
    if actual!=EXPECTED[name]: raise SystemExit(f'{name}: expected {EXPECTED[name]}, found {actual}; refusing overwrite')
    doc=json.loads(raw)
    for op in ops: apply(doc,op)
    path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
    print('updated',path)
