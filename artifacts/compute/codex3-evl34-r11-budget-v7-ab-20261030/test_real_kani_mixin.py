import asyncio
from kani.engines.openai import OpenAIEngine
from redel_budget import ReDelBudgetMixin
from budget_guard import BudgetExceeded
class Instrumented(ReDelBudgetMixin,OpenAIEngine):pass
async def fake_predict(self,messages,functions=None,**kw):return kw
async def fake_stream(self,messages,functions=None,**kw):yield kw
async def main():
 oldp,olds=OpenAIEngine.predict,OpenAIEngine.stream
 OpenAIEngine.predict,OpenAIEngine.stream=fake_predict,fake_stream
 try:
  e=Instrumented.__new__(Instrumented);e.init_budget()
  assert (await e.predict([])) == {'max_tokens':1024,'temperature':0,'seed':42}
  assert [v async for v in e.stream([])] == [{'max_tokens':1024,'temperature':0,'seed':42}]
  for _ in range(6): await e.predict([])
  try:await e.predict([])
  except BudgetExceeded:pass
  else:raise AssertionError('exceeded cap')
  print('pinned real Kani class MRO predict/stream intercepts; backend synthetic')
 finally: OpenAIEngine.predict,OpenAIEngine.stream=oldp,olds
asyncio.run(main())
