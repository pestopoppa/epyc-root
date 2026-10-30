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
  result={'id':'fixture','created':0,'model':'pinned','object':'chat.completion','choices':[{'index':0,'message':{'role':'assistant','content':'fixture answer with no delegation'},'finish_reason':'stop'}],'usage':{'prompt_tokens':17,'completion_tokens':3,'total_tokens':20}}
  return 200,{'content-type':'application/json'},iter([json.dumps(result).encode()])
def main():
 root=Path('/mnt/micron/codex3-evl34-v6-first-redel-fixture-20261030');root.mkdir(mode=0o700)
 d.Upstream=FakeUpstream;d.wrap=lambda argv,**kw:(argv,{})
 d.headroom=lambda _:True;d.END=time.monotonic()+50;d.PORT=19999
 result=d.run_arm('redel_delegate_wait','fixture question only',root,Server(),1,0,capture_request=True,milestone=True)
 assert result['status']=='partial_entry_redel',result
 assert result['server_usage']=={'prompt_tokens':17,'completion_tokens':3}
 assert len(result['request_evidence'])==1
 assert json.loads((root/'redel_delegate_wait/entry-quiesce.json').read_text())['all_inflight_drained'] is True
 assert not list(root.rglob('broker-error-*.json'))
 print('actual ReDel first model response, no delegation, quiescent writer and child drain passed')
if __name__=='__main__':main()
