#!/usr/bin/env python3
"""Hold the existing full CPU/GPU-quiet lease through M4 guardian cleanup.

Invoke with orchestrator's Python/venv and with a captured caller PID+birth.
The lease-holder is independent of the caller and passes the *same* locked
open file descriptions through the entry into its external guardian. Workload
processes do not inherit them. The guardian releases them only after drain.
"""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

import m4_cgroup_guard as guard

LOCK_ROOT = Path('/mnt/raid0/llm/tmp')


def lease_fds() -> tuple[int, ...]:
    expected = {f'cpu_region.GLOBAL.q{i}.lock' for i in range(4)} | {'gpu_quiet.lock'}
    found = {}
    for name in os.listdir('/proc/self/fd'):
        try:
            fd=int(name); path=Path(os.readlink(f'/proc/self/fd/{fd}'))
            if path.parent == LOCK_ROOT and path.name in expected:
                if path.name in found: raise ValueError('duplicate lease descriptor')
                found[path.name]=fd
        except FileNotFoundError:
            continue
    if set(found) != expected:
        raise RuntimeError('cross-role or GPU-quiet lease descriptor missing')
    for name,fd in found.items():
        fcntl.flock(fd, (fcntl.LOCK_SH if name == 'gpu_quiet.lock' else fcntl.LOCK_EX) | fcntl.LOCK_NB)
    return tuple(found[name] for name in sorted(found))


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caller-pid',type=int,required=True)
    parser.add_argument('--caller-birth',type=int,required=True)
    parser.add_argument('--timeout',type=float,default=0)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command and args.command[0]=='--' else args.command
    if not command:
        parser.error('entry command required')
    if os.getsid(0) != os.getpid():
        os.setsid()  # survive caller/session disappearance while draining
    caller_fd=guard._pin_process(args.caller_pid,args.caller_birth)
    proc=None; proc_fd=None; notice_r=None; notice_w=None; guardian_fd=None; guarded_cgroup=None
    try:
        os.environ['ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT']='1'
        sys.path.insert(0,'/workspace/repos/epyc-orchestrator')
        from src.runtime.gpu_quiet_lock import gpu_quiet_then_regions
        def caller_gone(): return bool(select.select([caller_fd],[],[],0)[0])
        with gpu_quiet_then_regions('bench', {'q0','q1','q2','q3'},gpu_quiet='shared',
                                   timeout_s=args.timeout,request_tag='inf22-m4-cpu',cancel_check=caller_gone):
            try:
                if caller_gone(): raise RuntimeError('caller exited before lease admission')
                fds=lease_fds()
                os.sched_setaffinity(0,set(range(96)))
                command=[s.replace('{owner_pid}',str(os.getpid())).replace('{owner_birth}',str(guard.birth(os.getpid()))) for s in command]
                notice_r,notice_w=os.pipe2(os.O_CLOEXEC)
                env=dict(os.environ,M4_LEASE_FDS=','.join(str(fd) for fd in fds),M4_GUARDIAN_NOTIFY_FD=str(notice_w))
                proc=subprocess.Popen(command,env=env,pass_fds=(*fds,notice_w))
                os.close(notice_w); notice_w=None
                proc_fd=os.pidfd_open(proc.pid)
                # The watcher reports its guardian before releasing any workload.
                while not select.select([proc_fd],[],[],0.1)[0]:
                    if notice_r is not None and select.select([notice_r],[],[],0)[0]:
                        payload=os.read(notice_r,128); os.close(notice_r); notice_r=None
                        if payload:
                            pid,stamp,cg=payload.decode().strip().split()
                            guarded_cgroup=Path(cg)
                            if guarded_cgroup.parent != Path('/sys/fs/cgroup') or not guarded_cgroup.name.startswith('m4-private-'): raise RuntimeError('invalid guardian cgroup')
                            try: guardian_fd=guard._pin_process(int(pid),int(stamp))
                            except (OSError, RuntimeError): guardian_fd=None
                    if caller_gone():
                        signal.pidfd_send_signal(proc_fd,signal.SIGTERM)
                        break
                rc=proc.wait()
                if notice_r is not None:
                    payload=os.read(notice_r,128); os.close(notice_r); notice_r=None
                    if payload:
                        pid,stamp,cg=payload.decode().strip().split()
                        guarded_cgroup=Path(cg)
                        if guarded_cgroup.parent != Path('/sys/fs/cgroup') or not guarded_cgroup.name.startswith('m4-private-'): raise RuntimeError('invalid guardian cgroup')
                        try: guardian_fd=guard._pin_process(int(pid),int(stamp))
                        except (OSError, RuntimeError): guardian_fd=None
                # Keep the lease until the independently surviving guardian exits.
                if guardian_fd is not None:
                    select.select([guardian_fd],[],[])
                if guarded_cgroup is not None:
                    guard.drain_or_hold(guarded_cgroup)
                return rc
            finally:
                # This finally is INSIDE both lock contexts. No exception may
                # release exclusion while an owned child or guardian remains.
                if proc is not None and proc.poll() is None:
                    if proc_fd is not None:
                        try: signal.pidfd_send_signal(proc_fd,signal.SIGTERM)
                        except ProcessLookupError: pass
                    proc.wait()
                if notice_r is not None:
                    payload=os.read(notice_r,128); os.close(notice_r); notice_r=None
                    if payload:
                        try:
                            pid,stamp,cg=payload.decode().strip().split()
                            guarded_cgroup=Path(cg)
                            if guarded_cgroup.parent != Path('/sys/fs/cgroup') or not guarded_cgroup.name.startswith('m4-private-'):
                                raise ValueError('invalid owned cgroup')
                            try: guardian_fd=guard._pin_process(int(pid),int(stamp))
                            except (OSError, RuntimeError): guardian_fd=None
                        except (UnicodeError,ValueError):
                            # Corrupt identity cannot prove a drain; hold the
                            # lease and expose the fault instead of releasing it.
                            print('M4 lease retained: corrupt guardian identity',file=sys.stderr,flush=True)
                            while True: time.sleep(60)
                if guardian_fd is not None:
                    select.select([guardian_fd],[],[])
                if guarded_cgroup is not None:
                    guard.drain_or_hold(guarded_cgroup)

    except (OSError, ValueError, RuntimeError) as exc:
        print(f'M4 lease owner refused: {exc}',file=sys.stderr)
        return 2
    finally:
        if proc is not None and proc.poll() is None:
            if proc_fd is not None:
                signal.pidfd_send_signal(proc_fd,signal.SIGTERM)
            proc.wait()
        if guardian_fd is not None:
            select.select([guardian_fd],[],[])
            os.close(guardian_fd)
        if notice_r is not None: os.close(notice_r)
        if notice_w is not None: os.close(notice_w)
        if proc_fd is not None: os.close(proc_fd)
        os.close(caller_fd)


if __name__=='__main__':
    raise SystemExit(main())
