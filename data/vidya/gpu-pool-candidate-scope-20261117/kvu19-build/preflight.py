import hashlib,json,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
s=json.loads((D/'pins.json').read_text())
r=Path('/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-root-code')
assert subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()=='1ea56a495413be89ea9bcc89407f547a47f3e9f2'
assert not subprocess.check_output(['git','-C',str(r),'status','--porcelain'],text=True).strip()
for path,want in s['files'].items():
 assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==want,path
print(json.dumps({'status':'pins-verified','files':len(s['files']),'gpu_launched':False}))
