"""Bridge captured upstream to REPL broker; preserve native server usage."""
import json
class REPLUpstream:
 def __init__(self,upstream,usage):self.upstream=upstream;self.usage=usage
 def __call__(self,path,body):
  try:
   status,headers,chunks=self.upstream(path,body)
   if status!=200 or 'application/json' not in headers.get('content-type','').lower():raise ValueError('unexpected response')
   raw=b''.join(chunks)
   if len(raw)>2*1024*1024:raise ValueError('response too large')
   result=json.loads(raw)
   if not isinstance(result,dict):raise ValueError('unexpected payload')
   self.usage.add(result.get('usage'))
   return result
  except BaseException:
   self.usage.add(None);raise
