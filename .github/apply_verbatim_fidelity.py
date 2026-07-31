#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, io, json, shutil, zipfile
from pathlib import Path
ROOT=Path.cwd()
ANN=ROOT/'step3_extension_20_v1/human_review_working'
PAYLOAD=ROOT/'.github/verbatim_release_payload.zip'
TMP=ROOT/'.verbatim_release_tmp'
BEFORE={
  "2006-0077__d5877768ebe69914.annotation.json": "2bf9828062882d5b2adbdd4bb93f14204158e4ae3e0d269ba1f57160f59e6eb7",
  "2007-0249__7a239ec5c306fa6d.annotation.json": "3ac914465e05434a49f33857c8b6b0f556461c968099791c84ea1d49ff795dba",
  "2008-0066__843fc74e8a4f44c0.annotation.json": "da2a66f623d772c4f85ce959203eb2d706f5fe28b1c446e630f60a176a4d0905",
  "2009-0171__6edf8772870b3a19.annotation.json": "5e43c0713b31d7578971156dee78275a90d3211dda2c69530f8920192d65c4d9",
  "2010-0271__2db3e9f8dfdadc71.annotation.json": "1e64a671b9bcf38e7777d6a1cb6cc276674660e2466a9bac568cf760ed327ef4",
  "2011-0098__ee69a71e72e4a031.annotation.json": "5bd3f84cdee96514aaa1718db387380d526efd35029b3ac7ed407837a9e2af2f",
  "2012-0259__71d534e47740b13c.annotation.json": "e1e0ba4833bfbf235c209aff5c592f6066763a7931f535aed8b7a4dbb75e9ebb",
  "2013-0011__5f652dd0aa52e54f.annotation.json": "000d11591f2a65b44357ee34aed9d8ed25f48c555d1896c62ce49a7c51f50b8f",
  "2016-0175__c13a622de38db424.annotation.json": "b824e1819772f56927670577b329cf96cb8c2f7b5e9049a93ea786f935308792",
  "2018-0246__0ffbff521ab9746f.annotation.json": "532d9ed289c1a3652fa35bdebe81c538e9a0f04469ea4ee3178067da075259f1",
  "2019-0188__1d1f6357de0f3352.annotation.json": "4047069388f9d8f67eda81005b86c60ad785f80a09bda6eebf4cedfa5a17dcad",
  "2020-0016__5c6e21ab23447af0.annotation.json": "73a3ff1055f0c4075348e9878c24871db8040e530ae1288a579f1e5a13fe96e2",
  "2021-0221__8aaaf372db377584.annotation.json": "3acaace02b9aa82d918f2647b9a5f76ef09129d13bf73311f5c4fa8edfe7cc05",
  "2021-0286__a36d7f18af6e7a27.annotation.json": "afa4cba06be22a26500dbeb9e670a9b3fd70db5d2df1a4e502bc25e8a6d1c121",
  "2022-0058__772cd84a0961a452.annotation.json": "336d647c53a8b911afefdeea4217a7c598bbf076c70ed372db45fbe9c0a1c050",
  "2023-0057__e17febf10e432eb9.annotation.json": "64ae987c4a3f1f43837037fb392a3edd40722ed8eb0b9f12451c597bb06bd56f",
  "2024-0001__dc59a5a0114b782d.annotation.json": "0604294132e2616758f37a025066b2489115917af112e4ab13753ce3c2bf4906",
  "2025-0138__5762b029d7edbc0c.annotation.json": "fa2aa190dee40c2cea3b16af1a99fad59866e23958dd568c8432099b92a94e7d",
  "2025-0181__b0e89b78cd668c9e.annotation.json": "5945f0d1952a194f8e65df0fbd4c5a7781c79571ff12d986d16949eed202f29a",
  "2026-0100__34edf2d1b2e65515.annotation.json": "360ba85ef9cc82f5d37d98c364b786f8e595789bc5d80ff5bd9ed284163eeb3e"
}
AFTER={
  "2006-0077__d5877768ebe69914.annotation.json": "dd5e87d5b1699ecf50cdb0fa7f25092883fca80858667332853b8f1d8b14367f",
  "2007-0249__7a239ec5c306fa6d.annotation.json": "d4721c83ee3540fe29aa64fce64ed8ace9828b5e261c2557397830673041acee",
  "2008-0066__843fc74e8a4f44c0.annotation.json": "68c5a02d7c19343817f4a838944cbbf0df49e92886a39a28f98aad3311801e6f",
  "2009-0171__6edf8772870b3a19.annotation.json": "537215767a39f36991b7b785ab3bf2df1b98bd9d8f789165268ef84ad03280d6",
  "2010-0271__2db3e9f8dfdadc71.annotation.json": "45a1fc6b64bf405c88eb7e7b7acfd94af317f31235b3115e45b5f905a84c151a",
  "2011-0098__ee69a71e72e4a031.annotation.json": "e90cd5f239718d59e21015ceb40cc5959ccff10a611fbcae3f8a682807dc4cf0",
  "2012-0259__71d534e47740b13c.annotation.json": "782ad1963436a9129cdce25a49d3f220402629b9dc0a7befde30b9d3eef94f28",
  "2013-0011__5f652dd0aa52e54f.annotation.json": "7b67f242db01a1b826feaba6fb88bb5b2145113c33d1b67b365b66b2899783b5",
  "2016-0175__c13a622de38db424.annotation.json": "dd8c17e34a3e4f30f00d711f4bba3c27f919244a30b38c29a472ed8536af0f0b",
  "2018-0246__0ffbff521ab9746f.annotation.json": "a6ca820b920be1e3918a8db962f56a6b90de6d8bf3dc5d991f266927e32b21c5",
  "2019-0188__1d1f6357de0f3352.annotation.json": "1f13e8917b306329e7a16764aad5b174431ecbe2ff1b390f39353dcf2624bab9",
  "2020-0016__5c6e21ab23447af0.annotation.json": "d544d1135d3d7a4706aa43528938438ef3a2523095582245f544430957131c71",
  "2021-0221__8aaaf372db377584.annotation.json": "c67a82e9adf35cb86201b32cc7030bdf1c0f198836aa56be459a451d519f7a47",
  "2021-0286__a36d7f18af6e7a27.annotation.json": "da2daf3dff7f90a78e4db90b4c324da10d19396e3897263f00b7ff3d66b13e48",
  "2022-0058__772cd84a0961a452.annotation.json": "82ceda3bae098e9ff527b0ad5aff8d71ac714da9562d4e050aa90ec7d131cf8d",
  "2023-0057__e17febf10e432eb9.annotation.json": "a2dcb1d3765cda1b1fc43c5caf7dd4a22586ffcd42764cf37e095e5b5776a81c",
  "2024-0001__dc59a5a0114b782d.annotation.json": "361df72b91aa16902508c767ff73b9e4986d3706bcfc659b700c80d02cb760c8",
  "2025-0138__5762b029d7edbc0c.annotation.json": "631c6d3f4a455001546c57a75764c3e0c63f6dda77915167378e5fc1cc788e81",
  "2025-0181__b0e89b78cd668c9e.annotation.json": "695d635931e95c7483929151f3e8fdc517f20d1517135e91933498624c0ca589",
  "2026-0100__34edf2d1b2e65515.annotation.json": "2b3c03c257f3fb587ca0f398e8c41a89db0b5566a91fbdae92967bc46688e5bf"
}
SOURCE_SCALAR={'raw_text','raw_value','raw_expression','definition_text','raw_reason_text','action_text','contact_text','raw_name','section_raw','exact_quote'}
SOURCE_LIST={'observed_events_or_defects','causes','unsafe_conditions','potential_consequences','affected_components','intended_risk_mitigation','objects_or_components','conditions','exclusions','configuration_conditions'}
EVIDENCE_LOCATION={'page_number','printed_page_label','page_text_sha256','start_char','end_char','extraction_method','quality','annotation_note'}

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def protected(v,path=''):
    if isinstance(v,dict):
        out={}
        for k,ch in v.items():
            p=f'{path}/{k}'
            if k in SOURCE_SCALAR: continue
            if k in SOURCE_LIST: continue
            if k=='text' and path.strip('/').split('/')[0] in {'exceptions','previous_action_credit'}: continue
            if path.startswith('/evidence_spans/') and k in EVIDENCE_LOCATION: continue
            out[k]=protected(ch,p)
        return out
    if isinstance(v,list):return [protected(x,f'{path}/{i}') for i,x in enumerate(v)]
    return v

