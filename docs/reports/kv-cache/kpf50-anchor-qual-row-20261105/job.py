#!/usr/bin/env python3
import errno
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

D=Path(__file__).resolve().parent
ROW='kpf50-anchor-qual-20261105'
FULL=D/'full-results/RESULT.json'
ENGINE=Path('/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh')
ENGINE_SHA='21987e52ee02c609cd5a80f7b493b2d69fbaf367b4dd44bd9ff9fa3ec20c51b2'
STOPPED=False
def stopped(signum, frame):
    global STOPPED
    STOPPED=True
for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stopped)
def digest(data):return hashlib.sha256(data).hexdigest()
def verify():
    seals=json.loads((D/'seals.json').read_text())
    if set(seals)!={'job.py','case_runner.py','complete.py','launch.sh','spec.json','retained/anchor_preflight.py'}:
        raise ValueError('unexpected qualification seal set')
    for name,sha in seals.items():
        p=D/name
        if p.is_symlink() or not p.is_file() or digest(p.read_bytes())!=sha:raise ValueError('source seal drift: '+name)
    if digest(ENGINE.read_bytes())!=ENGINE_SHA:raise ValueError('engine seal drift')
def write_new(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:
        json.dump(obj,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def fixture(path,case):
    packet=path/'packet';admission=path/'admission'
    packet.mkdir(parents=True);admission.mkdir()
    dependencies={}
    for name in ('seals.json','check_models.py','models.stat.json'):
        # Sealed inert fixture bytes, never executable admission/model material.
        p=admission/name;p.write_text('synthetic '+name+'\n');dependencies[str(p)]=digest(p.read_bytes())
    (packet/'supervisor.py').write_text('# inert synthetic supervisor\n')
    write_new(packet/'plan.json',{'status':'SYNTHETIC_DISABLED','target_enabled':False})
    write_new(packet/'dependencies.json',dependencies)
    seals={name:digest((packet/name).read_bytes()) for name in ('supervisor.py','plan.json','dependencies.json')}
    write_new(packet/'seals.json',seals)
    anchor=digest((packet/'seals.json').read_bytes())
    expected={'kind':'accepted','payload':{'schema':'kpf50.anchor-preflight.v1','status':'SOURCE_BYTES_MATCH_ONLY','target_enabled':False,'supervisor_seals_sha256':anchor,'native_validator_qualified':False}}
    if case=='changed-root':
        (packet/'seals.json').write_text('{}\n')
        expected={'kind':'refused','type':'ValueError','message':'anchor mismatch: '+str(packet/'seals.json'),'errno':None}
    elif case=='changed-dependency':
        p=admission/'check_models.py';p.write_text('changed synthetic bytes\n')
        expected={'kind':'refused','type':'ValueError','message':'anchor mismatch: '+str(p),'errno':None}
    elif case=='symlink-alias':
        p=admission/'models.stat.json';p.rename(admission/'alias-target');p.symlink_to('alias-target')
        expected={'kind':'refused','type':'OSError','message':None,'errno':errno.ELOOP}
    elif case=='missing-file':
        (packet/'plan.json').unlink()
        expected={'kind':'refused','type':'FileNotFoundError','message':None,'errno':errno.ENOENT}
    return anchor,expected
def cleanup(p,fd):
    if not select.select([fd],[],[],0)[0]:
        try:signal.pidfd_send_signal(fd,signal.SIGTERM)
        except ProcessLookupError:pass
        try:p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:signal.pidfd_send_signal(fd,signal.SIGKILL)
            except ProcessLookupError:pass
            p.wait(timeout=2)
    p.wait(timeout=2)
    if not select.select([fd],[],[],0)[0]:raise RuntimeError('captured child remains alive')
    os.close(fd)
def main():
    verify()
    if sys.argv[1:]==['--check']:return
    if sys.argv[1:]:raise ValueError('unexpected arguments')
    if os.environ.get('FILLER_ID')!=ROW:raise ValueError('wrong outer completion identity')
    for key in ('FILLER_CPUS','FILLER_END','FILLER_DEADLINE','FILLER_STOPFILE','FILLER_PIDFILE'):
        if not os.environ.get(key):raise ValueError('missing grant '+key)
    smoke=os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1'
    affinity=os.sched_getaffinity(0)
    if len(affinity)<4 or (smoke and len(affinity)!=4):raise ValueError('requires four CPU smoke / >=four CPU full affinity')
    result=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else FULL
    if not result.is_absolute() or result.resolve()!=result:raise ValueError('noncanonical result path')
    if smoke and (result==FULL or D/'full-results' in result.parents):raise ValueError('smoke/full isolation')
    if result.exists():raise ValueError('existing result; no redraw')
    run=result.parent/('anchor-smoke-attempt' if smoke else 'anchor-full-attempt')
    run.mkdir(parents=True,exist_ok=False)
    cases=['positive','changed-root'] if smoke else ['positive','changed-root','changed-dependency','symlink-alias','missing-file']
    end=min(time.time()+180,float(os.environ['FILLER_END'])-15,float(os.environ['FILLER_DEADLINE']))
    r={'schema':'kpf50.anchor-qualification.v1','row_id':ROW,'status':'INVALID','smoke':smoke,'partial':smoke,'scan_complete':False,'cleanup_confirmed':True,'synthetic_only':True,'target_enabled':False,'cases':[]}
    try:
        for case in cases:
            if STOPPED or Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=end:raise RuntimeError('STOP/deadline')
            anchor,expected=fixture(run/case,case)
            cmd=[sys.executable,'-I','-B',str(D/'case_runner.py'),str(run/case),anchor]
            with (run/(case+'.stdout')).open('x') as out,(run/(case+'.stderr')).open('x') as err:
                p=subprocess.Popen(cmd,stdout=out,stderr=err)
                fd=os.pidfd_open(p.pid)
                child_deadline=min(end,time.time()+5)
                try:
                    while p.poll() is None:
                        if STOPPED or Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=child_deadline:raise RuntimeError('STOP/deadline/case-timeout')
                        time.sleep(.02)
                finally:
                    try:cleanup(p,fd)
                    except Exception:
                        r['cleanup_confirmed']=False;raise
            actual=json.loads((run/(case+'.stdout')).read_text())
            rc=0 if case=='positive' else 2
            match=p.returncode==rc and actual==expected and (run/(case+'.stderr')).read_bytes()==b''
            r['cases'].append({'case':case,'expected':expected,'actual':actual,'rc':p.returncode,'expected_rc':rc,'matched':match,'captured_pid':p.pid,'pidfd_dead_verified':True})
            if not match:raise RuntimeError('exact outcome mismatch: '+case)
        verify()
        if STOPPED or Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=end:raise RuntimeError('STOP/deadline at completion')
        r.update(status='SMOKE_ONLY' if smoke else 'SYNTHETIC_ANCHOR_QUALIFIED',scan_complete=not smoke)
    except Exception as exc:r['reason']=str(exc)
    write_new(result,r)
    if r['status']=='INVALID':raise SystemExit(2)
if __name__=='__main__':main()
