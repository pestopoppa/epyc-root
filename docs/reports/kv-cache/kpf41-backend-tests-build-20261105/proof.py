import hashlib,json,os,pathlib,time
D=pathlib.Path(__file__).resolve().parent; B=D/'build/bin';O=D/'out';names=['test-backend-ops','libggml.so','libggml-base.so','libggml-cpu.so','libggml-hip.so']
if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=int(os.environ['FILLER_DEADLINE']):raise SystemExit(75)
files={}
for n in names:
 p=B/n
 if not p.is_file():raise RuntimeError('missing '+n)
 files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
r={'status':'BUILD_PASS','binary_size_bytes':(B/names[0]).stat().st_size,'source_commit':'15caecbbf4cb27452dbd87fa1a68a0e75098388e','files':files,'scope':'backend test executable and own ggml linkage build only; no GPU execution or parity'}
p=O/'RESULT.json';q=O/'RESULT.tmp'
if p.exists() or q.exists():raise RuntimeError('output collision')
q.write_text(json.dumps(r,indent=2)+'\n')
if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=int(os.environ['FILLER_DEADLINE']):raise SystemExit(75)
os.replace(q,p)
