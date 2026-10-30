from pathlib import Path
import json,hashlib
from partial_assessment import assess
p=Path('/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r11-budget-v6-20261030');j=Path('/mnt/micron/codex3-evl34-deepdive-r11-budget-v6-20261030/pilot/pilot-journal');a=j.parent/'campaign-pilot-1793397283007158126'
dec=(p/'PREDECLARATION-FROZEN.json').read_bytes();manifest=json.loads((p/'FROZEN-PROMPT-MANIFEST.json').read_bytes());rows=json.loads((p/'PILOT-PRIVATE.json').read_bytes())['rows']
r=assess(j,a,hashlib.sha256(dec).hexdigest(),rows,manifest['pilot'])
assert r['arms']['production_repl']['correct_bounds']==[0,0]
assert r['arms']['redel_delegate_wait']['correct_bounds']==[0,6]
assert r['paired_complete']==4 and r['matched_case_ids']==['11','12','13','14','15','16','19']
assert r['delegation_unknown_case_ids']==['20'] and r['step3_gate_passed'] is False
print('PASS: original 14 complete, 6 unknown, matched 7 and unresolved absence 1; no private data printed')
