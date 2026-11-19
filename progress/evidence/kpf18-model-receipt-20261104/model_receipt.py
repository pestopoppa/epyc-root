"""Verify pre-grant identity receipt; never open model weights."""
import hashlib
import json
import os
import re
import stat

ROLES = ('target', 'drafter')
def signature(path):
    s = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(s.st_mode):
        raise ValueError('model path is not a regular file: ' + str(path))
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]

def draft_shape(record):
    meta=record['metadata'];arch=meta.get('general.architecture')
    if not isinstance(arch,str) or 'dflash' not in arch.lower():raise ValueError('native drafter architecture unproved')
    layers=meta.get(arch+'.block_count');window=meta.get(arch+'.attention.sliding_window')
    pattern=meta.get(arch+'.attention.sliding_window_pattern')
    if layers!=5 or window!=2048:raise ValueError('not exact five-layer2048 drafter')
    if isinstance(pattern,int):pattern=[pattern]*layers
    if pattern!=[True]*layers:raise ValueError('all-five SWA layer pattern unproved')
    return {'draft_base_layers':0,'draft_swa_layers':5,'source':'a1 dflash.cpp258-264 + actual GGUF fields','metadata':meta}

def load_verified(path, pinned_sha256, paths, original):
    if not re.fullmatch(r'[0-9a-f]{64}', pinned_sha256):
        raise ValueError('invalid pinned receipt digest')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        raw = f.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != pinned_sha256:
        raise ValueError('model receipt altered or oversized')
    data = json.loads(raw)
    if set(data) != {'target', 'drafter', 'draft_cache_shape'} or set(paths) != set(ROLES):
        raise ValueError('model receipt roles invalid')
    for role in ROLES:
        item = data[role]
        if item['path'] != str(paths[role]) or any(item[k] != original[role][k] for k in ('path', 'sha256')):
            raise ValueError('model receipt identity mismatch: ' + role)
        if signature(paths[role]) != item['stat_identity']:
            raise ValueError('model file stat changed since pre-grant receipt: ' + role)
    if draft_shape(data['drafter']) != data['draft_cache_shape']:
        raise ValueError('drafter shape receipt mismatch')
    return data
