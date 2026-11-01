from pathlib import Path
import hashlib
base=Path('/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-tc-r2-20261030')
catalog=base/'SOURCE-SHA256SUMS'
needed={'PLAN.md','PROFILE.md','INPUT-PINS.json','nemo_job.py','nemo_tokens.py','vocab.json','chunk_materialize.py','long_chunk_plan.py','score_validation.py'}
found={}
for line in catalog.read_text().splitlines():
 h,name=line.split('  ',1); p=Path(name)
 if p.parent == base and p.name in needed:
  actual=hashlib.sha256(p.read_bytes()).hexdigest(); assert actual==h,p.name
  found[p.name]=actual
assert set(found)==needed,(needed-set(found))
print('source catalog:',hashlib.sha256(catalog.read_bytes()).hexdigest())
print('verified pinned native caller, plan, input pins and relevant scoring helpers:',len(found))
