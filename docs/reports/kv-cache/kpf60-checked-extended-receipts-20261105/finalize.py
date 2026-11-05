import hashlib,json,os,sys,time,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent; o=Path(sys.argv[1]).resolve(); smoke=bool(sys.argv[2]); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check_stop():
 if Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE']): raise SystemExit('stop/deadline')
def publish(target, data):
 target.parent.mkdir(exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.'+target.name+'.',dir=target.parent)
 try:
  with os.fdopen(fd,'w') as f: f.write(data)
  check_stop()
  os.link(tmp,target)
 finally: os.unlink(tmp)
check_stop()
if o.parent != (D/'attempts').resolve(): raise SystemExit('invalid attempt')
if not smoke and any(p.exists() for p in (o/'RESULT.json',D/'out/RESULT.json',D/'COMPLETE_ATTEMPT')): raise SystemExit('output already exists')
for name in ('compile','test'):
 r=json.loads((o/(name+'.receipt.json')).read_text())
 if r.get('command_exit')!=0 or r.get('supervisor_exit')!=0 or not r.get('cleanup_verified') or not r.get('child_absent') or r.get('cleanup_killed') or r.get('interrupted') or not r.get('birth_ticks'): raise SystemExit('invalid receipt: '+name)
for name in ('checked_counter.hpp','test_checked_counter.cpp'):
 if sha(o/name)!=sha(D/name): raise SystemExit('source drift')
names=('checked_counter.hpp','test_checked_counter.cpp','test_checked_counter','compile.log','test.log','compile.receipt.json','test.receipt.json')
r={'schema':'kpf60.checked-fixture-receipts.v1','status':'PASS','smoke':smoke,'attempt':str(o),'sha256':{name:sha(o/name) for name in names},'binary_size_bytes':(o/'test_checked_counter').stat().st_size,'scope':'isolated arithmetic only; no native cache, measurement or calibration'}
data=json.dumps(r,sort_keys=True)+'\n'
if smoke: publish(Path(sys.argv[2]),data)
else:
 publish(o/'RESULT.json',data)
 publish(D/'out/RESULT.json',data)
 publish(D/'COMPLETE_ATTEMPT',str(o)+'\n')
