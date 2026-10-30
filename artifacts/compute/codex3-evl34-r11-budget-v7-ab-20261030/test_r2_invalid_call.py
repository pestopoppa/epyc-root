import asyncio,hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from redel_budget import ReDelBudgetMixin

class Fake:
 async def predict(self,messages,functions=None,**kw):return self.response
 async def stream(self,messages,functions=None,**kw):
  yield 'partial'
  yield self.response
class Engine(ReDelBudgetMixin,Fake):pass

def completion(args):return NS(message=NS(tool_calls=[NS(id='call1',function=NS(name='delegate',arguments=args))]))

class MalformedTests(unittest.TestCase):
 def run_case(self,stream):
  async def run(root):
   e=Engine();e.init_budget(root);e.response=completion('{"instructions":"unfinished')
   with self.assertRaisesRegex(ValueError,'raw evidence retained'):
    if stream: [x async for x in e.stream([])]
    else: await e.predict([])
   record=json.loads(next(root.glob('invalid-tool-call-*.json')).read_text());self.assertEqual(record['tool_name'],'delegate');self.assertEqual(record['arguments_sha256'],hashlib.sha256(b'{"instructions":"unfinished').hexdigest());self.assertEqual(e.evl34_budget.reserved,2048)
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:asyncio.run(run(Path(d)))
 def test_predict(self):self.run_case(False)
 def test_stream(self):self.run_case(True)
 def test_valid_json_preserved(self):
  async def run():
   e=Engine();e.init_budget();e.response=completion('{"instructions":"do research"}');self.assertIs(await e.predict([]),e.response)
  asyncio.run(run())
if __name__=='__main__':unittest.main()
