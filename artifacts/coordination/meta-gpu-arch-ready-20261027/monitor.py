#!/usr/bin/env python3
"""Narrow qwen4exp synthetic architecture diagnostic; never a full C5 gate."""
import datetime, hashlib, json, os, pathlib, re, subprocess, sys, time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet')
B=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep')
ID='codex-ni-meta-gpu-arch-20261027'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def holds(): return list(Path('/mnt/raid0/llm/tmp').glob('HOLD_*'))+list(Path('/mnt/raid0/llm/tmp/compute-flags').rglob('HOLD_*'))
def guard():
 if os.environ.get('FILLER_ID')!=ID or os.environ.get('FILLER_CPUS')!='184-191' or os.environ.get('FILLER_NEEDGPU')!='1' or os.sched_getaffinity(0)!=set(range(184,192)): raise ValueError('affinity or job identity')
 g=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant')
 if g.is_symlink() or not g.is_file(): raise ValueError('grant absent')
 fields=dict(x.split('=',1) for x in g.read_text().split())
 if set(fields)!={'regions','start','end'} or fields['regions']!='mi210_0,184-191': raise ValueError('grant shape')
 start,end=(datetime.datetime.fromisoformat(fields[x].replace('Z','+00:00')).timestamp() for x in ('start','end'))
 if not start<=time.time()<int(os.environ['FILLER_DEADLINE'])<end or int(os.environ['FILLER_END'])!=int(end): raise ValueError('grant window')
 if os.environ.get('FILLER_STOPFILE')!=str(D/'STOP') or os.path.lexists(D/'STOP') or holds(): raise ValueError('stop/hold')
 if os.environ.get('LD_PRELOAD') or os.environ.get('LD_AUDIT'): raise ValueError('injected library')
 if os.statvfs(D).f_bavail*os.statvfs(D).f_frsize < 151*1024**3: raise ValueError('disk floor')
 pid=os.getppid(); found=False
 while pid>1:
  p=Path('/proc',str(pid)); cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ')
  if b'filler_run12.sh' in cmd:
   for fd in (p/'fd').iterdir():
    try:
     if os.readlink(fd)=='/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock' and 'FLOCK' in (p/'fdinfo'/fd.name).read_text(): found=True
    except OSError: pass
  pid=int(next(x.split()[1] for x in (p/'status').read_text().splitlines() if x.startswith('PPid:')))
 if not found: raise ValueError('own engine ancestor GPU lock absent')
def identity(pci,drm,topology):
 devices=[p for p in Path(drm).glob('card[0-9]*') if (p/'device').resolve().name.lower()==pci.lower()]
 if len(devices)!=1: raise ValueError('PCI DRM mapping not unique')
 domain,bus,slot=pci.split(':'); device,function=slot.split('.')
 loc=(int(bus,16)<<8)|(int(device,16)<<3)|int(function,16); matches=[]
 for node in Path(topology).iterdir():
  vals=dict(x.split() for x in (node/'properties').read_text().splitlines())
  if int(vals['domain'])==int(domain,16) and int(vals['location_id'])==loc:
   gid=int((node/'gpu_id').read_text())
   if gid: matches.append(gid)
 if len(matches)!=1: raise ValueError('PCI KFD mapping not unique')
 return devices[0],matches[0]
def validate(rc,text,positive):
 plain=re.sub(r'\x1b\[[0-9;]*m','',text)
 rows=[x.split('|') for x in plain.splitlines() if re.search(r'\|\s*qwen4exp\s*\|\s*Meta\s*\|',x)]
 if rc!=0 or positive<2 or len(rows)!=1: raise ValueError('fixture rc, live residency or Meta row count')
 row=[x.strip() for x in rows[0]]
 if row[3]!='MoE' or not re.match(r'^OK\b',row[4]) or row[5]!='SKIP': raise ValueError('Meta MoE NMSE or expected roundtrip status')
 return {'fixture_process_rc':rc,'meta_moe_nmse':'OK','meta_roundtrip':'SKIP (tensor split fixture limitation)','positive_device_samples':positive}
def emit_native(carrier,out,fields):
 return carrier.write_belief_measurements(out,run_id=ID,producer=sha(Path(__file__)),results_path=out/"results.json",records=[{"record_kind":"meta_qwen4exp_native","fields":fields}])
