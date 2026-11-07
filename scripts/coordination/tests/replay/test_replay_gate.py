"""Replay gate tests - MUST pass before a rowflow deploy (scripts/coordination/rowflow/deploy_rowflow.sh).

The candidate is $ROWFLOW_CANDIDATE (a directory holding rowflow.py + siblings); default: this tree's rowflow/.
    ROWFLOW_CANDIDATE=/path/to/rowflow python3 -m pytest -q scripts/coordination/tests/replay
"""
import os
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay_allocator as RA  # noqa: E402
import replay_lib as RL  # noqa: E402
import scenarios as SC  # noqa: E402

CAND = os.path.abspath(os.environ.get("ROWFLOW_CANDIDATE", os.path.join(HERE, "..", "..", "rowflow")))


@pytest.fixture(scope="module")
def work():
    os.makedirs(RA.SCRATCH, exist_ok=True)
    return tempfile.mkdtemp(prefix="pytest-", dir=RA.SCRATCH)


# ------------------------------------------------------------------ harness self-tests (candidate-independent)
def test_trace_roundtrip(tmp_path):
    p = str(tmp_path / "t.jsonl.gz")
    w = RL.TraceWriter(p, "test")
    b = SC.row("a")
    w.tick(1.0, {"a": b}); w.tick(2.0, {"a": b})
    w.close()
    h, ticks = RL.read_trace(p)
    assert h["schema"] == RL.SCHEMA and len(ticks) == 2 and ticks[1]["rows"]["a"] == b
    assert sum(1 for l in __import__("gzip").open(p, "rt") if '"blob"' in l) == 1   # content-addressed


def test_oracle_resolves_python_thread_variable():
    p, text, files = SC.launcher("n", cls="cpu+gpu", claim="0-95", gpu_quiet="exclusive", role="bench")
    files["/x/job.py"] = SC.NPD1_JOB
    c = RL.contract_lite({"manifest": {"regions": "mi210_0,0-95"}, "launcher_text": text, "files": files})
    assert c["threads"] == 48 and c["evidence"] and c["timing"]


def test_oracle_workers1():
    b = SC.row("k", regions="0-95", claim="0-95", extra="gitnexus analyze --workers 1", man={"shape": "host"})
    c = RL.contract_lite(b)
    assert c["threads"] == 1 and not c["evidence"] and c["lock_ex_quarters"] == set(RL.QUARTERS)


def test_day_fixture_present():
    assert os.path.exists(RA.DAY_TRACE)
    _, ticks = RL.read_trace(RA.DAY_TRACE)
    assert len(ticks) > 100 and any(b["stopped"] for t in ticks for b in t["rows"].values())


# ------------------------------------------------------------------ deploy-blocking: scenarios
@pytest.mark.parametrize("name", list(SC.SCENARIOS))
def test_scenario(name, work):
    tpath, check = SC.SCENARIOS[name](os.path.join(work, name + ".trace.jsonl"))
    dec, err = RA.worker(CAND, tpath, os.path.join(work, "out", name))
    assert dec is not None, err
    _, ticks = RL.read_trace(tpath)
    inv = RL.check_invariants(ticks, dec)
    viol = list(check(dec))
    for k in SC.SUBJECT.get(name, []) + ["INV-NO-CRASH", "INV-STOP", "INV-1THREAD", "INV-EVIDENCE"]:
        viol += [f"{k}: {x}" for x in inv.get(k, [])]
    assert not viol, "\n".join(viol[:10])


# ------------------------------------------------------------------ negative control: the rule gpu-q3 NARROW replaces
OLD_GPU_Q3_LINE = 'GPU_Q3_TOKENS = frozenset({GPU, "q3"} | {f"t{k}" for k in range(184, 192)})   # OLD: whole q3\n'


