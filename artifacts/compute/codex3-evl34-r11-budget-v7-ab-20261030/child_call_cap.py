"""Prospective child-only cap: explicit failure, no synthetic answer.

Integration sketch: install on ReDelKani.full_round_stream; invoke reserve_child
before the existing shared engine reservation. Root calls remain under the
shared per-arm budget only. Do not use until the amended protocol is sealed.
"""
from contextvars import ContextVar
from budget_guard import BudgetExceeded

_child=ContextVar('evl34_child_call_budget',default=None)

def install(kani_type,limit=16):
 if type(limit) is not int or limit<1:raise ValueError('invalid per-child cap')
 original=kani_type.full_round_stream
 async def bounded(self,*args,**kwargs):
  if self.depth!=1:
   async for item in original(self,*args,**kwargs):yield item
   return
  budget=getattr(self,'_evl34_lifetime_budget',None)
  if budget is None:
   budget={'calls':0,'limit':limit};self._evl34_lifetime_budget=budget
  elif budget['limit']!=limit:raise RuntimeError('child limit changed')
  token=_child.set(budget)
  try:
   async for item in original(self,*args,**kwargs):yield item
  finally:
   try:_child.reset(token)
   except ValueError:
    # Async-generator finalization can run in a different task context; the
    # originating delegated task has already unwound and owns that context.
    pass
 kani_type.full_round_stream=bounded

def reserve_child():
 budget=_child.get()
 if budget is None:return False
 if budget['calls']>=budget['limit']:raise BudgetExceeded('per-child model call limit exhausted')
 budget['calls']+=1
 return True
