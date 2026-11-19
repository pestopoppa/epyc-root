#!/usr/bin/env python3
"""Keeper-contained P3 dedicated lifecycle qualification or full A1 experiment."""
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import p3_kvu_probe as p
D=Path(__file__).resolve().parent
PORT=18198

def context(env):
    mode=env.get('FILLER_DRYRUN')
    if mode not in ('0','1') or env.get('FILLER_NEEDGPU')!='1':
        raise ValueError('explicit keeper GPU/mode grant required')
    deadline=int(env['FILLER_DEADLINE'])
    if deadline-time.time()<120:raise ValueError('insufficient deadline')
    if not env.get('FILLER_PIDFILE') or not env.get('FILLER_STOPFILE'):raise ValueError('keeper custody missing')
    out=Path(env['FILLER_DRYRUN_RESULT_PATH']) if mode=='1' else D/'result.json'
    if mode=='1' and out.resolve()==(D/'result.json').resolve():raise ValueError('qualification cannot target full result')
    return mode,deadline,out

def granted_cpus(env, affinity=None):
    raw=env.get('FILLER_CPUS','')
    granted=set()
    for part in raw.split(','):
        if not part:raise ValueError('keeper CPU grant missing')
        bounds=part.split('-')
        if len(bounds)>2 or not all(x.isdecimal() for x in bounds):raise ValueError('malformed CPU grant')
        lo=int(bounds[0]);hi=int(bounds[-1])
        if lo>hi:raise ValueError('reversed CPU grant')
        granted.update(range(lo,hi+1))
    allowed=set(os.sched_getaffinity(0) if affinity is None else affinity)
    effective=granted & allowed & set(range(184,192))
    if not effective:raise ValueError('no granted GPU host CPU available')
    if env.get('FILLER_DRYRUN')=='1':
        effective=effective & set(range(184,188))
        if len(effective)!=4:raise ValueError('qualification requires exactly four granted CPUs184-187')
    return ','.join(map(str,sorted(effective)))

def qualification():
    """Native control: two real dedicated server lifecycles; no target verdict."""
    runs=[]
    for variant in ('drafted','nodraft'):
        p.ACTIVE_VARIANT=variant
        p.P3=ROOT/variant;p.LOGS=p.P3/'logs';p.SLOTDIR=p.P3/'slots'
        for directory in (p.P3,p.LOGS,p.SLOTDIR):directory.mkdir(parents=True,exist_ok=True)
        srv=p.Server('qualification',PORT,False,False)
        # Qualification has its own reduced geometry; full measurement constants stay unchanged.
        srv.argv=p.SB._set(srv.argv,('-c','--ctx-size'),'4096')
        srv.argv=p.SB._set(srv.argv,('--cache-ram',),'0')
        p.SERVER_ARGV[srv.base]=srv.argv
        try:
            srv.start()
            healthy_at=time.time()
            result=p.chat(srv.base,'Reply with a short greeting.',0,16)
            p.require_draft_count(variant,result)
            result['draft_count_observation']='unknown' if result.get('draft_n') is None else 'reported'
            # Require two own-PID post-health samples DURING this native lifetime.
            sample_deadline=time.monotonic()+30
            while True:
                live=[sample for sample in srv.sampler.samples
                      if sample['t']>=healthy_at and sample.get('pids',{}).get(srv.proc.pid,{}).get('vram_b',0)>0]
                if len(live)>=2:break
                if time.monotonic()>=sample_deadline:raise RuntimeError('two post-health own-PID VRAM samples missing')
                time.sleep(.25)
            srv.rec['qualification_live_samples']=live
            srv.rec['qualification_healthy_at']=healthy_at
        finally:srv.stop()
        rec=srv.rec
        if (rec.get('hip_dlopen_proof',{}).get('ok') is not True or
            (rec.get('vram',{}).get('nonzero_samples') or 0)<2 or
            rec.get('teardown',{}).get('verified_dead') is not True or rec.get('port_free_after') is not True):
            raise RuntimeError('native qualification custody/residency refused')
        if any(x['server']['pid']==rec['pid'] for x in runs):raise RuntimeError('server PID reused')
        runs.append({'variant':variant,'server':rec,'request':result})
    return {'schema':'kvu16h.p3.qualification.v1','mode':'qualification','status':'ok',
            'native_units':2,'runs':runs,'interpretation':'lifecycle control only; no occupancy or performance verdict'}

def write_result(out,record):
    out.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(out,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(record,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def main():
    global ROOT
    mode,deadline,out=context(os.environ)
    if out.exists():raise RuntimeError('completion result already exists')
    ROOT=Path(tempfile.mkdtemp(prefix='qualification-' if mode=='1' else 'run-',dir=D))
    cpus=granted_cpus(os.environ)
    os.sched_setaffinity(0,{int(cpu) for cpu in cpus.split(',')})
    p.SB.PREFIX=['numactl','--membind=3','--','taskset','-c',cpus]
    original_server_argv=p.server_argv
    def bounded_server_argv(*args,**kwargs):
        argv,notes=original_server_argv(*args,**kwargs)
        threads=str(len(cpus.split(',')))
        argv=p.SB._set(argv,('-t','--threads'),threads)
        argv=p.SB._set(argv,('-tb','--threads-batch'),threads)
        return argv,notes+['keeper effective CPUs '+cpus]
    p.server_argv=bounded_server_argv
    done=threading.Event()
    def watch():
        while not done.wait(.5):
            if time.time()>=deadline-45 or Path(os.environ['FILLER_STOPFILE']).exists():
                os.kill(os.getpid(),signal.SIGTERM);return
    threading.Thread(target=watch,daemon=True).start()
    try:
        if mode=='1':record=qualification()
        else:
            p.P3=ROOT;p.LOGS=ROOT/'logs';p.SLOTDIR=ROOT/'slots'
            # Select the existing prefill path; retain every occupancy threshold.
            full_rc=p.phase_a1(SimpleNamespace(port=PORT,park_mode='prefill'))
            record=json.loads((ROOT/'a1.json').read_text())
            record.update(schema='kvu16h.p3.full.v1',mode='full',
                          native_units=len(record.get('variant_runs',[])),
                          park_mode_declared='prefill',full_rc=full_rc)
            if full_rc:
                record.update(run_dir=str(ROOT),effective_cpus=cpus,
                              preflight=str(D/'preflight.json'),
                              measurement_contract=str(D/'measurement-sufficiency.json'))
                write_result(out,record)
                return 1
            p.phase_report(None)
            record['derived_report']=str(ROOT/'p3_result.json')
        record.update(run_dir=str(ROOT),effective_cpus=cpus,preflight=str(D/'preflight.json'),measurement_contract=str(D/'measurement-sufficiency.json'))
        write_result(out,record)
    finally:done.set()
    return 0
if __name__=='__main__':sys.exit(main())
