#!/usr/bin/env python3
import copy,gzip,hashlib,importlib.util,json,sys
from pathlib import Path
D=Path(__file__).parent
sp=importlib.util.spec_from_file_location('a4a_repaired_proxy',D/'proxy3.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
w=Path('/mnt/raid0/llm/tmp/refactor-a4a-prefix-20261031/runs/native-1793472509/results/C4/cxa+a4a-treatment/r1/wire/wire-bodies.jsonl.gz')
rows=[json.loads(l) for l in gzip.open(w,'rt')]; original=rows[0]['body']['input'][3];candidate=rows[5]['body']['input'][3]
f=m._middle_truncated_task_match
checks={}
assert f(original,candidate); checks['recorded_three_part_match']=True
for name,mutate in [
 ('prefix_tamper',lambda x:x['content'][0].update(text='X'+x['content'][0]['text'][1:])),
 ('suffix_tamper',lambda x:x['content'][2].update(text=x['content'][2]['text'][:-1]+'X')),
 ('metadata_tamper',lambda x:x['content'][1].update(detail='changed')),
 ('nontruncation',lambda x:x['content'][1].update(text='ordinary omitted text')),
 ('role_tamper',lambda x:x.update(role='assistant')),
 ('second_marker',lambda x:x['content'][0].update(text=x['content'][0]['text']+'…3 tokens truncated…'))]:
 bad=copy.deepcopy(candidate); mutate(bad); assert not f(original,bad),name;checks[name]=True
xf=m.Transformer([],True,True); xf.transform(rows[0]['body'],rows[0]['path']); body,rec=xf.transform(rows[5]['body'],rows[5]['path'])
assert rec['task_pin']['mode']=='restored-exact-middle-truncation';assert body['input'][3]==original
checks['recorded_transform_restores_exact_original']=True
xf=m.Transformer([],True,True);xf.transform(rows[0]['body'],rows[0]['path']);bad=copy.deepcopy(rows[5]['body']);bad['input'].append(copy.deepcopy(candidate));_,rec=xf.transform(bad,rows[5]['path']);assert 'task_pin' not in rec;checks['duplicate_candidate_ambiguous_refused']=True
xf=m.Transformer([],True,True);xf.transform(rows[0]['body'],rows[0]['path']);s=xf.session(rows[0]['body']);other=copy.deepcopy(original);other['content'][0]['text']=other['content'][0]['text'][:40000]+'DIFFERENT'+other['content'][0]['text'][40000:];s.last_tool_body['input'].append(other);_,rec=xf.transform(rows[5]['body'],rows[5]['path']);assert 'task_pin' not in rec;checks['multiple_known_originals_refused']=True
single=copy.deepcopy(candidate);single['content']=[dict(candidate['content'][0],text=''.join(p['text'] for p in candidate['content']))];assert f(original,single);checks['legacy_single_part_retained']=True
out={'status':'PASS','checks':checks,'wire':str(w),'wire_sha256':hashlib.sha256(w.read_bytes()).hexdigest(),'scope':'offline recorded-wire repair only; no native performance or efficacy conclusion'}
(D/'replay-controls.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
