"""Sample only an explicitly owned server PID while an adapter request is in flight."""
import hashlib,os,subprocess,time
from pathlib import Path

def start_ticks(pid):
 s=Path(f'/proc/{pid}/stat').read_text();return s[s.rfind(')')+2:].split()[19]

def identity(pid):
 base=Path(f'/proc/{pid}');exe=os.readlink(base/'exe');args=(base/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip();maps=(base/'maps').read_text();libs=sorted({line.split()[-1] for line in maps.splitlines() if 'libggml' in line and line.split()[-1].startswith('/')})
 raw=(base/'environ').read_bytes().split(b'\0');selected={}
 for entry in raw:
  k,sep,v=entry.partition(b'=')
  if sep and k in (b'LLAMA_LSA_SCREEN',b'LLAMA_LSA_WORKER',b'LLAMA_LSA_MAP',b'LSA_THREADS'):selected[k.decode()]=v.decode(errors='replace')
 return {'pid':pid,'start_ticks':start_ticks(pid),'exe':exe,'argv':args,'lsa_environment':selected,'mapped_ggml':[{ 'path':p,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in libs if Path(p).is_file()]}

def sample(pid):
 base=Path(f'/sys/class/kfd/kfd/proc/{pid}');vram={}
 if base.exists():
  for p in base.glob('vram_*'):
   try:vram[p.name]=int(p.read_text().strip())
   except (OSError,ValueError):vram[p.name]=None
 return {'monotonic_ns':time.monotonic_ns(),'kfd_present':base.exists(),'vram_bytes':vram}

def run(argv,request,timeout,pid,expected_exe,expected_ticks,device,build_root,arm,map_sha):
 before=identity(pid)
 if os.path.realpath(before['exe'])!=os.path.realpath(expected_exe) or before['start_ticks']!=str(expected_ticks):raise ValueError('running server executable or PID start mismatch')
 mode={'dense':'','all_keys':'all','pca':'pca','distilled':'distilled','window':'positional'}.get(arm)
 if mode is None or before['lsa_environment'].get('LLAMA_LSA_SCREEN','')!=mode:raise ValueError('running process LSA mode differs from requested arm')
 if arm in ('pca','distilled'):
  map_path=Path(before['lsa_environment'].get('LLAMA_LSA_MAP',''))
  if not map_path.is_file() or hashlib.sha256(map_path.read_bytes()).hexdigest()!=map_sha:raise ValueError('running process projection map mismatch')
 link=subprocess.run(['ldd',expected_exe],text=True,capture_output=True,timeout=10)
 proc=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 # communicate in a helper thread so pipes cannot deadlock while monitoring.
 import threading
 result={}
 def communicate():
  try:result['out'],result['err']=proc.communicate(request,timeout=timeout)
  except subprocess.TimeoutExpired:
   proc.kill();result['out'],result['err']=proc.communicate();result['timeout']=True
 t=threading.Thread(target=communicate);t.start();samples=[]
 while t.is_alive():
  samples.append(sample(pid));t.join(timeout=1)
 t.join()
 try:after=identity(pid)
 except (OSError,ValueError):after=None
 witness={'before':before,'after':after,'ldd_rc':link.returncode,'ldd_stdout':link.stdout,'ldd_stderr':link.stderr,'samples':samples,'sample_window':'while adapter request in flight','gpu_residency_observed':any(s['kfd_present'] and any(isinstance(v,int) and v>0 for v in s['vram_bytes'].values()) for s in samples)}
 errors=[]
 if not after or after['start_ticks']!=before['start_ticks'] or os.path.realpath(after['exe'])!=os.path.realpath(expected_exe):errors.append('server PID changed or disappeared')
 if not after or not after['mapped_ggml'] or link.returncode!=0:errors.append('missing ggml mappings or failed ldd')
 if after and any(os.path.commonpath((os.path.realpath(x['path']),os.path.realpath(build_root)))!=os.path.realpath(build_root) for x in after['mapped_ggml']):errors.append('mapped ggml library outside candidate build root')
 if device.lower().startswith(('gpu','mi210')) and not witness['gpu_residency_observed']:errors.append('no in-window nonzero own-PID KFD VRAM sample')
 witness['errors']=errors
 return result,proc.returncode,witness
