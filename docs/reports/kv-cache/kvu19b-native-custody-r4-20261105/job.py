import hashlib,json,os,subprocess,sys,re,time
from pathlib import Path
from output_path import result_path
D=Path(__file__).resolve().parent
p=result_path(D);out=p.parent;out.mkdir(parents=True,exist_ok=True)
if p.exists(): raise RuntimeError('refuse overwritten result')
env=dict(os.environ,HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0',LD_LIBRARY_PATH='/opt/rocm/lib:'+str(D/'profiler/lib'),ROCM_PATH='/opt/rocm',HIP_PATH='/opt/rocm',HIP_COMPILER='clang',HIP_PLATFORM='amd',HIPCC_USE_PERL_SCRIPT='0',PATH='/opt/rocm/bin:'+os.environ.get('PATH',''))
def run(name,args):
 with (out/(name+'.log')).open('w') as f:
  result=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT)
 if result.returncode: raise RuntimeError(name+' rc='+str(result.returncode))
try:
 exe=out/'clock';run('build',['/opt/rocm/bin/hipcc','--offload-arch=gfx90a','-O2',str(D/'clock.cpp'),'-o',str(exe)])
 run('before',[sys.executable,str(D/'hsa_clock.py'),'--out',str(out/'before.json')])
 with (out/'witness.log').open('w') as f:
  proc=subprocess.Popen([str(D/'profiler/bin/rocprof'),'--timestamp','on','-o',str(out/'dispatch.csv'),str(exe)],env=env,stdout=f,stderr=subprocess.STDOUT)
  observed=[]; limit=time.monotonic()+20
  while proc.poll() is None and time.monotonic()<limit and len(observed)<2:
   m=re.search(r'^IDENTITY pid=(\d+) birth=(\d+) bdf=([0-9a-fA-F:.]+) device=(\d+)$',(out/'witness.log').read_text(),re.M)
   if m:
    pid=int(m[1]); stat=Path(f'/proc/{pid}/stat').read_text(); fields=stat[stat.rfind(')')+2:].split(); actual_exe=os.readlink(f'/proc/{pid}/exe')
    observed.append({'pid':pid,'birth':int(fields[19]),'exe':actual_exe,'observed_monotonic_ns':time.monotonic_ns()})
   time.sleep(0.1)
  rc=proc.wait()
  if rc: raise RuntimeError('witness rc='+str(rc))
  if len(observed)!=2: raise RuntimeError('independent live process observations missing')
  (out/'process_observations.json').write_text(json.dumps(observed,indent=2)+'\n')
 run('after',[sys.executable,str(D/'hsa_clock.py'),'--out',str(out/'after.json')])
 run('verify',[sys.executable,str(D/'verify.py'),str(out)])
 run('verify-process',[sys.executable,str(D/'verify_process.py'),str(out)])
 r={'schema':'kvu19b.native-custody.v1','status':'QUALIFIED_LIMITED','progress':3,'model':None,'scope':'independent live PID/birth observations; profiler GPU ID to PCI mapping UNKNOWN; target conditional on constant offset, interior drift UNKNOWN; no real target alignment, inference or attribution','binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
except Exception as e:
 r={'schema':'kvu19b.native-custody.v1','status':'INVALID','error':str(e),'model':None}
r['files']={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file()}
p.write_text(json.dumps(r,indent=2)+'\n')
raise SystemExit(r['status']!='QUALIFIED_LIMITED')
