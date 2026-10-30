"""Prospective smoke-only quiescence gate; never changes normal pilot dispatch."""
import threading,time
class EntryGate:
 def __init__(self):self.lock=threading.Lock();self.ready=threading.Event()
 def dispatch(self,operation,*,first_model_response=False):
  with self.lock:
   if self.ready.is_set():return False
   operation()
   if first_model_response:self.ready.set()
   return True

class DrainGate:
 """Stop new smoke-only dispatch; acknowledge only after every active send."""
 def __init__(self):self.condition=threading.Condition();self.active=0;self.closed=False;self.acknowledged=False;self.ready=threading.Event()
 def begin(self):
  with self.condition:
   if self.closed:return False
   self.active+=1;return True
 def end(self):
  with self.condition:
   if self.active<1:raise RuntimeError('unbalanced dispatch')
   self.active-=1;self.condition.notify_all()
 def close_and_drain(self,stop):
  with self.condition:
   if self.closed:raise RuntimeError('duplicate quiescence request')
   self.closed=True;deadline=time.monotonic()+30
   while self.active:
    if stop():raise RuntimeError('stop while draining broker')
    if time.monotonic()>=deadline:raise TimeoutError('broker quiescence deadline')
    self.condition.wait(.1)

 def finish_first_and_drain(self,stop):
  with self.condition:
   if self.active<1 or self.closed:raise RuntimeError('invalid first response completion')
   self.active-=1;self.closed=True;deadline=time.monotonic()+30
   while self.active:
    if stop():raise RuntimeError('stop while draining broker')
    if time.monotonic()>=deadline:raise TimeoutError('broker quiescence deadline')
    self.condition.wait(.1)
   self.acknowledged=True
 def acknowledge(self,operation):
  with self.condition:
   if not self.closed or self.active:raise RuntimeError('broker not drained')
   operation()
   self.acknowledged=True
 def is_acknowledged(self):
  with self.condition:return self.acknowledged
