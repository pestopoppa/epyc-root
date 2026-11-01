import hashlib, importlib.util, json, os, subprocess, tempfile
from pathlib import Path
W=Path('/tmp/c3-success-isolation-work')
for name in ('host-job-v2.sh','host-job-wrapper-v2.sh'):
    subprocess.run(['bash','-n',str(W/name)],check=True)
for name in ('complete-v2.py','publish-result-v2.py'):
    subprocess.run(['python3','-m','py_compile',str(W/name)],check=True)

# The helper's configured source/destination roots are host and rowflow namespaces respectively.
with tempfile.TemporaryDirectory(prefix='c3-copy-test-') as td:
    root=Path(td); host=root/'host'; shared=root/'shared'; run=host/'run-20300101T000000-123'
    (run/'pass-B').mkdir(parents=True)
    for name,body in [('capture.json','{"capture":1}\n'),('belief-receipt.json','{"claim":"test"}\n')]:
        (run/'pass-B'/name).write_text(body)
    helper=root/'publish-result-v2.py'
    text=(W/'publish-result-v2.py').read_text()
    text=text.replace("Path('/mnt/micron/refactor-c3-native-profile-r4-20261101')",'Path('+repr(str(host))+')')
    text=text.replace("Path('/mnt/raid0/llm/tmp/refactor-c3-native-profile-r4-20261101')",'Path('+repr(str(shared))+')')
    helper.write_text(text)
    proc=subprocess.run(['python3',str(helper),str(run)],check=False,capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    out=proc.stdout.strip()
    assert out and Path(out).exists(), out
    published=Path(out)
    assert published==shared/'results'/run.name
    assert (published/'pass-B'/'capture.json').read_bytes()==(run/'pass-B'/'capture.json').read_bytes()
    assert (published/'pass-B'/'belief-receipt.json').read_bytes()==(run/'pass-B'/'belief-receipt.json').read_bytes()
    provenance=json.loads((published/'source-provenance.json').read_text())
    for name in ('capture.json','belief-receipt.json'):
        assert provenance['artifacts'][name]['host_source']==str(run/'pass-B'/name)
        assert provenance['artifacts'][name]['sha256']==hashlib.sha256((published/'pass-B'/name).read_bytes()).hexdigest()
    # Re-publishing a run cannot silently overwrite an already-published result.
    assert subprocess.run(['python3',str(helper),str(run)],capture_output=True).returncode!=0

# Completion is evaluated by the rowflow-visible shared tree; dryrun cannot accept it.
with tempfile.TemporaryDirectory(prefix='c3-complete-visible-') as td:
    root=Path(td); run=root/'results'/'run-fixture'; (run/'pass-B').mkdir(parents=True)
    (run/'pass-B'/'capture.json').write_text('{}')
    (run/'pass-B'/'belief-receipt.json').write_text('{}')
    proof={'schema':'c3-native-r4-shared-result-provenance-v1','run_id':run.name,'artifacts':{}}
    for name in ('capture.json','belief-receipt.json'):
        proof['artifacts'][name]={'sha256':hashlib.sha256((run/'pass-B'/name).read_bytes()).hexdigest()}
    (run/'source-provenance.json').write_text(json.dumps(proof))
    (root/'SUCCESS').write_text(str(run)+'\n')
    checker=root/'complete-v2.py'; checker.write_text((W/'complete-v2.py').read_text())
    env=os.environ.copy(); env.pop('FILLER_DRYRUN',None); env.pop('WS58_QUAL',None)
    assert subprocess.run(['python3',str(checker)],env=env).returncode==0
    env['FILLER_DRYRUN']='1'
    assert subprocess.run(['python3',str(checker)],env=env).returncode!=0
    env.pop('FILLER_DRYRUN')
    (run/'pass-B'/'belief-receipt.json').write_text('{"tampered":true}')
    assert subprocess.run(['python3',str(checker)],env=env).returncode!=0, 'tampered copied result accepted'

# Validate current row spec routes the unique result glob to shared D and keeps it.
spec=json.loads((W/'row-spec.json').read_text())
assert spec['result_path'].endswith('/results/run-*/pass-B/belief-receipt.json')
assert 'results/**' in spec['keep'] and spec['result_format']=='json'

# Exercise the actual rowflow JSON unit counter against the shared-layout glob.
import importlib.util
rf_path=Path('/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/rowflow.py')
rf_spec=importlib.util.spec_from_file_location('rowflow_readonly_test',rf_path)
rf=importlib.util.module_from_spec(rf_spec); rf_spec.loader.exec_module(rf)
with tempfile.TemporaryDirectory(prefix='c3-rowflow-units-') as td:
    root=Path(td); globpath=str(root/'results'/'run-*'/'pass-B'/'belief-receipt.json')
    assert rf.count_units(globpath,'json')==0
    out=root/'results'/'run-example'/'pass-B'/'belief-receipt.json'; out.parent.mkdir(parents=True)
    out.write_text('{"claim":"one"}')
    assert rf.count_units(globpath,'json')==1

# Verify source seals for modified and added code.
for manifest in ('SOURCE.sha256','V2-SOURCE.sha256'):
    for line in (W/manifest).read_text().splitlines():
        digest,path=line.split(None,1); path=path.lstrip('*')
        rel=path.rsplit('/',1)[-1]
        if rel in ('host-job-v2.sh','host-job-wrapper-v2.sh','complete-v2.py','publish-result-v2.py'):
            assert digest==hashlib.sha256((W/rel).read_bytes()).hexdigest(),f'{manifest}: bad {rel}'
print('PASS: shell/Python syntax, namespace-copy bytes and provenance hashes, collision refusal, shared-tree completion, dryrun rejection, row-spec shared glob/retention, rowflow unit counter, source seals')
