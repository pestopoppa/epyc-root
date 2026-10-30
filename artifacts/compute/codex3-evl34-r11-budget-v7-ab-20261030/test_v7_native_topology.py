import asyncio
from unittest.mock import patch
from redel_budget import ReDelBudgetMixin
from budget_guard import BudgetExceeded
from child_call_cap import install
from request_policy import RequestPolicy
from safe_delegate_wait import SafeDelegateWait,DelegateWait
class Engine(ReDelBudgetMixin):pass
class Child:
 def __init__(self,e):self.depth=1;self.engine=e
 async def full_round_stream(self):yield self.engine._evl34_args({})
install(Child,16)
async def test():
 e=Engine();e.init_budget()
 for _ in range(128):e._evl34_args({})
 try:e._evl34_args({})
 except BudgetExceeded:pass
 else:raise AssertionError('root exceeded')
 for _ in range(16):
  c=Child(e)
  for _ in range(16):
   async for _ in c.full_round_stream():pass
  try:
   async for _ in c.full_round_stream():pass
  except BudgetExceeded:pass
  else:raise AssertionError('child lifetime exceeded across rounds')
 assert e.evl34_budget.reserved==384*4096
 try:e.evl34_budget.reserve(4096)
 except BudgetExceeded:pass
 else:raise AssertionError('aggregate exceeded')
 async def fake_create(self,*args,**kwargs):return object()
 scheme=object.__new__(SafeDelegateWait)
 with patch.object(DelegateWait,'create_delegate_kani',fake_create):
  for _ in range(16): await scheme.create_delegate_kani('natural instructions')
  try:await scheme.create_delegate_kani('natural instructions')
  except RuntimeError as exc:assert 'child limit' in str(exc)
  else:raise AssertionError('17th child admitted')
 p=RequestPolicy('pinned')
 body={'model':'pinned','stream':False,'temperature':0,'seed':42,'messages':[{'role':'user','content':'fixture'}],'max_tokens':4096}
 for _ in range(384):p.admit('/v1/chat/completions',body)
 try:p.admit('/v1/chat/completions',body)
 except BudgetExceeded:pass
 else:raise AssertionError('broker aggregate exceeded')
 for bad in (1,4095,4097,None,True):
  try:p.admit('/v1/chat/completions',body|{'max_tokens':bad})
  except ValueError:pass
  else:raise AssertionError('variable reservation allowed')
 for _ in range(128):p.admit_repl(0)
 for _ in range(256):p.admit_repl(1)
 for depth in (0,1):
  try:p.admit_repl(depth)
  except BudgetExceeded:pass
  else:raise AssertionError('REPL topology cap exceeded')
 print('PASS: 128 root plus 16 distinct children x 16 lifetime requests fit 384; all limits refuse overflow; REPL 128 root + 256 child limits enforced')
asyncio.run(test())
