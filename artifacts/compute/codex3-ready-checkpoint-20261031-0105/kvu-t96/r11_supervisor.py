#!/usr/bin/env python3
"""R11 smoke supervisor. RSS is sampled, not a kernel-enforced peak."""
import ctypes
import json
import os
from pathlib import Path
import resource
import select
import signal
import subprocess
import sys
import time
import smoke_admission
import pidfd_custody_v2 as custody
import pidfd_subreaper_v3 as owned_drain
import pf1_graceful

if len(sys.argv) < 4 or sys.argv[2] != '--':
    raise SystemExit('usage: smoke-supervisor.py seconds -- command ...')
limit = float(sys.argv[1])
if not 0 < limit <= 265:
    raise SystemExit('invalid deadline')
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
ceiling = min([16 * 1024**3] + [x for x in (soft, hard) if x != resource.RLIM_INFINITY])
resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
libc = ctypes.CDLL(None, use_errno=True)
if libc.prctl(36, 1, 0, 0, 0):
    raise OSError(ctypes.get_errno(), 'subreaper')
interrupted = False
def stop_signal(_sig, _frame):
    global interrupted
    interrupted = True
signal.signal(signal.SIGTERM, stop_signal)
signal.signal(signal.SIGINT, stop_signal)
def identity(pid):
    proc = Path('/proc') / str(pid)
    stat = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()
    return proc.stat().st_uid, int(stat[19]), stat[0]
def children(pid):
    tasks = Path("/proc") / str(pid) / "task"
    result = []
    for task in tasks.iterdir():
        result.extend(int(x) for x in (task / "children").read_text().split())
    return result
