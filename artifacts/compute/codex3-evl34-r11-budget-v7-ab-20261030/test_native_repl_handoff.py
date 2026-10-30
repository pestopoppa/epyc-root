import json,os,threading,time
from pathlib import Path
import control_driver as d
class Server:
 pid=os.getpid()
 def poll(self):return None
class FakeUpstream:
 def __init__(self,*args):self.local=threading.local()
 def __call__(self,path,body):
  self.local.evidence={'synthetic':True}
  result={'choices':[{'message':{'content':"```python\nprint('fixture')\n```"}}],'usage':{'prompt_tokens':17,'completion_tokens':3}}
  return 200,{'content-type':'application/json'},iter([json.dumps(result).encode()])
def main():
 root=Path('/mnt/micron/codex3-evl34-v6-repl-entry-fixture-20261030');root.mkdir(mode=0o700)
 d.Upstream=FakeUpstream;d.wrap=lambda argv,**kw:(argv,{})
 original_env=d.child_env
 def child_env(path,extra):
  env=original_env(path,extra);env['PYTHONPATH']='/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r11-budget-v6-20261030:'+env['PYTHONPATH'];return env
 d.child_env=child_env;d.headroom=lambda _:True;d.END=time.monotonic()+50;d.PORT=19999
 result=d.run_arm('production_repl','fixture question only',root,Server(),1,0,milestone=True)
 assert result['status']=='partial_entry_repl',result
 assert result['server_usage']=={'prompt_tokens':17,'completion_tokens':3},result['server_usage']
 assert len(result['request_evidence'])==1
 assert not list(root.rglob('broker-error-*.json'))
 print('actual REPL child and socket broker: first response delivered, quiesced, owned child drained, no broker error')
if __name__=='__main__':main()
