#!/usr/bin/env python3
"""Extract the prospectively declared original 120-item cell from one new 141-item run."""
import hashlib
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
SOURCE_SHA = '022ba34ca80ac0d8fa734d7fdf3d9b5e484f4ad2265fba81f31021d87619ff04'
WHOLE_SHA = 'dc8fa414b5e50328d294fe6d4b9a32fe5bea97b98a727808c37ceb5c4f4ade68'
SUBSET_SHA = '536a5af4058aa512c4217daf9d9c0408cfc8404713fc1f1c73003a1d7ba1bf4d'
CELL = 'oolong_synth@131072'
MODEL_SHA = 'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348'
BIN_SHA = '2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b'
TEMPLATE_SHA = '1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551'
HIP_SHA = 'f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079'
PRIVATE_BIN = '/mnt/raid0/llm/tmp/codex-ni-gpu-anchor-custody-20261030/private-v10-view/bin/llama-server'


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def extract(out):
    declaration = json.loads((D / 'JOINT-PREDECLARATION.json').read_text())
    source = json.loads((D / 'source-120/plan.json').read_text())
    full = json.loads((out / 'plan/plan.json').read_text())
    decision = json.loads((out / 'decision.json').read_text())
    assert declaration['whole_plan_sha256'] == full['plan_sha256'] == decision['plan_sha256'] == WHOLE_SHA
    assert full['n_items'] == 141 and decision['status'] == 'FINAL'
    assert declaration['original_120_source_plan_sha256'] == source['plan_sha256'] == SOURCE_SHA
    src = read_jsonl(D / 'source-120/items.jsonl')
    assert len(src) == source['n_items'] == 120
    assert len({r['item_id'] for r in src}) == 120
    digest = hashlib.sha256('\n'.join(f"{r['item_id']} {r['prompt_sha256']}"
                                      for r in sorted(src, key=lambda r: r['item_id'])).encode()).hexdigest()
    assert digest == declaration['original_120_subset_id_prompt_sha256'] == SUBSET_SHA
    expected = {r['item_id']: r for r in src}
    whole_rows = read_jsonl(out / 'plan/items.jsonl')
    assert len(whole_rows) == 141 and len({r['item_id'] for r in whole_rows}) == 141
    selected = [r for r in whole_rows if r['segment'] == 'new_oolong']
    assert len(selected) == 120 and {r['item_id'] for r in selected} == set(expected)
    assert all(r['cell'] == CELL and r['gate'] == 'native_mcnemar' and
               r['arms'] == ['A0', 'A1'] and r['prompt_sha256'] == expected[r['item_id']]['prompt_sha256']
               for r in selected)
    assert all(r['cell'] != CELL for r in whole_rows if r['segment'] != 'new_oolong')
    pins = decision['identity']
    assert pins['plan_sha256'] == WHOLE_SHA
    for key, value in [('model_sha256', MODEL_SHA), ('binary_sha256', BIN_SHA),
                       ('template_sha256', TEMPLATE_SHA), ('ggml_dso_sha256', HIP_SHA),
                       ('binary_path', PRIVATE_BIN)]:
        assert pins[key] == value, key
    assert pins['source_manifest_sha256'] == hashlib.sha256((D / 'ARCHIVE.sha256').read_bytes()).hexdigest()
    assert pins['paired_recipe_sha256'] == hashlib.sha256((D / 'job.sh').read_bytes()).hexdigest()
    assert pins['research_sha'] == '7e7d5ef7f28f0c0ec45c16b7a90a51750006671f'
    arms = {}
    for arm in ('A0', 'A1'):
        path = out / 'results' / f'{arm}.jsonl'
        rows = read_jsonl(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == decision['results_sha256'][arm]
        found = {}
        for row in rows:
            item_id = row['item_id']
            if item_id not in expected:
                continue
            assert item_id not in found, f'duplicate {arm} {item_id}'
            assert row['arm'] == arm and row['status'] == 'ok' and row['plan_sha256'] == WHOLE_SHA
            assert row['prompt_sha256'] == expected[item_id]['prompt_sha256']
            assert row['segment'] == 'new_oolong' and row['cell'] == CELL and row['gate'] == 'native_mcnemar'
            assert row['zone'] == 'native' and row['n_source'] == 'server_timings'
            assert isinstance(row['real_n'], int) and row['real_n'] > 0
            assert row['real_n'] == row['timings']['prompt_n'] + (row['timings'].get('cache_n') or 0)
            assert row['server']['model'] == pins['model']
            assert row['server']['build_dir'] == str(Path(PRIVATE_BIN).parent)
            found[item_id] = row
        assert set(found) == set(expected), f'incomplete {arm}: {len(found)}/120'
        arms[arm] = found
    sys.path.insert(0, str(D / 'archive'))
    from scripts.benchmark.yarn_gate import agg_scoring
    a0 = {item_id: r['score'] for item_id, r in arms['A0'].items()}
    a1 = {item_id: r['score'] for item_id, r in arms['A1'].items()}
    result = agg_scoring.net_paired_mcnemar(a0, a1)
    assert result == decision['per_cell_native'][CELL]
    assert result['n_pairs'] == 120 and result['alpha'] == 0.05
    return {'schema': 'epyc.yarn_agg_1g.original_120_result.v1', 'status': 'FINAL',
            'whole_plan_sha256': WHOLE_SHA, 'source_plan_sha256': SOURCE_SHA,
            'subset_id_prompt_sha256': SUBSET_SHA, 'cell': CELL,
            'result': result, 'power_target_reached': result['n_discordant'] >= 10,
            'attempted_a0': sum(bool(r['attempted']) for r in arms['A0'].values()),
            'attempted_a1': sum(bool(r['attempted']) for r in arms['A1'].values()),
            'attempted_both': sum(bool(arms['A0'][i]['attempted']) and bool(arms['A1'][i]['attempted'])
                                  for i in expected),
            'denominator': 'all 120 exact paired native scored items, including no-answer as wrong',
            'interpretation': 'harm detection only; NOT-FAIL is no equivalence claim',
            'scope': 'one prospectively declared subset of the same new 141-item run; prior R6 scores not pooled'}


if __name__ == '__main__':
    out = Path(sys.argv[1])
    try:
        record = extract(out)
    except Exception as exc:
        record = {'schema': 'epyc.yarn_agg_1g.original_120_result.v1',
                  'status': 'INCOMPLETE', 'reason': f'{type(exc).__name__}: {exc}',
                  'whole_plan_sha256': WHOLE_SHA, 'source_plan_sha256': SOURCE_SHA,
                  'subset_id_prompt_sha256': SUBSET_SHA}
    (out / 'SUBSET-120-RESULT.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    if record['status'] != 'FINAL':
        raise SystemExit(2)
