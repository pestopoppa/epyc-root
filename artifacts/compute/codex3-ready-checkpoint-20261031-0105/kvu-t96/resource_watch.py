#!/usr/bin/env python3
"""Sample aggregate RSS and drain only this subreaper's captured descendants."""
import ctypes
import glob
import json
import os
import shutil
from pathlib import Path
import signal
import subprocess
import sys
import time

MAX_KIB = 110 * 1024 * 1024
MIN_FREE_BYTES = 150 * 1024**3
DISK_PATH = '/mnt/raid0/llm'


def proc(pid):
    try:
        root = Path('/proc') / str(pid)
        fields = (root / 'stat').read_text().rsplit(')', 1)[1].split()
        state, birth = fields[0], int(fields[19])
        status = (root / 'status').read_text().splitlines()
        rss = next((int(x.split()[1]) for x in status if x.startswith('VmRSS:')), 0)
        children = set()
        for thread in (root / 'task').iterdir():
            try:
                children.update(int(x) for x in (thread / 'children').read_text().split())
            except (FileNotFoundError, ProcessLookupError):
                continue  # a thread exited while it was enumerated
        return birth, state, rss, children
    except (FileNotFoundError, ProcessLookupError):
        return None


def scan(known):
    todo = [os.getpid(), *known]
    visited = set()
    total = 0
    while todo:
        pid = todo.pop()
        if pid in visited:
            continue
        visited.add(pid)
        item = proc(pid)
        if item is None:
            continue
        birth, state, rss, children = item
        if pid == os.getpid():
            total += rss
        else:
            previous = known.get(pid)
            if previous is not None and previous != birth:
                del known[pid]  # PID reused: never signal it
                continue
            known[pid] = birth
            if state != 'Z':
                total += rss
        todo.extend(children)
    return total


def living(known):
    result = []
    for pid, birth in list(known.items()):
        item = proc(pid)
        if item is None or item[0] != birth or item[1] == 'Z':
            continue
        result.append(pid)
    return result


def signal_owned(known, sig):
    for pid in living(known):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


def reap_adopted(root_pid):
    for pid in list(_known):
        if pid == root_pid:
            continue
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            pass


def pending(known, root_pid):
    """Adopted zombies stay pending until reaped; root is reaped by Popen."""
    result = []
    for pid, birth in list(known.items()):
        item = proc(pid)
        if item is not None and item[0] == birth and (pid != root_pid or item[1] != 'Z'):
            result.append(pid)
    return result


def drain(known, root_pid):
    scan(known)
    signal_owned(known, signal.SIGTERM)
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        scan(known)
        reap_adopted(root_pid)
        if not pending(known, root_pid):
            return True
        time.sleep(0.05)
    scan(known)
    signal_owned(known, signal.SIGKILL)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        scan(known)
        signal_owned(known, signal.SIGKILL)
        reap_adopted(root_pid)
        if not pending(known, root_pid):
            return True
        time.sleep(0.05)
    return False


_known = {}
_interrupted = False


def interrupt(_signum, _frame):
    global _interrupted
    _interrupted = True


def main():
    args = sys.argv[1:]
    limit = MAX_KIB
    if len(args) >= 2 and args[0] == '--limit-kib':
        limit = int(args[1])
        args = args[2:]
    if not args or limit < 1 or limit > MAX_KIB:
        return 64
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    child = subprocess.Popen(args)
    peak = 0
    failure = ''
    try:
        while True:
            total = scan(_known)
            peak = max(peak, total)
            rc = child.poll()
            if total > limit:
                failure = f'RSS_SAMPLE_LIMIT_EXCEEDED kib={total} limit_kib={limit}'
                break
            if shutil.disk_usage(DISK_PATH).free < MIN_FREE_BYTES:
                failure = f'DISK_FLOOR_BREACHED path={DISK_PATH} floor_bytes={MIN_FREE_BYTES}'
                break
            stopfile = os.environ.get('FILLER_STOPFILE')
            if ((stopfile and os.path.lexists(stopfile)) or
                    glob.glob('/mnt/raid0/llm/tmp/HOLD_*') or
                    glob.glob('/mnt/raid0/llm/tmp/compute-flags/**/HOLD_*', recursive=True)):
                failure = 'HOLD_OR_STOP_DETECTED'
                break
            if _interrupted:
                failure = 'monitor interrupted'
                break
            if time.time() >= int(os.environ['FILLER_DEADLINE']):
                failure = 'FILLER_DEADLINE_EXCEEDED'
                break
            if rc is not None:
                scan(_known)
                if living(_known):
                    failure = 'root exited with owned descendants still running'
                break
            time.sleep(0.05)
    except Exception as exc:
        failure = f'monitor error: {type(exc).__name__}: {exc}'
    try:
        drained = drain(_known, child.pid)
    except Exception as exc:
        print(f'monitor cleanup error: {exc}', file=sys.stderr, flush=True)
        drained = False
    try:
        child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        drained = False
    identities = {str(pid): {'birth': birth, 'current': proc(pid)} for pid,birth in _known.items()}
    partial = child.returncode == 75 or failure.startswith(('DISK_FLOOR_BREACHED','FILLER_DEADLINE_EXCEEDED','HOLD_OR_STOP_DETECTED','monitor interrupted'))
    status = {'partial': partial, 'cleanup_verified': drained, 'failure': failure or None, 'root_pid': child.pid, 'native_rc': child.returncode, 'captured': identities, 'sampled_peak_kib': peak}
    rc = 125 if not drained else (75 if partial else (125 if failure else child.returncode))
    status['rc'] = rc
    out = Path(os.environ.get('WATCH_RESULT', str(Path(__file__).resolve().parent/'watch-result.json')))
    tmp = out.with_name(out.name+'.tmp');tmp.write_text(json.dumps(status,indent=2)+'\n');tmp.replace(out)
    print(f'RSS_SAMPLED_PEAK_KIB={peak} LIMIT_KIB={limit} drained={drained}', flush=True)
    if failure:
        print(failure, file=sys.stderr, flush=True)
    if not drained:
        print('captured descendants not confirmed dead', file=sys.stderr, flush=True)
        return 125
    return rc

if __name__ == '__main__':
    sys.exit(main())
