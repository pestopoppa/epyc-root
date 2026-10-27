#!/usr/bin/python3
"""Fail closed unless main seals the packet and owner enrolls the write side."""
import hashlib, json, pathlib, re, subprocess
D=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
main=json.loads((D/'MAIN-APPROVED.json').read_text())
if main != {'id':'rtg57-c5-vkq-t96','source_manifest_sha256':sha(D/'SOURCES.sha256'), 'protocol_sha256':sha(D.parent/'PROTOCOL.md'), 'scope':'experimental-t96-only'}:
    raise SystemExit('main seal mismatch')
enrollment=json.loads((D/'OWNER-ENROLLED.json').read_text())
commit=enrollment.get('root_commit','')
if not re.fullmatch('[0-9a-f]{40}',commit) or enrollment.get('task') != 'VB-RTG57-VKQ-WIRE':
    raise SystemExit('invalid owner enrollment identity')
subprocess.run(['git','-C','/workspace','merge-base','--is-ancestor',commit,'origin/main'],check=True)
for path, text in [('scripts/vidya/adapters/README.md','rtg57-c5-vkq-t96'),('handoffs/active/vidya-belief-substrate-program.md','VB-RTG57-VKQ-WIRE')]:
    content=subprocess.check_output(['git','-C','/workspace','show',f'{commit}:{path}'],text=True)
    if text not in content:
        raise SystemExit(f'owner enrollment missing {text}')
print('main seal and committed write-side enrollment verified')
