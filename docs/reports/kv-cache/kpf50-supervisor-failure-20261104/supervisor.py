#!/usr/bin/env python3
"""Isolated candidate: supervise one owned window command via newline JSON IPC.

This is a model-free process-boundary candidate, not an integrated profiler.
"""
import ctypes
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
import cleanup_receipt as cleanup


requested_signal = None

def request_stop(signum, frame):
    global requested_signal
    requested_signal = signum

def send(data):
    print(json.dumps(data, sort_keys=True), flush=True)


def terminate(pid, ticks, sig):
    if pid not in cleanup.children() or cleanup.birth(pid) != ticks:
        raise RuntimeError('refusing changed or non-child PID')
    try:
        fd = os.pidfd_open(pid)
    except OSError:
        # An unreaped direct child has a reserved PID; prove ownership again.
        if pid not in cleanup.children() or cleanup.birth(pid) != ticks:
            raise RuntimeError('refusing pidfd fallback for changed child')
        os.kill(pid, sig)
        return
    try:
        if pid not in cleanup.children() or cleanup.birth(pid) != ticks:
            raise RuntimeError('PID changed after pidfd open')
        try:
            signal.pidfd_send_signal(fd, sig)
        except ProcessLookupError:
            pass
    finally:
        os.close(fd)


def emergency_drain(guard, timeout=5):
    """Best-effort drain after IPC/protocol failures; never publish a receipt."""
    end=time.monotonic()+timeout
    while cleanup.children():
        if time.monotonic()>=end:raise TimeoutError('emergency drain incomplete')
        for pid in cleanup.children():
            b=cleanup.birth(pid)
            if b is None:continue
            if pid not in guard.captured:guard.capture(pid,b)
            if guard.captured[pid]['birth_ticks'] != b:raise RuntimeError('emergency PID reused')
            event=os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
            if event is None:terminate(pid,b,signal.SIGKILL)
            else:guard.reap(pid)
        # Bounded kernel scheduling wait; supervisor is a dedicated process.
        time.sleep(.01)


def run(cfg):
    if not isinstance(cfg, dict) or set(cfg) != {'argv','directory','window','run_id','timeout_s'}:
        raise ValueError('invalid configuration')
    argv=cfg['argv']
    if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x for x in argv):
        raise ValueError('invalid argv')
    duration=cfg['timeout_s']
    if type(duration) not in (int,float) or not 0 < duration <= 3600:
        raise ValueError('invalid deadline')
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(36,1,0,0,0):raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
    guard=cleanup.Guard()
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, request_stop)
    proc=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
    pid=proc.pid
    try:
        b=cleanup.birth(pid)
        if b is None:raise RuntimeError('initial child identity unavailable')
        guard.capture(pid,b)
        send({'event':'started','pid':pid,'birth_ticks':b})
        selector=selectors.DefaultSelector();selector.register(sys.stdin,selectors.EVENT_READ)
    except BaseException:
        # Direct child remains unreaped by this single-threaded supervisor.
        if pid in cleanup.children():
            try:
                fd=os.pidfd_open(pid)
            except OSError:
                if pid not in cleanup.children():raise
                os.kill(pid,signal.SIGKILL)
            else:
                try:signal.pidfd_send_signal(fd,signal.SIGKILL)
                finally:os.close(fd)
        try:proc.wait(timeout=5)
        finally:emergency_drain(guard)
        raise
    deadline=time.monotonic()+duration; stopping=False; reason=None; kill_at=None; root_reaped=False; killed_adopted=False
    try:
        while True:
            now=time.monotonic()
            if requested_signal is not None and not stopping:
                stopping=True;reason='supervisor-signal';kill_at=now+0.25
                if not root_reaped:terminate(pid,b,signal.SIGTERM)
            if now >= deadline and not stopping:
                stopping=True;reason='deadline';kill_at=now+0.25
                if not root_reaped:terminate(pid,b,signal.SIGTERM)
            if selector.select(timeout=0.02):
                line=sys.stdin.readline()
                if not line:
                    selector.unregister(sys.stdin)
                    if not stopping:
                        stopping=True;reason='ipc-eof';kill_at=now+0.25
                        if not root_reaped:terminate(pid,b,signal.SIGTERM)
                else:
                    try:message=json.loads(line)
                    except ValueError: message={}
                    if message != {'command':'stop'}:
                        stopping=True;reason='invalid-ipc';kill_at=now+0.25
                    elif not stopping:
                        stopping=True;reason='requested-stop';kill_at=now+0.25
                    if not root_reaped:terminate(pid,b,signal.SIGTERM)
            if not root_reaped:
                try: event=os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                except ChildProcessError as exc:raise RuntimeError('root reaped externally') from exc
                if event is not None:
                    guard.reap(pid);root_reaped=True
                elif stopping and time.monotonic() >= kill_at:
                    terminate(pid,b,signal.SIGKILL);kill_at=time.monotonic()+0.25
            if root_reaped:
                for child in cleanup.children():
                    if child in guard.captured:continue
                    cb=cleanup.birth(child)
                    if cb is None:raise RuntimeError('adopted child identity unavailable')
                    guard.capture(child,cb)
                    event=os.waitid(os.P_PID,child,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                    if event is None:
                        killed_adopted=True;terminate(child,cb,signal.SIGKILL)
                    else:guard.reap(child)
                for child, info in list(guard.captured.items()):
                    if info['reaped']:continue
                    event=os.waitid(os.P_PID,child,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                    if event is not None:guard.reap(child)
                if all(v['reaped'] for v in guard.captured.values()) and not cleanup.children():break
                if time.monotonic()>deadline+10:raise TimeoutError('drain incomplete')
        payload=guard.publish(Path(cfg['directory']),cfg['window'],cfg['run_id'])
        status=guard.captured[pid]['wait_status']
        normal=not stopping and not killed_adopted and os.WIFEXITED(status) and os.WEXITSTATUS(status)==0
        send({'event':'finished','normal':normal,'reason':reason,'root_wait_status':status,
              'cleanup':payload,'killed_adopted':killed_adopted})
        return 0 if normal else 75
    finally:
        selector.close()
        if cleanup.children():emergency_drain(guard)

if __name__=='__main__':
    try:
        cfg=json.loads(sys.stdin.readline());sys.exit(run(cfg))
    except Exception as exc:
        send({'event':'error','message':type(exc).__name__+': '+str(exc)})
        sys.exit(1)
