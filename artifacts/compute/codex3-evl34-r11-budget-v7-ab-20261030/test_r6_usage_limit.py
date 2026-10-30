import json,unittest
from native_usage import UsageLedger,SSEUsage
from repl_upstream_adapter import REPLUpstream
class UsageTests(unittest.TestCase):
 def test_actual_repl_adapter_accepts_declared_ceiling_and_refuses_excess(self):
  for count in (1024,1025,2048):
   ledger=UsageLedger();body={'choices':[{'message':{'content':'answer'}}],'usage':{'prompt_tokens':17,'completion_tokens':count}}
   upstream=lambda *args:(200,{'content-type':'application/json'},[json.dumps(body).encode()])
   self.assertEqual(REPLUpstream(upstream,ledger)('/v1/chat/completions',{})['usage']['completion_tokens'],count);self.assertEqual(ledger.totals()['completion_tokens'],count)
  ledger=UsageLedger();body={'usage':{'prompt_tokens':1,'completion_tokens':2049}}
  with self.assertRaisesRegex(ValueError,'per-call'):REPLUpstream(lambda *a:(200,{'content-type':'application/json'},[json.dumps(body).encode()]),ledger)('/v1/chat/completions',{})
  self.assertIsNone(ledger.totals())
 def test_sse_usage_accepts_2048_and_refuses_2049(self):
  for count in (2048,2049):
   ledger=UsageLedger();parser=SSEUsage(ledger);parser.feed(('data: '+json.dumps({'usage':{'prompt_tokens':17,'completion_tokens':count}})+'\n\ndata: [DONE]\n\n').encode())
   if count==2048:parser.finish();self.assertEqual(ledger.totals()['completion_tokens'],2048)
   else:
    with self.assertRaisesRegex(ValueError,'per-call'):parser.finish()
if __name__=='__main__':unittest.main()
