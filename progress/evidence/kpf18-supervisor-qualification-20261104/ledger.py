"""Data-boundary logging around existing calls; no transport implementation."""
import hashlib
import json
from pathlib import Path
import time

def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

class Ledger:
    def __init__(self,directory,ctx,srv):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False)
        self.ctx,self.srv=ctx,srv;self.events=[];self.inventory={};self.serial=0;self.views=[]
    def artifact(self,path):
        path=Path(path);ref=str(path.relative_to(self.directory)) if path.is_relative_to(self.directory) else str(path)
        self.inventory[ref]={'path':str(path),'sha256':file_sha(path),'basis':'native_capture'}
        return ref
    def json(self,name,value):
        path=self.directory/name
        def data_value(item):
            if isinstance(item,Path):return str(item)
            if type(item).__name__=='TraceSlice':return {'type':'native TraceSlice','path':str(item.path),'start':item.start,'end':item.end}
            raise TypeError('unsupported raw data value: '+type(item).__name__)
        with path.open('x') as stream:json.dump(value,stream,sort_keys=True,allow_nan=False,default=data_value);stream.write('\n')
        return self.artifact(path)
    def cursor(self):return Path(self.srv.log).stat().st_size if Path(self.srv.log).exists() else 0
    def invoke(self,label,slot,body,call,*,path='/completion',method='POST'):
        self.ctx.check_boundary();self.serial+=1
        entry={'event_id':self.serial,'label':label,'slot':slot,'method':method,'path':path,
               'request':body,'native_start':self.cursor(),'begin_ns':time.monotonic_ns()}
        raw=self.directory/f'{self.serial:03d}-{label}.read-frames.jsonl'
        old=getattr(self.ctx.client,'raw_observer',None)
        with raw.open('x') as output:
            def observe(kind,value):
                output.write(json.dumps({'kind':kind,'bytes_hex':value.hex()},sort_keys=True)+'\n');output.flush()
            self.ctx.client.raw_observer=observe
            try:
                entry['response']=call()
                return entry['response'],entry
            except BaseException as error:
                entry['error']=type(error).__name__+': '+str(error)
                raise
            finally:
                self.ctx.client.raw_observer=old
                entry.update(end_ns=time.monotonic_ns(),native_end=self.cursor(),raw_frames=self.artifact(raw))
                entry['raw_ref']=self.json(f'{self.serial:03d}-{label}.event.json',entry)
                self.events.append(entry)
                self.ctx.check_boundary()
    def snapshot(self,name):
        reply,event=self.invoke(name,None,None,lambda:self.ctx.client.slots(),method='GET',path='/slots')
        return {item['id']:item for item in reply},event
    def request(self,gate,R,label,body):
        reply,event=self.invoke(label,body['id_slot'],body,lambda:self.ctx.client.stream(body))
        row=R.row(label,reply,group=3,slot=body['id_slot'])
        return row,event
    def action(self,slot,action,body):
        path=f'/slots/{slot}?action={action}'
        reply,event=self.invoke(f'{action}{slot}',slot,body,lambda:self.ctx.client._req('POST',path,body),path=path)
        status,result=reply
        if status!=200 or not isinstance(result,dict):raise ValueError('native foreign action failed: '+str(reply))
        if result.get('id_slot')!=slot:raise ValueError('foreign action returned another slot')
        event['decoded_response']=result
        return result,event
    def close(self):
        # Original log is retained in full, including every rejected trial.
        self.artifact(self.srv.log)
        for path in sorted(self.directory.rglob('*')):
            if path.is_file():self.artifact(path)
        construction=Path(self.ctx.out)/'construction'
        if construction.exists():
            for path in sorted(construction.rglob('*')):
                if path.is_file():self.artifact(path)
        return self.json('EVENT-LEDGER.json',{'schema':'epyc.kpf18.serial-native-ledger.v1','events':self.events,'native_capture_views':self.views,
            'inventory':self.inventory,'single_outstanding_mutating_request':True,
            'capture_basis':'serialized controller calls plus original complete pump log and already-read byte frames'})
