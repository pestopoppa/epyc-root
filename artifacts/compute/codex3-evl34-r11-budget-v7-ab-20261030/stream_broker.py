"""Private per-arm incremental HTTP bridge; synthetic controls only.

The trusted parent admits each request once before calling upstream. The
upstream supplies (status, headers, byte iterator). Per-frame and cumulative
caps are mandatory; an incomplete stream remains an error, never a success.
"""
import base64,json
from native_usage import SSEUsage
from broker_protocol import recv,send
MAX_CHUNK=64*1024
MAX_TOTAL=2*1024*1024

def serve_stream(sock,policy,upstream,usage_ledger=None,request_observer=None,req=None):
 if req is None:req=recv(sock)
 if not isinstance(req,dict) or set(req)!={'path','body'}:raise ValueError('invalid envelope')
 if request_observer is not None:request_observer(req['path'],req['body'])
 reservation=policy.admit(req['path'],req['body'])
 status,headers,chunks=upstream(req['path'],req['body'])
 if type(status) is not int or not isinstance(headers,dict):raise ValueError('invalid response metadata')
 send(sock,{'type':'headers','status':status,'headers':headers,'reservation':reservation})
 total=0
 is_sse='text/event-stream' in str(headers.get('content-type','')).lower()
 capture=SSEUsage(usage_ledger) if usage_ledger is not None and is_sse else None
 raw=bytearray() if usage_ledger is not None and not is_sse else None
 recorded=False
 try:
  for chunk in chunks:
   if not isinstance(chunk,bytes):raise ValueError('non-byte response')
   for offset in range(0,len(chunk),MAX_CHUNK):
    part=chunk[offset:offset+MAX_CHUNK];total+=len(part)
    if total>MAX_TOTAL:raise ValueError('response exceeds cap')
    if capture is not None:capture.feed(part)
    if raw is not None:raw.extend(part)
    send(sock,{'type':'data','data':base64.b64encode(part).decode('ascii')})
  if capture is not None:capture.finish();recorded=True
  if raw is not None:
   try:usage_ledger.add(json.loads(raw).get('usage'))
   except (ValueError,TypeError,AttributeError):usage_ledger.add(None)
   recorded=True
  send(sock,{'type':'done','total':total})
 except Exception as exc:
  if usage_ledger is not None and not recorded:usage_ledger.add(None)
  send(sock,{'type':'error','error':type(exc).__name__});raise
