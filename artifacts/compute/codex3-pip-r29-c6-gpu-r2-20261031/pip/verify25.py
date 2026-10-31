import contextlib,io,importlib.util,json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');spec=importlib.util.spec_from_file_location('inspect_pip',p);m=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(m)
paths=list(Path('/mnt/micron/codex3-pip-head-r26-20261030/attempts').glob('*/capture.json'))+list(Path('/mnt/micron/codex3-pip-split-r22-20261030/attempts').glob('*/capture.json'));proof=m.t.NativeProof(paths,m.config['campaign'],m.raw);out=[]
for shard in (0,1,2,3,4):
 roots=[f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-head-r26-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}'];w=m.Read(roots);j=m.j.Journal(w,m.config['campaign'])
 for page in m.plan['pages'][5*shard:5*shard+5]:out.append({'index':page['index'],'journal_complete':j.state(page)=='complete','native_finish_proof':proof.complete(j,page)})
print(json.dumps({'scope':'25 native page journal/capture checks','pages':out},indent=2))
