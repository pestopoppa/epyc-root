import hashlib,json,os,sys
from pathlib import Path
R=Path(__file__).resolve().parent
try:
 d=json.loads(Path(os.environ['CANCEL_RESULT']).read_text()); assert d['schema']=='kpf18.cancel-order.v1' and d['status']=='PASS' and len(d['controls'])==7
 assert d['sources']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in R.glob('*.py')}
 assert not (R/'STOP').exists()
except (OSError,ValueError,KeyError,TypeError,AssertionError):sys.exit(1)
