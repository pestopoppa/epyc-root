#!/usr/bin/env python3
"""One anchored R7 normal + STOP qualification; never publishes or grants."""
import datetime,fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3');F=Path('/mnt/raid0/llm/tmp/compute-flags')
LAUNCH='b717421f7205e92406671aefb887ee7f2ab37b5c6c846322c4c9d60171bc0726';SOURCE='96ca5e50911a1dc0838ecef538986904e0ff077d741f40e0b5100f7083855dee'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def anchor():return sha(D/'launch.sh')==LAUNCH and sha(D/'SOURCES.sha256')==SOURCE
def emit(kind,obj):
 p=D/('QUALIFIER-'+kind+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');os.replace(tmp,p)
 if kind in ('QUALIFIED','HALT','EXPIRED'):(D/('QUALIFIER-'+kind+'.flag')).touch()
def quiet():
 now=time.time();rows=(F/'FILLERS.md').read_text().splitlines()
 for p in (F/'grants').glob('*.grant'):
  try:
   fields=dict(x.split('=',1) for x in p.read_text().split());start=datetime.datetime.fromisoformat(fields['start'].replace('Z','+00:00')).timestamp();end=datetime.datetime.fromisoformat(fields['end'].replace('Z','+00:00')).timestamp()
   if end<=now or start>=now+300:continue
   matching=[line for line in rows if line.startswith('| '+p.stem+' |')]
   if len(matching)!=1 or 'mi210_0' in fields['regions'].split(',') or 'block-timing' in matching[0]:return False
  except (OSError,ValueError,KeyError):return False
 return True
def supervisor(log):
 for line in reversed(log.read_text(errors='replace').splitlines()):
  try:
   value=json.loads(line)
   if value.get('schema')=='kpf181-r7-smoke-supervisor/v1':return value
  except (ValueError,AttributeError):pass
 return None

def attempt(mode,n):
 tag=mode+str(n);out=D/('control-'+tag);log=D/('QUALIFIER-'+tag+'.log')
 if out.exists() or log.exists():raise RuntimeError('control attempt identity already exists')
 with log.open('w') as f:
  p=subprocess.Popen(['/bin/bash',str(D/'launch.sh'),'--smoke',tag],stdout=f,stderr=subprocess.STDOUT)
  touched=False
  while p.poll() is None:
   if mode=='stop' and not touched and list((out/'done').glob('*.started')):
    (out/'STOP').touch();touched=True
   time.sleep(.05)
  rc=p.returncode
 text=log.read_text(errors='replace');sup=supervisor(log)
 if not out.exists() and rc in (75,124) and ('timeout' in text.lower() or 'could not acquire' in text.lower()):return 'retry',{'tag':tag,'rc':rc,'log':str(log),'native_started':False}
 if not anchor():raise RuntimeError('launcher or source anchor changed')
 if sup is None or sup.get('failure') is not None or not sup.get('children_drained') or sup.get('elapsed_s',999)>300:raise RuntimeError('missing safe supervisor completion')
 if mode=='stop':
  pp=out/'PARTIAL.json'
  if rc!=75 or not touched or not pp.is_file() or not json.loads(pp.read_text()).get('partial'):raise RuntimeError('STOP partial/drain proof absent')
  return 'pass',{'tag':tag,'rc':rc,'log':str(log),'partial':str(pp),'supervisor':sup}
 if rc!=0:raise RuntimeError('normal native control failed rc='+str(rc))
 consumer=out/'CONTROL-RESULT.json'
 if not consumer.is_file():raise RuntimeError('same native log consumer did not write its result')
 consumed=json.loads(consumer.read_text())
 if consumed.get('active_fork_control',{}).get('status')!='observed' or not consumed.get('comparator',{}).get('target_parameters_match'):raise RuntimeError('native log consumer did not validate active fork and comparator')
 files=list((out/'records').glob('*.json'));records=[json.loads(p.read_text()) for p in files]
 if len(records)!=4:raise RuntimeError('expected four actual native A records')
 for r in records:
  v=r.get('residency',{});w=v.get('vram') or {}
  if not v.get('hip_mapped') or not (v.get('linkage') or {}).get('pass') or w.get('own_vram_nonzero_samples',0)<2 or w.get('kfd_process_count_max',0)<1 or w.get('own_vram_peak_gib',999)>48 or w.get('abort') or not (v.get('stop') or {}).get('verified_dead'):raise RuntimeError('HIP/VRAM/linkage/drain evidence incomplete')
 siblings=[c for r in records if r.get('arm')=='A_ckpt' for c in r.get('cells',[]) if c.get('role')=='sibling']
 if len(siblings)!=1:raise RuntimeError('real fork sibling missing')
 child=siblings[0];active=child.get('active_slot_evidence') or {}
 if (not isinstance(child.get('n_fork_tokens'),int) or child['n_fork_tokens']<=0 or active.get('status')!='observed'
     or active.get('n_fork_tokens')!=child['n_fork_tokens'] or active.get('matched_active_samples',0)<1
     or not isinstance(active.get('final_task_id'),int) or active.get('final_slot_id')!=child.get('slot')
     or not Path(active.get('path','/nonexistent')).is_file() or sha(Path(active['path']))!=active.get('sha256')):
  raise RuntimeError('matching active fork slot sample absent or inconsistent')
 cmpfiles=list((out/'comparator'/'records').glob('*.json'));cmp=[json.loads(p.read_text()) for p in cmpfiles]
 if len(cmp)!=2 or {r.get('arm') for r in cmp}!={'champion','fork_off'}:raise RuntimeError('actual e332 comparator records missing')
 for r in cmp:
  v=r.get('residency',{});w=v.get('vram') or {}
  if not v.get('hip_mapped') or not (v.get('linkage') or {}).get('pass') or w.get('own_vram_nonzero_samples',0)<2 or w.get('kfd_process_count_max',0)<1 or w.get('own_vram_peak_gib',999)>48 or w.get('abort') or not (v.get('stop') or {}).get('verified_dead'):raise RuntimeError('comparator GPU proof incomplete')
 if {r.get('binary_sha256') for r in cmp}!={'8a3710ad9f0bea535dd9cbd84ff49d8b8af9e2783979077fb109db13a5620b7b','2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635'}:raise RuntimeError('comparator binaries differ from pin')
 def normalized(argv):
  out=[];i=1
  while i<len(argv):
   if argv[i] in ('--slot-save-path','--slot-fork-min-tokens','--port'):i+=2;continue
   out.append(argv[i]);i+=1
  return out
 if normalized(cmp[0].get('argv') or [])!=normalized(cmp[1].get('argv') or []) or cmp[0].get('prompt_set_sha256')!=cmp[1].get('prompt_set_sha256'):raise RuntimeError('comparator target configuration mismatch')
 return 'pass',{'tag':tag,'rc':rc,'log':str(log),'records':[str(p) for p in files],'comparator_records':[str(p) for p in cmpfiles],'consumer_result':str(consumer),'active_sample':active,'supervisor':sup}

if not anchor():emit('HALT',{'reason':'initial hash mismatch'});raise SystemExit(1)
start=time.time();birth=int(Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()[19]);emit('RUNNING',{'pid':os.getpid(),'birth':birth,'started':start,'max_wait_s':7200,'launcher_sha256':LAUNCH,'source_sha256':SOURCE})
proof={}
try:
 for mode in ('normal','stop'):
  for n in range(1,4):
   while time.time()<start+7200:
    if not anchor():raise RuntimeError('source changed during quiet wait')
    try:
     with open(F/'prep-locks/30-31.lock','a') as lk:
      fcntl.flock(lk,fcntl.LOCK_EX|fcntl.LOCK_NB)
      eligible=quiet()
    except BlockingIOError:eligible=False
    if eligible:break
    time.sleep(5)
   else:emit('EXPIRED',{'reason':'no eligible quiet boundary within 2h','proof':proof});raise SystemExit(75)
   state,record=attempt(mode,n)
   if state=='retry':continue
   proof[mode]=record;break
  else:raise RuntimeError('quiet lock attempts exhausted without native launch')
 emit('QUALIFIED',{'launcher_sha256':LAUNCH,'source_sha256':SOURCE,'proof':proof,'note':'small public-control qualification only; target 27B not loaded; no READY implied'})
except Exception as exc:
 emit('HALT',{'error':repr(exc),'proof':proof});raise
