#!/usr/bin/env python3
"""Require a real native model callback trace written by this smoke invocation."""
import json,os,time
from pathlib import Path
candidates=list((Path(os.environ['FILLER_STATE_DIR']).parent/'native').glob('attempt-*/trace.jsonl'))
p=max(candidates,key=lambda p:p.stat().st_mtime) if candidates else Path('/nonexistent')
try:
 if 'FILLER_SMOKE_T0' not in os.environ:
  result=json.loads((p.parent/'RESULT.json').read_text());assert result['status']=='pass' and result['unit']=='window-exact-retrieval-8204';raise SystemExit(0)
 assert p.stat().st_mtime>=float(os.environ['FILLER_SMOKE_T0'])
 rows=[json.loads(line) for line in p.read_text().splitlines()]
 assert any(r['layer'] in range(3,64,4) and r['queries']>0 and r['allowed_before']>0 for r in rows)
except (OSError,ValueError,AssertionError,KeyError):raise SystemExit(1)
