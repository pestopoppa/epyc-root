"""The shared agent-loop belief reader: mandatory freshness, refusal + alarm, evidence buckets,
known-good snapshots and degraded-mode seed checks.

Fixture ledgers go through the real write path (`ClaimTuple` -> `to_frames` -> `Ledger`), so the
grade a test sees is what `claim_tuple.grade()` assigned and `fold()` kept. Freshness uses a fake
sync module (the plumbing `sync.py` may not be on this branch); alarms go to a tmp state/config.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import loop_beliefs as lb  # noqa: E402
from claim_tuple import ClaimTuple, to_frames  # noqa: E402
from frames import make_frame  # noqa: E402
from ledger import Ledger  # noqa: E402

KVQ = "kv-quant-27b-v10-measurement"
AS_OF = "2026-09-24T12:00:00+00:00"
WRITTEN = "2026-09-24T10:00:00+00:00"
SHA = "a" * 64
GPU_27B = {"model_path": "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf", "quant": "Q8_0",
           "backend": "gpu"}
DS41_CPU = {"model_path": "/mnt/raid0/llm/models/DeepSeek-V4.1-Flash-Q4.gguf", "quant": "Q4_K",
            "backend": "cpu"}
ARMS = ("A_f16_kv", "B_q8_0_kv", "C_q4_0_kv")
DEPTHS = ("d2k", "d32k")
METRICS = ("gpu_decode_tps", "gpu_prefill_tps")


# ------------------------------------------------------------------------------ fixtures


def _kvq(run, arm, depth, metric, *, date="2026-09-24"):
    return ClaimTuple(
        measurement_id=f"kvq-{run}-{arm}-{depth}-{metric}", metric=metric, value=100.0,
        date=date, category="BASELINE" if arm == "A_f16_kv" else "CANDIDATE",
        claim=f"{arm} {metric} at {depth}: 100.0 tokens/s (fixture).",
        protocol_id="P-GPU-1", reps=5, reps_basis="scored", unit="tokens/s",
        attestation_sha256=SHA,
        attestation_locator=f"kvq:{run}:{arm}:{depth}:{metric}|data/run/summary.json#sha256={SHA}",
        attestation_present=True, attestation_verified=True, source_kind=KVQ)


def _kvq_run(run="run-20260924T100000Z", **kw):
    return [_kvq(run, a, d, m, **kw) for a in ARMS for d in DEPTHS for m in METRICS]


def _scoped(ident, *, model="DeepSeek-V4.1-Flash-Q4.gguf", device="epyc-9655", backend="cpu",
            kind="ak-fixture-measurement", text=None, run_id=None):
    scope = {"device": device, "backend": backend}
    if model:
        scope["model_file"] = f"/mnt/raid0/llm/models/{model}"
    if run_id:
        scope["run_id"] = run_id
    return ClaimTuple(
        measurement_id=ident, metric="decode_tps", value=20.0, date="2026-09-24",
        category="CANDIDATE", claim=text or f"{ident}: candidate decode 20.0 tokens/s (fixture).",
        protocol_id="P-CPU-1", reps=5, reps_basis="scored", unit="tokens/s",
        attestation_sha256=SHA, attestation_locator=f"akfx:{ident}|x.json#sha256={SHA}",
        attestation_present=True, attestation_verified=True, source_kind=kind,
        applicability=scope)


def _frames(tup):
    return to_frames(tup, as_of=WRITTEN, adapter_id="fixture/v1")


def _claim_id(tup):
    return next(f["assertion"]["claim_id"] for f in _frames(tup)
                if f["frame_type"].endswith("claim_proposed/v1"))


def _ledger(tmp_path, tuples, name="ledger.jsonl"):
    path = tmp_path / name
    led = Ledger(path)
    for tup in tuples:
        for frame in _frames(tup):
            led.append(frame)
    return path


def _support(tup):
    return next(f for f in _frames(tup) if f["frame_type"].endswith("evidence_supports_claim/v1"))


def _retract(path, tup, at="2026-09-24T11:00:00+00:00"):
    Ledger(path).append(make_frame(
        frame_type="epyc.vidya/frame/retraction/v1",
        assertion={"retracts": _support(tup)["frame_id"], "reason": "fixture"},
        provenance={"method": "fixture/v1"}, actor="fixture/v1",
        authority_scope="measurement", created_at=at))


def _oppose(path, tup, at="2026-09-24T11:00:00+00:00"):
    support = _support(tup)
    Ledger(path).append(make_frame(
        frame_type="epyc.vidya/frame/evidence_opposes_claim/v1",
        assertion=copy.deepcopy(support["assertion"]),
        provenance=copy.deepcopy(support.get("provenance") or {"method": "fixture/v1"}),
        actor="fixture/v1", authority_scope="measurement", created_at=at))


class FakeSync:
    """The plumbing `sync` module's two calls, scripted."""

    def __init__(self, fresh=True, becomes_fresh=True, sync_raises=None):
        self.fresh, self.becomes_fresh, self.sync_raises = fresh, becomes_fresh, sync_raises
        self.sync_calls = 0

    def status(self, ledger, index):
        return {"fresh": self.fresh, "lag_entries": 0 if self.fresh else 7,
                "index_max_id": 2213, "synced_max_id": 2213 if self.fresh else 2206,
                "last_sync": "2026-10-21T10:33:45Z"}

    def sync(self, ledger, index):
        self.sync_calls += 1
        if self.sync_raises:
            raise self.sync_raises
        self.fresh = self.becomes_fresh
        return {"action": "ingested", "frames_emitted": 14, "seconds": 0.2}


