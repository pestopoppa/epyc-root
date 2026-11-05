import hashlib,json,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 r=json.loads(Path(os.environ['SUPERVISOR_RESULT']).read_text())
 assert r['schema']=='epyc.kpf18.supervisor.v1' and r['status']=='PASS' and r['controls']==4
 assert r['sources']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.py')}
 assert not (D/'STOP').exists()
except (OSError,ValueError,KeyError,TypeError,AssertionError):sys.exit(1)
