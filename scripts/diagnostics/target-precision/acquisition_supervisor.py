"""External acquisition watchdog. Never joins the worker's memory cgroup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import acquisition as acq


def validate_leaf(leaf, cap):
    leaf = acq.safe_directory(leaf)
    root = Path('/sys/fs/cgroup').resolve()
    if root not in leaf.parents or any(p.is_dir() for p in leaf.iterdir()):
        raise ValueError('dedicated kernel cgroup leaf required')
    own = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[-1]
    own = (root/own.lstrip('/')).resolve()
    if own == leaf or leaf in own.parents:
        raise ValueError('supervisor must remain outside worker cgroup')
    acq.prep.check_cgroup(leaf, cap)
    if (leaf/'cgroup.events').read_text().split()[:2] != ['populated', '0']:
        raise ValueError('cgroup subtree must be empty')
    return leaf


def stop_child(child):
    # Only the process group captured at Popen is signalled, never a name match.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            continue
        if sig == signal.SIGKILL:
            return
    raise RuntimeError('captured acquisition worker did not reap')


def supervise(raw, plan_path, budget, cgroup, event, *, timeout_s=7200, interval_s=0.25):
    """Bound one serial worker; reserve durable terminal-event blocks first.

    A killed supervisor/host cannot report its own death. The guarantee here is
    independence from worker leaf OOM/SIGKILL, not host-wide OOM or power loss.
    """
    if not 0 < timeout_s <= 86400 or not 0 < interval_s <= 1:
        raise ValueError('bounded supervisor timing required')
    event = Path(event).absolute()
    if event.parent != budget.controls or event.exists() or event.is_symlink():
        raise ValueError('fresh event directly inside durable controls required')
    slot = event.with_name(event.name+'.reserved')
    worker_event = event.with_name(event.name+'.worker')
    if worker_event.exists() or worker_event.is_symlink():
        raise ValueError('fresh worker event required')
    # Preallocate real durable blocks so worker resource loss cannot consume the
    # terminal receipt allowance. The final file contains valid padded JSON.
    fd = os.open(slot, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    child = None
    result = dict(status='FAILED', verified_weights=False,
                  plan_sha256=hashlib.sha256(raw).hexdigest())
    previous = {}
    def interrupted(signum, frame):
        raise RuntimeError(f'supervisor interrupted: {signum}')
    try:
        os.posix_fallocate(fd, 0, acq.EVENT_CAP)
        os.fsync(fd)
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, interrupted)
        plan = json.loads(raw)
        sources = acq.source_list(plan)
        remaining = acq.file_state(budget.source, sources)
        budget.check(remaining)
        cap = 4*acq.GIB+(sum(s['size'] for s in sources) if budget.volatile else 0)
        if acq.prep.host_memory_available() < 250*acq.GIB+cap:
            raise ValueError('acquisition memory envelope unavailable')
        leaf = validate_leaf(cgroup, cap)
        initial = acq.prep._events(leaf)
        # Bind the plan bytes actually handed to the worker, not a mutable path.
        with Path(plan_path).open('rb') as plan_stream:
            if plan_stream.read(acq.CHUNK+1) != raw or len(raw) > acq.CHUNK:
                raise ValueError('plan changed or oversized')
            plan_stream.seek(0)
            started = time.monotonic()
            child = subprocess.Popen([sys.executable, str(Path(acq.__file__).resolve()),
                '--plan', f'/proc/self/fd/{plan_stream.fileno()}',
                '--source', str(budget.source), '--controls', str(budget.controls),
                '--placement', 'tmpfs-intermediates' if budget.volatile else 'durable',
                '--cgroup', str(leaf), '--event', str(worker_event)],
                pass_fds=(plan_stream.fileno(),), start_new_session=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            while True:
                # These observations come from the parent even while the worker
                # blocks in a socket or has been killed by its leaf's OOM policy.
                budget.check(acq.file_state(budget.source, sources))
                current = acq.prep._events(leaf)
                if any(current.get(k, 0) > initial.get(k, 0) for k in ('max', 'oom', 'oom_kill')):
                    raise ValueError('worker cgroup memory budget hit')
                if time.monotonic()-started > timeout_s:
                    raise ValueError('external acquisition deadline exceeded')
                rc = child.poll()
                if rc is not None:
                    if rc != 0:
                        raise ValueError(f'acquisition worker exit {rc}')
                    if worker_event.is_symlink() or worker_event.stat().st_size > acq.EVENT_CAP:
                        raise ValueError('unsafe worker receipt')
                    receipt = json.loads(worker_event.read_text())
                    if (receipt.get('status') != 'COMPLETE' or
                            receipt.get('plan_sha256') != result['plan_sha256'] or
                            receipt.get('verified_weights') is not False or
                            len(receipt.get('files', [])) != len(sources) or
                            acq.file_state(budget.source, sources) != 0):
                        raise ValueError('worker completion receipt mismatch')
                    for record, source in zip(receipt['files'], sources):
                        if (record.get('source') != source or
                                record.get('path') != str(budget.source/source['path']) or
                                record.get('size') != source['size'] or
                                not acq.re.fullmatch('[0-9a-f]{64}', record.get('sha256', '')) or
                                ('sha256' in source and record['sha256'] != source['sha256']) or
                                not (budget.source/source['path']).is_file()):
                            raise ValueError('worker source receipt mismatch')
                    result = receipt
                    break
                try:
                    child.wait(timeout=interval_s)
                except subprocess.TimeoutExpired:
                    pass
    except Exception as exc:
        result.update(status='FAILED', error=str(exc), verified_weights=False)
    finally:
        try:
            if child is not None:
                result['worker_pid'] = child.pid
                stop_child(child)
                result['worker_returncode'] = child.returncode
                result['worker_reaped'] = True
        except Exception as exc:
            result.update(status='FAILED', error=f'cleanup failed: {exc}', worker_reaped=False)
        try:
            encoded = (json.dumps(result, sort_keys=True)+'\n').encode()
            if len(encoded) > acq.EVENT_CAP:
                raise ValueError('terminal receipt exceeds reservation')
            os.lseek(fd, 0, os.SEEK_SET)
            with os.fdopen(os.dup(fd), 'r+b') as stream:
                stream.write(encoded.ljust(acq.EVENT_CAP, b' '))
                stream.flush()
                os.fsync(stream.fileno())
            os.link(slot, event)  # exclusive publication; never overwrite evidence
            slot.unlink()
            directory = os.open(budget.controls, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            os.close(fd)
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'source', 'controls', 'cgroup', 'placement', 'event'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    budget = acq.Budget(args.source, args.controls, args.placement)
    raw = Path(args.plan).read_bytes()
    result = supervise(raw, args.plan, budget, args.cgroup, args.event)
    return 0 if result['status'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
