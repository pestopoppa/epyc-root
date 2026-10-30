"""Bounded socketpair framing for future confined executor-to-model broker.

A frame is length-prefixed JSON; the trusted parent owns the only upstream
callable. No process launching, endpoint selection or native integration here.
"""
import json,struct,os
MAX_FRAME=2*1024*1024

def read_exact(sock,n):
 data=bytearray()
 while len(data)<n:
  part=os.read(sock.fileno(),n-len(data))
  if not part: raise EOFError('truncated frame')
  data.extend(part)
 return bytes(data)

def recv(sock):
 n=struct.unpack('!I',read_exact(sock,4))[0]
 if n==0 or n>MAX_FRAME:raise ValueError('frame outside bounds')
 return json.loads(read_exact(sock,n))

def send(sock,value):
 data=json.dumps(value,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()
 if not data or len(data)>MAX_FRAME:raise ValueError('frame outside bounds')
 data=struct.pack('!I',len(data))+data
 while data:
  written=os.write(sock.fileno(),data)
  if written<=0:raise BrokenPipeError('short broker write')
  data=data[written:]

def serve_one(sock,policy,upstream,on_admit=None,req=None):
 if req is None:req=recv(sock)
 if not isinstance(req,dict) or set(req) not in ({'path','body'},{'path','body','depth'}):raise ValueError('invalid envelope')
 if 'depth' in req and (type(req['depth']) is not int or req['depth'] not in (0,1)):raise ValueError('invalid depth')
 if 'depth' not in req:raise ValueError('missing depth for REPL request')
 policy.admit_repl(req['depth'])
 reservation=policy.admit(req['path'],req['body'])
 if on_admit is not None:on_admit(req,reservation)
 response=upstream(req['path'],req['body'])
 send(sock,{'reservation':reservation,'response':response})
