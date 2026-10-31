#!/usr/bin/env python3
"""Source-pinned owner entry. Cohort groups require exclusive original shards."""
import argparse,hashlib,importlib.util,json,os,pathlib,sys,time
H=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/control-stop')
OLD=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029')
BASE=pathlib.Path('/mnt/raid0/llm/tmp/pip02-pipeline-prep-20261029')
E2=pathlib.Path('/mnt/raid0/llm/tmp/rtg28-e2-nodelete-successor-20261029')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
 a=argparse.ArgumentParser();a.add_argument('--first-shard',type=int,required=True);a.add_argument('--regions',required=True);a.add_argument('--port',type=int,required=True);a.add_argument('--smoke',action='store_true');x=a.parse_args()
 if x.first_shard not in (0,3) or x.regions not in ('0-23','24-47','48-71','72-95') or not 1024<=x.port<=65535:raise ValueError('invalid scope')
 if not os.environ['FILLER_ID'].startswith('codex3-pip02-paddle-relocatable-'):raise ValueError('unexpected identity')
 if x.smoke:
  pid=os.getppid();ancestry=[]
  for _ in range(8):
   if pid<=1:break
   proc=pathlib.Path('/proc',str(pid));ancestry+=proc.joinpath('cmdline').read_bytes().split(b'\0');pid=int(proc.joinpath('stat').read_text().rsplit(') ',1)[1].split()[1])
  if b'/mnt/micron/codex3-pip-head-r26-20261030/cpu_r11_split_supervisor.py' not in ancestry:raise RuntimeError('R11 supervisor required')
  shards=[807,836]
 else:
  shards=list(range(x.first_shard,min(x.first_shard+3,5)))
  # An R12 same-group packet must not still own READY or a live grant.
  prior_r12=f'codex3-pip02-paddle-relocatable-r12-g{x.first_shard}-20261030'
  for d in ('/mnt/raid0/llm/tmp/compute-flags/ready','/mnt/raid0/llm/tmp/compute-flags/ready/armed','/mnt/raid0/llm/tmp/compute-flags/grants'):
   if any((pathlib.Path(d)/(prior_r12+suffix)).exists() for suffix in ('.json','.grant')):raise RuntimeError('prior R12 group row or grant still present')
  # R11 same-group owner must be retired before a fresh R12 successor.
  prior_r11=f'codex3-pip02-paddle-relocatable-r11-g{x.first_shard}-20261029'
  for d in ('/mnt/raid0/llm/tmp/compute-flags/ready','/mnt/raid0/llm/tmp/compute-flags/ready/armed','/mnt/raid0/llm/tmp/compute-flags/grants'):
   if any((pathlib.Path(d)/(prior_r11+suffix)).exists() for suffix in ('.json','.grant')):raise RuntimeError('prior R11 group row or grant still present')
  # R9 same-group queue/active ownership must be retired before this successor.
  prior=f'codex3-pip02-paddle-relocatable-r9-g{x.first_shard}-20261029'
  for d in ('/mnt/raid0/llm/tmp/compute-flags/ready','/mnt/raid0/llm/tmp/compute-flags/ready/armed','/mnt/raid0/llm/tmp/compute-flags/grants'):
   if any((pathlib.Path(d)/(prior+suffix)).exists() for suffix in ('.json','.grant')):raise RuntimeError('prior R9 group row or grant still present')
  for n in shards:
   prefix=f'codex3-pip02-paddle-generic-s{n}-20261029'
   for d in ('/mnt/raid0/llm/tmp/compute-flags/ready','/mnt/raid0/llm/tmp/compute-flags/ready/armed','/mnt/raid0/llm/tmp/compute-flags/grants'):
    root=pathlib.Path(d)
    if any(any(root.glob(prefix+suffix)) for suffix in ('.json','.grant')):raise RuntimeError('prior shard row or grant still present')
 snap=load('parallel_source',E2/'source_witness_v2.py').Snapshot(H/'host-source-witness.json','afacfb9ae9e798b75553617fe1ca36c691805005300a5159f3f2a67734e00886',lambda:True)
 pins_path=H/'source-pins.json';pin_sha=hashlib.sha256(pins_path.read_bytes()).hexdigest();pins=json.loads(pins_path.read_bytes())
 private_pins_path=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/source-pins.json');private_pin_sha=hashlib.sha256(private_pins_path.read_bytes()).hexdigest();private_pins=json.loads(private_pins_path.read_bytes())
 def check():
  if hashlib.sha256(private_pins_path.read_bytes()).hexdigest()!=private_pin_sha or any(hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()!=value for name,value in private_pins.items()):raise RuntimeError('private source changed')
  snap.check()
  if hashlib.sha256(pins_path.read_bytes()).hexdigest()!=pin_sha:raise RuntimeError('source pin manifest changed')
  for name,expected in pins.items():
   if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()!=expected:raise RuntimeError('source changed: '+name)
 check();owner=load('parallel_owner',pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/control-stop/parallel_owner.py'))
 def progress():
  roots=[H/'campaigns-fresh'/f'shard-{n:02d}' for n in shards]+[OLD/'campaigns-fresh'/f'shard-{n:02d}' for n in shards]
  return sum(1 for root in roots for f in root.rglob('*') if f.is_file() and (f.name.endswith('.result') or f.name.endswith('.result.json')))
 while True:
  before=progress() if not x.smoke else 0
  rc=owner.run(shards,x.regions,x.port,x.smoke,check);check()
  if x.smoke or rc!=75:break
  if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()+1100>=float(os.environ['FILLER_DEADLINE']):rc=75;break
  if progress()<=before:
   record=owner.LAST_RECORD or {}
   rc=75 if record.get('error') or record.get('reason') else 78
   break
 if rc==0 and not x.smoke:
  fd=os.open(H/f'GROUP-DONE-{x.first_shard}',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  try:os.write(fd,b'complete\n');os.fsync(fd)
  finally:os.close(fd)
 return rc
if __name__=='__main__':raise SystemExit(main())
