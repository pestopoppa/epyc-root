#!/usr/bin/env python3
"""One reviewed post-build qualification attempt; never publishes."""
import datetime,hashlib,json,os,subprocess,time,sys,fcntl,signal,select
sys.path.insert(0,"/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/build-r3")
import pidfd_subreaper_v3 as subreaper
import pf1_graceful
from classifier import classify
from pathlib import Path
B=Path('/mnt/raid0/llm/tmp/codex3-kpf183-e332-build-r2-20261030');D=Path('/mnt/raid0/llm/tmp/codex3-kpf183-multiturn-20261030');R=Path('/mnt/raid0/llm/tmp/compute-flags/ready');S=Path('/mnt/raid0/llm/tmp/codex3-kpf183-postbuild-repair-20261031');rid='codex3-kpf183-multiturn-r1-20261030'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check_prior_attempts():
 for prior in S.glob('attempt-*'):
  if not prior.is_dir():continue
  try:data=json.loads((prior/'status.json').read_text())
  except (OSError,ValueError):raise RuntimeError('ambiguous prior attempt: '+str(prior))
  if data.get('state')!='RETRYABLE_PRE_NATIVE_ADMISSION_REFUSAL':
   raise RuntimeError('prior attempt is not retryable: '+str(prior))
def fsync_dir(p):
 fd=os.open(str(p),os.O_RDONLY|os.O_DIRECTORY)
 try: os.fsync(fd)
 finally: os.close(fd)
def sync_tree(root):
 for directory,dirs,files in os.walk(root,topdown=False):
  for name in files:
   path=Path(directory,name)
   if path.is_symlink():continue
   fd=os.open(path,os.O_RDONLY)
   try:os.fsync(fd)
   finally:os.close(fd)
  fsync_dir(Path(directory))
def write_status(attempt,state,**extra):
 tmp=attempt/'status.tmp'
 with tmp.open('w') as f:
  json.dump({'state':state,**extra},f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,attempt/'status.json');fsync_dir(attempt)
def archive(attempt,name):
 p=D/'smoke-final'
 if p.exists():
  p.rename(attempt/name);fsync_dir(D);fsync_dir(attempt)
def verify_control(attempt,phase):
 control='/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf'
 assert os.stat(control).st_size==811843840
 out=attempt/('control-'+phase+'.log')
 cmd=['flock','-n','/mnt/raid0/llm/tmp/compute-flags/prep-locks/28-29.lock','taskset','-c','124,125','env','OMP_NUM_THREADS=1','sudo','-n','--preserve-env=OMP_NUM_THREADS','/usr/bin/chroot','/proc/1/root','/usr/bin/setpriv','--reuid=1000','--regid=1000','--groups=992','/usr/bin/python3','-B','/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/build-r3/r11_supervisor.py','260','--','sha256sum',control]
 with out.open('x') as f:
  r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT);f.flush();os.fsync(f.fileno())
 lines=out.read_text().splitlines()
 assert r.returncode==0 and lines[0].split()[0]=='0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c'
 assert classify(r.returncode,out.read_text(),False)=='SUPERVISOR_PASS_REQUIRES_RESULT_VALIDATION'
def descendants(root):
 seen=set();pending=[root]
 while pending:
  pid=pending.pop()
  if pid in seen:raise RuntimeError('duplicate descendant')
  seen.add(pid)
  try:
   for task in Path('/proc',str(pid),'task').iterdir():
    try:pending.extend(int(x) for x in (task/'children').read_text().split())
    except FileNotFoundError:pass
  except FileNotFoundError:pass
 return seen-{root}
def captured_server(root):
 for pid in descendants(root):
  try:
   cmd=Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')
   if not cmd or not cmd[0].endswith(b'/llama-server'):continue
   fd=os.pidfd_open(pid)
   try:
    raw=Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()
    if raw[0] in ('Z','X') or pid not in descendants(root):
     os.close(fd);continue
    return fd,pid,int(raw[19])
   except BaseException:
    os.close(fd);raise
  except (FileNotFoundError,ProcessLookupError):continue
 return None
