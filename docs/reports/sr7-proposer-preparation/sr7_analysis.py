"""Fail-closed prospective SR-7 analysis of independently verified request evidence.

This analysis does not establish the authenticity of lifecycle/runtime attestations;
the caller must independently audit them and the sealed plan before use.
"""
import math
import random
from collections import Counter
from acceptance_decomposition import decompose_acceptance
from proposer_stats import parse_proposer_stats

WIDTHS = (2, 4, 6)
CLASSES = ('code', 'rag', 'prose')
ARMS = tuple((mode, width) for mode in ('composed', 'control') for width in WIDTHS)
DRAWS = 10000
SEED = 20261102


def _request(record, mode):
    if not isinstance(record, dict) or record.get('http_status') != 200:
        raise ValueError('missing or failed response')
    if any(record.get(k) is not True for k in ('lifecycle_verified', 'runtime_seal_verified', 'settings_verified', 'complete_response')):
        raise ValueError('unverified lifecycle, runtime or response')
    response = record.get('response')
    if not isinstance(response, dict) or response.get('stop_type') not in ('eos', 'word'):
        raise ValueError('incomplete or budget-limited response')
    tokens = record.get('output_token_ids')
    if not isinstance(tokens, list) or not tokens or any(type(t) is not int or t < 0 for t in tokens):
        raise ValueError('missing output token IDs')
    timings = response.get('timings')
    if not isinstance(timings, dict) or not isinstance(record.get('trace'), str):
        raise ValueError('missing native evidence')
    names = ['ngram-mod', 'draft-mtp'] if mode == 'composed' else ['draft-mtp']
    result = parse_proposer_stats(record['trace'], names, timings.get('draft_n'), timings.get('draft_n_accepted'))
    if response.get('tokens_predicted') != len(tokens) or any(v['begin'] != 1 for v in result['proposers'].values()):
        raise ValueError('output token count or single-request trace mismatch')
    prompt_tokens = record.get('prompt_token_ids')
    if not isinstance(prompt_tokens, list) or len(prompt_tokens) < 5 or any(type(t) is not int or t < 0 for t in prompt_tokens):
        raise ValueError('missing rendered prompt token IDs')
    result['prompt_token_ids'] = prompt_tokens
    result['output_tokens'] = len(tokens)
    return result


def analyze(plan, records):
    """Analyze exact sealed plan and native request records; return UNKNOWN on any defect.

    Plan contains three windows, each with id and prompts (id, class, seed).
    Records contain window, prompt, mode, width and native evidence fields.
    No exclusion is silently dropped. Caller must retain all raw source artifacts.
    """
    try:
        return _analyze(plan, records)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        return {'status': 'UNKNOWN', 'reason': str(exc)}


