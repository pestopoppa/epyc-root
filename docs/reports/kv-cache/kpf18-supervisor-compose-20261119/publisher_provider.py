"""Read-only witness for the deployed publisher's shared-quiet/device-writer pair.

Only explicitly sealed publisher-smoke installations may select this provider.
Official execution keeps current_lock.py's exclusive-quiet contract unchanged.
No lock is acquired, upgraded, released or inferred from a process name.
"""
import hashlib
import os
from pathlib import Path
import types

LEGACY = Path(__file__).resolve().parent.parent / 'kpf18-g3-current-lock-20261104/current_lock.py'
LEGACY_SHA = '8b598901b6d4d5edd1ca1e9cf5844b7ca22e4f3ede2817a1df72edb104f2478c'
ORCHESTRATOR = Path('/mnt/raid0/llm/epyc-orchestrator')
SOURCES = ('src/runtime/gpu_quiet_lock.py', 'src/runtime/cpu_region_lock.py',
           'src/runtime/lock_queue.py', 'src/runtime/region_lock_cli.py', 'scripts/region-lock')
DEVICE = Path('/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock')
ENGINE = '/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh'
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')


def legacy():
    raw = LEGACY.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEGACY_SHA:
        raise ValueError('publisher predecessor provider drift')
    module = types.ModuleType('_publisher_retained_provider')
    exec(compile(raw, str(LEGACY), 'exec'), module.__dict__)
    return module


def device_writer(lineage, identities, quiet_owner, row, proc_root=Path('/proc')):
    """Witness the inner shell's captured fd9, including locks left by flock(1).

    flock(1) exits before the job starts; /proc/locks can name that exited PID.
    fdinfo instead binds the live ancestor's open description to the WRITE lock.
    Device numbers and inode must all match, and waiters never count as owners.
    """
    st = DEVICE.stat()
    wanted = (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino)
    matches = []
    for pid in lineage[:lineage.index(quiet_owner)]:
        root = proc_root / str(pid)
        fd = root / 'fd/9'
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target != str(DEVICE):
            continue
        if identities[pid][0] != os.getuid():
            raise ValueError('foreign publisher device ancestor')
        if not DEVICE.is_file() or fd.stat().st_ino != st.st_ino or fd.stat().st_dev != st.st_dev:
            raise ValueError('publisher device descriptor replaced')
        argv = (root / 'cmdline').read_bytes().decode().rstrip('\0').split('\0')
        # Match the engine's actual inner invocation, rather than a substring
        # of a command containing some other process's name.
        if (len(argv) < 9 or argv[0] != '/bin/bash' or argv[1] != ENGINE
                or argv[2:8] != ['--inner', '--id', row, '--class', 'gpu', '--cmd']):
            raise ValueError('publisher device holder is not this row inner engine')
        info = root / 'fdinfo/9'
        before_info = info.read_text()
        locks = []
        for line in before_info.splitlines():
            fields = line.split()
            if not fields or fields[0] != 'lock:':
                continue
            if (len(fields) != 9 or fields[2:5] != ['FLOCK', 'ADVISORY', 'WRITE']
                    or fields[7:] != ['0', 'EOF']):
                raise ValueError('publisher device lock is not an exclusive owner')
            major, minor, inode = fields[6].split(':')
            locks.append((int(major, 16), int(minor, 16), int(inode)))
        if locks != [wanted]:
            raise ValueError('publisher device WRITE lock absent or mismatched')
        after_fd = fd.stat()
        if (os.readlink(fd) != str(DEVICE)
                or (after_fd.st_dev, after_fd.st_ino) != (st.st_dev, st.st_ino)
                or info.read_text() != before_info):
            raise ValueError('publisher device descriptor changed during capture')
        matches.append({'pid': pid, 'identity': list(identities[pid]),
                        'device': st.st_dev, 'inode': st.st_ino})
    if len(matches) != 1:
        raise ValueError('one captured publisher device writer required')
    after = DEVICE.stat()
    if (after.st_dev, after.st_ino) != (st.st_dev, st.st_ino):
        raise ValueError('publisher device lock file replaced')
    return matches[0]


def capture(row_id, expected_sources):
    if (os.environ.get('FILLER_SMOKE') != '1' or os.environ.get('FILLER_DRYRUN') != '1'
            or os.environ.get('FILLER_ID') != row_id
            or os.environ.get('FILLER_GPU_LOCK', str(DEVICE)) != str(DEVICE)):
        raise ValueError('explicit publisher smoke identity required')
    dry = FLAGS / 'dryrun' / row_id
    if (os.environ.get('FILLER_DRYRUN_DIR') != str(dry)
            or os.environ.get('FILLER_GRANTS_DIR') != str(dry / 'grants')):
        raise ValueError('publisher smoke namespace mismatch')
    previous = legacy()
    if previous.source_digests() != expected_sources:
        raise ValueError('publisher provider source drift')
    module = previous.provider()
    before = previous.LOCK.stat()
    lineage = previous.ancestors()
    identities = {pid: previous.identity(pid) for pid in lineage}
    status, owners = module.holders(), module.lock_owners(previous.LOCK)
    if (status.get('path') != str(previous.LOCK) or status.get('held') is not True
            or status.get('mode') != 'shared' or not isinstance(owners, dict)
            or len(owners) != 1 or set(owners.values()) != {'shared'}):
        raise ValueError('one attributed shared publisher quiet holder required')
    records = status.get('holders')
    if not isinstance(records, list) or len(records) != 1 or records[0].get('mode') != 'shared':
        raise ValueError('publisher shared holder attribution missing')
    quiet_owner = next(iter(owners))
    if quiet_owner not in identities or identities[quiet_owner][0] != os.getuid():
        raise ValueError('publisher quiet holder is not a same-UID ancestor')
    quiet_identity = identities[quiet_owner]
    record = records[0]
    if (record.get('schema') != 'epyc.orchestrator.gpu_quiet_holder.v1'
            or record.get('verified') is False or record.get('pid') != quiet_owner
            or record.get('start_ticks') != quiet_identity[1] or record.get('role') != 'bench'
            or record.get('lock_path') != str(previous.LOCK)
            or record.get('request_tag') != 'filler-' + row_id):
        raise ValueError('publisher shared holder row attribution mismatch')
    writer = device_writer(lineage, identities, quiet_owner, row_id)
    after = previous.LOCK.stat()
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise ValueError('publisher quiet lock file replaced')
    for pid in (quiet_owner, writer['pid']):
        if previous.identity(pid) != identities[pid]:
            raise ValueError('publisher provider ancestor changed')
    if previous.source_digests() != expected_sources:
        raise ValueError('publisher provider source changed during capture')
    return {'mode': 'publisher-shared-quiet-device-writer-v1', 'row_id': row_id,
            'quiet_owner': quiet_owner, 'quiet_identity': list(quiet_identity),
            'quiet_device': after.st_dev, 'quiet_inode': after.st_ino,
            'device_writer': writer, 'sources': expected_sources}


def recheck(witness):
    if capture(witness['row_id'], witness['sources']) != witness:
        raise ValueError('captured publisher lock pair no longer retained')
    return True
