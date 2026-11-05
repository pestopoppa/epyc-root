"""Dynamic later-slot software controls. HTTP peers are synthetic, never models."""
import hashlib,json,math,os,signal,socket,threading,time,traceback
from pathlib import Path
from types import SimpleNamespace as NS
import cancel_seed_transport as transport

ROOT=Path(__file__).resolve().parent
class Abort(RuntimeError):pass
class SyntheticStop(RuntimeError):pass
class GrantStop(RuntimeError):pass
class GrantDeadline(RuntimeError):pass
TERMINATED=threading.Event()
SIGNAL_NUMBER=None
def signal_notice(number,frame):
    global SIGNAL_NUMBER
    SIGNAL_NUMBER=number
    TERMINATED.set()
def grant_boundary():
    if TERMINATED.is_set():raise GrantStop(f"received signal {SIGNAL_NUMBER}")
    stop_paths=[ROOT/"STOP"]
    if os.environ.get("FILLER_STOPFILE"):stop_paths.append(Path(os.environ["FILLER_STOPFILE"]))
    if any(p.exists() for p in stop_paths):raise GrantStop("actual row/grant STOP")
    ends=[float(os.environ[name]) for name in ("FILLER_DEADLINE","FILLER_END") if os.environ.get(name)]
    if ends and (not all(math.isfinite(end) for end in ends) or time.time()>=min(ends)):
        raise GrantDeadline("earliest grant deadline/end reached")
class Deadline(RuntimeError):pass

class Peer:
    def __init__(self,phase,mode,log):
        self.phase,self.mode,self.log=phase,mode,log
        self.socket=socket.socket();self.socket.bind(('127.0.0.1',0));self.socket.listen(8);self.socket.settimeout(.05)
        self.port=self.socket.getsockname()[1];self.done=threading.Event();self.target=threading.Event()
        self.threads=[];self.requests=[];self.slots=0;self.errors=[];self.connections=[]
        self.thread=threading.Thread(target=self.serve,name='fixture-accept');self.thread.start()
    def serve(self):
        while not self.done.is_set():
            try:conn,_=self.socket.accept()
            except socket.timeout:continue
            except OSError:break
            self.connections.append(conn)
            worker=threading.Thread(target=self.handle,args=(conn,),name='fixture-request')
            self.threads.append(worker);worker.start()
    def handle(self,conn):
        try:
            with conn:
                conn.settimeout(.6);raw=b''
                while b'\r\n\r\n' not in raw:
                    part=conn.recv(4096)
                    if not part:return
                    raw+=part
                first=raw.split(b'\r\n',1)[0].decode();self.requests.append(first)
                if first.startswith('POST /completion '):
                    # Full synthetic body is drained before emitting one progress event.
                    header,body=raw.split(b'\r\n\r\n',1)
                    size=int(next(x.split(b':',1)[1] for x in header.split(b'\r\n') if x.lower().startswith(b'content-length:')))
                    while len(body)<size:body+=conn.recv(min(65536,size-len(body)))
                    self.log.write_text('slot launch_slot_: id 1 | task 9 | processing task, is_child = 0\n'+'cancel task, id_task = 9\n'+'slot release: id 1 | task 9 | stop processing: n_tokens = 32000, truncated = 0\n')
                    event=b'data: {"id_slot":-1,"prompt_progress":{"total":32512,"processed":31744}}\n\n'
                    conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: '+str(len(event)).encode()+b'\r\n\r\n'+event)
                    self.done.wait(1);return
                assert first.startswith('GET /slots '),first
                self.slots+=1;query=self.slots
                target=query==self.phase
                if target and self.mode!='stop_body':self.target.set()
                row={'id':1,'id_task':9,'is_processing':query==2,'n_prompt_tokens':0 if query==1 else 32000,'kv_cells':{'private':0}}
                payload=json.dumps([row]).encode()
                mode=self.mode if target else 'success'
                if mode in ('headers','stop_headers'):self.done.wait(1);return
                conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(payload)).encode()+b'\r\nConnection: close\r\n\r\n')
                if mode=='stop_body':self.target.set()
                if mode in ('body','stop_body'):self.done.wait(1);return
                if mode=='trickle':
                    for byte in payload:
                        if self.done.wait(.025):return
                        conn.sendall(bytes([byte]))
                else:conn.sendall(payload)
        except (OSError,TimeoutError):pass
        except BaseException: self.errors.append(traceback.format_exc())
    def close(self):
        self.done.set();self.socket.close()
        for conn in self.connections:
            try:conn.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        self.thread.join(2)
        for worker in self.threads:worker.join(2)
        assert not self.thread.is_alive() and not any(t.is_alive() for t in self.threads),'peer threads remain'
        assert not self.errors,self.errors


