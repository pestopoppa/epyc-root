#!/usr/bin/env python3
"""Predeclare lexicon-free FLEURS contexts from IDs only; never inspect references."""
import hashlib,json,pathlib,os,collections
D=pathlib.Path(__file__).resolve().parent; L=D.parent/'lex2'
P=pathlib.Path('/mnt/raid0/llm/data/stt-cs8-public-20261030/stt5-baseline-test-manifest.json')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
if sha(P)!='242be009933eaf7e6b2e70e56b0f55f76a3d22b815eb4ce7fcf95a1467b72362':raise RuntimeError('FLEURS source drift')
c=json.loads((D/'TEST-CONVERSATION-CONTEXTS.json').read_text());calls=sorted(c['calls']);domain=json.loads((L/'DOMAIN-LEXICON-PROPOSAL.json').read_text())['phrases']['en'];src=json.loads(P.read_text());rows=[]
for r in src['rows']:
 if r.get('condition')!='fleurs-test':continue
 ident=r['clip_id'];i=int.from_bytes(hashlib.sha256(('LEX2-FLEURS-CALL-v1\0'+ident).encode()).digest(),'big')%len(calls)
 rows.append({'clip_id':ident,'language':r['language'],'wav_path':r['wav_path'],'wav_sha256':r['wav_sha256'],'frames':r['frames'],'assigned_call_id':calls[i]})
counts=collections.Counter(r['language'] for r in rows)
if counts!={'en_us':647,'it_it':865,'de_de':862,'fr_fr':676}:raise RuntimeError('FLEURS membership drift')
obj={'schema':'cs8.lex2.fleurs-context-policy.v1','source_sha256':sha(P),'test_contexts_sha256':sha(D/'TEST-CONVERSATION-CONTEXTS.json'),'domain_lexicon_sha256':sha(L/'DOMAIN-LEXICON-PROPOSAL.json'),'global_list_policy':'same pinned English CS technical-name list is used as the explicitly labeled probe list on each of the four languages; do not call this a translated or complete language-specific lexicon','local_list_policy':'assign one of the 46 heldout call supplied-dictionary unions by SHA256(LEX2-FLEURS-CALL-v1 NUL clip_id) modulo sorted call count; assignment uses no references, keywords, hypotheses or scores','limitations':'language-dependent results describe insertion of supplied probe terms only; no claim that the lists cover every language or domain term','global_context':domain,'counts':dict(counts),'rows':rows}
p=D/'FLEURS-CONTEXT-POLICY.json';fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
with os.fdopen(fd,'w') as f:json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print('rows',len(rows),'sha256',sha(p))