@pytest.fixture
def alarm(tmp_path):
    cfg = tmp_path / "alarm_config.yaml"
    cfg.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarms.jsonl'}\n")
    return {"alarm_state": tmp_path / "alarm_state.json", "alarm_config": cfg}


def _prepare(tmp_path, alarm, ledger, targets, sync=None, **kw):
    return lb.prepare("test.loop", targets, ledger=ledger, index_path=tmp_path / "index.yaml",
                      as_of=AS_OF, sync_module=sync or FakeSync(),
                      known_good=tmp_path / "known_good.json", **alarm, **kw)


def _active(alarm):
    try:
        return json.loads(Path(alarm["alarm_state"]).read_text()).get("active", {})
    except FileNotFoundError:
        return {}


# ------------------------------------------------------------------------------ freshness


def test_fresh_ledger_is_ready_with_verified_state(tmp_path, alarm):
    path = _ledger(tmp_path, _kvq_run())
    sync = FakeSync(fresh=True)
    ans = _prepare(tmp_path, alarm, path, GPU_27B, sync=sync)
    assert ans["status"] == "ready" and sync.sync_calls == 0
    state = ans["ledger_state"]
    assert state["schema"] == lb.LEDGER_STATE_SCHEMA and state["fresh"] is True
    assert state["frame_count"] == len(list(Ledger(path).read_all())) == state["head_seq"] + 1
    assert state["head_hash"] == list(Ledger(path).read_all())[-1].frame_hash
    assert state["freshness"]["sync_action"] == "already-fresh"
    assert ans["ledger_state_digest"].startswith("sha256:")
    assert lb.validate_ready(ans)["status"] == "ready"


def test_stale_ledger_triggers_ingest_then_ready(tmp_path, alarm):
    sync = FakeSync(fresh=False, becomes_fresh=True)
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), GPU_27B, sync=sync)
    assert sync.sync_calls == 1 and ans["status"] == "ready"
    fr = ans["ledger_state"]["freshness"]
    assert (fr["was_fresh"], fr["sync_action"], fr["frames_emitted"]) == (False, "ingested", 14)


