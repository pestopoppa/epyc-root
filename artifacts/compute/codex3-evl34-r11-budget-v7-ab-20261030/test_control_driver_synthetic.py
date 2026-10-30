"""Control driver with an owned synthetic server; no model or pilot exposure."""
import hashlib,json,os,subprocess,sys,time,socket
from pathlib import Path
import control_driver as d
from server_peer import birth
REAL_POPEN=subprocess.Popen;REAL_RUN=subprocess.run
ROOT=Path(__file__).parent
SCRIPT='''from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nimport json,threading,time\nlock=threading.Lock();roots=0;barrier=threading.Barrier(2,timeout=4);repl=0\nclass H(BaseHTTPRequestHandler):\n def log_message(self,*a):pass\n def do_GET(self):\n  self.send_response(200);self.end_headers();self.wfile.write(b'{"status":"ok"}')\n def do_POST(self):\n  global roots,repl\n  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));stream=body.get('stream',False);redel=bool(body.get('tools')) or stream\n  if redel and stream:\n   barrier.wait();common={'id':'fixture','created':0,'model':'pinned','object':'chat.completion.chunk'}\n   chunks=[common|{'choices':[{'index':0,'delta':{'role':'assistant','content':'fixture helper answer'},'finish_reason':None}]},common|{'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]},common|{'choices':[],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}];wire=(''.join('data: '+json.dumps(x)+'\\n\\n' for x in chunks)+'data: [DONE]\\n\\n').encode();content='text/event-stream'\n  elif redel:\n   with lock:roots+=1;ordinal=roots\n   if ordinal==1:msg={'role':'assistant','content':None,'tool_calls':[{'id':f'call{i}','type':'function','function':{'name':'delegate','arguments':json.dumps({'instructions':f'fixture helper {i}'})}} for i in (1,2)]};finish='tool_calls'\n   elif ordinal==2:msg={'role':'assistant','content':None,'tool_calls':[{'id':'wait','type':'function','function':{'name':'wait','arguments':json.dumps({'until':'all'})}}]};finish='tool_calls'\n   else:msg={'role':'assistant','content':'fixture final'};finish='stop'\n   wire=json.dumps({'id':'fixture','created':0,'model':'pinned','object':'chat.completion','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}).encode();content='application/json'\n  else:\n   with lock:repl+=1;ordinal=repl\n   msg="```python\\nFINAL('fixture answer')\\n```" if ordinal==1 else 'fixture answer'\n   wire=json.dumps({'choices':[{'message':{'content':msg}}],'usage':{'prompt_tokens':10,'completion_tokens':2}}).encode();content='application/json'\n  time.sleep(.1);self.send_response(200);self.send_header('content-type',content);self.end_headers();self.wfile.write(wire);self.wfile.flush()\ns=ThreadingHTTPServer(('127.0.0.1',int(__import__('sys').argv[1])),H);s.serve_forever()'''
def main():
 r=ROOT/('driver-synthetic-'+str(os.getpid()));r.mkdir()
 for name in ('repl_live_entry.py','redel_live_entry.py','CONTROL-PRIVATE.json'):(r/name).symlink_to(ROOT/name)
 (r/'SOURCE.sha256').write_text('synthetic-only\n');(r/'ROOT-REVIEW.json').write_text(json.dumps({'decision':'approved','source_manifest_sha256':hashlib.sha256((r/'SOURCE.sha256').read_bytes()).hexdigest()}))
 probe=socket.socket();probe.bind(('127.0.0.1',0));d.PORT=probe.getsockname()[1];probe.close()
 d.D=r;d.MODEL=r/'fake-model';d.BIN=r/'fake-bin';d.MODEL.write_text('fixture');d.BIN.write_text('fixture');d.END=time.monotonic()+50;d.headroom=lambda _:True
 original_sha=d.sha
 def sha(p):
  if p==d.MODEL:return '061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a'
  if p==d.BIN:return '2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b'
  return original_sha(p)
 d.sha=sha
 def popen(cmd,*args,**kwargs):
  if cmd[0]==str(d.BIN):return REAL_POPEN([sys.executable,'-c',SCRIPT,str(d.PORT)],*args,**kwargs)
  return REAL_POPEN(cmd,*args,**kwargs)
 def run(cmd,*args,**kwargs):
  if cmd[0] in ('sha256sum','/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh','/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/verify-source.sh'):return subprocess.CompletedProcess(cmd,0)
  return REAL_RUN(cmd,*args,**kwargs)
 d.subprocess.Popen=popen;d.subprocess.run=run
 d.witness=lambda pid,b:{'identity':(pid,b),'gpu_own_pid_vram_bytes':1,'fixture_only':True} if birth(pid)==b else (_ for _ in ()).throw(RuntimeError('identity changed'))
 os.environ['EVL34_OTHER_RESERVED_BYTES']='0'
 try:d.main()
 finally:d.subprocess.Popen=REAL_POPEN;d.subprocess.run=REAL_RUN
 attempts=list(r.glob('control-attempt-*'));assert len(attempts)==1
 assert json.loads((attempts[0]/'COMPLETE.json').read_text())['server_drained'] is True
 ends=list((r/'control-journal').glob('*.end'));assert len(ends)==2
 for path in ends:
  native=json.loads(path.read_text())['native'];assert native['status']=='complete' and native['server_usage'] is not None
 print('control driver both actual entries, journal, captured synthetic server and cleanup passed; GPU witness synthetic')
if __name__=='__main__':main()
