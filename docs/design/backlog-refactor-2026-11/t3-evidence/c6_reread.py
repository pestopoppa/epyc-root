#!/usr/bin/env python3
"""C6 re-read under the UNCHANGED predicates (zero inference; no GPU; no rebuild).
Stop rule (before computing): for each of the 11 codex-c6-*-20261102 dirs, run its OWN completion predicate (complete.py / build_complete.py /
test_revalidation.py / q4k-hardened-job/complete.py) read-only and, independently of RESULT.json, re-parse the raw native logs for the headline
numbers the ticked sub-bullets in autokernel-champion-aggregate.md cite. Stop when each dir has a verdict: REPRODUCES / NOT-RUN (no result artifact) /
FAILS. A predicate or parser failure is a defect to characterise; a modified predicate is out of scope (new generation).
Usage: c6_reread.py OUT.json"""
import collections, json, os, re, subprocess, sys
T = '/mnt/raid0/llm/tmp'
OWN = T + '/codex-c6-combined-20261102/owned-code'
def run(argv, cwd, extra=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **(extra or {}))
    p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
    return {'rc': p.returncode, 'tail': (p.stderr or p.stdout)[-240:].strip()}
PY = [sys.executable, '-B']
pred = {
 'combined': run(PY + ['complete.py'], T + '/codex-c6-combined-20261102'),
 'fp64-probe': run(PY + ['complete.py'], T + '/codex-c6-fp64-probe-20261102'),
 'mmvq-fix': run(PY + ['complete.py'], T + '/codex-c6-mmvq-fix-20261102'),
 'q4k-fix': run(PY + ['complete.py'], T + '/codex-c6-q4k-fix-20261102'),
 'remain-q4k': run(PY + ['complete.py'], T + '/codex-c6-remain-q4k-20261102'),
 'route-probe': run(PY + ['complete.py'], T + '/codex-c6-route-probe-20261102'),
 'q4k-hardened': run(PY + ['complete.py'], T + '/codex-c6-q4k-hardened-20261102/q4k-hardened-job'),
 'mmqfix(build)': run(PY + ['build_complete.py'], T + '/codex-c6-mmqfix-20261102'),
 'diag-validation': run(PY + ['test_revalidation.py'], T + '/codex-c6-diag-validation-20261102', {'PYTHONPATH': OWN}),
 'q4full': run(PY + ['complete.py'], T + '/codex-c6-q4full-20261102'),
 'q4k-probe': run(PY + ['complete.py'], T + '/codex-c6-q4k-probe-20261102'),
}
out = {'schema': 'brf-t3/c6-reread/1', 'predicates': pred}
# independent re-parse of headline numbers from raw logs
sys.path.insert(0, T + '/codex-c6-combined-20261102'); sys.dont_write_bytecode = True
sys.path.insert(0, OWN)
from strict_capture import read_complete  # the dir's own parser
comb = json.load(open(T + '/codex-c6-combined-20261102/RESULT.json')); run_dir = comb['run']
ops = {}
for op in ('MUL_MAT', 'MUL_MAT_ID', 'FLASH_ATTN_EXT'):
    rc = [r for r in comb['records'] if r['op'] == op][0]['native_rc']
    cases = read_complete(open(f'{run_dir}/{op}.log').read(), rc)
    ops[op] = {'native_rc': rc, 'n': len(cases), 'counts': dict(collections.Counter(c.status for c in cases)),
               'fail_types': dict(collections.Counter(re.search(r'type_a=(\w+)', c.params).group(1) for c in cases if c.status == 'fail'))}
