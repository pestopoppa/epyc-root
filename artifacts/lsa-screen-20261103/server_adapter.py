#!/usr/bin/env python3
"""One llama-server streaming completion against an owned, already-bound server."""
import ipaddress,json,sys,time,urllib.error,urllib.parse,urllib.request
req=json.load(sys.stdin);cfg=req['effective_config'];url=urllib.parse.urlsplit(cfg['server_url'])
try:local=ipaddress.ip_address(url.hostname).is_loopback
except ValueError:local=url.hostname=='localhost'
if url.scheme!='http' or not local or url.path not in ('','/'):raise SystemExit('server_url must be a loopback HTTP origin')
payload={'prompt':req['token_ids'],'n_predict':req['max_tokens'],'temperature':0,'seed':req['seed'],'cache_prompt':False,'stream':True,'n_probs':cfg.get('n_probs',0)}
request=urllib.request.Request(urllib.parse.urlunsplit((url.scheme,url.netloc,'/completion','','')),data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
start=time.monotonic();first=None;last=None;events=[];parts=[];timings={};result={}
try:
 with urllib.request.urlopen(request,timeout=cfg.get('http_timeout_s',3600)) as response:
  for line in response:
   if not line.startswith(b'data:'):continue
   text=line[5:].strip()
   if text==b'[DONE]':break
   event=json.loads(text);events.append(event);content=event.get('content','')
   if content:
    now=time.monotonic();first=first or now;last=now;parts.append(content)
   if event.get('timings'):timings=event['timings']
 result={'output':''.join(parts),'ttft_ms':(first-start)*1000 if first else None,'tpot_ms':((last-first)*1000/(timings['predicted_n']-1) if first and last and timings.get('predicted_n',0)>1 else None),'ttft_scope':'client request to first streamed nonempty content','tpot_scope':'first to last streamed nonempty content divided by predicted_n-1','server_timings':timings,'events':events}
except urllib.error.HTTPError as e:
 body=e.read().decode(errors='replace');result={'output':'','status':'invalid' if e.code in (400,413,422,503) else 'failure','reason':f'HTTP {e.code}: {body}'}
except TimeoutError:result={'output':'','status':'timeout','reason':'HTTP timeout'}
print(json.dumps(result,allow_nan=False))
