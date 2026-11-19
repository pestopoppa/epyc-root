import hashlib,json,os,subprocess,sys
from pathlib import Path
B=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]); mode=sys.argv[3]
cache=(B/'CMakeCache.txt').read_text(); assert 'GGML_HIP:BOOL=ON' in cache and 'gfx90a' in cache and '-fsanitize=address' in cache
names=['libggml-base.so'] if mode=='smoke' else ['tts-server','libggml.so','libggml-base.so','libggml-cpu.so','libggml-hip.so']
files={}
for name in names:
 p=(B/name).resolve(); assert p.is_file() and p.is_relative_to(B)
 symbols=subprocess.check_output(['/usr/bin/nm','-D',str(p)],text=True)
 assert '__asan_' in symbols, f'missing ASan marker: {p}'
 files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
if mode=='full':
 for name in names:
  p=(B/name).resolve(); data=subprocess.check_output(['/usr/bin/ldd',str(p)],text=True,env={**os.environ,'LD_LIBRARY_PATH':str(B)+':/opt/rocm/lib'})
  assert 'not found' not in data
  for line in data.splitlines():
   if 'libggml' in line and '=>' in line:
    target=Path(line.split('=>',1)[1].strip().split()[0]).resolve(); assert target.is_relative_to(B),line
result={'bytes':sum((B/name).resolve().stat().st_size for name in names),'schema':'kvu11c.host-asan-build.v1','status':'BUILT' if mode=='full' else 'SMOKE','files':files,'scope':'host ASan instrumentation; no device ASan, model, GPU execution or inference'}
out.parent.mkdir(parents=True,exist_ok=True)
import time
assert not Path(os.environ['FILLER_STOPFILE']).exists() and time.time()<int(os.environ['FILLER_DEADLINE']), 'STOP/deadline before receipt'
with out.open('x') as f: json.dump(result,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
