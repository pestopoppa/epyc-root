"""Bind a native slot-fork log to its own captured completion, never invent a task ID."""
import hashlib
import re
from evidence_view import original_segments
from debug3_data import DataError,FORK

SLOT=re.compile(r'id\s+(\d+)\s*\|\s*task\s+(-?\d+)\s*\|')
PUMP=re.compile(r'^\d+\.\d{3} ')
FORK_LOG=re.compile(r'^\d+(?:\.\d+)+ I slot\s+do_slot_fork: ')
LAUNCH_LOG=re.compile(r'^\d+(?:\.\d+)+ I slot\s+launch_slot_: ')

def original_line(mapping,start,end,raw,text):
    segments=original_segments(mapping,start,end)
    if len(segments)!=1:raise DataError('binding line original bytes discontinuous')
    lo,hi=segments[0];line=raw[lo:hi]
    try:decoded=line[:-1].decode('ascii') if line.endswith(b'\n') else ''
    except UnicodeDecodeError:raise DataError('binding line is not native ASCII')
    match=PUMP.match(decoded)
    if not match or decoded[match.end():]!=text:raise DataError('binding text differs from captured bytes')
    return lo,hi

def bind_native_fork(item,messages,events,mapping,scope_native_start,original_raw):
    start,end,text=item;fork=FORK.search(text);slot_binding=SLOT.search(text)
    if not fork or not slot_binding or not FORK_LOG.match(text) or type(scope_native_start) is not int or scope_native_start<0:
        raise DataError('native fork has no provable slot/offset')
    slot=int(slot_binding[1]); logged_task=int(slot_binding[2]);src=int(fork[1]);t=int(fork[2]);total=int(fork[3])
    if slot not in range(4) or logged_task < -1:raise DataError('invalid native fork slot/task')
    if src not in range(4) or src == slot or not 0 < t < total:
        raise DataError('invalid native fork source or token range')
    lo,hi=original_line(mapping,start,end,original_raw,text);native_lo=scope_native_start+lo;native_hi=scope_native_start+hi
    candidates=[]
    for event in events:
        if event.get('path')!='/completion':continue
        a,b=event.get('native_start'),event.get('native_end')
        req=event.get('request');response=event.get('response')
        if not (type(a) is int and type(b) is int and a<=native_lo<native_hi<=b):continue
        if event.get('error'):raise DataError('overlapping fork event failed')
        if not isinstance(req,dict) or not isinstance(response,dict):raise DataError('overlapping fork event missing request/response')
        timing=response.get('timings')
        if not isinstance(timing,dict):raise DataError('overlapping fork event missing timings')
        task=timing.get('id_task');prompt=req.get('prompt')
        if (type(event.get('event_id')) is not int or event['event_id']<0 or type(task) is not int or task<0 or type(event.get('slot')) is not int or event.get('slot')!=slot or type(req.get('id_slot')) is not int or req.get('id_slot')!=slot or
            type(timing.get('id_slot')) is not int or timing.get('id_slot')!=slot or type(response.get('http')) is not int or response.get('http')!=200 or timing.get('fork_src_kind')!='checkpoint' or
            type(timing.get('fork_src_slot')) is not int or timing.get('fork_src_slot')!=src or type(timing.get('n_fork_tokens')) is not int or timing.get('n_fork_tokens')!=t or not isinstance(prompt,list) or len(prompt)!=total or
            logged_task not in (-1,task)):
            raise DataError('overlapping fork event conflicts with native evidence')
        candidates.append((event,task,a,b))
    if len(candidates)!=1:raise DataError('fork lacks unique matching captured completion')
    event,task,a,b=candidates[0]
    launches=[]
    for s,e,line in messages:
        if s<=start or not LAUNCH_LOG.match(line) or 'processing task, is_child =' not in line:continue
        binding=SLOT.search(line)
        if not binding or int(binding[1])!=slot:continue
        ls,le=original_line(mapping,s,e,original_raw,line);ls+=scope_native_start;le+=scope_native_start
        if a<=ls<le<=b:launches.append((s,e,ls,le,int(binding[2])))
    if len(launches)!=1 or launches[0][4]!=task:raise DataError('fork lacks unique subsequent native task launch')
    launch=launches[0]
    if any(start<s<launch[0] and FORK.search(line) for s,e,line in messages):raise DataError('intervening native fork before launch')
    return {'start':start,'end':end,'task':task,'slot':slot,'source':src,'T':t,'total':total,
            'logged_task':logged_task,'event_id':event.get('event_id'),'fork_native_range':[native_lo,native_hi],
            'launch_native_range':[launch[2],launch[3]],
            'fork_text_sha256':hashlib.sha256(original_raw[lo:hi]).hexdigest(),
            'launch_text_sha256':hashlib.sha256(original_raw[launch[2]-scope_native_start:launch[3]-scope_native_start]).hexdigest(),
            'binding_basis':'captured completion window + matching response task + unique subsequent native launch'}
