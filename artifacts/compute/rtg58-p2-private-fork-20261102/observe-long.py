import json,sys,time,threading,urllib.request,urllib.error
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-private-live-20261102'); arm=sys.argv[1]
r=json.loads((p/'diagnostic-request.json').read_text()); r['request_id']='rtg58-kpf26-pair-'+arm+'-20261102'
if arm.startswith('long-'): r['task_root']=(p/'long-scope-path.txt').read_text().strip()
(p/(arm+'-request.json')).write_text(json.dumps(r,indent=2)+'\n')
stop=threading.Event()
def sample():
 with (p/(arm+'-slots.jsonl')).open('w') as f:
  while not stop.is_set():
   t=time.time()
   try:
    with urllib.request.urlopen('http://127.0.0.1:18976/slots',timeout=2) as s: obj={'t':t,'slots':json.load(s)}
   except Exception as e: obj={'t':t,'error':str(e)}
   f.write(json.dumps(obj,separators=(',',':'))+'\n'); f.flush(); stop.wait(.5)
t=threading.Thread(target=sample);t.start()
try:
 req=urllib.request.Request('http://127.0.0.1:18076/chat', data=json.dumps(r).encode(), headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=650) as response: (p/(arm+'-response.json')).write_bytes(response.read())
finally: stop.set(); t.join()
