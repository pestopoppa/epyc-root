#!/usr/bin/env python3
import copy, http.client, json, os, subprocess, tempfile, time
from pathlib import Path
from unittest.mock import patch
import capture, pair

plan=json.loads((capture.D/'plan.json').read_bytes()); original=json.loads((capture.D.parent/'dspark-dflash-r2-20261118'/'plan.json').read_bytes())
assert plan['items']==original['items'] and plan['arms']==original['arms'] and plan['model_shards']==original['model_shards'] and plan['draft_model']==original['draft_model']
a=copy.deepcopy(plan['recipes']['cpu_slice']); b=copy.deepcopy(original['recipes']['cpu_slice']); assert a.pop('request_s')==240 and b.pop('request_s')==90 and a==b
capture.verify_files(plan); requests=capture.read_requests(plan); pair.verify_pairs(plan['items'])
bad=copy.deepcopy(plan['items']); bad[1]['request_body']['prompt']+=' altered'
try: pair.verify_pairs(bad); raise AssertionError('accepted altered prompt')
except ValueError: pass
item=plan['items'][1]; recipe=plan['recipes']['cpu_slice']; data=json.loads((capture.D.parent/'dspark-dflash-r2-20261118/out/native/production/dflash2-json-cap7.response.json').read_bytes()); pair.verify_response(data,item,recipe)
bad=copy.deepcopy(data); bad['generation_settings'][pair.CAP_KEY]=0
try: pair.verify_response(bad,item,recipe); raise AssertionError('accepted cap mismatch')
except ValueError: pass
bad=copy.deepcopy(data); bad['timings']['draft_n_accepted']=bad['timings']['draft_n']+1
try: pair.verify_response(bad,item,recipe); raise AssertionError('accepted invalid counters')
except ValueError: pass
class Resp:
 status=200
 def __init__(self,fail): self.fail=fail; self.n=0
 def read1(self,n):
  self.n+=1
  if self.n==1: return b'original partial bytes'
  if self.fail: raise TimeoutError('fixture timeout')
  return b''
class Conn:
 fail=False
 def __init__(self,*a,**kw): pass
 def request(self,*a,**kw): pass
 def getresponse(self): return Resp(self.fail)
 def close(self): pass
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'partial';
 with patch.object(http.client,'HTTPConnection',Conn):
  assert capture.request('/',1,b'{}',partial_path=p)==(200,b'original partial bytes') and not p.exists()
  Conn.fail=True
  try: capture.request('/',1,b'{}',partial_path=p); raise AssertionError('accepted timeout')
  except TimeoutError: pass
  assert p.read_bytes()==b'original partial bytes'
 for value,expected in [({'status':'capture-complete'},0),({'status':'capture-failed'},1),({},1)]:
  q=Path(t)/'result.json'; q.write_text(json.dumps(value)); assert subprocess.run(['/usr/bin/python3',str(capture.D/'complete_predicate.py'),str(q)]).returncode==expected
class Child:
 pid=12345; returncode=None
 def poll(self): return self.returncode
 def terminate(self): self.returncode=0
 def wait(self,timeout): return self.returncode
child=Child()
with tempfile.TemporaryDirectory() as t, patch.dict(os.environ,{'FILLER_ID':'offline-control'}), patch.object(capture,'listeners',return_value=set()), patch.object(capture.subprocess,'Popen',return_value=child), patch.object(capture,'owns_listener',return_value=True), patch.object(capture,'request',side_effect=RuntimeError('injected failure')):
 try: capture.capture_arm('production',plan['arms']['production'],recipe,plan['items'],requests,Path(t),[0],time.time()+30,Path(t)/'STOP'); raise AssertionError('accepted injected failure')
 except RuntimeError as exc: assert str(exc)=='injected failure'
 cleanup=json.loads((Path(t)/'production/cleanup.json').read_text()); assert cleanup=={'pid':12345,'dead':True,'port_closed':True,'exit_status':0}
print('PASS: original identities and requests, preflight, pair/counter refusals, raw partial, cleanup, completion predicate')
