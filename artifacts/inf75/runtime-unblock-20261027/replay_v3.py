from pathlib import Path
from types import SimpleNamespace
import json
import server_evidence_full as ev
p=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-host-excluding/v3/out/1793132121714157253')
log=next(p.glob('*prefill.log')).read_bytes()
offset=json.loads(next(p.glob('*prefill.requests.json')).read_text())['phase_log_byte_offset']
startup=log[:offset].decode(errors='replace'); phase=log[offset:].decode(errors='replace')
graph=ev.graph_evidence(startup+phase,phase,'/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
shape=SimpleNamespace(phase='prefill',n_tokens=2048,n_seq=1)
assert not ev.tensor_shape_observed(shape,graph)
description=ev.split_prefill_description(shape,graph)
assert description['observed_split_prefill']
assert any([x['tokens'] for x in w['batches']] == [4,2044] for w in description['witnesses'])
missing={'graphs':[g for g in graph['graphs'] if g['decode_id'] != 5]}
assert not ev.split_prefill_description(shape,missing)['observed_split_prefill']
print('V3_RAW_DIAGNOSTIC_REPLAY strict=false split=4+2044 missing_intervening=false; no new observation')
