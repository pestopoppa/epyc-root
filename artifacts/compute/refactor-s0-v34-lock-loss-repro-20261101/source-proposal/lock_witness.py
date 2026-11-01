"""Read-only CPU quarter claim witness using the owning ancestor's kernel FD rows."""
import hashlib
import os
from pathlib import Path
import select

ID = 'yarn-oolong-s0-host256-eligible28-v34-20261031'
RAID = Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/yarn-s0-v34-lock-witness-20261031')
ENGINE = RAID / 'engine/filler_run13.sh'
ORCH = Path('/mnt/raid0/llm/epyc-orchestrator')
PYTHON = ORCH / '.venv/bin/python3'
PYTHON_ALIASES = (str(PYTHON), '/workspace/repos/epyc-orchestrator/.venv/bin/python3')
CLI = ORCH / 'src/runtime/region_lock_cli.py'
CLI_SHA = '58c2ea675db751f7403222ebbb3d6e52a4ce151ade86035e00fddda411b69940'
LOCK_ROOT = Path('/mnt/raid0/llm/tmp')
LAST = None


def proc(pid):
    root = Path('/proc') / str(pid)
    fields = (root / 'stat').read_text().rsplit(') ', 1)[1].split()
    return {'pid': pid, 'uid': root.stat().st_uid, 'birth': int(fields[19]),
            'parent': int(fields[1]),
            'argv': [os.fsdecode(a) for a in (root / 'cmdline').read_bytes().split(b'\0') if a]}


def birth(pid):
    row = proc(pid)
    return row['uid'], row['birth']


def ancestors():
    rows = []; seen = set(); pid = os.getppid()
    while pid > 1:
        if pid in seen or len(rows) >= 128:
            raise RuntimeError('ancestor cycle/depth')
        seen.add(pid); row = proc(pid); rows.append(row); pid = row['parent']
    return rows


def option(args, flag):
    if args.count(flag) != 1 or args.index(flag) + 1 >= len(args):
        raise RuntimeError('missing/duplicate ancestor option ' + flag)
    return args[args.index(flag) + 1]


def is_transport(row):
    args = row['argv']
    return len(args) >= 4 and args[0] in PYTHON_ALIASES and args[1:4] == ['-m', 'src.runtime.region_lock_cli', 'run']


def authenticate_cli(row):
    """Reuse the namespace-aware shared transport component unchanged."""
    if not is_transport(row):
        raise RuntimeError('not a registered canonical Python module transport')
    import canonical_cli
    expected = dict(canonical_cli.IDENTITY)
    expected['python_argv'] = row['argv'][0]
    result = canonical_cli.require(row['pid'], [os.fsencode(a) for a in row['argv']], expected)
    if proc(row['pid']) != row or result['birth'] != row['birth']:
        raise RuntimeError('canonical CLI identity changed during authentication')
    return result


