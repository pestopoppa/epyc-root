"""Private, unvalidated Linux ownership primitive. Never signal a numeric PID."""
import ctypes, json, os, select, signal, stat, subprocess, sys, time
from pathlib import Path

SAFE_PATH='/usr/bin:/bin'
TRUSTED_BARE={'numactl','taskset','env'}
# Reviewed launch-environment knobs the runner may set through the env wrapper (runtime_env_prefix + scenario_device_env).
ENV_NAMES={'LD_LIBRARY_PATH','OMP_NUM_THREADS','ROCR_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES','CUDA_VISIBLE_DEVICES'}

def _env_name_ok(name):
    return name in ENV_NAMES or (name.startswith('GGML_') and name.replace('_','').isalnum())

def resolve_env(binary, rest, depth):
    # env only carries reviewed `-u NAME` / NAME=VALUE tokens; the first other token is the wrapped command and is
    # validated by the same rules as any top-level argv (numactl/taskset chain, absolute path, no relative/bare).
    i=0; head=[]
    while i<len(rest):
        t=rest[i]
        if t=='-u':
            if i+1>=len(rest) or not _env_name_ok(rest[i+1]): raise ValueError('unreviewed env unset')
            head+=[t,rest[i+1]]; i+=2; continue
        if t.startswith('-') or '=' not in t.split('/',1)[0]: break
        if not _env_name_ok(t.split('=',1)[0]): raise ValueError('unreviewed env assignment')
        head.append(t); i+=1
    if i>=len(rest): raise ValueError('env wrapper without command')
    if rest[i] in ('env','/usr/bin/env') or depth: raise ValueError('nested env wrapper forbidden')
    return [str(binary),*head,*resolve_argv(rest[i:],depth+1)]

def resolve_argv(argv,depth=0):
    if not argv or not isinstance(argv[0],str): raise ValueError('missing executable')
    name=argv[0]
    if '/' not in name:
        if name not in TRUSTED_BARE: raise ValueError('unbound bare executable')
        candidate=Path('/usr/bin')/name
    else:
        candidate=Path(name)
        if not candidate.is_absolute(): raise ValueError('relative executable forbidden')
    binary=candidate.resolve(strict=True)
    if '/' not in name or name in ('/usr/bin/numactl','/usr/bin/taskset','/usr/bin/env'):
        # /usr/bin/env is a link into the root-owned uutils multicall dir on this host's image; no other parent is trusted.
        allowed={Path('/usr/bin')}|({Path('/usr/lib/cargo/bin/coreutils')} if binary.name=='env' else set())
        if binary.parent not in allowed: raise ValueError('untrusted wrapper target')
        for component in (*reversed(binary.parents),binary):
            info=component.stat()
            if info.st_uid!=0 or info.st_mode & (stat.S_IWGRP|stat.S_IWOTH):
                raise ValueError('wrapper path is not root-owned and immutable to this user')
    if not binary.is_file() or not os.access(binary,os.X_OK):
        raise ValueError('executable unavailable')
    if binary.name=='env' and name in ('env','/usr/bin/env'):
        return resolve_env(binary,argv[1:],depth)
    if binary.name=='numactl':
        if len(argv)<4 or argv[2]!='--' or argv[3]!='taskset':
            raise ValueError('unexpected NUMA wrapper chain')
        resolve_argv(['taskset'])  # check nested binary ownership before PATH exec
    return [str(binary),*argv[1:]]

def birth(pid):
    return int(Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()[19])

def exited(fd):
    return bool(select.select([fd],[],[],0)[0])

def stop(child, fd, expected):
    # The fd binds the kernel task; expected birth is provenance, not a signal target.
    if not exited(fd):
        try: signal.pidfd_send_signal(fd,signal.SIGTERM)
        except ProcessLookupError: pass
        if not select.select([fd],[],[],10)[0]:
            try: signal.pidfd_send_signal(fd,signal.SIGKILL)
            except ProcessLookupError: pass
            if not select.select([fd],[],[],10)[0]: raise RuntimeError('pidfd exit not confirmed')
    child.wait(timeout=10)
    if not exited(fd): raise RuntimeError('pidfd exit not confirmed')

