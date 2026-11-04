from src.backends.context_limits import ContextLimitResolver, set_context_limit_resolver
import uvicorn
set_context_limit_resolver(ContextLimitResolver(registry_facts=lambda:{18976:{'context_tokens':98304,'slots':4,'kv_unified':True}},role_urls=lambda:{'frontdoor':['http://127.0.0.1:18976']}))
uvicorn.run('src.api:app',host='127.0.0.1',port=18076)
