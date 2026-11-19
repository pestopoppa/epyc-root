#!/usr/bin/env python3
"""Model-free subprocess qualification of retained supervisor; never invoke native driver."""
import hashlib,importlib.util,json,os,pathlib,signal,subprocess,sys,tempfile,time,types
P=pathlib.Path
SCRIPT=P(__file__).resolve()
ROOT=P('/mnt/raid0/llm/tmp/kvfork/g3-cleanup-qualification-20261104')
ROOT.mkdir(parents=True,exist_ok=True)
SRC=P('/mnt/raid0/llm/tmp/kpf18-g3-repair-successor-20261029/candidate')
FILES=['supervisor.py','owned_drain.py','guard.py','output_reserve.py','ledger.py']
def hashes():return {n:hashlib.sha256((SRC/n).read_bytes()).hexdigest() for n in FILES}
def worker(case,scenario):
    case=P(case);sys.path.insert(0,str(SRC))
    import guard,owned_drain
    # Substitute external admission providers only. Exercise original boundary and drain code.
    for n in ['lock_witness','gpu_smoke_admission','ram_admission']:
        sys.modules[n]=types.SimpleNamespace(capture_gpu=lambda:('synthetic',{}),verify_gpu=lambda *a:None,check=lambda *a,**k:None)
    spec=importlib.util.spec_from_file_location('retained_supervisor',SRC/'supervisor.py')
    s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);s.D=case
    flags=case/'flags';(flags/'grants').mkdir(parents=True)
    def mapped(value):
        value=str(value)
        if value=='/mnt/raid0/llm/tmp/compute-flags':return flags
        if value=='/mnt/raid0/llm/tmp':return case/'holds'
        if value=='/sys/class/drm/card2/device/mem_info_vram_used':return case/'vram'
        return P(value)
    s.Path=mapped;guard.Path=mapped;guard.BASE=case
    guard.GRANT=flags/'grants'/(guard.ID+'.grant')
    # Disk and CPU provider values are synthetic, not resource qualification.
    guard.shutil.disk_usage=lambda p:types.SimpleNamespace(free=300*1024**3)
    guard.os.sched_getaffinity=lambda pid:set(range(184,192))
    start=int(time.time())-100;end=start+9000
    def stamp(t):return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(t))
    guard.GRANT.write_text('regions=mi210_0,184-191 start='+stamp(start)+' end='+stamp(end)+'\n')
    os.environ.update(FILLER_ID=guard.ID,FILLER_CPUS='184-191',FILLER_END=str(end),FILLER_DEADLINE=str(end-90),FILLER_THREADS='8',FILLER_NEEDGPU='1',FILLER_STOPFILE=str(case/'STOP'))
    (case/'vram').write_text('0')
    real_popen=subprocess.Popen
    def spawn(args,**kwargs):
        assert str(case/'driver.py') in args, 'unexpected child execution'
        return real_popen([sys.executable,'-B',str(SCRIPT),'child',str(case),scenario],**kwargs)
    s.subprocess.Popen=spawn
    sys.argv=['supervisor.py','official']
    rc=s.main();(case/'worker-rc').write_text(str(rc));return rc

def child(case,scenario):
    case=P(case);out=P(os.environ['KPF_OUTPUT_ROOT'])
    if scenario in ['stop','deadline','signal','orphan']:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
    if scenario=='orphan':
        g=subprocess.Popen([sys.executable,'-B','-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(45)'],start_new_session=True)
        (case/'grandchild.pid').write_text(str(g.pid))
    (case/'child.pid').write_text(str(os.getpid()))
    if scenario=='stop':(case/'STOP').touch()
    if scenario=='deadline':
        # Make grant itself expired while preserving its exactly9000-second shape.
        start=int(time.time())-9100;end=start+9000
        stamp=lambda t:time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(t))
        (case/'flags/grants'/('kpf18-g3-diagnostic-v1-20261029.grant')).write_text('regions=mi210_0,184-191 start='+stamp(start)+' end='+stamp(end)+'\n')
    if scenario=='orphan':return 0
    if scenario in ['success','missing']:
        if scenario=='success':
            (out/'conformance').mkdir()
            for n in ['VERDICT.json','SHARED-PROJECTION.json']:(out/'conformance'/n).write_text('{}\n')
        return 0
    time.sleep(45);return 0

def main():
    initial=hashes();results=[]
    for scenario in ['success','missing','stop','deadline','signal','orphan']:
        case=P(tempfile.mkdtemp(prefix=scenario+'-',dir=ROOT))
        with (case/'worker.log').open('w') as log:
            p=subprocess.Popen([sys.executable,'-B',str(SCRIPT),'worker',str(case),scenario],stdout=log,stderr=subprocess.STDOUT)
            if scenario=='signal':
                until=time.monotonic()+5
                while not (case/'child.pid').exists() and p.poll() is None and time.monotonic()<until:time.sleep(.02)
                assert (case/'child.pid').exists(),'child readiness absent'
                p.send_signal(signal.SIGTERM)
            try:rc=p.wait(timeout=12)
            except subprocess.TimeoutExpired:
                p.kill();p.wait();raise AssertionError('fixture exceeded12s; inspect owned fixture PIDs')
        records=list((case/'attempts').glob('run-*/*RESULT.json'))+list((case/'attempts').glob('run-*/PARTIAL.json'))
        assert len(records)==1,(scenario,rc,(case/'worker.log').read_text())
        record=json.loads(records[0].read_text());expected={'success':0,'missing':70,'orphan':0}.get(scenario,75)
        # Orphan native completion has missing outputs, so result must be70 while cleanup still drains.
        if scenario=='orphan':expected=70
        assert rc==expected and record['rc']==expected,(scenario,rc,record)
        assert record['children_drained'] is True
        for name in ['child.pid','grandchild.pid']:
            if (case/name).exists():assert not P('/proc/'+(case/name).read_text()).exists(),(scenario,name,'surviving PID')
        results.append({'scenario':scenario,'rc':rc,'record':str(records[0]),'children_absent':True,'reason':record['reason']})
    assert hashes()==initial,'retained source changed'
    report={'schema':'g3-model-free-supervisor-qualification.v1','source':str(SRC),'source_hashes':initial,'source_unchanged':True,'tests':results,'scope':'Original supervisor, guard.boundary and owned_drain with inert Python child processes. Synthetic GPU/claim/affinity/disk providers; no inference, resource qualification, native data or publication.'}
    (ROOT/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='worker':raise SystemExit(worker(sys.argv[2],sys.argv[3]))
    if len(sys.argv)>1 and sys.argv[1]=='child':raise SystemExit(child(sys.argv[2],sys.argv[3]))
    main()
