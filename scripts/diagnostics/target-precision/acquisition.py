"""Pinned matched-source acquisition, outside inference grants.

Run only as a dedicated process: admission joins a preconfigured delegated
cgroup before opening any network stream. No cgroup limits are changed here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import time
import urllib.request

import preparation as prep

GIB = prep.GIB
CHUNK = 1024 * 1024
EVENT_CAP = 256 * 1024


def safe_directory(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('symlink directory refused')
    if not path.is_dir():
        raise ValueError('existing task directory required')
    return path


def source_list(plan):
    if plan.get('schema') != 'epyc.target-precision.weight-plan.v1':
        raise ValueError('unsupported source plan')
    base = plan['base']
    if base['repo'] != 'Qwen/Qwen3.8-27B' or not re.fullmatch('[0-9a-f]{40}', base['revision']):
        raise ValueError('unpinned source')
    sources = plan['sources']
    if not isinstance(sources, list) or not 1 <= len(sources) <= 64:
        raise ValueError('bounded source inventory required')
    names = set()
    for source in sources:
        name = source['path']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,254}', name) or name in names:
            raise ValueError('unsafe or duplicate source')
        names.add(name)
        prep.positive(source['size'], 'source size')
        identity = [k for k in ('sha256', 'git_blob_sha1') if k in source]
        if len(identity) != 1 or not re.fullmatch(
                '[0-9a-f]{64}' if identity == ['sha256'] else '[0-9a-f]{40}', source[identity[0]]):
            raise ValueError('missing pinned content identity')
        if set(source) != {'path', 'size', 'url', identity[0]}:
            raise ValueError('unknown source fields')
        if source['url'] != f'https://huggingface.co/{base["repo"]}/resolve/{base["revision"]}/{name}':
            raise ValueError('source URL drift')
    if not sources or any(n+'.part' in names for n in names):
        raise ValueError('empty or ambiguous source inventory')
    return sources


def free_bytes(path):
    stat = os.statvfs(path)
    return stat.f_bavail * stat.f_frsize


def is_tmpfs(path):
    # Inspect the longest matching mount, including bind mounts. Mount paths in
    # mountinfo are octal escaped; filesystem names cannot be inferred from /dev/shm.
    path = str(Path(path).resolve())
    mounts = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        mount = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), left.split()[4])
        if path == mount or path.startswith(mount.rstrip('/')+'/'):
            mounts.append((len(mount), right.split()[0]))
    if not mounts:
        raise ValueError('unknown placement filesystem')
    return max(mounts)[1] == 'tmpfs'


def control_bytes(root):
    total = 0
    for path in root.rglob('*'):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise ValueError('unsafe control artifact')
        if path.is_file():
            total += path.stat().st_size
    return total


class Budget:
    """Reserve remaining source and aggregate control bytes on each volume."""
    def __init__(self, source, controls, placement, reserve=GIB):
        self.source = safe_directory(source)
        self.controls = safe_directory(controls)
        if self.source == self.controls or self.source in self.controls.parents or self.controls in self.source.parents:
            raise ValueError('source and control roots must be disjoint')
        if placement not in ('durable', 'tmpfs-intermediates'):
            raise ValueError('explicit placement required')
        self.volatile = placement == 'tmpfs-intermediates'
        if is_tmpfs(self.source) != self.volatile or is_tmpfs(self.controls):
            raise ValueError('placement filesystem mismatch')
        prep.positive(reserve, 'control reserve')
        if reserve > GIB:
            raise ValueError('control reserve exceeds audited schedule')
        self.reserve = reserve

    def check(self, remaining):
        if type(remaining) is not int or remaining < 0:
            raise ValueError('invalid remaining source budget')
        used = control_bytes(self.controls)
        if used > self.reserve-EVENT_CAP:
            raise ValueError('aggregate control reserve exceeded')
        # Combine obligations when paths share a filesystem, rather than
        # admitting each independently against the same free bytes.
        volumes = {}
        for path, floor, pending in [(self.source, 0 if self.volatile else 150*GIB, remaining),
                                      (self.controls, 150*GIB, self.reserve-used)]:
            dev = path.stat().st_dev
            old_path, old_floor, old_pending = volumes.get(dev, (path, 0, 0))
            volumes[dev] = old_path, max(floor, old_floor), pending+old_pending
        for path, floor, pending in volumes.values():
            if free_bytes(path) < floor+pending:
                raise ValueError('per-volume remaining budget/floor unavailable')
        # Tmpfs charges reduce MemAvailable. Reserve the remaining pages as
        # well as preserving the unchanged shared-host floor.
        if prep.host_memory_available() < 250*GIB+(remaining if self.volatile else 0):
            raise ValueError('host memory floor/remaining tmpfs budget unavailable')


def enter_leaf(leaf, memory_max_bytes):
    leaf = safe_directory(leaf)
    root = Path('/sys/fs/cgroup').resolve()
    if root not in leaf.parents or any(p.is_dir() for p in leaf.iterdir()):
        raise ValueError('dedicated kernel cgroup leaf required')
    prep.check_cgroup(leaf, memory_max_bytes)
    if (leaf/'cgroup.events').read_text().split()[:2] != ['populated', '0']:
        raise ValueError('cgroup subtree must be empty')
    (leaf/'cgroup.procs').write_text(str(os.getpid()))
    actual = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[-1]
    if (root/actual.lstrip('/')).resolve() != leaf:
        raise ValueError('kernel cgroup membership mismatch')
    return leaf


def file_state(root, sources):
    allowed = {s['path']+suffix for s in sources for suffix in ('', '.part')}
    if any(p.name not in allowed or p.is_symlink() or not p.is_file() for p in root.iterdir()):
        raise ValueError('foreign source contents')
    remaining = 0
    for source in sources:
        final, partial = root/source['path'], root/(source['path']+'.part')
        if final.exists() and partial.exists():
            raise ValueError('ambiguous completed and partial source')
        size = (final if final.exists() else partial).stat().st_size if final.exists() or partial.exists() else 0
        if size > source['size'] or (final.exists() and size != source['size']):
            raise ValueError('retained source size mismatch')
        remaining += source['size']-size
    return remaining


def acquire(plan, budget, cgroup, *, timeout_s=7200):
    sources = source_list(plan)
    if not 0 < timeout_s <= 86400:
        raise ValueError('bounded acquisition deadline required')
    remaining = file_state(budget.source, sources)
    budget.check(remaining)
    # Tmpfs payload pages belong to the allocating acquisition cgroup, including
    # after process exit. Its leaf must survive until those files are released.
    memory_cap = 4*GIB+(sum(s['size'] for s in sources) if budget.volatile else 0)
    if prep.host_memory_available() < 250*GIB+memory_cap:
        raise ValueError('acquisition memory envelope unavailable')
    leaf = enter_leaf(cgroup, memory_cap)
    initial = prep._events(leaf)
    started = time.monotonic()

    def check():
        budget.check(remaining)
        events = prep._events(leaf)
        if any(events.get(k, 0) > initial.get(k, 0) for k in ('max', 'oom', 'oom_kill')):
            raise ValueError('acquisition cgroup memory budget hit')
        if time.monotonic()-started > timeout_s:
            raise ValueError('acquisition deadline exceeded')

    verified = []
    for source in sources:
        final = budget.source/source['path']
        partial = budget.source/(source['path']+'.part')
        retained = final if final.exists() else partial
        count = retained.stat().st_size if retained.exists() else 0
        sha = hashlib.sha256()
        git = hashlib.sha1(b'blob '+str(source['size']).encode()+b'\0')
        if retained.exists():
            with retained.open('rb') as stream:
                while chunk := stream.read(CHUNK):
                    sha.update(chunk); git.update(chunk); check()
        if count < source['size']:
            check()
            headers = {'User-Agent': 'epyc-matched-source/1'}
            if count:
                headers['Range'] = f'bytes={count}-'
            request = urllib.request.Request(source['url'], headers=headers)
            with urllib.request.urlopen(request, timeout=min(30, timeout_s)) as response:
                if int(response.headers.get('Content-Length', '-1')) != source['size']-count:
                    raise ValueError('remote length mismatch')
                if count:
                    if (response.status != 206 or response.headers.get('Content-Range') !=
                            f'bytes {count}-{source["size"]-1}/{source["size"]}'):
                        raise ValueError('remote resume mismatch')
                elif response.status != 200:
                    raise ValueError('remote status mismatch')
                with partial.open('ab' if count else 'xb') as out:
                    # One socket read per check: read(n) may aggregate a slow
                    # stream indefinitely while individual receives succeed.
                    while chunk := response.read1(CHUNK):
                        check()
                        if count+len(chunk) > source['size']:
                            raise ValueError('remote source exceeds pinned size')
                        out.write(chunk); out.flush()
                        count += len(chunk); remaining -= len(chunk)
                        sha.update(chunk); git.update(chunk); check()
                    os.fsync(out.fileno())
        if count != source['size']:
            raise ValueError('incomplete source retained for retry')
        if (('sha256' in source and sha.hexdigest() != source['sha256']) or
                ('git_blob_sha1' in source and git.hexdigest() != source['git_blob_sha1'])):
            # Preserve evidence rather than silently retrying corrupted bytes.
            raise ValueError('pinned source digest mismatch')
        check()
        if not final.exists():
            partial.rename(final)
        verified.append(dict(path=str(final), size=count, sha256=sha.hexdigest(), source=source))
    check()
    return dict(status='COMPLETE', files=verified, memory_max_bytes=memory_cap,
                verified_weights=False, limitations=['source payloads only; conversion/correspondence/native floor not qualified',
                    'tmpfs pages remain charged to acquisition leaf until released; reboot invalidates source presence'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('plan', 'source', 'controls', 'cgroup', 'placement', 'event'):
        parser.add_argument('--'+option, required=True)
    args = parser.parse_args()
    event = Path(args.event).absolute()
    controls = safe_directory(args.controls)
    if event.parent != controls or event.exists() or event.is_symlink():
        raise ValueError('fresh event directly inside durable controls required')
    def interrupted(signum, frame):
        raise RuntimeError(f'acquisition interrupted: {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        raw = Path(args.plan).read_bytes()
        if len(raw) > CHUNK:
            raise ValueError('source plan too large')
        budget = Budget(args.source, controls, args.placement)
        result = acquire(json.loads(raw), budget, args.cgroup)
        result['plan_sha256'] = hashlib.sha256(raw).hexdigest()
    except Exception as exc:
        result = dict(status='FAILED', error=str(exc), verified_weights=False)
    encoded = (json.dumps(result, sort_keys=True)+'\n').encode()
    # Leave room for the event even after a refusal; never exceed the aggregate
    # reserve to report failure. No event is better than overwriting evidence.
    if len(encoded) > EVENT_CAP or control_bytes(controls)+len(encoded) > GIB:
        raise ValueError('no control reserve for event')
    with event.open('xb') as stream:
        stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
    return 0 if result['status'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
