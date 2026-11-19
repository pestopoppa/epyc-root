#!/usr/bin/env python3
"""Bounded native request-owner/perf functional qualification. Never a floor."""
import base64
import select
import signal
import json
import os
import pathlib
import subprocess
import sys
import time

D = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(D / 'native'))
from owner_hook import RequestCapture
from perf_ring import decode

CPUS = (0, 1, 2, 3)
EVENTS = ('irq_handler_entry', 'irq_handler_exit', 'sched_switch', 'softirq_entry', 'softirq_exit')
MAX_PER_CHILD_S = 8.0
CHILD = r'''import os,sys,time
cpu=int(sys.argv[1]);os.sched_setaffinity(0,{cpu})
print('ready',flush=True)
if sys.stdin.readline().strip()!='run':raise SystemExit(41)
end=time.monotonic()+0.35
x=1
while time.monotonic()<end:x=(x*1664525+1013904223)&0xffffffff
print('worked',flush=True)
if sys.stdin.readline().strip()!='release':raise SystemExit(42)
print('released',flush=True)
'''

def require(ok, msg):
    if not ok: raise RuntimeError(msg)

def validate_capture(path, cpu, pid, boot_id, expected_owner_pid=None):
    doc=json.loads(path.read_text())
    require(doc.get('measurement_admission')=='none', 'measurement admission field')
    require(doc.get('errors')==[], 'native worker reported errors')
    require(doc.get('status')=='unproven', 'native result status changed')
    markers=doc.get('markers')
    require(isinstance(markers,list) and len(markers)==2, 'two markers required')
    a,b=markers
    require((a.get('kind'),a.get('seq'),b.get('kind'),b.get('seq'))==('begin',1,'end',2), 'marker order')
    require(all(a.get(k)==b.get(k) for k in ('pid','uid','start_ticks','boot_id')), 'owner identity changed')
    require(a['pid']==(os.getpid() if expected_owner_pid is None else expected_owner_pid), 'marker owner PID mismatch')
    require(type(a['uid']) is int and a['uid']>=0, 'marker owner UID invalid')
    require(a['boot_id']==boot_id, 'boot identity mismatch')
    require(type(a['timestamp_ns']) is int and type(b['timestamp_ns']) is int and a['timestamp_ns'] < b['timestamp_ns'], 'invalid marker times')
    observations=doc.get('target_observations')
    require(isinstance(observations,list) and len(observations)>=3, 'target snapshots missing')
    for row in observations:
        require(row.get('pid')==pid and row.get('boot_id')==boot_id and type(row.get('start_ticks')) is int, 'target pidfd identity mismatch')
    sources=doc.get('source_provenance'); snapshots=doc.get('snapshots'); rings=doc.get('rings')
    require(isinstance(sources,list) and isinstance(snapshots,list) and isinstance(rings,list), 'native source records missing')
    expected={(c,e) for c in CPUS for e in EVENTS}
    require(len(sources)==len(expected) and {(x.get('cpu'),x.get('name')) for x in sources}==expected, 'source inventory mismatch')
    require(len({x.get('event_id') for x in sources})==len(expected), 'duplicate event identity')
    require(len(rings)==len(expected), 'terminal result count mismatch')
    by_id={x['event_id']:x for x in sources}
    require(len({x.get('event_id') for x in rings})==len(expected), 'duplicate terminal event identity')
    for row in rings:
        src=by_id.get(row.get('event_id'))
        require(src is not None and row.get('cpu')==src['cpu'] and row.get('name')==src['name'], 'terminal source binding')
        require(row.get('errors')==[] and row.get('lost_samples')==0 and type(row.get('count')) is int and row['count']>=0 and row.get('enabled_ns',0)>0 and row.get('running_ns')==row.get('enabled_ns'), 'terminal perf result incomplete')
        if row.get('name')=='sched_switch': require(row['count']>0, 'sched_switch terminal counter has no event')
    found=False
    sched_config=next(x['tracepoint_id'] for x in sources if x['name']=='sched_switch' and x['cpu']==cpu)
    for item in snapshots:
        ring=item.get('ring',{})
        raw_snapshot=ring.get('snapshot')
        if isinstance(raw_snapshot,dict) and raw_snapshot.get('encoding')=='base64':
            ring=dict(ring); ring['snapshot']=base64.b64decode(raw_snapshot['data'],validate=True)
        require(item.get('event_id') in by_id and item.get('cpu')==by_id[item['event_id']]['cpu'], 'snapshot source identity')
        require(ring.get('errors')==[], 'ring reported loss or malformed samples')
        parsed=decode(ring.get('snapshot'),head=ring.get('head'),tail=ring.get('tail'))
        require(parsed.get('errors')==[], 'ring decode error')
        for event in parsed['events']:
            if event.get('type')!='sample': continue
            body=event.get('body',b'')
            if len(body)<54: continue
            import struct
            ident,_,_,_,stamp,event_cpu,reserved,period,rawsize=struct.unpack_from('=QQIIQIIQI',body)
            require(ident==item['event_id'] and event_cpu==item['cpu'] and reserved==0 and period==1 and rawsize<=len(body)-52, 'sample provenance mismatch')
            if item['event_id'] not in by_id or by_id[item['event_id']]['name']!='sched_switch' or item['cpu']!=cpu: continue
            if struct.unpack_from('=H',body,52)[0]!=sched_config: continue
            raw=body[52:52+rawsize]
            fmt=by_id[item['event_id']]['format']
            fields={}
            import re
            for name in ('prev_pid','next_pid'):
                m=re.search(r'field:int\s+'+name+r';\s*offset:(\d+);\s*size:4;\s*signed:1;',fmt)
                if m: fields[name]=int(m.group(1))
            require(set(fields)=={'prev_pid','next_pid'}, 'sched_switch payload format incomplete')
            if max(fields.values())+4<=len(raw):
                prev=struct.unpack_from('<i',raw,fields['prev_pid'])[0]
                nxt=struct.unpack_from('<i',raw,fields['next_pid'])[0]
                if pid in (prev,nxt) and a['timestamp_ns']<=stamp<=b['timestamp_ns']:
                    found=True
    require(found, 'controlled child absent from request-window sched_switch samples')
    return {'cpu':cpu,'target_pid':pid,'owner_pid':a['pid'],'owner_uid':a['uid'],'owner_start_ticks':a['start_ticks'],'marker_begin_ns':a['timestamp_ns'],'marker_end_ns':b['timestamp_ns'],'source_count':len(sources),'target_sched_switch_observed':True}

