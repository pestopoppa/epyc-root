"""Task-private captured-loopback upstream; no model launch or grant.

The producer child holds only its pipe and restricted loopback socket. The
caller must own and supervise the server, provide a truthful live witness, and
preserve evidence; this module does not establish admission by itself.
"""
import http.client,json,multiprocessing as mp,os,socket,sys,time,threading
sys.path.insert(0,'/mnt/raid0/llm/tmp/evl37-rus3-full-scope-20261029')
from bound_socket_lock import install
from server_peer import verify_tuple

def producer(send,port,path,body,server_pid,server_birth,timeout):
 try:
  sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
  keep={0,1,2,send.fileno(),sock.fileno()}
  for item in os.listdir('/proc/self/fd'):
   try:
    fd=int(item)
    if fd not in keep:os.close(fd)
   except OSError:pass
  install(sock,port);sock.settimeout(timeout);sock.connect(('127.0.0.1',port))
  send.send(('connected',sock.getsockname(),sock.getpeername()))
  if not send.poll(min(2,timeout)):raise TimeoutError('parent attribution timeout')
  evidence=send.recv()
  if not isinstance(evidence,dict) or evidence.get('pid')!=server_pid or evidence.get('birth_ticks')!=server_birth:raise RuntimeError('server attribution refused')
  conn=http.client.HTTPConnection('127.0.0.1',port,timeout=timeout);conn.sock=sock
  conn.request('POST',path,body=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  send.send(('dispatch',time.monotonic_ns(),evidence));response=conn.getresponse()
  if response.status!=200:raise RuntimeError('server HTTP '+str(response.status))
  send.send(('headers',response.status,{'content-type':response.getheader('content-type','')}))
  while True:
   chunk=response.read1(65536)
   if not chunk:break
   send.send(('chunk',time.monotonic_ns(),chunk))
  conn.close();send.send(('done',))
 except BaseException as exc:
  try:send.send(('error',type(exc).__name__+': '+str(exc)))
  except (OSError,EOFError):pass
 finally:send.close()

class Upstream:
 def __init__(self,port,pid,birth,deadline,stop,witness):
  if type(port) is not int or not 1024<=port<=65535 or type(pid) is not int or type(birth) is not int:raise ValueError('invalid captured identity')
  self.port,self.pid,self.birth,self.deadline,self.stop,self.witness=port,pid,birth,deadline,stop,witness
  self.local=threading.local()
 def __call__(self,path,body):
  if path!='/v1/chat/completions':raise ValueError('unsupported endpoint')
  self.local.evidence=None
  before=self.witness();ctx=mp.get_context('spawn');recv,send=ctx.Pipe(True)
  p=ctx.Process(target=producer,args=(send,self.port,path,body,self.pid,self.birth,max(.1,min(120,self.deadline-time.monotonic()))));p.start();send.close()
  pending_samples=[];dispatch_time=[None]
  def message():
   while time.monotonic()<self.deadline and not self.stop():
    if dispatch_time[0] is not None:
     sample=self.witness()
     if sample.get('identity')!=before.get('identity'):raise RuntimeError('server identity changed during request')
     if (sample.get('cpu_residency_verified') is True and sample.get('own_pid_rss_bytes',0)>0) or sample.get('gpu_own_pid_vram_bytes',0)>0:pending_samples.append((time.monotonic_ns(),sample))
    if recv.poll(.05):return recv.recv()
    if not p.is_alive():raise RuntimeError('producer exited')
   raise TimeoutError('upstream deadline/stop')
  try:
   connection=message()
   if connection[0]!='connected' or connection[2]!=('127.0.0.1',self.port):raise RuntimeError('producer did not connect to captured endpoint: '+str(connection))
   until=time.monotonic()+2
   while True:
    try:peer=verify_tuple(connection[1],connection[2],self.pid,self.birth);break
    except RuntimeError:
     if time.monotonic()>=until:raise
     time.sleep(.01)
   recv.send(peer)
   dispatch=message()
   if dispatch[0]!='dispatch':raise RuntimeError('producer did not dispatch: '+str(dispatch))
   dispatch_time[0]=dispatch[1]
   head=message()
   if head[0]!='headers':raise RuntimeError('producer response refused: '+str(head))
  except BaseException:
   self._drain(p,recv);raise
  def chunks():
   total=0;samples=pending_samples;first=None;last=None
   try:
    while True:
     sample=self.witness()
     if sample.get('identity')!=before.get('identity'):raise RuntimeError('server identity changed during request')
     if (sample.get('cpu_residency_verified') is True and sample.get('own_pid_rss_bytes',0)>0) or sample.get('gpu_own_pid_vram_bytes',0)>0:samples.append((time.monotonic_ns(),sample))
     event=message()
     if event[0]=='done':break
     if event[0]!='chunk':raise RuntimeError('producer failed: '+str(event))
     if first is None:first=event[1]
     last=event[1]
     total+=len(event[2])
     if total>2*1024*1024:raise ValueError('upstream cap exceeded')
     yield event[2]
    samples=[sample for sample in samples if last is not None and dispatch[1]<=sample[0]<=last]
    if not samples:raise RuntimeError('no during-request residency witness')
    after=self.witness()
    if before.get('identity') is None or before.get('identity')!=after.get('identity'):raise RuntimeError('server identity changed')
    self.local.evidence={'dispatch_ns':dispatch[1],'peer':dispatch[2],'first_chunk_ns':first,'last_chunk_ns':last,'samples':samples,'identity_before':before,'identity_after':after}
   finally:self._drain(p,recv)
  return head[1],head[2],chunks()
 @staticmethod
 def _drain(p,recv):
  if p.is_alive():p.terminate();p.join(1)
  if p.is_alive():p.kill();p.join(1)
  if p.is_alive():raise RuntimeError('producer did not exit')
  p.join();recv.close()
