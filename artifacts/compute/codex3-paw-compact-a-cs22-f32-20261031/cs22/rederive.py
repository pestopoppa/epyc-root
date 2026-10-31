import json,hashlib,collections
from pathlib import Path
r=Path('/mnt/raid0/llm/tmp/codex3-cs22-a1-native-20261030/results'); files=sorted(r.glob('[0-9][0-9][0-9].result.json')); assert len(files)==160
pair={}; rows=[]
for f in files:
 j=json.loads(f.read_text());b=j['binding'];name=f.name[:3];assert j['rc']==0 and j['valid'] and j['child_reaped'] and j['final']['stage']=='final' and j['final']['tokens']
 for suffix,key in [('stdout','stdout_sha256'),('stderr','stderr_sha256')]:assert hashlib.sha256((r/(name+'.'+suffix)).read_bytes()).hexdigest()==j[key]
 e=json.loads((r/(name+'.exposure.json')).read_text());assert e['binding']==b
 key=(b['clip_id'],b['right']);assert b['mode'] not in pair.setdefault(key,{});pair[key][b['mode']]=j
 rows.append({'record':name,'result_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'stdout_sha256':j['stdout_sha256'],'stderr_sha256':j['stderr_sha256']})
assert len(pair)==80
for key,v in pair.items():
 assert set(v)=={'chunk80','single'} and v['chunk80']['binding']['pcm_sha256']==v['single']['binding']['pcm_sha256'] and v['chunk80']['binding']['pins']==v['single']['binding']['pins'] and v['chunk80']['final']['tokens']==v['single']['final']['tokens']
c=json.loads((r/'COMPLETE.json').read_text());assert c['cache_pass'] and len(c['pairs'])==80 and all(x['identical'] for x in c['pairs'])
print(json.dumps({'records':160,'pairs':80,'identical':80,'clips':len({x[0] for x in pair}),'right_contexts':sorted({x[1] for x in pair}),'pins':files and json.loads(files[0].read_text())['binding']['pins'],'complete_sha256':hashlib.sha256((r/'COMPLETE.json').read_bytes()).hexdigest(),'rows':rows},indent=2))
