#!/usr/bin/env python3
"""Unqualified KPF50 supervisor component. No target adapter is installed."""
import ctypes
import fcntl
import hashlib
import json
import os
import runpy
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

D=Path(__file__).resolve().parent
ORDER=('full','mask','mask','full')
STOPPED=False

def stop_signal(signum, frame):
    global STOPPED
    STOPPED=True

def birth(pid):
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]

# Orphan descendants reparent to this job, so an intermediate exit cannot hide them.
if ctypes.CDLL(None).prctl(36, 1, 0, 0, 0)!=0:
    raise RuntimeError('subreaper setup failed')

def child_setup(parent):
    libc=ctypes.CDLL(None)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) or os.getppid()!=parent:
        os._exit(64)

def children(pid):
    result=set()
    for task in Path(f'/proc/{pid}/task').glob('*'):
        try: result.update(map(int,(task/'children').read_text().split()))
        except FileNotFoundError: pass
    return result

def capture(pid, owned):
    if pid in owned:
        if alive(owned[pid]): return
        try: current=birth(pid)
        except (ProcessLookupError,FileNotFoundError): return
        if current==owned[pid][0]: return
        # Numeric PID was reused by a new descendant; retain only its fresh pidfd.
        os.close(owned.pop(pid)[1])
    try:
        token=birth(pid); fd=os.pidfd_open(pid)
        if birth(pid)!=token:
            os.close(fd); raise RuntimeError('child identity changed during capture')
        owned[pid]=(token,fd)
    except ProcessLookupError: pass
    except FileNotFoundError: pass

def alive(item):
    return not select.select([item[1]],[],[],0)[0]

def send(pid,item,sig):
    if alive(item):
        if birth(pid)!=item[0]:
            raise RuntimeError('owned process birth changed')
        try: signal.pidfd_send_signal(item[1],sig)
        except ProcessLookupError: pass

def discover(owned, freeze=False):
    # Direct children are either Popen children or adopted descendants of this job.
    # Capture/freeze parents before reading their child lists, preventing fork escape.
    queue=list(children(os.getpid()))+list(owned)
    seen=set()
    while queue:
        pid=queue.pop()
        if pid in seen: continue
        seen.add(pid); capture(pid,owned)
        item=owned.get(pid)
        if item is None or not alive(item): continue
        if freeze:
            send(pid,item,signal.SIGSTOP)
            stop_deadline=time.monotonic()+5
            while alive(item):
                try: state=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
                except FileNotFoundError: break
                if state in ('T','t','Z','X'): break
                if time.monotonic()>=stop_deadline:
                    raise RuntimeError('owned process failed to freeze')
                time.sleep(.01)
        queue.extend(children(pid))

def cleanup(owned,p):
    # Freeze the entire captured subtree before graceful termination; then recapture
    # any forks during TERM grace and freeze again before KILL. No process groups.
    discover(owned,freeze=True)
    for pid,item in list(owned.items()):
        send(pid,item,signal.SIGTERM); send(pid,item,signal.SIGCONT)
    deadline=time.monotonic()+5
    while any(alive(item) for item in owned.values()) and time.monotonic()<deadline:
        discover(owned)
        time.sleep(.05)
    discover(owned,freeze=True)
    for pid,item in list(owned.items()): send(pid,item,signal.SIGKILL)
    deadline=time.monotonic()+5
    while any(alive(item) for item in owned.values()) and time.monotonic()<deadline:
        time.sleep(.05)
    # A parent can exit while an adopted child becomes visible. Recapture direct
    # children after the first kill pass; do not infer a drained subtree from old fds.
    discover(owned,freeze=True)
    for pid,item in list(owned.items()): send(pid,item,signal.SIGKILL)
    deadline=time.monotonic()+5
    while any(alive(item) for item in owned.values()) and time.monotonic()<deadline:
        time.sleep(.05)
    if any(alive(item) for item in owned.values()):
        raise RuntimeError('owned descendant remains alive')
    p.wait(timeout=1)
    for pid,(token,fd) in owned.items():
        try: os.waitpid(pid,os.WNOHANG)
        except ChildProcessError: pass
        os.close(fd)
    # Zombies are reaped above; any remaining direct child invalidates completion.
    if children(os.getpid()):
        raise RuntimeError('unreaped or uncaptured direct child remains')


def durable_json(path, data):
    # O_EXCL means an exposed or incomplete unit is never silently replaced.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(data,stream,sort_keys=True); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    finally:
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)

def boundary():
    if STOPPED or Path(os.environ['FILLER_STOPFILE']).exists():
        raise RuntimeError('STOP')
    if time.time()>=float(os.environ['FILLER_DEADLINE']):
        raise RuntimeError('grant deadline')

def model_admission():
    # Outer dependency seal anchors both the admission checker and its seal file.
    for path,digest in json.loads((D/'dependencies.json').read_text()).items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:
            raise ValueError('external admission seal changed: '+path)
    runpy.run_path(str(D.parent/'kpf50-model-admission-20261105'/'check_models.py'),run_name='__main__')

