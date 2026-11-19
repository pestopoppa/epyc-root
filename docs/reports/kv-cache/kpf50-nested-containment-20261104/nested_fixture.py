"""Bounded own-child control; not a native profiling runner."""
import ctypes
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1] / 'kpf50-parent-death-20261104'

def birth(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
    except FileNotFoundError:
        return None

def children():
    return {int(x) for x in Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()}

def main():
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(36,1,0,0,0): raise OSError(ctypes.get_errno(),'subreaper')
    if children(): raise RuntimeError('fixture must start child-free')
    with tempfile.TemporaryDirectory() as td:
        sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        sock.settimeout(8); path=str(Path(td)/'ready.sock'); sock.bind(path); sock.listen(1)
        command=('import os,socket,sys,time\n'
                 'p=os.fork()\n'
                 'if p == 0:\n'
                 ' s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n'
                 ' s.connect(sys.argv[1]);s.sendall(str(os.getpid()).encode());s.close()\n'
                 'time.sleep(30)\n')
        proc=subprocess.Popen([sys.executable,'-B',str(ROOT/'outer.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        captured={proc.pid:birth(proc.pid)}
        try:
            config={'argv':[sys.executable,'-c',command,path], 'directory':td,
                    'window':'full-a','run_id':'nested-control','timeout_s':30}
            proc.stdin.write(json.dumps(config)+'\n');proc.stdin.flush()
            supervisor=json.loads(proc.stdout.readline()); root=json.loads(proc.stdout.readline())
            if supervisor.get('event')!='supervisor-started' or root.get('event')!='started':raise RuntimeError('missing start receipts')
            captured[supervisor['pid']]=supervisor['birth_ticks'];captured[root['pid']]=root['birth_ticks']
            conn,_=sock.accept()
            with conn: nested=int(conn.recv(64).decode())
            nested_birth=birth(nested)
            if nested_birth is None:raise RuntimeError('nested identity missing')
            captured[nested]=nested_birth
            proc.stdin.write('{"command":"stop"}\n');proc.stdin.flush()
            stdout,stderr=proc.communicate(timeout=8)
            events=[json.loads(line) for line in stdout.splitlines()]
            finish=[x for x in events if x.get('event')=='finished']
            if len(finish)!=1 or finish[0].get('normal') is not False:raise RuntimeError('missing interrupted finish')
            row=finish[0].get('cleanup',{}).get('captured',[])
            # Receipt schema is validated via its actual captured PID/birth entries.
            if not any(x.get('pid')==nested and x.get('birth_ticks')==nested_birth and x.get('reaped') for x in row):
                raise RuntimeError('nested adopted child not proven reaped')
            if birth(nested) is not None or proc.returncode==0:raise RuntimeError('nested survived or false success')
            print('nested adopted and reaped; interrupted outcome')
        finally:
            sock.close()
            if proc.poll() is None:
                if birth(proc.pid)!=captured[proc.pid]:raise RuntimeError('outer identity changed')
                proc.kill();proc.wait(timeout=5)
            # Any surviving descendants are owned by this isolated subreaper.
            for pid in list(children()):
                b=birth(pid)
                if pid not in captured or captured[pid]!=b:raise RuntimeError('unidentified adopted child; refusing signal')
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
                os.waitpid(pid,0)

if __name__=='__main__':main()
