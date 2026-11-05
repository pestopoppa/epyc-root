import hashlib,json,os,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
if Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE']):
 raise SystemExit('stop/deadline before result')
o=Path(sys.argv[1]); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'schema':'kpf60.checked-fixture.v1','status':'PASS','smoke':bool(sys.argv[2]),'source_sha256':sha(D/'checked_counter.hpp'),'fixture_sha256':sha(D/'test_checked_counter.cpp'),'binary_sha256':sha(o/'test_checked_counter'),'binary_size_bytes':(o/'test_checked_counter').stat().st_size,'compile_log_sha256':sha(o/'compile.log'),'test_log_sha256':sha(o/'test.log'),'scope':'isolated F16 row-major arithmetic fixture only; no native cache, model, transfer, integration, or calibration'}
target=Path(sys.argv[2]) if sys.argv[2] else o/'RESULT.json'
t=target.with_suffix('.tmp');t.write_text(json.dumps(r,sort_keys=True)+'\n');os.replace(t,target)
