"""Synthetic fixture: real _execute_repl + production primitives via broker.
Private transport replacement, no model and no admission claim.
"""
import asyncio,os,socket,sys
from pathlib import Path
from src.api.models import ChatRequest
import time
from src.api.state import AppState
from src.api.routes.chat_utils import RoutingResult
from src.api.routes.chat_pipeline.repl_executor import _execute_repl
from src.roles import Role
from repl_pool_primitives import PoolPrimitives
from channel_pool import ChannelPool
from repl_depth import install as install_depth
sys.path.insert(0,'/mnt/raid0/llm/tmp/evl37-rus3-full-scope-20261029')
from landlock_no_delete import install
from no_network import install as block_network
root=Path(sys.argv[1]);fds=[int(x) for x in sys.argv[2].split(',')];socks=[socket.socket(fileno=fd) for fd in fds]
os.environ.update(PYTEST_CURRENT_TEST='evl34_repl_fixture',PYTHONDONTWRITEBYTECODE='1',ORCHESTRATOR_PATHS_TMP_DIR=str(root/'tmp'),ORCHESTRATOR_PATHS_CACHE_DIR=str(root/'cache'),ORCHESTRATOR_PATHS_LOG_DIR=str(root/'logs'))
for name in ('tmp','cache','logs'):(root/name).mkdir()
install(root);block_network();install_depth()
if os.environ.get('EVL34_SENTINEL'):
 try:open(os.environ['EVL34_SENTINEL']).read()
 except PermissionError:pass
 else:raise RuntimeError('outer credential fence ineffective')
 try:open('/proc/'+os.environ['EVL34_PARENT_PID']+'/environ').read()
 except (PermissionError,FileNotFoundError):pass
 else:raise RuntimeError('foreign proc readable')
 try:socket.socket(socket.AF_INET,socket.SOCK_STREAM)
 except PermissionError:pass
 else:raise RuntimeError('network socket allowed')
 try:open(os.environ['EVL34_OUTSIDE_WRITE'],'w').write('bad')
 except PermissionError:pass
 else:raise RuntimeError('outside write allowed')
async def main():
 p=PoolPrimitives(ChannelPool(socks),'pinned');p.config.batch_parallelism=2;p._get_role_limit=lambda _:2
 req=ChatRequest(prompt='fixture question',real_mode=True,mock_mode=False,force_mode='repl',max_turns=3)
 routing=RoutingResult(task_id='evl34-fixture',task_ir={},use_mock=False,routing_strategy='forced',formalization_applied=False,document_result=None)
 state=AppState(llm_primitives=p)
 out=await _execute_repl(request=req,routing=routing,primitives=p,state=state,start_time=time.perf_counter(),initial_role=Role.FRONTDOOR)
 assert out.answer=='fixture answer',out.answer
 print('actual REPL plus production primitives and constrained child broker fixture passed')
asyncio.run(main())
