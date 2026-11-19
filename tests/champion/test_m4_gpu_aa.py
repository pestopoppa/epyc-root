import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('aa', Path(__file__).parents[2] / 'scripts/champion/m4/calibrate_gpu_aa.py')
aa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aa)


def sample():
    common = {'role': 'architect_critic', 'source_commit': 'c5', 'image_sha256': 'image', 'recipe_sha256': 'recipe', 'model_sha256': 'model', 'prompt_sha256': 'prompt', 'np': 1, 'pair': 0, 'request_count': 1}
    cells = [dict(common, id='first', arm='A1'), dict(common, id='second', arm='A2')]
    rows = []
    for c in cells:
        row = {k: v for k, v in c.items() if k not in ('id', 'request_count')}
        row.update(cell_id=c['id'], plan_sha256='seal', status='COMPLETE', cleanup_verified=True,
                   requests=[{'request_index': 0, 'stream_id': 0, 'success': True, 'http_status': 200, 'predicted_tokens': 100, 'predicted_ms': 1000}], aggregate_decode_tps=100.0)
        rows.append(row)
    return {'schema': 'epyc.m4.gpu.aa.plan.v1', 'intent': 'descriptive_only', 'cells': cells}, rows


def test_paired_control_is_descriptive_only():
    plan, rows = sample()
    result = aa.reduce(plan, rows, 'seal')
    assert result['pairs'][0]['a2_over_a1'] == 1.0
    assert result['decision'] is None and result['gate_authorized'] is False


@pytest.mark.parametrize('mutate', [
    lambda p,r: r.pop(),
    lambda p,r: r[1].update(image_sha256='other'),
    lambda p,r: r[1].update(cleanup_verified=False),
    lambda p,r: r[0]['requests'][0].update(success=False),
    lambda p,r: r[0].update(aggregate_decode_tps=99),
    lambda p,r: p.update(intent='gate'),
])
def test_refuses_incomplete_or_mismatched_input(mutate):
    plan, rows = sample(); mutate(plan, rows)
    with pytest.raises(ValueError):
        aa.reduce(plan, rows, 'seal')
