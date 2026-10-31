"""VB-LOOP-SCOPE: a scope re-observation is benign to fold and gate, and ingest is idempotent.

What is pinned:

1. A claim already live in the ledger WITHOUT applicability gets exactly ONE new frame -- a
   source_observed for the same source_id carrying the scope -- and nothing else: no second
   claim frame, no second support frame.
2. That frame moves nothing the fold or the gate decide: every belief's `as_dict()` (grades,
   witnesses, corrections, review flags), its support-path and source counts, and the gate's
   outcome/reasons are identical before and after. Only the loop reader's scope view changes.
3. Re-running is a no-op; a re-projection that disagrees with the recorded claim, a withdrawn
   claim, and partial ledger state are reported and never written.
"""
from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VIDYA = ROOT / "scripts" / "vidya"
sys.path.insert(0, str(VIDYA))

import loop_beliefs as lb  # noqa: E402
from claim_tuple import ClaimTuple, to_frames  # noqa: E402
from fold import FT_RETRACT, FT_SOURCE, fold  # noqa: E402
from frames import make_frame  # noqa: E402
from gate import UsePolicy, evaluate  # noqa: E402
from lattice import parse_grade  # noqa: E402
from ledger import Ledger  # noqa: E402
from scoped_ingest import append_scoped, scope_aware_frames  # noqa: E402

T0 = "2026-10-01T00:00:00Z"
T1 = "2026-10-21T00:00:00Z"
AS_OF = "2026-10-21T12:00:00Z"
SCOPE = {"device": "epyc-9655", "backend": "cpu", "run_id": "results-x-20261001T000000Z"}
POLICY = UsePolicy(use="planner-context", floor=parse_grade("Judged/Located"))
TARGET = lb.Target.from_mapping({"model_path": "/m/Some-Model-Q8_0.gguf", "quant": "Q8_0",
                                 "backend": "cpu"})


def _tuple(ident: str, value: float = 400.0, **kw) -> ClaimTuple:
    base = dict(measurement_id=ident, metric="bench_readbw.read-sum", value=value,
                date="2026-10-01T00:00:00Z", category="CANDIDATE",
                claim=f"{ident} read-sum = {value} GB/s", protocol_id="inf70.bench_readbw_block.v1",
                reps=5, unit="GB/s", attestation_locator=f"/runs/x/{ident}.txt",
                attestation_sha256="a" * 64, attestation_present=False,
                source_kind="inf70-roofline-measurement")
    base.update(kw)
    return ClaimTuple(**base)


def _frames(tup: ClaimTuple, at: str) -> list[dict]:
    return to_frames(tup, as_of=at, adapter_id="test.adapter/v1", authority="measurement")


def _fold_view(frames: list[dict]) -> dict:
    result = fold(frames, as_of=AS_OF)
    view = {}
    for cid, belief in sorted(result.beliefs.items()):
        verdict = evaluate(cid, result, POLICY)
        view[cid] = {"belief": belief.as_dict(), "pro_paths": len(belief.pro_paths),
                     "con_paths": len(belief.con_paths), "pro_sources": len(belief.pro_sources),
                     "gate": (verdict.outcome, tuple(verdict.reasons),
                              tuple(map(str, verdict.required_next_actions)))}
    return view


def _ledger(*tuples: ClaimTuple) -> list[dict]:
    out: list[dict] = []
    for tup in tuples:
        out.extend(_frames(tup, T0))
    return out


