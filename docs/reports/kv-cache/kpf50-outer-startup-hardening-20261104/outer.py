#!/usr/bin/env python3
"""Model-free containment prototype; do not use for native workloads."""
import ctypes, json, os, selectors, signal, subprocess, sys, time
from pathlib import Path
import cleanup_receipt as c

stop_signal = None

def stop(sig, _frame):
    global stop_signal
    stop_signal = sig

def send(obj):
    print(json.dumps(obj, sort_keys=True), flush=True)

def kill_child(pid, birth, sig):
    if pid not in c.children() or c.birth(pid) != birth:
        raise RuntimeError('child identity changed')
    try:
        fd = os.pidfd_open(pid)
    except OSError:
        if pid not in c.children() or c.birth(pid) != birth:
            raise RuntimeError('child identity changed on fallback')
        os.kill(pid, sig)
        return
    try:
        if pid not in c.children() or c.birth(pid) != birth:
            raise RuntimeError('child identity changed after pidfd')
        try: signal.pidfd_send_signal(fd, sig)
        except ProcessLookupError: pass
    finally:
        os.close(fd)

def drain(timeout=5):
    end = time.monotonic() + timeout
    captured = []
    while c.children():
        if time.monotonic() >= end: raise TimeoutError('adopted child drain timeout')
        for pid in c.children():
            birth = c.birth(pid)
            if birth is None: continue
            e = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if e is None:
                kill_child(pid, birth, signal.SIGKILL)
            else:
                got, status = os.waitpid(pid, os.WNOHANG)
                if got != pid or c.birth(pid) is not None: raise RuntimeError('child not reaped')
                captured.append({'pid':pid, 'birth_ticks':birth, 'wait_status':status})
        time.sleep(.01)
    try: os.waitpid(-1, os.WNOHANG)
    except ChildProcessError: return captured
    raise RuntimeError('ECHILD not established')

def run():
    config = sys.stdin.buffer.readline()
    json.loads(config)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36,1,0,0,0) or not c.is_subreaper() or c.children():
        raise RuntimeError('subreaper precondition failed')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP): signal.signal(sig, stop)
    proc = subprocess.Popen([sys.executable, '-B', str(Path(__file__).with_name('supervisor.py'))],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    birth = None
    adopted = []
    try:
        pid = proc.pid
        birth = c.birth(pid)
        if birth is None: raise RuntimeError('supervisor initial birth absent')
        startup_fd = os.pidfd_open(pid)
        os.close(startup_fd)
        send({'event':'supervisor-started', 'pid':pid, 'birth_ticks':birth})
        sel = selectors.DefaultSelector()
        sel.register(sys.stdin.buffer, selectors.EVENT_READ, 'stdin')
        sel.register(proc.stdout, selectors.EVENT_READ, 'stdout')
        pending = b''; interrupted = False; termination_at = None; output_broken = False; inner_success = False
        try:
            try:
                proc.stdin.write(config); proc.stdin.flush()
            except (BrokenPipeError, OSError): interrupted = True
            while proc.poll() is None:
                if stop_signal is not None or interrupted:
                    interrupted = True
                    if termination_at is None:
                        kill_child(pid, birth, signal.SIGTERM); termination_at=time.monotonic()+.5
                    elif time.monotonic() >= termination_at:
                        kill_child(pid, birth, signal.SIGKILL); termination_at=time.monotonic()+.5
                for key, _ in sel.select(.05):
                    if key.data == 'stdin':
                        data=os.read(key.fileobj.fileno(), 8192)
                        if not data:
                            sel.unregister(key.fileobj)
                            try: proc.stdin.close()
                            except OSError: pass
                        else:
                            try: proc.stdin.write(data); proc.stdin.flush()
                            except (BrokenPipeError, OSError): interrupted=True
                    else:
                        data=os.read(key.fileobj.fileno(), 8192)
                        if not data: sel.unregister(key.fileobj); continue
                        pending += data
                        while b'\n' in pending:
                            line,pending=pending.split(b'\n',1)
                            try:
                                event=json.loads(line)
                                if event.get('event') == 'finished' and event.get('normal') is True:
                                    inner_success = True
                                send(event)
                            except BrokenPipeError: output_broken=True; interrupted=True
            # Reap root before draining adopted descendants.
            rc=proc.wait()
            # Drain any already-buffered final event without waiting for another producer.
            os.set_blocking(proc.stdout.fileno(), False)
            try: pending += os.read(proc.stdout.fileno(), 65536)
            except BlockingIOError: pass
            for line in pending.splitlines():
                event=json.loads(line)
                if event.get('event') == 'finished' and event.get('normal') is True:
                    inner_success = True
        finally:
            sel.close()
    finally:
        if proc.poll() is None:
            if pid not in c.children(): raise RuntimeError('supervisor ownership lost')
            current = c.birth(pid)
            if birth is not None and current != birth: raise RuntimeError('supervisor identity changed')
            if current is None:
                # An unreaped direct child has a reserved PID even if procfs is unavailable.
                os.kill(pid, signal.SIGKILL)
            else:
                kill_child(pid, current, signal.SIGKILL)
            proc.wait(timeout=5)
        adopted = drain()
    if not output_broken:
        send({'event':'outer-finished','supervisor_rc':rc,'adopted':adopted,
              'normal':rc==0 and inner_success and not interrupted and not adopted})
    return 0 if rc==0 and inner_success and not interrupted and not adopted else 75

if __name__=='__main__':
    try: sys.exit(run())
    except Exception as exc:
        try: send({'event':'outer-error','message':type(exc).__name__+': '+str(exc)})
        except BrokenPipeError: pass
        sys.exit(1)
