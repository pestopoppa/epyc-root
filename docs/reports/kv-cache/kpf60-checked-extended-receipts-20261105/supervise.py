#!/usr/bin/env python3
"""Supervise one owned build and reap its descendants on every exit path."""
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

requested = False

def stop_signal(signum, frame):
    global requested
    requested = True

def birth(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
    except FileNotFoundError:
        return None

def children():
    return [int(x) for x in Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()]

def enable_subreaper():
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
    enabled=ctypes.c_int()
    if libc.prctl(37,ctypes.byref(enabled),0,0,0)!=0 or enabled.value!=1:
        raise RuntimeError('subreaper verification failed')

def kill_owned(pid,ticks):
    # Child PID remains reserved until this single-threaded parent reaps it.
    if pid not in children() or birth(pid)!=ticks:raise RuntimeError('child identity changed')
    try:fd=os.pidfd_open(pid)
    except OSError:
        if pid not in children() or birth(pid)!=ticks:raise RuntimeError('child identity changed')
        try:os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:pass
        return
    try:
        if pid not in children() or birth(pid)!=ticks:raise RuntimeError('child identity changed')
        try:signal.pidfd_send_signal(fd,signal.SIGKILL)
        except ProcessLookupError:pass
    finally:os.close(fd)

def drain(proc,ticks,timeout=10):
    end=time.monotonic()+timeout
    killed=False
    if proc.poll() is None:
        kill_owned(proc.pid,ticks);killed=True
        proc.wait(timeout=max(.01,end-time.monotonic()))
    while children():
        if time.monotonic()>=end:raise TimeoutError('child drain timed out')
        for pid in children():
            b=birth(pid)
            if b is None:continue
            kill_owned(pid,b);killed=True
            while True:
                got,_=os.waitpid(pid,os.WNOHANG)
                if got==pid:break
                if time.monotonic()>=end:raise TimeoutError('child reap timed out')
                time.sleep(.01)
            if birth(pid) is not None:raise RuntimeError('child not absent after reap')
    try:os.waitpid(-1,os.WNOHANG)
    except ChildProcessError:pass
    else:raise RuntimeError('child-free state not established')
    return killed

def run(stop,deadline,command,receipt):
    global requested
    if requested or stop.exists() or time.time()>=deadline:return 75
    enable_subreaper()
    if children():raise RuntimeError('unexpected pre-existing child')
    proc=subprocess.Popen(command)
    receipt.update(pid=proc.pid, command=command)
    # The owned PID is reserved while this child remains unreaped.
    ticks=birth(proc.pid)
    receipt['birth_ticks']=ticks
    if ticks is None:
        proc.wait(timeout=5)
        drain(proc,0)
        return 1
    interrupted=False
    try:
        while True:
            try:
                rc=proc.wait(timeout=.1)
                break
            except subprocess.TimeoutExpired:
                if requested or stop.exists() or time.time()>=deadline:
                    interrupted=True
                    rc=75
                    break
    finally:
        killed=drain(proc,ticks)
        receipt.update(cleanup_verified=True, cleanup_killed=killed, child_absent=birth(proc.pid) is None)
    receipt.update(command_exit=proc.returncode, interrupted=interrupted)
    if interrupted:return 75
    # A compiler that outlived its parent means the build did not complete cleanly.
    return 1 if killed else rc

def main():
    try:receipt_path,stop,deadline,*command=sys.argv[1:]
    except ValueError:return 64
    if not command or not deadline.isdigit():return 64
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop_signal)
    receipt={'cleanup_verified':False,'command_exit':None}
    try:
        result=run(Path(stop),int(deadline),command,receipt)
        receipt['supervisor_exit']=result
        return result
    finally:
        Path(receipt_path).write_text(__import__('json').dumps(receipt,sort_keys=True)+'\n')

if __name__=='__main__':sys.exit(main())
