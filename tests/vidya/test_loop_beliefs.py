"""The shared agent-loop belief reader: mandatory freshness, refusal + alarm, evidence buckets,
known-good snapshots and degraded-mode seed checks; and (belief redesign Phase 1, P1-E) the
tiered, value-bearing read side: target / sibling / host tiers, the declared model lineage,
ranking, caps, the empty-target banner, the refuted bucket, v1/v2 serving dedup and the
tried-mechanisms index.

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
    ev = ans["evidence"]
    # Tiered (belief redesign §7.1): the model-scoped claim is target evidence; the device-only
    # claim is host context, shown but never reliance-eligible.
    assert ev["claim_ids"] == [_claim_id(model_scoped)]
    assert ev["host_claim_ids"] == [_claim_id(host_scoped)]
    assert {c["claim_id"]: c["tier"] for c in ev["claims"]} == {
        _claim_id(model_scoped): "target", _claim_id(host_scoped): "host"}


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


# ------------------------------------------------------------------------------ tiered read side
#
# Synthetic loop beliefs in the belief-redesign §4.1 shape: a real ClaimTuple through `to_frames`
# (so the grade is the ladder's), then the carrier additions the reader consumes -- extra
# applicability keys on the source frame, `metric`/`value`/`unit`/`observation` on the evidence
# frame, `provenance.retrofit` -- re-sealed with `make_frame`. Numeric observation fields are
# DECIMAL STRINGS, as the canonical encoding (no floats) requires; the reader parses them through
# one helper.

MODELS = "/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf"
DS41_Q4 = "DeepSeek-V4.1-Flash-Q4.gguf"
DS41_1017 = "DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf"
Q38_UD = "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
Q38_UNI = "Qwen3.8-Flash-Next-IQ4_XS-uniform.gguf"
EXP = "autokernel-experiment"
SERVING = "autokernel-legacy-serving"
CAP_A = "a1" * 32
CAP_B = "b2" * 32


def _target(model, *, quant="", backend="cpu", **extra):
    return {"model_path": f"{MODELS}/{model}", "quant": quant, "backend": backend, **extra}


DS41_Q4_T = _target(DS41_Q4, quant="Q8_0")
DS41_1017_T = _target(DS41_1017)
Q38_T = _target(Q38_UD, quant="UD-IQ4_XS")
QWEN35_T = {"model_path": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf", "quant": "Q8_0",
            "backend": "cpu"}


def _reseal(frames, *, scope_extra, evidence_extra, retrofit):
    out = []
    for frame in frames:
        assertion = copy.deepcopy(frame["assertion"])
        provenance = copy.deepcopy(frame["provenance"])
        if frame["frame_type"].endswith("source_observed/v1"):
            assertion.setdefault("applicability", {}).update(scope_extra)
            if retrofit:
                provenance["retrofit"] = True
        elif frame["frame_type"].endswith("evidence_supports_claim/v1"):
            assertion.update({k: v for k, v in evidence_extra.items() if v is not None})
        out.append(make_frame(frame_type=frame["frame_type"], assertion=assertion,
                              provenance=provenance, actor=frame["pubinfo"]["actor"],
                              authority_scope=frame["pubinfo"]["authority_scope"],
                              created_at=frame["pubinfo"]["created_at"]))
    return out


def _loop(ident, *, model=DS41_Q4, quant="Q8_0", backend="cpu", device="epyc-9655",
          kind=EXP, mech="akm-fixture", outcome="null", value="22.31", anchor="21.9",
          effect="-0.0072", floor="0.03412", n_pairs=5, recipe="ds41-r1",
          epoch="c42cd5615dfb0000", build="7ef803926107aaaa", symbol="ggml_iqk_try_mul_mat_id",
          date="2026-10-04T04:37:38Z", reason="", native="measured_null", decisive=False,
          metric="aggregate_tok_s", unit="t/s", serving_claim_id=None, observation=True,
          model_sha256=None, locator=None, scope_keys=None):
    """One loop belief's three frames, §4.1 shape. `observation=False` gives an old-style frame
    (applicability only, no value-bearing evidence keys)."""
    scope = {k: v for k, v in (("backend", backend), ("device", device)) if v}
    if model:
        scope["model_file"] = f"{MODELS}/{model}"
    if quant:
        scope["quant"] = quant
    tup = ClaimTuple(
        measurement_id=ident, metric=metric, value=1, date=date, category="CANDIDATE",
        claim=f"{ident}: fixture loop belief.",
        reps=n_pairs if isinstance(n_pairs, int) and n_pairs > 0 else None,
        reps_basis="scored:matched process pairs", unit=unit, attestation_sha256=SHA,
        attestation_locator=locator or f"autokernel-experiments:store/experiments.db#attempt={ident}",
        attestation_present=True, source_kind=kind, applicability=scope)
    extra = {k: v for k, v in {"recipe": recipe, "epoch": epoch, "build_sha": build,
                               "symbol": symbol, "model_sha256": model_sha256,
                               "scope_basis": "native"}.items() if v}
    evidence: dict = {}
    if observation:
        obs = {"anchor_value": anchor, "effect_rel": effect, "noise_floor_rel": floor,
               "decisive": decisive, "n_pairs": n_pairs, "outcome": outcome,
               "outcome_native": native, "retrofit": True}
        obs = {k: v for k, v in obs.items() if v is not None}
        if reason:
            obs["outcome_reason"] = reason
        if mech:
            obs["mechanism"] = {"id": mech, "statement": f"{mech} statement",
                                "falsifier": f"{mech} falsifier"}
        if serving_claim_id:
            obs["serving_claim_id"] = serving_claim_id
        evidence = {"metric": metric, "value": value, "unit": unit, "observation": obs}
    return _reseal(to_frames(tup, as_of=WRITTEN, adapter_id="fixture/v1"),
                   scope_extra={**(extra if observation else {}), **(scope_keys or {})},
                   evidence_extra=evidence,
                   retrofit=observation)


def _host(ident, *, value="399.6"):
    """An INF-70-like device-only claim (no model)."""
    return _loop(ident, model=None, quant="", kind="inf70-roofline-measurement", mech=None,
                 outcome="", value=value, unit="GB/s", metric="bench_readbw.read-sum",
                 recipe=None, epoch=None, build=None, symbol=None, observation=True)


def _cid(frames):
    return next(f["assertion"]["claim_id"] for f in frames
                if f["frame_type"].endswith("claim_proposed/v1"))


def _write(tmp_path, *bundles, name="ledger.jsonl"):
    path = tmp_path / name
    led = Ledger(path)
    for frames in bundles:
        for frame in frames:
            led.append(frame)
    return path


def _ev(tmp_path, alarm, path, target, **kw):
    ans = _prepare(tmp_path, alarm, path, target, **kw)
    assert ans["status"] == "ready", ans.get("detail")
    return ans, ans["evidence"]


def _tier_of(ev, claim_id):
    return {c["claim_id"]: c["tier"] for c in ev["claims"]}.get(claim_id)


def test_focus_symbols_rank_claims_on_those_symbols_first_and_never_filter(tmp_path, alarm):
    """DESIGN §7.5: `focus_symbols` (AutoKernel passes its owned targets' symbols) is a ranking
    boost inside a group, never a filter."""
    focus = _loop("on-focus", mech="akm-focus", symbol="mul_mat_q", date="2026-10-04T04:00:00Z")
    newer = _loop("off-focus", mech="akm-other", symbol="ggml_iqk_try_mul_mat_id",
                  date="2026-10-05T04:00:00Z")
    path = _write(tmp_path, focus, newer)
    _, plain = _ev(tmp_path, alarm, path, DS41_Q4_T)
    ids = [c["claim_id"] for c in plain["claims"]]
    assert ids.index(_cid(newer)) < ids.index(_cid(focus))     # recency without a focus
    _, boosted = _ev(tmp_path, alarm, path, {**DS41_Q4_T, "focus_symbols": ["mul_mat_q"]})
    ids = [c["claim_id"] for c in boosted["claims"]]
    assert ids.index(_cid(focus)) < ids.index(_cid(newer))     # the focus symbol first
    assert {_cid(focus), _cid(newer)} <= set(ids)               # and nothing filtered out
    _, unknown = _ev(tmp_path, alarm, path, {**DS41_Q4_T, "focus_symbols": ["not_a_symbol"]})
    assert [c["claim_id"] for c in unknown["claims"]] == [c["claim_id"] for c in plain["claims"]]


def test_device_only_claims_never_reach_the_target_tier(tmp_path, alarm):
    hosts = [_host(f"inf70-{i}", value=f"{390 + i}.5") for i in range(5)]
    own = _loop("ds41-own", mech="akm-own")
    path = _write(tmp_path, own, *hosts)
    for target in (DS41_Q4_T, QWEN35_T, DS41_1017_T):
        _, ev = _ev(tmp_path, alarm, path, target)
        host_ids = {_cid(h) for h in hosts}
        assert not host_ids & set(ev["claim_ids"])            # never reliance-eligible
        assert all(c["tier"] == "host" and c["not_evidence"]
                   for c in ev["claims"] if c["claim_id"] in host_ids)
        assert ev["tiers"]["host"] == 5 and ev["tiers_shown"]["host"] <= 3
        assert "host ceiling, not about this model" in ev["section"]
    _, own_ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    assert own_ev["tiers"]["target"] == 1 and _tier_of(own_ev, _cid(own)) == "target"
    _, other = _ev(tmp_path, alarm, path, QWEN35_T)
    assert other["tiers"]["target"] == 0 and other["claim_ids"] == []


def test_sibling_evidence_is_labelled_transfer_unproven(tmp_path, alarm):
    q4 = [_loop(f"ds41-q4-{i}", mech=f"akm-sib-{i}", outcome="regressed", effect="-0.0341",
                decisive=True, native="regression") for i in range(3)]
    uniform = _loop("q38-uniform", model=Q38_UNI, quant="IQ4_XS", mech="akm-q38-uni")
    stranger = _loop("stranger", model="Some-Other-Model-Q8_0.gguf", mech="akm-stranger")
    path = _write(tmp_path, *q4, uniform, stranger)
    _, ev = _ev(tmp_path, alarm, path, DS41_1017_T)
    assert ev["tiers"] == {"knob": 0, "target": 0, "lineup": 0, "sibling": 3, "host": 0}
    sibling_lines = [line for line in ev["section"].splitlines()
                     if line.startswith("- ") and "transfer unproven" in line]
    assert len(sibling_lines) == 3
    assert all(f"measured on {DS41_Q4}, recipe ds41-r1; transfer unproven" in line
               for line in sibling_lines)
    assert {_tier_of(ev, _cid(b)) for b in q4} == {"sibling"}
    assert set(ev["claim_ids"]) == {_cid(b) for b in q4}       # sibling ids are reliance-eligible
    assert _cid(stranger) not in ev["section"]
    _, q38 = _ev(tmp_path, alarm, path, Q38_T)                 # uniform file is UD's sibling
    assert q38["tiers"] == {"knob": 0, "target": 0, "lineup": 0, "sibling": 1, "host": 0}
    assert f"measured on {Q38_UNI}" in q38["section"]


def test_section_caps(tmp_path, alarm):
    own = [_loop(f"own-{i:02d}", mech=f"akm-own-{i:02d}", outcome="improved",
                 effect=f"0.0{i % 9 + 1}", decisive=True, native="kept",
                 date=f"2026-10-{i % 28 + 1:02d}T00:00:00Z") for i in range(30)]
    sib = [_loop(f"sib-{i:02d}", model=DS41_1017, quant="", mech=f"akm-sib-{i:02d}")
           for i in range(12)]
    hosts = [_host(f"host-{i}") for i in range(6)]
    path = _write(tmp_path, *own, *sib, *hosts)
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    assert ev["tiers"] == {"knob": 0, "target": 30, "lineup": 0, "sibling": 12, "host": 6}
    assert ev["tiers_shown"]["target"] <= lb.TIER_CAPS["target"] == 16
    assert ev["tiers_shown"]["sibling"] <= lb.TIER_CAPS["sibling"] == 8
    assert ev["tiers_shown"]["host"] <= lb.TIER_CAPS["host"] == 3
    assert ev["section_bytes"] <= lb.DEFAULT_MAX_BYTES == 14000
    assert lb.DEFAULT_MAX_CLAIMS == 27
    assert "bounded" in ev["reasons"]
    _, tight = _ev(tmp_path, alarm, path, DS41_Q4_T, max_bytes=4000)
    assert 0 < tight["section_bytes"] <= 4000
    assert tight["tiers_shown"]["host"] == 0                   # host context is trimmed first
    assert tight["tiers_shown"]["target"] >= 1


def test_empty_target_banner(tmp_path, alarm):
    path = _write(tmp_path, _loop("q4-only", mech="akm-q4-only"), _host("inf70-x"))
    ans, ev = _ev(tmp_path, alarm, path, DS41_1017_T)
    assert ev["nonempty_target"] is False and ev["tiers"]["target"] == 0
    expected = (f"No beliefs are scoped to {DS41_1017} (cpu). The lines below are sibling/host "
                "context only.")
    assert ev["banner"] == expected and ans["banner"] == expected
    lines = ev["section"].splitlines()
    assert lines[0] == lb.SECTION_HEADER and lines[1] == expected   # says so FIRST
    ans, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    assert ev["nonempty_target"] is True and ev["banner"] is None and ans["banner"] is None
    assert "No beliefs are scoped" not in ev["section"]
    # nothing applies at all: still a banner in the answer, no section (pre-tier behaviour)
    ans, ev = _ev(tmp_path, alarm, _write(tmp_path, _loop("x", model="Unrelated.gguf"),
                                          name="other.jsonl"), QWEN35_T)
    assert ev["section"] == "" and ev["reasons"] == ["no_applicable_claims"]
    assert ev["banner"].startswith("No beliefs are scoped to Qwen3.6-35B-A3B-MTP-Q8_0.gguf")


def _oppose_distinct(path, frames, at="2026-09-24T11:00:00+00:00"):
    support = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assertion = copy.deepcopy(support["assertion"])
    assertion["evidence_id"] = assertion["evidence_id"] + ":opposing"
    Ledger(path).append(make_frame(
        frame_type="epyc.vidya/frame/evidence_opposes_claim/v1", assertion=assertion,
        provenance=copy.deepcopy(support["provenance"]), actor="fixture/v1",
        authority_scope="measurement", created_at=at))


def _retract_frames(path, frames, at="2026-09-24T11:30:00+00:00"):
    support = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    Ledger(path).append(make_frame(
        frame_type="epyc.vidya/frame/retraction/v1",
        assertion={"retracts": support["frame_id"], "reason": "fixture"},
        provenance={"method": "fixture/v1"}, actor="fixture/v1",
        authority_scope="measurement", created_at=at))


def test_refuted_bucket_from_the_fold_verdict(tmp_path, alarm):
    good = _loop("good", mech="akm-good")
    refuted = _loop("refuted", mech="akm-refuted", outcome="improved", effect="0.031")
    path = _write(tmp_path, good, refuted)
    _oppose_distinct(path, refuted)
    _retract_frames(path, refuted)             # support gone, opposition clears -> Opposed
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    assert ev["refuted_claim_ids"] == [_cid(refuted)]
    assert _cid(refuted) not in ev["claim_ids"] and _cid(refuted) not in ev["withdrawn_claim_ids"]
    assert ev["flagged"]["refuted"][0]["tier"] == "target"
    section = ev["section"]
    assert "### Refuted" in section and section.index("### Refuted") < section.index(
        "### Usable, target tier")
    assert ev["claim_ids"] == [_cid(good)]


def test_same_ledger_same_section_bytes(tmp_path, alarm):
    bundles = [_loop(f"d-{i}", mech=f"akm-d-{i % 4}", recipe=f"r{i % 2}",
                     outcome=("improved", "null", "regressed", "refused_correctness")[i % 4],
                     date=f"2026-10-0{i % 9 + 1}T00:00:00Z") for i in range(12)]
    bundles += [_host("h-1"), _loop("sib-1", model=DS41_1017, quant="", mech="akm-sib")]
    first = _write(tmp_path, *bundles, name="a.jsonl")
    second = _write(tmp_path, *bundles, name="b.jsonl")
    sections = []
    for path in (first, first, second):
        _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
        sections.append((ev["section"].encode(), ev["section_sha256"], ev["tried_index"]))
    assert sections[0] == sections[1] == sections[2]
    assert sections[0][0]


def test_v1_arm_claims_hide_behind_the_v2_capture_claim(tmp_path, alarm):
    receipt_a = f"autokernel:/s/serving-beliefs/receipts/{CAP_A}.json"
    receipt_b = f"autokernel:/s/serving-beliefs/receipts/{CAP_B}.json"
    v1_a = [_loop(f"legacy-serving:{CAP_A}:{arm}", kind=SERVING, observation=False,
                  locator=receipt_a) for arm in ("anchor", "candidate")]
    v1_b = [_loop(f"legacy-serving:{CAP_B}:{arm}", kind=SERVING, observation=False,
                  locator=receipt_b) for arm in ("anchor", "candidate")]
    v2_a = _loop(f"legacy-serving-v2:{CAP_A}", kind=SERVING, mech="akm-serv-a",
                 outcome="regressed", effect="-0.0822", decisive=True, native="regression",
                 locator=receipt_a)
    path = _write(tmp_path, *v1_a, *v1_b, v2_a)
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    shown = {c["claim_id"] for c in ev["claims"]}
    assert _cid(v2_a) in shown
    assert not {_cid(b) for b in v1_a} & shown                 # hidden behind v2
    assert {_cid(b) for b in v1_b} <= shown                    # no v2 yet: v1 still shown
    hidden = {o["claim_id"] for o in ev["omitted"] if o["reason"] == "superseded_by_v2"}
    assert hidden == {_cid(b) for b in v1_a}
    assert ev["tiers"]["target"] == 3


def test_experiment_and_linked_serving_claim_render_as_one_line(tmp_path, alarm):
    serving = _loop(f"legacy-serving-v2:{CAP_A}", kind=SERVING, mech="akm-linked",
                    outcome="regressed", value="20.11", anchor="21.9", effect="-0.0822",
                    floor="0.03412", decisive=True, native="regression")
    experiment = _loop("ak-exp:v1:0123456789abcdef:att-1", mech="akm-linked",
                       outcome="regressed", value=None, anchor=None, effect=None,
                       native="regression", serving_claim_id=f"legacy-serving-v2:{CAP_A}")
    path = _write(tmp_path, serving, experiment)
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    assert [c["claim_id"] for c in ev["claims"]] == [_cid(experiment)]
    claim = ev["claims"][0]
    assert claim["linked_claim_ids"] == [_cid(serving)]
    assert claim["value"] == 20.11 and claim["effect_rel"] == -0.0822
    assert set(ev["claim_ids"]) == {_cid(experiment), _cid(serving)}
    assert "akm-linked statement" in ev["section"] and "REGRESSED -8.22% vs anchor" in ev["section"]
    assert ev["section"].count("akm-linked @") == 1


def test_tried_index_contains_every_mechanism_with_its_outcome(tmp_path, alarm):
    outcomes = ("improved", "null", "regressed", "refused_correctness", "divergence")
    bundles, expect = [], {}
    for i in range(40):
        outcome = outcomes[i % 5]
        mech = f"akm-tried-{i:02d}"
        expect[mech] = outcome
        bundles.append(_loop(f"t-{i:02d}", mech=mech, outcome=outcome,
                             effect=None if outcome == "refused_correctness" else "-0.004",
                             reason="MUL_MAT failed on ROCm0" if i % 5 == 3 else "",
                             date=f"2026-10-{i % 28 + 1:02d}T00:00:00Z"))
        if i % 10 == 0:   # an earlier capture of the same mechanism (folded, still indexed once)
            bundles.append(_loop(f"t-{i:02d}-old", mech=mech, outcome="null",
                                 date="2026-09-01T00:00:00Z"))
    sib_mech = "akm-from-sibling"
    bundles.append(_loop("sib", model=DS41_1017, quant="", mech=sib_mech, outcome="improved",
                         effect="0.02"))
    path = _write(tmp_path, *bundles)
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    index = {(e["tier"], e["mechanism_id"]): e for e in ev["tried_index"]}
    for mech, outcome in expect.items():
        entry = index[("target", mech)]
        assert entry["outcome"] in (outcome, "null")             # newest capture wins
        assert entry["model_file"] == DS41_Q4
        assert mech in ev["section"]                             # 41 ids fit the 80-id index
    assert index[("target", "akm-tried-00")]["captures"] == 2
    assert index[("sibling", sib_mech)]["outcome"] == "improved"
    assert "Tried on DS41-Q4:" in ev["section"]
    assert "Tried on DS41-1017 (sibling; transfer unproven):" in ev["section"]
    assert ev["tried_index_count"] == 41
    assert any("(+1 earlier captures:" in line for line in ev["section"].splitlines())


def test_old_style_frames_without_observation_still_render(tmp_path, alarm):
    old = _scoped("pre-carrier")                      # VB-APPLICABILITY era, no observation
    path = _ledger(tmp_path, [old])
    _, ev = _ev(tmp_path, alarm, path, DS41_CPU)
    claim = ev["claims"][0]
    assert claim["claim_id"] == _claim_id(old) and claim["tier"] == "target"
    assert (claim["outcome"], claim["value"], claim["mechanism_id"]) == ("", None, "")
    line = next(l for l in ev["section"].splitlines() if l.startswith(f"- {_claim_id(old)} "))
    assert "candidate decode 20.0 tokens/s (fixture)" in line and "protocol P-CPU-1" in line
    assert ev["tried_index"] == []
    # malformed observation fields read as absent, never crash the reader
    bad = _loop("bad-obs", mech="akm-bad", value="fast", effect="NaN", floor=["x"], n_pairs="0")
    _, ev = _ev(tmp_path, alarm, _write(tmp_path, bad, name="bad.jsonl"), DS41_Q4_T)
    claim = ev["claims"][0]
    assert claim["value"] is None and claim["effect_rel"] is None and claim["n_pairs"] is None


def test_value_bearing_line_and_decimal_strings(tmp_path, alarm):
    reg = _loop("reg", mech="akm-ds41-q4q5-two-row-activation-reuse",
                symbol="mul_mat_qX_K_q8_2_X4_T", outcome="regressed", value="20.1",
                anchor="21.9", effect="-0.0822", floor="0.03412", n_pairs=5, decisive=True,
                native="regression")
    floor = _loop("floor", model="Qwen3.8-27B-Q8_0.gguf", backend="gpu", device="gfx90a",
                  kind="autokernel-serving-floor", mech=None, outcome="floor", value="81.12",
                  anchor=None, effect=None, floor="0.00807", n_pairs=None,
                  recipe="q27b-9a3f1392a-gpu-dflash2-np1", symbol=None)
    path = _write(tmp_path, reg, floor)
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    text = ev["section"]
    assert (f"- {_cid(reg)} [Judged/Located · verified · retrofit] DS41-Q4/cpu ds41-r1 "
            "build 7ef80392 epoch c42cd561") in text
    assert ("  akm-ds41-q4q5-two-row-activation-reuse @ mul_mat_qX_K_q8_2_X4_T: REGRESSED "
            "-8.22% vs anchor (20.1 t/s vs anchor 21.9 t/s; floor 3.41%; 5 pairs; decisive) "
            "-- producer verdict regression") in text
    claim = ev["claims"][0]
    assert (claim["value"], claim["unit"], claim["outcome"]) == (20.1, "t/s", "regressed")
    _, gpu = _ev(tmp_path, alarm, path, GPU_27B)
    assert "serving floor: median 81.12 t/s; floor 0.81%" in gpu["section"]


def test_newest_floor_is_always_shown_and_ranking_order(tmp_path, alarm):
    decisive = [_loop(f"dec-{i:02d}", mech=f"akm-dec-{i:02d}", outcome="improved",
                      effect="0.05", decisive=True, native="kept") for i in range(20)]
    nulls = [_loop(f"null-{i}", mech=f"akm-null-{i}") for i in range(3)]
    floors = [_loop(f"floor-{d}", kind="autokernel-serving-floor", mech=None, outcome="floor",
                    value=v, effect=None, anchor=None, date=f"2026-10-{d}T00:00:00Z")
              for d, v in (("01", "20.0"), ("09", "21.5"))]
    path = _write(tmp_path, *decisive, *nulls, *floors)
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    shown = [c["claim_id"] for c in ev["claims"]]
    assert _cid(floors[1]) in shown and _cid(floors[0]) not in shown   # newest floor per recipe
    assert not {_cid(n) for n in nulls} & set(shown)                  # decisive outranks nulls
    assert "(+1 earlier captures: floor" in ev["section"]


def test_stale_epoch_rows_rank_last_and_are_labelled(tmp_path, alarm):
    new = _loop("new", mech="akm-new", outcome="null", epoch="eeee0000",
                date="2026-10-05T00:00:00Z")
    old = _loop("old", mech="akm-old", outcome="improved", effect="0.03", epoch="dddd0000",
                date="2026-09-20T00:00:00Z")
    _, ev = _ev(tmp_path, alarm, _write(tmp_path, new, old), DS41_Q4_T)
    assert [c["claim_id"] for c in ev["claims"]] == [_cid(new), _cid(old)]
    assert [c["stale_epoch"] for c in ev["claims"]] == [False, True]
    assert "Older epochs (stale epoch -- the number is not comparable" in ev["section"]


def test_target_extras_recipe_from_surface_and_model_sha(tmp_path, alarm):
    sha = "c" * 64
    raw = {**DS41_Q4_T, "surface": "serving:ds41-r2", "model_sha256": sha,
           "focus_symbols": ["sym_b", "sym_a"]}
    target = lb.Target.from_mapping(raw)
    assert (target.recipe, target.model_sha256, target.focus_symbols) == (
        "ds41-r2", sha, ("sym_a", "sym_b"))
    assert target.as_dict()["recipe"] == "ds41-r2"
    with pytest.raises(ValueError):
        lb.Target.from_mapping({**DS41_Q4_T, "model_sha256": "nothex"})
    other = _loop("r1", mech="akm-r1", recipe="ds41-r1")
    same = _loop("r2", mech="akm-r2", recipe="ds41-r2")
    renamed = _loop("renamed", model="renamed-copy.gguf", quant="", mech="akm-renamed",
                    model_sha256=sha)
    wrong_sha = _loop("wrong-sha", mech="akm-wrong", model_sha256="d" * 64)
    _, ev = _ev(tmp_path, alarm, _write(tmp_path, other, same, renamed, wrong_sha), raw)
    ids = [c["claim_id"] for c in ev["claims"]]
    assert ids.index(_cid(same)) < ids.index(_cid(other))     # same recipe ranks first
    assert _cid(renamed) in ids                               # sha identifies the weights
    # a sha disagreement is never TARGET evidence; the same lineage file name carrying other
    # weights is exactly a sibling (DESIGN §7.1: "different weights or recipe")
    assert _tier_of(ev, _cid(wrong_sha)) == "sibling"
    assert _tier_of(ev, _cid(renamed)) == "target"
    assert ans_targets_roundtrip(tmp_path, alarm, raw)


def ans_targets_roundtrip(tmp_path, alarm, raw):
    ans = _prepare(tmp_path, alarm, _write(tmp_path, _host("h"), name="rt.jsonl"), raw)
    return ans["targets"][0]["recipe"] == "ds41-r2"


def test_existing_answer_keys_are_kept(tmp_path, alarm):
    path = _write(tmp_path, _loop("k", mech="akm-k"), _host("h"))
    _, ev = _ev(tmp_path, alarm, path, DS41_Q4_T)
    for key in ("status", "reasons", "frontier", "as_of", "claim_ids", "contested_claim_ids",
                "withdrawn_claim_ids", "claims", "flagged", "runs", "omitted", "omitted_count",
                "section", "section_sha256", "section_bytes"):
        assert key in ev
    for key in ("tiers", "tried_index", "nonempty_target", "banner", "refuted_claim_ids",
                "host_claim_ids", "not_evidence_claim_ids"):
        assert key in ev
    assert set(ev["flagged"]) == {"contested", "withdrawn", "refuted"}
    for claim in ev["claims"]:
        assert {"claim_id", "source_kind", "run", "grade", "locator", "tier", "status",
                "outcome", "mechanism_id", "value", "unit", "effect_rel"} <= set(claim)
    empty = lb._evidence_empty("no_applicable_claims", as_of=AS_OF)
    assert empty["tiers"] == {"knob": 0, "target": 0, "lineup": 0, "sibling": 0, "host": 0}
    assert empty["banner"] is None


# ------------------------------------------------------------------------------ knob / lineup (§12)

Q27 = "Qwen3.8-27B-Q8_0.gguf"
ARCHITECT_T = {"model_path": f"/mnt/raid0/llm/models/{Q27}", "quant": "Q8_0", "backend": "gpu",
               "role": "architect_critic",
               "knob_families": ["spec_draft", "kv_profile", "routing"]}
LINEUP_T = {"scope": "lineup", "stack_regime": "regime-r1",
            "knob_families": ["orchestrator", "kv_compaction"]}


def _gpu27(ident, **kw):
    kw.setdefault("mech", None)
    kw.setdefault("outcome", "")
    return _loop(ident, model=Q27, quant="Q8_0", backend="gpu", device="gfx90a",
                 recipe=None, epoch=None, build=None, symbol=None, **kw)


def test_knob_tier_ranks_above_plain_target_and_prints_knobs(tmp_path, alarm):
    pbhol = _gpu27("pb-hol-1:off:short", kind="pb-hol-1", value="22.05", unit="x",
                   metric="short_ttft_ratio_b_over_a",
                   scope_keys={"knob_family": "routing", "role": "architect_critic",
                          "varied": ["short_slot_index_order"],
                          "knobs": {"np": "3", "kv_unified": "on"}})
    kpf = _gpu27("kpf18:item7:B1", kind="kv-prefix-fork", value="25", unit="s",
                 scope_keys={"knob_family": "slot_serving", "varied": ["slot_fork"]})
    plain = _gpu27("plain-27b", value="81.12")
    bogus = _gpu27("bogus-family", value="1", scope_keys={"knob_family": "not_a_family"})
    path = _write(tmp_path, kpf, plain, bogus, pbhol)
    _, ev = _ev(tmp_path, alarm, path, ARCHITECT_T)
    tiers = {c["claim_id"]: c["tier"] for c in ev["claims"]}
    assert tiers[_cid(pbhol)] == "knob"
    assert tiers[_cid(kpf)] == "target"        # slot_serving is not a family this role changes
    assert tiers[_cid(plain)] == "target" and tiers[_cid(bogus)] == "target"
    assert ev["tiers"]["knob"] == 1 and ev["tiers"]["target"] == 3
    assert ev["claims"][0]["claim_id"] == _cid(pbhol)          # knob ranks first
    assert _cid(pbhol) in ev["claim_ids"]                       # reliance-eligible
    section = ev["section"]
    assert section.index("### Usable, knob tier") < section.index("### Usable, target tier")
    line = next(l for l in section.splitlines() if l.startswith(f"- {_cid(pbhol)} "))
    assert ("role architect_critic family routing varied [short_slot_index_order] "
            "knobs {kv_unified=on, np=3}") in line
    assert ev["claims"][0]["knob_family"] == "routing"
    assert ev["claims"][0]["varied"] == ["short_slot_index_order"]
    # the same claim with no families on the target is plain target evidence
    _, plain_ev = _ev(tmp_path, alarm, path, {k: v for k, v in ARCHITECT_T.items()
                                              if k != "knob_families"})
    assert plain_ev["tiers"]["knob"] == 0 and plain_ev["tiers"]["target"] == 4


def test_target_knob_families_are_declared_vocabulary():
    target = lb.Target.from_mapping({**ARCHITECT_T, "knob_families": ["routing", "spec_draft"]})
    assert target.knob_families == ("routing", "spec_draft") and target.role == "architect_critic"
    assert lb.Target.from_mapping({**ARCHITECT_T, "knob_families": None,
                                   "knob_family": "kv_profile"}).knob_families == ("kv_profile",)
    with pytest.raises(ValueError):
        lb.Target.from_mapping({**ARCHITECT_T, "knob_families": ["routng"]})
    lineup = lb.Target.from_mapping(LINEUP_T)
    assert lineup.is_lineup and lineup.key == ("lineup", "regime-r1")
    assert lineup.as_dict()["scope"] == "lineup"


def test_knob_and_target_share_the_target_budget(tmp_path, alarm):
    knob = [_gpu27(f"k-{i:02d}", value=f"{i}", scope_keys={"knob_family": "spec_draft"})
            for i in range(20)]
    plain = [_gpu27(f"p-{i:02d}", value=f"{i}") for i in range(20)]
    _, ev = _ev(tmp_path, alarm, _write(tmp_path, *knob, *plain), ARCHITECT_T)
    shown = ev["tiers_shown"]
    assert shown["knob"] + shown["target"] <= lb.TIER_CAPS["target"]
    # knob outranks plain target but, while target claims exist, takes at most half (option A)
    assert shown["knob"] == lb.KNOB_CAP_WITH_TARGET == 8 and shown["target"] == 8
    assert ev["section_bytes"] <= lb.DEFAULT_MAX_BYTES


def test_knob_tier_keeps_the_whole_budget_without_target_claims(tmp_path, alarm):
    knob = [_gpu27(f"k-{i:02d}", value=f"{i}", scope_keys={"knob_family": "spec_draft"})
            for i in range(20)]
    _, ev = _ev(tmp_path, alarm, _write(tmp_path, *knob), ARCHITECT_T)
    assert ev["tiers_shown"]["knob"] == 16 and ev["tiers_shown"]["target"] == 0


def test_knob_cap_leaves_room_for_target_claims_ac9(tmp_path, alarm):
    """P1 AC9 regression: 10 kv_profile knob claims must not push a lone target-tier claim
    (KPF-18 item 7 on architect_critic) out of the rendered section."""
    knob = [_gpu27(f"kvq-{i:02d}", value=f"{i}", scope_keys={"knob_family": "kv_profile"})
            for i in range(10)]
    plain = [_gpu27(f"p-{i:02d}", value=f"{100 + i}") for i in range(8)]
    _, ev = _ev(tmp_path, alarm, _write(tmp_path, *knob, *plain), ARCHITECT_T)
    shown = ev["tiers_shown"]
    assert shown["knob"] == 8 and shown["target"] == 8
    assert all(_cid(p) in ev["claim_ids"] for p in plain)


def _lineup_claim(ident, regime):
    return _loop(ident, model=None, quant="", backend="", device="", kind="autopilot-journal",
                 mech=None, outcome="", value="0.81", unit="q/s", metric="quality_per_second",
                 recipe=None, epoch=None, build=None, symbol=None,
                 scope_keys={"stack_regime": regime, "knob_family": "orchestrator",
                        "varied": ["memrl_retrieval.top_k"]})


def test_lineup_target_matches_only_its_stack_regime(tmp_path, alarm):
    old_regime = _lineup_claim("ap-trial-1480", "regime-r0")
    path = _write(tmp_path, old_regime, _gpu27("plain-27b", value="81.12"))
    ans, ev = _ev(tmp_path, alarm, path, LINEUP_T)
    assert ev["tiers"]["lineup"] == 0 and ev["nonempty_target"] is False
    assert ans["banner"] == ("No beliefs at this regime (regime-r1). The lines below are "
                             "sibling/host context only.")
    assert ev["empty_targets"] == ["lineup:regime-r1"]
    # the first post-restart trial at this regime
    new = _lineup_claim("ap-trial-1506", "regime-r1")
    path = _write(tmp_path, old_regime, new, name="after.jsonl")
    _, ev = _ev(tmp_path, alarm, path, LINEUP_T)
    assert ev["tiers"]["lineup"] == 1 and ev["nonempty_target"] is True and ev["banner"] is None
    assert ev["claim_ids"] == [_cid(new)]
    assert "### Usable, lineup tier" in ev["section"] and "lineup regime regime-r1" in ev["section"]


def test_per_role_and_lineup_targets_in_one_answer(tmp_path, alarm):
    pbhol = _gpu27("pb-hol-1:off:short", value="22.05", scope_keys={"knob_family": "routing"})
    ans, ev = _ev(tmp_path, alarm, _write(tmp_path, pbhol), [ARCHITECT_T, LINEUP_T])
    assert ev["tiers"]["knob"] == 1 and ev["nonempty_target"] is True
    assert ans["banner"] == "No beliefs at this regime (regime-r1)."
    assert "role architect_critic" in ev["section"] and "lineup / regime regime-r1" in ev["section"]


def test_bridge_shaped_role_and_lineup_targets_parse():
    """P1-J (orchestrator f0e670a1) sends exactly these shapes; neither may land in
    target_errors. The lineup target has no model and no backend."""
    role = lb.Target.from_mapping({"model_path": f"/mnt/raid0/llm/models/{Q27}", "quant": "Q8_0",
                                   "backend": "gpu", "role": "architect_critic",
                                   "label": "role:architect_critic",
                                   "knob_families": ["spec_draft", "kv_profile", "routing"]})
    assert role.role == "architect_critic" and not role.is_lineup
    lineup = lb.Target.from_mapping({"scope": "lineup", "stack_regime": "sha256:abc",
                                     "knob_families": ["kv_compaction", "orchestrator"],
                                     "label": "lineup"})
    assert lineup.is_lineup and (lineup.model_file, lineup.backend) == ("", "")
    assert lineup.knob_families == ("kv_compaction", "orchestrator")
    for family in ("spec_draft", "kv_profile", "kv_compaction", "placement", "routing",
                   "orchestrator"):
        assert family in lb.KNOB_FAMILIES
    unrecorded = lb.Target.from_mapping({"scope": "lineup", "label": "lineup"})
    assert unrecorded.is_lineup and unrecorded.stack_regime == ""
    assert not lb.lineup_matches({"stack_regime": ""}, unrecorded)


def test_lineup_target_through_prepare_is_not_a_target_error(tmp_path, alarm):
    ans, ev = _ev(tmp_path, alarm, _write(tmp_path, _gpu27("x", value="1")),
                  [ARCHITECT_T, {"scope": "lineup", "stack_regime": "sha256:abc",
                                 "knob_families": ["kv_compaction", "orchestrator"],
                                 "label": "lineup"}])
    assert "target_errors" not in ev and len(ans["targets"]) == 2
    assert ans["targets"][1]["scope"] == "lineup"


def test_p1_acceptance_script_runs_on_a_fixture_ledger(tmp_path, capsys):
    """The acceptance script itself (not the Phase-1 numbers): it runs end to end on a small
    ledger, refuses the canonical path, and AC9 passes on PB-HOL-1 / KPF-18 item-7 shaped claims."""
    import p1_acceptance as acc
    pbhol = _gpu27("pb-hol-1:20261021T160010Z:off:short", kind="pb-hol-1", value="22.05",
                   scope_keys={"knob_family": "slot_serving",
                               "varied": ["short_slot_index_order"]})
    kpf27 = _gpu27("kpf18:kpf18-run-c:item7:B1", kind="kv-prefix-fork", value="25",
                   scope_keys={"knob_family": "slot_serving", "varied": ["slot_fork"]})
    kpf35 = _loop("kpf18:kpf18cpu:item7:B1", model=None, quant="Q8_0", kind="kv-prefix-fork",
                  mech=None, outcome="", value="40", unit="s", recipe=None, epoch=None,
                  build=None, symbol=None,
                  scope_keys={"model_file": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
                              "knob_family": "slot_serving", "varied": ["slot_fork"]})
    path = _write(tmp_path, pbhol, kpf27, kpf35)
    rc = acc.main(["--ledger", str(path), "--as-of", AS_OF, "--skip", "AC7", "--skip", "AC8",
                   "--json"])
    out = json.loads(capsys.readouterr().out)
    checks = {c["check"]: c for c in out["checks"]}
    assert rc == 1 and not out["pass"]                 # AC1-AC5 need the real backfill
    assert checks["AC9"]["pass"], checks["AC9"]["detail"]
    assert "PB-HOL-1 1 claim(s) on tier target, 1 shown with a value line" in checks["AC9"]["detail"]
    assert set(checks) == {"AC1", "AC2", "AC3", "AC4", "AC5", "AC9"}
    assert acc.main(["--ledger", str(lb.CANONICAL_LEDGER)]) == 2 or not lb.CANONICAL_LEDGER.exists()


def test_claim_without_device_matches_gpu_target_and_is_never_host(tmp_path, alarm):
    """Lanes K/L (KPF-18, PB-HOL-1) scope by model_file + quant + backend=gpu and declare NO
    device (their argv names ROCm0, not the card). An undeclared device is unspecified, not a
    mismatch; a claim that names a model can never be host tier."""
    kpf = _loop("kpf18:kpf18-run-c:item7:A1", model=Q27, quant="Q8_0", backend="gpu", device="",
                kind="kv-prefix-fork", mech=None, outcome="", value="144", unit="s",
                recipe=None, epoch=None, build=None, symbol=None,
                scope_keys={"knob_family": "slot_serving", "varied": ["slot_fork"]})
    source = next(f for f in kpf if f["frame_type"].endswith("source_observed/v1"))
    assert "device" not in source["assertion"]["applicability"]
    _, ev = _ev(tmp_path, alarm, _write(tmp_path, kpf), ARCHITECT_T)
    assert ev["tiers"]["target"] == 1 and ev["tiers"]["host"] == 0
    assert ev["claims"][0]["tier"] == "target" and _cid(kpf) in ev["claim_ids"]
    scope = source["assertion"]["applicability"]
    for raw in (ARCHITECT_T, {**ARCHITECT_T, "backend": "cpu"}, QWEN35_T, DS41_Q4_T):
        assert not lb.host_matches(scope, lb.Target.from_mapping(raw))
    # same file on a cpu target: backend differs, so no tier at all (not host, not target)
    assert lb.tier_of(scope, lb.Target.from_mapping({**ARCHITECT_T, "backend": "cpu"})) is None


class _StubReader:
    """Just enough of p1_acceptance.Reader for ac5: per-target (evaluation, collection)."""

    def __init__(self, evs, rows35):
        self.evs, self.rows35 = evs, rows35

    def read(self, name, quant=None):
        rows = self.rows35 if name == "Qwen3.6-35B" else []
        return self.evs[name], {"rows": rows, "flagged": {b: [] for b in lb.FLAG_BUCKETS}}

    def target(self, name, quant=None):
        import p1_acceptance as acc
        return lb.Target.from_mapping(acc.TARGETS[name])


def _ac5_inputs(*, vl_target=0, vl_banner="No beliefs are scoped to Qwen3-VL-30B.",
                model35="Qwen3.6-35B-A3B-MTP-Q8_0.gguf", same_sets=False):
    import p1_acceptance as acc
    evs = {}
    for i, name in enumerate(acc.CPU_FIVE):
        ids = ["clm_shared"] if same_sets and name in ("DS41-Q4", "Q38FN") else [f"clm_{i}"]
        evs[name] = {"tiers": {"target": 0}, "banner": "", "section": "x", "claim_ids": ids}
    evs["Qwen3-VL-30B"].update(tiers={"target": vl_target}, banner=vl_banner,
                               section=f"{vl_banner}\nmore")
    rows35 = [{"claim_id": f"clm_kpf{i}", "tier": "target", "model_file": model35,
               "source_kind": "kv-prefix-fork-measurement"} for i in range(3)]
    return evs, rows35


def test_ac5_amended_passes_when_35b_target_claims_are_scoped_to_the_35b():
    import p1_acceptance as acc
    result = acc.ac5(_StubReader(*_ac5_inputs()))
    assert result["pass"], result["detail"]
    assert "kv-prefix-fork-measurement': 3" in result["detail"]
    assert "pairwise distinct across the five CPU models True" in result["detail"]


@pytest.mark.parametrize("kw,why", [
    ({"vl_target": 2}, "Qwen3-VL-30B: target 2"),
    ({"vl_banner": ""}, "banner False"),
    ({"model35": "Qwen3.8-27B-Q8_0.gguf"}, "foreign"),
    ({"same_sets": True}, "identical: [('DS41-Q4', 'Q38FN')]"),
])
def test_ac5_amended_fails_on_each_leg(kw, why):
    import p1_acceptance as acc
    result = acc.ac5(_StubReader(*_ac5_inputs(**kw)))
    assert not result["pass"] and why in result["detail"], result["detail"]
