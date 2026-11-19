#!/usr/bin/env python3
import datetime,hashlib,json,os,pathlib,select,sys,tempfile
D=pathlib.Path('/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor')
terminal=D/'build-terminal.json'
pid=int(sys.argv[1])
try:
 fd=os.pidfd_open(pid)
 select.select([fd],[],[])
 os.close(fd)
except ProcessLookupError:
 pass
if terminal.exists():
 sys.exit(0)
rp=D/'build-receipt.json'
try:
 r=json.loads(rp.read_text())
 assert r['schema']=='kvu19a2.successor-build.v1'
 assert r['source_commit']=='a0d0ae238e714aaab04e973ef4b5a4b7c9917744'
 assert len(r['artifacts'])==9
 for name,want in r['artifacts'].items():
  assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==want
 valid=True; detail='build receipt and nine artifact digests verified'
except (OSError,ValueError,KeyError,AssertionError,TypeError) as e:
 valid=False; detail='missing or invalid build receipt/artifacts: '+str(e)
event={'task':'kvu19-successor-build','state':'success' if valid else 'failure','exit_code':None,'exit_code_note':'unknown: notifier did not reap wrapper','evidence':detail,'notifier':'pidfd kernel wait for captured wrapper PID','wrapper_pid':pid,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build_receipt':str(rp),'log':str(D/'region-build.log')}
# Preserve the pre-existing fallback symlink and never overwrite a wrapper receipt.
target=terminal.resolve() if terminal.is_symlink() else terminal
target.parent.mkdir(parents=True,exist_ok=True)
fd,tmp=tempfile.mkstemp(dir=target.parent,prefix='.kvu19-notifier-')
try:
 with os.fdopen(fd,'w') as f:
  json.dump(event,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
 try: os.link(tmp,target)
 except FileExistsError: pass
finally: os.unlink(tmp)
