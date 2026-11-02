#!/usr/bin/env python3
"""Fixture prototype: fail closed on changing inputs; not an atomic FS snapshot."""
import argparse, datetime, hashlib, json, math, os, shutil, stat, sys, tempfile
from pathlib import Path


def sha(data): return hashlib.sha256(data).hexdigest()
def signature(st): return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
def read_stable(path):
    # O_NOFOLLOW prevents replacing a selected file with a symlink.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise ValueError(f'not regular: {path}')
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(fd, min(1048576, remaining))
            if not chunk: raise ValueError(f'short read: {path}')
            chunks.append(chunk); remaining -= len(chunk)
        data = b''.join(chunks)
        if signature(before) != signature(os.fstat(fd)): raise ValueError(f'changed: {path}')
        os.lseek(fd, 0, os.SEEK_SET)
        h = hashlib.sha256()
        while True:
            b = os.read(fd, 1048576)
            if not b: break
            h.update(b)
        if signature(before) != signature(os.fstat(fd)) or sha(data) != h.hexdigest(): raise ValueError(f'changed: {path}')
        if signature(before) != signature(os.stat(path, follow_symlinks=False)): raise ValueError(f'replaced: {path}')
        return data, before
    finally: os.close(fd)

def put(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())

def roles(data):
    obj = json.loads(data)
    mapping = obj['roles']
    if not isinstance(mapping, dict) or not mapping: raise ValueError('roles must be a nonempty object')
    out = []
    for name, v in sorted(mapping.items()):
        if not isinstance(name, str) or not name or not isinstance(v, dict): raise ValueError('invalid role')
        p, q = v.get('p50_s'), v.get('p90_s')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (p, q)) or p <= 0 or q < p: raise ValueError('invalid baseline')
        out.append(name)
    return (json.dumps(out, indent=2) + '\n').encode()

def names(path): return sorted(p.name for p in Path(path).glob('*.jsonl'))
def snapshot(args):
    os.umask(0o077)
    root = Path(tempfile.mkdtemp(prefix='private-audit-', dir=args.parent))
    try:
        src = Path(args.progress).resolve(strict=True)
        selected = names(src)
        if not selected: raise ValueError('no progress files')
        (root/'progress').mkdir(mode=0o700); (root/'provenance').mkdir(mode=0o700)
        records = []
        for name in selected:
            data, st = read_stable(src/name)
            if data and not data.endswith(b'\n'): raise ValueError(f'incomplete JSONL line: {name}')
            put(root/'progress'/name, data)
            records.append({'name':name, 'size':len(data), 'sha256':sha(data), 'source_dev':st.st_dev, 'source_ino':st.st_ino, 'source_mtime_ns':st.st_mtime_ns, 'source_ctime_ns':st.st_ctime_ns})
        if names(src) != selected: raise ValueError('progress file selection changed during capture')
        for rec in records:
            st = os.stat(src/rec['name'], follow_symlinks=False)
            if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != (rec['source_dev'], rec['source_ino'], rec['size'], rec['source_mtime_ns'], rec['source_ctime_ns']): raise ValueError('progress changed before capture completed')
        baseline, baseline_st = read_stable(args.baseline)
        provenance, provenance_st = read_stable(args.provenance)
        info = json.loads(provenance)
        if not isinstance(info, dict) or not info: raise ValueError('provenance must be a nonempty object')
        derived = roles(baseline)
        # Recheck every source after all reads; this detects changes, not an atomic snapshot.
        if names(src) != selected: raise ValueError('progress selection changed')
        for rec in records:
            st = os.stat(src/rec['name'], follow_symlinks=False)
            if signature(st) != (rec['source_dev'], rec['source_ino'], rec['size'], rec['source_mtime_ns'], rec['source_ctime_ns']): raise ValueError('progress changed')
        for path, st in ((args.baseline, baseline_st), (args.provenance, provenance_st)):
            if signature(os.stat(path, follow_symlinks=False)) != signature(st): raise ValueError('configuration changed')
        put(root/'provenance'/'baseline.json', baseline); put(root/'provenance'/'scorer-config.json', provenance)
        put(root/'baseline-roles.json', derived)
        manifest = {'schema':1, 'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'selection':{'directory':str(src),'glob':'*.jsonl','cutoff':'complete files unchanged at sampled checks through final source recheck; not atomic; no event-time cutoff','files':records}, 'artifacts':{'provenance/baseline.json':sha(baseline),'provenance/scorer-config.json':sha(provenance),'baseline-roles.json':sha(derived)}, 'limitations':'Configuration is supplied, not independently attested. Source is not an atomic filesystem snapshot.'}
        put(root/'manifest.json', (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode())
        # Read-only modes protect against accidental edits; the owner can reverse them.
        for directory, _, files in os.walk(root):
            for name in files: os.chmod(Path(directory)/name, 0o400)
        for directory, _, _ in os.walk(root, topdown=False): os.chmod(directory, 0o500)
        print(root)
    except BaseException:
        for directory, _, _ in os.walk(root): os.chmod(directory, 0o700)
        shutil.rmtree(root)
        raise

def verify(args):
    root = Path(args.snapshot)
    for directory in (root, root/'progress', root/'provenance'):
        if not stat.S_ISDIR(os.stat(directory, follow_symlinks=False).st_mode): raise ValueError('invalid snapshot directory')
    manifest_data, _ = read_stable(root/'manifest.json')
    manifest = json.loads(manifest_data)
    entries = manifest['selection']['files']
    expected = set()
    for item in entries:
        name = item['name']
        if not isinstance(name, str) or Path(name).name != name or not name.endswith('.jsonl') or name in expected:
            raise ValueError('invalid manifest selection')
        expected.add(name)
    if not expected or set(names(root/'progress')) != expected: raise ValueError('progress selection mismatch')
    for item in entries:
        data, _ = read_stable(root/'progress'/item['name'])
        if len(data) != item['size'] or sha(data) != item['sha256']: raise ValueError('progress digest mismatch')
    artifacts = manifest['artifacts']
    if set(artifacts) != {'provenance/baseline.json', 'provenance/scorer-config.json', 'baseline-roles.json'}:
        raise ValueError('invalid manifest artifacts')
    for name, digest in artifacts.items():
        data, _ = read_stable(root/name)
        if sha(data) != digest: raise ValueError('artifact digest mismatch')
    print('verified')

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('capture'); s.add_argument('--parent', required=True); s.add_argument('--progress', required=True); s.add_argument('--baseline', required=True); s.add_argument('--provenance', required=True); s.set_defaults(func=snapshot)
    v = sub.add_parser('verify'); v.add_argument('snapshot'); v.set_defaults(func=verify)
    a = p.parse_args(); a.func(a)
if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, KeyError, TypeError, OverflowError): print('error: snapshot operation failed', file=sys.stderr); sys.exit(1)
