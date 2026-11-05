import hashlib,importlib.util,json,os,pathlib,shutil,signal,sys,time,uuid
B=pathlib.Path(__file__).resolve().parent
ID='kpf50-own-child-map-acquisition-r2-20261105'
mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
root=B/'out'/mode/uuid.uuid4().hex
root.mkdir(parents=True,exist_ok=False)
result={'id':ID,'mode':mode,'status':'UNKNOWN','scientific_validity':'UNKNOWN','records':[],'cleanup':[],'root':str(root)}
spec=importlib.util.spec_from_file_location('acquisition',B/'acquire.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
deadline=time.monotonic()+240

def guard():
    if (B/'STOP').exists() or time.monotonic()>=deadline: raise RuntimeError('STOP/deadline')

def interrupted(signum,frame): raise RuntimeError('signal '+str(signum))
for signum in (signal.SIGTERM,signal.SIGINT): signal.signal(signum,interrupted)

def child_case(label):
    ready=root/(label+'.ready.json')
    with (root/(label+'.stdout')).open('wb') as stdout,(root/(label+'.stderr')).open('wb') as stderr:
        c=m.OwnChild([sys.executable,'-B','-I',str(B/'leaf.py'),str(private),str(ready),label],env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},cwd=root,stdout=stdout,stderr=stderr)
        try:
            while not ready.exists():
                guard();c.check();time.sleep(.02)
            witness=json.loads(ready.read_text())
            if witness!={'pid':c.process.pid,'mapped':str(private),'mode':label}: raise RuntimeError('readiness identity mismatch')
            if label=='honest':
                malformed=c.capture(max_segment_bytes=0)
                if malformed['status']!='UNKNOWN' or 'invalid read bound' not in malformed.get('reason',''): raise RuntimeError('malformed refusal missing')
                result['records'].append({'case':'malformed-bound','record':malformed})
            guard()
            record=c.capture();result['records'].append({'case':label,'record':record})
            if label=='honest' and record['status']=='OBSERVED_FILE_RANGES':
                dsos=[r for r in record['mappings'] if r['pathname_observed']==str(private)]
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
    honest=child_case('honest')
    if honest['status']!='OBSERVED_FILE_RANGES':
        result['reason']='Native map_files unavailable; no synthetic substitute; stopped after original honest attempt.'
        if mode=='smoke': result['status']='SMOKE_REFUSAL_OBSERVED';rc=0
    else:
        denied=child_case('denied')
        if denied['status']!='UNKNOWN' or not any(x in denied.get('reason','') for x in ('PermissionError','Operation not permitted','Permission denied')): raise RuntimeError('actual kernel permission refusal absent')
        result['status']='SMOKE_ACQUISITION_QUALIFIED' if mode=='smoke' else 'ACQUISITION_QUALIFIED';rc=0
    guard()
except (OSError,ValueError,RuntimeError) as exc:
    result['status']='UNKNOWN';result['reason']=f'{type(exc).__name__}: {exc}';rc=2
finally:
    result['end_monotonic_raw_ns']=m.now()
    raw=json.dumps(result,indent=2)+'\n'
    (root/'RESULT.json').write_text(raw)
    receipt=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(B/'out'/'RESULT.json')))
    receipt.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(raw)
sys.exit(rc)
