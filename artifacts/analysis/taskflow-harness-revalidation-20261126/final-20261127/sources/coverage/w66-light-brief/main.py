"""Fresh light-brief main comparator over exact original measured CLI modules."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parents[1]/'main-comparison'
ROOT=HERE/'main-comparison'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def modules():
    lock=json.loads((HERE/'MAIN-CODE-LOCK.json').read_text())
    for name,digest in lock['sha256'].items():assert sha(name)==digest,('source changed',name)
    spec=importlib.util.spec_from_file_location('prepare',ORIGINAL/'prepare.py');prepare=importlib.util.module_from_spec(spec);sys.modules['prepare']=prepare
    raw=(ORIGINAL/'prepare.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==lock['sha256'][str(ORIGINAL/'prepare.py')];exec(compile(raw,str(ORIGINAL/'prepare.py'),'exec'),prepare.__dict__);prepare.HERE=ROOT
    spec=importlib.util.spec_from_file_location('light_measure',ORIGINAL/'measure.py');measure=importlib.util.module_from_spec(spec)
    raw=(ORIGINAL/'measure.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==lock['sha256'][str(ORIGINAL/'measure.py')];exec(compile(raw,str(ORIGINAL/'measure.py'),'exec'),measure.__dict__)
    assert prepare.MODEL=='gpt-6.1-sol' and prepare.EFFORT=='low' and measure.HERE==ROOT
    return prepare,measure
p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','launch','report']);p.add_argument('--approval',type=Path);a=p.parse_args();prepare,measure=modules();run=ROOT/'runs/DS41-W-66/direct-1'
if a.action=='stage':
    run=prepare.stage('DS41-W-66','direct',1)
    plan=json.loads((run/'plan.json').read_text());plan['command_affinity']='180-183';plan['brief_class']='light/original-task-only';plan['comparison_scope']='fresh matched light-brief comparator; never reuse detailed direct-1 result'
    (run/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    prompt=(run/'prompt.md').read_text();assert not any(word in prompt for word in ['ArtifactStore','current_recipe','selection_reference','synthetic receipt','digest-bound'])
    (ROOT/'APPROVAL-TEMPLATE.json').write_text(json.dumps({'approved_by':None,'native_harness_qualified':False,'plans':{str(run/'plan.json'):sha(run/'plan.json')},'instruction':'Main reviews exact fresh light-brief plan and blinding before approving; no call authorized'},indent=2)+'\n');print(run)
elif a.action=='launch':
    assert a.approval;raise SystemExit(measure.launch(run,a.approval.resolve()))
else:print(json.dumps(measure.report(run),indent=2))
