import json
from pathlib import Path
try:
    x=json.loads(Path('/mnt/raid0/llm/tmp/evl46-live-unit-20261102/result.json').read_text())
    ok=x.get('schema')=='dtap.crm_live_source_tests.v1' and x.get('capture_kind')=='source-test' and x.get('passed',0)>=30 and x.get('model_invoked') is False
except (OSError,ValueError):
    ok=False
raise SystemExit(0 if ok else 1)
