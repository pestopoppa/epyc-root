import json
from pathlib import Path
try:
    d=json.loads((Path(__file__).resolve().parent/'RESULT.json').read_text())
    assert d['coverage_qualified'] is True and d['cleanup']['verified_dead'] is True
    assert d['target_kv_b_from_log']>0 and Path(d['artifacts']['belief_sidecar']).is_file()
except (OSError,ValueError,KeyError,AssertionError):raise SystemExit(1)
