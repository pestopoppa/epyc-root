"""Read-only captured-server GPU residency witness; never launches inference."""
import re,sys,json,os,time,hashlib
from pathlib import Path
sys.path.insert(0,'/mnt/raid0/llm/tmp/inf34-pf1-nodelete-successor-20261029')
import native_executor
from server_peer import birth
SERVER=Path('/mnt/raid0/llm/kernels/production/gpu/llama-server').resolve()
def initial_witness(pid,expected_birth):
 if birth(pid)!=expected_birth:raise RuntimeError('server identity changed')
 def observe():
  if (Path('/proc')/str(pid)/'exe').resolve(strict=True)!=SERVER:raise RuntimeError('wrong server executable')
  maps=(Path('/proc')/str(pid)/'maps').read_text()
  return maps,native_executor.capture(['rocm-smi','--showpids','--showmeminfo','vram','--showclocks','--showpower','--showtemp','--showuse'],timeout=3),native_executor.capture(['rocm-smi','--showpidgpus',str(pid)],timeout=3)
 (maps,proc,dev),bound=native_executor.bracket_observation(observe,[{'pid':pid,'start_ticks':expected_birth,'verdict':'pass'}])
 raw={'epoch':time.time(),'pid':pid,'birth':expected_birth,'bound':bound,'hip_mapped':'libggml-hip' in maps,'maps_sha256':hashlib.sha256(maps.encode()).hexdigest(),'process_query':proc,'device_query':dev}
 path=os.environ.get('EVL34_GPU_WITNESS_LOG')
 if path:
  with open(path,'a') as f:f.write(json.dumps(raw,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
 if {'pid':pid,'start_ticks':expected_birth} not in bound or proc.get('rc')!=0 or dev.get('rc')!=0 or 'libggml-hip' not in maps:raise RuntimeError('GPU identity/linkage unverified; raw query evidence retained')
 vram=0
 for line in proc['output'].splitlines():
  m=re.match(r'^\s*(\d+)\s+\S+\s+\d+\s+(\d+)\s+\d+\s+\d+\s*$',line)
  if m and int(m.group(1))==pid:vram=int(m.group(2));break
 if not vram or not re.search(rf'PID\s+{pid}\s+is using\s+1\s+DRM device\(s\):\s*\n\s*0\s*(?:\n|$)',dev['output']):raise RuntimeError('server GPU residency/device unverified')
 return {'identity':(pid,expected_birth),'gpu_own_pid_vram_bytes':vram,'hip_mapped':True,'device':0}

# Slow rocm-smi bracketing qualifies the captured server once. Per-request
# samples read the kernel's per-PID per-GPU allocation directly, so the sample
# itself can finish within a short real request rather than after its response.
_cached={}
def device_snapshot():
 nodes=[]
 for node in Path('/sys/class/kfd/kfd/topology/nodes').iterdir():
  gpu_id=int((node/'gpu_id').read_text())
  if not gpu_id:continue
  props=dict(line.split(maxsplit=1) for line in (node/'properties').read_text().splitlines())
  nodes.append((gpu_id,int(props['vendor_id']),int(props['device_id']),int(props['drm_render_minor']),str(node)))
 if len(nodes)!=1 or nodes[0][1]!=0x1002:raise RuntimeError('not a unique AMD KFD device; refuse ambiguous ROCm index')
 return nodes[0]
def witness(pid,expected_birth):
 key=(pid,expected_birth)
 if key not in _cached:
  qualified=initial_witness(pid,expected_birth)
  if qualified.get('device')!=0 or qualified.get('identity')!=key:raise RuntimeError('initial GPU device binding changed')
  _cached[key]=device_snapshot()
 started=time.monotonic_ns();topology=device_snapshot()
 if topology!=_cached[key]:raise RuntimeError('GPU topology changed')
 proc=Path('/proc')/str(pid)
 if proc.stat().st_uid!=os.getuid() or birth(pid)!=expected_birth or (proc/'exe').resolve(strict=True)!=SERVER:raise RuntimeError('captured GPU server identity changed')
 maps=(proc/'maps').read_text()
 if 'libggml-hip' not in maps:raise RuntimeError('HIP library unmapped')
 allocation=Path('/sys/class/kfd/kfd/proc')/str(pid)/('vram_'+str(topology[0]))
 vram=int(allocation.read_text().strip())
 if vram<=0:raise RuntimeError('captured server has no per-device resident VRAM')
 if birth(pid)!=expected_birth:raise RuntimeError('server identity changed across VRAM read')
 ended=time.monotonic_ns()
 record={'epoch':time.time(),'pid':pid,'birth':expected_birth,'kind':'fast-kfd-residency','sample_start_ns':started,'sample_end_ns':ended,'allocation_path':str(allocation),'gpu_topology':topology,'gpu_own_pid_vram_bytes':vram,'hip_mapped':True,'maps_sha256':hashlib.sha256(maps.encode()).hexdigest()}
 path=os.environ.get('EVL34_GPU_WITNESS_LOG')
 if path:
  with open(path,'a') as f:f.write(json.dumps(record,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
 return {'identity':key,'gpu_own_pid_vram_bytes':vram,'hip_mapped':True,'device':0,'kfd_gpu_id':topology[0],'sample_start_ns':started,'sample_end_ns':ended,'sample_duration_ns':ended-started}
