"""Pre-grant only: hash model weights, print receipt digest for launcher pinning."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from gguf_identity import metadata
from model_receipt import ROLES, draft_shape, signature

def prepare(paths, original, output):
    if set(paths) != set(ROLES) or set(original) != set(ROLES):
        raise ValueError('exact target/drafter roles required')
    result = {}
    for role in ROLES:
        path = Path(paths[role])
        if not path.is_absolute() or path.is_symlink():
            raise ValueError('absolute regular model path required')
        before = signature(path)
        item = metadata(path)
        if item['stat_identity'] != before or signature(path) != before:
            raise ValueError('model changed during pre-grant receipt')
        if any(item[k] != original[role][k] for k in ('path', 'sha256')):
            raise ValueError('original model identity mismatch: ' + role)
        result[role] = item
    result['draft_cache_shape'] = draft_shape(result['drafter'])
    raw = (json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n').encode()
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--original-models', type=Path, required=True)
    p.add_argument('--target', type=Path, required=True)
    p.add_argument('--drafter', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args()
    print(prepare({'target':a.target,'drafter':a.drafter},json.loads(a.original_models.read_text()),a.output))

if __name__=='__main__': main()
