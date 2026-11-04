"""Model-free active SIGTERM: registered private child must be reaped."""
import hashlib, json, os, pathlib, signal, socket, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent

class ActiveStopTest(unittest.TestCase):
    def test_signal_during_server_lifetime_cleans_captured_process(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); sockpath=str(root/'ready.sock')
            listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); listener.bind(sockpath); listener.listen(1); listener.settimeout(8)
            server=root/'server'; server.write_text('#!/usr/bin/env python3\nimport signal,socket,sys\ns=socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.sendall(b"ready"); s.close()\nwhile True: signal.pause()\n'); server.chmod(0o755)
            backend=root/'libhip'; backend.write_bytes(b'G3_FATTN_DISPATCH_V3')
            model=root/'model'; model.write_bytes(b'x'); st=model.stat()
            sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            pre=root/'preflight.json'; pre.write_text(json.dumps({'model':{'path':str(model),'sha256':'a'*64,'stat':dict(dev=st.st_dev,ino=st.st_ino,size=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns)}}))
            layers=root/'layers.json'; layers.write_text(json.dumps({'provenance':{'path':str(model),'size_bytes':st.st_size},'verify_attention_layer_ids':[3]}))
            config={'output':str(root/'out'),'server':str(server),'backend':str(backend),'backend_sha256':sha(backend),'model':str(model),'model_sha256':'a'*64,'model_preflight':str(pre),'model_preflight_sha256':sha(pre),'layer_manifest':str(layers),'layer_manifest_sha256':sha(layers),'trace_marker':'G3_FATTN_DISPATCH_V3','requests':[{'n_predict':1}],'timeout_seconds':60,'url':'http://127.0.0.1:1/completion','rocm_card':'card0','server_args':[sockpath]}
            config_path=root/'config.json'; config_path.write_text(json.dumps(config))
            driver=('import sys,types,time; sys.path.insert(0,sys.argv[1]); import diagnostic_runner as d; '
                    'from pathlib import Path; c=sys.argv[2]; '
                    'd.resolve_build_binding=lambda x: ({},Path(x["server"]),Path(x["backend"]),Path(x["server"]).parent); '
                    'd.gpu_sample=lambda: {"observation_start":time.time(),"observation_end":time.time(),"monotonic_start":time.monotonic(),"monotonic_end":time.monotonic()}; '
                    'd.subprocess.run=lambda *a,**k: types.SimpleNamespace(returncode=0); '
                    'sys.argv=["runner",c]; sys.exit(d.main())')
            env=os.environ.copy(); env.update(FILLER_STOPFILE=str(root/'STOP'), FILLER_DEADLINE=str(int(__import__('time').time())+120), FILLER_PIDFILE=str(root/'pids'))
            runner=subprocess.Popen([sys.executable,'-c',driver,str(HERE),str(config_path)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                conn,_=listener.accept(); self.assertEqual(conn.recv(20),b'ready'); conn.close()
                os.kill(runner.pid,signal.SIGTERM)
                _,err=runner.communicate(timeout=15)
                self.assertEqual(runner.returncode,75,err.decode())
                pid=int((root/'pids').read_text().strip())
                with self.assertRaises(ProcessLookupError): os.kill(pid,0)
                result=json.loads((root/'out/result.json').read_text())
                self.assertEqual(result['status'],'partial'); self.assertTrue(result['process_group_drained'])
            finally:
                listener.close()
                if runner.poll() is None:
                    runner.kill(); runner.wait(timeout=5)

if __name__=='__main__': unittest.main()