@pytest.mark.parametrize("sync,reason", [
    (FakeSync(fresh=False, becomes_fresh=False), "still_stale"),
    (FakeSync(fresh=False, sync_raises=OSError("disk")), "ingest_failed"),
])
def test_ledger_that_cannot_be_made_current_is_refused_and_alarmed(tmp_path, alarm, sync, reason):
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), GPU_27B, sync=sync)
    assert ans["status"] == "refused" and ans["reason"] == reason
    assert ans["ledger_state"] is None and ans["evidence"] is None
    assert "belief-ledger-not-current.test.loop" in _active(alarm)
    with pytest.raises(ValueError):
        lb.validate_ready(ans)


def test_broken_chain_is_refused(tmp_path, alarm):
    path = _ledger(tmp_path, _kvq_run())
    lines = path.read_bytes().splitlines(keepends=True)
    index = next(i for i, line in enumerate(lines) if b"(fixture)" in line)
    lines[index] = lines[index].replace(b"(fixture)", b"(tampered)", 1)
    path.write_bytes(b"".join(lines))
    ans = _prepare(tmp_path, alarm, path, GPU_27B)
    assert (ans["status"], ans["reason"]) == ("refused", "chain_broken")


def test_missing_ledger_and_missing_sync_module_are_refusals(tmp_path, alarm, monkeypatch):
    ans = _prepare(tmp_path, alarm, tmp_path / "absent.jsonl", GPU_27B)
    assert ans["reason"] == "ledger_missing"
    monkeypatch.setattr(lb, "HERE", tmp_path)          # no sync.py beside the module
    with pytest.raises(lb.LedgerNotCurrent) as err:
        lb.load_sync()
    assert err.value.reason == "sync_unavailable"


def test_escalation_after_timeout_and_clear_on_recovery(tmp_path, alarm):
    path = _ledger(tmp_path, _kvq_run())
    stale = FakeSync(fresh=False, becomes_fresh=False)
    first = _prepare(tmp_path, alarm, path, GPU_27B, sync=stale, escalate_after_s=3600)
    assert first["alarm"]["raised"] == "notified" and first["alarm"]["escalated"] is None
    second = _prepare(tmp_path, alarm, path, GPU_27B, sync=stale, escalate_after_s=0)
    assert second["alarm"]["escalated"] == "notified"
    active = _active(alarm)
    assert active["belief-ledger-not-current-escalated.test.loop"]["severity"] == "critical"
    ok = _prepare(tmp_path, alarm, path, GPU_27B, sync=FakeSync(fresh=True))
    assert ok["status"] == "ready" and _active(alarm) == {}


def test_unexpected_error_is_a_refusal_never_a_plan(tmp_path, alarm, monkeypatch):
    monkeypatch.setattr(lb, "evaluate_frames", lambda *a, **k: 1 / 0)
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), GPU_27B)
    assert (ans["status"], ans["reason"]) == ("refused", "reader_error")


def test_validate_ready_refuses_forged_answers():
    for forged in ({}, {"schema": lb.SCHEMA, "status": "ready"},
                   {"schema": lb.SCHEMA, "status": "ready", "evidence": {},
                    "ledger_state": {"schema": lb.LEDGER_STATE_SCHEMA, "fresh": True,
                                     "frame_count": 3, "head_hash": ""}}):
        with pytest.raises(ValueError):
            lb.validate_ready(forged)


# ------------------------------------------------------------------------------ evidence


def test_declared_scope_table_presents_complete_kvq_run(tmp_path, alarm):
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), GPU_27B)
    ev = ans["evidence"]
    assert ev["status"] == "presented" and len(ev["claim_ids"]) == 12
    assert ev["section"].startswith(lb.SECTION_HEADER) and "### Usable" in ev["section"]


def test_inapplicable_target_is_ready_with_empty_evidence(tmp_path, alarm):
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), DS41_CPU)
    assert ans["status"] == "ready" and ans["evidence"]["section"] == ""
    assert ans["evidence"]["reasons"] == ["no_applicable_claims"]


