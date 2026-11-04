import json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/vb-ak-wire-canary-r1-20261104/RESULT.json')
raise SystemExit(0 if p.exists() and json.loads(p.read_text()).get('status') in ('PASS','FAIL','UNKNOWN') else 1)