def test_rescope_emits_one_source_frame_and_is_benign_to_fold_and_gate():
    old = _tuple("inf70_a")
    other = _tuple("inf70_b", value=300.0, applicability=dict(SCOPE))
    existing = _ledger(old, other)
    rescoped = dataclasses.replace(old, applicability=dict(SCOPE))
    kept, report = scope_aware_frames(existing, _frames(rescoped, T1), as_of=AS_OF)

    assert report["rescoped"] == 1 and report["new_claims"] == 0 and report["refused"] == []
    assert len(kept) == 1 and kept[0]["frame_type"] == FT_SOURCE
    assert kept[0]["assertion"]["source_id"] == "src_inf70_a"
    assert kept[0]["assertion"]["applicability"] == SCOPE

    before, after = _fold_view(existing), _fold_view(existing + kept)
    assert after == before  # grades, witnesses, flags, path/source counts, gate: all unchanged
    assert after["clm_inf70_a"]["pro_paths"] == 1  # support is never double-counted

    # ... and the loop reader now sees the scope (last source_observed per source_id wins).
    seen_before = lb.evaluate_frames(existing, [TARGET], as_of=AS_OF)
    seen_after = lb.evaluate_frames(existing + kept, [TARGET], as_of=AS_OF)
    # A device-only scope is HOST tier (belief redesign §7.1): shown as host context, never a
    # reliance-eligible claim id.
    assert "clm_inf70_a" not in [c["claim_id"] for c in seen_before["claims"]]
    assert "clm_inf70_a" in seen_after["host_claim_ids"]
    assert "clm_inf70_a" not in seen_after["claim_ids"]


def test_rescope_is_idempotent():
    old = _tuple("inf70_a")
    existing = _ledger(old)
    incoming = _frames(dataclasses.replace(old, applicability=dict(SCOPE)), T1)
    kept, _ = scope_aware_frames(existing, incoming, as_of=AS_OF)
    again, report = scope_aware_frames(existing + kept, incoming, as_of=AS_OF)
    assert again == [] and report["already_present"] == 1 and report["rescoped"] == 0


def test_new_claim_appends_the_whole_bundle_once():
    tup = _tuple("inf70_new", applicability=dict(SCOPE))
    incoming = _frames(tup, T1) + _frames(tup, T1)  # a repeated path projects it twice
    kept, report = scope_aware_frames([], incoming, as_of=AS_OF)
    assert report["new_claims"] == 1 and len(kept) == 3
    assert scope_aware_frames(kept, incoming, as_of=AS_OF)[0] == []


def test_diverged_reprojection_is_reported_not_written():
    old = _tuple("inf70_a")
    changed = dataclasses.replace(old, claim="a different statement", applicability=dict(SCOPE))
    kept, report = scope_aware_frames(_ledger(old), _frames(changed, T1), as_of=AS_OF)
    assert kept == [] and report["refused"][0]["reason"].startswith("diverged")


def test_withdrawn_claim_is_never_revived_or_rescoped():
    old = _tuple("inf70_a")
    existing = _ledger(old)
    support = next(f for f in existing if f["frame_type"].endswith("evidence_supports_claim/v1"))
    existing.append(make_frame(frame_type=FT_RETRACT, assertion={"retracts": support["frame_id"]},
                               provenance={"method": "test", "reason": "withdrawn"},
                               actor=support["pubinfo"]["actor"], authority_scope="measurement", created_at=T0))
    incoming = _frames(dataclasses.replace(old, applicability=dict(SCOPE)), T1)
    kept, report = scope_aware_frames(existing, incoming, as_of=AS_OF)
    assert kept == [] and "no live evidence" in report["refused"][0]["reason"]


def test_partial_ledger_state_is_refused():
    old = _tuple("inf70_a")
    existing = [f for f in _ledger(old) if f["frame_type"] == FT_SOURCE]
    incoming = _frames(dataclasses.replace(old, applicability=dict(SCOPE)), T1)
    kept, report = scope_aware_frames(existing, incoming, as_of=AS_OF)
    assert kept == [] and report["refused"][0]["reason"] == "partial ledger state"


def test_append_scoped_writes_through_the_ledger_and_keeps_the_chain(tmp_path):
    ledger = Ledger(tmp_path / "ledger.jsonl")
    old = _tuple("inf70_a")
    for frame in _frames(old, T0):
        ledger.append(frame)
    incoming = _frames(dataclasses.replace(old, applicability=dict(SCOPE)), T1)
    assert append_scoped(ledger, incoming, as_of=AS_OF, dry_run=True)["frames"] == 1
    assert len(ledger) == 3
    assert append_scoped(ledger, incoming, as_of=AS_OF)["rescoped"] == 1
    assert append_scoped(ledger, incoming, as_of=AS_OF)["frames"] == 0
    assert len(ledger) == 4 and ledger.verify() == []