def read_line(proc, expected, timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        ready,_,_=select.select([proc.stdout],[],[],max(0.0,deadline-time.monotonic()))
        if ready:
            line=proc.stdout.readline()
            if line.strip()==expected: return
            if line=='': raise RuntimeError(f'controlled child stdout closed before {expected}')
            continue
        if proc.poll() is not None: raise RuntimeError(f'controlled child exited before {expected}: {proc.returncode}')
    raise TimeoutError(f'controlled child timeout waiting for {expected}')

def write_exclusive(path, value):
    raw=(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())

def _interrupted(signum, frame):
    raise InterruptedError(f'caught signal {signum}; bounded cleanup follows')

def make_capture(path, cpu):
    return RequestCapture(path, set(CPUS), request_context={'launch_ordinal': cpu, 'phase': 'diagnostic', 'slot_index': 0, 'prompt_id': 'controlled-child', 'request_sha256': '0'*64}, timeout_s=20)

def main():
    signal.signal(signal.SIGTERM,_interrupted); signal.signal(signal.SIGINT,_interrupted)
    run=os.environ['FILLER_ID']
    out=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH') if os.environ.get('FILLER_DRYRUN')=='1' else D/'native-results'/f'{run}.json')
    if not out.is_absolute() or out.exists(): raise FileExistsError('fresh native result path required')
    stop=pathlib.Path(os.environ['FILLER_STOPFILE']); deadline=int(os.environ['FILLER_DEADLINE'])
    admitted=set()
    for part in os.environ['FILLER_CPUS'].split(','):
        bounds=[int(x) for x in part.split('-')]; admitted.update(range(bounds[0],bounds[-1]+1))
    require(set(CPUS)<=admitted and set(CPUS)<=os.sched_getaffinity(0), 'claimed or schedulable CPUs do not cover 0-3')
    os.sched_setaffinity(0,set(CPUS))
    boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    summaries=[]; children=[]; failure=None
    try:
        for cpu in CPUS:
            if stop.exists() or time.time()>=deadline: raise TimeoutError('STOP/deadline before child')
            ev=D/'native-evidence'/run/f'cpu{cpu}.json'; ev.parent.mkdir(parents=True,exist_ok=True)
            require(not ev.exists(), f'evidence already exists: {ev}')
            p=subprocess.Popen([sys.executable,'-I','-c',CHILD,str(cpu)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
            children.append(p); read_line(p,'ready',5)
            capture=make_capture(ev,cpu)
            try:
                capture.attach_target(p.pid)
                capture.begin(); p.stdin.write('run\n'); p.stdin.flush(); read_line(p,'worked',MAX_PER_CHILD_S)
                capture.end()
                p.stdin.write('release\n'); p.stdin.flush(); read_line(p,'released',5)
                p.stdin.close(); rc=p.wait(timeout=5)
                require(rc==0, f'controlled child rc={rc}')
                import hashlib
                ev.chmod(0o644)  # ordinary filing user must be able to replay root-captured raw evidence
                row=validate_capture(ev,cpu,p.pid,boot)
                row['evidence_path']=str(ev); row['evidence_sha256']=hashlib.sha256(ev.read_bytes()).hexdigest()
                summaries.append(row)
            finally:
                if capture.state!='finished': capture.abort()
            if stop.exists() or time.time()>=deadline: raise TimeoutError('STOP/deadline after child')
        require(len(summaries)==len(CPUS), 'incomplete CPU cohort')
    except BaseException as exc:
        failure=f'{type(exc).__name__}:{exc}'[:512]
    finally:
        for p in children:
            if p.poll() is None:
                try:p.terminate();p.wait(timeout=2)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
    result={'schema':'epyc.ch26.owner-observer-functional.v1','run_id':run,
        'status':'failed' if failure else 'functional_pass','measurement_admission':'none',
        'measurement_claim':'none','floor_claim':'none','coverage':'unknown',
        'losslessness':'unknown','placement':'unproven','contention':'unproven',
        'boot_id':boot,'cpus':list(CPUS),'trace_events':list(EVENTS),
        'children':summaries,
        'errors':[] if failure is None else [failure]}
    out.parent.mkdir(parents=True,exist_ok=True)
    write_exclusive(out,result)
    out.chmod(0o644)  # completion gate and filing user replay the strict receipt
    if failure: raise RuntimeError(failure)
    print(json.dumps({'status':'functional_pass','children':len(summaries),'result':str(out)},sort_keys=True),flush=True)

if __name__=='__main__': main()
