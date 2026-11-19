import os
from src.backends.context_limits import ContextLimitResolver,set_context_limit_resolver
import uvicorn
import json
from pathlib import Path
from src.api.routes.chat_pipeline import scout_stage
from diagnostic_policy import apply
policy=apply(scout_stage)
Path(os.environ["KPF26_POLICY_RECEIPT"]).write_text(json.dumps(policy,indent=2)+"\n")
p=int(os.environ['PRIVATE_PORT']);a=int(os.environ['PRIVATE_API'])
set_context_limit_resolver(ContextLimitResolver(registry_facts=lambda:{p:{'context_tokens':98304,'slots':4,'kv_unified':True}},role_urls=lambda:{'frontdoor':[f'http://127.0.0.1:{p}']}))
uvicorn.run('src.api:app',host='127.0.0.1',port=a)