def test_incomplete_target_is_not_a_wildcard_but_still_ready(tmp_path, alarm):
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), {"quant": "Q8_0"})
    assert ans["status"] == "ready" and ans["evidence"]["claim_ids"] == []
    assert "target incomplete" in ans["evidence"]["error"]


def test_persisted_applicability_matches_declared_dimensions_only(tmp_path, alarm):
    model_scoped = _scoped("cand-1")
    host_scoped = _scoped("roofline-1", model=None, text="host read bandwidth 399.6 GB/s")
    other_model = _scoped("cand-2", model="Qwen3.8-Flash-Next-UD-IQ4_XS.gguf")
    gpu = _scoped("gpu-1", device="gfx90a", backend="gpu")
    ans = _prepare(tmp_path, alarm,
                   _ledger(tmp_path, [model_scoped, host_scoped, other_model, gpu]), DS41_CPU)
    assert set(ans["evidence"]["claim_ids"]) == {_claim_id(model_scoped), _claim_id(host_scoped)}


def test_contested_and_withdrawn_are_flagged_not_presented_as_usable(tmp_path, alarm):
    good, opposed, retracted = _scoped("good"), _scoped("opposed"), _scoped("retracted")
    path = _ledger(tmp_path, [good, opposed, retracted])
    _oppose(path, opposed)
    _retract(path, retracted)
    ev = _prepare(tmp_path, alarm, path, DS41_CPU)["evidence"]
    assert ev["claim_ids"] == [_claim_id(good)]
    assert ev["contested_claim_ids"] == [_claim_id(opposed)]
    assert ev["withdrawn_claim_ids"] == [_claim_id(retracted)]
    assert "### Contested" in ev["section"] and "### Withdrawn" in ev["section"]


def test_newest_run_supersedes_older_run(tmp_path, alarm):
    old = _scoped("a-old", run_id="run-1")
    new = _scoped("a-new", run_id="run-2")
    new = ClaimTuple(**{**new.__dict__, "date": "2026-09-25"})
    ev = _prepare(tmp_path, alarm, _ledger(tmp_path, [old, new]), DS41_CPU)["evidence"]
    assert ev["claim_ids"] == [_claim_id(new)] and "superseded_run" in ev["reasons"]


def test_bounded_rendering(tmp_path, alarm):
    tuples = [_scoped(f"c{i}") for i in range(20)]
    ev = _prepare(tmp_path, alarm, _ledger(tmp_path, tuples), DS41_CPU, max_claims=5)["evidence"]
    assert len(ev["claim_ids"]) == 5 and "bounded" in ev["reasons"]
    assert ev["section_bytes"] <= lb.DEFAULT_MAX_BYTES


# ------------------------------------------------------------------------------ degraded mode


def test_known_good_snapshot_and_seed_admission(tmp_path, alarm):
    good, retracted = _scoped("good"), _scoped("retracted")
    path = _ledger(tmp_path, [good, retracted])
    _retract(path, retracted)
    ready = _prepare(tmp_path, alarm, path, DS41_CPU)
    kg = lb.read_known_good(tmp_path / "known_good.json")
    assert kg["ledger_state"] == ready["ledger_state"] and _claim_id(retracted) in kg["withdrawn"]
    seeded = ready["ledger_state_digest"]
    out = lb.check_seeds([
        {"id": "seed-ok", "premises": [_claim_id(good)], "seeded_against": seeded},
        {"id": "seed-refuted", "premises": [_claim_id(retracted)], "seeded_against": seeded},
        {"id": "seed-blind", "premises": []},
    ], kg)
    assert out["admissible_ids"] == ["seed-ok"] and out["flagged_ids"] == ["seed-refuted"]
    blind = next(i for i in out["items"] if i["id"] == "seed-blind")
    assert blind["reasons"] == ["no_seeded_against_state"]
    assert out["checked_against"] == ready["ledger_state"]


