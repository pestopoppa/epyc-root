#!/usr/bin/env python3
"""gate_compare_env.py -- gate_compare.py (the AK loop's own serving.compare, matched_process_v2) with ONE extra capability:
`--cand-env KEY=VAL` (repeatable) puts that env into the CANDIDATE arm's resolved launch only, so a same-source-tree env knob
(V11-086: GGML_FA_VKQ_REG=1|auto on the fa-vkq build) can be A/B'd against the champion build.

Why a wrapper and not an edit: the loop's matched frame (serving._matched_frame) refuses arms that differ in environment
("same_workload_source_build_treatment_only"). Here the declared knob IS the treatment, so the wrapper (a) rebinds the second
run._cpu_arm() call (the candidate) with extra_env -- the loop's own provision for declared extra keys, which moves
execution_digest and adds the key to allowed_inherit_keys -- and (b) removes exactly those keys from the frame comparison.
Nothing in the loop tree or the campaign stores is modified; gate_compare.py is imported unchanged.  After an --execute it checks
that the knob really is in the candidate launch record (rc 7 otherwise).

usage: gate_compare_env.py {ds41|q38fn} --anchor-build D --cand-build D --cand-env K=V [--pairs 5] --out DIR {--dry-run|--execute}
"""
import json, sys
from pathlib import Path

argv = sys.argv[1:]
ENV, rest, i = {}, [], 0
while i < len(argv):
    if argv[i] == "--cand-env":
        k, _, v = argv[i + 1].partition("="); ENV[k] = v; i += 2
    else: rest.append(argv[i]); i += 1
if not ENV: sys.exit("gate_compare_env.py: --cand-env KEY=VAL required (use gate_compare.py for build-only A/B)")
sys.argv = [sys.argv[0]] + rest
sys.path.insert(0, "/mnt/raid0/llm/tmp/fold-allkeeps-20261004")
import gate_compare as G                      # pins the code root (sys.path) per surface at import
from scripts.kernel_rnd.autokernel.loop import run as R, serving

_calls = {"n": 0}
_orig_arm = R._cpu_arm
def _arm(original, build, *, extra_env=None):
    _calls["n"] += 1
    if _calls["n"] == 2:                       # gate_compare.main(): 1st call = anchor, 2nd = candidate
        extra_env = {**(extra_env or {}), **ENV}
    return _orig_arm(original, build, extra_env=extra_env)
R._cpu_arm = _arm
_orig_frame = serving._matched_frame
def _frame(recipe, resolved, frozen):
    f = _orig_frame(recipe, resolved, frozen)
    f["environment"] = {k: v for k, v in f["environment"].items() if k not in ENV}
    return f
serving._matched_frame = _frame

rc = G.main()
if rc == 0 and "--execute" in rest:
    out = Path(rest[rest.index("--out") + 1])
    rec = next(iter(out.glob("compare-*.json")), None)
    txt = rec.read_text() if rec else ""
    hit = all(k in txt for k in ENV)
    print(f"ENV_PROOF knob(s) {sorted(ENV)} in candidate launch record: {'yes' if hit else 'NO'}")
    if not hit: rc = 7
sys.exit(rc)
