from pathlib import Path
from collections import Counter
import json
out=Path('/mnt/raid0/llm/tmp/codex3-stt5-tc-rescore-20261101/derived')
d=json.loads((out/'validation-score.json').read_text()); cells=d['cells']; assert len(cells)==64
for m in ('r0','r3','r6','r13'):
 for mode in ('auto','forced'):
  raw=json.loads((out/f'raw-{m}-{mode}.json').read_text())['rows']; assert len(raw)==1437
  print(m,mode,'rows',len(raw),'statuses',dict(Counter(r['decode_status'] for r in raw)),'unk_evidence_unknown',sum(r['unk_count_unknown'] for r in raw))
  for norm in ('v1','v2'):
   for lang,n in [('en',394),('it',391),('de',363),('fr',289)]:
    cell=cells[f'{m}|{mode}|stt_norm/{norm}|{lang}']; assert cell['n']==n and sum(cell['classes'].values())==n
print('validated 64 score cells, per-language denominators and class totals')
