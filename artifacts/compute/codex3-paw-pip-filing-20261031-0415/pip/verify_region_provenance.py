import contextlib,io,hashlib,importlib.util,json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');spec=importlib.util.spec_from_file_location('inspect_pip',p);m=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(m)
root=Path('/mnt/micron/codex3-pip-head-r26-20261030/attempts');paths=list(root.glob('*/capture.json'));proof=m.t.NativeProof(paths,m.config['campaign'],m.raw);out=[]
for shard in (3,4):
 roots=[f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-head-r26-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}'];w=m.Read(roots);j=m.j.Journal(w,m.config['campaign'])
 for page in m.plan['pages'][5*shard:5*shard+5]:
  prefix='region-'+m.t.sha(m.t.canon(page))[:24]+'-';starts=w.glob(prefix+'*.start.json')
  for sp in starts:
   start=json.loads(w.read(sp.name)); assert proof.unknown(start['provenance'],j,page) is True
   result=sp.name.replace('.start.json','.result.json');assert w.exists(result); x=json.loads(w.read(result)); assert x['status']==200 and x['request_sha256']==start['body_sha256'] and x['start_sha256']==hashlib.sha256(w.read(sp.name)).hexdigest() and x['response_sha256']==hashlib.sha256(bytes.fromhex(x['body_hex'])).hexdigest()
   out.append({'index':page['index'],'start_path':str(sp),'start_sha256':hashlib.sha256(w.read(sp.name)).hexdigest(),'result_path':str(w.lookup(result)),'result_sha256':hashlib.sha256(w.read(result)).hexdigest(),'capture_sha256':start['provenance']['origin_capture_sha256'],'http_status':x['status']})
assert len(out)==5
print(json.dumps({'scope':'read-only verification of original region capture/source/request/response, not page completion','regions':out},indent=2))
