#!/usr/bin/env python3
"""CAP-06 offline threshold replay, CS-45.1 derived results (zero inference, no segmentation change).
Stop rule (stated before computing): for each of the 5 tails (t0300 t0600 t1000 t3000 t4000), re-run the UNCHANGED
cs45/source/{adaptive,score}.py against the stored out/*.jsonl and compare the outputs byte-for-byte with the filed
derived/{adaptive.json,scores/results.json}. Stop when all 5 tails are reproduced or the first mismatch is characterised.
Operating points are NOT re-chosen: this reads the points the filed derivation chose on the selection split; the
confirmation split is read only as filed (no new selection). Nothing here can advance an arm (no human stratum).
Usage: cap06_reread.py OUT.json   (scratch outputs go under /mnt/raid0/llm/tmp/ws58-brf-t3b-scratch/cap06)"""
import hashlib, json, os, subprocess, sys
B = '/mnt/raid0/llm/tmp/codex3-next-cpu-prep-20261031-0110/cs45'
S = '/mnt/raid0/llm/tmp/ws58-brf-t3b-scratch/cap06'
TAILS = ['t0300', 't0600', 't1000', 't3000', 't4000']
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
res = {'schema': 'brf-t3/cap06-reread/1', 'source': B + '/results/derived', 'tails': {}}
for t in TAILS:
    R = f'{B}/results/derived/{t}'; O = f'{S}/{t}'; os.makedirs(O, exist_ok=True)
    env = dict(os.environ, CS45_OUTPUT=R, CS45_MANIFEST=R + '/manifest', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    rc = {}
    for name, arg in (('adaptive.py', O + '/adaptive.json'), ('score.py', O + '/scores')):
        p = subprocess.run([sys.executable, '-B', f'{B}/source/{name}', arg], env=env, capture_output=True, text=True)
        rc[name] = p.returncode
        if p.returncode: rc[name + '_stderr'] = p.stderr[-300:]
    same = {'adaptive.json': sha(O + '/adaptive.json') == sha(R + '/adaptive.json'),
            'scores/results.json': sha(O + '/scores/results.json') == sha(R + '/scores/results.json'),
            'adaptive.items.jsonl': sha(O + '/adaptive.json.items.jsonl') == sha(R + '/adaptive.json.items.jsonl'),
            'scores/items.jsonl': sha(O + '/scores/items.jsonl') == sha(R + '/scores/items.jsonl')}
    ad = json.load(open(R + '/adaptive.json')); sc = json.load(open(R + '/scores/results.json'))
    def row(b, split):
        m = b[split]; return {'recall': round(m['recall'], 3), 'eot_fpr': round(m['eot_fpr'], 3), 'inc_never_fired_censored': round(m['incomplete_never_fired_censored'], 3), 'n': m['n'], 'n_complete': m['n_complete'], 'n_incomplete': m['n_incomplete']}
    arms = {}
    for b in ad:
        key = 'smartturn_silero_adaptive' if b['arm'].startswith('smart') else 'parakeet_eou_adaptive:' + b['variant']
        arms[key] = {'tag': b['tag'], 'point': {k: b[k] for k in ('theta', 'gate_s', 'T_short', 'T_long') if k in b}, 'sel': row(b, 'sel'), 'conf': row(b, 'conf')}
    st = arms['smartturn_silero_adaptive']; pk = {k: v for k, v in arms.items() if k.startswith('parakeet')}
    feas = {k: v for k, v in pk.items() if v['tag'] == 'feasible'}  # FPR <= 0.10 on selection, as filed
    best_pk_sel = max(feas.items(), key=lambda kv: kv[1]['sel']['recall']) if feas else None
    res['tails'][t] = {'rc': rc, 'byte_identical_to_filed': same, 'config_echo': {k: sc['config_echo'][k] for k in ('n_clips', 'n_selection', 'n_confirmation', 'human_recorded_n', 'advance_eligible_strata')},
        'arms': arms, 'smartturn_tag': st['tag'], 'parakeet_feasible_variants': len(feas), 'parakeet_variants': len(pk),
        'separation_selection_recall_smartturn_minus_best_feasible_parakeet': round(st['sel']['recall'] - best_pk_sel[1]['sel']['recall'], 3) if best_pk_sel else None,
        'best_feasible_parakeet_by_selection': best_pk_sel[0] if best_pk_sel else None}
res['all_reproduced'] = all(all(v['byte_identical_to_filed'].values()) and not any(r for k, r in v['rc'].items() if k.endswith('.py')) for v in res['tails'].values())
json.dump(res, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print('all_reproduced', res['all_reproduced'])
for t, v in res['tails'].items():
    st = v['arms']['smartturn_silero_adaptive']; print(t, v['byte_identical_to_filed'], 'ST sel', st['sel']['recall'], st['sel']['eot_fpr'], st['sel']['inc_never_fired_censored'], 'conf', st['conf']['recall'], st['conf']['eot_fpr'], '| ST tag', v['smartturn_tag'], 'PK feasible', v['parakeet_feasible_variants'], '/', v['parakeet_variants'], 'best', v['best_feasible_parakeet_by_selection'], 'sep', v['separation_selection_recall_smartturn_minus_best_feasible_parakeet'])
