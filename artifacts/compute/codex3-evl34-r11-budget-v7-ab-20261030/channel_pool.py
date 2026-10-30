"""Task-private pool of independently owned socketpair channels.

Exclusive channel per in-flight request; no dynamic network creation.
Closed/failed channels are discarded. Admission and custody remain external.
"""
import queue
class ChannelPool:
 def __init__(self,sockets):
  sockets=list(sockets)
  if not sockets or len({s.fileno() for s in sockets})!=len(sockets) or any(s.fileno()<0 for s in sockets):raise ValueError('distinct open channels required')
  self.q=queue.Queue(maxsize=len(sockets))
  for s in sockets:self.q.put_nowait(s)
 def take(self,timeout=60):return self.q.get(timeout=timeout)
 def put(self,sock):
  if sock.fileno()>=0:self.q.put_nowait(sock)
