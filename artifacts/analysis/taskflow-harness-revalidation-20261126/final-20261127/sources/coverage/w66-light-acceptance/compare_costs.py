"""Extract existing execution vectors only; no polling, model calls or price assumptions."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
MAIN=HERE.parent/'w66-light-brief-v2/main-comparison/runs/DS41-W-66/direct-1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
main=load(MAIN/'measurement.json')
output={'scope':'fresh light-v2 main implementation versus incremental fresh semantic acceptance reviews of exact unassisted native outputs','main_implementation':{'measurement_path':str(MAIN/'measurement.json'),'measurement_sha256':sha(MAIN/'measurement.json'),'events_sha256':sha(MAIN/'events.jsonl'),'execution':main['execution'],'usage':main['jsonl']['usage'],'acceptance':'Independent acceptance supplied by owning main session; not inferred from measurement.oracle or cost fields.'},'reviews':[],'model':'gpt-6.1-sol','effort':'low','reasoning_is_subset_of_output':True,'wall_scope':'Each full metered CLI execution wall, including its local tools. Sum of review walls is not parallel batch elapsed or isolated model compute time.','other_costs':'Manager/setup/source-audit/coordination costs are separate, not zero or included in these execution vectors. Local token monetary charge may be zero by experiment convention; local compute/time is still separate.','claim_limits':'No claim of minimum possible review/guidance cost, capacity or a general thinking effect. No semantic acceptance inferred from structural rc.','model_calls_by_extractor':0}
for mode in ['gpu-ON-on-common-light','gpu-OFF-off-common-light']:
    root=HERE/'reviews/DS41-W-66'/mode/'final-acceptance'
    run=root/'runs/DS41-W-66/guidance-1';accounting=run/'assistance-accounting.json'
    row={'mode':mode,'review_root':str(root),'review_seal_sha256':sha(root/'SEAL.json'),'state':'pending existing terminal report'}
    if accounting.exists():
        data=load(accounting)
        row.update(state='terminal report observed',accounting_sha256=sha(accounting),execution=data['execution'],usage=data['usage'],semantic_review_advisory=data['semantic_review_advisory'],candidate_unmodified=data['candidate_unmodified_by_review'])
        row['execution_wall_ratio_to_fresh_main']=data['execution']['wall_s']/main['execution']['wall_s']
        row['input_token_ratio_to_fresh_main']=data['usage']['input_tokens']/main['jsonl']['usage']['input_tokens']
    output['reviews'].append(row)
(HERE/'COST-COMPARISON.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({'output':str(HERE/'COST-COMPARISON.json'),'review_states':[r['state'] for r in output['reviews']]}))
