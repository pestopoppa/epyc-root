#!/usr/bin/env python3
import hashlib,json,os,re,signal,statistics,subprocess,sys,tempfile,time
from pathlib import Path
from custody import Refusal,birth_ticks,child_setup,terminate_owned,read_kfd,validate_cpu_grant
import device_identity
from datetime import datetime,timezone
from belief_write import write_child
D=Path(__file__).resolve().parent
ID='handoff-kvu19b-gap-clean-20261104'
def stat_model(a):
 p=Path(a['model']['path']);s=p.stat()
 if any(getattr(s,k)!=v for k,v in a['model']['stat'].items()):raise Refusal('model stat receipt changed: prepare again before grant')
def parse_output(text,kvu,own,steps):
 lines=[l for l in text.splitlines() if l.startswith('own=')]
 if len(lines)!=1:raise Refusal('missing/duplicate native summary')
 pattern=rf'own={own} n_act=4 draft=1 first_draft=1 kvu={kvu} ctk=q8_0 n_ctx=\d+ : ([\d.]+) ms/step  ([\d.]+) steps/s  ([\d.]+) tok/s'
 m=re.fullmatch(pattern,lines[0]);
 if not m or float(m[1])<=0:raise Refusal('native recipe differs or invalid timing')
 return {'ms_per_step':float(m[1]),'steps_per_s':float(m[2]),'tokens_per_s':float(m[3]),'n_steps':steps}
def paired_deltas(rows):
 if len(rows)%2:raise Refusal('incomplete pair')
 pairs=[]
 for index in range(0,len(rows),2):
  pair=rows[index:index+2]
  if {r['kvu'] for r in pair}!={0,1}:raise Refusal('duplicate/missing pair arm')
  values={r['kvu']:r['metrics']['ms_per_step'] for r in pair}
  if min(values.values())<=0:raise Refusal('nonpositive paired time')
  pairs.append({'pair':index//2,'unified_ms':values[1],'split_ms':values[0],'unified_over_split_pct':100*(values[1]/values[0]-1)})
 return pairs
def remove_registration(pid,birth,path):
 if not path:return
 p=Path(path)
 if p.is_symlink():raise Refusal('pid registry is a symlink')
 lines=p.read_text().splitlines()
 expected=f'{pid} {birth}'
 matching=[line for line in lines if line.split() and line.split()[0]==str(pid)]
 if matching!=[expected]:raise Refusal('pid registry birth/uniqueness mismatch')
 remaining=[line for line in lines if line!=expected]
 fd,name=tempfile.mkstemp(prefix=p.name+'.cleanup-',dir=p.parent)
 try:
  with os.fdopen(fd,'w') as file:
   file.write(''.join(line+'\n' for line in remaining));file.flush();os.fsync(file.fileno())
  os.replace(name,p)
 finally:Path(name).unlink(missing_ok=True)
def write(p,r):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2)+'\n')
 with open(tmp,'rb') as f:os.fsync(f.fileno())
 os.replace(tmp,p)
