from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,os,subprocess,sys,threading,time
D=Path(__file__).resolve().parent
class H(BaseHTTPRequestHandler):
 def do_POST(self):
  self.rfile.read(int(self.headers['content-length']));b=json.dumps({'choices':[{'message':{'content':'2'},'finish_reason':'stop'}],'model':'fixture'}).encode();self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*_):pass
s=ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=s.serve_forever,daemon=True).start()
out=D/'fixture-no-usage';out.mkdir(exist_ok=True);ep=D/'fixture-envelope.json';ep.write_text(json.dumps({'gpu_resident':True,'model_sha256':'fixture','source_catalog_sha256':'fixture'}))
env=dict(os.environ,PRB_ENVELOPE=str(ep),PRB_QUALIFIED_EXECUTION='1',PRB_SMOKE='1',PRB_OUTPUT=str(out),PRB_ENDPOINT=f'http://127.0.0.1:{s.server_port}',FILLER_STOPFILE=str(D/'fixture-stop-usage'),FILLER_DEADLINE=str(int(time.time()+30)))
p=subprocess.run([sys.executable,'-B',str(D/'campaign.py')],env=env,timeout=15,capture_output=True,text=True);s.shutdown();assert p.returncode==0
for arm in ('estimate','baseline','static'):
 r=json.loads((out/'0000'/f'{arm}.json').read_text());assert r['status']=='unknown_error' and 'usage unavailable' in r['error'] and 'result' not in r and r['http'][0]['status']==200
assert json.loads((out/'0000'/'tale.json').read_text())['status']=='unknown_dependency'
print('missing native usage -> UNKNOWN, raw response retained, no inferred cost PASS')
