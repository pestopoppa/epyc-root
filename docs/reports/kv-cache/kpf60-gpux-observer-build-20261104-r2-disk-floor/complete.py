import hashlib,json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 r=json.loads((D/'out/RESULT.json').read_text());assert r['schema']=='kpf60.selection-build.v1' and r['status']=='BUILT' and r['source_commit']=='8952a0f693fb923918157eb25117641b74766230'
 subprocess.run(['python3',str(D/'check.py')],check=True,stdout=subprocess.DEVNULL)
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in r['files'].items())
except (OSError,KeyError,ValueError,AssertionError,subprocess.CalledProcessError):sys.exit(1)