def execute(command, out):
    model_admission()
    owned={}; parent=os.getpid()
    with (out/'stdout').open('xb') as stdout, (out/'stderr').open('xb') as stderr:
        process=subprocess.Popen(command,cwd=D,stdout=stdout,stderr=stderr,
                                 preexec_fn=lambda: child_setup(parent))
        try:
            capture(process.pid,owned)
            durable_json(out/'root-birth.json',{'pid':process.pid,'birth':owned[process.pid][0]})
            while process.poll() is None:
                discover(owned); boundary(); time.sleep(.05)
        finally:
            # Any cleanup failure propagates and prevents a terminal success receipt.
            cleanup(owned,process)
        if process.returncode!=0:
            raise RuntimeError('window adapter failed: '+str(process.returncode))
    model_admission()  # Drift after use is failure/UNKNOWN, never accepted output.
    durable_json(out/'cleanup.json',{'verified_dead':True,'captured_pids':sorted(owned)})

def main():
    if len(sys.argv)!=1:
        raise ValueError('no command or path overrides permitted')
    seals=json.loads((D/'seals.json').read_text())
    for name,digest in seals.items():
        if hashlib.sha256((D/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('input seal changed: '+name)
    if set(seals)!={'supervisor.py','plan.json','dependencies.json'}:
        raise ValueError('incomplete runtime seal set')
    plan=json.loads((D/'plan.json').read_text())
    # This component deliberately cannot launch target windows until a reviewed
    # per-window adapter and its complete dependency seals are integrated.
    if plan.get('status')!='QUALIFIED_WINDOW_ADAPTER':
        raise ValueError('UNQUALIFIED: no target adapter installed')
    if plan.get('receipt_validator_status')!='QUALIFIED_SEALED_NATIVE_VALIDATOR':
        raise ValueError('UNQUALIFIED: native receipt validator absent')
    for key in ('FILLER_ID','FILLER_END','FILLER_DEADLINE','FILLER_STOPFILE','FILLER_CPUS','FILLER_PIDFILE'):
        if not os.environ.get(key): raise ValueError('missing grant contract: '+key)
    if os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1':
        raise ValueError('target supervisor forbidden in publisher smoke')
    if not time.time()<float(os.environ['FILLER_DEADLINE'])<float(os.environ['FILLER_END']):
        raise ValueError('invalid grant deadline')
    if plan['order']!=list(ORDER) or len(plan['commands'])!=4:
        raise ValueError('predeclared four-window sequence required')
    ledger=Path(plan['lineage_ledger'])
    if not ledger.is_absolute(): raise ValueError('absolute lineage ledger required')
    ledger.mkdir(parents=True,exist_ok=True)
    if ledger.resolve(strict=True)!=ledger:
        raise ValueError('lineage ledger symlink substitution')
    directory=os.open(ledger.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)
    lock=os.open(ledger/'owner.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # Never resume from any prior exposure, even under a fresh FILLER_ID.
    if any(ledger.glob('window-*.exposed.json')):
        raise ValueError('lineage already exposed; no redraw or automatic resume')
    attempt=ledger/'attempt'
    attempt.mkdir(exist_ok=False)
    for index,(scenario,command) in enumerate(zip(ORDER,plan['commands']),1):
        boundary()
        if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command):
            raise ValueError('invalid window argv')
        out=attempt/str(index); out.mkdir()
        # Conservative point of no return: fsync before spawning any adapter.
        durable_json(ledger/f'window-{index}.exposed.json',
                     {'index':index,'scenario':scenario,'row':os.environ['FILLER_ID'],
                      'time_ns':time.time_ns(),'command':command,
                      'semantics':'reserved before spawn; never retry automatically'})
        execute(command,out)
        receipt=out/'window-result.json'
        if receipt.is_symlink() or not receipt.is_file():
            raise ValueError('native receipt missing or symlinked')
        result=json.loads(receipt.read_text())
        if (result.get('window_index')!=index or result.get('scenario')!=scenario or
            result.get('row_id')!=os.environ['FILLER_ID'] or
            result.get('command_sha256')!=hashlib.sha256(json.dumps(command,separators=(',',':')).encode()).hexdigest() or
            result.get('status')!='VALID_FIRST_QUALIFYING_STEP' or result.get('partial') is not False):
            raise ValueError('missing bound window validation receipt')
        durable_json(out/'accepted.json',{'index':index,'scenario':scenario,'cleanup_verified':True})
    boundary()
    durable_json(ledger/'COMPLETE.json',{'status':'DIAGNOSTIC_COMPLETE','windows':4,
                 'cleanup_verified':True,'gate_verdict':None})
    os.close(lock)

if __name__=='__main__':
    signal.signal(signal.SIGTERM,stop_signal)
    signal.signal(signal.SIGINT,stop_signal)
    main()
