"""Fail-closed CPU observer evidence evaluation; no retrospective evidence."""
import re

def check(stderr, samples, pid, birth, pins, start, end, max_gap=.75):
    if not pins or start >= end: raise ValueError('missing pins/window')
    lines=[x for x in stderr.splitlines() if x.startswith('CPU_OBSERVER ')]
    if not lines: raise ValueError('missing observer')
    events={}
    for line in lines:
        fields=line.split(); name=fields[1]
        vals=dict(x.split('=',1) for x in fields[2:] if '=' in x)
        events.setdefault(name,[]).append(vals)
        if 'pid' in vals and int(vals['pid']) != pid: raise ValueError('observer pid')
    for name in ('hooks','sched_new','device','backend','buffer','usage','graph','graph_backend'):
        if not events.get(name): raise ValueError('missing hook '+name)
    if any(x.get('count')!='5' for x in events['hooks']) or events.get('hook_failure'): raise ValueError('missing hook coverage')
    for name in ('device','backend','graph_backend'):
        if any(x.get('type')!='0' for x in events.get(name,[])): raise ValueError('non-CPU '+name)
    for name in ('buffer','usage','direct_graph'):
        if any(x.get('device_type')!='0' for x in events.get(name,[])): raise ValueError('non-CPU '+name)
    if any(x.get('host')!='1' for x in events['buffer']+events['usage']): raise ValueError('nonhost buffer')
    if not any(x.get('usage')=='1' and int(x.get('size','0'))>0 for x in events['usage']): raise ValueError('missing weights')
    if any(int(x.get('devices','0'))!=1 or int(x.get('backends','0'))!=1 for x in events['sched_new']): raise ValueError('scheduler inventory')
    if any(int(x.get('backends','0'))!=1 for x in events['graph']): raise ValueError('graph inventory')
    if len(events['graph_backend']) != len(events['graph']) or len(events['device'])!=len(events['sched_new']) or len(events['backend'])!=len(events['sched_new']): raise ValueError('incomplete inventory')
    window=[s for s in samples if start<=s['time']<=end]
    if len(window)<2 or window[0]['time']-start>max_gap or end-window[-1]['time']>max_gap: raise ValueError('audio window uncovered')
    if any(b['time']-a['time']>max_gap or b['time']<=a['time'] for a,b in zip(window,window[1:])): raise ValueError('sampling gap')
    for s in window:
        if s['pid']!=pid or s['birth']!=birth or s['affinity']!='24-25': raise ValueError('pid birth/affinity')
        if not s['maps'] or any(p not in pins or pins[p]!=h for p,h in s['maps'].items()): raise ValueError('foreign/missing mapped pin')
        if s['kfd_present'] and (not s['vram'] or any(v!=0 for v in s['vram'].values())): raise ValueError('missing/nonzero VRAM')
    return {'audio_samples':len(window),'event_counts':{k:len(v) for k,v in events.items()}}
