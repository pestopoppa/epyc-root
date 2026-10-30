"""Extract only server-reported usage; missing or malformed means unknown."""
import json,threading
class UsageLedger:
 def __init__(self):self.lock=threading.Lock();self.records=[]
 def add(self,usage):
  if not isinstance(usage,dict):entry=None
  else:
   p=usage.get('prompt_tokens');c=usage.get('completion_tokens')
   if type(c) is int and c>4096:raise ValueError('server exceeded per-call output limit')
   entry={'prompt_tokens':p,'completion_tokens':c} if type(p) is int and p>=0 and type(c) is int and c>=0 else None
  with self.lock:self.records.append(entry)
 def totals(self):
  with self.lock:
   if not self.records or any(x is None for x in self.records):return None
   return {k:sum(x[k] for x in self.records) for k in ('prompt_tokens','completion_tokens')}
class SSEUsage:
 def __init__(self,ledger):self.ledger=ledger;self.buffer=b'';self.usage=None;self.done=False
 def feed(self,chunk):
  if not isinstance(chunk,bytes):raise ValueError('bytes required')
  self.buffer+=chunk
  if len(self.buffer)>2*1024*1024:raise ValueError('SSE buffer too large')
  while b'\n' in self.buffer:
   line,self.buffer=self.buffer.split(b'\n',1);line=line.rstrip(b'\r')
   if not line.startswith(b'data:'):continue
   data=line[5:].strip()
   if data==b'[DONE]':self.done=True;continue
   obj=json.loads(data)
   if obj.get('usage') is not None:self.usage=obj['usage']
 def finish(self):
  self.ledger.add(self.usage if self.done else None)
