"""GDB-inferior Test-6 mapping witnesses; correctness only, not timing."""
import gdb,hashlib,json,os,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvfork/kpf17-integrated-custody-20261104')
B=Path('/mnt/micron/rtg58-integrated-c5-a58b513ba-20261102/bin').resolve()
MODEL=Path('/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf').resolve(strict=True)
ENTRY='_ZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEj'
DECODE='_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUlP13llama_contextiiE_clESA_ii'
RESTORE='_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUliRKS4_IhSaIhEEE_clEiSC_'
EXPECTED={'libllama-common.so.0.0.10448':'72278caa75913cba756aed4cdfa57b7368045cfe98d49019d4122ecfa0b834c5'}
for line in (B.parent/'BINARIES.sha256').read_text().splitlines():
 digest,name=line.split(None,1);EXPECTED[name.lstrip('*')]=digest
REQUIRED={'libggml.so.0.16.0','libggml-base.so.0.16.0','libggml-cpu.so.0.16.0','libllama.so.0.0.10448','libllama-common.so.0.0.10448'}
state={'schema':'epyc.kpf17.in-test-maps.v1','mode':None,'pid':None,'birth_ticks':None,'entries':[],'samples':[],'restore_returns':[],'error':None}
def save():
 p=D/'witness.json';tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n');os.replace(tmp,p)
def birth(pid):return int(Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()[19])
def fail(exc):
 state['error']=type(exc).__name__+': '+str(exc);save();gdb.write('KPF17_WITNESS_ERROR '+state['error']+'\n');return True
class Main(gdb.Breakpoint):
 def stop(self):
  try:
   pid=gdb.selected_inferior().pid
   if pid<=0:raise ValueError('no inferior PID')
   state.update(pid=pid,birth_ticks=birth(pid))
   nspid=[int(x) for x in next(line for line in Path('/proc/%d/status'%pid).read_text().splitlines() if line.startswith('NSpid:')).split()[1:]]
   if nspid!=[pid] or Path('/proc/%d/exe'%pid).resolve(strict=True)!=(B/'test-save-load-state').resolve(strict=True):raise ValueError('inferior PID namespace or executable mismatch')
   state.update(nspid=nspid,exe=str(Path('/proc/%d/exe'%pid).resolve(strict=True)))
   with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(pid)+'\n');f.flush();os.fsync(f.fileno())
   save();self.enabled=False;return False
  except Exception as e:return fail(e)
class Entry(gdb.Breakpoint):
 def stop(self):
  try:
   mode=int(gdb.parse_and_eval('$ecx')) & 0xffffffff
   if mode not in (0,8):raise ValueError('unexpected n_rs_seq at Test 6 entry: '+str(mode))
   if state['pid']!=gdb.selected_inferior().pid or state['birth_ticks']!=birth(state['pid']):raise ValueError('inferior identity changed')
   state['mode']=mode;state['entries'].append({'mode':mode,'at_utc':time.time(),'monotonic_ns':time.monotonic_ns()});save();return False
  except Exception as e:return fail(e)
def capture(point):
 mode=state['mode'];pid=state['pid']
 if mode not in (0,8) or pid!=gdb.selected_inferior().pid or birth(pid)!=state['birth_ticks']:raise ValueError('witness outside captured Test 6')
 if any(x['mode']==mode and x['point']==point for x in state['samples']):return
 libs={};raw_maps=Path('/proc/%d/maps'%pid).read_text()
 if str(MODEL) not in raw_maps:raise ValueError('target model not mapped in Test 6')
 for line in raw_maps.splitlines():
  fields=line.split()
  if len(fields)<6:continue
  path=fields[-1]
  if not path.startswith('/') or not Path(path).name.startswith(('libggml','libllama')):continue
  real=Path(path).resolve(strict=True)
  if real.parent!=B:raise ValueError('mapped project library outside sealed bin: '+path)
  with real.open('rb') as f:
   st=os.fstat(f.fileno());major,minor=fields[3].split(':')
   if (os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)!=(int(major,16),int(minor,16),int(fields[4])):raise ValueError('mapped inode differs from hashed file')
   h=hashlib.sha256()
   for block in iter(lambda:f.read(1048576),b''):h.update(block)
  digest=h.hexdigest()
  if real.name not in EXPECTED or digest!=EXPECTED[real.name]:raise ValueError('unsealed mapped project library '+real.name)
  libs[str(real)]={'sha256':digest,'device_major':os.major(st.st_dev),'device_minor':os.minor(st.st_dev),'inode':st.st_ino}
 if not REQUIRED.issubset({Path(x).name for x in libs}):raise ValueError('required project mapping absent')
 state['samples'].append({'mode':mode,'at_utc':time.time(),'monotonic_ns':time.monotonic_ns(),'pid':pid,'birth_ticks':state['birth_ticks'],'libraries':libs,'maps_text':raw_maps,'maps_sha256':hashlib.sha256(raw_maps.encode()).hexdigest(),'model_path':str(MODEL),'point':point})
 save()
class Decode(gdb.Breakpoint):
 def stop(self):
  try:
   capture('decode_entry')
   if state['mode']==8:self.enabled=False
   return False
  except Exception as e:return fail(e)
class RestoreReturn(gdb.FinishBreakpoint):
 def __init__(self,mode,dest):
  super().__init__(gdb.newest_frame(),internal=True);self.mode=mode;self.dest=dest
 def stop(self):
  try:
   value=int(gdb.parse_and_eval('$al')) & 0xff
   if value not in (0,1):raise ValueError('invalid restore boolean return')
   state['restore_returns'].append({'mode':self.mode,'dest':self.dest,'returned':bool(value),'at_utc':time.time(),'monotonic_ns':time.monotonic_ns()});save();return False
  except Exception as e:return fail(e)
class Restore(gdb.Breakpoint):
 def stop(self):
  try:
   dest=int(gdb.parse_and_eval('$esi')) & 0xffffffff
   if dest not in (1,2):raise ValueError('unexpected restore destination '+str(dest))
   capture('restore_dst_'+str(dest))
   RestoreReturn(state['mode'],dest)
   if state['mode']==8 and dest==2:self.enabled=False
   return False
  except Exception as e:return fail(e)
Main('*main',internal=True);Entry('*'+ENTRY,internal=True);Decode('*'+DECODE,internal=True);Restore('*'+RESTORE,internal=True)
