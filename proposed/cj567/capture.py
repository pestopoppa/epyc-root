"""Hosted original synthetic source controls through unchanged carrier/shared grade."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
W = Path(os.environ['GITHUB_WORKSPACE'])
R = W/'recipe/proposed/cj567'
T = Path(os.environ['RUNNER_TEMP'])
F = T/'cj567-fixture'
O = T/'cj567-result'
O.mkdir()
M = json.loads((R/'source-map.json').read_bytes())
if sys.version_info[:3] != (3, 13, 15): raise RuntimeError('pinned Python differs')
if os.environ.get('GITHUB_EVENT_NAME') != 'push' or os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or os.environ.get('GITHUB_REF') != 'refs/heads/codex/cj567-source-native-20261021': raise RuntimeError('fresh original OWN push required')
context = O/'runtime.json'
context.write_text(json.dumps({'python':sys.version,'executable':sys.executable,'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},'scope':'source controls only; no model/server/judge/prior changes'},indent=2)+'\n')
reads = [context, Path(sys.executable).resolve()]
for repo in ('recipe','enrollment','carrier','app','research','official','nltk'):
    root = W/repo
    if repo == 'app': paths = [root/x['path'] for x in M['app_python_envelope']]
    elif repo == 'research': paths = [root/x['path'] for x in M['research_sources']]
    elif repo == 'enrollment': paths = [root/x for x in ('scripts/vidya/adapters/README.md','handoffs/active/vidya-belief-substrate-program.md')]
    elif repo == 'nltk': paths = [root/x['path'] for x in json.loads((R/'nltk-seed-lock.json').read_bytes())['archives']]
    elif repo == 'recipe': paths = [p for p in R.rglob('*') if p.is_file()] + [root/'.github/workflows/cj567-source-fixtures.yml']
    else: paths = [p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '.venv' not in p.parts and (p.suffix in ('.py','.json','.jsonl','.lock','.toml') or p.name == 'LICENSE')]
    reads += paths
reads += [p for p in F.iterdir() if p.is_file()]
reads += [W/'official/ifbench/.nltk_data'/p for p in json.loads((R/'nltk-seed-lock.json').read_bytes())['seed_files']]
for d in importlib.metadata.distributions():
    for name in d.files or ():
        p = Path(d.locate_file(name)).resolve()
        if p.is_file() and (p.suffix in ('.py','.so') or p.name in ('METADATA','RECORD','WHEEL')): reads.append(p)
stdlib = Path(sysconfig.get_path('stdlib'))
reads += [p for pattern in ('*.py','*.so') for p in stdlib.rglob(pattern) if 'site-packages' not in p.parts and p.is_file() and not p.is_symlink()]
command = [sys.executable,'-B',str(W/'carrier/scripts/ci/native_conformance.py'),'--cwd',str(F),'--junit',str(O/'original-junit.xml'),'--output',str(O/'native')]
for repo in ('recipe','enrollment','carrier','app','research','official','nltk'): command += ['--repo',repo+'='+str(W/repo)]
for p in dict.fromkeys(reads): command += ['--read-path',str(p)]
for selection in json.loads((R/'case-selection.json').read_bytes()):command += ['--select',selection]
command += ['--',sys.executable,'-B','-m','pytest','--noconftest','-o','addopts=','-p','no:cacheprovider','-q','-o','junit_logging=all','-o','junit_log_passing_tests=true','--junitxml='+str(O/'original-junit.xml'),*[str(F/n) for n in ('test_cj_candidate_report.py','test_ifbench_fixture.py','test_cj_edit_fixture.py','test_official_oracles.py')]]
run = subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(O/'outer.stdout.raw').write_bytes(run.stdout)
(O/'outer.stderr.raw').write_bytes(run.stderr)
(O/'outer.argv-exit.json').write_text(json.dumps({'argv':command,'exit':run.returncode},indent=2)+'\n')
sys.path.insert(0,str(W/'carrier/scripts/vidya'))
sys.path.insert(0,str(W/'carrier'))
from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
from claim_tuple import grade
out=[{'Q':q,'T':t,'reasons':why} for row in native_rows(O/'native/receipt.json') for q,t,why in [grade(project_ci_conformance(row))]]
(O/'shared-grade.json').write_text(json.dumps(out,indent=2)+'\n')
raise SystemExit(run.returncode)
