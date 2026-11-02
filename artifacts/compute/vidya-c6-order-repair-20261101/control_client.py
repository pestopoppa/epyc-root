#!/usr/bin/env python3
"""Call original ab_probe.main with request lifecycle witness; payload/body unchanged."""
import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]);port=int(sys.argv[2]);out.mkdir(exist_ok=True)
p=HERE/'original/ab_probe.py';spec=importlib.util.spec_from_file_location('original_ab_probe',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
original=mod.post;counter=0

def traced_post(port_,path,body,timeout=mod.HTTP_TIMEOUT_S):
 global counter
 counter+=1
 payload=json.dumps(body,sort_keys=True).encode()
 row={'schema':'c6.gpu27b_control_request.v1','sequence':counter,'pid':os.getpid(),'port':port_,'path':path,'payload_sha256':hashlib.sha256(payload).hexdigest(),'started_at':time.time(),'status':'ACTIVE'}
 active=out/'REQUEST-ACTIVE.json';active.write_text(json.dumps(row,sort_keys=True)+'\n')
 try:
  response=original(port_,path,body,timeout)
  row.update(status='COMPLETE',finished_at=time.time())
  return response
 finally:
  (out/f'REQUEST-{counter:02d}.json').write_text(json.dumps(row,sort_keys=True)+'\n')
  active.unlink(missing_ok=True)
mod.post=traced_post
sys.argv=[str(p),'probe','mtp','--port',str(port),'--out',str(out/'probe.json'),'--identity-tokens','16','--probs-tokens','4','--pp-items','8','--pp-reps','0','--tg-n','16','--tg-reps','0']
sys.exit(mod.main())
