#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent
out=Path(sys.argv[1]); binary=out/'p3batch-clock'
strings=subprocess.check_output(['/usr/bin/strings',str(binary)])
if b'P3_CLOCK phase=' not in strings or b'P3_CLOCK_ERROR' not in strings:raise SystemExit('clock instrument missing')
env=dict(os.environ,LD_LIBRARY_PATH=str(D/'bin'))
link=subprocess.run(['/usr/bin/ldd',str(binary)],capture_output=True,text=True,env=env,check=True)
(out/'linkage.txt').write_text(link.stdout)
for lib in ('libllama.so','libggml.so','libggml-base.so'):
 if not any(lib in line and str(D/'bin') in line for line in link.stdout.splitlines()):raise SystemExit('nonlocal linkage: '+lib)
rec={'schema':'kvu19b.profiler-build.v1','status':'built','smoke':bool(sys.argv[2]),'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((D/'p3batch-clock.cpp').read_bytes()).hexdigest(),'linkage_sha256':hashlib.sha256((out/'linkage.txt').read_bytes()).hexdigest(),'source_commit':'1bceceb0514d423ad220888313eafcddc30e485e','cpu_affinity':sorted(os.sched_getaffinity(0)),'compiler':'/usr/bin/g++','predecessor_assets_sha256':hashlib.sha256((D/'predecessor-assets.json').read_bytes()).hexdigest(),'scope':'build only, no model, profiler calibration, or attribution'}
target=Path(sys.argv[2]) if sys.argv[2] else out/'RESULT.json'
target.write_text(json.dumps(rec,sort_keys=True)+'\n')
