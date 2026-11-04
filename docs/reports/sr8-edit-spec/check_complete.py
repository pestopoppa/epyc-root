import json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr8-edit-spec/live/RESULT.json')
x=json.loads(p.read_text())
assert x['state']=='COMPLETE' and x['analysis']['n_pairs']==5
