"""Capture debugger stop and inferior-exit events; run inside GDB Python."""
import gdb
import time

def install(state,save):
    state['debug_events']=[]
    def stopped(event):
        inf=gdb.selected_inferior()
        rec={'kind':'stop','event_type':type(event).__name__,'inferior_num':inf.num,
             'pid':inf.pid,'signal':getattr(event,'stop_signal',None),'time_ns':time.time_ns()}
        state['debug_events'].append(rec);save()
    def exited(event):
        inf=event.inferior
        code=getattr(event,'exit_code',None)
        rec={'kind':'exit','event_type':type(event).__name__,'inferior_num':inf.num,
             'exit_code':int(code) if code is not None else None,'time_ns':time.time_ns()}
        state['debug_events'].append(rec);save()
    gdb.events.stop.connect(stopped)
    gdb.events.exited.connect(exited)
    def continue_return():
        inf=gdb.selected_inferior()
        state['continue_return']={'inferior_num':inf.num,'pid':inf.pid,
                                  'live':bool(inf.pid),'time_ns':time.time_ns()}
        save()
    return continue_return
