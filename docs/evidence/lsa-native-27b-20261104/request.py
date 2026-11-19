#!/usr/bin/env python3
"""Capture exactly one reviewed native-server request; does not decide trace validity."""
import datetime, hashlib, json, signal, sys, time, urllib.error, urllib.request
from pathlib import Path
d=Path(__file__).resolve().parent
plan=json.loads((d/'plan.json').read_text())
ids=Path(plan['ids']).read_bytes()
assert hashlib.sha256(ids).hexdigest()==plan['ids_sha256']
tokens=json.loads(ids); assert len(tokens)==plan['prompt_n']
port=int(sys.argv[1]); output=Path(sys.argv[2]); assert not output.exists()
request=urllib.request.Request(f'http://127.0.0.1:{port}/completion',data=json.dumps({'prompt':tokens,**plan['request']}).encode(),headers={'Content-Type':'application/json'})
class Deadline(Exception): pass
class Think(Exception): pass
def alarm(*_): raise Deadline('request deadline')
signal.signal(signal.SIGALRM,alarm); signal.setitimer(signal.ITIMER_REAL,300)
start=time.monotonic_ns(); first=None; raw=bytearray(); pending=b''; events=[]; completed=False; reason='incomplete'; outcome_hint='transport_invalid'
try:
 with urllib.request.urlopen(request,timeout=365) as response:
  while True:
   chunk=response.read1(4096)
   if not chunk: break
   raw.extend(chunk); pending+=chunk
   while b'\n' in pending:
    line,pending=pending.split(b'\n',1)
    if not line.startswith(b'data:'): continue
    payload=line[5:].strip()
    if payload==b'[DONE]': continue
    event=json.loads(payload); events.append(event)
    if first is None and event.get('content'):
     first=time.monotonic_ns(); signal.setitimer(signal.ITIMER_REAL,max(.000001,360-(first-start)/1e9))
    text=''.join(x.get('content','') for x in events)
    if '<think>' in text.lower() or any(x.get('reasoning_content') for x in events): raise Think('thinking reopened')
 completed=True; reason='complete'; outcome_hint='complete'
except Think as e: reason=str(e); outcome_hint='thinking'
except (Deadline,TimeoutError) as e: reason=repr(e); outcome_hint='timeout'
except urllib.error.URLError as e: reason=repr(e); outcome_hint='timeout' if isinstance(e.reason,TimeoutError) else 'transport_invalid'
except Exception as e: reason=repr(e)
finally: signal.setitimer(signal.ITIMER_REAL,0)
end=time.monotonic_ns(); final=events[-1] if events else {}; timings=final.get('timings',{}); text=''.join(x.get('content','') for x in events)
checks={'complete':completed and final.get('stop') is True and not pending.strip(),'first_token':first is not None,'gold_exact':text.strip()==plan['expected'],
 'prompt_n':timings.get('prompt_n')==plan['prompt_n'],'predicted_within_cap':isinstance(final.get('tokens_predicted'),int) and 1<=final['tokens_predicted']<=24,
 'no_think':'<think>' not in text.lower() and not any(x.get('reasoning_content') for x in events)}
record={'schema':'lsa-native-sentinel-request-v1','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'request_pass_pending_native_trace_and_residency' if all(checks.values()) else 'invalid_or_wrong',
 'reason':reason,'outcome_hint':outcome_hint,'checks':checks,'output':text,'request_start_monotonic_ns':start,'first_token_monotonic_ns':first,
 'request_end_monotonic_ns':end,'timings':timings,'events':events,'raw_sse_hex':raw.hex(),'raw_sse_sha256':hashlib.sha256(raw).hexdigest()}
with output.open('x') as f: json.dump(record,f,indent=2,allow_nan=False); f.write('\n')
sys.exit(0 if all(checks.values()) else 1)
