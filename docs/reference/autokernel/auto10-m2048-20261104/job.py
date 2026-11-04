#!/usr/bin/env python3
"""Publisher-owned executor. Do not invoke directly; requires filler_run15 env."""
import hashlib, json, os, pathlib, shutil, signal, subprocess, sys, threading, time

D=pathlib.Path(__file__).resolve().parent
SRC=D/'mmid_roofline_probe_v3.cpp'; BIN=D/'bin/mmid_roofline_probe_v3'
INPUT=D/'inputs-v1'; BUILD='/mnt/raid0/llm/llama.cpp-experimental-deepseek41-20260923'
LIB=D/'vendor/lib'; HEADERS=D/'vendor/ggml-include'; VENDOR_MANIFEST=D/'vendor/manifest.json'
RL='/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock'
CHILD=None

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def stop(): return pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=int(os.environ['FILLER_DEADLINE'])
def cpus():
 out=[]
 for part in os.environ['FILLER_CPUS'].split(','):
  a,*r=part.split('-'); b=int(r[0]) if r else int(a); out.extend(range(int(a),b+1))
 return sorted(set(out))
def ensure_active():
 if stop(): raise RuntimeError('stop/deadline reached before arm')
def build():
 BIN.parent.mkdir(parents=True,exist_ok=True)
 vendor=json.loads(VENDOR_MANIFEST.read_text())
 for rel,expected in vendor['headers_sha256'].items():
  if sha(HEADERS/rel)!=expected: raise RuntimeError('compiler header changed before build: '+rel)
 for filename,pinned in vendor['libraries'].items():
  p=LIB/filename; st=p.stat()
  if st.st_dev!=pinned['device'] or st.st_ino!=pinned['inode'] or sha(p)!=pinned['sha256']:
   raise RuntimeError('private ggml DSO snapshot changed before build: '+filename)
 use=cpus()[:4]
 if len(use)<4: raise RuntimeError('publisher smoke needs four FILLER_CPUS')
 cmd=['c++','-O2','-std=c++17','-I'+str(HEADERS),str(SRC),'-L'+str(LIB),'-Wl,-rpath,'+str(LIB),'-lggml-cpu','-lggml','-lggml-base','-pthread','-o',str(BIN)]
 subprocess.run(['taskset','-c',','.join(map(str,use)),*cmd],check=True,env={**os.environ,'LD_LIBRARY_PATH':str(LIB),'OMP_NUM_THREADS':'4'})
 libs={}
 for n in ('libggml-cpu.so','libggml.so','libggml-base.so'):
  p=(LIB/n).resolve(); st=p.stat(); libs[n]={'path':str(p),'sha256':sha(p),'device':st.st_dev,'inode':st.st_ino}
 compdb=pathlib.Path(BUILD)/'build-cpu/compile_commands.json'
 iqk=bool(compdb.exists() and 'GGML_USE_IQK_MULMAT' in compdb.read_text(errors='replace'))
 repo=subprocess.run(['git','-C',BUILD,'rev-parse','HEAD'],check=True,text=True,capture_output=True).stdout.strip()
 manifest={'schema':'akx-auto10-build-manifest.v1','producer_source_sha256':sha(SRC),'binary_sha256':sha(BIN),'compiler':subprocess.run(['c++','--version'],text=True,capture_output=True).stdout.splitlines()[0],'compile_argv':cmd,'libraries_identity':libs,'vendor_manifest_sha256':sha(VENDOR_MANIFEST),'vendor_header_root':str(HEADERS),'library_source_provenance':'historical DSO; exact source/build provenance unproven','repository_head_observed':repo,'GGML_IQK':'1','compile_commands_has_GGML_USE_IQK_MULMAT':iqk,'input_manifest_sha256':sha(INPUT/'manifest.json')}
 (D/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest
def verify(manifest):
 if sha(SRC)!=manifest['producer_source_sha256'] or sha(BIN)!=manifest['binary_sha256']: raise RuntimeError('producer source/binary changed')
 if sha(INPUT/'manifest.json')!=manifest['input_manifest_sha256']: raise RuntimeError('prepared input manifest changed')
 if sha(VENDOR_MANIFEST)!=manifest['vendor_manifest_sha256']: raise RuntimeError('vendor manifest changed')
 vendor=json.loads(VENDOR_MANIFEST.read_text())
 for rel,expected in vendor['headers_sha256'].items():
  if sha(HEADERS/rel)!=expected: raise RuntimeError('compiler header changed: '+rel)
 for n,v in manifest['libraries_identity'].items():
  p=pathlib.Path(v['path']); st=p.stat()
  if st.st_dev!=v['device'] or st.st_ino!=v['inode'] or sha(p)!=v['sha256']: raise RuntimeError('pinned ggml library changed: '+n)
 im=json.loads((INPUT/'manifest.json').read_text())
 for f in im['files']:
  st=(INPUT/f['path']).stat()
  if st.st_ino!=f['inode'] or st.st_size!=f['bytes'] or st.st_mtime_ns!=f['mtime_ns'] or st.st_ctime_ns!=f['ctime_ns']:
   raise RuntimeError('prepared input identity changed; refusing to rehash during grant')
def monitor(proc, obs):
 while proc.poll() is None:
  row={'time_unix':time.time(),'pid':proc.pid,'scope':'overlaps whole native process, not inner graph timer'}
  try:
   row['affinity']=pathlib.Path(f'/proc/{proc.pid}/status').read_text().split('Cpus_allowed_list:\t')[1].splitlines()[0]
   maps=pathlib.Path(f'/proc/{proc.pid}/maps').read_text()
   mapped=[]
   for line in maps.splitlines():
    fields=line.split(None,5)
    if len(fields)==6 and 'libggml' in fields[5] and '/' in fields[5]: mapped.append({'path':fields[5],'device':fields[3],'inode':fields[4]})
   row['mapped_ggml_records']=mapped
   row['loaded_ggml_paths']=sorted(set(x['path'] for x in mapped))
   if mapped:
    lock=subprocess.run([RL,'status'],text=True,capture_output=True,timeout=5)
    row['region_lock_status']=lock.stdout[-4000:]; row['lock_status_rc']=lock.returncode
   else:
    row['region_lock_status']='not sampled before ggml mapping'
  except Exception as e: row['observation_error']=repr(e)
  row['filler_id']=os.environ.get('FILLER_ID','<unset>'); row['filler_deadline']=os.environ.get('FILLER_DEADLINE','<unset>')
  row['filler_end']=os.environ.get('FILLER_END','<unset>'); row['filler_cpus']=os.environ.get('FILLER_CPUS','<unset>')
  grant=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(row['filler_id']+'.grant')
  try: row['grant_file']={'path':str(grant),'text':grant.read_text()}
  except Exception as e: row['grant_file']={'path':str(grant),'observation_error':repr(e)}
  obs.append(row); time.sleep(.2 if row.get('mapped_ggml_records') else .002)
def validate(raw, nth, modes, kmax):
 lines=[json.loads(x) for x in raw.read_text().splitlines() if x.strip()]
 cells={}; times={}
 for r in lines:
  if r.get('schema')=='akx-all-26.cell.v1' and r.get('op')=='MUL_MAT_ID': cells[(r['shape'],r['mode'],r['k'],r['nth'])]=r
  if r.get('schema')=='akx-auto10-mmid-timing.v3' and r.get('status')=='observed': times[(r['shape'],r['mode'],r['k'],r['n_threads'])]=r
 keys=[('M2048',m,k,nth) for m in modes for k in range(1,kmax+1)]
 verified=[]
 for key in keys:
  c=cells.get(key); t=times.get(key)
  if not c or not t or c.get('verdict')!='PASS' or c.get('aa_clean') is not True or c.get('n_reps',0)<2: raise RuntimeError('missing correctness PASS/timing '+repr(key))
  b=[int(x) for x in t['batch_ns_raw'].split(',')]; s=[int(x) for x in t['serial_ns_raw'].split(',')]
  if len(b)<3 or len(b)!=len(s) or min(b+s)<=0: raise RuntimeError('bad timing samples '+repr(key))
  if t['logical_operand_bytes'] != t['logical_selected_weight_bytes']+t['activation_bytes']+t['ids_bytes']+t['output_bytes']: raise RuntimeError('byte formula mismatch')
  if t['batch_effective_logical_gb_s']<=0 or t['serial_effective_logical_gb_s']<=0: raise RuntimeError('nonpositive rate')
  t['correctness_verdict']=c['verdict']; t['correctness_aa_clean']=c['aa_clean']; t['correctness_reps']=c['n_reps']
  t['sample_unit']='seven repeated graph timing pairs in one process; not independent process samples'
  verified.append(t)
 if len(verified)!=len(keys): raise RuntimeError('incomplete cell set')
 return verified
def arm(label,nth,smoke,manifest):
 ensure_active(); allcpus=cpus(); use=allcpus[:nth]
 if len(use)<nth: raise RuntimeError(f'FILLER_CPUS has {len(use)} CPUs, needs {nth}')
 modes=['rand'] if smoke else ['rand','shared','disjoint']; km=1 if smoke else 9
 outdir=D/('smoke' if smoke else 'full')/label
 if outdir.exists():
  archived=D/'archive'/f'{outdir.parent.name}-{label}-{time.time_ns()}'
  archived.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(outdir),str(archived))
 outdir.mkdir(parents=True,exist_ok=True)
 raw=outdir/'native.raw.jsonl'; log=outdir/'native.stdout.log'; obs=[]
 args=[str(BIN),'--backend','cpu','--route','cpu','--op','mmid','--type','Q4_K','--shape','M2048','--mode',modes[0] if smoke else '', '--nth',str(nth),'--reps','2','--kmax',str(km),'--seed','20261102','--timed','--time-reps','7','--input-root',str(INPUT),'--out',str(raw)]
 if not smoke: args.remove('--mode'); args.remove('')
 env={**os.environ,'GGML_IQK':'1','OMP_NUM_THREADS':str(nth),'LD_LIBRARY_PATH':str(LIB)}
 with log.open('w') as lf:
  p=subprocess.Popen(['taskset','-c',','.join(map(str,use)),*args],stdout=lf,stderr=subprocess.STDOUT,env=env)
  try: birth=pathlib.Path(f'/proc/{p.pid}/stat').read_text().split(') ',1)[1].split()[19]
  except Exception: birth='unknown'
  sampler=threading.Thread(target=monitor,args=(p,obs),daemon=True); sampler.start()
  while p.poll() is None:
   if stop():
    p.send_signal(signal.SIGTERM)
    try: p.wait(timeout=3)
    except subprocess.TimeoutExpired:
     p.send_signal(signal.SIGKILL); p.wait()
    if p.poll() is None: raise RuntimeError('owned child did not terminate after STOP/deadline')
    raise RuntimeError(f'STOP/deadline during child pid={p.pid} start_ticks={birth}; partial arm only')
   time.sleep(.2)
  rc=p.wait(); sampler.join(timeout=2)
 if p.poll() is None: raise RuntimeError('child still alive after wait')
 if rc: raise RuntimeError(f'native child rc={rc}; see {log}')
 (outdir/'observations.json').write_text(json.dumps({'samples':obs,'sample_count':len(obs),'placement_observed':len(obs)>=2,'contention_status':'unknown unless region-lock output proves otherwise'},indent=2)+'\n')
 (outdir/'child-identity.json').write_text(json.dumps({'pid':p.pid,'start_ticks':birth,'dead_after_wait':p.poll() is not None,'returncode':rc},indent=2)+'\n')
 text=log.read_text(errors='replace')
 active='[iqk] ACTIVE:' in text
 if not active: raise RuntimeError('runtime IQK active capability line absent')
 mapped_records=[x for sample in obs for x in sample.get('mapped_ggml_records',[])]
 mapped={x['path']:x for x in mapped_records}
 mapped_hashes={}
 for name,pinned in manifest['libraries_identity'].items():
  path=pinned['path']; rec=mapped.get(path)
  if not rec or rec['path'].endswith(' (deleted)'):
   raise RuntimeError(f'live maps missing pinned ggml path: {name}')
  try: mapped_major, mapped_minor = (int(x, 16) for x in rec['device'].split(':'))
  except (ValueError, TypeError): raise RuntimeError(f'invalid mapped device: {name}')
  if (mapped_major, mapped_minor) != (os.major(pinned['device']), os.minor(pinned['device'])) or int(rec['inode'])!=pinned['inode']:
   raise RuntimeError(f'live maps do not match pinned ggml path/dev/inode: {name}')
  st=pathlib.Path(path).stat()
  digest=sha(path)
  if st.st_dev!=pinned['device'] or st.st_ino!=pinned['inode'] or digest!=pinned['sha256']:
   raise RuntimeError(f'ggml DSO changed during child: {name}')
  mapped_hashes[path]={'sha256':digest,'device':st.st_dev,'inode':st.st_ino,'maps_device':rec['device'],'maps_inode':rec['inode']}
 (outdir/'loaded-dso-hashes.json').write_text(json.dumps(mapped_hashes,indent=2)+'\n')
 rows=validate(raw,nth,modes,km)
 return rows
