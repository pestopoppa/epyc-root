import os,sys,json,time,subprocess,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
for p,h in json.loads((D/'inputs.json').read_text()).items():
    if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h: raise ValueError('sealed input drift')
smoke=os.environ.get('FILLER_SMOKE')=='1'
if os.environ.get('FILLER_DRYRUN')=='1' and not smoke: raise ValueError('dryrun requires smoke')
for key in ('FILLER_ID','FILLER_END','FILLER_DEADLINE','FILLER_STOPFILE','FILLER_CPUS','FILLER_PIDFILE'):
    if not os.environ.get(key): raise ValueError('missing grant '+key)
affinity=os.sched_getaffinity(0)
if len(affinity)<4 or (smoke and len(affinity)!=4): raise ValueError('at least four CPUs full; exactly four smoke required')
if not time.time()<float(os.environ['FILLER_DEADLINE'])<float(os.environ['FILLER_END']): raise ValueError('deadline')
if smoke:
    external=os.environ.get('FILLER_DRYRUN_RESULT_PATH')
    if not external: raise ValueError('publisher smoke result path required')
    external_path=Path(external)
    if not external_path.is_absolute(): raise ValueError('absolute smoke result path required')
    if external_path.resolve()==(D/'full-results/RESULT.json').resolve(): raise ValueError('smoke/full collision')
    R=external_path.parent/'kpf50-custody-smoke-attempt'
else:
    R=D/'full-results'
R.mkdir(parents=True,exist_ok=False)
def boundary():
    if Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE']): raise RuntimeError('outer STOP/deadline')
def case(name,mode):
    boundary(); f=R/name; f.mkdir(); ledger=f/'ledger'
    if 'target-exposure-ledger' in str(ledger) or not ledger.is_relative_to(R): raise ValueError('non-synthetic ledger')
    commands=[[sys.executable,'-I','-B',str(D/'stub.py'),str(ledger/'attempt'/str(i)),str(i),s,mode] for i,s in enumerate(('full','mask','mask','full'),1)]
    plan={'status':'QUALIFIED_WINDOW_ADAPTER','receipt_validator_status':'QUALIFIED_SEALED_NATIVE_VALIDATOR','order':['full','mask','mask','full'],'commands':commands,'lineage_ledger':str(ledger)}
    (f/'plan.json').write_text(json.dumps(plan)); (f/'dependencies.json').write_text('{}'); (f/'supervisor.py').write_bytes((D/'supervisor.py').read_bytes())
    (f/'seals.json').write_text(json.dumps({n:hashlib.sha256((f/n).read_bytes()).hexdigest() for n in ('supervisor.py','plan.json','dependencies.json')}))
    env=dict(os.environ,FILLER_ID='synthetic-'+name,FILLER_STOPFILE=str(f/'STOP'),FILLER_SMOKE='0',FILLER_DRYRUN='0')
    def launch():
        log=(f/('worker-'+str(time.time_ns())+'.log')).open('xb')
        p=subprocess.Popen([sys.executable,'-I','-B',str(D/'worker.py'),str(f)],env=env,stdout=log,stderr=log)
        birth=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[19]
        with open(os.environ['FILLER_PIDFILE'],'a') as pf: pf.write(str(p.pid)+'\n')
        (f/('driver-capture-'+str(p.pid)+'.json')).write_text(json.dumps({'pid':p.pid,'birth':birth}))
        limit=time.monotonic()+35
        try:
            while p.poll() is None:
                boundary()
                if mode=='stop' and (ledger/'attempt/1/stub-descendant.json').exists(): (f/'STOP').touch()
                if time.monotonic()>limit: raise RuntimeError('synthetic case timeout')
                time.sleep(.02)
        finally:
            if p.poll() is None:
                # Only our captured worker; supervisor TERM handler cleans its captured subtree.
                if Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[19]!=birth: raise RuntimeError('birth mismatch')
                p.terminate()
            try: p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                # Only identities born under this synthetic fixture may be escalated.
                identities=[json.loads(q.read_text()) for q in ledger.glob('attempt/*/root-birth.json')]+[json.loads(q.read_text()) for q in ledger.glob('attempt/*/stub-descendant.json')]+[{'pid':p.pid,'birth':birth}]
                import signal
                for identity in identities:
                    proc=Path('/proc')/str(identity['pid'])/'stat'
                    if proc.exists() and proc.read_text().rsplit(')',1)[1].split()[19]==identity['birth']:
                        fd=os.pidfd_open(identity['pid'])
                        try:
                            if proc.exists() and proc.read_text().rsplit(')',1)[1].split()[19]==identity['birth']: signal.pidfd_send_signal(fd,signal.SIGKILL)
                            import select
                            if not select.select([fd],[],[],5)[0]: raise RuntimeError('captured identity survives SIGKILL')
                        finally: os.close(fd)
                p.wait(timeout=5)
                raise RuntimeError('supervisor cleanup timeout; forced own captured identities dead; qualification failed')
            finally: log.close()
        if Path(f'/proc/{p.pid}').exists(): raise RuntimeError('worker remains')
        return p.returncode
    rc=launch()
    if mode=='normal':
        if rc or not (ledger/'COMPLETE.json').exists(): raise RuntimeError('normal custody failed')
        before={p.name:p.read_bytes() for p in ledger.glob('window-*.exposed.json')}
        env['FILLER_ID']='fresh-row-no-redraw'
        if launch()==0: raise RuntimeError('redraw accepted')
        if before!={p.name:p.read_bytes() for p in ledger.glob('window-*.exposed.json')}: raise RuntimeError('exposure changed')
    else:
        if rc==0 or (ledger/'COMPLETE.json').exists() or len(list(ledger.glob('window-*.exposed.json')))!=1: raise RuntimeError('fault accepted')
        if mode=='stop':
            identity=json.loads((ledger/'attempt/1/stub-descendant.json').read_text()); path=Path('/proc')/str(identity['pid'])/'stat'
            if path.exists() and path.read_text().rsplit(')',1)[1].split()[19]==identity['birth']: raise RuntimeError('descendant remains')
    return {'case':name,'returncode':rc,'scope':'synthetic custody only','ledger':str(ledger),'captures':sorted(str(p) for p in f.glob('driver-capture-*.json')),'no_redraw_verified':mode=='normal','descendant_absence_verified':mode=='stop'}
results=[case('normal-and-no-redraw','normal')]
if not smoke: results += [case('stop-descendant','stop'),case('bad-receipt-binding','badbinding')]
boundary()
result={'status':'PASS','smoke':smoke,'results':results,'native_target_validator_qualified':False,'row_id':os.environ['FILLER_ID'],'attempt_root':str(R)}
(R/'RESULT.json').write_text(json.dumps(result,indent=2))
if smoke:
    external=os.environ.get('FILLER_DRYRUN_RESULT_PATH')
    if not external: raise ValueError('publisher smoke result path required')
    target=Path(external)
    if target.resolve()==(D/'full-results/RESULT.json').resolve(): raise ValueError('smoke/full collision')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as stream: json.dump(result,stream)

