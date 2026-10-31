from pathlib import Path
import json,os,subprocess,sys,time
import importlib.util
spec=importlib.util.spec_from_file_location('worker7',str(Path(__file__).resolve().parent/'native-worker-v7.py'));w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
D=Path(__file__).resolve().parent;T=D/'native-fixture-cutoff-v14';S=T/'store';S.mkdir(parents=True,exist_ok=True)
(S/'llama-server').write_text('''#!/usr/bin/python3
from http.server import BaseHTTPRequestHandler,HTTPServer
import argparse,json,time
p=argparse.ArgumentParser(add_help=False);p.add_argument('--port',type=int);p.add_argument('-m');a,_=p.parse_known_args()
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  x={'status':'ok'} if self.path=='/health' else {'model_path':a.m};b=json.dumps(x).encode();self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_POST(self):
  q=json.loads(self.rfile.read(int(self.headers['content-length'])));time.sleep(.25);v='[[20]]' if q['max_tokens']==32 else '2';b=json.dumps({'choices':[{'message':{'content':v},'finish_reason':'stop'}],'usage':{'completion_tokens':3},'model':a.m}).encode();self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*x):pass
HTTPServer(('127.0.0.1',a.port),H).serve_forever()
''');(S/'llama-server').chmod(0o700)
(T/'campaign.py').symlink_to(D/'campaign.py') if not (T/'campaign.py').exists() else None
model=T/'fixture-model';model.write_text('fixture');st=model.stat();keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns');(T/'MODEL-ATTESTATION.json').write_text(json.dumps({'sha256':'fixture','identity':{k:getattr(st,k) for k in keys}}))
for n in ('SAMPLE.json','PREDECLARED.md','launch.sh'):(T/n).symlink_to(D/n)
w.D=T;w.STORE=S;w.MODEL=str(model);w.TEMPLATE='/public-template';w.PORT=19864
w.lock_witness.capture_gpu=lambda:(0,0);w.lock_witness.verify_gpu=lambda *a:None;w.gpu_smoke_admission.check=lambda:True
w.mapped_identity=lambda *a:{'fixture_only':True}; original=subprocess.Popen;server=[None]
def launch(*args,**kwargs):
 p=original(*args,**kwargs)
 if server[0] is None:server[0]=p
 return p
subprocess.Popen=launch
w.kfd=lambda:({} if server[0] is None or server[0].poll() is not None else {server[0].pid:1})
os.environ.update(PRB_SOURCE_SHA='fixture-only',PRB_NATIVE_REVIEWED='1',FILLER_STOPFILE=str(T/'STOP'),FILLER_END=str(int(time.time()+90)),FILLER_DEADLINE=str(int(time.time()+80)))
sys.argv=['native_worker.py','cutoff'];rc=w.main();assert rc==75
records=list(T.glob('smoke-*/RESULT.json'));assert len(records)==1
r=json.loads(records[0].read_text());assert r['rc']==75 and r['partial'] and r['gpu_samples']>=2 and r['server_dead'] and r['client_dead'] and not r['cleanup_errors'] and r['cutoff_triggered'] and r['completed_rounds']>=1
print('same worker fixture: after-work explicit cutoff rc75 and captured child cleanup PASS')
