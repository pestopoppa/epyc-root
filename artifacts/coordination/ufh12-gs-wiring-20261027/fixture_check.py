import importlib.util, json, os, pathlib, socket, subprocess, sys, tempfile, threading, time, types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import faiss
B=pathlib.Path(__file__).resolve().parent
spec_native=importlib.util.spec_from_file_location('fixture_native','/mnt/raid0/llm/worktrees/ni-ufh12-gs-rehearsal-wiring-root/scripts/vidya/producers/ufh12_gs_capture.py')
native=importlib.util.module_from_spec(spec_native); spec_native.loader.exec_module(native)
spec=importlib.util.spec_from_file_location('diag',B/'diagnostic.py'); d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
class Server(BaseHTTPRequestHandler):
    fault=False
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if Server.fault:
            self.send_response(500); self.end_headers(); return
        if self.path=='/tokenize':
            assert body['content'].startswith(d.DOC) and body['add_special'] is True
            result={'tokens':[1,2,3]}
        else:
            text=body['input']; eg=text.startswith(d.QUERY); size=768 if eg else 1024
            v=[0.0]*size; v[0]=1.0
            result={'data':[{'index':0,'embedding':v}]}
        data=json.dumps(result).encode(); self.send_response(200); self.end_headers(); self.wfile.write(data)
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),Server); thread=threading.Thread(target=server.serve_forever); thread.start()
try:
    with tempfile.TemporaryDirectory(dir=B/'test-run/tmp') as tmp:
        root=pathlib.Path(tmp)/'copy'; out=pathlib.Path(tmp)/'out'; root.mkdir()
        for kind,n in [('episodic',489),('strategy',11)]:
            ids=[f'{kind}-{i:04}' for i in range(n)]
            for lane,dim in [('old',1024),('new',256)]:
                folder=(d.OLD if lane=='old' else d.NEW)[kind]; path=root/folder; path.mkdir()
                index=faiss.IndexFlatIP(dim); vectors=np.zeros((n,dim),dtype='float32'); vectors[:,0]=1; index.add(vectors)
                indexfile,idfile,dbfile=d.FILES[kind]; faiss.write_index(index,str(path/indexfile)); np.save(path/idfile,np.array(ids)); (path/dbfile).write_text('fixture')
        tool=pathlib.Path(tmp)/'fixture.py'
        tool.write_text('''import contextlib, numpy as np\n@contextlib.contextmanager\ndef _ro_connect(path): yield None\nclass Base:\n def __init__(self,directory): self.dir=directory\n def _load_id_map(self): return np.load(self.dir/self.map).tolist()\n def resolve_rows(self,con,ids): return {i:("fixture "+i,None) for i in ids}\nclass EpisodicComponent(Base):\n map="id_map.npy"; db_name="episodic.db"\nclass StrategyComponent(Base):\n map="strategy_id_map.npy"; db_name="strategies.db"\n''')
        url='http://127.0.0.1:'+str(server.server_port)
        context={'region_lock_claim':'synthetic-test','server_proof':{str(tool):d.digest(tool)},'synthetic':True,'model_path':str(tool),'model_sha256':d.digest(tool)}
        a=types.SimpleNamespace(copy=str(root),tool=str(tool),out=str(out),bge_model=str(tool),eg2_model=str(tool),server_bin=str(tool),eg2_url=url,bge_url=url,context=context,deadline=time.monotonic()+60)
        man,src=d.prepare(a); assert sum(map(len,man['selection'].values()))==500
        m=d.module(tool)
        badout=pathlib.Path(tmp)/'bad-out'; badargs=types.SimpleNamespace(**vars(a)); badargs.out=str(badout)
        badman,badsrc=d.prepare(badargs); realpost=d.post
        for payload in ({'tokens':'not-a-list'},{'tokens':[True]},{'tokens':[]}):
            d.post=lambda *args, **kw: payload
            try: d.tokens(badargs,badman,badsrc,m); raise AssertionError('bad token response accepted')
            except ValueError: pass
        d.post=realpost
        Server.fault=True
        try: d.tokens(a,man,src,m); raise AssertionError('HTTP failure accepted')
        except Exception as exc:
            assert not isinstance(exc,AssertionError)
        assert not (out/'tokens-summary.json').exists()
        Server.fault=False
        a.deadline=0; assert not d.tokens(a,man,src,m); assert not (out/'tokens-summary.json').exists()
        a.deadline=time.monotonic()+60; assert d.tokens(a,man,src,m); assert sum(x['n'] for x in d.load(out/'tokens-summary.json')['records'])==500
        token_record,token_side=native.emit(out,'tokens',context)
        token_row=json.loads(token_side.read_text()); assert native.validate(token_row)==[] and token_row['value']==500
        a.deadline=time.monotonic()+180
        oldstop=d.stopped; calls=[0]
        def stop_after_one(args):
            calls[0]+=1
            return calls[0]>=4
        d.stopped=stop_after_one
        assert not d.scores(a,man,src,m); d.stopped=oldstop
        assert not (out/'scores-summary.json').exists()
        checkpoint=next(out.glob('score-*.json')); original=checkpoint.read_text(); damaged=json.loads(original); damaged['bge'][0]['cosine']=0.123; checkpoint.write_text(json.dumps(damaged))
        try: d.scores(a,man,src,m); raise AssertionError('tampered checkpoint accepted')
        except ValueError: pass
        checkpoint.write_text(original)
        a.deadline=time.monotonic()+180; assert d.scores(a,man,src,m)
        assert d.load(out/'scores-summary.json')['records'][0]['overlap_fraction_percentiles']['50']==1
        rec,side=native.emit(out,'scores',context)
        row=json.loads(side.read_text()); assert native.validate(row)==[]
        claim=native.project(row); assert claim.value==500 and claim.protocol_id==''
        record=d.load(rec); record['checkpoints'][0]['record']['bge'][0]['cosine']=0.2; d.save(rec,record)
        assert native.validate(row)
        realpost=d.post
        for payload in ({'data':[]},{'data':[{'index':1,'embedding':[1]*1024}]},{'data':[{'index':0,'embedding':[float('nan')]*1024}]}):
            d.post=lambda *a, **kw: payload
            try: d.query(url,'query',1024,False); raise AssertionError('bad embedding accepted')
            except ValueError: pass
        d.post=realpost
        server_path=pathlib.Path(tmp)/'server'
        server_path.write_text('''#!/usr/bin/env python3\nimport sys,json\nfrom http.server import BaseHTTPRequestHandler,HTTPServer\na=sys.argv; model=a[a.index('-m')+1]; port=int(a[a.index('--port')+1]); dim=768 if model.endswith('eg.gguf') else 1024\nclass H(BaseHTTPRequestHandler):\n def log_message(self,*x): pass\n def do_GET(self):\n  payload={'data':[{'id':model}]} if self.path=='/v1/models' else {'status':'ok'}\n  self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(payload).encode())\n def do_POST(self):\n  n=int(self.headers['Content-Length']); body=json.loads(self.rfile.read(n)); v=[0.0]*dim; v[0]=1\n  payload={'tokens':[1,2]} if self.path=='/tokenize' else {'data':[{'index':0,'embedding':v}]}\n  self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(payload).encode())\nHTTPServer(('127.0.0.1',port),H).serve_forever()\n'''); server_path.chmod(0o755)
        (pathlib.Path(tmp)/'eg.gguf').write_text('fixture eg'); (pathlib.Path(tmp)/'bg.gguf').write_text('fixture bg')
        link=pathlib.Path(tmp)/'link.sh'; link.write_text('#!/bin/bash\necho PASS\n'); link.chmod(0o755)
        env=os.environ.copy(); env.update({'GS_FIXTURE_ROOT':tmp,'FILLER_ID':'ufh12-gs-fixture','FILLER_CPUS':'48-49','FILLER_DEADLINE':str(int(time.time())+1100)})
        launch=subprocess.run(['bash',str(B/'job.sh'),'scores'],env=env,text=True,capture_output=True,timeout=180)
        assert launch.returncode==0, (launch.returncode,launch.stdout,launch.stderr)
        assert (pathlib.Path(tmp)/'results/scores-summary.json').exists()
        assert list((pathlib.Path(tmp)/'results').glob('*.belief_measurements.jsonl'))
        for port in (19111,19112):
            with socket.socket() as s: assert s.connect_ex(('127.0.0.1',port))!=0
        env['GS_FIXTURE_FAIL_CLEANUP']='1'
        failed_drain=subprocess.run(['bash',str(B/'job.sh'),'scores'],env=env,text=True,capture_output=True,timeout=180)
        assert failed_drain.returncode!=0 and 'cleanup failed' in failed_drain.stderr
        assert not (B/'COMPLETE.scores').exists()
        for port in (19111,19112):
            with socket.socket() as s: assert s.connect_ex(('127.0.0.1',port))!=0
        del env['GS_FIXTURE_FAIL_CLEANUP']
        server_path.write_text('#!/bin/bash\nexit 44\n'); server_path.chmod(0o755)
        failed=subprocess.run(['bash',str(B/'job.sh'),'scores'],env=env,text=True,capture_output=True,timeout=30)
        assert failed.returncode!=0
        for port in (19111,19112):
            with socket.socket() as s: assert s.connect_ex(('127.0.0.1',port))!=0
        (root/d.OLD['episodic']/d.FILES['episodic'][2]).write_text('changed')
        try: d.prepare(a); raise AssertionError('changed source accepted')
        except ValueError: pass
        print('PASS fake HTTP, paired-ID scores, token checkpoints, resume, mutation refusal')
finally:
    server.shutdown(); thread.join(); server.server_close()
