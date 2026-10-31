import pathlib,os,sys,time,json,hashlib,subprocess,signal,threading,re,fcntl,datetime
D=pathlib.Path(__file__).parent;S=D.parent;B=S/'build-hip';sys.path.insert(0,str(D))
from runtime_helpers import proc_rows,capture,signal_matching
from native_checks import CASES,NMSE_GATE,exact_numerical_pass,exact_trace_pass
start=time.monotonic();deadline=start+280;stopping=False
for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *_:globals().__setitem__('stopping',True))
lock=open(D/'writer.lock','a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Immutable build/source custody before invoking a device-touching executable.
terminal=json.loads((S/'HIP-TERMINAL.json').read_text());assert terminal['status']=='PASS_BUILD_ONLY'
for path,meta in terminal['images'].items():assert sha(pathlib.Path(path))==meta['sha256']
for line in (S/'PATCHED-SOURCE-SHA256SUMS').read_text().splitlines():
 digest,path=line.split(None,1);assert sha(S/'source'/path)==digest
for line in (D/'SOURCES.sha256').read_text().splitlines():
 digest,path=line.split(None,1);assert sha(pathlib.Path(path))==digest
os.environ.update(LD_LIBRARY_PATH=str(B/'bin')+':/opt/rocm/lib:/opt/rocm/lib64',GGML_BACKEND_PATH=str(B/'bin'),GGML_CUDA_DELTANET_CHUNKED_DEBUG='1',GGML_CUDA_DISABLE_DELTANET_CHUNKED='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',HIP_VISIBLE_DEVICES='0',ROCR_VISIBLE_DEVICES='0')
# Exact loader check runs inside R7, never as an unclaimed GPU probe.
link=subprocess.run(['/bin/bash','/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',str(B/'bin/test-backend-ops'),str(B/'bin')],capture_output=True,text=True)
(D/'runtime-linkage.log').write_text(link.stdout+link.stderr)
assert link.returncode==0,'runtime linkage preflight failed'
run=D/('run-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));run.mkdir()
receipts=[];partial=False
manifest_sha=sha(S/'IMAGE-SHA256SUMS')
if (D/'LATEST-RESULT.json').exists():
 prior=json.loads((D/'LATEST-RESULT.json').read_text())
 if prior.get('image_manifest_sha256')==manifest_sha:
  receipts=[r for r in prior.get('receipts',[]) if not r.get('partial')]
completed={(r['tokens'],r['seqs']) for r in receipts}
assert len(completed)==len(receipts) and completed.issubset(set(CASES))
for tokens,seqs in CASES:
 if (tokens,seqs) in completed:continue
 if stopping or time.monotonic()>=deadline:partial=True;break
 ident=f't{tokens}-s{seqs}';prefix=f'type=f32,head_count=32,head_size=128,n_seq_tokens={tokens},n_seqs={seqs},v_repeat=1,permuted=0,kda=0,K=1'
 command=[str(B/'bin/test-backend-ops'),'-o','GATED_DELTA_NET','-b','ROCm0','-p','^'+prefix+'$']
 out=open(run/(ident+'.stdout.log'),'w');err=open(run/(ident+'.stderr.log'),'w')
 p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,start_new_session=True)
 rows=proc_rows();birth=rows[p.pid]['birth'];owned={p.pid:birth};events=[];samples=[];maps={};peak=0;count=0;stopped=False
 def pump(stream,dest,label):
  for line in stream:
   dest.write(line);dest.flush()
   if label=='stderr' and '[gdn] chunked dispatch' in line:events.append({'monotonic':time.monotonic(),'line':line.strip()})
 threads=[threading.Thread(target=pump,args=(p.stdout,out,'stdout')),threading.Thread(target=pump,args=(p.stderr,err,'stderr'))]
 for t in threads:t.start()
 def sample():
  global peak,count
  rows=proc_rows();live=capture(owned,rows);rss=sum(rows[pid]['rss'] for pid in live);peak=max(peak,rss);count+=1
  # Every residency sample occurs while this exact PID/birth is live.
  if rows.get(p.pid,{}).get('birth')!=birth or rows[p.pid]['state']=='Z':return live
  try:
   text=pathlib.Path('/proc',str(p.pid),'maps').read_text()
   for line in text.splitlines():
    path=line.split()[-1]
    if path.startswith('/') and any(n in path for n in ('libggml-hip.so','libggml-base.so','libggml-cpu.so','libggml.so')):
     resolved=str(pathlib.Path(path).resolve())
     if resolved not in maps:maps[resolved]=sha(pathlib.Path(resolved))
  except OSError:pass
  vram={}
  for path in pathlib.Path('/sys/class/drm').glob('card[0-9]*/device/mem_info_vram_used'):
   try:vram[str(path)]=int(path.read_text())
   except (OSError,ValueError):pass
  kfd_path=pathlib.Path('/sys/class/kfd/kfd/proc',str(p.pid));kfd=kfd_path.exists()
  own_vram={}
  for path in kfd_path.glob('vram_*'):
   try:own_vram[path.name]=int(path.read_text().strip())
   except (OSError,ValueError):pass
  now_rows=proc_rows()
  if now_rows.get(p.pid,{}).get('birth')!=birth or now_rows[p.pid]['state']=='Z':return live
  # Keep the first two positive samples and samples overlapping the traced run window;
  # also retain counts, so a short run can remain explicitly unwitnessed.
  if kfd and any(v>0 for v in own_vram.values()):
   if len(samples)<2 or (events and len(samples)<32):samples.append({'monotonic':time.monotonic(),'pid':p.pid,'birth':birth,'kfd_pid_present':kfd,'own_kfd_vram_bytes':own_vram,'device_vram_bytes':vram})
  return live
 while p.poll() is None:
  sample()
  if stopping or time.monotonic()>=deadline or peak>8*1024**3:
   stopped=True
   for sig,grace in ((signal.SIGTERM,2),(signal.SIGKILL,2)):
    until=time.monotonic()+grace
    while True:
     live=sample()
     for pid,b in live.items():signal_matching(pid,b,sig)
     rows=proc_rows();active={pid:b for pid,b in live.items() if rows.get(pid,{}).get('birth')==b and rows[pid]['state']!='Z'}
     if not active or time.monotonic()>=until:break
     time.sleep(.05)
   break
  time.sleep(.01)
 try:rc=p.wait(timeout=2)
 except subprocess.TimeoutExpired:raise RuntimeError('native root not drained')
 for t in threads:t.join(timeout=2)
 assert not any(t.is_alive() for t in threads),'native log readers not drained'
 out.close();err.close()
 rows=proc_rows();live=capture(owned,rows);undrained=[{'pid':pid,'birth':b} for pid,b in live.items() if rows[pid]['state']!='Z']
 assert not undrained,'native descendants not drained'
 stdout=re.sub(r'\x1b\[[0-9;]*m','',(run/(ident+'.stdout.log')).read_text());stderr=(run/(ident+'.stderr.log')).read_text()
 numerical=exact_numerical_pass(stdout,prefix,rc)
 required=seqs==2
 trace=exact_trace_pass(events,tokens)
 loaded=any('libggml-hip.so' in path and digest==terminal['images'][str(B/'bin/libggml-hip.so')]['sha256'] for path,digest in maps.items())
 witnessed=loaded and len(samples)>=2
 if required:witnessed=witnessed and any(sample['monotonic']>=events[0]['monotonic'] for sample in samples) if events else False
 receipt={'tokens':tokens,'seqs':seqs,'command':command,'pid':p.pid,'birth':birth,'rc':rc,'numerical_pass_unrelaxed_1e_7':numerical,'required_chunked_trace':required,'trace_pass':trace if required else None,'dispatch_events':events,'loaded_images':maps,'native_residency_witnessed':witnessed,'residency_samples':samples,'sample_count':count,'peak_tree_rss_bytes':peak,'partial':stopped,'live_after':undrained,'raw_dir':str(run),'standalone_CPU_control_run':False}
 receipt['dispatch_proven_numerical_failure']=required and trace and any('GATED_DELTA_NET('+prefix+'):' in line and line.strip().endswith('FAIL') for line in stdout.splitlines())
 receipts.append(receipt);(run/(ident+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 if receipt['dispatch_proven_numerical_failure']:
  trigger={'task':'G16b - diagnostic arm if a dispatch-proven G16 fails 1e-7','failed_case':[tokens,seqs],'receipt':str(run/(ident+'.receipt.json')),'next_action':'Prepare separate experimental scalar-f32 diagnostic build: FGDN_TILE_MMA undefined while host arch gate still admits chunked. Preserve original1e-7 gate. Do this before relaxing or declining. No automatic kernel/source change in native qualifier.'}
  (D/'G16B-TRIGGER.json').write_text(json.dumps(trigger,indent=2)+'\n');(D/'G16B-TRIGGER.flag').touch()
  pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/codex-channels/NI-G16B-DISPATCH-PROVEN-FAILURE-20261031.flag').touch()
 if stopped:partial=True;break
all_cases=len(receipts)==len(CASES) and not partial
passed=all_cases and all(r['numerical_pass_unrelaxed_1e_7'] and r['native_residency_witnessed'] and (not r['required_chunked_trace'] or r['trace_pass']) for r in receipts)
result={'status':'PASS_G16A_NATIVE_SCOPE_ONLY' if passed else ('PARTIAL' if partial else 'FAIL_OR_UNWITNESSED'),'partial':partial,'original_cases':CASES,'nmse_gate':NMSE_GATE,'receipts':receipts,'wall_s':time.monotonic()-start,'greedy_AB':'NOT_RUN','keep_rs':'NOT_QUALIFIED','champion_integration':'HOLD_FOR_NATIVE_REVIEW','source_commit':'af90102c7c3659c78b4e4c87698e258525c77000','image_manifest_sha256':manifest_sha}
(run/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');(D/'LATEST-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');(D/'NATIVE-TERMINAL.flag').touch()
with open('/mnt/raid0/llm/tmp/compute-flags/codex-channels/codex3.md','a') as f:f.write('\n## NI G16a native terminal (scope pending review)\n'+json.dumps({'status':result['status'],'partial':partial,'completed_cases':len(receipts),'result':str(run/'RESULT.json'),'greedy_AB':'NOT_RUN','keep_rs':'NOT_QUALIFIED','champion_integration':'HOLD_FOR_NATIVE_REVIEW'})+'\n')
pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/codex-channels/NI-G16A-NATIVE-TERMINAL-20261031.flag').touch()
sys.exit(75 if partial else (0 if passed else 1))
