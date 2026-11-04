import http.server,json,subprocess,sys,threading
from pathlib import Path
P=Path(__file__).resolve().parent
class H(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  assert self.path=='/completion';self.server.payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  self.send_response(200);self.end_headers()
  for x in ({'content':'ZX-'},{'content':'742-'},{'content':'B'},{'content':'','timings':{'predicted_n':3,'prompt_n':2}}):self.wfile.write(('data: '+json.dumps(x)+'\n\n').encode());self.wfile.flush()
 def log_message(self,*args):pass
server=http.server.HTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.handle_request);thread.start()
try:
 req={'token_ids':[1,2],'max_tokens':24,'seed':0,'effective_config':{'server_url':'http://127.0.0.1:'+str(server.server_port)}}
 p=subprocess.run([sys.executable,str(P/'server_adapter.py')],input=json.dumps(req),text=True,capture_output=True,check=True);r=json.loads(p.stdout)
 assert r['output']=='ZX-742-B' and r['ttft_ms'] is not None and r['tpot_ms'] is not None and r['server_timings']['prompt_n']==2 and server.payload['prompt']==[1,2] and server.payload['n_predict']==24
 print('loopback adapter token IDs, streaming output and timing scopes: PASS')
finally:thread.join();server.server_close()

# Offline runner regression: mock the monitored adapter and evidence hook, not inference.
def test_versioned_runner():
 import contextlib,gzip,hashlib,io,runpy,tempfile,types
 from unittest.mock import patch
 def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
 with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/rope-ctx-assessment') as tmp:
  d=Path(tmp); ids=[1,2]; raw=json.dumps(ids).encode(); (d/'ids.gz').write_bytes(gzip.compress(raw))
  binary=d/'server';binary.write_bytes(b'binary');patchfile=d/'patch';patchfile.write_bytes(b'patch');tokenizer=d/'tokenizer';tokenizer.write_bytes(b'tokenizer')
  proof=d/'proof.json';proof.write_text(json.dumps({'candidate_tokenizer':str(tokenizer),'candidate_tokenizer_sha256':digest(tokenizer),'passed':True,'model_sha256':'model','tokenizer_sha256':'tokenizer'}))
  build=d/'build.json';build.write_text(json.dumps({'source_commit':'c72ec82f5417bb2937310326120f149b665e8400','candidate_binary_sha256':digest(binary),'candidate_patch_sha256':digest(patchfile)}))
  receipt=d/'dense.json';receipt.write_text(json.dumps({'arm':'dense','owner_nonce':'n','candidate_binary_sha256':digest(binary),'server_url':'http://127.0.0.1:1','pid':1,'start_ticks':1}))
  manifest=d/'manifest.json';manifest.write_text(json.dumps({'model_sha256':'model','tokenizer_sha256':'tokenizer','rows':[{'id':'item','nominal':2,'token_ids':str(d/'ids.gz'),'token_ids_sha256':hashlib.sha256(raw).hexdigest(),'prompt_n':2,'max_output_tokens':1,'expected':'answer'}]}))
  binding=d/'binding.json';binding.write_text(json.dumps({'reviewed':True,'model_sha256':'model','effective_config':{'server_url':'http://127.0.0.1:1','speculation':False},'source_commit':'c72ec82f5417bb2937310326120f149b665e8400','native_evidence_ready':True,'declaration_reviewed':True,'candidate_tokenizer_proof':str(proof),'candidate_tokenizer_proof_sha256':digest(proof),'server_receipt_dir':str(d),'owner_nonce':'n','candidate_binary_sha256':digest(binary),'candidate_patch_path':str(patchfile),'candidate_patch_sha256':digest(patchfile),'candidate_build_manifest':str(build),'candidate_build_manifest_sha256':digest(build),'candidate_binary':str(binary),'candidate_build_root':str(d),'device_topology':'cpu','kv_dtype':'bf16','context_config':{'n':2},'batch_config':{'n':1},'supported_arms':['dense'],'adapter_argv':['fake']}))
  for count,expected in [(2,'pass'),(1,'invalid')]:
   captured={};out=d/f'{count}.json'
   def emit(record,manifest_path,output_path,producer_path=None): captured.update(record=record,path=producer_path,sha=digest(producer_path))
   def monitor_run(*args): return ({'out':json.dumps({'output':'answer','server_timings':{'prompt_n':count}})},0,{'errors':[]})
   argv=['runner_v2.py','--manifest',str(manifest),'--binding',str(binding),'--id','item','--length','2','--arm','dense','--phase','quality','--output',str(out)]
   with patch.dict(sys.modules,{'monitor':types.SimpleNamespace(run=monitor_run),'native_evidence':types.SimpleNamespace(emit=emit)}),patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(P/'runner_v2.py'),run_name='__main__')
   assert captured['record']['status']==expected and captured['record']['request']['token_ids']==ids
   assert captured['path'].resolve()==(P/'runner_v2.py').resolve() and captured['sha']==digest(P/'runner_v2.py')

if __name__=='__main__':
 test_versioned_runner()
 print('versioned producer and served prompt count guard: PASS')
