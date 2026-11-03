"""Spawn and stop M4 workload processes by pidfd.

`spawn` starts the argv in its own session, captures a pidfd and the birth stamp
before returning, and optionally (a) places the child in a delegated cgroup before
it execs and (b) appends `<pid> <birth>` to a server registry. Any argv is accepted,
including an `env NAME=VALUE ... numactl ... -- taskset ... /abs/binary` prefix; a
bare executable name is resolved on PATH. `stop` signals only through the pidfd.
"""
import os, select, shutil, signal, subprocess
from pathlib import Path

DEFAULT_PATH='/usr/bin:/bin'


def resolve_argv(argv, path=None):
    if not argv or not isinstance(argv[0],str) or not argv[0]: raise ValueError('missing executable')
    if '/' in argv[0]: return list(argv)
    binary=shutil.which(argv[0],path=path or DEFAULT_PATH)
    if binary is None: raise ValueError(f'executable not found on PATH: {argv[0]}')
    return [binary,*argv[1:]]


def birth(pid):
    return int(Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()[19])


def exited(fd):
    return bool(select.select([fd],[],[],0)[0])


def stop(child, fd, expected=None):
    # The pidfd binds the kernel task; `expected` (birth) is provenance only.
    if not exited(fd):
        try: signal.pidfd_send_signal(fd,signal.SIGTERM)
        except ProcessLookupError: pass
        if not select.select([fd],[],[],10)[0]:
            try: signal.pidfd_send_signal(fd,signal.SIGKILL)
            except ProcessLookupError: pass
            if not select.select([fd],[],[],10)[0]: raise RuntimeError('pidfd exit not confirmed')
    child.wait(timeout=10)
    if not exited(fd): raise RuntimeError('pidfd exit not confirmed')


def spawn(argv, *, env, stdout=None, stderr=None, registry=None, attach=None):
    env=dict(env); env.setdefault('PATH',DEFAULT_PATH)
    argv=resolve_argv(argv,env['PATH'])
    preexec=None
    if attach is not None:
        procs=str(Path(attach)/'cgroup.procs')
        def preexec():  # runs in the child before exec: it never runs outside the cgroup
            with open(procs,'w') as f: f.write('0')
    child=subprocess.Popen(argv,env=env,stdout=stdout,stderr=stderr,
                           start_new_session=True,preexec_fn=preexec)
    fd=None
    try:
        fd=os.pidfd_open(child.pid)  # unreaped child: the PID cannot be reused yet
        stamp=birth(child.pid)
        if registry is not None:
            with Path(registry).open('a') as output:
                output.write(f'{child.pid} {stamp}\n'); output.flush(); os.fsync(output.fileno())
        return child,fd,stamp
    except BaseException:
        if fd is not None:
            try: stop(child,fd)
            finally: os.close(fd)
        else:
            child.kill(); child.wait(timeout=10)
        raise
