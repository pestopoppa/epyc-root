"""Verify the sealed neutral comparison sidecar without calling a model."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import review

stage = review.HERE / 'reviews/TU-GR-1/gpu-OFF-off-common-on-sampling/final-acceptance'
seal = review.verify(stage)
prep, measure = review.modules(stage)
run = Path(seal['run'])
plan = review.load(run / 'plan.json')
lane = run / 'lane'
scoped = review.review_source_map(prep.file_map, seal['comparison_evidence'])
assert scoped(lane) == plan['before_files']
assert len(seal['comparison_evidence']) == len(review.load(stage / 'cases/TU-GR-1/case.json')['baseline_files']) + 1
assert (lane / '.review-evidence/candidate.patch').stat().st_mode & 0o222 == 0
prompt = (run / 'prompt.md').read_text()
assert '.review-evidence' in prompt and 'baseline/' in prompt and 'candidate.patch' in prompt
assert 'generic `cannot unshare`' not in prompt
with TemporaryDirectory(prefix='cpu-tu-review-control-') as tmp:
    scratch = Path(tmp)
    path = scratch / '.review-evidence'
    path.mkdir()
    subject = path / 'candidate.patch'
    subject.write_text('sealed')
    bound = review.review_source_map(prep.file_map, prep.file_map(path))
    assert bound(scratch) == {}
    subject.write_text('changed')
    try:
        bound(scratch)
    except ValueError as error:
        assert str(error) == 'read-only baseline or patch evidence changed'
    else:
        raise AssertionError('modified reviewer comparison accepted')
print(json.dumps({'complete_candidate_map': True, 'comparison_files': len(seal['comparison_evidence']),
                  'changed_comparison_rejected': True, 'prior_paid_guidance_output_tokens': 1128,
                  'no_new_semantic_hint': True, 'model_calls': 0}))
