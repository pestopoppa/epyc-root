import json, os, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path
from server_control import request_owned, stop_owned

FAKE = r'''import http.server,json,sys,time
class H(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def do_POST(self):
  self.rfile.read(int(self.headers['Content-Length']))
  if self.path == '/block':
   print('ENTERED',flush=True); time.sleep(30); return
  out=json.dumps({'ok':True}).encode(); self.send_response(200); self.send_header('Content-Length',str(len(out)));self.end_headers();self.wfile.write(out)
s=http.server.HTTPServer(('127.0.0.1',0),H);print(s.server_port,flush=True);s.serve_forever()
'''

class Tests(unittest.TestCase):
 def test_interrupted_request_terminates_and_reaps_owned_server(self):
  child=subprocess.Popen([sys.executable,'-u','-c',FAKE],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
  try:
   port=int(child.stdout.readline()); url=f'http://127.0.0.1:{port}/block'
   with tempfile.TemporaryDirectory() as d:
    stop=Path(d)/'stop'; out=[]
    thread=threading.Thread(target=lambda:out.append(request_owned(child,url,{},stop_file=str(stop),deadline=time.monotonic()+8,endpoint_owned=lambda c,u:c is child and u==url)))
    thread.start(); self.assertEqual(child.stdout.readline().strip(),'ENTERED'); stop.touch(); thread.join(4)
    self.assertFalse(thread.is_alive()); self.assertEqual(out[0]['state'],'unknown'); self.assertTrue(out[0]['cleanup']['server_reaped']); self.assertFalse(out[0]['cleanup']['descendants_proven_absent']); self.assertIsNotNone(child.poll()); self.assertFalse(Path(f'/proc/{child.pid}').exists())
  finally:
   stop_owned(child); child.stdout.close()
 def test_unowned_endpoint_is_never_contacted(self):
  child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
  try:
   with self.assertRaises(ValueError): request_owned(child,'http://127.0.0.1:1/',{},stop_file='/tmp/absent-a2-stop',deadline=time.monotonic()+5,endpoint_owned=lambda *_:False)
   self.assertIsNone(child.poll())
  finally: stop_owned(child)
 def test_normal_result_retains_server_for_owner(self):
  child=subprocess.Popen([sys.executable,'-u','-c',FAKE],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
  try:
   port=int(child.stdout.readline()); url=f'http://127.0.0.1:{port}/ok'
   with tempfile.TemporaryDirectory() as d:
    out=request_owned(child,url,{},stop_file=str(Path(d)/'stop'),deadline=time.monotonic()+5,endpoint_owned=lambda c,u:c is child and u==url)
    self.assertEqual(out['state'],'complete');self.assertIsNone(child.poll())
  finally: stop_owned(child);child.stdout.close()
if __name__=='__main__':unittest.main()
