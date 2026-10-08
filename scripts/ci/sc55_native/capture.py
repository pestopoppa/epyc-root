"""Prepared SC55 existing-native-carrier capture. Off-host source conformance only."""
import hashlib,importlib.metadata,json,os,platform,subprocess,sys
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
CARRIER_PIN='4c0c653baf1654c8c25c66433cf39c8faefd8e52'
CONTEXT_PIN='ab53a8e9322ae430007a2131f2d425d1641ee05c'
RESEARCH_PIN='c7229b461bdf06e82e12f721aad35bbd81c4dced'
CARRIER_READS=('scripts/ci/native_conformance.py','scripts/vidya/adapters/ci_conformance.py',
 'scripts/vidya/claim_tuple.py','scripts/vidya/lattice.py','scripts/vidya/frames.py','scripts/vidya/canonical.py')
PACKAGES={'colorama':'0.4.6','iniconfig':'2.3.0','packaging':'26.0','pluggy':'1.6.0','Pygments':'2.20.0','pytest':'9.0.3'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args]).decode().strip()
def once(path,obj):
 with open(path,'x') as stream:json.dump(obj,stream,sort_keys=True,indent=2);stream.write('\n')
def hashes(paths):return {str(path.resolve()):sha(path.read_bytes()) for path in paths}
def main():
 workspace=Path(os.environ['GITHUB_WORKSPACE']).resolve();recipe=workspace/'recipe';carrier=workspace/'carrier';research=workspace/'research'
 run=Path(os.environ['RUNNER_TEMP'])/'sc55-native';result=run/'result';result.mkdir(parents=True,exist_ok=True)
 status=run/'status.json';state={'state':'preflight','exit_code':None,'control_count':43,'no_models_or_inference':True}
 try:
  pins={'recipe':git(recipe,'rev-parse','HEAD'),'carrier':git(carrier,'rev-parse','HEAD'),'research':git(research,'rev-parse','HEAD')}
  if pins!={'recipe':os.environ['GITHUB_SHA'],'carrier':CARRIER_PIN,'research':RESEARCH_PIN}:raise RuntimeError('checkout pin mismatch')
  subprocess.check_call(['git','-C',str(recipe),'merge-base','--is-ancestor',CONTEXT_PIN,pins['recipe']])
  manifest=json.loads((HERE/'source-map.json').read_text());cases=json.loads((HERE/'expected-cases.json').read_text())
  paths=[HERE/'source-map.json',HERE/'expected-cases.json',HERE/'bootstrap.py',HERE/'capture.py',HERE/'requirements.txt',recipe/'.github/workflows/sc55-native.yml']
  for row in manifest['files']:
   base={'recipe':recipe,'research':research}[row['repo']];path=base/row['path']
   raw=path.read_bytes()
   if sha(raw)!=row['sha256'] or len(raw)!=row['size']:raise RuntimeError('source closure changed: '+row['path'])
   paths.append(path)
  for name in CARRIER_READS:
   path=carrier/name
   if path.read_bytes()!=subprocess.check_output(['git','-C',str(carrier),'show',CARRIER_PIN+':'+name]):raise RuntimeError('carrier modified')
   paths.append(path)
  installed={name:importlib.metadata.version(name) for name in PACKAGES}
  if installed!=PACKAGES:raise RuntimeError('locked package identities differ')
  envfile=result/'environment.json';once(envfile,{'python':sys.version,'platform':platform.platform(),'packages':installed,'runner':os.environ['RUNNER_OS'],'execution':'SC55 synthetic source conformance only'})
  freeze=result/'freeze.txt';freeze.write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze','--all']))
  paths += [envfile,freeze,result/'dependency-install.log']
  before=hashes(paths);once(run/'source-readset.json',{'kind':'pre-execution original input hashes','sha256_by_absolute_path':before})
  junit=result/'original-junit.xml';native=result/'native'
  if junit.exists() or native.exists():raise RuntimeError('refuse output reuse')
  producer=[sys.executable,str(carrier/'scripts/ci/native_conformance.py'),'--cwd',str(recipe),'--junit',str(junit),'--output',str(native),
   '--repo','recipe='+str(recipe),'--repo','research='+str(research),'--repo','carrier='+str(carrier)]
  for path in paths:producer+=['--read-path',str(path)]
  for selection in ('research:scripts/kernel_rnd/autokernel/loop/test_graph_profile_capture.py','research:scripts/kernel_rnd/autokernel/loop/test_graph_profile_reader.py','recipe:tests/test_graph_profile_measurement.py'):producer+=['--select',selection]
  env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0');env.pop('PYTHONPATH',None)
  rc=subprocess.call(producer+['--',sys.executable,'-I',str(HERE/'bootstrap.py'),str(junit)],cwd=recipe,env=env)
  receipt=json.loads((native/'receipt.json').read_text());summary=receipt['summary']
  if summary is None:
   if before!=hashes(paths):raise RuntimeError('source/readset changed during event')
   once(result/'ungraded-null.json',{'fixture_execution_conformant':receipt['fixture_execution_conformant'],
    'diagnostic':receipt.get('diagnostic'),'native_summary':None,'shared_grade':None,'reason':'native summary unavailable; no tuple or grade projected'})
   state.update(state='ungraded_null',exit_code=rc or 1,fixture_execution_conformant=receipt['fixture_execution_conformant'],
    diagnostic=receipt.get('diagnostic'),native_summary=None,shared_grade=None,source_readset_unchanged=True)
   return state['exit_code']
  counts=summary['counts']
  expected=Counter((case['classname'],case['name']) for case in cases)
  actual=Counter((case['classname'],case['name']) for case in summary['cases'])
  xml=Counter((case.get('classname',''),case.get('name','')) for case in ET.parse(junit).getroot().iter('testcase'))
  exact=expected==actual==xml and sum(expected.values())==43
  conformant=rc==0 and exact and counts['collected']==43 and counts['executed']==43 and all(counts[key]==0 for key in ('skipped','failure','error')) and receipt['fixture_execution_conformant'] is True
  if before!=hashes(paths):raise RuntimeError('source/readset changed during event')
  # Existing carrier adapter and shared grader only; immutable native originals stay untouched.
  native_before=hashes([p for p in result.rglob('*') if p.is_file()])
  sys.path[:0]=[str(carrier),str(carrier/'scripts/vidya')]
  from scripts.vidya.adapters.ci_conformance import native_rows,project_ci_conformance
  from claim_tuple import grade
  projected=native_rows(native/'receipt.json')
  if len(projected)!=1:raise RuntimeError('native receipt not exactly one existing CI row')
  q,t,reasons=grade(project_ci_conformance(projected[0]))
  if native_before!=hashes([p for p in result.rglob('*') if p.is_file()]):raise RuntimeError('analysis changed native originals')
  once(result/'shared-grade.json',{'Q':q,'T':t,'reasons':reasons,'new_grade_authored':False,'original_before':native_before,'original_after':native_before})
  passed=conformant and (q,t)==('Judged','Located');state.update(state='passed' if passed else 'failed',exit_code=0 if passed else (rc or 1),exact_case_multiset=exact,native_counts=counts,source_readset_unchanged=True)
  return state['exit_code']
 except Exception as exc:
  state.update(state='failed',exit_code=1,error=type(exc).__name__+': '+str(exc));return 1
 finally:status.write_text(json.dumps(state,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':raise SystemExit(main())
