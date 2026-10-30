"""Synthetic fixture: real _execute_repl + production primitives via broker.
Private transport replacement, no model and no admission claim.
"""
import asyncio,os,socket,sys
from pathlib import Path
from src.api.models import ChatRequest
from tests.unit.test_oab7_context_bundle import _run
from repl_broker_primitives import BrokerPrimitives
from repl_depth import install as install_depth
sys.path.insert(0,'/mnt/raid0/llm/tmp/evl37-rus3-full-scope-20261029')
from landlock_no_delete import install
from no_network import install as block_network
root=Path(sys.argv[1]);fd=int(sys.argv[2]);sock=socket.socket(fileno=fd)
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
 p=BrokerPrimitives(sock,'pinned')
 req=ChatRequest(prompt='fixture question',real_mode=True,mock_mode=False,force_mode='repl',max_turns=3)
 out=await _run(req,p)
 assert out.answer=='fixture answer',out.answer
 print('actual REPL plus production primitives and constrained child broker fixture passed')
asyncio.run(main())
