#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT = Path.cwd()
ANN = ROOT / 'step3_extension_20_v1/human_review_working'
TMP = ROOT / '.fidelity_apply_tmp'
BEFORE = {
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
AFTER = {
  "2006-0077__d5877768ebe69914.annotation.json": "c151de7d31c23593a3103010acde60c0e85b7a2c4b5c33026911fcf57a21eb37",
  "2007-0249__7a239ec5c306fa6d.annotation.json": "a666d220bdbc16dd541777116da9ef2f3247334bf8e8256c51e2d9422ae5f8f8",
  "2008-0066__843fc74e8a4f44c0.annotation.json": "94370bda95592a988f5d757221e7c9708f9e54978a79ba464d1ed834cdab06ee",
  "2009-0171__6edf8772870b3a19.annotation.json": "6c0a77b912bd9b63131639bec9189ffe785dbee540bcea7f9f72547bd8d02081",
  "2010-0271__2db3e9f8dfdadc71.annotation.json": "ca0532527c4d583e8de4c2d4254e200ede3f0e851a7f5911b42a25b2ba0805ab",
  "2011-0098__ee69a71e72e4a031.annotation.json": "723744f8fbe3adc2d1aad6d031e2a85cb12d37dd397419e6477af5e5d1208e01",
  "2012-0259__71d534e47740b13c.annotation.json": "00d0a19b23ca3f0abbbdc3239c55579ba991f3809ddbdb7f78529e1f2350c090",
  "2013-0011__5f652dd0aa52e54f.annotation.json": "61c1566e9dcf96c00d5f974f3ab3ce6b0f1ee7037251d16afe61a269f89d2567",
  "2016-0175__c13a622de38db424.annotation.json": "52d62618d36aaf20023b0b1da281098b038f32a18897ae829a953f7aae130eac",
  "2018-0246__0ffbff521ab9746f.annotation.json": "65b1b5d2d3f07caa753199164ef19a5aacb5d609ecce170891059d2515af69d3",
  "2019-0188__1d1f6357de0f3352.annotation.json": "ad19b2b97aef496cc7f6f99088ad1eaadeaa4de49ac19f16108460739005b74f",
  "2020-0016__5c6e21ab23447af0.annotation.json": "a3b48b03d465ca40f68b8a413892a30d9bc8f521c8f9ea5a1abc45e7da1d384b",
  "2021-0221__8aaaf372db377584.annotation.json": "47cb64206b2f1deaf9675fca0585081443c16a3d44d2358bbd5770a55a8561ef",
  "2021-0286__a36d7f18af6e7a27.annotation.json": "ba2ed65d0fa2314993fa3675407965fc82ada5c0bf4f182d564c0fb8b8724bbf",
  "2022-0058__772cd84a0961a452.annotation.json": "f951e6a313af4d9ea58a2efff40c965d7c2c9b660a8838ad1ea7f7bccebe271e",
  "2023-0057__e17febf10e432eb9.annotation.json": "b9ad01e75ef90f9b73492c4ce45de4bcd40e18f73a7ecc0e653d58096942cd71",
  "2024-0001__dc59a5a0114b782d.annotation.json": "21f9c26e0a5a90729ea38d9c23aa18796d5cb1e4c56a7b66ea04444a492687b9",
  "2025-0138__5762b029d7edbc0c.annotation.json": "9fab82a4365f04ce9bf6453a3ff4aa4616b61cc342dcd29ce93f365a80e9fbc9",
  "2025-0181__b0e89b78cd668c9e.annotation.json": "0ba6e7dbcaf850d12595a6267346e3d5980d3dc4e9ff6f805b06699a0d21ac06",
  "2026-0100__34edf2d1b2e65515.annotation.json": "160061cc21753472ac80299a1a5cdb58af467bef00d8d336a9f34cfc41e11873"
}
ALLOWED_KEYS = {'raw_text','raw_value','raw_expression','definition_text','raw_reason_text','action_text','contact_text','exact_quote','text','evidence_ids','page_number','printed_page_label','page_text_sha256','start_char','end_char','extraction_method','quality','annotation_note'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def protected(value, path=''):
    if isinstance(value, dict):
        out = {}
        for key, child in value.items():
            p = f'{path}/{key}'
            if key in ALLOWED_KEYS:
                if key == 'text' and not any('/'+name+'/' in p for name in ('exceptions','previous_action_credit','relationships')):
                    out[key] = protected(child, p)
                continue
            if p.endswith('/annotation_metadata/quality_flags'):
                out[key] = sorted(x for x in child if x != 'visual_transcription_used')
            else:
                out[key] = protected(child, p)
        return out
    if isinstance(value, list):
        return [protected(x, f'{path}/{i}') for i, x in enumerate(value)]
    return value

def resolve_parent(root, path):
    node = root
    for key in path[:-1]:
        node = node[key]
    return node, path[-1]

def main():
    files = sorted(ANN.glob('*.annotation.json'))
    if len(files) != 20:
        raise SystemExit(f'expected 20 annotations, found {len(files)}')
    originals = {}
    for path in files:
        if BEFORE.get(path.name) != sha(path):
            raise SystemExit(f'guard failed for {path.name}')
        originals[path.name] = json.loads(path.read_text(encoding='utf-8'))
    archive = ROOT/'.fidelity_patch.zip'
    archive.write_bytes(b''.join((ROOT/f'.github/fidelity_patch.part{i}').read_bytes() for i in range(4)))
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir()
    with zipfile.ZipFile(archive) as z:
        z.extractall(TMP)
    patch = json.loads((TMP/'patch.json').read_text(encoding='utf-8'))
    if set(patch) != set(BEFORE):
        raise SystemExit('patch file set mismatch')
    for name, operations in patch.items():
        dest = ANN/name
        data = json.loads(dest.read_text(encoding='utf-8'))
        for op, path, value in operations:
            parent, key = resolve_parent(data, path)
            if op == 'set':
                parent[key] = value
            elif op == 'del':
                del parent[key]
            else:
                raise SystemExit(f'unknown operation {op}')
        if protected(originals[name]) != protected(data):
            raise SystemExit(f'protected-field invariance failed: {name}')
        if data['classification']['human_confirmed'] is not False:
            raise SystemExit(f'human_confirmed changed: {name}')
        if data['benchmark_metadata']['gold_record'] is not False:
            raise SystemExit(f'gold_record changed: {name}')
        if data['annotation_metadata']['record_status'] != 'first_pass_complete':
            raise SystemExit(f'record_status changed: {name}')
        dest.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        if sha(dest) != AFTER[name]:
            raise SystemExit(f'corrected hash mismatch: {name}')
    shutil.rmtree(TMP)
    archive.unlink()
    for p in [ROOT/'.github/apply_verbatim_fidelity.py', ROOT/'.github/workflows/apply-verbatim-fidelity.yml', ROOT/'.github/workflows/export-current-annotations.yml', ROOT/'.github/fidelity_patches/2007-0249__7a239ec5c306fa6d.annotation.json.patch.json']:
        if p.exists():
            p.unlink()
    for i in range(4):
        p = ROOT/f'.github/fidelity_patch.part{i}'
        if p.exists():
            p.unlink()
    print('applied 20 guarded source-text/evidence corrections')

if __name__ == '__main__':
    main()
