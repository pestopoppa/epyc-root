"""Serial durable preparation schedule and fail-closed Linux resource controls.

No downloader, source deletion, build or model execution is performed by planning.
The caller supplies a dedicated empty delegated cgroup-v2 leaf for each command.
"""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import selectors
import subprocess
import threading

GIB = 1024**3


def positive(value, label):
    if type(value) is not int or value <= 0:
        raise ValueError(label)
    return value


def preparation_schedule(sizing, available_bytes, *, placement="durable",
                         tmpfs_available_bytes=0, host_available_bytes=0):
    if sizing.get('schema') != 'epyc.target-precision.converter-sizing.v1':
        raise ValueError('unsupported sizing schema')
    source = positive(sizing['source_bytes'], 'source bytes')
    floor = positive(sizing['disk_floor_bytes'], 'disk floor')
    if floor < 150*GIB:
        raise ValueError('disk floor cannot be lowered')
    caps = sizing['output_cap_bytes']
    if set(caps) != {'BF16', 'Q8_0', 'Q4_K_M'}:
        raise ValueError('three output caps required')
    for cap in caps.values():
        positive(cap, 'output cap')
    if sizing['workspace']['extra_disk_bytes'] != 0:
        raise ValueError('new disk workspace requires audit')
    # Keep all three derived arms. Release ONLY task-owned source shards after
    # validated BF16 correspondence and immutable source/build/output receipts.
    reserve = GIB  # total logs, receipts and metadata, separately budgeted
    steps = [
        dict(name='acquire', retained_bytes=source, memory_max_bytes=4*GIB),
        dict(name='convert', retained_bytes=source+caps['BF16'], memory_max_bytes=128*GIB),
        dict(name='release_verified_source', retained_bytes=caps['BF16'], memory_max_bytes=4*GIB),
        dict(name='quantize_Q8_0', retained_bytes=caps['BF16']+caps['Q8_0'], memory_max_bytes=64*GIB),
        dict(name='quantize_Q4_K_M', retained_bytes=sum(caps.values()), memory_max_bytes=64*GIB),
    ]
    if placement not in ['durable', 'tmpfs-intermediates']:
        raise ValueError('explicit supported placement required')
    for step in steps:
        step['durable_bytes'] = step['retained_bytes']
        step['tmpfs_bytes'] = 0
    if placement == 'tmpfs-intermediates':
        # The writer owns tmpfs page charges, even after it exits. Acquisition
        # cannot use a 4 GiB total cap while allocating the entire source set.
        steps[0]['memory_max_bytes'] += source
        volatile = [source, source+caps['BF16'], caps['BF16'], caps['BF16'], caps['BF16']]
        for step, count in zip(steps, volatile):
            step['tmpfs_bytes'] = count
            step['durable_bytes'] -= count
    required = floor + reserve + max(s['durable_bytes'] for s in steps)
    tmpfs_peak = max(s['tmpfs_bytes'] for s in steps)
    # Deliberately double-count tmpfs pages charged to process cgroups: these
    # are independent enforced budgets, not an estimate of typical RSS.
    memory_required = 250*GIB+max(s['tmpfs_bytes']+s['memory_max_bytes'] for s in steps)
    resources_fit = (available_bytes >= required and host_available_bytes >= memory_required and
                     (placement == 'durable' or tmpfs_available_bytes >= tmpfs_peak+reserve))
    return dict(schema='epyc.target-precision.preparation.v1',
                sizing_sha256=hashlib.sha256(json.dumps(sizing, sort_keys=True).encode()).hexdigest(),
                placement=placement,
                tmpfs_peak_bytes=tmpfs_peak, tmpfs_required_free_bytes=tmpfs_peak+reserve if tmpfs_peak else 0,
                tmpfs_available_bytes=tmpfs_available_bytes,
                host_available_bytes=host_available_bytes, host_required_bytes=memory_required,
                resource_envelope_fits=resources_fit,
                volatile_recovery='tmpfs source/BF16 lost on reboot: reacquire/rederive and fully reverify before row publication',
                steps=steps, output_cap_bytes=caps, control_reserve_bytes=reserve,
                disk_floor_bytes=floor, required_free_bytes=required,
                available_bytes=available_bytes, disk_envelope_fits=available_bytes >= required,
                execution_admitted=False,
                source_release_gate=['all pinned source payloads verified',
                                     'BF16 digest and full tensor/tokenizer correspondence verified',
                                     'source/build/output receipts persisted outside source directory',
                                     'task-owned source only; no shared model deletion'],
                enforcement=dict(memory='dedicated cgroup-v2 memory.max; memory.swap.max=0',
                                 output='RLIMIT_FSIZE per serial single-output command',
                                 disk='remaining output budget plus unchanged floor on every monitor sample',
                                 controls='aggregate logs/receipts bounded within control reserve'),
                limitations=['snapshot reserves no shared disk, tmpfs or RAM',
                             'memory caps are enforced budgets, not measured sufficiency',
                             'source release requires receipt validation; planner never deletes files',
                             'restart may need source reacquisition and BF16 rederivation; volatile paths cannot be treated as durable',
                             'acquisition and aggregate control-reserve enforcement require integration'])


