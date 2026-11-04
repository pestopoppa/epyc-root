import hashlib,json,os,select,secrets,subprocess,sys,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvu/find-slot-native-v1')
B=D/'fixture'
BIN='078cafd6e72d274f40d82c50012b0170f80d2f0d8e72f5574cca6f88e7de7d7d'
ROW='kvu-kpf131-old-native-findslot-20261104'
assert hashlib.sha256((D/'map_identity.py').read_bytes()).hexdigest()=='90aab639b65530823fc087e0aae1499f02c6a655ad8aca5a522d2f197e58ae1c'
assert hashlib.sha256((D/'pins.json').read_bytes()).hexdigest()=='d4447b28bd561d77bba6f94b8c0e905e8af59edc53917f7acc7d93b834bf9ef8'
from map_identity import verify_snapshot
PINS=json.loads((D/'pins.json').read_text())
NEEDED={p for p in PINS if Path(p).name in {'libllama.so.0.0.10348','libggml-base.so.0.16.0','libggml.so.0.16.0','libggml-cpu.so.0.16.0','libggml-hip.so.0.16.0'}}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check(cond,msg):
 if not cond:raise ValueError(msg)
def line(proc):
 check(bool(select.select([proc.stdout],[],[],20)[0]),'fixture timeout')
 return proc.stdout.readline().strip()
def capture(proc):
 ex=os.stat(f'/proc/{proc.pid}/exe'); actual=B.stat()
 check((ex.st_dev,ex.st_ino)==(actual.st_dev,actual.st_ino) and sha(B)==BIN,'executable mismatch')
 lines=Path(f'/proc/{proc.pid}/maps').read_text().splitlines()
 maps=verify_snapshot(lines,PINS)
 check(set(maps)==NEEDED,'mapped DSO set mismatch: '+str(set(maps)^NEEDED))
 return {p:{'device_inode':list(maps[p]),'sha256':PINS[p]} for p in sorted(maps)}
def case(arm):
 env=dict(os.environ);env['LD_LIBRARY_PATH']='/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin'
 proc=subprocess.Popen([str(B),arm],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
 try:
  check(line(proc)=='READY '+str(proc.pid),'missing ready')
  before=capture(proc)
  proc.stdin.write('g\n');proc.stdin.flush()
  answer=line(proc)
  check(answer==('RESULT PASS 2 3' if arm=='honest' else 'RESULT DETECTED 0 1'),'unexpected native answer '+answer)
  after=capture(proc);check(before==after,'DSO mapping changed')
  proc.stdin.write('q\n');proc.stdin.flush()
  out,err=proc.communicate(timeout=20)
  check(proc.returncode==0 and not out,'native exit or extra output')
  return {'arm':arm,'pid':proc.pid,'answer':answer,'before':before,'after':after,'stderr':err}
 finally:
  if proc.poll() is None:proc.kill();proc.wait()

def main():
 check(sha(B)==BIN,'executable digest drift')
 check(sha(D/'build-manifest.json')=='9237c44d954878d660b97298c89675a8d3ad26478401b974db8b4a9ee7d212ab','build manifest mismatch')
 manifest=json.loads((D/'build-manifest.json').read_text())
 check(manifest['source_commit']=='a1f0c8cf9bd7102415a72577474f307b8ba94db9' and manifest['binary_sha256']==BIN and sha(D/'fixture.cpp')==manifest['source_sha256'],'build/source binding mismatch')
 dry=os.getenv('FILLER_DRYRUN_RESULT_PATH'); out=Path(dry) if dry else D/'out/RESULT.json'
 nonce=None
 if not dry:
  check(os.getenv('FILLER_ID')==ROW,'wrong row attempt')
  out.unlink(missing_ok=True); nonce=secrets.token_hex(24)
  (D/'out').mkdir(parents=True,exist_ok=True)
  (D/'out/attempt.json').write_text(json.dumps({'row_id':ROW,'nonce':nonce,'result_path':str(out)}))
 records=[case('honest'),case('skip_apply')]
 result={'schema':'kpf131.native-findslot.v1','row_id':ROW,'case_count':2,'status':'FIXTURE_PASS','executable_sha256':BIN,'build_manifest_sha256':sha(D/'build-manifest.json'),'records':records,'smoke':bool(dry),'attempt_nonce':nonce,'timestamp_ns':time.time_ns(),'scope':'model-free source-header fixture; no physical layout or historical control verdict'}
 out.parent.mkdir(parents=True,exist_ok=True); temp=out.with_name(out.name+'.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');os.replace(temp,out)
 print('FIXTURE_PASS',flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:print('INVALID:',repr(e),file=sys.stderr);sys.exit(1)
