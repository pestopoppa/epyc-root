"""Per-case shared ReDel engine reservation mixin; not a launch adapter.

Inherit before OpenAIEngine; same instance must be root and delegate engine.
Calls reserve before the native engine opens a request, including streams.
Native request capture must independently prove no route bypass.
"""
import hashlib,json,os,time
from budget_guard import Budget
from child_call_cap import reserve_child

class ReDelBudgetMixin:
 def init_budget(self,invalid_path=None):
  self.evl34_budget=Budget(1572864,4096);self.evl34_root_budget=Budget(128,1);self.evl34_invalid_path=invalid_path
 def _evl34_validate_completion(self,value):
  message=getattr(value,'message',None)
  for call in getattr(message,'tool_calls',None) or []:
   arguments=call.function.arguments
   try:
    parsed=json.loads(arguments)
    if not isinstance(parsed,dict):raise ValueError('tool arguments must be a JSON object')
   except (ValueError,TypeError) as exc:
    if self.evl34_invalid_path is None:raise RuntimeError('invalid tool output without evidence path') from exc
    raw=str(arguments);record={'reason':'invalid_tool_arguments','tool_name':call.function.name,'call_id':call.id,'arguments_prefix':raw[:16384],'arguments_length':len(raw),'arguments_sha256':hashlib.sha256(raw.encode()).hexdigest(),'error':type(exc).__name__}
    path=self.evl34_invalid_path/('invalid-tool-call-'+hashlib.sha256(str(call.id).encode()).hexdigest()[:16]+'-'+str(time.time_ns())+'.json')
    with open(path,'x',encoding='utf-8') as f:
     json.dump(record,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
    raise ValueError('invalid tool-call argument JSON; raw evidence retained') from exc
  return value
 def _evl34_args(self,kw):
  if not hasattr(self,'evl34_budget'): raise RuntimeError('budget uninitialized')
  for name,value in [('max_tokens',4096),('temperature',0),('seed',42)]:
   if name in kw and kw[name]!=value: raise ValueError('sampling override: '+name)
  if any(k in kw for k in ('max_completion_tokens','n_predict')) or kw.get('n',1)!=1:raise ValueError('unsupported generation option')
  if not reserve_child(): self.evl34_root_budget.reserve(1)
  self.evl34_budget.reserve(4096)
  return kw|{'max_tokens':4096,'temperature':0,'seed':42}
 async def predict(self,messages,functions=None,**kw):
  return self._evl34_validate_completion(await super().predict(messages,functions,**self._evl34_args(kw)))
 async def stream(self,messages,functions=None,**kw):
  args=self._evl34_args(kw)
  async for chunk in super().stream(messages,functions,**args): yield self._evl34_validate_completion(chunk)
