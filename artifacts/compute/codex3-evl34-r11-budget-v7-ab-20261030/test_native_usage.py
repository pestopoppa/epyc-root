from native_usage import UsageLedger,SSEUsage
ledger=UsageLedger();ledger.add({'prompt_tokens':10,'completion_tokens':3})
s=SSEUsage(ledger);s.feed(b'data: {"usage":{"prompt_tokens":7,');s.feed(b'"completion_tokens":2}}\n\ndata: [DONE]\n\n');s.finish()
assert ledger.totals()=={'prompt_tokens':17,'completion_tokens':5}
missing=UsageLedger();x=SSEUsage(missing);x.feed(b'data: {"usage":{"prompt_tokens":1,"completion_tokens":2}}\n\n');x.finish();assert missing.totals() is None
bad=UsageLedger();bad.add({'prompt_tokens':True,'completion_tokens':0});assert bad.totals() is None
try:UsageLedger().add({'prompt_tokens':1,'completion_tokens':1025})
except ValueError:pass
else:raise AssertionError('server overrun accepted')
print('server usage sums, fragmented SSE, missing terminal and malformed usage controls passed')