def main():
 if os.getenv('FILLER_ID')!=ID or os.getenv('FILLER_NEEDGPU')!='1':raise Refusal('missing row/grant GPU identity')
 qual=os.getenv('FILLER_DRYRUN')=='1';target=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if qual else D/'RESULT.json'
 if target.exists():raise Refusal('native target exists')
 a=json.loads((D/'assets.json').read_text());stat_model(a)
 grant=os.environ['FILLER_CPUS'];aff=validate_cpu_grant(grant,True) if qual else None
 if not qual:
  # Allocator grants quiet whole host; producer and model use its fixed eight host threads.
  declared=set()
  for t in grant.split(','):
   x,_,y=t.partition('-');declared.update(range(int(x),int(y or x)+1))
  if declared!=set(range(192)) or not set(range(184,192))<=os.sched_getaffinity(0):raise Refusal('full comparison requires whole-host grant and host thread availability')
  os.sched_setaffinity(0,set(range(184,192)));aff={'declared':grant,'affinity':sorted(os.sched_getaffinity(0)),'count':8}
 device=device_identity.discover();run=Path(tempfile.mkdtemp(prefix='qualification-' if qual else 'run-',dir=D))
 result={'schema':'kvu19b-gap.clean.v1','id':ID,'status':'running','qualification':qual,'affinity':aff,'device':device,'rows':[],'scope':'clean same-binary descriptive remeasurement; no profiling or parent closure'}
 own,steps=(128,2048) if qual else (16384,100)
 arms=[1,0] if qual else [v for pair in range(6) for v in ((1,0) if pair%2==0 else (0,1))]
 try:
  for index,kvu in enumerate(arms):
   stop=os.getenv('FILLER_STOPFILE')
   if stop and Path(stop).exists():raise Refusal('STOP')
   if time.time()>float(os.getenv('FILLER_DEADLINE',time.time()+1800))-10:raise Refusal('deadline')
   out=run/f'{index:02d}-{kvu}.stdout';err=run/f'{index:02d}-{kvu}.stderr'
   env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LD_LIBRARY_PATH':str(D/'bin')+':/opt/rocm/lib','GGML_CUDA_FA_SEQ_ROWS':'1','HSA_OVERRIDE_CPU_AFFINITY_DEBUG':'0','OMP_NUM_THREADS':str(aff['count'])}
   argv=[str(D/'bin/p3batch'),a['model']['path'],str(own),'4',str(steps),'1',str(kvu),'q8_0','1']
   with out.open('w') as fo,err.open('w') as fe:
    started_utc=datetime.now(timezone.utc).isoformat();parent=os.getpid();proc=subprocess.Popen(argv,stdout=fo,stderr=fe,env=env,start_new_session=True,preexec_fn=lambda:child_setup(parent));birth=birth_ticks(proc.pid)
    reg=os.getenv('FILLER_PIDFILE')
    if reg:
     with open(reg,'a') as f:f.write(f'{proc.pid} {birth}\n')
    row={'started_utc':started_utc,'index':index,'kvu':kvu,'pid':proc.pid,'birth_ticks':birth,'argv':argv,'samples':[],'stdout':str(out),'stderr':str(err)};result['rows'].append(row)
    try:
     while proc.poll() is None:
      if (stop and Path(stop).exists()) or time.time()>float(os.getenv('FILLER_DEADLINE',time.time()+1800))-5:raise Refusal('STOP/deadline during child')
      try:
       sample=read_kfd(proc.pid,birth,device,D/'bin',a['libraries']);row['samples'].append(sample)
      except (FileNotFoundError,ProcessLookupError):pass
      time.sleep(.05)
     row['rc']=proc.returncode
    finally:
     row['cleanup']=terminate_owned(proc,birth)
     remove_registration(proc.pid,birth,reg)
   if row['rc']!=0:raise Refusal('native child failed')
   # Every selected ggml library must be mapped in two same-PID positive samples.
   expected={n for n in a['libraries'] if n.startswith('libggml')}
   valid=[s for s in row['samples'] if s['own_vram_b']>0 and all(s['mapped_libraries'].get(n) for n in expected)]
   if len(valid)<2:raise Refusal('missing two in-window own-PID positive VRAM + ggml/HIP mapping samples')
   row['completed_utc']=datetime.now(timezone.utc).isoformat()
   row['raw_sha256']={name:hashlib.sha256(Path(row[name]).read_bytes()).hexdigest() for name in ('stdout','stderr')}
   row['metrics']=parse_output(out.read_text(),kvu,own,steps)
   if not qual:
    result['belief_sidecar']=write_child(run,row,a,qualification=False,manifest_sha=hashlib.sha256((D/'runtime.sha256').read_bytes()).hexdigest())
   write(run/'PARTIAL.json',result)
  result['status']='qualified_four_cpu' if qual else 'completed_descriptive'
  if not qual:
   grouped={k:[r['metrics']['ms_per_step'] for r in result['rows'] if r['kvu']==k] for k in (0,1)}
   result['median_ms']={str(k):statistics.median(v) for k,v in grouped.items()}
   result['unified_over_split_pct']=100*(result['median_ms']['1']/result['median_ms']['0']-1)
   result['paired_deltas']=paired_deltas(result['rows'])
   result['within_arm_range_pct']={str(k):100*(max(v)-min(v))/statistics.median(v) for k,v in grouped.items()}
   result['interpretation']='Descriptive six-pair scoped answer. Parent profiling and causal attribution remain open. No formal timing gate.'
  write(run/'NATIVE.json',result);write(target,result);return 0
 except Exception as e:
  result['status']='inconclusive';result['reason']=str(e);write(run/'NATIVE.json',result)
  if not qual:write(target,result)
  print(str(e),file=sys.stderr);return 75
if __name__=='__main__':sys.exit(main())
