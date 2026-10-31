#!/usr/bin/env python3
"""Deterministic union of supplied dictionary metadata by call, never gold references."""
import collections,hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parent;P=pathlib.Path('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/dev-native/MANIFEST-V2.json');h=lambda b:hashlib.sha256(b).hexdigest();m=json.loads(P.read_bytes());calls=collections.defaultdict(set);bindings=[]
for r in m['records']:
 raw=pathlib.Path(r['annotations_path']).read_bytes()
 if h(raw)!=r['annotations_sha256']:raise RuntimeError('annotation drift')
 d=json.loads(raw)['dictionary']
 if not isinstance(d,list) or not all(isinstance(x,str) for x in d):raise RuntimeError('invalid supplied dictionary')
 calls[r['call_id']].update(x.strip() for x in d if x.strip());bindings.append({'clip_id':r['file_id'],'call_id':r['call_id'],'dictionary_sha256':r['dictionary_sha256'],'annotation_sha256':r['annotations_sha256']})
out={'schema':'cs8.lex2.call-contexts.v1','dev_manifest_sha256':h(P.read_bytes()),'construction':'sorted exact-string union of supplied dictionary entries by call; no reference or keyword fields accessed','calls':{k:sorted(v) for k,v in sorted(calls.items())},'input_bindings':sorted(bindings,key=lambda x:x['clip_id'])};q=D/'CONVERSATION-CONTEXTS.json';q.write_text(json.dumps(out,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n');print('calls',len(calls),'inputs',len(bindings),'sha256',h(q.read_bytes()))
