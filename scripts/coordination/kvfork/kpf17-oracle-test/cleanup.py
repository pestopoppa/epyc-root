"""Stop only the captured GDB inferior, without signalling a reused PID."""
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
            send_signal=signal.pidfd_send_signal,close_fd=os.close):
    result={'pid':pid,'birth_ticks':birth,'signals':[],'verified_dead':False,'reason':None}
    if not isinstance(pid,int) or pid<=0 or not isinstance(birth,int) or birth<=0:
        result['reason']='missing captured PID or birth identity';return result
    def status():
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
