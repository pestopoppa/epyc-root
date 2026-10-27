import json, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import numpy as np
import collect
items=json.loads((collect.REF/'items.json').read_text())
ref=np.load(collect.REF/'vec-st-fp32-full.npz')
vec=np.concatenate([ref['docs'],ref['queries']])
expected=['title: none | text: '+x for x in items['doc_texts']]
expected += [('task: code retrieval | query: ' if q['code_intent'] else 'task: search result | query: ')+q['text'] for q in items['queries']]
state={'count':0,'mode':'pass'}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  i=state['count']; state['count']+=1
  assert self.path=='/v1/embeddings' and data['input']==expected[i*4:i*4+4]
  rows=[{'index':n,'embedding':vec[4*i+n].tolist()} for n in range(4)]
  if state['mode']=='missing': rows.pop()
  if state['mode']=='duplicate': rows[0]['index']=1
  if state['mode']=='dims': rows[0]['embedding'].pop()
  if state['mode']=='nonfinite': rows[0]['embedding'][0]=float('nan')
  body=json.dumps({'data':rows}).encode(); self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler); thread=threading.Thread(target=server.serve_forever); thread.start()
meta={'st-fp32-full':{'runtime':'sentence-transformers/transformers/torch-cpu','argv':['recorded','reference'],'versions':{'torch':'2.14.1+cpu','transformers':'5.20.1','sentence_transformers':'6.1.0'},'flash_attn_requested':'n/a','flash_attn_resolved':'n/a'},'gguf-bf16':{'runtime':'fixture','argv':['fixture','np4'],'binary_sha256':'a'*64,'flash_attn_requested':'auto','flash_attn_resolved':'off'}}
try:
 with tempfile.TemporaryDirectory(dir=collect.BASE) as tmp:
  original=collect.gate._spec
  with patch.object(collect.gate,"_spec",side_effect=lambda lane: replace(original(lane),doc_prompt="BAD PREFIX ") if lane=="st-fp32-full" else original(lane)):
   try: collect.run("http://127.0.0.1:"+str(server.server_port),Path(tmp)/"prefix",meta)
   except ValueError as e: assert "identity/prefix" in str(e); print("prefix mismatch refused before HTTP")
   else: raise AssertionError("wrong prefix accepted")
  for mode in ['pass','missing','duplicate','dims','nonfinite']:
   state.update(count=0,mode=mode); out=Path(tmp)/mode
   try: collect.run('http://127.0.0.1:'+str(server.server_port),out,meta)
   except Exception as e:
    if mode=='pass': raise
    print(mode,'refused',type(e).__name__,str(e)[:150])
   else:
    assert mode=='pass' and state['count']==64 and (out/'RESULT.json').is_file() and (out/'belief/repl_embedder_parity.beliefs.jsonl').is_file()
    print('PASS: 64 exact lists of four, all prefixes, native compare and belief write')
finally:
 server.shutdown(); server.server_close(); thread.join()
