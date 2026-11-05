import hashlib,json,os,signal,time,unittest
from pathlib import Path
from output_path import result_path
D=Path(__file__).resolve().parent
stopped=False
def stop(*_):
 global stopped
 stopped=True
signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
def guard():
 if stopped or Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE']): raise RuntimeError('STOP/deadline')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
guard()
for name,h in json.loads((D/'inputs.json').read_text()).items():
 if sha(name if name.startswith('/') else D/name)!=h: raise RuntimeError('source drift '+name)
import test_marks
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_marks))
guard()
if not r.wasSuccessful() or r.testsRun!=2: raise RuntimeError('controls failed')
p=result_path(D);p.parent.mkdir(parents=True,exist_ok=True)
if p.exists(): raise RuntimeError('refuse overwrite')
p.write_text(json.dumps({'status':'QUALIFIED_SYNTHETIC','progress':12,'tests':2,'mutations':12,'inputs_sha256':sha(D/'inputs.json'),'scope':'target mark parsing only; no GPU, target process alignment, drift, attribution or inference'})+'\n')