def require_containment():
    cg=Path(os.environ['M4_OWNED_CGROUP']).resolve(strict=True)
    root=Path('/sys/fs/cgroup').resolve(strict=True)
    relative=cg.relative_to(root)
    membership='0::/'+relative.as_posix()
    if membership not in Path('/proc/self/cgroup').read_text().splitlines():
        raise RuntimeError('process is outside watch-owned cgroup')
    if not (cg/'cgroup.kill').is_file(): raise RuntimeError('cgroup.kill absent')
    return cg

def spawn(argv, *, env, stdout=None, stderr=None, registry=None, attach=None):
    argv=resolve_argv(argv)
    env=dict(env,PATH=SAFE_PATH)  # numactl resolves nested taskset on this fixed path
    if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
        raise RuntimeError('pidfd API required')
    if attach is None: require_containment()
    readfd,writefd=os.pipe2(os.O_CLOEXEC)
    child=None; fd=None
    try:
        expected_parent=birth(os.getpid())
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--gate',
                 str(readfd),str(os.getpid()),str(expected_parent),'--',*argv]
        child=subprocess.Popen(command,env=env,stdout=stdout,stderr=stderr,
                               pass_fds=(readfd,),start_new_session=True)
        os.close(readfd); readfd=None
        # Gate cannot exec argv until pidfd capture, cgroup attach and registry fsync.
        fd=os.pidfd_open(child.pid)
        stamp=birth(child.pid)
        if exited(fd) or stamp!=birth(child.pid): raise RuntimeError('gate identity lost')
        if attach is not None:
            (attach/'cgroup.procs').write_text(str(child.pid))
            membership='0::/'+attach.resolve().relative_to(Path('/sys/fs/cgroup').resolve()).as_posix()
            if membership not in Path('/proc',str(child.pid),'cgroup').read_text().splitlines():
                raise RuntimeError('gate cgroup attachment failed')
        if registry is not None:
            with Path(registry).open('a') as output:
                output.write(f'{child.pid} {stamp}\n'); output.flush(); os.fsync(output.fileno())
        os.write(writefd,b'G')
        return child,fd,stamp
    except BaseException:
        # EOF prevents exec even if pidfd_open failed. No Popen.kill/terminate fallback.
        os.close(writefd); writefd=None
        if child is not None:
            if fd is not None:
                try: stop(child,fd,None)
                finally: os.close(fd)
            else: child.wait(timeout=10)
        raise
    finally:
        if readfd is not None: os.close(readfd)
        if writefd is not None: os.close(writefd)

def gate():
    readfd,parent,stamp=int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4])
    argv=sys.argv[6:]
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(1,signal.SIGKILL,0,0,0)!=0: raise OSError(ctypes.get_errno(),'PR_SET_PDEATHSIG')
    if os.getppid()!=parent or birth(parent)!=stamp: raise RuntimeError('parent lost before gate')
    token=os.read(readfd,1); os.close(readfd)
    if token!=b'G' or os.getppid()!=parent or birth(parent)!=stamp:
        raise RuntimeError('closed gate or parent lost')
    require_containment()
    argv=resolve_argv(argv)
    os.environ['PATH']=SAFE_PATH
    binary=Path(argv[0])
    if binary.stat().st_mode & (stat.S_ISUID|stat.S_ISGID):
        raise RuntimeError('privileged exec would clear parent-death protection')
    os.execve(str(binary),argv,dict(os.environ))

if __name__=='__main__':
    if len(sys.argv)<7 or sys.argv[1]!='--gate' or sys.argv[5]!='--':
        raise SystemExit('internal gate only')
    gate()
