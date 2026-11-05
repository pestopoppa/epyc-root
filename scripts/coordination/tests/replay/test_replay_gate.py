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
