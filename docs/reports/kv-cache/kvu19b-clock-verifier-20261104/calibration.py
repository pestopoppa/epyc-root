"""Fail-closed arithmetic for prospective KPF profiling clock records.

No GPU/runtime/model access. Input custody/identity and the origin of a drift
bound are the caller's responsibility; this is not a gate verdict.
"""
from dataclasses import dataclass

NS = 1_000_000_000

@dataclass(frozen=True)
class Sample:
    before_ns: int
    hsa_tick: int
    after_ns: int
    hz: int

@dataclass(frozen=True)
class Witness:
    marker: str
    host_begin_ns: int
    host_end_ns: int
    profiler_begin_ns: int
    profiler_end_ns: int


def _u64(value, name):
    if type(value) is not int or not 0 <= value < 1 << 64:
        raise ValueError('invalid '+name)
    return value


def validate(samples, witnesses, expected_markers, max_gap_ns, *, bound_source):
    """Check host/HSA brackets plus named witness containment.

    A stable measured offset is assumed only after caller supplies an externally
    justified nonempty bound_source and max_gap_ns. Samples/witnesses prove
    only their exact times. A finite witness set never proves interior drift.
    Return explicitly diagnostic evidence, with no authorization to attribute.
    """
    if not isinstance(bound_source, str) or not bound_source.strip():
        raise ValueError('drift-bound provenance required')
    _u64(max_gap_ns, 'max_gap_ns')
    if max_gap_ns == 0: raise ValueError('positive witness gap required')
    if len(samples) < 4: raise ValueError('need at least four clock samples')
    if not expected_markers or len(expected_markers) < 3 or len(set(expected_markers)) != len(expected_markers):
        raise ValueError('need unique edge and interior markers')
    if len(witnesses) != len(expected_markers) or {w.marker for w in witnesses} != set(expected_markers):
        raise ValueError('missing or duplicate witnesses')
    freq = samples[0].hz
    if type(freq) is not int or not 1_000_000 <= freq <= 400_000_000:
        raise ValueError('invalid HSA frequency')
    offsets=[]
    last_tick=-1; last_host=-1
    for s in samples:
        if not isinstance(s, Sample) or s.hz != freq: raise ValueError('changed HSA frequency')
        b=_u64(s.before_ns,'before'); e=_u64(s.after_ns,'after'); t=_u64(s.hsa_tick,'tick')
        if b > e or b < last_host or t < last_tick: raise ValueError('invalid clock order')
        last_tick=t;last_host=e
        floor=t*NS//freq; ceil=(t*NS+freq-1)//freq
        offsets.append((b-ceil,e-floor))
    lo=max(x[0] for x in offsets); hi=min(x[1] for x in offsets)
    if lo > hi: raise ValueError('clock offsets disagree')
    ws=sorted(witnesses,key=lambda x:x.host_begin_ns)
    if [w.marker for w in ws] != list(expected_markers):
        raise ValueError('witness ordering mismatch')
    for w in ws:
        b=_u64(w.host_begin_ns,'host begin'); e=_u64(w.host_end_ns,'host end')
        p=_u64(w.profiler_begin_ns,'profiler begin'); q=_u64(w.profiler_end_ns,'profiler end')
        if b >= e or p >= q or not (b <= p+lo <= p+hi and q+lo <= q+hi <= e):
            raise ValueError('witness outside host bracket')
    if max(s.after_ns for s in samples[:2]) > ws[0].host_begin_ns or min(s.before_ns for s in samples[-2:]) < ws[-1].host_end_ns:
        raise ValueError('samples do not bracket all witnesses')
    if any(b.host_begin_ns-a.host_end_ns > max_gap_ns for a,b in zip(ws,ws[1:])):
        raise ValueError('witness gap exceeds declared limit')
    return {'schema':'kvu19b.clock-arithmetic.v1','observed_offset_ns':[lo,hi],
            'witnesses':len(ws),'bound_source':bound_source,
            'scope':'diagnostic arithmetic only; no identity, interior drift, GPU residency, or attribution established'}
