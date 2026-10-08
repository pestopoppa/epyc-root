import json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
for name,wanted in json.loads((p/"source-pins.json").read_text()).items():
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==wanted,name
