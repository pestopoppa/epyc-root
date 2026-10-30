"""Fail-closed request gate for a future private shared-model broker.

This policy is not a server or a native-engine integration. Each case/arm MUST
own a separate instance, and every model request MUST pass this gate.
"""
from budget_guard import Budget, BudgetExceeded
from threading import Lock

class RequestPolicy:
 def __init__(self, model):
  if not isinstance(model,str) or not model: raise ValueError('model identity required')
  self.model=model; self.budget=Budget(1572864,4096); self._root=0; self._children=0; self._lock=Lock()
 def admit(self, path, body):
  if path != '/v1/chat/completions' or not isinstance(body,dict): raise ValueError('unsupported endpoint')
  if body.get('model') != self.model: raise ValueError('wrong model')
  stream=body.get('stream',False)
  if type(stream) is not bool or (stream and body.get('stream_options') != {'include_usage': True}): raise ValueError('stream usage required')
  if type(body.get('temperature')) not in (int,float) or body['temperature'] != 0 or type(body.get('seed')) is not int or body['seed'] != 42: raise ValueError('sampling mismatch')
  allowed={'model','messages','max_tokens','temperature','seed','n','stream','stop','tools','tool_choice','parallel_tool_calls','stream_options'}
  if set(body)-allowed: raise ValueError('unsupported request parameter')
  if 'max_completion_tokens' in body or 'n_predict' in body: raise ValueError('alternate limit unsupported')
  if body.get('n',1) != 1: raise ValueError('multiple completions unsupported')
  messages=body.get('messages')
  if not isinstance(messages,list) or not messages: raise ValueError('missing messages')
  if type(body.get('max_tokens')) is not int or body['max_tokens']!=4096: raise ValueError('fixed 4096 output reservation required')
  return self.budget.reserve(body['max_tokens'])

 def admit_repl(self, depth):
  if type(depth) is not int or depth not in (0,1): raise ValueError('missing REPL depth')
  with self._lock:
   if depth==0:
    if self._root>=128: raise BudgetExceeded('root call limit exhausted')
    self._root+=1
   else:
    # Each tracked REPL child makes exactly one request.
    if self._children>=256: raise BudgetExceeded('child call limit exhausted')
    self._children+=1
