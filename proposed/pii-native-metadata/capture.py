"""Hosted original PII controls, unchanged native carrier and shared grade."""
import importlib.metadata,json,os,subprocess,sys,sysconfig
from pathlib import Path
W=Path(os.environ['GITHUB_WORKSPACE']);T=Path(os.environ['RUNNER_TEMP']);R=W/'recipe/proposed/pii-native-metadata';O=T/'pii-native-result';O.mkdir();F=T/'pii-native-tests';policy=T/'pii-policy'
if sys.version_info[:3]!=(3,13,15):raise RuntimeError('pinned Python differs')
if os.environ.get('GITHUB_EVENT_NAME')!='push' or os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('GITHUB_REF')!='refs/heads/codex/pii-job-metadata-repair-source-20261021':raise RuntimeError('fresh original push attempt1 required')
context=O/'runtime.json';context.write_text(json.dumps({'python':sys.version,'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},'scope':'synthetic staged source controls only; not privacy or promotion authority'},indent=2)+'\n')
reads=[context,Path(sys.executable).resolve(),F/'test_pii_native_metadata.py']
for root in (R,W/'baseline/scripts',W/'carrier/scripts',policy/'scripts'):
 reads += [p for p in root.rglob('*') if p.is_file() and (p.suffix in ('.py','.sh','.json','.jsonl','.txt') or p.name=='requirements.txt')]
reads += [W/'job-baseline/scripts/hooks/pii_precommit.sh',W/'recipe/scripts/hooks/pii_precommit.sh',W/'recipe/research/fixtures/pii_native_ci_metadata_controls.jsonl',W/'recipe/research/fixtures/pii_native_ci_metadata_tests.py',W/'recipe/.github/workflows/pii-native-metadata-source.yml',W/'enrollment/scripts/vidya/adapters/README.md',W/'enrollment/handoffs/active/vidya-belief-substrate-program.md']
for d in importlib.metadata.distributions():
 for name in d.files or ():
  p=Path(d.locate_file(name)).resolve()
  if p.is_file() and (p.suffix in ('.py','.so') or p.name in ('METADATA','RECORD','WHEEL')):reads.append(p)
stdlib=Path(sysconfig.get_path('stdlib'));reads += [p for pattern in ('*.py','*.so') for p in stdlib.rglob(pattern) if 'site-packages' not in p.parts and p.is_file() and not p.is_symlink()]
cmd=[sys.executable,'-B',str(W/'carrier/scripts/ci/native_conformance.py'),'--cwd',str(F),'--junit',str(O/'original-junit.xml'),'--output',str(O/'native')]
for name in ('recipe','baseline','enrollment','carrier','job-baseline'):cmd+=['--repo',name+'='+str(W/name)]
for p in dict.fromkeys(reads):cmd+=['--read-path',str(p)]
for name in json.loads((R/'case-selection.json').read_bytes()):cmd+=['--select',name]
cmd+=['--',sys.executable,'-B','-m','pytest','--noconftest','-o','addopts=','-p','no:cacheprovider','-q','-o','junit_logging=all','-o','junit_log_passing_tests=true','--basetemp='+str(O/'staged-originals'),'--junitxml='+str(O/'original-junit.xml'),str(F/'test_pii_native_metadata.py')]
r=subprocess.run(cmd,capture_output=True);(O/'outer.stdout.raw').write_bytes(r.stdout);(O/'outer.stderr.raw').write_bytes(r.stderr);(O/'outer.argv-exit.json').write_text(json.dumps({'argv':cmd,'exit':r.returncode},indent=2)+'\n')
sys.path.insert(0,str(W/'carrier/scripts/vidya'));sys.path.insert(0,str(W/'carrier'))
from scripts.vidya.adapters.ci_conformance import native_rows,project_ci_conformance
from claim_tuple import grade
g=[{'Q':q,'T':t,'reasons':why} for row in native_rows(O/'native/receipt.json') for q,t,why in [grade(project_ci_conformance(row))]];(O/'shared-grade.json').write_text(json.dumps(g,indent=2)+'\n')
raise SystemExit(r.returncode)