exited_processes = 0
exited_threads = 0
def dead_pidfd(fd):
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    return bool(poller.poll(0))
def sample_tree():
    global exited_processes, exited_threads
    total = 0
    pending = [(os.getpid(), None)]
    seen = set()
    while pending:
        pid, expected_parent = pending.pop()
        if pid in seen:
            raise RuntimeError('duplicate process identity during sampling')
        seen.add(pid)
        try:
            fd = os.pidfd_open(pid)
        except ProcessLookupError:
            exited_processes += 1
            continue
        except OSError as exc:
            if exc.errno != 22:
                raise
            status = Path('/proc', str(pid), 'status')
            try:
                fields = dict(line.split(':', 1) for line in status.read_text().splitlines() if ':' in line)
            except FileNotFoundError:
                exited_processes += 1
                continue
            tgid = int(fields['Tgid'].strip())
            uid = int(fields['Uid'].split()[0])
            if uid == os.getuid() and tgid != pid and tgid in seen:
                # pidfd_open rejects non-leader TIDs on this kernel. Their RSS
                # is already included in the identity-checked owned TGID.
                continue
            raise RuntimeError(f'pidfd EINVAL without an already owned TGID: pid={pid}, tgid={tgid}') from exc
        try:
            proc = Path('/proc') / str(pid)
            try:
                before = identity(pid)
                fields = (proc/'stat').read_text().rsplit(') ',1)[1].split()
                if before[0] != os.getuid():
                    raise RuntimeError('foreign process in owned tree')
                if expected_parent is not None and int(fields[1]) != expected_parent:
                    raise RuntimeError('process parent changed during sampling')
                total += int((proc/'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
                for task in (proc/'task').iterdir():
                    try:
                        pending.extend((int(x),pid) for x in (task/'children').read_text().split())
                    except FileNotFoundError:
                        if task.exists() or identity(pid)[:2] != before[:2]:
                            raise RuntimeError('ambiguous task disappearance')
                        exited_threads += 1
                after = identity(pid)
                if before[:2] != after[:2]:
                    raise RuntimeError('process identity changed while sampling')
            except FileNotFoundError:
                if not dead_pidfd(fd):
                    raise RuntimeError('live process became unreadable')
                exited_processes += 1
        finally:
            os.close(fd)
    return total, len(seen)
class AdmissionLost(Exception):pass
def admitted(owner,ident):
    try:
        smoke_admission.check(os.sched_getaffinity(0))
    except (OSError,RuntimeError,ValueError) as exc:
        raise AdmissionLost(str(exc)) from exc

if children(os.getpid()):
    raise SystemExit('unexpected pre-existing children')
try:
    gpu_owner,gpu_identity=None,None
    admitted(gpu_owner,gpu_identity)
except (AdmissionLost,OSError,RuntimeError,ValueError) as exc:
    print('supervisor admission refused:',str(exc),flush=True)
    raise SystemExit(78)
started = time.monotonic()
signalled_children = set()
child = None
child_fd = None
birth = None
failure = None
peak = 0
samples = 0
next_guard = started
admission_lost = False
def notice(*args):
    try: print(*args, flush=True)
    except BaseException: pass
try:
    # The outer finally covers Popen itself, including an exception after fork
    # but before Popen returns, and every instruction after it returns.
    child = subprocess.Popen(sys.argv[3:], start_new_session=True)
    try:
        child_fd, _ = custody.open_child(child.pid)
        birth = identity(child.pid)
        if birth[0] != os.getuid(): raise RuntimeError('leader ownership mismatch')
    except BaseException as exc:
        birth = None
        failure = 'leader capture: ' + str(exc)
    while failure is None and not interrupted:
        try:
            rss, _ = sample_tree()
            peak = max(peak, rss)
            samples += 1
            if rss > 8 * 1024**3: failure = 'sampled aggregate RSS exceeds 8 GiB'
            now = time.monotonic()
            if now >= next_guard:
                admitted(gpu_owner, gpu_identity)
                next_guard = now + 2
            if now - started >= limit: failure = 'supervisor deadline'
            if child.poll() is not None: break
        except AdmissionLost as exc:
            admission_lost = True
            failure = 'monitoring/admission gap: ' + str(exc)
        except BaseException as exc:
            failure = 'monitoring/admission exception: ' + repr(exc)
        if failure is None: time.sleep(.1)
    if interrupted and failure is None: failure = 'interrupted'
except BaseException as exc:
    failure = 'supervisor exception: ' + repr(exc)
finally:
    if failure is not None: notice('supervisor refusal:', failure)
    warned = False
    # The same one-shot set covers the leader and all adopted descendants;
    # never re-send after an interrupted or ambiguous signal delivery.
    while True:
        try:
            pf1_graceful.drain(signalled_children, child)
            if child is not None: child.wait()
            break
        except BaseException as exc:
            if not warned: notice('cleanup incomplete; retaining custody:', repr(exc)); warned = True
            try: time.sleep(.5)
            except BaseException: pass
    if child_fd is not None: os.close(child_fd)
if child is None:
    raise SystemExit(1)

if failure is None:
    try:admitted(gpu_owner,gpu_identity)
    except AdmissionLost as exc:
        admission_lost=True
        failure='post-drain admission loss: '+str(exc)
    except BaseException as exc:
        admission_lost=True
        failure='post-drain admission exception: '+repr(exc)
elapsed = time.monotonic() - started
if failure is None and child.returncode == 0 and os.environ.get("HIL_SMOKE_NORMAL") == "1" and elapsed < 60:
    failure = "normal smoke shorter than 60s"
if failure is None and elapsed > 300:
    failure = 'elapsed including cleanup exceeds 300s'
print(json.dumps({'schema': 'hil15-r11-smoke-supervisor/v1', 'elapsed_s': elapsed,
                  'sampled_peak_tree_rss_bytes': peak, 'samples': samples,
                  'verified_exited_processes': exited_processes, 'verified_exited_threads': exited_threads,
                  'per_process_address_space_limit_bytes': ceiling,
                  'rss_scope': 'sum of sampled resident pages across owned process tree; sampling may miss transients and double-count shared pages',
                  'leader_pid': child.pid, 'leader_birth': None if birth is None else birth[1],
                  'child_rc': child.returncode, 'children_drained': True, 'failure': failure}), flush=True)
sys.exit(78 if admission_lost else (1 if failure else child.returncode))