def run_case(phase,mode,root):
    case=root/f'query{phase}-{mode}';case.mkdir(parents=True,exist_ok=False)
    log=case/'synthetic-server.log';log.touch()
    peer=Peer(phase,mode,log);calls=[];rows=[];started=time.monotonic()
    original=transport.bounded_slots
    def boundary():
        grant_boundary()
        if peer.target.is_set() and mode.startswith('stop_'):raise SyntheticStop('synthetic STOP at target query')
        if time.monotonic()-started>1.0:raise Deadline('fixture terminal boundary')
    ctx=NS(check_boundary=boundary,client=NS(base=f'http://127.0.0.1:{peer.port}'),args=NS(port=peer.port),deadline=NS(remaining=lambda:.18),out=case)
    def observed(ctx,**kw):
        item={'site':len(calls)+1,'start':time.monotonic()};calls.append(item)
        try:
            value=original(ctx,**kw);item['status']='returned';item['rows']=value;return value
        except BaseException as exc:item['status']=type(exc).__name__;raise
        finally:item['end']=time.monotonic()
    def write_json(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
    gate=NS(Abort=Abort,body_for=lambda ids,n,slot,**kw:{'prompt':ids,'n_predict':n,'id_slot':slot},write_json=write_json,sha256_file=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest())
    transport.bounded_slots=observed
    status='returned';returned=None
    try:
        try:returned=transport.SeedControl(delay_s=0)(gate=gate,ctx=ctx,R=NS(rows=NS(add=rows.append)),srv=NS(proc=NS(pid=os.getpid(),poll=lambda:None),log=log),slot=1,source_ids=[0]*32512,checkpoint=32000,n_predict=256,control=1,attempt=1)
        except BaseException as exc:status=type(exc).__name__
    finally:
        transport.bounded_slots=original;peer.close()
    elapsed=time.monotonic()-started
    assert len(calls)>=phase,(phase,mode,status,calls)
    assert all(call['status']=='returned' for call in calls[:phase-1]),calls
    expected='SyntheticStop' if mode.startswith('stop_') else ('returned' if mode=='success' else 'TimeoutError')
    assert calls[phase-1]['status']==expected,(expected,calls,status)
    assert calls[phase-1]['end']-calls[phase-1]['start']<.8,calls
    if mode=='success':
        assert status=='returned' and len(calls)==3,(status,calls)
        assert returned['seed_task_id']==9 and returned['slot']['is_processing'] is False
    elif mode.startswith('stop_'):
        assert status=='SyntheticStop',(status,calls)
    elif phase==3:assert status=='TimeoutError',(status,calls)
    else:assert status=='Deadline',(status,calls) # SeedControl records/catches binding errors then polls; expose this behavior.
    assert elapsed<3,elapsed
    return {'phase':phase,'mode':mode,'status':status,'calls':calls,'requests':peer.requests,'elapsed_s':elapsed,'peer_joined':True,'ownership':'real same-process loopback listener; synthetic HTTP peer and process wrapper; no native server','synthetic_log':str(log)}


def main():
    signal.signal(signal.SIGTERM,signal_notice)
    signal.signal(signal.SIGINT,signal_notice)
    out=Path(os.environ['G3_LATER_RESULT']);out.parent.mkdir(parents=True,exist_ok=True)
    assert not out.exists() and not out.is_symlink()
    work=out.parent/'fixture-cases';work.mkdir(exist_ok=False)
    observations=[];error=None
    try:
        for phase in (2,3):
            for mode in ('success','headers','body','trickle','stop_headers','stop_body'):
                grant_boundary()
                observations.append(run_case(phase,mode,work))
                grant_boundary()
        grant_boundary()
        assert not any(t.name in ('fixture-accept','fixture-request') or t.name.endswith('(watch)') for t in threading.enumerate())
    except BaseException:error=traceback.format_exc()
    result={'schema':'kpf18.g3.later-slots.v1','status':'FAIL' if error else 'PASS','controls':len(observations),'observations':observations,'error':error,'affinity':sorted(os.sched_getaffinity(0)),'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')},'scope':'dynamic second task-binding and third postcancel-idle slot-query software controls in copied patched SeedControl; synthetic native log; no native cancellation/release, GPU, admission or full lifecycle claim'}
    if not error:
        try:grant_boundary()
        except BaseException:
            result['error']=traceback.format_exc();result['status']='FAIL';error=result['error']
    out.write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(1 if error else 0)
if __name__=='__main__':main()
