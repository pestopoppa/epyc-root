import os
from src.backends.context_limits import ContextLimitResolver,set_context_limit_resolver
import uvicorn
p=int(os.environ['PRIVATE_PORT']);a=int(os.environ['PRIVATE_API'])
set_context_limit_resolver(ContextLimitResolver(registry_facts=lambda:{p:{'context_tokens':98304,'slots':4,'kv_unified':True}},role_urls=lambda:{'frontdoor':[f'http://127.0.0.1:{p}']}))
# Private diagnostic-only policy: preserve pinned source and workload, allow the already-requested 600s scout budget.
import json
from pathlib import Path
from src.api.routes.chat_pipeline import scout_stage
assert scout_stage.PER_CALL_TIMEOUT_S == 180.0, 'unexpected native per-call policy'
assert scout_stage.REQUEST_BUDGET_FRACTION == 0.4, 'unexpected native request fraction'
scout_stage.PER_CALL_TIMEOUT_S = 600.0
policy = {'schema':'epyc.kpf26.private-api-policy.v1', 'pid':os.getpid(),
          'native_per_call_timeout_s':180.0, 'configured_per_call_timeout_s':600.0,
          'request_budget_fraction':scout_stage.REQUEST_BUDGET_FRACTION,
          'api_request_timeout_s':1800.0, 'configured_scout_budget_s':600.0,
          'intended_effective_scout_budget_s':600.0,
          'scope':'private diagnostic policy only; actual effective budget remains in native scout report'}
Path(os.environ['KPF26_POLICY_OUTPUT']).write_text(json.dumps(policy,sort_keys=True)+'\n')
uvicorn.run('src.api:app',host='127.0.0.1',port=a)
