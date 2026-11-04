import os, signal, subprocess, time
from pathlib import Path

def interrupted(signum, frame):
    raise InterruptedError(f'signal {signum}')
signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)

def stopped():
    stop=os.environ.get('FILLER_STOPFILE')
    end=os.environ.get('FILLER_DEADLINE')
    return bool(stop and Path(stop).exists()) or bool(end and time.time() >= float(end))

def group_exists(pgid):
    try: os.killpg(pgid, 0); return True
    except ProcessLookupError: return False

def cleanup(child, grace):
    # Every group here was created and captured by this worker. Reap even if
    # its leader exits before a descendant that ignores TERM.
    old=signal.signal(signal.SIGTERM, signal.SIG_IGN)
    try:
        try: os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        end=time.monotonic()+grace
        while time.monotonic()<end and group_exists(child.pid):
            child.poll()
            time.sleep(.05)
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        child.wait()
        end=time.monotonic()+grace
        while time.monotonic()<end and group_exists(child.pid):
            time.sleep(.05)
        if group_exists(child.pid):
            raise RuntimeError(f"owned process group {child.pid} remains after SIGKILL")
    finally:
        signal.signal(signal.SIGTERM,old)

def run(cmd, log, env=None, timeout=None, grace=2):
    if stopped(): return 75
    child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
    start=time.monotonic()
    try:
        while child.poll() is None:
            if stopped() or (timeout and time.monotonic()-start>=timeout):
                raise InterruptedError('stop/deadline/timeout')
            time.sleep(.1)
        return child.wait()
    except BaseException:
        cleanup(child,grace)
        raise
