import hashlib,json,pathlib,subprocess,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf50-hip-build-20261104')
try:
 r=json.loads((D/'out/RESULT.json').read_text());assert r['schema']=='kpf50.hip-build.v1' and r['status']=='BUILT' and r['source_commit']=='1e8a6d5da9836a27e8f1d2010a02e6cebd95abdc'
 subprocess.run(['python3',str(D/'check.py')],check=True,stdout=subprocess.DEVNULL)
 assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in r['files'].items())
except (OSError,KeyError,ValueError,AssertionError,subprocess.CalledProcessError):sys.exit(1)
