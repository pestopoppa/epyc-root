#!/usr/bin/env python3
"""Qualify only after a fresh, generated model token; not a startup message."""
import json,os
from pathlib import Path
root=Path(os.environ['FILLER_STATE_DIR']).parent/'native'
try:
 if 'FILLER_SMOKE_T0' not in os.environ:
  result=json.loads((root/'RESULT.json').read_text());assert result['status'] in ('pass','failure') and result['unit']=='dense-bf16-dev-8204';raise SystemExit(0)
 files=list(root.glob('attempt-*/first-token.json'));stamp=float(os.environ['FILLER_SMOKE_T0'])
 assert any(p.stat().st_mtime>=stamp and json.loads(p.read_text()).get('unit')=='dense-first-token' for p in files)
except (OSError,KeyError,ValueError,AssertionError):raise SystemExit(1)
