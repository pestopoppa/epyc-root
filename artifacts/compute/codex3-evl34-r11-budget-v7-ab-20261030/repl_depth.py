"""Task-private depth attribution at production REPL's tracked child entry.

Install only inside the isolated child. This does not observe graph delegation
outside tracked llm_call/llm_batch, and requires completeness proof before use.
"""
import contextvars, functools
DEPTH=contextvars.ContextVar('evl34_depth',default=0)
def install():
 from src.repl_environment import REPLEnvironment
 for name in ('_tracked_llm_call','_tracked_llm_batch'):
  original=getattr(REPLEnvironment,name)
  if getattr(original,'_evl34_wrapped',False):raise RuntimeError('already instrumented')
  def make(original):
   @functools.wraps(original)
   def wrapped(*args,**kwargs):
    depth=DEPTH.get()+1
    if depth>1:raise RuntimeError('depth exceeds predeclaration')
    token=DEPTH.set(depth)
    try:return original(*args,**kwargs)
    finally:DEPTH.reset(token)
   wrapped._evl34_wrapped=True
   return wrapped
  setattr(REPLEnvironment,name,make(original))

class ChildRequestBudget:
 """One instance per flat REPL child; batch members are distinct children."""
 def __init__(self,limit=16):
  if type(limit) is not int or limit<1:raise ValueError('invalid child cap')
  self.limit=limit;self.calls=0
 def reserve(self):
  if self.calls>=self.limit:raise RuntimeError('per-child model call limit exhausted')
  self.calls+=1
