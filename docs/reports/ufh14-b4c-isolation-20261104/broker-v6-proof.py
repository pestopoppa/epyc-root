import os,sys,json,pathlib,socket,array,threading,subprocess,importlib.util,errno,asyncio
BASE=pathlib.Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes'); P=BASE/'cpu-isolate-v6'; SRC=BASE/'gs-app-impact-source'
REAL=socket.socket

def child(fd,port):
    root=P/'private';root.mkdir(exist_ok=True)
    os.environ.update({'PYTHONDONTWRITEBYTECODE':'1','ORCHESTRATOR_PATHS_PROJECT_ROOT':str(root),'ORCHESTRATOR_RUNTIME_FLAGS_PATH':str(root/'flags.json')})
    import ast
    tree=ast.parse((SRC/'src/config/models.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ServerURLsConfig')
    for n in cls.body:
        if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name):os.environ['ORCHESTRATOR_SERVER_URLS_'+n.target.id.upper()]=f'http://127.0.0.1:{port}'
    sys.path.insert(0,str(SRC))
    ctrl=REAL(fileno=fd);lock=threading.Lock()
    def request(addr):
        with lock:
            ctrl.setblocking(True);ctrl.send(json.dumps(addr).encode());data,anc,flags,_=ctrl.recvmsg(4096,socket.CMSG_SPACE(4))
        payload=json.loads(data)
        rights=[]
        for level,kind,b in anc:
            if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
                a=array.array('i');a.frombytes(b);rights.extend(a)
        if flags or len(rights)!=(1 if payload.get('ok') else 0):
            for x in rights:os.close(x)
            raise RuntimeError('malformed broker reply')
        if not payload.get('ok'):raise PermissionError(errno.EACCES,payload.get('error'))
        return rights[0]
    class BrokerSocket(REAL):
        def __init__(self,family=socket.AF_INET,type=socket.SOCK_STREAM,proto=0,fileno=None):
            if fileno is None and family in (socket.AF_INET,socket.AF_INET6):
                if family!=socket.AF_INET or type!=socket.SOCK_STREAM:raise PermissionError(errno.EACCES,'only IPv4 TCP brokered')
                super().__init__(family,type,proto,fileno=os.dup(ctrl.fileno()));self._pending=True
            else:super().__init__(family,type,proto,fileno=fileno);self._pending=False
        def connect(self,addr):
            if not self._pending:return super().connect(addr)
            newfd=request(addr)
            try:os.dup2(newfd,self.fileno())
            finally:os.close(newfd)
            self._pending=False;self.setblocking(False)
        def connect_ex(self,addr):
            try:self.connect(addr);return 0
            except OSError as e:return e.errno
    spec=importlib.util.spec_from_file_location('fence',SRC/'src/repl_environment/_fence_kernel_shim.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    arch,pair,nrs=m._K_SECCOMP_ARCH['x86_64'];metadata=(42,90,91,92,93,94,132,235,260,268,280,188,189,190,197,198,199,165,166,155,304,452,62,200,234,440,448)
    m._K_SECCOMP_ARCH=dict(m._K_SECCOMP_ARCH,x86_64=(arch,pair,nrs+metadata))
    handled=((1<<15)-1)&~((1<<0)|(1<<2)|(1<<3));m._k_landlock_restrict([(str(root),m._K_FULL)],[],{'handled':handled,'full':handled,'file':(1<<1)|(1<<14)},netdeny=True,scope=True);m._k_seccomp_netdeny()
    def raw_connect():
        import ctypes
        rc=m._k_libc().syscall(42,ctrl.fileno(),0,0)
        if rc<0:raise OSError(ctypes.get_errno(),'raw connect syscall')
    checks={}
    for name,fn in {'outside_write':lambda:(P/'sentinel').write_text('BAD'),'outside_create':lambda:(P/'escape').write_text('BAD'),'outside_chmod':lambda:os.chmod(P/'sentinel',0o600),'raw_inet_socket':lambda:REAL(socket.AF_INET,socket.SOCK_STREAM),'raw_connect_on_inherited_channel':raw_connect,'outside_unlink':lambda:(P/'sentinel').unlink()}.items():
        try:fn()
        except OSError as e:
            assert e.errno in (errno.EACCES,errno.EPERM);checks[name]='denied'
        else:raise AssertionError(name)
    (root/'allowed').write_text('yes')
    for addr in [['127.0.0.1',8000],['localhost',port],['127.0.0.2',port],['::1',port],['::ffff:127.0.0.1',port],['192.0.2.1',port],['127.0.0.1',str(port)],['127.0.0.1',port,1],{},None]:
        try:os.close(request(addr))
        except PermissionError:pass
        else:raise AssertionError(addr)
    checks['broker_negative_cases']=10
    # Full pinned native ASGI app receives the request; real native route probes
    # owned HTTP backend through its unmodified httpx.AsyncClient implementation.
    socket.socket=BrokerSocket
    # All application and third-party imports occur after kernel enforcement
    # and successful outside-write/raw-network denial tests.
    import httpx
    from src.api import app
    from src.api.routes.health import _probe_backend
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://offline-api') as client:
            r=await client.get('/health');r.raise_for_status();body=r.json()
        probe=await _probe_backend(f'http://127.0.0.1:{port}')
        assert probe['ok'],probe
        # Native deployment priors still request source-defined ports; broker refuses them.
        assert body.get('backend_probes'),body
        return {'http_status':r.status_code,'native_health':body,'native_direct_probe':probe}
    result=asyncio.run(run())
    print(json.dumps({'checks':checks,'private_write':'allowed','native':result}))

def main():
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    hits=[];audit=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append({'path':self.path,'peer':self.client_address[0]});self.send_response(200);self.end_headers();self.wfile.write(b'{"status":"ok","offline_dummy":true}')
        def log_message(self,*args):pass
    backend=ThreadingHTTPServer(('127.0.0.1',0),Handler);port=backend.server_port
    threading.Thread(target=backend.serve_forever,daemon=True).start()
    a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
    def broker():
        while True:
            try:data,anc,flags,_=a.recvmsg(4096,socket.CMSG_SPACE(64))
            except ConnectionResetError:break
            if not data:break
            rights=[]
            for level,kind,raw in anc:
                if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
                    f=array.array('i');f.frombytes(raw);rights+=f.tolist()
            for x in rights:os.close(x)
            try:
                req=json.loads(data);valid=(not flags and not anc and type(req) is list and len(req)==2 and type(req[0]) is str and req[0]=='127.0.0.1' and type(req[1]) is int and req[1]==port)
                if not valid:raise PermissionError('exact private IPv4 endpoint required')
                conn=REAL(socket.AF_INET,socket.SOCK_STREAM);conn.settimeout(2)
                try:
                    conn.connect(('127.0.0.1',port));a.sendmsg([b'{"ok":true}'],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[conn.fileno()]))])
                finally:conn.close()
                audit.append({'request':req,'allowed':True})
            except Exception as exc:
                audit.append({'request':locals().get('req'),'allowed':False,'reason':str(exc)});a.send(json.dumps({'ok':False,'error':str(exc)}).encode())
    t=threading.Thread(target=broker,daemon=True);t.start()
    sentinel=P/'sentinel';sentinel.write_text('unchanged');before=sentinel.stat().st_mode
    try:r=subprocess.run([sys.executable,__file__,'child',str(b.fileno()),str(port)],pass_fds=(b.fileno(),),capture_output=True,text=True,timeout=30)
    finally:b.close();backend.shutdown();backend.server_close()
    report={'schema':'epyc.offline-cpu-isolation.v6','inference':False,'production_endpoints_contacted':False,'backend_port':port,'child_returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'broker_audit':audit,'backend_hits':hits,'sentinel_unchanged':sentinel.read_text()=='unchanged' and sentinel.stat().st_mode==before,'escape_absent':not (P/'escape').exists(),'scope':'sandbox-before-application-import native ASGI /health plus native backend probe; no lifespan/model execution','sandbox_before_application_import':True,'deployment_ready':False,'limitations':['Full native health source stack-prior URLs are safely refused; private route configuration remains incomplete.','API ingress is in-process ASGI; backend leg uses real TCP HTTP.','No model, lifespan, REPL or inference execution.']}
    if r.returncode==0:report['child']=json.loads(r.stdout)
    (BASE/'cpu-isolate-v6-20261104.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'returncode':r.returncode,'stderr':r.stderr,'hits':len(hits),'audit':len(audit)}))
if __name__=='__main__':
    if len(sys.argv)>1:child(int(sys.argv[2]),int(sys.argv[3]))
    else:main()
