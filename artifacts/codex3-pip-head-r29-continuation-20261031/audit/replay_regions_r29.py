import sys,contextlib,io,importlib.util,json,hashlib,asyncio
sys.path.insert(0,'/mnt/raid0/llm/venvs/paddleocr/lib/python3.12/site-packages')
import httpx
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');spec=importlib.util.spec_from_file_location('inspect_pip',p);m=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location('native_region','/mnt/micron/codex3-pip-head-r26-20261030/region_generic.py');region=importlib.util.module_from_spec(spec);spec.loader.exec_module(region)
class Reject(httpx.AsyncBaseTransport):
 async def handle_async_request(self,request):raise AssertionError('cached replay reached network')
async def main():
 replay=[]
 for shard in (3,4):
  roots=[f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-head-r26-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}'];w=m.Read(roots)
  for page in m.plan['pages'][5*shard:5*shard+5]:
   prefix='region-'+m.t.sha(m.t.canon(page))[:24]+'-';starts=w.glob(prefix+'*.start.json')
   if not starts:continue
   obj=json.loads(w.read(starts[0].name));body=bytes.fromhex(obj['body_hex']);endpoint='http://127.0.0.1:25400/v1';transport=region.RegionTransport(Reject(),w.root,endpoint,writer=w,prefix=prefix,provenance={'identity':dict(obj['provenance']['identity'],source_pins={**obj['provenance']['identity']['source_pins'],**json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/source-pins.json').read_bytes())})});request=httpx.Request('POST',endpoint+'/chat/completions',content=body);result=await transport.handle_async_request(request);saved=json.loads(w.read(starts[0].name.replace('.start.json','.result.json')));assert result.status_code==200 and hashlib.sha256(result.content).hexdigest()==saved['response_sha256'] and transport.new_requests==0
   replay.append({'index':page['index'],'response_sha256':saved['response_sha256'],'new_requests':transport.new_requests})
 assert len(replay)==5
 print(json.dumps({'scope':'real native transport cached region replay, no network/no writes/no inference','replayed':replay},indent=2))
asyncio.run(main())