def _analyze(plan, records):
    if not isinstance(plan, dict) or plan.get('seal_verified') is not True or not isinstance(records, list):
        raise ValueError('sealed plan and records required')
    windows = plan.get('windows')
    if not isinstance(windows, list) or len(windows) != 3:
        raise ValueError('three windows required')
    ids, prompts, seeds = set(), set(), set()
    expected = {}
    expected_seeds = {}
    for window in windows:
        wid = window['id']
        if not isinstance(wid, str) or not wid or wid in ids:
            raise ValueError('duplicate or invalid window')
        ids.add(wid)
        entries = window['prompts']
        if not isinstance(entries, list) or len(entries) < 15:
            raise ValueError('at least 15 prompts per window required')
        counts = Counter()
        for p in entries:
            pid, cls, seed = p['id'], p['class'], p['seed']
            if not isinstance(pid, str) or not pid or pid in prompts or cls not in CLASSES or type(seed) is not int or seed in seeds:
                raise ValueError('invalid or repeated prompt, class or seed')
            prompts.add(pid); seeds.add(seed); counts[cls] += 1
            for mode, width in ARMS:
                expected[(wid, pid, mode, width)] = cls
                expected_seeds[(wid, pid, mode, width)] = seed
        if any(counts[c] < 5 for c in CLASSES):
            raise ValueError('at least five prompts per class required')
    observed = {}
    for rec in records:
        key = (rec['window'], rec['prompt'], rec['mode'], rec['width'])
        if key not in expected or key in observed or type(rec['width']) is not int:
            raise ValueError('unexpected or duplicate request')
        if type(rec.get('seed')) is not int or rec['seed'] != expected_seeds[key]:
            raise ValueError('request seed differs from plan')
        observed[key] = _request(rec, rec['mode'])
    if set(observed) != set(expected):
        raise ValueError('missing request or paired arm')
    for wid, pid, _, _ in expected:
        reference = observed[(wid, pid, *ARMS[0])]['prompt_token_ids']
        if any(observed[(wid, pid, mode, width)]['prompt_token_ids'] != reference for mode, width in ARMS):
            raise ValueError('rendered prompt tokens differ between arms')
    rng = random.Random(SEED)
    out = {}
    for wid in sorted(ids):
        groups = {c: sorted({k[1] for k, v in expected.items() if k[0] == wid and v == c}) for c in CLASSES}
        def estimate(mode, low, high, samples):
            return sum(sum(observed[(wid, p, mode, high)]['acceptance'] - observed[(wid, p, mode, low)]['acceptance'] for p in samples[c]) / len(samples[c]) for c in CLASSES) / 3
        comparisons = {}
        for mode in ('composed', 'control'):
            for low, high in ((2, 4), (4, 6)):
                point = estimate(mode, low, high, groups)
                draws = []
                for _ in range(DRAWS):
                    sample = {c: rng.choices(groups[c], k=len(groups[c])) for c in CLASSES}
                    draws.append(estimate(mode, low, high, sample))
                draws.sort()
                lo = draws[math.floor((.05 / 4) * (DRAWS - 1))]
                hi = draws[math.ceil((1 - .05 / 4) * (DRAWS - 1))]
                label = 'RISE' if lo > 0 else 'NO_RISE_RESOLVED' if hi <= 0 else 'INCONCLUSIVE'
                comparisons[f'{mode}_{low}_{high}'] = {'difference': point, 'interval': [lo, hi], 'classification': label if mode == 'composed' else 'DESCRIPTIVE'}
        cells = {}
        for mode, width in ARMS:
            rows = [observed[(wid, p, mode, width)] for c in CLASSES for p in groups[c]]
            names = ('ngram-mod', 'draft-mtp') if mode == 'composed' else ('draft-mtp',)
            counts = {n: {k: sum(r['proposers'][n][k] for r in rows) for k in ('generated_tokens', 'accepted_tokens')} for n in names}
            total = sum(v['generated_tokens'] for v in counts.values())
            for v in counts.values():
                v['share'] = v['generated_tokens'] / total
                v['acceptance'] = v['accepted_tokens'] / v['generated_tokens'] if v['generated_tokens'] else None
            cells[f'{mode}_{width}'] = {'proposers': counts, 'class_balanced_acceptance': sum(sum(observed[(wid, p, mode, width)]['acceptance'] for p in groups[c]) / len(groups[c]) for c in CLASSES) / 3, 'prompt_acceptance': [r['acceptance'] for r in rows], 'output_lengths': [r['output_tokens'] for r in rows]}
        for low, high in ((2, 4), (4, 6)):
            a = cells[f'composed_{low}']['proposers']; b = cells[f'composed_{high}']['proposers']
            if any(v['generated_tokens'] == 0 for sample in (a, b) for v in sample.values()):
                comparisons[f'decomposition_{low}_{high}'] = {'status': 'UNDEFINED'}
            else:
                d = decompose_acceptance(a, b)
                comparisons[f'decomposition_{low}_{high}'] = {'status': 'DEFINED', **{k: str(d[k]) for k in ('delta', 'mix', 'rate')}}
        prompt_audit = {}
        for c in CLASSES:
            for pid in groups[c]:
                tokens = observed[(wid, pid, *ARMS[0])]['prompt_token_ids']
                grams = [tuple(tokens[i:i+5]) for i in range(len(tokens)-4)]
                numerator = len(grams) - len(set(grams))
                prompt_audit[pid] = {'class': c, 'repeated_5gram_numerator': numerator, 'denominator': len(grams), 'fraction': numerator / len(grams)}
        out[wid] = {'comparisons': comparisons, 'cells': cells, 'prompt_audit': prompt_audit, 'planned': sum(map(len, groups.values())), 'attempted': sum(map(len, groups.values())), 'completed': sum(map(len, groups.values())), 'excluded': 0}
    replicated = {}
    for low, high in ((2, 4), (4, 6)):
        labels = [out[w]['comparisons'][f'composed_{low}_{high}']['classification'] for w in sorted(ids)]
        replicated[f'{low}_{high}'] = 'REPLICATED_RISE' if all(x == 'RISE' for x in labels) else 'NO_RISE_RESOLVED' if all(x == 'NO_RISE_RESOLVED' for x in labels) else 'INCONCLUSIVE'
    return {'status': 'COMPLETE', 'windows': out, 'cross_window': replicated, 'scope': 'descriptive decomposition; lifecycle and provenance require independent audit'}
