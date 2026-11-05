"""Decode captured sched_switch perf samples with a retained tracefs format.

Diagnostic projection only: this does not establish source authenticity, event
coverage, loss semantics, thread ownership, contention, or measurement admission.
"""
import re
import struct

_FIELD = re.compile(r'^\s*field:(.+?);\s*offset:(\d+);\s*size:(\d+);\s*signed:([01]);\s*$')
_NAME = re.compile(r'([A-Za-z_][A-Za-z_0-9]*)(?:\[\d+\])?\s*$')

def parse_format(text, expected_id):
    if not isinstance(text, str) or type(expected_id) is not int or expected_id <= 0:
        raise ValueError('invalid format or expected ID')
    ids = re.findall(r'^ID:\s*(\d+)\s*$', text, re.M)
    names = re.findall(r'^name:\s*(\S+)\s*$', text, re.M)
    if ids != [str(expected_id)] or names != ['sched_switch']:
        raise ValueError('wrong tracepoint format identity')
    fields = {}
    for line in text.splitlines():
        m = _FIELD.match(line)
        if not m:
            continue
        name = _NAME.search(m.group(1))
        if not name:
            raise ValueError('unrecognized field')
        name = name.group(1)
        if name in fields:
            raise ValueError('duplicate field')
        fields[name] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    for name, size, signed in [('common_type', 2, 0), ('prev_pid', 4, 1), ('next_pid', 4, 1)]:
        if name not in fields or fields[name][1:] != (size, signed):
            raise ValueError('missing or incompatible ' + name)
    spans = sorted((offset,offset + size,name) for name,(offset,size,_) in fields.items())
    if any(size <= 0 or offset < 0 or offset + size > 4096 for offset,size,_ in fields.values()):
        raise ValueError('invalid field span')
    if any(a[1] > b[0] for a,b in zip(spans,spans[1:])):
        raise ValueError('overlapping fields')
    return fields

def decode_sample(body, *, cpu, event_id, tracepoint_id, fields):
    if not isinstance(body, bytes) or len(body) < 54 or type(cpu) is not int or cpu < 0:
        raise ValueError('invalid sample')
    try:
        ident, _, pid, tid, stamp, observed_cpu, reserved, period, rawsize = struct.unpack_from('<QQIIQIIQI', body)
    except struct.error as exc:
        raise ValueError('short perf sample') from exc
    if ident != event_id or observed_cpu != cpu or reserved or period != 1 or not stamp:
        raise ValueError('sample source or time mismatch')
    if rawsize > len(body) - 52:
        raise ValueError('truncated raw payload')
    raw = body[52:52+rawsize]
    def field(name, fmt):
        off, size, _ = fields[name]
        if off + size > len(raw):
            raise ValueError('field exceeds raw payload')
        return struct.unpack_from(fmt, raw, off)[0]
    if field('common_type', '<H') != tracepoint_id:
        raise ValueError('tracepoint type mismatch')
    prev, nxt = field('prev_pid', '<i'), field('next_pid', '<i')
    if prev < 0 or nxt < 0:
        raise ValueError('negative thread ID')
    return {'cpu':cpu,'timestamp_ns':stamp,'prev_tid':prev,'next_tid':nxt,'sample_pid':pid,'sample_tid':tid}

def check_continuity(events, *, cpus, begin_ns, end_ns):
    """Check per-CPU switch chains bracket a window; never assert event completeness."""
    if not isinstance(cpus, (set,frozenset)) or not cpus or any(type(x) is not int or x < 0 for x in cpus):
        raise ValueError('invalid CPUs')
    if type(begin_ns) is not int or type(end_ns) is not int or not 0 < begin_ns < end_ns:
        raise ValueError('invalid interval')
    grouped = {c:[] for c in cpus}
    for e in events:
        if not isinstance(e,dict) or e.get('cpu') not in grouped or any(type(e.get(k)) is not int for k in ('timestamp_ns','prev_tid','next_tid')) or e['prev_tid'] < 0 or e['next_tid'] < 0:
            raise ValueError('invalid switch')
        grouped[e['cpu']].append(e)
    result = {}
    for cpu, rows in grouped.items():
        if any(a['timestamp_ns'] >= b['timestamp_ns'] for a,b in zip(rows,rows[1:])):
            raise ValueError('nonmonotonic switch timestamps')
        if any(a['next_tid'] != b['prev_tid'] for a,b in zip(rows,rows[1:])):
            raise ValueError('switch chain discontinuity')
        if not rows or rows[0]['timestamp_ns'] > begin_ns or rows[-1]['timestamp_ns'] < end_ns:
            raise ValueError('window not bracketed')
        result[str(cpu)] = len(rows)
    return {'status':'consistent-only','switches_per_cpu':result,'coverage':'unknown','loss':'unknown','placement':'unproven','contention':'unproven','measurement_admission':'none'}
