from native_usage import UsageLedger
from repl_upstream_adapter import REPLUpstream
ledger=UsageLedger()
def upstream(path,body):return 200,{'content-type':'application/json'},[b'{"choices":[],"usage":{"prompt_tokens":7,"completion_tokens":3}}']
a=REPLUpstream(upstream,ledger);assert a('/v1/chat/completions',{})['choices']==[] and ledger.totals()=={'prompt_tokens':7,'completion_tokens':3}
def bad(path,body):return 500,{},[]
try:REPLUpstream(bad,ledger)('/v1/chat/completions',{})
except ValueError:pass
else:raise AssertionError('bad status accepted')
assert ledger.totals() is None
print('REPL captured-upstream native usage and missing/failure propagation passed')
