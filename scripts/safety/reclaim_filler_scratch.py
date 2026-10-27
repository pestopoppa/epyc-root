#!/usr/bin/env python3
"""Stage completed filler scratch files to normal trash; default is dry run.

This deliberately refuses uncertain custody, active references and symlinks.
It never purges, follows links, removes a directory, or bypasses guarded_rm.
"""
import argparse
import fnmatch
import glob
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'coordination'))
import validate_fillers as vf

FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags/FILLERS.md')
SCRATCH = Path('/mnt/raid0/llm/tmp')
TRASH = Path('/mnt/raid0/llm/.trash')
GUARD = Path(__file__).with_name('guarded_rm.sh')
HANDOFFS = Path('/workspace/handoffs/active')
GRANTS = Path('/mnt/raid0/llm/tmp/compute-flags/grants')

def fields(notes):
    out = {}
    for part in notes.split(';'):
        if '=' in part:
            key, value = part.strip().split('=', 1)
            if key in ('scratch_root', 'raw_globs', 'keep_globs'):
                if key in out: raise ValueError('duplicate retention field')
                out[key] = value.strip()
    return out

def patterns(root, value):
    result = []
    for token in value.split(','):
        token = token.strip()
        if not token or token in ('-', 'none', '[]'): continue
        p = Path(token) if token.startswith('/') else root / token
        if '..' in p.parts or not p.is_relative_to(root): raise ValueError('glob outside scratch root: ' + token)
        result.append(str(p))
    return result

def no_symlinks(path, root):
    p = root
    for part in path.relative_to(root).parts:
        p = p / part
        if p.is_symlink(): raise ValueError('symlink in selected path: ' + str(p))

def no_keep_marker(path, root):
    if path.name in ('KEEP', '.KEEP', 'KEEP.md'):
        raise ValueError('explicit KEEP marker: ' + str(path))
    current = path.parent
    while True:
        for name in ('KEEP', '.KEEP', 'KEEP.md'):
            if os.path.lexists(current / name): raise ValueError('KEEP marker protects path: ' + str(current / name))
        if current == SCRATCH: break
        if current == current.parent or not current.is_relative_to(SCRATCH): raise ValueError('path escaped scratch')
        current = current.parent

def no_holders(root):
    """Refuse on an inaccessible process, cwd/fd/exe or mapped object in root."""
    prefix = str(root) + '/'
    def inside(s): return s == str(root) or s.startswith(prefix)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid(): continue
        try:
            for name in ('cwd', 'exe'):
                try: target = os.readlink(proc / name)
                except FileNotFoundError: continue
                if inside(target): raise ValueError('live holder: ' + str(proc / name))
            for fd in (proc / 'fd').iterdir():
                try: target = os.readlink(fd)
                except FileNotFoundError: continue
                if inside(target): raise ValueError('live holder: ' + str(fd))
            for line in (proc / 'maps').read_text().splitlines():
                parts = line.split(None, 5)
                if len(parts) == 6 and inside(parts[5]): raise ValueError('live mapped holder: ' + str(proc))
            for name in ('cmdline', 'environ'):
                data = (proc / name).read_bytes().replace(b'\0', b' ')
                if str(root).encode() in data: raise ValueError('live process references scratch: ' + str(proc / name))
        except FileNotFoundError:
            continue  # process exited
        except PermissionError as e:
            raise ValueError('cannot prove holder scan complete: ' + str(e)) from e

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('row_id'); ap.add_argument('--apply', action='store_true'); a = ap.parse_args()
    text = FLAGS.read_text(); col, rows, _ = vf.parse_table(text)
    matches = [c for _, c in rows if c and c[0] == a.row_id]
    if len(matches) != 1 or len(matches[0]) != len(vf.COLUMNS): raise ValueError('row absent, duplicate or malformed')
    row = matches[0]
    if row[col['status']] not in ('COMPLETE', 'CANCELLED'): raise ValueError('row is not terminal')
    f = fields(row[col['notes']]); issues = vf.scratch_retention_violations(row[col['notes']])
    if issues or not f.get('scratch_root'): raise ValueError('retention declaration: ' + '; '.join(issues))
    root = Path(f['scratch_root'])
    if root == SCRATCH or not root.is_relative_to(SCRATCH) or root.is_symlink() or root.resolve(strict=True) != root: raise ValueError('invalid scratch root')
    raw, keep = patterns(root, f.get('raw_globs', '')), patterns(root, f.get('keep_globs', ''))
    for grant in GRANTS.glob('*.grant'):
        if grant.stem == a.row_id or str(root) in grant.read_text(errors='replace'):
            raise ValueError('open grant references row or scratch: ' + str(grant))
    for _, other in rows:
        if len(other) == len(vf.COLUMNS) and other[0] != a.row_id and other[col['status']] not in ('COMPLETE', 'CANCELLED') and str(root) in ' '.join(other):
            raise ValueError('nonterminal queue row references scratch: ' + other[0])
    for path in HANDOFFS.rglob('*.md'):
        if str(root) in path.read_text(errors='replace'): raise ValueError('active handoff references scratch: ' + str(path))
    selected = set()
    for pattern in raw:
        for name in glob.iglob(pattern, recursive=True):
            p = Path(name)
            if not p.is_relative_to(root) or p == root: raise ValueError('glob escaped root')
            no_symlinks(p, root)
            if '.git' in p.relative_to(root).parts: raise ValueError('git dependency in raw selection: ' + str(p))
            if p.is_file() and not any(fnmatch.fnmatchcase(str(p), k) for k in keep):
                no_keep_marker(p, root)
                if p.stat().st_dev != root.stat().st_dev: raise ValueError('cross-device file: ' + str(p))
                if p.stat().st_nlink != 1: raise ValueError('hard-linked file: ' + str(p))
                selected.add(p)
    no_holders(root)
    identities = {p: (p.stat().st_dev, p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in selected}
    total = sum(p.stat().st_blocks * 512 for p in selected)
    print(f'{a.row_id}: {len(selected)} files, {total / 1e9:.3f} GB allocated; ' + ('stage' if a.apply else 'dry run'))
    for p in sorted(selected): print(p)
    if not a.apply or not selected: return
    # One isolated trash container per file prevents guarded_rm basename collisions.
    batch = Path(tempfile.mkdtemp(prefix='filler-reclaim-', dir=TRASH))
    for i, p in enumerate(sorted(selected)):
        no_holders(root); no_symlinks(p, root); no_keep_marker(p, root)
        st = p.stat()
        if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != identities[p]: raise ValueError('file changed; partial batch retained: ' + str(p))
        item = batch / f'item-{i:06d}'; item.mkdir(mode=0o700)
        subprocess.run(['bash', str(GUARD), str(p)], env={**os.environ, 'TRASH_ROOT': str(item)}, check=True)
    print('staged to normal trash:', batch)

if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, vf.Malformed, subprocess.CalledProcessError) as e:
        print('REFUSED:', e, file=sys.stderr); sys.exit(1)
