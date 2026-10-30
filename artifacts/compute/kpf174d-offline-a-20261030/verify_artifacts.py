#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
out=Path('/mnt/raid0/llm/tmp/codex3-kpf174d-offline-a-20261030')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
v=json.loads((out/'verdict.json').read_text())
c=json.loads((out/'custody.json').read_text())
assert v['result']=='CONTROL_LAYOUT_NUMERICS'
assert v['scope']=='KPF-17.4b spec-off g2-c2148 only'
assert c['prepared_artifacts_sha256']['verdict.json']==sha(out/'verdict.json')
assert c['prepared_artifacts_sha256']['handoff-child-proposed.md']==sha(out/'handoff-child-proposed.md')
assert c['prepared_artifacts_sha256']['progress-proposed.md']==sha(out/'progress-proposed.md')
assert c['prepared_artifacts_sha256']['derive.py']==sha(out/'derive.py')
lines=(out/'INPUTS.sha256').read_text().splitlines()
assert len(lines)==len(c['source_artifacts_sha256'])
for line in lines:
 digest,path=line.split('  ',1)
 assert sha(path)==digest,(path,digest)
assert '[x] **KPF-17.4d(a)' in (out/'handoff-child-proposed.md').read_text()
assert '✅ 2026-10-30 [belief: cc]' in (out/'handoff-child-proposed.md').read_text()
context=json.loads((out/'source-context/ROOT-SOURCE-CONTEXT.json').read_text())
assert context['root_commit']=='7edab852fb2e2718d540763f962c408d8a8fc1d7'
assert len(context['snapshots'])==2
assert '[belief: cc]' in (out/'progress-proposed.md').read_text()
assert c['already_filed_check']['fully_qualified_A_filing_found'] is False
print(json.dumps({'status':'verified','inputs':len(lines),'outputs':len(c['prepared_artifacts_sha256']),'result':v['result']},sort_keys=True))