def test_negative_control_old_gpu_q3_rule_refuses_timing_beside_q3_build(work):
    """operator 2026-11-05 (NARROW): a copy of the candidate with the pre-NARROW gpu-q3 option (gpu-quiet + ALL of q3 +
    184-191) must fail the concurrency scenario - proving the scenario detects the q38p4b-int8 refusal, not a tautology."""
    import re
    import shutil
    old = os.path.join(work, "old-gpu-q3-cand")
    shutil.copytree(CAND, old, ignore=shutil.ignore_patterns("__pycache__", "*.bak*"))
    src = os.path.join(old, "rowflow.py")
    text = open(src).read()
    text, n = re.subn(r"^GPU_Q3_TOKENS = .*\n", OLD_GPU_Q3_LINE, text, count=1, flags=re.M)
    assert n == 1, "GPU_Q3_TOKENS definition not found in the candidate"
    open(src, "w").write(text)
    name = "gpu-timing-narrow-q3-concurrent-with-8core-build"
    tpath, check = SC.SCENARIOS[name](os.path.join(work, name + ".neg.trace.jsonl"))
    dec, err = RA.worker(old, tpath, os.path.join(work, "out", name + "-old"))
    assert dec is not None, err
    viol = list(check(dec))
    assert viol and any("never granted beside" in v or "not concurrent" in v for v in viol), \
        f"the old whole-q3 rule should refuse the GPU timing row beside the 8-core q3 build; got {viol}"


# ------------------------------------------------------------------ deploy-blocking: the 2026-11-05 day replay
def test_day_replay_blocking_invariants(work):
    dec, err = RA.worker(CAND, RA.DAY_TRACE, os.path.join(work, "day"))
    assert dec is not None, err
    _, ticks = RL.read_trace(RA.DAY_TRACE)
    inv = RL.check_invariants(ticks, dec)
    bad = {k: v for k, v in inv.items() if v and k in RA.DAY_BLOCKING}
    print("idle metrics", RL.idle_metrics(dec))
    assert not bad, "\n".join(f"{k}: {v[0]}" for k, v in bad.items())


# ------------------------------------------------------------------ deploy-blocking: PUBLISH-path scenarios
@pytest.mark.parametrize("name", sorted(SC.PUBLISH_SCENARIOS))
def test_publish_scenario(name, tmp_path):
    import importlib.util
    spec_ = importlib.util.spec_from_file_location("rowflow_cand_publish", os.path.join(CAND, "rowflow.py"))
    sys.path.insert(0, CAND)
    try:
        rf = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(rf)
    finally:
        sys.path.remove(CAND)
    root = str(tmp_path)
    flags = os.path.join(root, "compute-flags")
    os.makedirs(os.path.join(flags, "ready")); os.makedirs(os.path.join(flags, "grants"))
    rf.TMP = root + "/"
    spec, check = SC.PUBLISH_SCENARIOS[name](root)
    row, err = None, None
    try:
        row = rf.publish(spec, flags)
    except rf.Refused as e:
        err = str(e)
    import inspect
    v = check(row, err, rf) if len(inspect.signature(check).parameters) >= 3 else check(row, err)
    assert not v, "\n".join(v)

# ------------------------------------------------------------------ negative controls: friction pass-4 fixes (2026-11-06)
# Each fix is guarded by a module flag; a copy of the candidate with the flag OFF (the pre-fix keeper) must FAIL the
# scenario that the fix is deployed for - proving each scenario detects the incident class, not a tautology.
P4_CONTROLS = [
    ("PRECOND_PARK_ONCE", "p4-precond-refusal-parks-once", ("FAIL records per tick", "re-admitted")),
    ("COMPLETE_BEFORE_RC14", "p4-completed-row-not-rc14", ("got a FAIL record",)),
    ("GPU_IDLE_BY_DEVICE", "p4-gpu-harness-with-kfd-never-idle-held", ("read IDLE-HELD",)),
    ("GPU_IDLE_BY_DEVICE", "p4-gpu-grant-cpu-regions-not-judged", ("by CPU %",)),
    ("OVERRIDE_BOOKS_WIDTH", "override-multiquarter-books-two", ("2-quarter row granted",)),   # negative control: old code grants 1
    ("LOG_ON_TRANSITION", "p5-idle-held-logs-once", ("transition only",)),   # Pass 5 item 3: the pre-fix keeper logs every tick
]