def test_degraded_mode_uses_last_known_good_then_recheck_flags_on_recovery(tmp_path, alarm):
    good, later = _scoped("good"), _scoped("later-retracted")
    path = _ledger(tmp_path, [good, later])
    ready = _prepare(tmp_path, alarm, path, DS41_CPU)
    refused = _prepare(tmp_path, alarm, path, DS41_CPU,
                       sync=FakeSync(fresh=False, becomes_fresh=False))
    assert refused["status"] == "refused"
    assert refused["last_known_good"]["ledger_state"] == ready["ledger_state"]
    seed = {"id": "seed-1", "premises": [_claim_id(later)],
            "seeded_against": ready["ledger_state_digest"]}
    kg = lb.read_known_good(Path(refused["known_good_path"]))
    assert lb.check_seeds([seed], kg)["admissible_ids"] == ["seed-1"]   # ran while degraded
    _retract(path, later, at="2026-09-24T11:30:00+00:00")               # premise refuted meanwhile
    recovered = _prepare(tmp_path, alarm, path, DS41_CPU)
    assert recovered["status"] == "ready"
    recheck = lb.check_seeds([seed], lb.read_known_good(Path(recovered["known_good_path"])))
    assert recheck["flagged_ids"] == ["seed-1"]
    assert recheck["items"][0]["flagged_premises"] == [
        {"claim_id": _claim_id(later), "status": "withdrawn"}]


def test_no_known_good_snapshot_admits_nothing():
    out = lb.check_seeds([{"id": "s", "premises": [], "seeded_against": "sha256:x"}], None)
    assert out["admissible_ids"] == [] and out["items"][0]["reasons"] == ["no_known_good_state"]


# ------------------------------------------------------------------------------ CLI


def test_cli_prepare_refusal_exit_code_and_single_json(tmp_path, alarm):
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "vidya" / "loop_beliefs.py"), "prepare",
         "--consumer", "cli.test", "--target-json", json.dumps(GPU_27B),
         "--ledger", str(tmp_path / "absent.jsonl"), "--as-of", AS_OF,
         "--alarm-state", str(alarm["alarm_state"]), "--alarm-config", str(alarm["alarm_config"]),
         "--known-good", str(tmp_path / "kg.json")],
        capture_output=True, text=True, timeout=120, check=False)
    answer = json.loads(proc.stdout)
    assert proc.returncode == lb.EXIT_REFUSED and answer["reason"] == "ledger_missing"
    assert answer["last_known_good"] is None
    assert "belief-ledger-not-current.cli.test" in _active(alarm)


def test_real_sync_module_from_a_local_index_file(tmp_path, alarm):
    """The landed plumbing sync, driven with an explicit index file (no fetch): an index whose
    sha is already in the marker is fresh, so prepare is ready without an ingest."""
    if not (REPO / "scripts" / "vidya" / "sync.py").is_file():
        pytest.skip("plumbing sync.py absent")
    import hashlib
    path = _ledger(tmp_path, _kvq_run())
    index = tmp_path / "index.yaml"
    index.write_text("- id: intake-1\n")
    Path(str(path) + ".sync.json").write_text(json.dumps(
        {"seen_sha256": [hashlib.sha256(index.read_bytes()).hexdigest()], "max_id": 1}))
    ans = lb.prepare("test.loop", GPU_27B, ledger=path, index_path=index, as_of=AS_OF,
                     known_good=tmp_path / "kg.json", **alarm)
    assert ans["status"] == "ready", ans.get("detail")
    assert ans["ledger_state"]["freshness"]["sync_action"] == "already-fresh"
    assert ans["ledger_state"]["freshness"]["index_sha256"] == hashlib.sha256(
        index.read_bytes()).hexdigest()


