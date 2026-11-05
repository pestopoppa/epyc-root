"""Native SSE cancellation capture, with NO import-time network activity.

Caller supplies an already admitted own-server transport. Closing a socket
does NOT prove native cancellation; cancel_seed_admission separately demands
the actual task handler, idle same task, full retained grid, and no generation.
"""
import json
import time

class SeedCaptureError(ValueError):pass

def capture(*,lines,close_transport,capture_task_identity,write_raw,deadline_check,
            slot_id=1,total=32512,trigger_processed=31744,delay_s=.05,
            sleep=time.sleep,clock=time.monotonic):
    """One construction attempt; every raw SSE line is retained.

    Trigger is BEFORE T: cancellation must be serviced only after the T
    forward, never assumed from a client-side time. Early/late outcomes are
    construction refusals preserved by the caller, maximum THREE attempts
    per control. Delay is predeclared; no outcome-driven search is allowed.
    """
    if not 0<=delay_s<=.25:raise SeedCaptureError('unapproved cancellation delay')
    events=[];identity=None;closed=False;trigger=None;prior=-1
    try:
        for raw in lines:
            deadline_check()
            if not isinstance(raw,bytes):raise SeedCaptureError('raw transport bytes required')
            write_raw(raw)
            if not raw.startswith(b'data:'):continue
            payload=raw[5:].strip()
            if not payload or payload==b'[DONE]':continue
            event=json.loads(payload)
            if not isinstance(event,dict):raise SeedCaptureError('nonobject native SSE')
            events.append(event)
            # a1f0c8cf9 send_partial_response never assigns inherited id_slot,
            # so its actual native partial JSON carries -1. Bind the real slot
            # through the captured own connection/body + native /slots task,
            # never fabricate slot1 from this sentinel.
            if event.get('id_slot')!=-1:raise SeedCaptureError('unexpected exact-image native partial slot field')
            progress=event.get('prompt_progress')
            if progress is None:
                if any(type(t) is int and t>=0 for t in event.get('tokens',[])):
                    raise SeedCaptureError('seed generated before intended cancellation')
                continue
            if not isinstance(progress,dict) or progress.get('total')!=total:
                raise SeedCaptureError('original full prompt total changed')
            processed=progress.get('processed')
            if type(processed) is not int or processed<prior:
                raise SeedCaptureError('bad/out-of-order native progress')
            prior=processed
            if identity is None:
                # Exactly one native /slots read at seed start, bound to this
                # own SSE connection/body slot and original full-prompt task.
                identity=capture_task_identity(event)
                if type(identity) is not int or identity<0:raise SeedCaptureError('missing native seed task id')
            if processed==trigger_processed:
                trigger={'processed':processed,'at_monotonic':clock(),'delay_s':delay_s}
                deadline_check()
                sleep(delay_s)
                deadline_check()
                close_transport()
                closed=True
                break
            if processed>trigger_processed:raise SeedCaptureError('missed exact progress trigger')
        if trigger is None:raise SeedCaptureError('no exact cancellation trigger')
        return {'events':events,'seed_task_id':identity,'client_cancel_trigger':trigger,
                'transport_closed':closed,'native_cancel_accepted':False,
                'note':'client close is a request only; native post-cancel geometry admission still mandatory'}
    finally:
        if not closed:close_transport()

