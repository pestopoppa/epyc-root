"""Prospective sampled request boundaries, never continuous placement."""
import json,os,time,threading
from pathlib import Path
from placement_observation import WindowSampler, MAX_SAMPLES, sample_process
import runtime_linkage

def identity(pid):
 s=Path('/proc') .joinpath(str(pid),'stat').read_text();n=s.rfind(') ')
 if n<0 or int(s[:s.find(' ')])!=pid:raise ValueError('bad identity')
 return {'pid':pid,'start_ticks':int(s[n+2:].split()[19]),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}

class Hook:
 def __init__(self,owned,slots,path,*,snapshot,quiet,request_context,launch_ordinal,placement_sample=None,placement_interval_s=0.05,observer_required=False,runtime_prepared=None):
  if slots!=1 or owned.poll() is not None:raise ValueError('live single-slot owned server required')
  self.proc=owned;self.path=Path(path);self.snapshot=snapshot;self.quiet=quiet;self.state='new';self.target=identity(owned.pid)
  self.request_context=dict(request_context);self.launch_ordinal=launch_ordinal
  if runtime_prepared is None:raise ValueError('prepared C5 runtime identity required')
  self.runtime_prepared=runtime_prepared
  self.observer_required=bool(observer_required)
  self.placement=WindowSampler(owned.pid,sample=placement_sample or sample_process,interval_s=placement_interval_s)
  self._stop=threading.Event();self._thread=None;self._sample_error=None
 def capture(self):
  if self.proc.poll() is not None or identity(self.proc.pid)!=self.target:raise ValueError('target identity changed')
  t=time.monotonic_ns();m=self.snapshot(self.proc.pid);allowed=set(range(96))
  if self.proc.pid not in m or len(m)<2 or any(not a or not set(a)<=allowed for a in m.values()):raise ValueError('incomplete/outside-mask task snapshot')
  if set().union(*(set(a) for a in m.values()))!=allowed or set().union(*(set(a) for tid,a in m.items() if tid!=self.proc.pid))!=allowed:raise ValueError('task or worker affinity union incomplete')
  q=self.quiet()
  if q.get('verdict')!='PASS' or q.get('basis')!='CLAIM_WITNESS':raise ValueError('claim witness not PASS')
  own=q.get('owned') or {};pids=set(own.get('pids',[]))
  if not pids or own.get('incomplete'):raise ValueError('claim ownership incomplete')
  held={}
  for claim in q.get('region_claims',[]):
   if claim.get('role')=='GLOBAL' and claim.get('held') and claim.get('region') in ('q0','q1','q2','q3'):
    holders=set(claim.get('holder_pids',[]));region=claim['region']
    if not holders or not holders<=pids or claim.get('unattributed_holders') or region in held:raise ValueError('unattributed or duplicate global claim')
    held[region]=sorted(holders)
  if set(held)!={'q0','q1','q2','q3'} or not set.intersection(*(set(v) for v in held.values())):raise ValueError('full CPU claim missing common owner')
  mapped=runtime_linkage.capture(self.proc.pid,self.runtime_prepared)
  if mapped['target']!=self.target:raise ValueError('mapped binary target identity changed')
  if self.proc.poll() is not None or identity(self.proc.pid)!=self.target:raise ValueError('target changed during capture')
  return {'runtime_linkage':mapped,'monotonic_ns':t,'target':self.target,'tasks':{str(k):sorted(v) for k,v in m.items()},'global_holders':held,'preflight':q}
 def begin(self):
  if self.state!='new':raise ValueError('wrong hook state')
  self.before=self.capture();self.state='begun'
  self.placement_start_ns=time.monotonic_ns()
  self.placement.rows.append(self.placement.sample(self.proc.pid))
  self._thread=threading.Thread(target=self._sample_loop,name='ch26-placement-sampler',daemon=True);self._thread.start()
 def _sample_loop(self):
  while not self._stop.wait(self.placement.interval_s):
   try:
    if len(self.placement.rows)>=MAX_SAMPLES:raise ValueError('placement sample limit reached')
    self.placement.rows.append(self.placement.sample(self.proc.pid))
   except Exception as e:
    self._sample_error=str(e);self._stop.set();return
 def _stop_sampler(self):
  self._stop.set()
  if self._thread is not None:
   self._thread.join(timeout=2)
   if self._thread.is_alive():raise ValueError('placement sampler failed to stop')
 def end(self,observer_receipt=None):
  if self.state!='begun':raise ValueError('wrong hook state')
  after=self.capture();placement_end_ns=time.monotonic_ns();self._stop_sampler()
  if self._sample_error:raise ValueError('placement sampling failed: '+self._sample_error)
  placement_rows=self.placement.collect(self.placement_start_ns,placement_end_ns)
  if self.before['tasks']!=after['tasks']:raise ValueError('task set or affinity changed across boundaries')
  if self.before['global_holders']!=after['global_holders']:raise ValueError('global claim ownership changed across boundaries')
  if self.before['runtime_linkage']!=after['runtime_linkage']:raise ValueError('mapped binaries changed across boundaries')
  event={**self.request_context,'launch_ordinal':self.launch_ordinal,'status':'observed-at-boundaries','target':self.target,'before':self.before,'after':after,'placement_observation':'sampled-during-request','placement_window_ns':[self.placement_start_ns,placement_end_ns],'placement_samples':placement_rows,'placement_continuous':'unproven','contention_continuous':'unproven','no_inference_scope':'sanctioned-claim-witness-only'}
  if self.observer_required:
   from request_observer_join import join_event
   event=join_event(event,observer_receipt)
  self.write(event)
  self.state='finished'
 def abort(self):
  self._stop_sampler()
  self.write({**self.request_context,'launch_ordinal':self.launch_ordinal,'status':'incomplete','target':self.target});self.state='failed'
 def close(self):pass
 def write(self,row):
  from journal_writer import append_event
  append_event(self.path,row)
