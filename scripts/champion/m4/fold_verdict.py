#!/usr/bin/env python3
"""INF-22 M4 fold verdict: apply the signed rule to every cell-result.json of a sealed plan.

  fold_verdict.py --plan DIR/FOLD-PLAN.json [--out VERDICT.json]

Rule (artifacts/operator/m4-fold-rule-20261104.json, bound into the plan with its sha):
  per role   ratio = median(candidate aggregate_decode_tps) / median(baseline ...) over ABBA pairs
  FAIL       any role < its backend's fail_ratio, or any greedy output differs between arms
  PASS       every role of every backend >= pass_ratio (and no FAIL)
  else       INCONCLUSIVE (no fold)
A plan with a missing or invalid cell result yields INCOMPLETE, never a verdict.

Fixed-format lines:
  M4-FOLD-VERDICT verdict=<PASS|FAIL|INCONCLUSIVE|INCOMPLETE> roles=<n> cells=<n> plan=<sha> rule=<sha>
  ROLE <role> backend=<b> ratio=<x.xxxx> pass=<p> fail=<f> base_med=<tps> cand_med=<tps> n=<pairs> quality=<SAME|DIFF> <OK|BELOW_PASS|BELOW_FAIL>
  QUALITY_DIFF <role> pair=<k> qid=<id>
  MISSING <cell> <reason>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = 'epyc.m4.fold_verdict.v1'


def _fold_entry():
    if 'fold_entry' in sys.modules:
        return sys.modules['fold_entry']
    spec = importlib.util.spec_from_file_location('fold_entry', HERE / 'fold_entry.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules['fold_entry'] = mod
    spec.loader.exec_module(mod)
    return mod


def output_key(o: dict):
    """Greedy identity: token ids when both arms returned them, else the text hash."""
    return o.get('tokens_sha256') or o.get('text_sha256')


def load_results(plan: dict) -> tuple[dict, list[str]]:
    root = Path(plan['result_root'])
    res, missing = {}, []
    for c in plan['cells']:
        p = root / c['id'] / 'cell-result.json'
        try:
            r = json.loads(p.read_text())
        except (OSError, ValueError):
            missing.append(f'{c["id"]} no cell-result.json')
            continue
        bad = [k for k in ('cell', 'arm', 'pair', 'position', 'role') if r.get(k) != {**c, 'cell': c['id']}.get(k)]
        if r.get('plan_sha256') != plan['plan_sha256']:
            bad.append('plan_sha256')
        tps = r.get('aggregate_decode_tps')
        if not isinstance(tps, (int, float)) or not tps > 0:
            bad.append('aggregate_decode_tps')
        if bad:
            missing.append(f'{c["id"]} invalid: {",".join(bad)}')
            continue
        res[c['id']] = r
    return res, missing


def decide(plan: dict, results: dict) -> dict:
    rule = plan['decision_rule']['rule']
    roles = {}
    for c in plan['cells']:
        roles.setdefault(c['role'], {'backend': c['backend'], 'cells': []})['cells'].append(c)
    out_roles, diffs = [], []
    for role, info in roles.items():
        b = info['backend']
        tps = {'baseline': [], 'candidate': []}
        by_pair: dict[int, dict] = {}
        for c in info['cells']:
            r = results[c['id']]
            tps[c['arm']].append(float(r['aggregate_decode_tps']))
            by_pair.setdefault(c['pair'], {})[c['arm']] = r
        base, cand = statistics.median(tps['baseline']), statistics.median(tps['candidate'])
        ratio = cand / base
        # Greedy identity between arms, within each ABBA pair: the candidate's output for a prompt
        # must equal the baseline's output for the same prompt (missing outputs count as a diff).
        same = True
        for k in sorted(by_pair):
            outs = {arm: {o['qid']: output_key(o) for o in (by_pair[k].get(arm, {}).get('greedy') or {}).get('outputs') or []}
                    for arm in ('baseline', 'candidate')}
            for qid in sorted(set(outs['baseline']) | set(outs['candidate'])):
                bk, ck = outs['baseline'].get(qid), outs['candidate'].get(qid)
                if bk is None or ck is None or bk != ck:
                    same = False
                    diffs.append((role, k, qid))
        p, f = rule[b]['pass_ratio'], rule[b]['fail_ratio']
        state = 'BELOW_FAIL' if ratio < f else ('OK' if ratio >= p else 'BELOW_PASS')
        out_roles.append({'role': role, 'backend': b, 'ratio': ratio, 'pass_ratio': p, 'fail_ratio': f,
                          'baseline_median_tps': base, 'candidate_median_tps': cand,
                          'baseline_tps': tps['baseline'], 'candidate_tps': tps['candidate'],
                          'pairs': len(by_pair), 'quality': 'SAME' if same else 'DIFF', 'state': state})
    if any(r['state'] == 'BELOW_FAIL' or r['quality'] == 'DIFF' for r in out_roles):
        verdict = 'FAIL'
    elif all(r['state'] == 'OK' for r in out_roles):
        verdict = 'PASS'
    else:
        verdict = 'INCONCLUSIVE'
    return {'verdict': verdict, 'roles': out_roles,
            'quality_diffs': [{'role': r, 'pair': k, 'qid': q} for r, k, q in diffs]}


def verdict_doc(plan: dict) -> dict:
    results, missing = load_results(plan)
    base = {'schema': SCHEMA, 'plan_sha256': plan['plan_sha256'],
            'rule_sha256': plan['decision_rule']['sha256'], 'rule_path': plan['decision_rule']['path'],
            'cells': len(plan['cells']), 'missing': missing}
    if missing:
        return base | {'verdict': 'INCOMPLETE', 'roles': [], 'quality_diffs': []}
    return base | decide(plan, results)


def lines(doc: dict) -> list[str]:
    out = [f'M4-FOLD-VERDICT verdict={doc["verdict"]} roles={len(doc["roles"])} cells={doc["cells"]} '
           f'plan={doc["plan_sha256"]} rule={doc["rule_sha256"]}']
    for r in doc['roles']:
        out.append(f'ROLE {r["role"]} backend={r["backend"]} ratio={r["ratio"]:.4f} pass={r["pass_ratio"]} '
                   f'fail={r["fail_ratio"]} base_med={r["baseline_median_tps"]:.3f} '
                   f'cand_med={r["candidate_median_tps"]:.3f} n={r["pairs"]} quality={r["quality"]} {r["state"]}')
    out += [f'QUALITY_DIFF {d["role"]} pair={d["pair"]} qid={d["qid"]}' for d in doc['quality_diffs']]
    out += [f'MISSING {m}' for m in doc['missing']]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--out', type=Path, help='default: <result_root>/VERDICT.json')
    a = ap.parse_args(argv)
    fe = _fold_entry()
    try:
        plan = fe.load_plan(a.plan, verify_live=False)
    except fe.Refused as exc:
        print(f'M4-FOLD-VERDICT verdict=REFUSED {exc}')
        return 2
    doc = verdict_doc(plan)
    print('\n'.join(lines(doc)))
    target = a.out or Path(plan['result_root']) / 'VERDICT.json'
    with open(target, 'x') as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
    return {'PASS': 0, 'FAIL': 1, 'INCONCLUSIVE': 3}.get(doc['verdict'], 4)


if __name__ == '__main__':
    raise SystemExit(main())
