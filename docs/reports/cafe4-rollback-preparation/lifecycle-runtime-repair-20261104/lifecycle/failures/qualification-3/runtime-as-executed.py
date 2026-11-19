import datetime,hashlib,json,os,pathlib,re,resource,signal,subprocess,sys,time,uuid
D=pathlib.Path('/mnt/raid0/llm/tmp/df2/cafe4-lifecycle-runtime')
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def output():return pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_DRYRUN')=='1' else D/'RESULT.json'
def atomic(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.'+uuid.uuid4().hex);q.write_text(json.dumps(d,sort_keys=True)+'\n');os.replace(q,p)
def check_input():
 m=json.loads((D/'INPUTS.json').read_text())
 for p,h in {**m['artifact_files'],**m['corrected_source'],**m['headers']}.items():assert digest(p)==h
 compiler_path=pathlib.Path(m['compiler']['path']);compiler_path=compiler_path if compiler_path.exists() else pathlib.Path('/proc/1/root'+str(compiler_path));assert digest(compiler_path)==m['compiler']['sha256']
 src=m['source_tree'];assert subprocess.check_output(['git','-C',src['path'],'rev-parse','HEAD'],text=True).strip()==src['commit']
 assert hashlib.sha256(subprocess.check_output(['git','-C',src['path'],'diff','--binary','--abbrev=10','HEAD'])).hexdigest()==src['diff_sha256']
 p=pathlib.Path(m['model']['path']);s=p.stat();actual={'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns};assert actual==m['model']['stat'];return m
if sys.argv[1]=='predicate':
 try:
  p=output();r=json.loads(p.read_text());assert r['status']=='LIFECYCLE_OBSERVED' and r['child_reaped'] is True and r['draft_width']>0 and r['scope']=='lifecycle only; rollback/fault UNKNOWN' and p.stat().st_mtime>=int(os.environ['FILLER_SMOKE_T0']);check_input()
 except Exception:sys.exit(1)
 sys.exit(0)
if sys.argv[1]=='check':
 r=json.loads(output().read_text());assert r['status']=='LIFECYCLE_OBSERVED' and r['child_reaped'] is True;sys.exit(0)
m=check_input();attempt=uuid.uuid4().hex;R=D/'runs'/attempt;R.mkdir(parents=True);log=R/'native.log';deadline=float(os.environ['FILLER_DEADLINE']);stop=pathlib.Path(os.environ['FILLER_STOPFILE']);started=datetime.datetime.now(datetime.timezone.utc).isoformat();seen={};proc=None;rc=None;cutoff=None
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
exe=R/'cafe4-mtp-lifecycle-loadmtp';src=pathlib.Path(m['source_tree']['path']);compile_command=[m['compiler']['path'],'-std=c++17','-O2','-I'+str(D),'-I'+str(src/'common'),'-I'+str(src/'src'),'-I'+str(src/'include'),'-I'+str(src/'ggml/include'),str(D/'candidate.cpp'),'-L'+str(D/'bin'),'-Wl,-rpath,'+str(D/'bin'),'-llama-common','-llama','-pthread','-o',str(exe)]
with (R/'compile.log').open('w') as f:
 build_rc=subprocess.run([sys.executable,str(D/'supervise.py'),str(stop),str(int(deadline)),*compile_command],stdout=f,stderr=subprocess.STDOUT).returncode
if build_rc!=0:
 atomic(output(),{'schema':'cafe4.lifecycle.result.v1','status':'UNKNOWN','scope':'lifecycle only; rollback/fault UNKNOWN','attempt':attempt,'build_rc':build_rc,'run':str(R)});sys.exit(2)
assert exe.is_file() and b'MTP_LIFECYCLE' in subprocess.check_output(['strings',str(exe)])
check_input()
try:
 with log.open('w') as stream:
  proc=subprocess.Popen([str(exe),m['model']['path']],stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,LD_LIBRARY_PATH=str(D/'bin'),OMP_NUM_THREADS='1'),start_new_session=True)
  while proc.poll() is None:
   try:
    maps=pathlib.Path(f'/proc/{proc.pid}/maps').read_text();paths=sorted(set(line.split()[-1] for line in maps.splitlines() if len(line.split())>=6 and ('/libggml' in line or '/libllama' in line)))
    for p in paths:
     q=str(pathlib.Path(p).resolve());assert q in m['artifact_files'],'foreign ggml/llama mapping '+q;seen[q]=m['artifact_files'][q]
    if paths:(R/'loaded-libraries.json').write_text(json.dumps({'pid':proc.pid,'sample_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'maps':paths},sort_keys=True))
   except FileNotFoundError:pass
   if stop.exists() or time.time()>=deadline:cutoff='STOP' if stop.exists() else 'deadline';proc.terminate();break
   time.sleep(.05)
  try:rc=proc.wait(timeout=10)
  except subprocess.TimeoutExpired:proc.kill();rc=proc.wait(timeout=10)
finally:
 if proc is not None and proc.poll() is None:
  proc.kill();rc=proc.wait(timeout=10)
text=log.read_text() if log.exists() else '';matches=re.findall(r'^MTP_LIFECYCLE width=(\d+) accepted=(\d+)$',text,re.M);expected={p for p in m['artifact_files'] if '/libggml' in p or '/libllama' in p};ok=(cutoff is None and rc==2 and len(matches)==1 and 'UNKNOWN rollback and fault controls unimplemented' in text and expected<=set(seen))
width,accepted=map(int,matches[0]) if len(matches)==1 else (0,0);ok=ok and 0<width<=3 and 0<=accepted<=width
r={'schema':'cafe4.lifecycle.result.v1','status':'LIFECYCLE_OBSERVED' if ok else 'UNKNOWN','scope':'lifecycle only; rollback/fault UNKNOWN','attempt':attempt,'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'qualification' if os.environ.get('FILLER_DRYRUN')=='1' else 'scheduled','model':m['model'],'inputs_sha256':digest(D/'INPUTS.json'),'child_rc':rc,'child_reaped':proc is not None and proc.poll() is not None,'pid':proc.pid if proc else None,'draft_width':width,'accepted':accepted,'loaded_libraries':seen,'expected_libraries':sorted(expected),'cutoff':cutoff,'affinity':sorted(os.sched_getaffinity(0)),'run':str(R),'raw_log_sha256':digest(log),'native_executable':str(exe),'native_executable_sha256':digest(exe),'compile_command':compile_command,'compile_log_sha256':digest(R/'compile.log'),'source_sha256':m['corrected_source'],'compiler':m['compiler'],'limitations':['fixed one-prompt lifecycle prerequisite','return code 2 is expected explicit unimplemented rollback/fault, not parent PASS','no rollback, fault sensitivity, parity or performance verdict']}
check_input();atomic(output(),r);sys.exit(0 if ok else 2)
