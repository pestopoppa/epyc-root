#!/usr/bin/env python3
"""Model-free GDB continue/exit and unsignalled cleanup prerequisite check."""
import ctypes, hashlib, json, os, re, signal, shutil, subprocess, tempfile, time
from pathlib import Path

D=Path(__file__).resolve().parent
GDB=Path('/usr/bin/gdb')
libc=ctypes.CDLL(None,use_errno=True)


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def atomic(p, obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(obj,f,sort_keys=True,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    check_stop()
    os.replace(tmp,p)
    fd=os.open(p.parent,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def proc_birth(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19])
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return None


def set_subreaper():
    if libc.prctl(ctypes.c_int(36),ctypes.c_ulong(1),0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
    value=ctypes.c_int()
    if libc.prctl(ctypes.c_int(37),ctypes.byref(value),0,0,0)!=0 or value.value!=1:
        raise RuntimeError('subreaper status not verified')


STOP=False
OWNED={}
SIGNALS=[]


def check_stop():
    if STOP or (D/'STOP').exists() or (D/'STOP').is_symlink():
        raise RuntimeError('STOP flag/file prohibits publication or completion')


def request_stop(_sig, _frame):
    global STOP
    STOP=True


def direct_children(pid):
    result=set()
    try:
        for task in Path(f'/proc/{pid}/task').iterdir():
            try: result.update(int(x) for x in (task/'children').read_text().split())
            except FileNotFoundError: pass
    except FileNotFoundError: pass
    return result


def capture(pid):
    if pid in OWNED: return
    # Open the stable handle first; never signal a numeric PID.
    try: fd=os.pidfd_open(pid)
    except ProcessLookupError: return
    birth=proc_birth(pid)
    if birth is None:
        os.close(fd)
        raise RuntimeError(f'cannot establish child birth identity: {pid}')
    OWNED[pid]=(birth,fd)
    info=Path(f'/proc/self/fdinfo/{fd}').read_text()
    if not re.search(r'^Pid:\s*'+str(pid)+r'\s*$',info,re.M) or proc_birth(pid)!=birth:
        raise RuntimeError(f'pidfd/birth identity uncertain: {pid}')


def capture_tree(root):
    frontier=[root]; seen=set()
    while frontier:
        parent=frontier.pop()
        if parent in seen: continue
        seen.add(parent)
        for child in direct_children(parent):
            capture(child); frontier.append(child)


def cleanup_all():
    """Drain captured descendants and unknown adoptees of our verified subreaper."""
    set_subreaper()
    deadline=time.monotonic()+4
    term=set(); killed=set()
    errors=[]
    while time.monotonic()<deadline:
        for pid in list(direct_children(os.getpid())):
            capture(pid); capture_tree(pid)
        for pid,(birth,fd) in list(OWNED.items()):
            current=proc_birth(pid)
            if current is None: continue
            if current!=birth:
                errors.append(f'PID identity changed: {pid}'); continue
            if pid in direct_children(os.getpid()):
                try:
                    got,_=os.waitpid(pid,os.WNOHANG)
                    if got==pid: continue
                except ChildProcessError:
                    errors.append(f'child ownership uncertain: {pid}'); continue
            sig=None
            if pid not in term: sig=signal.SIGTERM; term.add(pid)
            elif time.monotonic()>deadline-2 and pid not in killed:
                sig=signal.SIGKILL; killed.add(pid)
            if sig is not None:
                try:
                    signal.pidfd_send_signal(fd,sig)
                    SIGNALS.append({'pid':pid,'birth':birth,'signal':sig.name})
                except ProcessLookupError: pass
        alive=[pid for pid,(birth,_) in OWNED.items() if proc_birth(pid)==birth]
        if not alive and not direct_children(os.getpid()):
            if errors: raise RuntimeError('; '.join(errors))
            return
        time.sleep(.01)
    raise RuntimeError('cleanup bound exceeded; captured or adopted children may remain')


def run_owned(argv,tmp,label):
    """No pipes or throwing signal handler: registration precedes bounded polling."""
    start_signals=len(SIGNALS)
    with (tmp/f'{label}.stdout').open('w') as out, (tmp/f'{label}.stderr').open('w') as err:
        p=None
        try:
            if STOP: raise RuntimeError('STOP requested before launch')
            p=subprocess.Popen(argv,cwd=tmp,stdout=out,stderr=err,start_new_session=True)
            capture(p.pid)
            if p.pid not in OWNED: raise RuntimeError('launched PID vanished before identity capture')
            deadline=time.monotonic()+15
            while True:
                capture_tree(p.pid)
                rc=p.poll()
                if rc is not None: break
                if STOP: raise RuntimeError('STOP requested')
                if time.monotonic()>=deadline: raise RuntimeError('owned command timed out')
                time.sleep(.01)
        finally:
            cleanup_all()
            if p is not None: p.wait(timeout=0)
    if STOP: raise RuntimeError('STOP requested')
    if len(SIGNALS)!=start_signals:
        raise RuntimeError('command required cleanup signals; qualification fails')
    return rc,(tmp/f'{label}.stdout').read_text(errors='replace'),(tmp/f'{label}.stderr').read_text(errors='replace')


def one(tmp, label, expected):
    src=tmp/f'{label}.c'; exe=tmp/label
    code=0 if expected==0 else 23
    src.write_text('#include <unistd.h>\nint main(void){ volatile int x=7; return (x==7)?%d:99; }\n'%code)
    cc_rc,_,cc_stderr=run_owned(['/usr/bin/gcc','-g','-O0','-o',str(exe),str(src)],tmp,label+'-gcc')
    if cc_rc: raise RuntimeError(f'{label} compile failed: {cc_stderr[:500]}')
    src_sha=sha(src); exe_sha=sha(exe)
    argv=[str(GDB),'--batch','-nx','-ex','set confirm off','-ex','set startup-with-shell off','-ex','set disable-randomization off','-ex','start','-ex','python _p=gdb.selected_inferior().pid; print("KPF17Q_PID="+str(_p)); print("KPF17Q_BIRTH="+open("/proc/%d/stat"%_p).read().rsplit(")",1)[1].split()[19])','-ex','continue','-ex','python print("KPF17Q_POST_PID="+str(gdb.selected_inferior().pid))','-ex','printf "KPF17Q_EXITCODE=%d\\n", $_exitcode','-ex','quit $_exitcode','--args',str(exe)]
    t0=time.monotonic()
    rc,stdout,stderr=run_owned(argv,tmp,label+'-gdb')
    cleanup=[]; timed_out=False; gdb_orphans=0
    elapsed=time.monotonic()-t0
    text=stdout+'\n'+stderr
    m=re.search(r'KPF17Q_PID=(\d+)',text)
    if not m: raise RuntimeError(f'{label}: GDB did not expose inferior PID; rc={rc}; {text[-1000:]}')
    pid=int(m.group(1))
    post=re.search(r'KPF17Q_POST_PID=(\d+)',text)
    exitm=re.search(r'KPF17Q_EXITCODE=(-?\d+)',text)
    bm=re.search(r'KPF17Q_BIRTH=(\d+)',text)
    if not bm: raise RuntimeError(f'{label}: GDB did not expose inferior birth identity')
    birth=int(bm.group(1))
    normal='exited normally' in text
    nonzero=re.search(r'exited with code (?:0x[0-9a-fA-F]+|[0-9]+)',text) is not None
    # The exact captured inferior must already be gone after GDB exits; no signal cleanup is used.
    alive=bool(birth and proc_birth(pid)==birth)
    expect_text=normal if expected==0 else (nonzero and not normal)
    cleanup_verified=all(x.get('reaped',False) for x in cleanup)
    ok=(not timed_out and not gdb_orphans and rc==expected and expect_text and post is not None and int(post.group(1))==0 and exitm is not None and int(exitm.group(1))==expected and not alive and cleanup_verified)
    return {'case':label,'expected_exit_code':expected,'gdb_rc':rc,'inferior_pid':pid,'inferior_birth':birth,
            'post_continue_inferior_pid':int(post.group(1)) if post else None,'gdb_exitcode':int(exitm.group(1)) if exitm else None,
            'gdb_normal_exit_marker':normal,'gdb_nonzero_exit_marker':nonzero,
            'inferior_absent_after_gdb':not alive,'signals_sent':[] if not timed_out else [x['signal'] for x in cleanup],
            'timed_out':timed_out,'cleanup_actions':cleanup,'cleanup_verified':cleanup_verified,
            'generated_source_sha256':src_sha,'generated_executable_sha256':exe_sha,
            'elapsed_s':round(elapsed,4),'status':'PASS' if ok else 'FAIL',
            'transcript_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'transcript_tail':text[-1600:]}


def main():
    signal.signal(signal.SIGTERM,request_stop)
    signal.signal(signal.SIGINT,request_stop)
    if len(__import__('sys').argv)==3 and __import__('sys').argv[1]=='--validate-result':
        validate_result(Path(__import__('sys').argv[2]))
        return None
    set_subreaper()
    smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
    if smoke:
        if not os.environ.get('FILLER_DRYRUN_RESULT_PATH'): raise RuntimeError('smoke/dryrun requires FILLER_DRYRUN_RESULT_PATH')
        out=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    else:
        out=Path(os.environ.get('KPF17Q_OUT',D/'out/RESULT.json'))
    attempt=os.environ.get('KPF17Q_ATTEMPT_ID')
    nonce=os.environ.get('KPF17Q_ATTEMPT_NONCE')
    if not attempt or not nonce: raise RuntimeError('attempt ID and nonce are required')
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists() or out.is_symlink(): raise RuntimeError(f'refusing result collision: {out}')
    full=D/'out/full-attempt-kvfork17-gdb-continue-qual-r2-20261104-7f3a91c6/RESULT.json'
    if smoke and out.resolve()==full.resolve(): raise RuntimeError('smoke result collides with full attempt')
    evidence=out.with_name(out.stem+'.evidence')
    if evidence.exists() or evidence.is_symlink(): raise RuntimeError(f'refusing evidence collision: {evidence}')
    check_stop()
    with tempfile.TemporaryDirectory(prefix='kpf17-gdb-qual-',dir=out.parent) as td:
        td=Path(td)
        control=one(td,'control',0)
        mutation=one(td,'mutation',23)
        verdict={'schema':'kpf17.gdb-continue-qualification.v1',
          'status':'PASS' if control['status']==mutation['status']=='PASS' else 'FAIL',
          'scope':'model-free GDB continue/inferior-exit and cleanup prerequisite only',
          'control':control,'mutation':mutation,'gdb_path':str(GDB),'gdb_sha256':sha(GDB),
          'gcc_path':'/usr/bin/gcc','gcc_sha256':sha('/usr/bin/gcc'),
          'launcher_sha256':sha(D/'launch.sh'),'qualifier_sha256':sha(__file__),
          'no_model_or_kpf17_binary_used':True,
          'no_kpf17_source_library_mapping_or_custody_claim':True,
          'qualification_mutation':'private executable returns 23; expected as nonzero inferior exit',
          'attempt_id':attempt,'attempt_nonce':nonce,
          'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        # Exclusive copy preserves full transcripts and generated inputs after temp cleanup.
        shutil.copytree(td,evidence)
        for case in (control,mutation):
            label=case['case']
            names=[label+'.c',label,label+'-gcc.stdout',label+'-gcc.stderr',label+'-gdb.stdout',label+'-gdb.stderr']
            case['evidence_files']={name:{'path':str(evidence/name),'sha256':sha(evidence/name)} for name in names}
    # Publication belongs to __main__, after final verified cleanup and fd closure.
    return out,verdict


def validate_result(path):
    check_stop()
    try: result=json.loads(path.read_text())
    except Exception as exc: raise RuntimeError(f'result is not readable JSON: {exc}')
    if result.get('schema')!='kpf17.gdb-continue-qualification.v1' or result.get('status')!='PASS':
        raise RuntimeError('result schema/status is not PASS')
    if result.get('attempt_id')!=os.environ.get('KPF17Q_ATTEMPT_ID') or result.get('attempt_nonce')!=os.environ.get('KPF17Q_ATTEMPT_NONCE'):
        raise RuntimeError('result attempt ID/nonce mismatch')
    for name,code in (('control',0),('mutation',23)):
        case=result.get(name)
        if not isinstance(case,dict) or case.get('status')!='PASS' or case.get('expected_exit_code')!=code:
            raise RuntimeError(f'{name} case is not a PASS for exact expected code')
        if case.get('gdb_rc')!=code or case.get('gdb_exitcode')!=code or case.get('post_continue_inferior_pid')!=0:
            raise RuntimeError(f'{name} GDB exit/continue predicate failed')
        if case.get('gdb_normal_exit_marker') is not (code==0) or (code==23 and case.get('gdb_nonzero_exit_marker') is not True):
            raise RuntimeError(f'{name} expected GDB exit marker missing')
        if not isinstance(case.get('inferior_pid'),int) or case['inferior_pid']<=0 or not isinstance(case.get('inferior_birth'),int) or case['inferior_birth']<=0 or case.get('cleanup_actions')!=[]:
            raise RuntimeError(f'{name} captured identity/cleanup predicate failed')
        if case.get('timed_out') is not False or case.get('cleanup_verified') is not True or case.get('inferior_absent_after_gdb') is not True or case.get('signals_sent')!=[]:
            raise RuntimeError(f'{name} does not prove clean normal completion')
        evidence=case.get('evidence_files',{})
        expected={name+'.c',name,name+'-gcc.stdout',name+'-gcc.stderr',name+'-gdb.stdout',name+'-gdb.stderr'}
        if set(evidence)!=expected: raise RuntimeError(f'{name} complete evidence missing')
        for filename,record in evidence.items():
            artifact=path.with_name(path.stem+'.evidence')/filename
            if record.get('path')!=str(artifact) or artifact.is_symlink() or sha(artifact)!=record.get('sha256'):
                raise RuntimeError(f'{name} evidence digest/path mismatch: {filename}')
        if evidence[name+'.c']['sha256']!=case.get('generated_source_sha256') or evidence[name]['sha256']!=case.get('generated_executable_sha256'):
            raise RuntimeError(f'{name} generated evidence mismatch')
        transcript=(path.with_name(path.stem+'.evidence')/(name+'-gdb.stdout')).read_text(errors='replace')+'\n'+(path.with_name(path.stem+'.evidence')/(name+'-gdb.stderr')).read_text(errors='replace')
        if hashlib.sha256(transcript.encode()).hexdigest()!=case.get('transcript_sha256'):
            raise RuntimeError(f'{name} complete transcript mismatch')
    check_stop()

if __name__=='__main__':
    publication=None
    try:
        publication=main()
    finally:
        if not (len(__import__('sys').argv)==3 and __import__('sys').argv[1]=='--validate-result'):
            try: cleanup_all()
            finally:
                for _,fd in OWNED.values(): os.close(fd)
    if publication is not None:
        out,verdict=publication
        if SIGNALS: raise RuntimeError('cleanup signals prohibit PASS publication')
        check_stop()
        atomic(out,verdict)
        raise SystemExit(0 if verdict['status']=='PASS' else 1)
