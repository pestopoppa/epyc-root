import asyncio
from redel_budget import ReDelBudgetMixin
from budget_guard import BudgetExceeded
class Fake:
 async def predict(self,messages,functions=None,**kw):return kw
 async def stream(self,messages,functions=None,**kw):yield kw
class Engine(ReDelBudgetMixin,Fake):pass
async def main():
 e=Engine();e.init_budget()
 assert (await e.predict([]))['seed']==42
 assert [x async for x in e.stream([])][0]['max_tokens']==4096
 try:await e.predict([],temperature=.2)
 except ValueError:pass
 else:raise AssertionError('override accepted')
 assert e.evl34_budget.reserved==8192
 for i in range(126):await e.predict([])
 try:await e.predict([])
 except BudgetExceeded:pass
 else:raise AssertionError('exhaustion accepted')
 print('ReDel mixin fixture: predict and stream share enforced budget, overrides refused')
asyncio.run(main())
