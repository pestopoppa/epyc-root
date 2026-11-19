import hashlib,json,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
for p,h in json.loads((D/'inputs.json').read_text()).items():
 if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h: raise SystemExit('input changed: '+p)
for p,r in json.loads((D/'toolchain-identity.json').read_text())['files'].items():
 if str(pathlib.Path(p).resolve())!=r['realpath'] or hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=r['sha256']: raise SystemExit('toolchain changed: '+p)