def check_cgroup(leaf, memory_max_bytes):
    """Verify an already configured dedicated leaf; never modify shared limits."""
    leaf = Path(leaf)
    positive(memory_max_bytes, 'memory cap')
    if leaf.is_symlink() or not leaf.is_dir():
        raise ValueError('dedicated cgroup leaf required')
    for name in ['cgroup.procs', 'memory.max', 'memory.swap.max', 'memory.oom.group', 'memory.events']:
        if (leaf / name).is_symlink():
            raise ValueError('symlink cgroup control')
    if (leaf/'cgroup.procs').read_text().strip():
        raise ValueError('cgroup must be empty and exclusively owned')
    if (leaf/'memory.max').read_text().strip() != str(memory_max_bytes):
        raise ValueError('total memory cap mismatch')
    if (leaf/'memory.swap.max').read_text().strip() != '0':
        raise ValueError('swap must be disabled')
    if (leaf/'memory.oom.group').read_text().strip() != '1':
        raise ValueError('group OOM enforcement required')
    return leaf


def _events(leaf):
    return dict((key, int(value)) for key, value in
                (line.split() for line in (leaf/'memory.events').read_text().splitlines()))


def host_memory_available():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1])*1024
    raise ValueError('missing host memory observation')


def check_disk(output, output_cap_bytes, floor_bytes, free_bytes):
    positive(output_cap_bytes, 'output cap')
    if floor_bytes < 150*GIB:
        raise ValueError('disk floor cannot be lowered')
    output = Path(output)
    if output.is_symlink():
        raise ValueError('symlink output')
    used = output.stat().st_size if output.exists() else 0
    if used > output_cap_bytes or free_bytes < floor_bytes + output_cap_bytes-used:
        raise ValueError('disk/output budget exceeded')


def run_bounded(argv, *, output, output_cap_bytes, cgroup, memory_max_bytes,
                disk_floor_bytes=150*GIB, timeout_s=3600, sample_s=0.2,
                log_path=None, log_cap_bytes=GIB):
    """Run ONE audited single-output command, in an exclusively owned leaf.

    Caller must bind tools/argv, receipts, control reserve and step release gate.
    RLIMIT_FSIZE caps each file (not their aggregate); commands with temporary,
    split or multiple outputs are outside this audited interface.
    """
    if threading.active_count() != 1:
        raise ValueError('preexec cgroup join requires single-threaded caller')
    output = Path(output)
    log = Path(log_path) if log_path is not None else output.with_name(output.name+'.log')
    positive(log_cap_bytes, 'log cap')
    if log == output or log.exists() or log.is_symlink():
        raise ValueError('fresh separate log required')
    if not argv or not isinstance(argv, list) or output.exists() or output.is_symlink():
        raise ValueError('fresh output and argv required')
    if log.parent.resolve() != output.parent.resolve():
        raise ValueError('log and output must share filesystem directory')
    if not 0 < sample_s <= 1 or not 0 < timeout_s <= 86400:
        raise ValueError('bounded monitoring and deadline required')
    leaf = check_cgroup(cgroup, memory_max_bytes)
    initial = _events(leaf)

    def free():
        stat = os.statvfs(output.parent)
        return stat.f_bavail * stat.f_frsize

    check_disk(output, output_cap_bytes, disk_floor_bytes+log_cap_bytes, free())
    if host_memory_available() < 250*GIB + memory_max_bytes:
        raise ValueError('host memory budget unavailable')

    def constrain_child():
        # preexec runs in a single-threaded caller. No allocation work may be
        # started before joining the leaf; exec and all descendants inherit it.
        (leaf/'cgroup.procs').write_text(str(os.getpid()))
        actual = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[-1]
        if Path('/sys/fs/cgroup', actual.lstrip('/')).resolve() != leaf.resolve():
            raise RuntimeError('child cgroup membership mismatch')
        resource.setrlimit(resource.RLIMIT_FSIZE, (output_cap_bytes, output_cap_bytes))
        os.setsid()

    import time
    start = time.monotonic()
    child = None
    written = 0
    with log.open('xb', buffering=0) as stream, selectors.DefaultSelector() as selector:
        try:
            child = subprocess.Popen(argv, preexec_fn=constrain_child, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
            selector.register(child.stdout, selectors.EVENT_READ)
            eof = False
            while True:
                check_disk(output, output_cap_bytes, disk_floor_bytes+log_cap_bytes-written, free())
                if host_memory_available() < 250*GIB:
                    raise ValueError('host memory floor breached')
                if time.monotonic()-start > timeout_s:
                    raise ValueError('preparation timeout')
                for key, _ in selector.select(timeout=sample_s):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        eof = True
                    else:
                        if written+len(chunk) > log_cap_bytes:
                            raise ValueError('original tool log cap exceeded')
                        stream.write(chunk)
                        written += len(chunk)
                if child.poll() is not None and eof:
                    break
            rc = child.wait()
            events = _events(leaf)
            if rc != 0 or any(events.get(k, 0) > initial.get(k, 0) for k in ['oom', 'oom_kill', 'max']):
                raise ValueError('command failed or memory budget hit')
            if not output.is_file() or output.stat().st_size == 0:
                raise ValueError('missing output')
            check_disk(output, output_cap_bytes, disk_floor_bytes, free())
            return dict(returncode=rc, output_bytes=output.stat().st_size,
                        log_bytes=written, memory_events_before=initial, memory_events_after=events,
                        verified_weights=False)
        finally:
            if child is not None:
                # Only this captured child's new process group belongs to this command.
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
                if child.stdout is not None:
                    child.stdout.close()
