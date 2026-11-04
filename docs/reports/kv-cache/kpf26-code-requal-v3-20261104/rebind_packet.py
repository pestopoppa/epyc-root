#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-code-requal-v3-20261104'); packet=Path(sys.argv[1]);port=int(sys.argv[2]);root=(D/'scope-path.txt').read_text().strip();cohort=json.loads((D/'cohort-manifest.json').read_text());mpath=packet/'manifest.json';m=json.loads(mpath.read_text());task=m['tasks'][0]
def update(ref,change):
 p=packet/ref['path']; obj=json.loads(p.read_text()); change(obj); raw=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();p.write_bytes(raw);ref['sha256']=hashlib.sha256(raw).hexdigest();return obj
spec={'enabled':True,'max':3,'max_turns':1,'budget_s':600,'reserve_slots':1,'summary_tokens':400,'targets':cohort['targets']}
update(task['request'],lambda x:x.update(scope_root=root,scope_files=cohort['scope_files_sha256'],spec=spec))
# These substring checks merely diagnose whether relevant words occur, not outcome correctness.
update(task['expected'],lambda x:x.update(schema='epyc.kpf26.scorer.required-terms.v1',required_terms=[['trunk','prefill'],['fork'],['unified']]))
update(m['api_request'],lambda x:x.update(task_root=root,server_urls={'frontdoor':f'http://127.0.0.1:{port}'},prompt=cohort['task'],scouts=spec,timeout_s=1800))
task['id']='prospective-real-code-fanout';task['siblings']=3
m['provenance']={'kind':'prospective-real-code-three-scout-diagnostic','source_commit':cohort['source_commit'],'cohort_sha256':hashlib.sha256((D/'cohort-manifest.json').read_bytes()).hexdigest(),'interpretation':'Newly constructed tasks over real pinned source with a synthetic long root. Required-term scoring is a keyword diagnostic only. Not historical traffic or a KPF-26 gate.'}
mpath.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
