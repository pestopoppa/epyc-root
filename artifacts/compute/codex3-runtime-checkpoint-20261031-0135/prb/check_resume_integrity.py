from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import hashlib,json,os,subprocess,sys,threading,time,shutil
D=Path(__file__).resolve().parent
calls=[]
class H(BaseHTTPRequestHandler):
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['content-length']))); calls.append(body)
  content='[[20]]' if body['max_tokens']==32 else '2'
  b=json.dumps({'choices':[{'message':{'content':content},'finish_reason':'stop'}],'usage':{'completion_tokens':3},'model':'fixture'}).encode();self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*_):pass
s=ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=s.serve_forever,daemon=True).start()
out=D/'fixture-resume-integrity';shutil.rmtree(out,ignore_errors=True);out.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source='fixture-source';end=int(time.time()+120)
def envelope(name):
 p=out/name;p.write_text(json.dumps({'run_id':'codex3-prbt4-r1-20261031','gpu_resident':True,'model_sha256':'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348','source_catalog_sha256':source,'sample_sha256':sha(D/'SAMPLE.json'),'launcher_sha256':sha(D/'launch.sh'),'predeclared_sha256':sha(D/'PREDECLARED.md'),'server_pid':1,'server_birth_ticks':1,'server_uid':os.getuid(),'grant':'fixture','observed_unix':time.time()-1,'deadline_epoch':end}));return p
old=envelope('old-envelope.json');new=envelope('new-envelope.json')
env=dict(os.environ,PRB_SOURCE_SHA=source,PRB_ENVELOPE=str(old),PRB_QUALIFIED_EXECUTION='1',PRB_SMOKE='1',PRB_OUTPUT=str(out/'cells'),PRB_ENDPOINT=f'http://127.0.0.1:{s.server_port}',FILLER_STOPFILE=str(out/'no-stop'),FILLER_DEADLINE=str(end))
def run():return subprocess.run([sys.executable,'-B',str(D/'campaign.py')],env=env,timeout=15,capture_output=True,text=True)
p=run();assert p.returncode==0,(p.returncode,p.stderr)
cell=out/'cells/0000/estimate.json'; original=cell.read_bytes();r=json.loads(original);r['result']['budget']=999;cell.write_text(json.dumps(r))
env['PRB_ENVELOPE']=str(new);before=len(calls);p=run();assert p.returncode!=0 and len(calls)==before,(p.returncode,len(calls)-before,p.stderr)
r.pop('record_sha256');r['record_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();cell.write_text(json.dumps(r));before=len(calls);p=run();assert p.returncode!=0 and len(calls)==before,(p.returncode,p.stderr)
cell.write_bytes(original)
for name in ('baseline','static','tale'):(cell.parent/(name+'.json')).unlink()
before=len(calls);p=run();assert p.returncode==0 and len(calls)-before==3,(p.returncode,p.stderr,len(calls)-before)
assert cell.read_bytes()==original
for name in ('baseline','static','tale'):
 r=json.loads((cell.parent/(name+'.json')).read_text());assert r['write_warrant']['envelope_path']==str(new)
s.shutdown();print('PASS: altered cached beta -> zero HTTP calls; valid resume preserves old warrant and three new cells use new envelope')
