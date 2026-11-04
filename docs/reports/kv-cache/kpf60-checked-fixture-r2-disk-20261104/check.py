import hashlib, json
from pathlib import Path
D=Path(__file__).resolve().parent
items=json.loads((D/'inputs.json').read_text())
for name, expected in items.items():
 p=Path(name) if name.startswith('/') else D/name
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
  raise SystemExit('input changed: '+name)
