#!/usr/bin/env python3
import json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 p=Path(sys.argv[1]);r=json.loads(p.read_text());q=sys.argv[2]=='qualification'
 assert r['id']=='handoff-kvu19b-gap-clean-20261104'
 assert r['status']==('qualified_four_cpu' if q else 'completed_descriptive')
 assert r['qualification']==q and r['affinity']['count']==(4 if q else 8)
 assert len(r['rows'])==(2 if q else 12)
 for row in r['rows']:
  assert row['rc']==0 and row['cleanup']['verified_dead'] is True
  assert row['metrics']['ms_per_step']>0
  assert len([s for s in row['samples'] if s['own_vram_b']>0 and all(v for k,v in s['mapped_libraries'].items() if k.startswith('libggml'))])>=2
  assert Path(row['stdout']).is_file() and Path(row['stderr']).is_file()
except Exception as e:
 print('incomplete/refused:',repr(e),file=sys.stderr);sys.exit(1)
