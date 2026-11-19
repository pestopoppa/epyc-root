import os,sys,json,hashlib,pathlib,subprocess,time,fcntl,pty,termios,select,threading,http.server
from control import stopped,cleanup
D=pathlib.Path(__file__).resolve().parent
M=json.loads((D/'manifest.json').read_text()); B=pathlib.Path(M['custody'])/'bin'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity():
 for name,digest in M['files'].items():assert sha(pathlib.Path(name))==digest,name
 for name,digest in M['inputs'].items():assert sha(D/name)==digest,name
identity()
lock=open(D/'run.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
requested=set()
for item in os.environ['FILLER_CPUS'].split(','):
 a,_,b=item.partition('-');requested.update(range(int(a),int(b or a)+1))
cpus=sorted(requested & os.sched_getaffinity(0))[:4]; assert len(cpus)==4
os.sched_setaffinity(0,cpus)
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(B);env['LC_ALL']='C.UTF-8'
records=[]
def failure(kind,value,tb):
 result={'status':'UNKNOWN','rc':1,'reason':str(value),'records':records,'inference_executed':False,'model_loaded':False,'manifest':M}
 path=D/'partials.jsonl'
 with path.open('a') as f:f.write(json.dumps(result)+'\n');f.flush();os.fsync(f.fileno())
 sys.__excepthook__(kind,value,tb)
sys.excepthook=failure
def execute(cmd,name,input_data=b'',terminal=False,timeout=10,map_required=False):
 if stopped():raise RuntimeError('stopped')
 logpath=D/(name+'.log'); master=slave=None
 def setup():
  os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
 if terminal:
  master,slave=pty.openpty()
  p=subprocess.Popen(cmd,stdin=slave,stdout=slave,stderr=slave,env=env,preexec_fn=setup)
  os.close(slave);slave=None
 else:
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  # Keep stdin open until the owned CLI's loader mappings are verified.
 fd=master if terminal else p.stdout.fileno();os.set_blocking(fd,False)
 output=b'';sent=False;start=time.monotonic();mapped=[]
 try:
  if map_required:
   while time.monotonic()-start<3 and p.poll() is None:
    if stopped():raise RuntimeError('stopped before linkage sample')
    text=pathlib.Path('/proc')/str(p.pid)/'maps'
    lines=text.read_text().splitlines()
    relevant=[]
    for line in lines:
     fields=line.split(None,5)
     if len(fields)<6:continue
     path=pathlib.Path(fields[5])
     if not path.name.startswith(('libllama','libggml','libmtmd')):continue
     resolved=path.resolve()
     assert resolved.parent==B.resolve(),('foreign ggml/llama mapping',line)
     assert str(resolved) in M['files'] and sha(resolved)==M['files'][str(resolved)],line
     assert int(fields[4])==resolved.stat().st_ino,('inode mismatch',line)
     relevant.append(line)
    names=[pathlib.Path(line.split(None,5)[5]).name for line in relevant]
    if all(any(n.startswith(prefix) for n in names) for prefix in ['libllama-cli-impl.so','libllama.so','libggml.so','libggml-base.so']):
     mapped=relevant;break
    time.sleep(.01)
   assert mapped,'UNKNOWN: no complete owned CLI runtime linkage sample'
  if not terminal:p.stdin.write(input_data);p.stdin.close()
  while True:
   if stopped() or time.monotonic()-start>timeout:raise TimeoutError(name)
   if select.select([fd],[],[],.05)[0]:
    try:data=os.read(fd,65536)
    except (BlockingIOError,OSError):data=b''
    output+=data
    if len(output)>1048576:raise RuntimeError('output cap exceeded '+name)
   if terminal and not sent and b'READY' in output:
    os.write(master,input_data);sent=True
   if p.poll() is not None:
    while True:
     try:data=os.read(fd,65536)
     except (BlockingIOError,OSError):break
     if not data:break
     output+=data
     if len(output)>1048576:raise RuntimeError("output cap exceeded "+name)
    break
  rc=p.wait()
 finally:
  if p.poll() is None:cleanup(p,2)
  if master is not None:os.close(master)
  logpath.write_bytes(output)
  records.append({'case':name,'argv':cmd,'input_hex':input_data.hex(),'pty':terminal,'runtime_maps':mapped,'rc':p.poll(),'elapsed_s':time.monotonic()-start,'limit_s':timeout,'log_sha256':sha(logpath),'pid':p.pid,'cleanup':'owned captured process group cleaned if still running; process reaped'})
 return rc,output
rc,out=execute(['/bin/bash',str(D/'verify_ggml_linkage.sh'),str(B/'llama-cli'),str(B)],'verify-ggml-linkage',timeout=10)
assert rc==0,out
class Mock(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.server.requests.append(('GET',self.path))
  responses={'/health':{'status':'ok'},'/v1/models':{'data':[{'id':'mock-a'},{'id':'mock-b'}]},'/props':{}}
  body=json.dumps(responses.get(self.path,{'error':'unexpected route'})).encode()
  self.send_response(200 if self.path in responses else 400);self.send_header('Content-Length',str(len(body)));self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
 def do_POST(self):
  self.server.requests.append(('POST',self.path));self.send_response(500);self.end_headers()
 def log_message(self,*args):pass
# Bound loopback socket is the port claim. There is no upstream or inference endpoint.
server=http.server.HTTPServer(('127.0.0.1',0),Mock);server.timeout=.1;server.requests=[]
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);thread.start()
try:
 rc,out=execute([str(B/'llama-cli'),'--server-base',f'http://127.0.0.1:{server.server_port}','--simple-io'],'cli-model-selection-eof',timeout=10,map_required=True)
 assert rc==1,(rc,out)
 assert b'Select model by number' in out,out
 assert ('GET','/v1/models') in server.requests,server.requests
 assert not any(method=='POST' for method,path in server.requests),server.requests
 records[-1]['requests']=server.requests
finally:
 server.shutdown();server.server_close();thread.join(2);assert not thread.is_alive()
smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
if not smoke:
 cmd=[M['compiler'],'-std=c++17',str(D/'harness.cpp'),'-L'+str(B),'-Wl,-rpath,'+str(B),'-Wl,--no-as-needed','-lllama-common','-o',str(D/'console-harness')]
 rc,out=execute(cmd,'compile-harness',timeout=60);assert rc==0,out
 for mode,terminal,cases in [('simple',False,[('eof',b'',b''),('blank',b'\n',b'0a'),('slash',b'/\n',b'0a'),('text',b'hello\n',b'68656c6c6f0a')]),('advanced',True,[('eof',b'\x04',b''),('blank',b'\n',b'0a'),('slash',b'/\n',b'0a'),('text',b'hello\n',b'68656c6c6f0a')])]:
  for name,data,expected in cases:
   rc,out=execute([str(D/'console-harness'),mode],mode+'-'+name,data,terminal)
   assert rc==0 and b'RESULT more=0 hex='+expected+b'\r' in out.replace(b'\n',b'\r'),out
   assert str(B/'libllama-common.so').encode() in out,out
   records[-1]['expected_hex']=expected.decode()
identity()
result={'status':'COMPLETE','rc':0,'smoke':smoke,'cpus':cpus,'records':records,'inference_executed':False,'model_loaded':False,'manifest':M,'scope':'Linux model-selection EOF via actual CLI plus linked console reader semantics; no chat/mtmd/Windows admission claim'}
path=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(D/'results.jsonl')))
with path.open('a') as f:f.write(json.dumps(result)+'\n');f.flush();os.fsync(f.fileno())
if not smoke:(D/'COMPLETE').write_text('bounded native model-free behavior checks complete\n')
