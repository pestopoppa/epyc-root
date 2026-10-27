import json, threading, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from live_audit import ServerRenderer,validate_fixtures,validate_verdict
try: validate_fixtures([])
except ValueError: pass
else: raise AssertionError('empty fixture set accepted')
assert not validate_verdict({}) and not validate_verdict({'P1':True,'P2':True})
assert validate_verdict({'P1':True,'P2':True,'P3':True})
seen=[]
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  assert self.path=='/apply-template'
  d=json.loads(self.rfile.read(int(self.headers['Content-Length']))); seen.append(d)
  if len(seen)==1: payload={'prompt':'actual schema prompt'}; status=200
  elif len(seen)==2: payload={'error':'bad'}; status=200
  else: payload={'error':'bad request'}; status=400
  b=json.dumps(payload).encode(); self.send_response(status); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
 def log_message(self,*args): pass
s=HTTPServer(('127.0.0.1',0),Handler); t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
try:
 e=ServerRenderer('http://127.0.0.1:'+str(s.server_port),'')
 m=[{'role':'assistant','content':'','generated':'raw','generated_json':'raw2','tool_calls':[]}]
 assert e(m,tools=[{'type':'function'}])=='actual schema prompt'
 assert seen[0]=={'messages':[{'role':'assistant','content':'','tool_calls':[]}], 'add_generation_prompt':True, 'chat_template_kwargs':{'enable_thinking':False},'tools':[{'type':'function'}]}
 for error in (ValueError,urllib.error.HTTPError):
  try: e(m,add_generation_prompt=False)
  except error: pass
  else: raise AssertionError('bad response accepted')
 assert seen[1]['add_generation_prompt'] is False
finally: s.shutdown();s.server_close();t.join()
print('adapter mock PASS: request schema, response schema, invalid response and HTTP failure')
