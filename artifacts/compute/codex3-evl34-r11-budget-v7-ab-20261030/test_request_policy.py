from request_policy import RequestPolicy
from budget_guard import BudgetExceeded
b={'model':'pinned','temperature':0,'seed':42,'max_tokens':2048,'messages':[{'role':'user','content':'fixture'}]}
p=RequestPolicy('pinned')
for k,v in [('model','other'),('temperature',.5),('seed',1),('max_tokens',2049),('stream',True),('n',2),('max_completion_tokens',8)]:
 altered=b|{k:v}
 try:p.admit('/v1/chat/completions',altered)
 except (ValueError,BudgetExceeded):pass
 else:raise AssertionError(k)
assert p.budget.reserved==0
for i in range(32): assert p.admit('/v1/chat/completions',b)['reserved']==(i+1)*2048
try:p.admit('/v1/chat/completions',b)
except BudgetExceeded:pass
else:raise AssertionError('aggregate ceiling')
print('request policy: mismatches refused before reservation; 32 calls admitted, 33rd refused')
