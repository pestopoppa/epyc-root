#!/usr/bin/env python3
"""Metadata-only: freeze the per-conversation union of supplied dictionaries."""
import hashlib,json,pathlib,os
D=pathlib.Path(__file__).resolve().parent
P=pathlib.Path('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/test-native/MANIFEST-V2.json')
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
expected='bf5a32fb1a74d6cac4950f8973abc2583c08ad4e71a1169399aa8eb443188fd7'
if sha(P)!=expected:raise RuntimeError('test membership manifest drift')
rows=json.loads(P.read_text())['records'];calls={};bindings={}
for row in rows:
 if row['eligibility']!='heldout':continue
 path=pathlib.Path(row['annotations_path'])
 if sha(path)!=row['annotations_sha256']:raise RuntimeError('metadata hash drift '+row['file_id'])
 terms=json.loads(path.read_text())['dictionary']
 if not isinstance(terms,list) or any(not isinstance(v,str) for v in terms):raise RuntimeError('invalid provided dictionary')
 canonical=sorted(set(v.strip() for v in terms if v.strip()))
 calls.setdefault(row['call_id'],set()).update(canonical)
 bindings[row['file_id']]={'dictionary_sha256':row['dictionary_sha256'],'annotation_sha256':row['annotations_sha256'],'call_id':row['call_id'],'aa_overlap_status':row['aa_overlap_status']}
if len(bindings)!=755:raise RuntimeError('original test membership changed')
out={'schema':'cs8.lex2.test-conversation-contexts.v1','test_manifest_sha256':expected,'policy':'sorted outcome-independent per-call union of supplied dictionary fields only; no references, keywords, hypotheses or scores used','candidate_n':755,'unknown_aa_overlap_n':sum(v['aa_overlap_status']=='unknown' for v in bindings.values()),'calls':{k:sorted(v) for k,v in sorted(calls.items())},'binding':bindings}
p=D/'TEST-CONVERSATION-CONTEXTS.json';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'w') as f:json.dump(out,f,sort_keys=True,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print('calls',len(calls),'candidates',len(bindings),'unknown_aa',out['unknown_aa_overlap_n'],'sha256',sha(p))