def expected_paths(path):
    assigned = os.environ.get('FILLER_CPUS', '')
    if assigned not in ('0-23', '24-47', '48-71'):
        raise RuntimeError('exact original CPU quarter required')
    q = 'q' + str(int(assigned.split('-')[0]) // 24)
    global_path = LOCK_ROOT / ('cpu_region.GLOBAL.' + q + '.lock')
    if Path(path) != global_path:
        raise RuntimeError('GLOBAL lock path differs from assigned quarter')
    return assigned, {'GLOBAL': global_path,
                      'build': LOCK_ROOT / ('cpu_region.build.' + q + '.lock')}


def owner_for(path):
    assigned, paths = expected_paths(path)
    if os.environ.get('FILLER_ID') != ID or os.environ.get('WS58_REGIONS') != assigned:
        raise RuntimeError('own calendar CPU identity differs')
    rows = ancestors(); inner = None
    for row in rows:
        args = row['argv']
        if args[:3] == ['/bin/bash', str(ENGINE), '--inner']:
            if inner is not None or option(args, '--id') != ID or option(args, '--class') != 'cpu':
                raise RuntimeError('wrong/duplicate exact R13 CPU inner ancestor')
            inner = row
        if is_transport(row):
            authenticate_cli(row)
            if inner is None:
                raise RuntimeError('canonical CLI does not enclose exact R13 CPU inner')
            prefix = args[:args.index('--')] if '--' in args else []
            child = args[args.index('--') + 1:] if '--' in args else []
            if (option(prefix, '--cpu-list') != assigned
                    or option(prefix, '--role') != 'build'
                    or option(prefix, '--tag') != 'filler-' + ID
                    or float(option(prefix, '--timeout-s')) <= 0
                    or ('--gpu-quiet' in prefix and option(prefix, '--gpu-quiet') != 'none')
                    or child[:3] != ['/bin/bash', str(ENGINE), '--inner']
                    or option(child, '--id') != ID or option(child, '--class') != 'cpu'):
                raise RuntimeError('canonical CLI claim/child differs from exact CPU allocation')
            if row['uid'] != os.getuid():
                raise RuntimeError('foreign ancestor UID')
            if proc(inner['pid']) != inner:
                raise RuntimeError('R13 inner changed during traversal')
            return row, inner, paths
    raise RuntimeError('exact canonical CLI/R13 CPU ancestry absent')


def held(row, paths):
    """Inspect actual owner FDs, not a process-global /proc/locks traversal."""
    fd = os.pidfd_open(row['pid'])
    poll = select.poll(); poll.register(fd, select.POLLIN)
    try:
        if poll.poll(0) or proc(row['pid']) != row:
            raise RuntimeError('ancestor exited/reused before descriptor inspection')
        root = Path('/proc') / str(row['pid'])
        descriptors = list((root / 'fd').iterdir())
        if len(descriptors) > 512:
            raise RuntimeError('ancestor descriptor observation bound')
        expected = {}
        for name, path in paths.items():
            if path.is_symlink(): raise RuntimeError('lock path is symlink: ' + str(path))
            st = path.stat(); expected[name] = (st.st_dev, st.st_ino)
        found = {}
        for descriptor in descriptors:
            try:
                before = descriptor.stat()
                names = [name for name, inode in expected.items()
                         if inode == (before.st_dev, before.st_ino)]
                if not names: continue
                info = (root / 'fdinfo' / descriptor.name).read_text()
                after = descriptor.stat()
            except (FileNotFoundError, ProcessLookupError):
                continue
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise RuntimeError('ancestor descriptor changed during read')
            rows = [line.split() for line in info.splitlines() if line.startswith('lock:')]
            if len(rows) != 1:
                raise RuntimeError('ancestor FD lacks unique kernel lock: ' + descriptor.name)
            fields = rows[0]
            if len(fields) != 9 or fields[2:6] != ['FLOCK', 'ADVISORY', 'WRITE', str(row['pid'])] or fields[7:] != ['0', 'EOF']:
                raise RuntimeError('kernel FD row is not exact owner exclusive whole-file FLOCK')
            major, minor, ino = fields[6].split(':')
            if (int(major, 16), int(minor, 16), int(ino)) != (os.major(before.st_dev), os.minor(before.st_dev), before.st_ino):
                raise RuntimeError('kernel FD row inode/device differs')
            for name in names:
                if name in found: raise RuntimeError('duplicate canonical lock descriptor: ' + name)
                found[name] = {'path': str(paths[name]), 'fd': int(descriptor.name),
                               'device': before.st_dev, 'inode': before.st_ino,
                               'kernel_row': ' '.join(fields)}
        if set(found) != set(paths):
            raise RuntimeError('ancestor lock descriptor set incomplete: ' + str(sorted(set(paths) - set(found))))
        for name, path in paths.items():
            st = path.stat()
            if path.is_symlink() or expected[name] != (st.st_dev, st.st_ino):
                raise RuntimeError('canonical lock path identity changed')
        if poll.poll(0) or proc(row['pid']) != row:
            raise RuntimeError('ancestor exited/reused during descriptor inspection')
        return found
    finally:
        os.close(fd)


def observe(path, owner=None, identity=None):
    global LAST
    row, inner, paths = owner_for(path)
    if owner is not None and (row['pid'] != owner or (row['uid'], row['birth']) != tuple(identity)):
        raise RuntimeError('recorded CPU claim owner changed')
    locks = held(row, paths)
    # Re-traverse after FD inspection; wrappers between worker/inner/CLI are valid,
    # while a reparented worker or a replaced inner/owner is not.
    again, same_inner, again_paths = owner_for(path)
    if again != row or same_inner != inner or again_paths != paths:
        raise RuntimeError('CPU claim ancestry changed during descriptor inspection')
    LAST = {'owner': row, 'inner': inner, 'locks': locks,
            'cli_source_sha256': CLI_SHA, 'grant_inference': False}
    return LAST


def capture(path=LOCK_ROOT / 'cpu_region.GLOBAL.q0.lock'):
    record = observe(path)
    owner = record['owner']
    return owner['pid'], (owner['uid'], owner['birth'])


def verify(owner, identity, path=LOCK_ROOT / 'cpu_region.GLOBAL.q0.lock'):
    observe(path, owner, identity)
    return True