def main():
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if not smoke and (D/'results.jsonl').exists():
  (D/'archive').mkdir(exist_ok=True); shutil.move(str(D/'results.jsonl'),str(D/'archive'/f'results-{time.time_ns()}.jsonl'))
 if smoke:
  manifest=build()
  verify(manifest)
  rows=arm('m2048-4cpu',4,True,manifest)
  for r in rows: r.update({'producer_source_sha256':manifest['producer_source_sha256'],'binary_sha256':manifest['binary_sha256'],'input_manifest_sha256':manifest['input_manifest_sha256'],'loaded_dso_hash_file':'smoke/m2048-4cpu/loaded-dso-hashes.json','IQK_environment':'1','compiled_IQK_capability_observed':manifest['compile_commands_has_GGML_USE_IQK_MULMAT']})
  native_path=os.environ.get('FILLER_DRYRUN_RESULT_PATH')
  if not native_path: raise RuntimeError('publisher dry-run native result path missing')
  smoke_obj={'schema':'akx-auto10-publisher-smoke.v1','verdict':'PASS','manifest_sha256':sha(D/'build-manifest.json'),'records':rows,'scope':'one synthetic native M2048/rand/k=1 cell at four publisher CPUs'}
  tmp=pathlib.Path(native_path+'.tmp'); tmp.write_text(json.dumps(smoke_obj,sort_keys=True,allow_nan=False)+'\n'); os.replace(tmp,native_path)
  return
 manifest=json.loads((D/'build-manifest.json').read_text()); verify(manifest)
 (D/'full'/'RESULT.json').unlink(missing_ok=True)
 allrows=[]
 for n in (48,96):
  ensure_active(); armrows=arm(f'threads-{n}',n,False,manifest)
  for r in armrows:
   r.update({'producer_source_sha256':manifest['producer_source_sha256'],'binary_sha256':manifest['binary_sha256'],'input_manifest_sha256':manifest['input_manifest_sha256'],'loaded_dso_hash_file':f'full/threads-{n}/loaded-dso-hashes.json','IQK_environment':'1','compiled_IQK_capability_observed':manifest['compile_commands_has_GGML_USE_IQK_MULMAT']})
  allrows.extend(armrows)
  (D/'results.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in allrows))
 (D/'full'/'RESULT.json').write_text(json.dumps({'schema':'akx-auto10-full-result.v1','manifest_sha256':sha(D/'build-manifest.json'),'units':len(allrows),'thread_arms':[48,96],'scope':'synthetic M2048 only; diagnostic effective logical bandwidth; no DRAM or model claim'},indent=2)+'\n')
if __name__=='__main__':
 try: main()
 except Exception as e:
  partial={'schema':'akx-auto10-partial.v1','error':str(e),'stopfile_seen':pathlib.Path(os.environ.get('FILLER_STOPFILE','/nonexistent')).exists(),'time_unix':time.time(),'success':False}
  (D/'PARTIAL.json').write_text(json.dumps(partial,indent=2)+'\n')
  print('row failure:',e,file=sys.stderr); sys.exit(1)
