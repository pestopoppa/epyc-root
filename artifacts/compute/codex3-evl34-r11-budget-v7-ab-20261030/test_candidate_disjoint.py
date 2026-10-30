import hashlib,json
from pathlib import Path
import pyarrow.parquet as pq
p=Path('/mnt/raid0/llm/tmp/codex3-evl34-deepdive-prep-20261030/qa_rl.parquet');t=pq.read_table(p,columns=['id','question','answer']);rows=t.slice(0,50).to_pylist();assert len(rows)==50
h=lambda x:hashlib.sha256(x.encode()).hexdigest()
oldid={str(r['id']) for r in rows[:39]};oldq={h(r['question']) for r in rows[:39]};oldpair={(h(r['question']),h(r['answer'])) for r in rows[:39]}
new=rows[39:50];assert len({str(r['id']) for r in new})==11 and len({h(r['question']) for r in new})==11
assert all(str(r['id']) not in oldid and h(r['question']) not in oldq and (h(r['question']),h(r['answer'])) not in oldpair for r in new)
print('PASS: source indices 39-49 have unique ids and question hashes, disjoint from all source-order 0-38; no private content emitted')
