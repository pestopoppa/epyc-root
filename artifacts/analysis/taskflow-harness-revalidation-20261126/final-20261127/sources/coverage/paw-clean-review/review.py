"""Fresh clean-replay namespace over the exact immutable metered review wrapper."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def wrapper():
    lock=load(HERE/'CODE-LOCK.json')
    for name,digest in lock['sha256'].items():assert sha(name)==digest,('source changed',name)
    source=Path(lock['wrapper_path']);spec=importlib.util.spec_from_file_location('immutable_clean_review',source);module=importlib.util.module_from_spec(spec)
    raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==lock['sha256'][str(source)]
    exec(compile(raw,str(source),'exec'),module.__dict__)
    module.HERE=HERE
    old_write=module.write
    def write(path,value):
        path=Path(path)
        if path.name=='feedback.json':
            for help_record in value['actual_prior_help']:
                if help_record['native_ordinal']==1:help_record['help_kind']='neutral-self-check; no failure or semantic diagnosis'
            value['clean_replay_protocol']='original0 + neutral-self-check1/guidance0 + optional one paid correction2'
            value['old_false_feedback_branch_excluded']=True
        if path.name=='plan.json':
            value['command_affinity']='180-183'
            value['scheduling_protocol']={'review_tool_affinity':'180-183','profile_unchanged':True,'accounting_unchanged':True,'no_speed_comparison_claim':True}
            value['clean_review_adapter_sha256']=sha(Path(__file__))
        return old_write(path,value)
    module.write=write
    return module
p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
q=sub.add_parser('stage');q.add_argument('--result',type=Path,required=True);q.add_argument('--kind',choices=['initial-diagnosis','final-acceptance'],required=True);q.add_argument('--structural-receipt',type=Path,required=True)
for name in ['verify','launch','report']:
    q=sub.add_parser(name);q.add_argument('root',type=Path)
    if name=='launch':q.add_argument('--approval',type=Path,required=True)
a=p.parse_args();module=wrapper()
if a.command=='stage':
    result=load(a.result);row=load(HERE.parent/'paw-clean-replay/ROW.json');assert result['case']=='PAW-5' and result['backend']=='gpu' and result['thinking'] is False and result['profile']=='off-recommended'
    assert result['id'] in ['gpu-PAW-5-off-recommended-clean-guidance-1','gpu-PAW-5-off-recommended-clean-guidance-2']
    ordinal=module.infer_ordinal(result)
    if ordinal==1:
        assert result['resume']['prior_result_sha256']==row['resume']['prior_result_sha256'] and result['resume']['prior_session_sha256']==row['resume']['prior_session_sha256']
        assert result['resume']['feedback_sha256']==row['resume']['feedback_sha256']
    else:
        assert Path(result['resume']['prior']).name=='gpu-PAW-5-off-recommended-clean-guidance-1'
    out=module.stage(a.result,a.kind,ordinal,a.structural_receipt)
elif a.command=='verify':out=module.verify(a.root)
elif a.command=='launch':raise SystemExit(module.launch(a.root,a.approval))
else:out=module.report(a.root)
print(json.dumps(out,indent=2))
