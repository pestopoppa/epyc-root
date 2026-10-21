"""Hosted-only original native carrier; unbound future enrollment refuses."""
import pathlib,json,hashlib,os,sys,subprocess,xml.etree.ElementTree as ET
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2];CARRIER=pathlib.Path(os.environ['GITHUB_WORKSPACE'])/'carrier';OUT=pathlib.Path(os.environ['RUNNER_TEMP'])/'nib83-native-result'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,v):
 with (OUT/name).open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
OUT.mkdir(mode=0o700,exist_ok=True);sm=json.loads((HERE/'source-map.json').read_text());receipt=None
try:
 if sm['enrollment_root'].startswith('__'):raise RuntimeError('prospective enrollment is unbound')
 if os.environ['GITHUB_EVENT_NAME']!='push' or os.environ['GITHUB_RUN_ATTEMPT']!='1' or os.environ['GITHUB_REF']!='refs/heads/'+sm['branch']:raise RuntimeError('fresh OWN push only')
 def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
 if git(ROOT,'rev-parse','HEAD')!=os.environ['GITHUB_SHA'] or git(ROOT,'rev-parse','HEAD^')!=sm['enrollment_root']:raise RuntimeError('source parent/event mismatch')
 if git(CARRIER,'rev-parse','HEAD')!=sm['carrier_root']:raise RuntimeError('carrier pin mismatch')
 paths=[ROOT/x['path'] for x in sm['payload_readset']]+[HERE/'source-map.json']+[CARRIER/x for x in sm['carrier_readset']]+[ROOT/x['path'] for x in sm['enrollment_readset']]
 for x in sm['payload_readset']+sm['enrollment_readset']:
  if sha(ROOT/x['path'])!=x['sha256']:raise RuntimeError('source readset mismatch')
 before={str(p):sha(p) for p in paths};junit=OUT/'original-junit.xml';native=OUT/'native';command=[sys.executable,str(HERE/'run_controls.py'),str(junit)]
 argv=[sys.executable,str(CARRIER/'scripts/ci/native_conformance.py'),'--cwd',str(ROOT),'--junit',str(junit),'--output',str(native),'--repo','root_recipe='+str(ROOT),'--repo','carrier='+str(CARRIER)]
 for p in paths:argv+=['--read-path',str(p)]
 argv+=['--select','scripts/ci/nib83_native/test_histogram_controls.py','--',*command]
 write('execution-request.json',{'argv':argv,'source_before':before,'enrollment':sm['enrollment_root'],'event_source':os.environ['GITHUB_SHA'],'case_count_expectation':7,'synthetic_only':True})
 r=subprocess.run(argv,cwd=ROOT,capture_output=True);(OUT/'carrier.stdout').write_bytes(r.stdout);(OUT/'carrier.stderr').write_bytes(r.stderr);write('carrier-exit.json',{'exit':r.returncode})
 receipt_path=native/'receipt.json';receipt=json.loads(receipt_path.read_text());after={str(p):sha(p) for p in paths};write('pre-grade-custody.json',{'source_before':before,'source_after':after,'receipt':receipt})
 sys.path.insert(0,str(CARRIER));sys.path.insert(0,str(CARRIER/'scripts/vidya'))
 from scripts.vidya.adapters.ci_conformance import native_rows,project_ci_conformance
 from claim_tuple import grade
 grades=[]
 for row in native_rows(receipt_path):
  c=project_ci_conformance(row);q,t,reasons=grade(c);grades.append({'measurement_id':c.measurement_id,'Q':q,'T':t,'reasons':reasons})
 write('shared-grade.json',{'grades':grades,'native_value_preserved':receipt.get('fixture_execution_conformant'),'new_grade_authored':False})
 expected=json.loads((HERE/'expected-cases.json').read_text())['case_identities'];actual=[{'classname':x.get('classname'),'name':x.get('name')} for x in ET.parse(junit).iter('testcase')]
 if before!=after or sorted(actual,key=lambda x:x['name'])!=expected or r.returncode!=0:raise RuntimeError('source stability/native count or command failed')
 write('status.json',{'state':'captured','native_value':receipt.get('fixture_execution_conformant'),'actual_cases':len(actual),'synthetic_only':True})
except Exception as e:
 write('error-custody.json',{'error':str(e),'receipt_original':receipt,'synthetic_only':True,'real_histogram_created':False});raise
