"""Bounded request-window snapshots; device activity is not PID-attributed compute.
Caller supplies an exclusive owned one-slot server, brackets calls within one
HTTP request, and makes slots() a bounded identity-checked /slots request.
No background worker and no native inference is started by this module.
"""
import time
from pathlib import Path

class ObservationError(RuntimeError): pass

def read_busy(path='/sys/class/drm/card2/device/gpu_busy_percent'):
    value = int(Path(path).read_text().strip())
    if not 0 <= value <= 100: raise ObservationError('invalid device busy percent')
    return value

def processing(slots):
    if not isinstance(slots, list) or len(slots) != 1 or not isinstance(slots[0], dict):
        raise ObservationError('expected exactly one server slot')
    v = slots[0].get('is_processing')
    if type(v) is not bool: raise ObservationError('missing boolean is_processing')
    task = slots[0].get('id_task')
    if v and (type(task) is not int or task < 0): raise ObservationError('active slot missing task identity')
    return (v, task)

class Observer:
    def __init__(self, request_id, custody, slots, busy, *, interval_s=1.0, max_samples=512, clock=time.monotonic_ns):
        if not isinstance(request_id,str) or not request_id or interval_s <= 0 or not 2 <= max_samples <= 100000:
            raise ValueError('invalid sampling configuration')
        self.request_id, self.custody, self.slots, self.busy = request_id, custody, slots, busy
        self.interval_ns, self.max_samples, self.clock = int(interval_s*1e9), max_samples, clock
        self.samples=[]; self.attempts=0; self.inactive=0; self.timeouts=0; self.next_ns=0; self.truncated=0
        self.window_start_ns=clock(); self.closed=False; self.observed_count=0; self.max_vram_bytes=0; self.max_device_busy_percent=0
    def poll(self):
        if self.closed: raise ObservationError('observation closed')
        now=self.clock()
        if now < self.next_ns: return
        self.next_ns=now+self.interval_ns; self.attempts+=1
        before_start=self.clock()
        try: before,before_task=processing(self.slots())
        except TimeoutError:
            self.timeouts+=1; self.inactive+=1; return
        before_end=self.clock()
        if not before:
            self.inactive+=1; return
        measured_start=self.clock(); own=self.custody(); busy=self.busy(); measured_end=self.clock()
        after_start=self.clock()
        try: after,after_task=processing(self.slots())
        except TimeoutError:
            self.timeouts+=1; self.inactive+=1; return
        after_end=self.clock()
        if not after or before_task != after_task:
            self.inactive+=1; return
        if not isinstance(own,dict) or type(own.get('vram_bytes')) is not int or own['vram_bytes'] <= 0:
            raise ObservationError('invalid owned KFD VRAM')
        if type(busy) is not int or not 0 <= busy <= 100: raise ObservationError('invalid device busy percent')
        sample={'request_id':self.request_id,'slot_task_id':before_task,'slot_before':True,'slot_after':True,
                'slot_before_interval_ns':[before_start,before_end], 'measurement_interval_ns':[measured_start,measured_end],
                'slot_after_interval_ns':[after_start,after_end], 'owned':own, 'device_busy_percent':busy}
        if self.samples and (own.get('pid'),own.get('start_ticks')) != (self.samples[0]['owned'].get('pid'),self.samples[0]['owned'].get('start_ticks')):
            raise ObservationError('server identity changed')
        self.observed_count+=1; self.max_vram_bytes=max(self.max_vram_bytes,own['vram_bytes']); self.max_device_busy_percent=max(self.max_device_busy_percent,busy)
        if len(self.samples) < self.max_samples: self.samples.append(sample)
        else: self.truncated+=1
    def finish(self):
        if self.closed: raise ObservationError('observation already closed')
        end=self.clock(); self.closed=True
        return {'schema':'a2.gpu-observation.v1','request_id':self.request_id,
                'request_client_window_ns':[self.window_start_ns,end], 'interval_ns':self.interval_ns,
                'attempts':self.attempts,'slot_not_bracketed':self.inactive,'slot_timeouts':self.timeouts,'samples':self.samples,
                'truncated_samples':self.truncated, 'bracketed_sample_count':self.observed_count,
                'sampled_max_own_vram_bytes':self.max_vram_bytes if self.observed_count else None,
                'sampled_max_device_busy_percent':self.max_device_busy_percent if self.observed_count else None,
                'interpretation':'owned PID KFD residency and device-wide busy snapshots bracketed by one-slot processing observations; sampling is not continuous, does not prove PID-attributed compute or the true peak'}