def _candidate_with_flag_off(work, flag):
    import re
    import shutil
    old = os.path.join(work, f"old-{flag.lower()}-cand")
    if not os.path.isdir(old):
        shutil.copytree(CAND, old, ignore=shutil.ignore_patterns("__pycache__", "*.bak*"))
        src = os.path.join(old, "rowflow.py")
        text = open(src).read()
        text, n = re.subn(rf"^{flag} = True\b", f"{flag} = False", text, count=1, flags=re.M)
        assert n == 1, f"{flag} = True not found in the candidate"
        open(src, "w").write(text)
    return old


@pytest.mark.parametrize("flag,name,expect", P4_CONTROLS, ids=[f"{f}:{n}" for f, n, _ in P4_CONTROLS])
def test_negative_control_pass4_old_rule_fails_scenario(flag, name, expect, work):
    old = _candidate_with_flag_off(work, flag)
    tpath, check = SC.SCENARIOS[name](os.path.join(work, name + f".neg-{flag}.trace.jsonl"))
    dec, err = RA.worker(old, tpath, os.path.join(work, "out", name + f"-old-{flag}"))
    assert dec is not None, err
    viol = list(check(dec))
    assert viol and any(e in v for v in viol for e in expect), \
        f"with {flag} off the old keeper should fail {name} ({expect}); got {viol}"


def test_negative_control_width_justification_old_code_refuses_justified_multiquarter(work, tmp_path):
    """With WIDTH_JUSTIFICATION off (the pre-change publish gate) the justified multi-quarter scenario must FAIL."""
    import importlib.util
    old = _candidate_with_flag_off(work, "WIDTH_JUSTIFICATION")
    spec_ = importlib.util.spec_from_file_location("rowflow_old_wj", os.path.join(old, "rowflow.py"))
    sys.path.insert(0, old)
    try:
        rf = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(rf)
    finally:
        sys.path.remove(old)
    root = str(tmp_path)
    flags = os.path.join(root, "compute-flags")
    os.makedirs(os.path.join(flags, "ready")); os.makedirs(os.path.join(flags, "grants"))
    rf.TMP = root + "/"
    spec, check = SC.PUBLISH_SCENARIOS["publish-wj-justified-multiquarter-accepted"](root)
    row, err = None, None
    try:
        row = rf.publish(spec, flags)
    except rf.Refused as e:
        err = str(e)
    assert check(row, err, rf), "the old code should refuse the justified multi-quarter row"


def test_negative_control_multiquarter_q3_rule_off_grants_q1_q3(work):
    """operator 2026-11-06: with the q0-q2-only rule removed (the 15804eaf5 behaviour) the same trace grants q1+q3."""
    import re
    import shutil
    old = os.path.join(work, "old-mq-q3-cand")
    shutil.copytree(CAND, old, ignore=shutil.ignore_patterns("__pycache__", "*.bak*"))
    src = os.path.join(old, "rowflow.py")
    text, n = re.subn(r'if shape\.startswith\("multi-quarter\("\) and not gpu_tok:', "if False:", open(src).read(), count=1)
    assert n == 1, "the multi-quarter q0-q2 rule was not found in the candidate"
    open(src, "w").write(text)
    name = "multiquarter-never-q3"
    tpath, check = SC.SCENARIOS[name](os.path.join(work, name + ".neg.trace.jsonl"))
    dec, err = RA.worker(old, tpath, os.path.join(work, "out", name + "-old"))
    assert dec is not None, err
    viol = list(check(dec))
    assert viol and any("q3" in v for v in viol), f"without the rule the row should be granted q1+q3; got {viol}"
