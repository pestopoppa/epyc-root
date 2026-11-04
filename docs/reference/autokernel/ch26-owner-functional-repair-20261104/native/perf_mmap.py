"""Experimental same-FD perf mmap lifecycle; never issues a coverage warrant.

Caller supplies an already opened disabled tracepoint perf FD with the documented
IDENTIFIER|IP|TID|TIME|CPU|PERIOD|RAW layout and exclusive ownership. No host
process is opened here. Linux perf's metadata atomic protocol is used via
libatomic; counter/stream/owner integration still requires independent review.
"""
import ctypes,fcntl,mmap,os,struct,time
from perf_ring import decode
from child_trace_counter import IOC_ID
from kernel_counter import IOC_ENABLE,IOC_DISABLE

HEAD=1024;TAIL=1032;DATA_OFFSET=1040;DATA_SIZE=1048
class Atomics:
 def __init__(self,mem):
  self.mem=mem;self.lib=ctypes.CDLL('libatomic.so.1');self.base=ctypes.addressof(ctypes.c_char.from_buffer(mem))
  self.loadfn=getattr(self.lib,'__atomic_load_8');self.loadfn.argtypes=(ctypes.c_void_p,ctypes.c_int);self.loadfn.restype=ctypes.c_uint64
  self.exchangefn=getattr(self.lib,'__atomic_exchange_8');self.exchangefn.argtypes=(ctypes.c_void_p,ctypes.c_uint64,ctypes.c_int);self.exchangefn.restype=ctypes.c_uint64
 def acquire(self,offset):return self.loadfn(self.base+offset,2) # __ATOMIC_ACQUIRE
 def release(self,offset,value):self.exchangefn(self.base+offset,value,5) # seq-cst RMW: full barrier before data_tail update

class Session:
 def __init__(self,fd,cpu,*,pages=8,mapper=mmap.mmap,atomics=Atomics,ioctl=fcntl.ioctl,read=os.read,close=os.close,clock=time.monotonic_ns,page_size=None):
  if type(fd) is not int or fd<0 or type(cpu) is not int or cpu<0 or type(pages) is not int or pages<1 or pages>1024 or pages&(pages-1):raise ValueError('invalid FD/CPU/ring pages')
  self.fd=fd;self._closed=False;self.cpu=cpu;self.page_size=page_size or os.sysconf('SC_PAGESIZE');self.ioctl=ioctl;self.read=read;self.closefd=close;self.clock=clock;self.state='new';self.errors=[]
  self.mem=mapper(fd,(pages+1)*self.page_size,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE)
  try:
   self.atomics=atomics(self.mem);self.data_offset,self.data_size=struct.unpack_from('=QQ',self.mem,DATA_OFFSET)
   if self.data_offset<self.page_size or self.data_size!=pages*self.page_size or self.data_offset+self.data_size>len(self.mem):raise ValueError('unsupported perf mmap layout')
   b=bytearray(8);self.ioctl(fd,IOC_ID,b,True);self.event_id=struct.unpack('=Q',b)[0]
   if not self.event_id:raise ValueError('invalid event identity')
  except BaseException:self.mem.close();raise
 def start(self):
  if self.state!='new':raise ValueError('wrong state')
  try:
   a=self.clock();self.ioctl(self.fd,IOC_ENABLE,0);b=self.clock()
   if b<a:raise ValueError('clock regression')
   self.enabled=(a,b);self.state='running'
  except BaseException:
   self.state='failed'
   try:self.ioctl(self.fd,IOC_DISABLE,0)
   finally:self.close()
   raise
 def drain(self):
  if self.state not in ('running','disabled'):raise ValueError('wrong state')
  head=self.atomics.acquire(HEAD);tail=self.atomics.acquire(TAIL)
  data=bytes(self.mem[self.data_offset:self.data_offset+self.data_size]);r=decode(data,head=head,tail=tail)
  # Preserve the exact ring bytes and positions for an independent decoder.
  r.update(snapshot=data,head=head,tail=tail)
  for event in r.get('events',[]):
   if event.get('type')=='sample':
    body=event.pop('body')
    if len(body)<52:
     r['errors'].append('short identified sample');continue
    eid,ip,pid,tid,stamp,cpu,res,period,rawsize=struct.unpack_from('=QQIIQIIQI',body)
    if eid!=self.event_id or cpu!=self.cpu or res or not stamp or rawsize>len(body)-52:
     r['errors'].append('sample ID/CPU/layout mismatch');continue
    event.update(id=eid,cpu=cpu,pid=pid,tid=tid,timestamp_ns=stamp,raw_bytes=rawsize)
  self.errors.extend(r.get('errors',[]))
  if not r.get('errors'):
   self.atomics.release(TAIL,r['new_tail'])
  # Explicit loss, overrun, malformed or unknown records fail closed: no tail write.
  return r
 def stop(self,*,request_window=None):
  if self.state!='running':raise ValueError('wrong state')
  try:
   a=self.clock();self.ioctl(self.fd,IOC_DISABLE,0);b=self.clock();self.state='disabled'
   if b<a or a<self.enabled[1]:raise ValueError('invalid enable/disable brackets')
   ring=self.drain()
   if request_window is not None:
    if not isinstance(request_window,tuple) or len(request_window)!=2 or any(type(v) is not int for v in request_window):raise ValueError('invalid request interval')
    begin,end=request_window
    if not self.enabled[1]<=begin<end<=a:self.errors.append('request extends outside conservative enable interval')
   for event in ring.get('events',[]):
    if event.get('type')=='sample' and 'timestamp_ns' in event and not self.enabled[0]<=event['timestamp_ns']<=b:self.errors.append('sample outside enable/disable brackets')
   raw=self.read(self.fd,40)
   if len(raw)!=40:raise ValueError('short event counter read')
   value,enabled,running,eid,lost=struct.unpack('=5Q',raw)
   if eid!=self.event_id or running>enabled:raise ValueError('event identity or counter mismatch')
   if lost:self.errors.append('kernel lost count nonzero')
   if not enabled or enabled!=running:self.errors.append('event did not run continuously')
   return {'status':'unproven','coverage':'unknown','loss':'unknown','event_id':eid,'cpu':self.cpu,'enable_before_ns':self.enabled[0],'enable_after_ns':self.enabled[1],'disable_before_ns':a,'disable_after_ns':b,'count':value,'enabled_ns':enabled,'running_ns':running,'lost_samples':lost,'ring':ring,'errors':list(self.errors),'limitations':['no authenticated request or tracepoint FD attributes','tracepoint raw payload and process ownership not authenticated','kernel loss semantics and continuous coverage not validated','caller must drain often enough to avoid overwrite']}
  except BaseException:self.state='failed';raise
  finally:
   self.close()
   if self.state!='failed':self.state='stopped'

 def close(self):
  """Idempotently release the supplied FD and mapping; disable a running event."""
  if self._closed:return
  self._closed=True
  try:
   if self.state=='running':self.ioctl(self.fd,IOC_DISABLE,0)
  finally:
   try:self.mem.close()
   finally:self.closefd(self.fd)
  if self.state not in ('failed','stopped'):self.state='closed'
