import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import numpy as np
r=Path('/mnt/raid0/llm/tmp/repl-emb-25-26-20261020/out25/gate-probe45')
items=json.loads((r/'items.json').read_text()); ref=np.load(r/'vec-st-fp32-full.npz'); vs=np.concatenate([ref['docs'],ref['queries']]); count=0
expected=['title: none | text: '+s for s in items['doc_texts']]+[('task: code retrieval | query: ' if q['code_intent'] else 'task: search result | query: ')+q['text'] for q in items['queries']]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
 def do_POST(self):
  global count
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  assert len(body['input'])==4 and body['input']==expected[count:count+4]
  data=[{'index':i,'embedding':vs[count+i].tolist()} for i in range(4)]; count+=4
  raw=json.dumps({'data':data}).encode(); self.send_response(200); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
print('llama_context: flash_attn    = auto',flush=True)
print('resolve_fused_ops: Flash Attention enabled',flush=True)
HTTPServer(('127.0.0.1',int(sys.argv[1])),Handler).serve_forever()