def test_cli_check_seeds(tmp_path):
    kg = tmp_path / "kg.json"
    kg.write_text(json.dumps({"schema": lb.KNOWN_GOOD_SCHEMA, "contested": ["clm_x"],
                              "withdrawn": [], "aliases": {},
                              "ledger_state": {"head_hash": "h"},
                              "ledger_state_digest": "sha256:d"}))
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "vidya" / "loop_beliefs.py"), "check-seeds",
         "--consumer", "cli.test", "--known-good", str(kg), "--items-json",
         json.dumps([{"id": "a", "premises": ["clm_x"], "seeded_against": "sha256:d"},
                     {"id": "b", "premises": ["clm_y"], "seeded_against": "sha256:d"}])],
        capture_output=True, text=True, timeout=60, check=True)
    out = json.loads(proc.stdout)
    assert out["admissible_ids"] == ["b"] and out["flagged_ids"] == ["a"]


def test_reply_field_is_the_consumers(tmp_path, alarm):
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), GPU_27B,
                   reply_field="vidya_claim_ids")
    assert "Optional reply field vidya_claim_ids" in ans["evidence"]["section"]


def test_operator_provenance_counts_as_seeded_against():
    kg = {"schema": lb.KNOWN_GOOD_SCHEMA, "contested": [], "withdrawn": [], "aliases": {}}
    out = lb.check_seeds([{"id": "op-1", "premises": [],
                           "seeded_against": {"kind": "operator", "author": "op", "at": "t"}}], kg)
    assert out["admissible_ids"] == ["op-1"]
    assert out["items"][0]["seeded_against"]["kind"] == "operator"


def test_target_without_quant_matches_on_the_gguf_basename(tmp_path, alarm):
    claim = _scoped("q38fn-1", model="Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf")
    target = {"model_path": "/m/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf", "quant": "",
              "backend": "cpu"}
    ev = _prepare(tmp_path, alarm, _ledger(tmp_path, [claim]), target)["evidence"]
    assert ev["claim_ids"] == [_claim_id(claim)]


class FakeScoped:
    def __init__(self, raises=None):
        self.calls, self.raises = [], raises

    def ingest_scoped_store(self, ledger, root, *, as_of, memo_path=None):
        self.calls.append((str(root), memo_path))
        if self.raises:
            raise self.raises
        return {"store_root": str(root), "receipts_listed": 3, "receipts_read": 1,
                "new_claims": 1, "rescoped": 0, "frames_appended": 3, "seconds": 0.01,
                "refusals": []}


def test_source_roots_are_ingested_before_reading(tmp_path, alarm):
    scoped = FakeScoped()
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), GPU_27B,
                   source_roots=[tmp_path / "store"], source_memo_dir=tmp_path / "memo",
                   scoped_module=scoped)
    assert ans["status"] == "ready" and scoped.calls[0][0] == str(tmp_path / "store")
    assert Path(scoped.calls[0][1]).parent == tmp_path / "memo"
    assert ans["ledger_state"]["freshness"]["sources"][0]["frames_appended"] == 3


def test_failed_source_ingest_is_a_refusal(tmp_path, alarm):
    ans = _prepare(tmp_path, alarm, _ledger(tmp_path, _kvq_run()), GPU_27B,
                   source_roots=[tmp_path / "store"], scoped_module=FakeScoped(OSError("io")))
    assert (ans["status"], ans["reason"]) == ("refused", "ingest_failed")
    assert "source" in ans["detail"]


def test_round_robin_packing_keeps_every_source_visible(tmp_path, alarm):
    big = [_scoped(f"big-{i}", kind="big-source", run_id="run-1") for i in range(20)]
    small = [_scoped(f"small-{i}", kind="small-source") for i in range(3)]
    ev = _prepare(tmp_path, alarm, _ledger(tmp_path, big + small), DS41_CPU,
                  max_claims=6)["evidence"]
    kinds = [c["source_kind"] for c in ev["claims"]]
    assert len(kinds) == 6 and kinds.count("small-source") == 3
