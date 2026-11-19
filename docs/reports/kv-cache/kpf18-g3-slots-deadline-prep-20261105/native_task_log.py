"""Exact a1 native task ownership/release witness; no fuzzy process matching."""
import re
from physical_trace import TraceError

SLOT=re.compile(r'slot\s+([A-Za-z_]+): id\s+(\d+) \| task (\d+) \| (.*)')
CANCEL=re.compile(r'cancel task, id_task = (\d+)')

def canceled_task(lines,*,task_id,slot_id=1,T=32000):
    launched=[];released=[];cancel=[];errors=[];own=[]
    for line in lines:
        match=SLOT.search(line)
        if match and int(match[2])==slot_id and int(match[3])==task_id:
            own.append(line)
            if match[1]=='launch_slot_' and 'processing task, is_child = 0' in match[4]:launched.append(line)
            if match[1]=='release':
                n=re.fullmatch(r'stop processing: n_tokens = (\d+), truncated = ([01])\s*',match[4])
                if n:released.append((int(n[1]),int(n[2])))
        cm=CANCEL.search(line)
        if cm and int(cm[1])==task_id:cancel.append(line)
        # Entire own-server request byte window is retained. No foreign model
        # requests are permitted in the protocol; every native ERROR matters.
        if re.match(r'^\s*(?:[0-9]+(?:\.[0-9]+)+\s+){1,2}E\s',line) or any(s in line for s in ('failed to process speculative batch','decode() failed:','post_decode() failed:')):
            errors.append(line)
    if len(launched)!=1:raise TraceError('seed native task launch identity absent/ambiguous')
    if released!=[(T,0)]:raise TraceError('seed native release did not preserve exact T untruncated')
    if not cancel:raise TraceError('native reader did not enqueue cancellation for seed task')
    if errors:raise TraceError('native target/drafter error in seed request window')
    return {'task_id':task_id,'slot_id':slot_id,'release_tokens':T,'truncated':False,
            'cancel_enqueued':True,'native_release_observed':True,
            'source_state_argument':'original task32512 > retainedT; prefix append-only until CANCEL release',
            'native_task_lines':own,'native_cancel_lines':cancel,'native_errors':errors}
