"""Bind an approved scheduling change before any model launch; no model calls."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root.resolve()
lock=load(HERE/'FUTURE-SOURCE-LOCK.json');wrapper=Path(lock['wrapper'])
assert sha(wrapper)==lock['wrapper_sha256'] and sha(Path(lock['code_lock']))==lock['code_lock_sha256']
spec=importlib.util.spec_from_file_location('immutable_assisted_review',wrapper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
seal=module.verify(root);run=Path(seal['run']);plan_path=run/'plan.json';plan=load(plan_path)
for name in ['launch-start.json','events.jsonl','execution.json','measurement.json']:
    assert not (run/name).exists(),('already launched',run/name)
assert not (root/'MAIN-APPROVAL.json').exists(),'stage a fresh namespace; preserve existing approval'
assert plan['command_affinity']=='84-87'
assert plan['model']=='gpt-6.1-sol' and plan['reasoning_effort']=='low'
assert not (root/'AFFINITY-ADAPTATION.json').exists()
old={name:(root/name).read_text() for name in ['SEAL.json','APPROVAL-TEMPLATE.json']}
old['plan.json']=plan_path.read_text()
write(root/'UNLAUNCHED-PRE-AFFINITY.json',old)
plan['command_affinity']='180-183'
plan['scheduling_protocol']={'kind':'review-tool-host-affinity-only','previous':'84-87','current':'180-183','reason':'avoid runnable pytest starvation from concurrent96CPU inference','preserve_model_profile_and_usage_accounting':True,'speed_comparison_claim':False,'adapter_source_sha256':sha(Path(__file__))}
write(plan_path,plan)
seal['immutable'][str(plan_path.relative_to(root))]=sha(plan_path)
write(root/'SEAL.json',seal)
approval=load(root/'APPROVAL-TEMPLATE.json');approval['review_seal_sha256']=sha(root/'SEAL.json');approval['plans'][str(plan_path)]=sha(plan_path);write(root/'APPROVAL-TEMPLATE.json',approval)
write(root/'AFFINITY-ADAPTATION.json',{'adapter_sha256':sha(Path(__file__)),'source_lock_sha256':sha(HERE/'FUTURE-SOURCE-LOCK.json'),'plan_sha256':sha(plan_path),'review_seal_sha256':sha(root/'SEAL.json'),'model_calls':0,'unlaunched_only':True})
module.verify(root)
print(json.dumps(load(root/'AFFINITY-ADAPTATION.json'),indent=2))
