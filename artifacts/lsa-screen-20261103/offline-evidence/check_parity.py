import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts/vidya'))
from adapters import research_screen
base = ROOT/'artifacts/lsa-screen-20261103'
result = []
for name in ('booking-cpu-parity', 'booking-cpu-parity-r2', 'booking-cpu-parity-r3'):
    path = base/name/'ATTEMPT_FENCE/parity-conformance.raw.json.research-screen.json'
    rows = research_screen.native_rows(path)
    claim = research_screen.project(rows[0])
    result.append({'receipt': str(path), 'metric':claim.metric, 'value':claim.value, 'reader':'accepted'})
(Path(__file__).parent/'parity-custody-check.json').write_text(json.dumps(result, indent=2)+'\n')