def test_cli_inf70_only_new_rescopes_then_is_idempotent(tmp_path):
    """The real fixture run, through `cli.py ingest inf70 --only-new`: an unscoped prior ingest
    gains its scope with one frame per source, and a re-run appends nothing."""
    from adapters import inf70_roofline_ledger as reader

    import shutil

    fixture = tmp_path / "corpus"  # `discover()` walks `results*` run directories
    shutil.copytree(Path(__file__).resolve().parent / "fixtures" / "inf70_run",
                    fixture / "results-c5v2-20260902T103808Z")
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = Ledger(ledger_path)
    rows = [reader.project(n)
            for n in reader.native_rows(fixture / "results-c5v2-20260902T103808Z")]
    assert rows and all(t.applicability for t in rows)
    for tup in rows:  # the pre-VB-LOOP-SCOPE ledger: same claims, no scope
        for frame in to_frames(dataclasses.replace(tup, applicability={}), as_of=T0,
                               adapter_id=reader.ADAPTER_ID, authority=reader.AUTHORITY):
            ledger.append(frame)
    base = len(ledger)

    def run(at: str) -> dict:
        out = subprocess.run([sys.executable, str(VIDYA / "cli.py"), "--ledger", str(ledger_path),
                              "--json", "ingest", "inf70", "--root", str(fixture), "--only-new",
                              "--as-of", at], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    first = run(T1)
    assert first["only_new"]["rescoped"] == len(rows) and first["only_new"]["new_claims"] == 0
    assert len(Ledger(ledger_path)) == base + len(rows)
    second = run(AS_OF)
    assert second["only_new"]["frames"] == 0 and second["only_new"]["already_present"] == len(rows)
    assert Ledger(ledger_path).verify() == []


# --- P1-B / P1-D / P1-C wiring: v2 beside v1, floors, incremental experiments -----------------

import hashlib  # noqa: E402
import shutil  # noqa: E402
import sqlite3  # noqa: E402

import scoped_ingest as si  # noqa: E402

P1 = Path(__file__).resolve().parent / "fixtures" / "belief_p1"


def _p1_store(tmp_path: Path, label: str) -> Path:
    """A copy of one real-derived capture laid out as a loop store."""
    src = P1 / "serving" / label
    assert (src / "serving-beliefs").is_dir(), "derive the P1 fixtures first"
    dst = tmp_path / "campaign" / f"store-{label}"
    shutil.copytree(src, dst)
    return dst


def test_v2_capture_claim_is_ingested_beside_the_v1_arms(tmp_path):
    store = _p1_store(tmp_path, "q38fn")
    ledger = Ledger(tmp_path / "ledger.jsonl")
    first = si.ingest_scoped_store(ledger, store, as_of=AS_OF)
    assert first["rows_projected"] == 2 and first["v2_projected"] == 1
    assert first["new_claims"] == 3 and first["frames_appended"] == 9
    sids = [r.frame["assertion"]["source_id"] for r in ledger.read_all()
            if r.frame["frame_type"] == FT_SOURCE]
    assert sum(s.startswith("src_legacy-serving-v2:") for s in sids) == 1
    second = si.ingest_scoped_store(ledger, store, as_of=T1)
    assert second["receipts_known"] == 1 and second["frames_appended"] == 0


def test_a_pre_p1b_capture_is_reopened_once_for_its_v2_claim(tmp_path):
    from adapters import autokernel_legacy_serving as serving

    store = _p1_store(tmp_path, "ds41")
    (receipt,) = sorted((store / "serving-beliefs").glob("*.json"))
    raw = receipt.read_bytes()
    natives = serving.native_rows(json.loads(raw), receipt_locator=f"autokernel:{receipt}",
                                  receipt_sha256=hashlib.sha256(raw).hexdigest())
    ledger = Ledger(tmp_path / "ledger.jsonl")
    for native in natives:  # the ledger as VB-LOOP-SCOPE left it: scoped v1 arms only
        for frame in to_frames(serving.project(native), as_of=T0,
                               adapter_id=serving.ADAPTER_ID, authority=None):
            ledger.append(frame)
    assert si._ledger_capture_ids([r.frame for r in ledger.read_all()]) == set()
    report = si.ingest_scoped_store(ledger, store, as_of=AS_OF)
    assert report["receipts_read"] == 1 and report["new_claims"] == 1
    assert report["already_present"] == 2 and report["frames_appended"] == 3
    assert si._ledger_capture_ids([r.frame for r in ledger.read_all()]) == {receipt.stem}


def test_floor_is_ingested_once_with_its_store_manifest_scope(tmp_path):
    store = tmp_path / "store-q27b"
    shutil.copytree(P1 / "floor" / "q27b", store)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    first = si.ingest_scoped_store(ledger, store, as_of=AS_OF)
    assert first["floors_listed"] == 1 and first["floors_projected"] == 1
    assert first["new_claims"] == 1 and first["frames_appended"] == 3
    source = next(r.frame for r in ledger.read_all() if r.frame["frame_type"] == FT_SOURCE)
    assert source["assertion"]["applicability"]["model_file"].endswith("Qwen3.8-27B-Q8_0.gguf")
    assert source["assertion"]["applicability"]["scope_basis"] == "store_manifest"
    second = si.ingest_scoped_store(ledger, store, as_of=T1)
    assert second["floors_known"] == 1 and second["frames_appended"] == 0


class _FakeExperiments:
    """Lane C's interface (native_rows / project / build_store_manifest), over a tiny db."""

    ADAPTER_ID = "test.fake_experiments/v1"
    AUTHORITY = "measurement"

    def __init__(self):
        self.manifest_builds = 0
        self.since_calls = []

    def build_store_manifest(self, store, label=None, overrides=None):
        self.manifest_builds += 1
        return {"store": str(store), "scope": {"model_file": "/m/x.gguf", "backend": "cpu"}}

    def native_rows(self, store_dir, since_rowid=None):
        self.since_calls.append(since_rowid)
        conn = sqlite3.connect(f"file:{Path(store_dir) / 'experiments.db'}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT rowid, attempt_id, status FROM experiments WHERE rowid > ?"
                                " ORDER BY rowid", (since_rowid or 0,)).fetchall()
        finally:
            conn.close()
        return [{"rowid": r, "attempt_id": a, "status": s} for r, a, s in rows]

    def project(self, row, *, store_manifest):
        if row["status"] == "planner_transient":
            return None
        return ClaimTuple(measurement_id=f"ak-exp:v1:test:{row['attempt_id']}",
                          metric="aggregate_tok_s", value=20.0, date=T0, category="CANDIDATE",
                          claim=f"{row['attempt_id']} {row['status']}",
                          source_kind="autokernel-experiment",
                          applicability=dict(store_manifest["scope"], scope_basis="store_manifest"),
                          observation={"outcome": "null", "outcome_native": row["status"],
                                       "retrofit": True})


def _exp_store(tmp_path: Path, rows) -> Path:
    store = tmp_path / "store-exp"
    store.mkdir()
    conn = sqlite3.connect(store / "experiments.db")
    conn.execute("CREATE TABLE experiments (attempt_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
    conn.executemany("INSERT INTO experiments VALUES (?, ?)", rows)
    conn.commit()
    conn.close()
    return store


def _insert(store: Path, rows) -> None:
    conn = sqlite3.connect(store / "experiments.db")
    conn.executemany("INSERT INTO experiments VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def test_experiments_are_read_incrementally_above_the_memo_watermark(tmp_path, monkeypatch):
    fake = _FakeExperiments()
    monkeypatch.setattr(si, "_experiments_adapter", lambda: fake)
    store = _exp_store(tmp_path, [("a1", "measured_null"), ("a2", "planner_transient")])
    ledger, memo = Ledger(tmp_path / "ledger.jsonl"), tmp_path / "memo.json"
    first = si.ingest_scoped_store(ledger, store, as_of=AS_OF, memo_path=memo)
    assert fake.since_calls == [None]  # a small db with no watermark: complete read
    assert first["experiments_rows_read"] == 2 and first["experiments_projected"] == 1
    assert first["new_claims"] == 1
    body = json.loads(memo.read_text())
    assert body["watermarks"] == {str(store / "experiments.db"): 2}
    assert fake.manifest_builds == 1

    second = si.ingest_scoped_store(ledger, store, as_of=T1, memo_path=memo)
    assert fake.since_calls == [None]  # nothing above the watermark: the adapter is not called
    assert second["frames_appended"] == 0

    _insert(store, [("a3", "regression")])
    third = si.ingest_scoped_store(ledger, store, as_of=T1, memo_path=memo)
    assert fake.since_calls == [None, 2] and third["experiments_rows_read"] == 1
    assert third["new_claims"] == 1
    assert fake.manifest_builds == 1  # cached per store in the memo, not rebuilt per step
    assert json.loads(memo.read_text())["watermarks"][str(store / "experiments.db")] == 3


def test_a_large_db_without_a_watermark_defers_history_to_the_backfill(tmp_path, monkeypatch):
    fake = _FakeExperiments()
    monkeypatch.setattr(si, "_experiments_adapter", lambda: fake)
    monkeypatch.setattr(si, "_FULL_READ_BYTES", 0)
    store = _exp_store(tmp_path, [("a1", "measured_null"), ("a2", "kept")])
    ledger, memo = Ledger(tmp_path / "ledger.jsonl"), tmp_path / "memo.json"
    report = si.ingest_scoped_store(ledger, store, as_of=AS_OF, memo_path=memo)
    assert fake.since_calls == [] and report["experiments_projected"] == 0
    assert report["experiments_deferred"][0]["watermark"] == 2
    _insert(store, [("a3", "regression")])
    later = si.ingest_scoped_store(ledger, store, as_of=T1, memo_path=memo)
    assert fake.since_calls == [2] and later["experiments_projected"] == 1


def test_experiments_full_is_the_backfill(tmp_path, monkeypatch):
    fake = _FakeExperiments()
    monkeypatch.setattr(si, "_experiments_adapter", lambda: fake)
    monkeypatch.setattr(si, "_FULL_READ_BYTES", 0)
    store = _exp_store(tmp_path, [("a1", "measured_null"), ("a2", "kept")])
    report = si.ingest_scoped_store(Ledger(tmp_path / "ledger.jsonl"), store, as_of=AS_OF,
                                    experiments_full=True)
    assert fake.since_calls == [None] and report["experiments_projected"] == 2


def test_dry_run_advances_no_watermark(tmp_path, monkeypatch):
    fake = _FakeExperiments()
    monkeypatch.setattr(si, "_experiments_adapter", lambda: fake)
    store = _exp_store(tmp_path, [("a1", "measured_null")])
    memo = tmp_path / "memo.json"
    si.ingest_scoped_store(Ledger(tmp_path / "ledger.jsonl"), store, as_of=AS_OF,
                           memo_path=memo, dry_run=True)
    assert not memo.exists()


def test_without_lane_c_the_experiments_path_is_inert(tmp_path, monkeypatch):
    import adapters

    # Both doors closed: the package attribute (set if lane C's module was imported earlier in
    # the session) and the module cache entry (None makes the import raise ImportError).
    monkeypatch.delattr(adapters, "autokernel_experiments", raising=False)
    monkeypatch.setitem(sys.modules, "adapters.autokernel_experiments", None)
    assert si._experiments_adapter() is None
    store = _exp_store(tmp_path, [("a1", "measured_null")])
    report = si.ingest_scoped_store(Ledger(tmp_path / "ledger.jsonl"), store, as_of=AS_OF)
    assert report["experiments_adapter"] is False and report["frames_appended"] == 0


def test_an_older_memo_without_watermarks_still_reads(tmp_path):
    memo = tmp_path / "memo.json"
    memo.write_text(json.dumps({"schema": si.MEMO_SCHEMA, "refused": {"x": {"stat": [1, 2]}}}))
    assert si._read_memo(memo) == {"x": {"stat": [1, 2]}}
    assert si._read_memo_body(memo).get("watermarks") is None
