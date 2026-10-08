"""Prepared SC55 existing-native-carrier capture. Off-host source conformance only."""
import hashlib,importlib.metadata,json,os,platform,subprocess,sys
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
CARRIER_PIN='4c0c653baf1654c8c25c66433cf39c8faefd8e52'
UFH13_PIN='1bace97dc655ab5896291b4571781e53b821d9a3'
CONTEXT_PIN='82dc0a8f0e4c9359a6733dd0241ba9caea94f785'
CARRIER_READS=('scripts/ci/native_conformance.py','scripts/vidya/adapters/ci_conformance.py',
 'scripts/vidya/claim_tuple.py','scripts/vidya/lattice.py','scripts/vidya/frames.py','scripts/vidya/canonical.py')
PACKAGES={'colorama':'0.4.6','iniconfig':'2.3.0','packaging':'26.0','pluggy':'1.6.0','Pygments':'2.20.0','pytest':'9.0.3','PyYAML':'6.0.3'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args]).decode().strip()
def once(path,obj):
 with open(path,'x') as stream:json.dump(obj,stream,sort_keys=True,indent=2);stream.write('\n')
def hashes(paths):return {str(path.resolve()):sha(path.read_bytes()) for path in paths}
def main():
 workspace=Path(os.environ['GITHUB_WORKSPACE']).resolve();recipe=workspace/'recipe';carrier=workspace/'carrier';research=workspace/'ufh13-research'
 bound_map=Path(os.environ['SC54_BOUND_SOURCE_MAP']).resolve(strict=True)
 if bound_map.is_symlink() or not bound_map.is_file():raise RuntimeError('bound source-map is not a regular file')
 run=Path(os.environ['RUNNER_TEMP'])/'sc54-quality-native';result=run/'result';result.mkdir(parents=True,exist_ok=True)
 status=run/'status.json';state={'state':'preflight','exit_code':None,'control_count':102,'no_models_or_inference':True}
 try:
  pins={'recipe':git(recipe,'rev-parse','HEAD'),'carrier':git(carrier,'rev-parse','HEAD')}
  if pins!={'recipe':os.environ['GITHUB_SHA'],'carrier':CARRIER_PIN}:raise RuntimeError('checkout pin mismatch')
  subprocess.check_call(['git','-C',str(recipe),'merge-base','--is-ancestor',CONTEXT_PIN,pins['recipe']])
  if git(research,'rev-parse','HEAD')!=UFH13_PIN or os.environ.get('UFH13_RESEARCH_ROOT')!=str(research):raise RuntimeError('UFH13 explicit checkout/env mismatch')
  manifest=json.loads(bound_map.read_text());cases=json.loads((HERE/'expected-cases.json').read_text())
  if manifest.get('root_source_commit')!=pins['recipe'] or manifest.get('root_context_base')!=CONTEXT_PIN:raise RuntimeError('bound source-map commit mismatch')
  if manifest.get('expected_case_rows')!=102 or len(cases)!=102:raise RuntimeError('prospective exact case inventory mismatch')
  if len({(c['classname'],c['name']) for c in cases})!=len(cases):raise RuntimeError('duplicate expected native case identity')
  paths=[HERE/'source-map.json',bound_map,HERE/'expected-cases.json',HERE/'bootstrap.py',HERE/'capture.py',HERE/'bind_source_map.py',HERE/'requirements.txt',recipe/'.github/workflows/sc54-quality-native.yml']
  for row in manifest['files']:
   base={'recipe':recipe,'ufh13-research':research}[row['repo']];path=base/row['path']
   raw=path.read_bytes()
   if sha(raw)!=row['sha256'] or len(raw)!=row['size']:raise RuntimeError('source closure changed: '+row['path'])
   paths.append(path)
  for name in CARRIER_READS:
   path=carrier/name
   if path.read_bytes()!=subprocess.check_output(['git','-C',str(carrier),'show',CARRIER_PIN+':'+name]):raise RuntimeError('carrier modified')
   paths.append(path)
  installed={name:importlib.metadata.version(name) for name in PACKAGES}
  if installed!=PACKAGES:raise RuntimeError('locked package identities differ')
  envfile=result/'environment.json';once(envfile,{'python':sys.version,'platform':platform.platform(),'packages':installed,'runner':os.environ['RUNNER_OS'],'execution':'SC54 synthetic source conformance only'})
  freeze=result/'freeze.txt';freeze.write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze','--all']))
  paths += [envfile,freeze,result/'dependency-install.log']
  before=hashes(paths);once(run/'source-readset.json',{'kind':'pre-execution original input hashes','sha256_by_absolute_path':before})
  junit=result/'original-junit.xml';native=result/'native'
  if junit.exists() or native.exists():raise RuntimeError('refuse output reuse')
  producer=[sys.executable,str(carrier/'scripts/ci/native_conformance.py'),'--cwd',str(recipe),'--junit',str(junit),'--output',str(native),
   '--repo','recipe='+str(recipe),'--repo','carrier='+str(carrier),'--repo','ufh13-research='+str(research)]
  for path in paths:producer+=['--read-path',str(path)]
  for selection in ('recipe:tests/vidya/test_sc54_qwen4exp_quality_adapter.py','recipe:tests/vidya/test_ingest_sources.py'):producer+=['--select',selection]
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
  exact=expected==actual==xml and sum(expected.values())==102
  conformant=rc==0 and exact and counts['collected']==102 and counts['executed']==102 and all(counts[key]==0 for key in ('skipped','failure','error')) and receipt['fixture_execution_conformant'] is True
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