out['combined_ops_reparsed'] = ops
out['claim_combined'] = {'MUL_MAT': {'ok': 1120, 'fail': 25, 'not_supported': 326, 'all_fail_q4_K': True}, 'MUL_MAT_ID_ok': 815, 'FLASH_ATTN_EXT': {'ok': 2978, 'not_supported': 2229}}
out['claim_combined_matches'] = (ops['MUL_MAT']['counts'] == {'ok': 1120, 'fail': 25, 'not_supported': 326} and ops['MUL_MAT']['fail_types'] == {'q4_K': 25}
    and ops['MUL_MAT_ID']['counts'].get('ok') == 815 and ops['MUL_MAT_ID']['native_rc'] == 0
    and ops['FLASH_ATTN_EXT']['counts'] == {'ok': 2978, 'not_supported': 2229} and ops['FLASH_ATTN_EXT']['native_rc'] == 0)
PROP = re.compile(r'AK_PROP_V2 metric=\S+ residual=(\S+) tolerance=(\S+) passed=(\d)')
def prop(path):
    ms = PROP.findall(open(path).read()); return [{'residual': r, 'tolerance': t, 'passed': p == '1'} for r, t, p in ms]
def one(d, rel):
    import glob
    return prop(glob.glob(f'{T}/{d}/runs/*/{rel}')[0])
out['single_case_reparsed'] = {
 'q4_0 mmvq-fix candidate (claim 0.0045127336805609736 < 0.0067690994136323929)': one('codex-c6-mmvq-fix-20261102', 'capture/stdout.log'),
 'q4_0 baseline route-probe C6 (claim 0.0086041991310414519)': one('codex-c6-route-probe-20261102', 'stdout.log'),
 'q4_K fix candidate (claim 0.0034182816219632496 < 0.0056649673550878913)': one('codex-c6-q4k-fix-20261102', 'capture/stdout.log'),
 'q4_K remaining n=5 ordinal 7047 baseline (claim 0.0086928737870828558 vs 0.0059480931310319316)': one('codex-c6-remain-q4k-20261102', 'baseline/stdout.log'),
 'q4_K remaining n=5 ordinal 7047 candidate': one('codex-c6-remain-q4k-20261102', 'candidate/stdout.log'),
}
q4k_h = [prop(p) for p in __import__('glob').glob(f'{T}/codex-c6-q4k-hardened-20261102/q4k-hardened-job/runs/*/c*/stdout.log')]
out['single_case_reparsed']['q4_K ordinal 7045 C5/C6 hardened (claim 0.0087896484419647033 vs 0.0056649673550878913)'] = q4k_h
claims = {'q4_0 mmvq-fix candidate': ('0.0045127336805609736', '0.0067690994136323929', True), 'q4_K fix candidate': ('0.0034182816219632496', '0.0056649673550878913', True)}
sc = out['single_case_reparsed']
out['single_case_claims_match'] = (sc['q4_0 mmvq-fix candidate (claim 0.0045127336805609736 < 0.0067690994136323929)'][0] == {'residual': '0.0045127336805609736', 'tolerance': '0.0067690994136323929', 'passed': True}
   and sc['q4_0 baseline route-probe C6 (claim 0.0086041991310414519)'][0]['residual'] == '0.0086041991310414519'
   and sc['q4_K fix candidate (claim 0.0034182816219632496 < 0.0056649673550878913)'][0] == {'residual': '0.0034182816219632496', 'tolerance': '0.0056649673550878913', 'passed': True}
   and all(x[0]['residual'] == '0.0086928737870828558' and not x[0]['passed'] for k, x in sc.items() if 'ordinal 7047' in k)
   and all(x and x[0]['residual'] == '0.0087896484419647033' and not x[0]['passed'] for x in q4k_h) and len(q4k_h) == 2)
out['verdict'] = {k: ('REPRODUCES' if v['rc'] == 0 else ('NOT-RUN (no RESULT artifact)' if 'No such file' in v['tail'] else 'FAILS')) for k, v in pred.items()}
json.dump(out, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print(json.dumps(out['verdict'], indent=1)); print('combined claims match:', out['claim_combined_matches'], '| single-case claims match:', out['single_case_claims_match'])