def main():
    files=sorted(ANN.glob('*.annotation.json'))
    if len(files)!=20:raise SystemExit(f'expected 20 annotations, found {len(files)}')
    original={}
    for p in files:
        if BEFORE.get(p.name)!=sha(p):raise SystemExit(f'before hash mismatch: {p.name}')
        original[p.name]=json.loads(p.read_text(encoding='utf-8'))
    shutil.rmtree(TMP,ignore_errors=True);TMP.mkdir()
    encoded=PAYLOAD.read_bytes()
    try:
        payload=base64.b64decode(encoded,validate=True)
    except Exception as exc:
        raise SystemExit(f'payload base64 decode failed: {exc}')
    expected_zip_sha='512f528a3cd0a0445b3b52d07e84bb23c9ecc4ad83d8be0e391bd59b4de6a6ce'
    actual_zip_sha=hashlib.sha256(payload).hexdigest()
    if actual_zip_sha!=expected_zip_sha:
        raise SystemExit(f'payload zip hash mismatch: {actual_zip_sha}')
    with zipfile.ZipFile(io.BytesIO(payload)) as z:z.extractall(TMP)
    extracted=sorted(TMP.glob('*.annotation.json'))
    if {p.name for p in extracted}!=set(BEFORE):raise SystemExit('payload file set mismatch')
    changes=0
    for src in extracted:
        dest=ANN/src.name
        new=json.loads(src.read_text(encoding='utf-8'))
        old=original[src.name]
        if protected(old)!=protected(new):raise SystemExit(f'protected-field invariance failed: {src.name}')
        if [r['requirement_id'] for r in old['requirements']] != [r['requirement_id'] for r in new['requirements']]:raise SystemExit(f'requirement IDs changed: {src.name}')
        if [r['paragraph_reference'] for r in old['requirements']] != [r['paragraph_reference'] for r in new['requirements']]:raise SystemExit(f'paragraph references changed: {src.name}')
        if new['classification']['human_confirmed'] is not False:raise SystemExit(f'human_confirmed changed: {src.name}')
        if new['benchmark_metadata']['gold_record'] is not False:raise SystemExit(f'gold_record changed: {src.name}')
        if new['annotation_metadata']['record_status']!='first_pass_complete':raise SystemExit(f'record_status changed: {src.name}')
        dest.write_bytes(src.read_bytes())
        if sha(dest)!=AFTER[src.name]:raise SystemExit(f'after hash mismatch: {src.name}')
        changes+=1
    shutil.rmtree(TMP)
    cleanup=[
      '.github/apply_verbatim_fidelity.py','.github/verbatim_release_payload.zip',
      '.github/workflows/apply-verbatim-fidelity.yml','.github/workflows/export-current-annotations.yml',
      '.github/fidelity_patches/2007-0249__7a239ec5c306fa6d.annotation.json.patch.json',
      '.github/fidelity_patch.part0','.github/fidelity_patch.part1','.github/fidelity_patch.part2','.github/fidelity_patch.part3'
    ]
    for rel in cleanup:
        p=ROOT/rel
        if p.exists():p.unlink()
    print(f'applied {changes} guarded verbatim source/evidence corrections')
if __name__=='__main__':main()
