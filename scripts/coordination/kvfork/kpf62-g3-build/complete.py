import hashlib,json,pathlib,subprocess,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf62-g3-build-20261104')
try:
 r=json.loads((D/'out/RESULT.json').read_text()); assert r['schema']=='kpf62.g3-build.v1' and r['status']=='BUILT' and r['source_commit']=='3ec14227a0e293bfc223c9026ed761ea3bdda9bb'
 subprocess.run(['python3',str(D/'check.py')],check=True,stdout=subprocess.DEVNULL)
 assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in r['files'].items())
except (OSError,KeyError,ValueError,AssertionError,subprocess.CalledProcessError):sys.exit(1)
