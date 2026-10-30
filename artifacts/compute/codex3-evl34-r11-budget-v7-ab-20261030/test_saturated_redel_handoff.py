import json,os,threading,time
from pathlib import Path
import control_driver as d
class Server:
 pid=os.getpid()
 def poll(self):return None
class FakeUpstream:
 def __init__(self,*args):self.local=threading.local();self.lock=threading.Lock();self.root=0;self.child=0;self.both=threading.Barrier(3,timeout=10)
 def __call__(self,path,body):
  self.local.evidence={'synthetic':True}
  if body.get('stream'):
   with self.lock:self.child+=1;ordinal=self.child
   self.both.wait()
   if ordinal>1:time.sleep(10)
   common={'id':'fixture','created':0,'model':'pinned','object':'chat.completion.chunk'}
   chunks=[common|{'choices':[{'index':0,'delta':{'role':'assistant','content':'fixture helper answer'},'finish_reason':None}]},common|{'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]},common|{'choices':[],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}]
   return 200,{'content-type':'text/event-stream'},iter([(''.join('data: '+json.dumps(x)+'\n\n' for x in chunks)+'data: [DONE]\n\n').encode()])
  with self.lock:self.root+=1;ordinal=self.root
  if ordinal==1:msg={'role':'assistant','content':None,'tool_calls':[{'id':f'call{i}','type':'function','function':{'name':'delegate','arguments':json.dumps({'instructions':f'fixture helper {i}'})}} for i in (1,2,3)]};finish='tool_calls'
  elif ordinal==2:msg={'role':'assistant','content':None,'tool_calls':[{'id':'wait','type':'function','function':{'name':'wait','arguments':json.dumps({'until':'next'})}}]};finish='tool_calls'
  else:msg={'role':'assistant','content':'fixture final'};finish='stop'
  result={'id':'fixture','created':0,'model':'pinned','object':'chat.completion','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}
  return 200,{'content-type':'application/json'},iter([json.dumps(result).encode()])
def main():
 root=Path('/mnt/micron/codex3-evl34-v6-saturation-audit-20261030');root.mkdir(mode=0o700)
 d.Upstream=FakeUpstream;d.wrap=lambda argv,**kw:(argv,{})
 original_env=d.child_env
 def child_env(path,extra):
  env=original_env(path,extra);env['PYTHONPATH']='/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r11-budget-v6-20261030:'+env['PYTHONPATH'];return env
 d.child_env=child_env;d.headroom=lambda _:True;d.END=time.monotonic()+50;d.PORT=19999
 try:
  result=d.run_arm('redel_delegate_wait','fixture question only',root,Server(),1,0,capture_request=True,milestone=True)
  assert result['status']=='partial_entry_milestone' and len(result.get('request_evidence',[]))>=6,result
  assert not list(root.rglob('broker-error-*.json'))
  print('three saturated child streams drained via dedicated control channel',flush=True)
 except Exception as exc:
  print('FAIL',type(exc).__name__,str(exc),flush=True)
  for p in root.rglob('broker-error-*.json'):print('BROKER',p.read_text(),flush=True)
  raise
if __name__=='__main__':main()
