# Restoring original failure evidence

The lifecycle captures contain nanosecond file timestamps. The Q38P4 r1 smoke captured Linux TCP rows and memory mappings. The account-number check matched numeric fields in those records. Their bytes are preserved in `epyc.original_bytes.v1` envelopes with the original filename, SHA-256 digest, and base64 payload.

| Archive directory under `data/vidya/` | Original filenames |
| --- | --- |
| `native-wiring-failures-20261118/vb-v9-8-lifecycle-native-20261118/` | `pins.json` |
| `native-wiring-failures-20261118/vb-v9-8-lifecycle-native-20261118/resident/` | `capture.json` |
| `q38p4-parity-native-20261118/r1-failed/smoke/attempt-e83_6bdo/capture/llama/` | `listener-after`, `listener-before`, `listener-cleanup`, `maps-824913.txt` |

Each envelope is beside its former archive path and appends `.original-bytes.json` to the original filename. Run this from the repository root to decode into a scratch directory with the same relative paths. It verifies each digest before writing the file.

```bash
replay=$(mktemp -d)
python3 - "$replay" <<'PY'
from base64 import b64decode
from hashlib import sha256
import json
from pathlib import Path
import sys

replay = Path(sys.argv[1])
lifecycle = Path('data/vidya/native-wiring-failures-20261118/vb-v9-8-lifecycle-native-20261118')
parity = Path('data/vidya/q38p4-parity-native-20261118/r1-failed/smoke/attempt-e83_6bdo/capture/llama')
originals = [lifecycle / 'pins.json', lifecycle / 'resident/capture.json']
originals.extend(parity / name for name in (
    'listener-after', 'listener-before', 'listener-cleanup', 'maps-824913.txt',
))
for original in originals:
    envelope = original.with_name(original.name + '.original-bytes.json')
    record = json.loads(envelope.read_bytes())
    if (record['schema'], record['encoding'], record['original_name']) != (
        'epyc.original_bytes.v1', 'base64', original.name,
    ):
        raise ValueError(f'Unexpected envelope metadata in {envelope}')
    raw = b64decode(record['bytes_b64'], validate=True)
    if sha256(raw).hexdigest() != record['sha256']:
        raise ValueError(f'SHA-256 mismatch in {envelope}')
    target = replay / original
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
print(replay)
PY
```
