import hashlib,json,os,sys,tempfile,time
from pathlib import Path
import direct_diagnostic as d
D=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp); receipt=p/'enrollment.json'; identity=p/'identity.json'; out=p/'run'
 receipt.write_text(json.dumps({'approved':True,'manifest_sha256':hashlib.sha256((D/'source-manifest.sha256').read_bytes()).hexdigest(),'profile':'ct21-direct-exploratory-v1','source_sha256':hashlib.sha256((D/'direct_diagnostic.py').read_bytes()).hexdigest(),'profile_sha256':hashlib.sha256((D/'DIAGNOSTIC-PROFILE.md').read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256((D/'fixtures.json').read_bytes()).hexdigest()}))
 identity.write_text(json.dumps({'source_commit':'a'*40,'binary_version':'1','template_sha256':'b'*64,'model_path':'/model'}))
 os.environ.update(WINDOW_CONFIRMED='1',CT21_ENROLLMENT_RECEIPT=str(receipt),CT21_RUNTIME_IDENTITY=str(identity),CT21_SERVER_PID='1',CT21_SERVER_UID='2',CT21_SERVER_BIRTH='3',CT21_MONITOR_PID='1',CT21_MONITOR_UID='2',CT21_MONITOR_BIRTH='3',FILLER_DEADLINE=str(int(time.time())+60),FILLER_STOPFILE=str(p/'stop'))
 d.identity=lambda pid:(2,3)
 class Reply:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self):return b'{"choices":[{"message":{"content":"D|A"},"finish_reason":"stop"}]}'
 calls=[]
 def fake(req,timeout): calls.append(json.loads(req.data));return Reply()
 d.urllib.request.urlopen=fake
 old=sys.argv;sys.argv=['direct_diagnostic','--url','http://example.invalid','--output',str(out)]
 try:d.main()
 finally:sys.argv=old
 assert len(calls)==80 and all(x['cache_prompt'] is False for x in calls)
 assert len(list(out.glob('*.raw.json')))==80 and len((out/'results.jsonl').read_text().splitlines())==80
 from adapters import chat_template_ab as reader
 import claim_tuple
 native=reader.rows_for_run(out);assert len(native)==4
 assert all(claim_tuple.grade(reader.project(n))[:2]==('Judged','Located') for n in native)
 class Unobservable(Reply):
  def read(self):return b'{"choices":[{"message":{"content":"I|brief:check|to:worker_math"},"finish_reason":"stop"}]}'
 count=[0]
 def one_unobservable(req,timeout):
  count[0]+=1
  return Unobservable() if count[0]==1 else Reply()
 d.urllib.request.urlopen=one_unobservable
 out2=p/'unobservable';old=sys.argv;sys.argv=['direct_diagnostic','--url','http://example.invalid','--output',str(out2)]
 try:
  try:d.main()
  except SystemExit as exc: assert exc.code==2
  else: raise AssertionError('unobservable response returned success')
 finally:sys.argv=old
 summary=json.loads((out2/'summary.json').read_text())
 assert summary['status']=='INCONCLUSIVE' and sum(x['status']=='refused' for x in summary['results'].values())==1
 assert len(list(out2.glob('*.raw.json')))==80 and len((out2/'results.jsonl').read_text().splitlines())==80
 assert not (out2/'belief_measurements.jsonl').exists()
 print('PASS synthetic 80-call no-network execution, raw capture, four actual family observations')