def main():
 guard(); out=D/'run'; out.mkdir(exist_ok=False)
 env=os.environ.copy(); env.update(LD_LIBRARY_PATH=str(B/'buildhip/bin')+':/opt/rocm/lib',HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0',OMP_NUM_THREADS='8')
 pci=subprocess.check_output([str(D/'hip-pci')],env=env,text=True,timeout=20).strip().lower(); card,gid=identity(pci,'/sys/class/drm','/sys/class/kfd/kfd/topology/nodes')
 subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',str(B/'buildhip/bin/test-llama-archs'),str(B/'buildhip/bin')],env=env,stdout=(out/'linkage.log').open('w'),stderr=subprocess.STDOUT,check=True)
 cmd=[str(B/'buildhip/bin/test-llama-archs'),'--arch','qwen4exp','--seed','42']; started=time.time_ns()
 with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr,(out/'residency.jsonl').open('w',buffering=1) as trace:
  p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=env); positive=0
  try:
   birth=Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
   while p.poll() is None:
    guard(); proc=Path('/sys/class/kfd/kfd/proc',str(p.pid)); v=proc/('vram_'+str(gid))
    try: n=int(v.read_text())
    except (OSError,ValueError): n=0
    current_birth=Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
    if current_birth != birth: raise ValueError('child birth identity changed')
    trace.write(json.dumps({'time_ns':time.time_ns(),'pid':p.pid,'start_ticks':birth,'kfd_gpu_id':gid,'vram_bytes':n,'pid_in_kfd':proc.exists()})+'\n')
    if proc.exists() and n>0: positive+=1
    time.sleep(.05)
   rc=p.wait()
  finally:
   if p.poll() is None:
    p.terminate()
    try: p.wait(timeout=5)
    except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=5)
   if p.poll() is None: raise ValueError('owned child not reaped')
 gates=validate(rc,(out/'stdout').read_text(errors='replace'),positive)
 receipt={'schema':'epyc.model_free_backend_correctness.v1','scope':'qwen4exp synthetic Meta diagnostic only','source_commit':'520ad4f55d805a544862be88d652ec68fcd194ab','candidate_base':'c72ec82f5417bb2937310326120f149b665e8400','argv':cmd,'seed':42,'pid':p.pid,'start_ticks':birth,'start_ns':started,'end_ns':time.time_ns(),'reaped':True,'hip_ordinal_0_pci':pci,'drm_card':str(card),'kfd_gpu_id':gid,'gates':gates,'binding_sha256':sha(D/'actual-bindings.sha256'),'source_seal_sha256':sha(D/'SOURCES.sha256'),'raw_sha256':{x:sha(out/x) for x in ('stdout','stderr','residency.jsonl','linkage.log')},'full_c5_gate':'OPEN','model_quality_claim':False}
 (out/'results.json').write_text(json.dumps(receipt,sort_keys=True)+'\n')
 # Use the already-registered speech/kernel gate carrier; its extension must be applied
 # to main and the planning canary approved before the owner may run this packet.
 root=Path('/mnt/raid0/llm/views/epyc-root-main')
 if root.resolve(strict=True)!=root or 'installed-root='+str(root) not in (D/'BK-ENROLLMENT-APPLIED.txt').read_text().splitlines(): raise ValueError('owner installed-root mismatch')
 adapter=root/'scripts/vidya/adapters/speech_ggml_optest.py'
 if sha(adapter)!=sha(D/'adapter-reviewed.py'): raise ValueError('approved adapter not installed')
 sys.path.insert(0,str(root/'scripts/vidya'))
 from adapters import speech_ggml_optest as carrier
 if Path(carrier.__file__).resolve()!=adapter.resolve(): raise ValueError('module loaded outside enrolled root')
 fields={'backend':'ROCm0','device_arch':'gfx90a','op':'qwen4exp-meta-moe-nmse','binary_sha256':sha(B/'buildhip/bin/test-llama-archs'),'source_seal_sha256':sha(D/'SOURCES.sha256'),'binding_sha256':sha(D/'actual-bindings.sha256'),'residency_proof':str(out/'residency.jsonl'),'positive_device_samples':positive,'suite_case_count':1,'n_failed':0,'tree':{'repo':'llama.cpp','branch':'codex/meta-host-view-fix-20261027','commit':'520ad4f55d805a544862be88d652ec68fcd194ab'}}
 emit_native(carrier,out,fields)
if __name__=='__main__':
 try: main()
 except Exception as e: print('REFUSED:',e,file=sys.stderr); sys.exit(1)
