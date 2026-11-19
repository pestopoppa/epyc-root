import json,os,signal,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,'/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf17-oracle-r3')
from test_gdb_events import DRIVER
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp); (root/'driver.py').write_text(DRIVER)
 env=dict(os.environ,EVENT_DIR='/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf17-oracle-r3',EVENT_OUTPUT=str(root/'events.json'))
 rd,wr=os.pipe(); os.set_inheritable(wr,True)
 src=f'import os,time;os.write({wr},b"R");os.close({wr});time.sleep(30)'
 args=['/usr/bin/gdb','-nx','--batch','-ex','set confirm off','-ex','source '+str(root/'driver.py'),'-ex','python run_test()','-ex','quit','--args',sys.executable,'-c',src]
 p=subprocess.Popen(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,pass_fds=(wr,));os.close(wr)
 try:
  marker=os.read(rd,1)
  if marker != b'R': raise RuntimeError('target did not signal readiness')
  os.kill(p.pid,signal.SIGTERM)
  try:out,_=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   os.kill(p.pid,signal.SIGKILL);out,_=p.communicate(timeout=5);raise
  print('gdb_rc',p.returncode)
  print('events',json.loads((root/'events.json').read_text()))
  print('log',out.decode(errors='replace')[-1200:])
 finally:
  os.close(rd)
  if p.poll() is None: os.kill(p.pid,signal.SIGKILL);p.wait()
