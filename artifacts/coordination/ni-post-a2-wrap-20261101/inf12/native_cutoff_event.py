"""Emit a cutoff trigger only after a live native HF first-result sidecar."""
import json
import os
import pathlib
import sys

first = json.loads(pathlib.Path(sys.argv[1]).read_text())
path = pathlib.Path(sys.argv[2]); nonce = sys.argv[3]
if path.exists(): raise SystemExit('cutoff event already exists')
pid, birth = first['native_pid'], first['native_birth_ticks']
stat = pathlib.Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
if int(stat[19]) != birth or stat[0] == 'Z': raise SystemExit('native child not alive at cutoff event')
manifest = json.loads(pathlib.Path(os.environ['WS58_MANIFEST_PATH']).read_text())
event = {'id': manifest['id'], 'nonce': nonce, 'phase': 'cutoff',
         'native_pid': pid, 'native_birth_ticks': birth,
         'native_first_event': True, 'first_request': first}
path.parent.mkdir(parents=True, exist_ok=True)
tmp = path.with_suffix(path.suffix + '.tmp.' + str(os.getpid()))
with tmp.open('x') as f:
    json.dump(event, f, sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
os.link(tmp, path); tmp.unlink()
