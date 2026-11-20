"""Validate/reduce prospective offset controls, never issue qualification."""
import math

OFFSETS = ('0', 'd', '4d')
PAIRS = ('01', '02', '12', 'shift1', 'shift2')


def summarize(positions, n_probe=64):
    """Keep all positions; no masking near ties or subtracting observed errors."""
    if type(n_probe) is not int or n_probe <= 0:
        raise ValueError('invalid probe count')
    expected = {f'cal_{off}_{pair}' for off in OFFSETS for pair in PAIRS}
    groups = {name: {} for name in expected}
    for row in positions:
        name = row.get('comparison', '')
        if not name.startswith('cal_'):
            continue  # Historical records belong to their original evaluator.
        if name not in groups or row.get('scenario') != 'position':
            raise ValueError('unknown calibration record')
        index = row.get('index')
        if type(index) is not int or not 0 <= index < n_probe or index in groups[name]:
            raise ValueError('invalid or duplicate position')
        for key in ('kld', 'ref_margin', 'test_margin'):
            value = row.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid ' + key)
        for key in ('ref_top1', 'test_top1'):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError('invalid ' + key)
        groups[name][index] = row
    result = {}
    for name, indexed in sorted(groups.items()):
        if len(indexed) != n_probe:
            raise ValueError('incomplete ' + name)
        rows = [indexed[i] for i in range(n_probe)]
        result[name] = {
            'kld_mean': math.fsum(r['kld'] for r in rows) / n_probe,
            'mismatch_indices': [r['index'] for r in rows if r['ref_top1'] != r['test_top1']],
            'positions': rows,
        }
    return {'schema': 'kshift-offset-calibration-v1', 'qualification': False,
            'verdict': 'CALIBRATION_COMPLETE', 'n_probe': n_probe, 'comparisons': result}