def remove_owned_stop(path,identity):
 try: st=path.stat()
 except FileNotFoundError: raise RuntimeError('owned STOP disappeared')
 if (st.st_dev,st.st_ino)!=identity: raise RuntimeError('STOP identity changed; refusing unlink')
 path.unlink();fsync_dir(path.parent)

def note(s):print(datetime.datetime.now(datetime.timezone.utc).isoformat(),s,flush=True)

def interrupted(sig,frame):
 raise InterruptedError('qualification interrupted by signal '+str(sig))
def preflight_host():
 assert Path('/mnt/micron/codex3-lanes/kpf-e332-src').is_dir()
 assert sha(B/'launch.sh')=='6066a2673a301943e114a475c2b295a995c053b53eed831a355c3dc627fe37d7'
 assert sha(B/'job.sh')=='cd2d004f9150b1d8a985133e64a08fad330df0217bdefa91490ae59943fc61cc'
 assert sha(B/'SOURCES.sha256')=='450379d17481937f1ce7565a99417e216cef4409d903cecfeb46088b4d5ff7e0'
 subprocess.run(['sha256sum','--strict','--quiet','-c',str(B/'SOURCES.sha256')],cwd=B,check=True)
 assert sha(B/'source-files.sha256')=='86e34ae3450420e3afc07f56e692b81d8cc8ebba5fdb74fd6e942297e6dc509b'
 subprocess.run(['sha256sum','--strict','--quiet','-c',str(B/'source-files.sha256')],cwd='/mnt/micron/codex3-lanes/kpf-e332-src',check=True)
 assert (B/'BUILD-SUCCESS').read_text().strip()=='/mnt/micron/codex3-lanes/kpf-e332-build/bin/llama-server'
 expected_bins={'/mnt/micron/codex3-lanes/kpf-e332-build/bin/'+x for x in ('llama-server','libllama-server-impl.so','libllama-common.so','libllama.so','libggml-cpu.so')}
 digest_lines=(B/'BUILD-DIGESTS.txt').read_text().splitlines()
 assert len(digest_lines)==5 and {line.split('  ',1)[1] for line in digest_lines}==expected_bins
 subprocess.run(['sha256sum','--strict','--quiet','-c',str(B/'BUILD-DIGESTS.txt')],check=True)
 assert not (D/'run/pending.json').exists() and not (D/'run/RESULT.json').exists() and not (D/'STOP').exists()
 assert sha(D/'launch.sh')=='52c2020e2c475ecea606c35badbf4299da38ab81e3dcf31321fa71be66cc2e24'
 assert sha(D/'SOURCES.sha256')=='e47b35b1ac190797796c85a0573658ec6f3315028fe2ed244e70f60ae02f0b5a'
 subprocess.run(['sha256sum','--strict','--quiet','-c',str(D/'SOURCES.sha256')],cwd=D,check=True)
 m=json.loads((D/'MANIFEST-STAGED.json').read_text())
 assert m['full_model']=='/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
 assert (m['full_model_size'],m['full_model_first64_sha256'],m['full_model_last64_sha256'])==(37801097504,'3711c69305b6d77a3a8bc69abff096cda9f90238887f29ce3e83ec5f3cd348eb','d90af8cf5c5047a758c11a6fd64f4902708f55cb96bee73201814f4755954bfa')
 assert m['full_model_sha256_verified']==m['full_model_sha256_expected']=='c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131'
 with open(m['full_model'],'rb') as f:
  n=os.fstat(f.fileno()).st_size;first=hashlib.sha256(f.read(64*1024**2)).hexdigest();f.seek(n-64*1024**2);last=hashlib.sha256(f.read()).hexdigest()
 assert (n,first,last)==(m['full_model_size'],m['full_model_first64_sha256'],m['full_model_last64_sha256'])
 cases=json.loads((D/'prompts.json').read_text())
 assert len(cases['full'])==4 and len(cases['smoke'])==2
 assert not ({x['id'] for x in cases['full']} & {x['id'] for x in cases['smoke']})
 assert not ({x['prompt'] for x in cases['full']} & {x['prompt'] for x in cases['smoke']})
 expected_launcher=sha(D/'launch.sh');expected_catalog=sha(D/'SOURCES.sha256')
