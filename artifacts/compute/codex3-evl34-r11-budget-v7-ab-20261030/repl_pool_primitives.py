"""Experimental multi-channel version of the private REPL transport."""
from repl_broker_primitives import BrokerPrimitives
from repl_depth import DEPTH,ChildRequestBudget
from broker_protocol import send,recv
class PoolPrimitives(BrokerPrimitives):
 def __init__(self,pool,model):
  super().__init__(None,model);self.pool=pool
 def _real_call(self,prompt,role,n_tokens=-1,stop_sequences=None,json_schema=None,grammar=None,temperature=None,seed=None,top_p=None,top_k=None,n_probs=None,post_sampling_probs=False,on_chunk=None):
  if on_chunk is not None or any(x is not None for x in (json_schema,grammar,top_p,top_k,n_probs)) or post_sampling_probs:raise ValueError('unsupported native request option')
  if temperature not in (None,0) or seed not in (None,42):raise ValueError('sampling conflict')
  if DEPTH.get()==1:ChildRequestBudget(16).reserve()
  body={'model':self._evl34_model,'temperature':0,'seed':42,'max_tokens':4096,'messages':[{'role':'user','content':prompt}]}
  if stop_sequences:body['stop']=stop_sequences
  sock=self.pool.take()
  try:
   send(sock,{'path':'/v1/chat/completions','body':body,'depth':DEPTH.get()})
   msg=recv(sock);text=msg['response']['choices'][0]['message']['content']
   if not isinstance(text,str):raise ValueError('non-text response')
  except BaseException:
   sock.close();raise
  else:self.pool.put(sock);return text
