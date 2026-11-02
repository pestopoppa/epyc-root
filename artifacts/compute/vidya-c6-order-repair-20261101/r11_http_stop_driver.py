#!/usr/bin/env python3
"""Stop the owned R11 llama-server while original ab_probe has an HTTP request active."""
import json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE/'R11-CUTOFF-05';STOP=HERE/'STOP-r11-cutoff-05';LOG=HERE/'R11-CUTOFF-05.log'
assert not OUT.exists() and not STOP.exists() and not LOG.exists() and set(os.sched_getaffinity(0))=={126,127}

def descendants(root):
 pending=[root];seen=set()
 while pending:
  pid=pending.pop()
  if pid in seen:continue
  seen.add(pid)
  try:tasks=(Path('/proc')/str(pid)/'task').iterdir()
  except FileNotFoundError:continue
  for task in tasks:
   try:pending.extend(int(x) for x in (task/'children').read_text().split())
   except FileNotFoundError:pass
 return seen

def identify(pid):
 p=Path('/proc')/str(pid);s=(p/'stat').read_text().rsplit(') ',1)[1].split()
 return {'pid':pid,'birth':int(s[19]),'ticks':int(s[11])+int(s[12]),'rss':int((p/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE'),'cmd':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')}
def own_tcp_established():
 for name in ('/proc/net/tcp','/proc/net/tcp6'):
  for line in Path(name).read_text().splitlines()[1:]:
   v=line.split()
   if len(v)>3 and v[3]=='01' and ('%04X'%19077) in (v[1].rsplit(':',1)[-1],v[2].rsplit(':',1)[-1]):return True
 return False
with LOG.open('wb') as f:
 parent=subprocess.Popen(['/usr/bin/python3','-B',str(HERE/'supervisor.py'),'280','--','/bin/bash',str(HERE/'frontdoor.sh'),'--cpu-control',str(OUT),str(STOP)],stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'R11_CPUS':'126,127','HIP_VISIBLE_DEVICES':'','ROCR_VISIBLE_DEVICES':'','CUDA_VISIBLE_DEVICES':''})
 witness=[];sent=None;baseline=None;active_baseline=None;deadline=time.monotonic()+30
 while parent.poll() is None and time.monotonic()<deadline:
  for pid in descendants(parent.pid):
   try:
    row=identify(pid)
    if '/bin/llama-server -m /mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/' not in row['cmd']:continue
    if baseline is None:baseline=row
    marker=OUT/'REQUEST-ACTIVE.json'
    if marker.exists():
     req=json.loads(marker.read_text());established=own_tcp_established();witness.append({'server':row,'request':req,'tcp_established':established,'at':time.time()})
     if active_baseline is None:active_baseline=row
     if row['birth']==baseline['birth'] and row['ticks']>active_baseline['ticks'] and req['status']=='ACTIVE' and established:
      STOP.touch();sent=witness[-1];break
   except (FileNotFoundError,json.JSONDecodeError):pass
  if sent:break
  time.sleep(.005)
 try:rc=parent.wait(timeout=15)
 except subprocess.TimeoutExpired:raise RuntimeError('owned supervisor did not drain')
supervisor=json.loads(LOG.read_text().splitlines()[-1]);result=json.loads((OUT/'RESULT.json').read_text()) if (OUT/'RESULT.json').exists() else None
receipt={'schema':'c6.gpu27b_r11_http_active_stop.v1','supervisor_pid':parent.pid,'supervisor_rc':rc,'supervisor':supervisor,'server_baseline':baseline,'active_witness':sent,'samples':witness,'result':result,'gpu_execution':False}
(HERE/'R11-CUTOFF-05-RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
assert sent and rc==75 and supervisor['child_rc']==75 and supervisor['failure'] is None and supervisor['children_drained']
assert result and result['status']=='PARTIAL_STOP' and result['server_dead'] and result['client_dead'] and result['active_at_stop']
print('R11_HTTP_ACTIVE_STOP_PASS')
