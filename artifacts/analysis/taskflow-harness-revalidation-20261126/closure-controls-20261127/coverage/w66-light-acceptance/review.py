"""Fresh per-mode W66 light-v2 acceptance, using immutable existing review code."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
VIEW=HERE/'import-view'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def wrapper():
    lock=load(HERE/'CODE-LOCK.json')
    for name,digest in lock['sha256'].items():assert sha(name)==digest,('immutable review source changed',name)
    source=Path(lock['expert_wrapper']);spec=importlib.util.spec_from_file_location('immutable_light_expert_review',source);module=importlib.util.module_from_spec(spec)
    raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==lock['sha256'][str(source)];exec(compile(raw,str(source),'exec'),module.__dict__)
    module.HERE=HERE;module.ORIGINAL=VIEW
    old_modules=module.modules
    def modules(root):
        prepare,measure=old_modules(root)
        original_prompt=prepare.prompt
        def prompt(case,arm,feedback=None):
            text=original_prompt(case,arm,feedback)
            return text+'\nExisting execution evidence: the hash-bound receipt reports both listed tests passed for this exact candidate under the unchanged independent checker. Do not rerun equivalent passed tests unnecessarily. Independently inspect the changed fixture, unchanged serial test and preserved private-lock isolation/assertions against the accurate light-v2 brief. Structural pass alone is not semantic acceptance. If a distinct additional check is necessary, explain why. Return one concise final ACCEPT or REJECT with source evidence; leave the candidate unmodified.\n'
        prepare.prompt=prompt
        return prepare,measure
    module.modules=modules
    old_write=module.write
    def write(path,value):
        if Path(path).name=='plan.json':
            value['command_affinity']='180-183'
            value['review_condition']='fresh independent acceptance of unassisted accurate-light-v2 native candidate; no detailed/v1/main answer reuse'
            value['review_adapter_sha256']=sha(Path(__file__))
        return old_write(path,value)
    module.write=write
    return module
p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
q=sub.add_parser('stage');q.add_argument('--result',type=Path,required=True);q.add_argument('--test-pass-receipt',type=Path,required=True)
for name in ['verify','launch','report']:
    q=sub.add_parser(name);q.add_argument('root',type=Path)
    if name=='launch':q.add_argument('--approval',type=Path,required=True)
a=p.parse_args();module=wrapper()
if a.command=='stage':
    result=load(a.result);unit=a.result.resolve().parent
    assert unit.parent==Path(load(HERE/'CODE-LOCK.json')['native_units_root'])
    expected={'gpu-DS41-W-66-on-common-light-v2':(True,'on-common-light'),'gpu-DS41-W-66-off-common-light-v2':(False,'off-common-light')}
    assert result['id']==unit.name and result['id'] in expected
    thinking,profile=expected[result['id']]
    assert result['thinking'] is thinking and result['profile']==profile and result['backend']=='gpu'
    assert result['status']=='oracle_pass' and not result.get('resume')
    receipt=load(a.test_pass_receipt)
    assert receipt['source_result_sha256']==sha(a.result) and receipt['two_listed_tests_passed'] is True
    assert receipt['candidate_patch_sha256']==result['patch_sha256']
    out=module.stage(a.result,'final-acceptance',0,a.test_pass_receipt)
elif a.command=='verify':out=module.verify(a.root)
elif a.command=='launch':raise SystemExit(module.launch(a.root,a.approval))
else:out=module.report(a.root)
print(json.dumps(out,indent=2))
