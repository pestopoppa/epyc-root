#!/usr/bin/env python3
"""Freeze the actual selected held-out instance before its first exposure."""
import hashlib,json,os,pathlib
D=pathlib.Path(__file__).resolve().parent;L=D.parent/'lex2';h=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();sp=L/'DEV-SELECTION.json';hp=L/'HELDOUT-PLAN.json'
if not sp.is_file() or not hp.is_file():raise SystemExit('HELD: actual dev selection and base held-out plan absent')
s=json.loads(sp.read_text());b=json.loads(hp.read_text())
if b['selection_sha256']!=h(sp) or b['selection']!=s['selection'] or s['test_opened'] is not False or s['raw_terminal_sha256']!=h(L/'run/TERMINAL.json') or s['nonlist_noise_floor_state']!='known_lexical':raise RuntimeError('frozen dev selection drift')
a=s['selection']['alpha'];scope=s['selection']['scope'];cells=[['nemo','none',0],['nemo','global',a],['nemo','local',a],['whisper','none',None],['whisper','global',None],['whisper','local',None]];aux=[['whisper','none-auto',None],['whisper','global-auto',None],['whisper','local-auto',None]]
o={'schema':'cs8.lex2.heldout-instance.v1','selection_sha256':h(sp),'base_heldout_plan_sha256':h(hp),'source_catalog_sha256':h(D/'SOURCE-SHA256SUMS'),'policy_sha256':h(D/'FLEURS-CONTEXT-POLICY.json'),'contexts_sha256':h(D/'TEST-CONVERSATION-CONTEXTS.json'),'contract_sha256':h(D/'HELDOUT-CONTRACT.md'),'selected_alpha':a,'selected_scope':scope,'contextual_original_n':755,'fleurs_original_n':3050,'original_cells':cells,'contextual_auto_language_whisper_auxiliary_cells':aux,'native_attempts_planned':25095,'m16_scope':'sole preselected Nemo alpha and scope vs alpha-zero, per original guards','test_inference_started':False,'test_scoring_started':False}
p=D/'INSTANCE-PLAN.json';fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
with os.fdopen(fd,'w') as f:json.dump(o,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
fd=os.open(D,os.O_DIRECTORY);os.fsync(fd);os.close(fd);print('pre-test instance',h(p))
