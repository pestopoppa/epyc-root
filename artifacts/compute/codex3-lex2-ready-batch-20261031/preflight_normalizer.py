#!/usr/bin/env python3
import collections,hashlib,json,pathlib,sys
D=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(D/'research-scorer-snapshot'));from scripts.speech.stt_bakeoff import stt_norm
p=pathlib.Path('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/dev-native/MANIFEST-V2.json');m=json.loads(p.read_text());counts=collections.Counter();problem=[]
for r in m['records']:
 a=pathlib.Path(r['annotations_path']);raw=a.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=r['annotations_sha256']:raise RuntimeError('annotation drift')
 x=json.loads(raw);ref=stt_norm.normalise_v1(x['reference'],'en',side='reference');terms=[stt_norm.normalise_v1(t,'en',side='reference') for t in x['keywords']];counts['refs_'+ref.status]+=1
 for t in terms:counts['keywords_'+t.status]+=1
 if ref.status!='ok' or any(t.status!='ok' for t in terms):problem.append({'clip_id':r['file_id'],'reference_status':ref.status,'keyword_status_counts':dict(collections.Counter(t.status for t in terms))})
out={'schema':'cs8.lex2.dev-reference-normalizer-preflight.v1','manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'normalizer_sha256':stt_norm.normaliser_sha256(),'records':len(m['records']),'counts':dict(counts),'problem_rows':problem,'test_accessed':False,'model_accessed':False,'raw_token_unk':'not observed; preflight does not infer it'};q=D/'NORMALIZER-PREFLIGHT.json';q.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(json.dumps({'records':out['records'],'counts':out['counts'],'problem_rows':len(problem),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()},sort_keys=True))
