"""Private LLMPrimitives transport prototype; NOT an admitted native adapter.

Uses production LLMPrimitives' public llm_call and llm_batch paths and a
single serialized socketpair to a parent broker. Replaces production _real_call
transport; this alters backend/routing semantics and therefore requires review.
The bridge has no independent depth attribution or native usage capture yet.
"""
import threading
from src.llm_primitives import LLMPrimitives
from broker_protocol import send,recv
from repl_depth import DEPTH,ChildRequestBudget
class BrokerPrimitives(LLMPrimitives):
 def __init__(self,sock,model):
  super().__init__(model_server=object(),mock_mode=False,use_worker_pool=False)
  self._evl34_sock=sock;self._evl34_model=model;self._evl34_lock=threading.Lock()
 def _real_call(self,prompt,role,n_tokens=-1,stop_sequences=None,json_schema=None,grammar=None,temperature=None,seed=None,top_p=None,top_k=None,n_probs=None,post_sampling_probs=False,on_chunk=None):
  if on_chunk is not None or any(x is not None for x in (json_schema,grammar,top_p,top_k,n_probs)) or post_sampling_probs:raise ValueError('unsupported native request option')
  if temperature not in (None,0) or seed not in (None,42):raise ValueError('sampling conflict')
  if DEPTH.get()==1:ChildRequestBudget(16).reserve()
  body={'model':self._evl34_model,'temperature':0,'seed':42,'max_tokens':4096,'messages':[{'role':'user','content':prompt}]}
  if stop_sequences:body['stop']=stop_sequences
  with self._evl34_lock:
   send(self._evl34_sock,{'path':'/v1/chat/completions','body':body,'depth':DEPTH.get()})
   msg=recv(self._evl34_sock)
  try:text=msg['response']['choices'][0]['message']['content']
  except (KeyError,IndexError,TypeError):raise ValueError('invalid broker response')
  if not isinstance(text,str):raise ValueError('non-text model response')
  return text
