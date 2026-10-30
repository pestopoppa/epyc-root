from budget_guard import Budget, BudgetExceeded
from concurrent.futures import ThreadPoolExecutor
b=Budget(8,2)
with ThreadPoolExecutor(max_workers=8) as x:
 def go(_):
  try: b.reserve(2); return True
  except BudgetExceeded: return False
 results=list(x.map(go,range(8)))
assert sum(results)==4 and b.reserved==8
for value in (0,-1,3,None,True):
 try: Budget(8,2).reserve(value)
 except BudgetExceeded: pass
 else: raise AssertionError(value)
print('budget guard: concurrent aggregate ceiling and malformed requests refused')
