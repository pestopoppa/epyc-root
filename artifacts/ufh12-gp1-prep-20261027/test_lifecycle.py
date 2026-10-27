import os, socket, subprocess, tempfile
from pathlib import Path
from unittest.mock import patch
import run_real
base=Path(run_real.B)
with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
real_popen=subprocess.Popen; real_read=Path.read_text; captured=[]
def spawn(argv,**kw):
 p=real_popen([os.environ['VIRTUAL_PY'],str(base/'fake_server.py'),str(port)],**kw); captured.append(p); return p
def read(path,*args,**kwargs):
 if str(path).startswith('/proc/') and str(path).endswith('/maps'):
  return '0000-0001 r-xp 0 00:00 0 '+str(run_real.BIN/'libggml.so')+'\n'
 return real_read(path,*args,**kwargs)
def linkage(*args,**kwargs): return subprocess.CompletedProcess(args,0)
with tempfile.TemporaryDirectory(dir=base) as tmp:
 with patch.object(run_real,'B',Path(tmp)), patch.object(run_real,'PORT',str(port)), patch.object(run_real.subprocess,'Popen',side_effect=spawn), patch.object(run_real.subprocess,'run',side_effect=linkage), patch.object(Path,'read_text',read), patch.object(os,'sched_getaffinity',return_value=set(range(72,96))): run_real.main()
 assert captured and captured[0].poll() is not None
 assert (Path(tmp)/'COMPLETE.json').exists() and (Path(tmp)/'out/belief/repl_embedder_parity.beliefs.jsonl').exists()
 print('PASS real lifecycle fake HTTP: startup, health, provenance seam, 64x4, native writer, cleanup/reap, completion')
