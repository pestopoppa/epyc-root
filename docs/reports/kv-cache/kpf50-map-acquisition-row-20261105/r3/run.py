import hashlib,importlib.util,json,os,pathlib,shutil,signal,sys,time,uuid
B=pathlib.Path(__file__).resolve().parent
ID='kpf50-own-child-map-acquisition-r3-20261105'
mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
root=B/'out'/mode/uuid.uuid4().hex
root.mkdir(parents=True,exist_ok=False)
result={'id':ID,'mode':mode,'status':'UNKNOWN','scientific_validity':'UNKNOWN','records':[],'cleanup':[],'root':str(root)}
spec=importlib.util.spec_from_file_location('acquisition',B/'acquire.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
deadline=time.monotonic()+240
stop_requested=None
for key,margin in (('FILLER_DEADLINE',0),('FILLER_END',10)):
    if os.environ.get(key): deadline=min(deadline,time.monotonic()+float(os.environ[key])-time.time()-margin)
result['grant_guards']={k:os.environ.get(k) for k in ('FILLER_STOPFILE','FILLER_DEADLINE','FILLER_END')}
result['supervisor_pid']=os.getpid()

def guard():
    if stop_requested or (B/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and pathlib.Path(os.environ['FILLER_STOPFILE']).exists()) or time.monotonic()>=deadline: raise RuntimeError('STOP/deadline')

def interrupted(signum,frame):
    global stop_requested
    stop_requested=signum # Deferred to guard; cannot interrupt owned-child cleanup.
for signum in (signal.SIGTERM,signal.SIGINT): signal.signal(signum,interrupted)

def child_case(label):
    guard()
    ready=root/(label+'.ready.json')
    with (root/(label+'.stdout')).open('wb') as stdout,(root/(label+'.stderr')).open('wb') as stderr:
        c=m.OwnChild([sys.executable,'-B','-I',str(B/'leaf.py'),'/proc/self/fd/'+str(dsofd),str(ready),label],env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},cwd=root,stdout=stdout,stderr=stderr,pinned_fds=(exefd,dsofd))
        try:
            while not ready.exists():
                guard();c.check();time.sleep(.02)
            witness=json.loads(ready.read_text())
            if witness!={'pid':c.process.pid,'mapped':'/proc/self/fd/'+str(dsofd),'mode':label}: raise RuntimeError('readiness identity mismatch')
            if label=='honest':
                malformed=c.capture(max_segment_bytes=0)
                if malformed['status']!='UNKNOWN' or 'invalid read bound' not in malformed.get('reason',''): raise RuntimeError('malformed refusal missing')
                result['records'].append({'case':'malformed-bound','record':malformed})
            guard()
            record=c.capture();result['records'].append({'case':label,'record':record})
            if label=='honest' and record['status']=='OBSERVED_FILE_RANGES':
                dsos=[r for r in record['mappings'] if r['inode']==os.fstat(dsofd).st_ino and r['parent_retained_fd']==dsofd]
                if not dsos or any(r['status']!='OBSERVED_FILE_RANGE' or not r.get('range_sha256') for r in dsos): raise RuntimeError('private DSO native range evidence missing')
            return record
        finally:
            result['cleanup'].append(c.close())

rc=2
try:
    affinity=sorted(os.sched_getaffinity(0));result['affinity']=affinity
    if len(affinity)!=(4 if mode=='smoke' else 24): raise RuntimeError('exact smoke/full affinity required')
    canonical=m.canonical_map_range('00420000-00763000')
    if canonical!='420000-763000' or canonical=='00420000-00763000': raise RuntimeError('zero-padding canonicalization mutation not detected')
    result['records'].append({'case':'zero-padding-control','original_range':'00420000-00763000','canonical_range':canonical,'padded_mutation_rejected':True})
    pins=json.loads((B/'runtime.json').read_text())
    for p,h in pins.items():
        if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h: raise RuntimeError('runtime seal drift '+p)
    source=pathlib.Path('/lib/x86_64-linux-gnu/libm.so.6')
    private=root/'libggml-qualification-private.so'
    shutil.copyfile(source,private)
    if hashlib.sha256(private.read_bytes()).hexdigest()!=pins[str(source)]: raise RuntimeError('private DSO copy mismatch')
    exefd=os.open(sys.executable,os.O_RDONLY|os.O_CLOEXEC)
    dsofd=os.open(private,os.O_RDONLY|os.O_CLOEXEC)
    expected_exe=pins[str(pathlib.Path(sys.executable).resolve())]
    for pinnedfd,expected in ((exefd,expected_exe),(dsofd,pins[str(source)])):
        st=os.fstat(pinnedfd)
        raw=os.pread(pinnedfd,st.st_size,0)
        if len(raw)!=st.st_size or hashlib.sha256(raw).hexdigest()!=expected: raise RuntimeError('pre-spawn descriptor content mismatch')
    result['pinned_files']={'executable':{'path':str(pathlib.Path(sys.executable).resolve()),'sha256':expected_exe,'fd':exefd},'private_dso':{'path':str(private),'sha256':pins[str(source)],'fd':dsofd}}
    guard()
    honest=child_case('honest')
    if honest['status']!='OBSERVED_FILE_RANGES':
        result['reason']='Native inherited-FD mapping evidence unavailable; no synthetic substitute; stopped after original honest attempt.'
        if mode=='smoke': result['status']='SMOKE_REFUSAL_OBSERVED';rc=0
    else:
        denied=child_case('denied')
        if denied['status']!='UNKNOWN' or not any(x in denied.get('reason','') for x in ('PermissionError','Operation not permitted','Permission denied')): raise RuntimeError('actual kernel permission refusal absent')
        result['status']='SMOKE_ACQUISITION_QUALIFIED' if mode=='smoke' else 'ACQUISITION_QUALIFIED';rc=0
    guard()
except (OSError,ValueError,RuntimeError) as exc:
    result['status']='UNKNOWN';result['reason']=f'{type(exc).__name__}: {exc}';rc=2
finally:
    for fdname in ('dsofd','exefd'):
        if fdname in globals():os.close(globals()[fdname])
    result['end_monotonic_raw_ns']=m.now()
    raw=json.dumps(result,indent=2)+'\n'
    (root/'RESULT.json').write_text(raw)
    receipt=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(B/'out'/'RESULT.json')))
    receipt.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(raw)
sys.exit(rc)