def run():
 global lock
 if not __debug__:raise RuntimeError('optimized Python is forbidden')
 if sys.argv[1:] != ['--execute-one-attempt']: raise SystemExit('REVIEW CANDIDATE: explicit --execute-one-attempt required')
 lock=(S/'qualification.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if os.getuid()!=1000 or os.readlink('/proc/self/ns/mnt')!=os.readlink('/proc/1970275/ns/mnt'):raise RuntimeError('wrong user or keeper mount namespace')
 assert Path('/workspace/scripts/coordination/validate_fillers.py').is_file()
 assert sha(D/'launch.sh')=='52c2020e2c475ecea606c35badbf4299da38ab81e3dcf31321fa71be66cc2e24'
 assert sha(D/'SOURCES.sha256')=='e47b35b1ac190797796c85a0573658ec6f3315028fe2ed244e70f60ae02f0b5a'
 check_prior_attempts()
 if not (B/'BUILD-SUCCESS').is_file() or not (B/'BUILD-DIGESTS.txt').is_file():raise RuntimeError('actual build success and digests required')
 attempt=S/('attempt-'+str(time.time_ns()));attempt.mkdir();fsync_dir(S)
 write_status(attempt,'PREPARING',native_exposure='none')
 preflight_log=attempt/'preflight.log'
 cmd=['flock','-n','/mnt/raid0/llm/tmp/compute-flags/prep-locks/28-29.lock','taskset','-c','124,125','env','OMP_NUM_THREADS=1','sudo','-n','--preserve-env=OMP_NUM_THREADS','/usr/bin/chroot','/proc/1/root','/usr/bin/setpriv','--reuid=1000','--regid=1000','--groups=992','/usr/bin/python3','-B','/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/build-r3/r11_supervisor.py','260','--','/usr/bin/python3','-B',__file__,'--preflight-host']
 with preflight_log.open('x') as f:
  pre=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT);f.flush();os.fsync(f.fileno())
 pre_class=classify(pre.returncode,preflight_log.read_text(),False)
 if pre_class!='SUPERVISOR_PASS_REQUIRES_RESULT_VALIDATION':
  write_status(attempt,pre_class,rc=pre.returncode,log=str(preflight_log))
  raise RuntimeError('bounded preflight failed; inspect '+str(preflight_log))
 cases=json.loads((D/'prompts.json').read_text())
 expected_launcher=sha(D/'launch.sh');expected_catalog=sha(D/'SOURCES.sha256')
 verify_control(attempt,'before')
 archive(attempt,'prior-smoke')
 try:
  write_status(attempt,'STARTING',native_exposure='unknown until classified')
  log=attempt/'launcher.log'
  with log.open('x') as f:
   p=subprocess.Popen([str(D/'launch.sh'),'--smoke'],stdout=f,stderr=subprocess.STDOUT)
   try:p.wait()
   except BaseException:
    pf1_graceful.drain(leader=p);p.wait();raise
   finally:f.flush();os.fsync(f.fileno())
  if subreaper.children():
   pf1_graceful.drain();raise RuntimeError('unexpected descendants after normal supervisor exit')
  result=classify(p.returncode,log.read_text(),(D/'smoke-final').exists())
  write_status(attempt,result,rc=p.returncode,log=str(log))
  if result!='SUPERVISOR_PASS_REQUIRES_RESULT_VALIDATION':raise SystemExit('qualification halted; inspect '+str(attempt))
  r=json.loads((D/'smoke-final/RESULT.json').read_text());rows=r['records']
  assert r['complete'] and r['smoke'] and len(rows)==6 and {x['arm'] for x in rows}=={'champion','fork-off','fork-on'}
  assert {(x['arm'],x['case']['id']) for x in rows} == {(a,c['id']) for a in ('champion','fork-off','fork-on') for c in cases['smoke']}
  assert all(x['model']=='/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf' and x['trunk']['ok'] and len(x['children'])==2 and {c['slot'] for c in x['children']}=={1,2} and all(c['ok'] for c in x['children']) for x in rows)
  champions=[line.split('  ',1)[0] for line in (B/'BUILD-DIGESTS.txt').read_text().splitlines() if line.endswith('/bin/llama-server')]
  assert len(champions)==1
  for rec in rows:
   assert rec['case']==next(c for c in cases['smoke'] if c['id']==rec['case']['id'])
   assert rec['binary_sha256']==(champions[0] if rec['arm']=='champion' else '1442c95d7516efadda0639cf07319078df0bae326b6a9bb95d72532b1499ad67')
   argv=rec['argv']
   if rec['arm']=='champion':assert '--slot-fork-min-tokens' not in argv
   else:assert argv[argv.index('--slot-fork-min-tokens')+1]==('0' if rec['arm']=='fork-off' else '1')

  assert sha(D/'launch.sh')==expected_launcher and sha(D/'SOURCES.sha256')==expected_catalog
  qualified=attempt/'normal-smoke';(D/'smoke-final').rename(qualified);fsync_dir(D);fsync_dir(attempt)
  write_status(attempt,'NORMAL_PASSED',normal_result=str(qualified/'RESULT.json'))
  # Same final launcher: STOP while our captured smoke server is live, then verify rc75 and partial writer.
  stop=D/'STOP';assert not stop.exists();stoplog=attempt/'STOP.log';stop_identity=None;server_fd=None
  with stoplog.open('w') as f:
   p=subprocess.Popen([str(D/'launch.sh'),'--smoke'],stdout=f,stderr=subprocess.STDOUT)
   try:
    for _ in range(2500):
     serverlog=D/'smoke-final/champion.server.log'
     if serverlog.exists() and 'listening on' in serverlog.read_text(errors='replace'):
      capture=captured_server(p.pid)
      if capture:
       server_fd,server_pid,server_birth=capture
       poll=select.poll();poll.register(server_fd,select.POLLIN)
       if not poll.poll(0):break
       os.close(server_fd);server_fd=None
     if p.poll() is not None:raise RuntimeError('STOP smoke exited before own server ready')
     time.sleep(.1)
    else:raise RuntimeError('STOP smoke timed out before server ready')
    write_status(attempt,'STOP_SERVER_CAPTURED',server_pid=server_pid,server_birth=server_birth)
    with stop.open('x') as sf:
     st=os.fstat(sf.fileno());stop_identity=(st.st_dev,st.st_ino);sf.write('owned postbuild STOP qualification\n');sf.flush();os.fsync(sf.fileno())
    fsync_dir(stop.parent)
    rc=p.wait(timeout=60);partial=json.loads((D/'smoke-final/PARTIAL.json').read_text())
    if rc!=75 or not partial['partial']:raise RuntimeError(f'STOP test invalid rc={rc}')
   finally:
    if p.poll() is None:pf1_graceful.drain(leader=p);p.wait()
    stray=bool(subreaper.children())
    if stray:pf1_graceful.drain()
    if stop_identity is not None:remove_owned_stop(stop,stop_identity)
    if server_fd is not None:os.close(server_fd)
    f.flush();os.fsync(f.fileno())
    if stray:raise RuntimeError('unexpected descendants after STOP supervisor exit')
  archive(attempt,'stop-smoke')
  verify_control(attempt,'after')
  write_status(attempt,'STOP_PASSED')
  # Validate keeper-transformed ARMED row against the real validator and a live owned poller.
  (D/'run').mkdir(exist_ok=True);(D/'ws58-launcher.out').touch(exist_ok=True)
  row=f'| {rid} | codex3 | {D}/launch.sh | any-cpu-quarter | 1800 | 64 | {D}/STOP | BACKLOG | block-correctness | 10800 | 1800 | n | y | /workspace/handoffs/active/kv-prefix-fork-and-paged-attention.md | Record KPF-18.3 end checkpoint and raw chat lanes with fork on off and exact e332 baseline | n/a (correctness diagnostic) | cpu | requested_window_s=10800; est_output_GiB=0.125; scratch_root={D}; launcher_log={D}/ws58-launcher.out; log_consumer={D}/job.py; result_path={D}/run/RESULT.json; model_path=/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf; model_sha256=c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131; keep_globs=*.sh,*.py,*.json,*.sha256,*.md,*.log,run/*.json,run/*.log,smoke-postbuild-qualified-*/*.json,smoke-postbuild-qualified-*/*.log,state/*.json,state/*.log; raw_globs=run/*.tmp,__pycache__/*; retention_v2=1; source KPF-18.3 fixed held-out cases, no redraw on unknown exposure |\n'
  header='| filler-id | owner | launcher + PID | resources | min useful window | max private RAM | STOP file | status | class | duration | min window | DS41-class y/n | ready y/n | prior | decision | min_effect | substrate | notes |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n'
  assert not (R/(rid+'.json')).exists() and not (R/'armed'/(rid+'.json')).exists()
  assert not (Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(rid+'.grant')).exists()
  env=dict(os.environ,WS58_REGIONS='0-23')
  with (attempt/'VALIDATOR-POLLER.log').open('w') as f:
   p=subprocess.Popen([str(D/'launch.sh')],env=env,stdout=f,stderr=subprocess.STDOUT)
   try:
    for _ in range(100):
     if p.poll() is not None:raise RuntimeError('validator poller exited')
     cmd=Path(f'/proc/{p.pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
     if 'filler_run13.sh' in cmd and rid in cmd:break
     time.sleep(.05)
    else:raise RuntimeError('validator poller not observed')
    c=row.split('|');c[3]=c[3].rstrip()+f' pid={p.pid} ';c[4]=' 0-23 ';c[8]=' ARMED ';c[13]=' y ';c[18]=c[18].rstrip()+'; claimed_cpus=0-23 ';(attempt/'VALIDATOR-FIXTURE.md').write_text(header+'|'.join(c)+'\n')
    q=subprocess.run(['python3','/workspace/scripts/coordination/validate_fillers.py','--file',str(attempt/'VALIDATOR-FIXTURE.md'),'--row',rid,'--for-grant'],capture_output=True,text=True)
    (attempt/'VALIDATOR.log').write_text(f'live_pid={p.pid}\n{cmd}\n{q.stdout}{q.stderr}rc={q.returncode}\n')
    if q.returncode:raise RuntimeError('full row validator refused')
   finally:
    if p.poll() is None:pf1_graceful.drain(leader=p);p.wait()
    if Path(f'/proc/{p.pid}').exists():raise RuntimeError('validator poller survived')

  obs=json.loads(next(x for x in reversed(log.read_text().splitlines()) if x.startswith('{') and 'sampled_peak_tree_rss_bytes' in x))
  assert obs['child_rc']==0 and obs['children_drained'] and obs['failure'] is None
  stop_obs=json.loads(next(x for x in reversed(stoplog.read_text().splitlines()) if x.startswith('{') and 'sampled_peak_tree_rss_bytes' in x))
  assert stop_obs['child_rc']==75 and stop_obs['children_drained'] and stop_obs['failure'] is None
  assert sha(D/'launch.sh')==expected_launcher and sha(D/'SOURCES.sha256')==expected_catalog
  sync_tree(attempt)
  write_status(attempt,'QUALIFIED_NOT_PUBLISHED',normal_result=str(qualified/'RESULT.json'),normal_log=str(log),stop_log=str(stoplog),validator_log=str(attempt/'VALIDATOR.log'))
  note('QUALIFIED_NOT_PUBLISHED '+str(attempt))

 except BaseException as exc:
  current=json.loads((attempt/'status.json').read_text())
  current['error']=repr(exc)
  state=current.pop('state')
  write_status(attempt,state,**current)
  raise
 finally:
  if (D/'smoke-final').exists():archive(attempt,'incomplete-smoke')
  sync_tree(attempt)

if __name__=='__main__':
 subreaper.enable()
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 try:
  if sys.argv[1:]==['--preflight-host']:preflight_host()
  else:run()
 finally:pf1_graceful.drain()
