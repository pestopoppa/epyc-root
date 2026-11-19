import json,shlex
from pathlib import Path
p=json.loads((Path(__file__).resolve().parent/'pins.json').read_text())['env']
for k,v in p.items():
 assert k in ('KVU19A2_BUILD_RECEIPT_SHA256','KVU19A2_EXE_SHA256','KVU19A2_HARNESS_RECEIPT_SHA256') and len(v)==64 and all(c in '0123456789abcdef' for c in v)
 print(f'{k}={shlex.quote(v)}')
