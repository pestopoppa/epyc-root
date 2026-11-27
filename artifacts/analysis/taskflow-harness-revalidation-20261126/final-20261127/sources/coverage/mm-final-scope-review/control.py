"""Verify all MM review templates, whole lane maps, and neutral evidence without execution."""
import json
from pathlib import Path

import review

staged = review.load(review.HERE / 'STAGED.json')
assert len(staged) == 3 and {entry['id'] for entry in staged} == review.MM_IDS
result = []
for entry in staged:
    root = Path(entry['root'])
    run = Path(entry['run'])
    seal = review.verify(root)
    prepare, _ = review.modules(root)
    plan = review.load(run / 'plan.json')
    scope = review.review_source_map(prepare.file_map, seal['comparison_evidence'])
    assert scope(run / 'lane') == plan['before_files']
    assert len(seal['comparison_evidence']) == len(review.load(root / 'cases/MM-5/case.json')['baseline_files']) + 1
    assert review.sha(run / 'lane/.review-evidence/candidate.patch') == plan['candidate_input_patch_sha256']
    assert review.sha(root / 'SEAL.json') == entry['seal_sha256']
    assert review.sha(run / 'plan.json') == entry['plan_sha256']
    assert plan['model'] == 'gpt-6.1-sol' and plan['reasoning_effort'] == 'low' and plan['command_affinity'] == '180-183'
    template = review.load(root / 'APPROVAL-TEMPLATE.json')
    assert template['approved_by'] is None and not template['native_harness_qualified']
    assert template['plans'][str(run / 'plan.json')] == entry['plan_sha256']
    prompt = (run / 'prompt.md').read_text()
    assert 'Begin with ACCEPT or REJECT for the original corrected owner brief' in prompt
    assert 'report the observed infeasible-cap robustness result' in prompt
    prior = review.load(root / 'feedback.json')['actual_prior_help']
    assert len(prior) == entry['historical_verifier_messages']
    assert seal['prior_measured_paid_guidance']['paid_model_calls'] == 0
    result.append({'id': entry['id'], 'comparison_files': len(seal['comparison_evidence']),
                   'scope_verified': True, 'approval_template_only': True})
print(json.dumps({'reviews': result, 'candidate_executions': 0, 'model_calls': 0}))
