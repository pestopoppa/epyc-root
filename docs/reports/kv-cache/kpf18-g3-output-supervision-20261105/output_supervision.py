"""New isolated supervisor, NOT installed in any native candidate. Sampled cap only."""
import os,signal,subprocess,time
from pathlib import Path
import owned_drain

def size(root):
    total=0
    for p in Path(root).rglob('*'):
        if p.is_symlink(): raise ValueError('output symlink')
        if p.is_file():
            s=p.stat();total+=max(s.st_size,s.st_blocks*512)
    return total

def run(argv,root,stop,deadline,cap,interval=.02):
    if owned_drain.children():raise RuntimeError('preexisting children')
    owned_drain.enable()
    root=Path(root);root.mkdir(exist_ok=False)
    samples=[];p=None;pidfd=None;reason='unknown';child_rc=None
    def sample(stage):
        n=size(root);samples.append({'monotonic':time.monotonic(),'bytes':n,'stage':stage});return n
    sample('before-launch')
    try:
        p=subprocess.Popen(argv,start_new_session=True)
        pidfd=os.pidfd_open(p.pid)
        while True:
            n=sample('running')
            if Path(stop).exists():reason='STOP';break
            if time.monotonic()>=deadline:reason='deadline';break
            if n>=cap:reason='budget';break
            child_rc=p.poll()
            if child_rc is not None:reason='normal' if child_rc==0 else 'child-failure';break
            time.sleep(interval)
    finally:
        try:
            if p is not None and p.poll() is None:
                # Only the explicitly captured child's pidfd is signalled.
                # Adopted descendants are captured individually by owned_drain.
                if pidfd is not None:
                    try:signal.pidfd_send_signal(pidfd,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:p.wait(timeout=.3)
                    except subprocess.TimeoutExpired:
                        try:signal.pidfd_send_signal(pidfd,signal.SIGKILL)
                        except ProcessLookupError:pass
                        p.wait()
                else:
                    # pidfd acquisition failed: retain this subreaper and use the
                    # existing child-capture drain rather than abandon children.
                    owned_drain.drain()
                    p.wait()
            owned_drain.drain()
            sample('after-drain')
        finally:
            if pidfd is not None:os.close(pidfd)
    peak=max(s['bytes'] for s in samples)
    return {'reason':reason,'child_rc':child_rc,'pid':p.pid,'pid_absent':not Path('/proc',str(p.pid)).exists(),
            'children_after':owned_drain.children(),'samples':samples,'cap_bytes':cap,
            'sample_interval_s':interval,'observed_sampled_peak_bytes':peak,
            'observed_sampled_overshoot_bytes':max(0,peak-cap),'unsampled_peak':'unknown'}
