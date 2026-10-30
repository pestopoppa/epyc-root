"""Actual production REPL executor using task-private fixed-model transport.

Requires caller-provided containment, scratch, socketpair channels, and journal.
No test mocks. Child receives only the public prompt, never the source answer.
"""
import asyncio,json,os,socket,sys,time
from pathlib import Path
from src.api.models import ChatRequest
from src.api.state import AppState
from src.api.routes.chat_utils import RoutingResult
from src.api.routes.chat_pipeline.repl_executor import _execute_repl
from src.roles import Role
from channel_pool import ChannelPool
from repl_pool_primitives import PoolPrimitives
from repl_depth import install as install_depth
from browse_adapters import Registry
from src.repl_environment.external_access import _ExternalAccessMixin
sys.path.insert(0,'/mnt/raid0/llm/tmp/evl37-rus3-full-scope-20261029')
from landlock_no_delete import install
from no_network import install as block_network
root=Path(sys.argv[1]).resolve(strict=True);fds=[int(x) for x in sys.argv[2].split(',')];socks=[socket.socket(fileno=fd) for fd in fds]
public=json.loads((root/'prompt.json').read_bytes())
if set(public)!={'prompt'} or not isinstance(public['prompt'],str):raise ValueError('prompt-only input required')
os.environ.update(PYTHONDONTWRITEBYTECODE='1',ORCHESTRATOR_PATHS_TMP_DIR=str(root/'tmp'),ORCHESTRATOR_PATHS_CACHE_DIR=str(root/'cache'),ORCHESTRATOR_PATHS_LOG_DIR=str(root/'logs'))
for name in ('tmp','cache','logs'):(root/name).mkdir()
loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
install(root);block_network(loop._csock.fileno());install_depth()
async def main():
 pool=ChannelPool(socks);p=PoolPrimitives(pool,'pinned');p.config.batch_parallelism=3;p._get_role_limit=lambda _:3
 registry=Registry(pool)
 def fetch(self,url,max_chars,aud):
  self._exploration_calls+=1
  return registry.call('visit',url)[:max_chars]
 _ExternalAccessMixin._web_fetch_inner=fetch
 req=ChatRequest(prompt=public['prompt'],real_mode=True,mock_mode=False,force_mode='repl',max_turns=8)
 routing=RoutingResult(task_id='evl34-control',task_ir={},use_mock=False,routing_strategy='forced',formalization_applied=False,document_result=None)
 out=await _execute_repl(request=req,routing=routing,primitives=p,state=AppState(llm_primitives=p,tool_registry=registry),start_time=time.perf_counter(),initial_role=Role.FRONTDOOR)
 data=json.dumps(out.model_dump(mode='json'),ensure_ascii=False,allow_nan=False).encode()
 if len(data)>2*1024*1024:raise ValueError('response exceeds cap')
 with (root/'response.json').open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
loop.run_until_complete(main());loop.close()
