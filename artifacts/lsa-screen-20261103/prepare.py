#!/usr/bin/env python3
"""Deterministic cohort definitions; token-ID freezing requires verified model tokenizer."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
rows=[]
for split in ('dev','heldout'):
 for group in ('code','multihop','document_qa','agent_history'):
  for i in range(8):
   ident=f'{split}-{group}-{i:02d}'
   h=hashlib.sha256(ident.encode()).hexdigest()
   a,b=int(h[:4],16)%97+2,int(h[4:8],16)%89+2
   marker='K'+h[8:20].upper()
   if group=='code':
    evidence=f'File {ident}.py: def transform_{h[:8]}(x): return (x + {a}) * {b}\n'
    question=f'What integer does transform_{h[:8]}(3) return? Reply with only the integer.'
    answer=str((3+a)*b)
   elif group=='multihop':
    evidence=[f'Ledger {ident}: crate {marker} uses pack type P{h[20:26]}.\n', f'Catalog: pack type P{h[20:26]} contains {b} units.\n', f'Manifest: crate {marker} holds {a} packs.\n']
    question=f'How many units are in crate {marker}? Reply with only the integer.'
    answer=str(a*b)
   elif group=='document_qa':
    evidence=f'Document {ident}: the archive accession for project {marker} is {a}-{b}-{h[20:26].upper()}.\n'
    question=f'What is the archive accession for project {marker}? Reply with only the accession.'
    answer=f'{a}-{b}-{h[20:26].upper()}'
   else:
    evidence=f'Agent history {ident}: the operator instructed the agent to use checkpoint {marker} for the final export.\n'
    question='Which checkpoint did the operator specify for the final export? Reply with only the checkpoint.'
    answer=marker
   rows.append(dict(id=ident,split=split,group=group,position=('early','middle','late')[i%3],evidence=evidence,question=question,answer=answer,exact_sentinel=group in ('document_qa','agent_history'),source_id=ident))
assert len(rows)==64 and len({r['source_id'] for r in rows})==64
(P/'cohort.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
