"""Stop only the captured GDB inferior, without signalling a reused PID."""
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import time


def identity(pid):
    try:
        # comm is parenthesized and may contain spaces or ')'.
        rest=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return int(rest[19])
    except FileNotFoundError:
        return None


def absent(pid):
    p=subprocess.run(['/usr/bin/ps','-p',str(pid),'-o','pid='],capture_output=True,text=True,timeout=3)
    if p.returncode not in (0,1): raise RuntimeError('ps could not verify PID')
    return p.returncode == 1 and not Path(f'/proc/{pid}').exists()


def cleanup(pid,birth,timeout_s=3.0, *, clock=time.monotonic,sleep=time.sleep,
            read_identity=identity,verify_absent=absent,open_pidfd=os.pidfd_open,
            send_signal=signal.pidfd_send_signal,close_fd=os.close,reap=lambda pid: None):
    result={'pid':pid,'birth_ticks':birth,'signals':[],'verified_dead':False,'reason':None}
    if not isinstance(pid,int) or pid<=0 or not isinstance(birth,int) or birth<=0:
        result['reason']='missing captured PID or birth identity';return result
    def status():
        reap(pid)
        found=read_identity(pid)
        return 'gone' if found is None else ('same' if found==birth else 'reused')
    def final(st):
        if st=='reused': result['reason']='PID reused; no further signals';return result
        if st=='gone' and verify_absent(pid): result.update(verified_dead=True,reason='PID absent by ps and proc');return result
        result['reason']='PID not verified absent';return result
    st=status()
    if st!='same':return final(st)
    try:fd=open_pidfd(pid,0)
    except ProcessLookupError:return final(status())
    except OSError as exc:result['reason']='cannot open captured pidfd: '+str(exc);return result
    try:
        # Recheck after opening; pidfd pins whichever process was opened.
        st=status()
        if st!='same':return final(st)
        for sig in (signal.SIGTERM,signal.SIGKILL):
            st=status()
            if st!='same':return final(st)
            try:send_signal(fd,sig)
            except ProcessLookupError:return final(status())
            result['signals'].append(signal.Signals(sig).name)
            end=clock()+timeout_s
            while clock()<end:
                st=status()
                if st!='same':return final(st)
                sleep(.1)
        return final(status())
    finally:close_fd(fd)


def direct_children():
    """Read only this supervisor's kernel-owned child table."""
    found=set()
    for task in Path(f'/proc/{os.getpid()}/task').iterdir():
        try: found.update(int(x) for x in (task/'children').read_text().split())
        except FileNotFoundError: pass
    return found


def prepare_adoption():
    """Require an exclusive, single-threaded supervisor before spawning GDB."""
    if len(list(Path(f'/proc/{os.getpid()}/task').iterdir())) != 1:
        raise RuntimeError('adoption requires a single-threaded supervisor')
    if direct_children():
        raise RuntimeError('adoption requires no pre-existing children')
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(ctypes.c_int(36),ctypes.c_ulong(1),0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
    value=ctypes.c_int()
    if libc.prctl(ctypes.c_int(37),ctypes.byref(value),0,0,0)!=0 or value.value!=1:
        raise RuntimeError('subreaper status not verified')


def reap_child(pid):
    try: os.waitpid(pid,os.WNOHANG)
    except ChildProcessError: pass


def drain_adopted(timeout_s=12):
    """After GDB is reaped, capture and drain adopted children, never groups.

    The caller must have passed prepare_adoption before its sole Popen and must
    not spawn anything else until this returns. No arbitrary process scan is used.
    """
    end=time.monotonic()+timeout_s
    records=[]
    while True:
        children=direct_children()
        if not children: return {'verified_dead':True,'children':records}
        if time.monotonic()>=end:
            raise RuntimeError('adopted-child drain deadline exceeded')
        for pid in children:
            if time.monotonic()>=end:
                raise RuntimeError('adopted-child drain deadline exceeded')
            birth=identity(pid)
            if birth is None:
                if not absent(pid): raise RuntimeError('adopted identity unavailable')
                continue
            budget=min(1.0,max(0.01,(end-time.monotonic())/2))
            record=cleanup(pid,birth,timeout_s=budget,reap=reap_child)
            records.append(record)
            if not record['verified_dead']:
                raise RuntimeError('adopted child death not verified: '+str(record))
