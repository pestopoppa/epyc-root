"""Capture raw in-flight /slots observations, joined only by native task+slot ids."""
import json,os,threading,time
from pathlib import Path


def capture(client,body,slot,path,interval=1.0):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    events=[];fatal=[];stop=threading.Event();start=time.monotonic_ns()
    def record(ev):
        events.append(ev)
        with path.open('a') as f:
            f.write(json.dumps(ev,sort_keys=True,default=str)+'\n');f.flush();os.fsync(f.fileno())
    record({'kind':'request_begin','monotonic_ns':start,'requested_slot':slot})
    def run():
        while not stop.is_set():
            a=time.monotonic_ns()
            try:
                if hasattr(client,'_req'):
                    status,value=client._req('GET','/slots',timeout=1.5)
                    if status!=200:raise RuntimeError('slots HTTP '+str(status))
                else:value=client.slots()
                b=time.monotonic_ns()
                record({'kind':'slots_sample','start_ns':a,'end_ns':b,'slots':value})
            except Exception as e:
                record({'kind':'slots_error','start_ns':a,'end_ns':time.monotonic_ns(),'error':repr(e)})
            if stop.wait(interval):break
    def run_guarded():
        try:run()
        except BaseException as exc:fatal.append(repr(exc))
    thread=threading.Thread(target=run_guarded,daemon=True);thread.start()
    try:
        response=client.complete(body)
    finally:
        ended=time.monotonic_ns();stop.set();thread.join(3.0)
        record({'kind':'request_end','monotonic_ns':ended,'sampler_drained':not thread.is_alive()})
    if fatal:raise RuntimeError('active sample writer failed: '+fatal[0])
    timings=response.get('timings') or {};task=timings.get('id_task');sid=timings.get('id_slot')
    matched=[]
    if type(task) is int and task>=0 and type(sid) is int and sid==slot and not thread.is_alive():
        for ev in events:
            if ev.get('kind')!='slots_sample' or ev.get('start_ns',0)<start or ev.get('end_ns',ended+1)>ended:continue
            if not isinstance(ev.get('slots'),list):continue
            for sample in ev['slots']:
                if isinstance(sample,dict) and sample.get('id')==sid and sample.get('id_task')==task and sample.get('is_processing') is True:
                    matched.append(sample)
    values=[s.get('fork',{}).get('n_fork_tokens') for s in matched if isinstance(s.get('fork'),dict) and type(s.get('fork',{}).get('n_fork_tokens')) is int]
    value=values[0] if values and len(set(values))==1 else None
    return response,{'source':'active_slots','path':str(path),'final_task_id':task,'final_slot_id':sid,
                     'matched_active_samples':len(matched),'matched_values':values,'matched_slot':matched[-1] if matched else None,'n_fork_tokens':value,
                     'status':'observed' if value is not None else 'unknown',
                     'sampler_drained':not thread.is_alive(),'sample_errors':sum(x.get('kind')=='slots_error' for x in events)}
