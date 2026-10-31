#!/usr/bin/env python3
"""Summarize CPU capture without treating it as completion of KPF-18.1."""
import json,os
from pathlib import Path
from aggregate_c import aggregate
D=Path('/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240'); root=D/'full'
records=[json.loads(p.read_text()) for p in sorted((root/'records').glob('*.json'))]
expected=list(range(2048,4096,128))
c=aggregate(records,expected)
result={'schema':'epyc.kpf181.cpu-subset.v1','partial':False,'task_gate_complete':False,
        'scope':'CPU Qwen3.6-35B Q8 MTP and no-drafter; GPU DFlash2 not run',
        'record_paths':[str(p) for p in sorted((root/'records').glob('*.json'))],
        'champion_record_paths':[str(p) for p in sorted((D/'champion'/'records').glob('*.json'))],
        'C':c,'unknown':'GPU DFlash2 and unexposed/missing native fields',
        'gate_note':'Original full KPF-18.1 criteria remain open; no cross-model pooling.'}
if not result['champion_record_paths']:raise SystemExit('champion control produced no records')
tmp=root/'RESULT.json.tmp'
with tmp.open('w') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
os.replace(tmp,root/'RESULT.json')
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
