#!/usr/bin/env python3
"""Only the final native result constitutes progress."""
import json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/triattention-s8c-api-params2-20261104/native/RESULT.json')
try:
 d=json.loads(p.read_text()); assert d['unit']=='s8c-real-api' and d['status'] in ('pass','fail','inconclusive')
except (OSError,ValueError,AssertionError,KeyError):raise SystemExit(1)
