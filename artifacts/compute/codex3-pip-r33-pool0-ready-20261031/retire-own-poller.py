from pathlib import Path
import hashlib,json,os,datetime,stat
F=Path('/mnt/raid0/llm/tmp/compute-flags');ident='codex3-pip02-paddle-relocatable-r27-pool0-20261030';pid=3309771;p=Path('/proc')/str(pid);engine=Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r13-20261030/engine/filler_run13.sh');stop=Path('/mnt/raid0/llm/tmp/codex3-filing-pip-dtap-c6-20261031-0230/repair/pool-0/STOP-0');grant=F/'grants'/f'{ident}.grant';statv=p.joinpath('stat').read_text().rsplit(') ',1)[1].split();assert int(statv[19])==154139851;cmd=p.joinpath('cmdline').read_bytes();assert ident.encode() in cmd and str(engine).encode() in cmd and str(stop).encode() in cmd;assert hashlib.sha256(engine.read_bytes()).hexdigest()=='e940173f539fcae2e814ab4022e3b3cb48eff1fc3d3a7ccdb5de898be5168aeb';assert not grant.exists();children=[]
for c in p.joinpath(f'task/{pid}/children').read_text().split():
 cp=Path('/proc')/c
 try:
  a=cp.joinpath('cmdline').read_bytes().split(b'\0');st=cp.joinpath('stat').read_text().rsplit(') ',1)[1].split();assert cp.stat().st_uid==os.getuid() and int(st[1])==pid and a[:2]==[b'sleep',b'45'];children.append(c)
 except FileNotFoundError:continue
assert not stop.exists();fd=os.open(stop,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd);assert not grant.exists()
r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'id':ident,'pid':pid,'birth_ticks':154139851,'stop':str(stop),'engine_sha256':hashlib.sha256(engine.read_bytes()).hexdigest(),'canonical_grant_absent_before_and_after':True,'observed_children':children,'action':'own cooperative STOP; no signals, grants or queue mutation','poller_liveness':'alive; source checks STOP before worker starts; no completion claim'};out=Path('/mnt/raid0/llm/tmp/codex3-pip-pool0-recovery-20261031-0638/OLD-STOP.json');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
