"""VB-AK-SEAT: the actor-seat write-side contract and its strict reader.

Pinned here:

* the closed producer field sets (call record, arm record, seat, session) -- the contract the
  research producer implements in ``actors._record_call`` and the seat A/B driver;
* pre-hook records emit ZERO tuples -- both the synthetic pre-hook shapes and, when present, the
  real 2026-09-24 records under ``/mnt/raid0/llm/tmp/ak-seat-ab`` (read only);
* a complete record projects tuples graded by ``claim_tuple.grade()`` at ``Judged/Located`` (an
  OBSERVATION) with n = 1 and the producer's scope carried verbatim; a cited protocol would lift
  the same tuple through the SAME ladder (so no ladder lives here);
* a v1 record missing a required field, tampered, pre-dating the hook, or backfilled is REFUSED;
* censored (timeout / signal) sessions emit zero tuples;
* a mutated export grades DOWN (attestation absent), it is not skipped;
* no ladder is registered by importing the adapter; writer -> ``cli.py ingest ak-actor-seat``.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from adapters import autokernel_actor_seat as reader  # noqa: E402
from adapters import autokernel_actor_seat_capture as capture  # noqa: E402
from ledger import Ledger  # noqa: E402

COMMIT = "e94959713671a6f73e0f52af76771532679a87fe"
ANCHOR = "ebb68dc55d5f6af4a4a5dccdd2a013fa76c63bee"
PROMPT = "## Selected target\n```json\n{}\n```\nPropose ONE change." * 40
SCOPE = ("n=1 planner session per arm, no repeat, no noise floor; both arms share this prompt, "
         "which differs from the historical escaped-prompt plain run -- a seat-shape "
         "observation, never a seat effect")
AS_OF = "2026-09-24T11:00:00Z"

PRODUCER = {"repo": "epyc-inference-research", "commit": COMMIT,
            "module": "scripts/kernel_rnd/autokernel/loop/actors.py"}
BACKEND = {"kind": "opencode", "model": "qwen-gpu/qwen3.8-27b", "effort": "high",
           "agent": "autokernel-planner"}
PLAIN_BACKEND = {**BACKEND, "agent": None}
SERVER = {"endpoint": "http://127.0.0.1:8083/v1", "served_model": "qwen3.8-27b",
          "build_info": "10303-ffc1bac82"}


def seat(bounded: bool = True) -> dict:
    if not bounded:
        return {"arm": "plain", "bounded": False, "fan_out": False, "steps": None,
                "opencode_version": "1.18.31", "global_config_sha256": "a" * 64,
                "config": None, "instructions": None}
    return {"arm": "bounded", "bounded": True, "fan_out": True, "steps": 60,
            "opencode_version": "1.18.31", "global_config_sha256": "a" * 64,
            "config": {"path": "/mnt/raid0/llm/tmp/ak-seat-ab/actor-opencode-planner.json",
                       "sha256": "b" * 64, "bytes": 4315},
            "instructions": {"path": "actor-opencode-planner.instructions.md",
                             "sha256": "c" * 64, "bytes": 2100}}


def call_record(**over) -> dict:
    kw = dict(call_id="20260924T130000Z-4242-0a1b2c3d4e5f", role="planner",
              workspace="/mnt/raid0/llm/tmp/ak-seat-ab/lane", producer=PRODUCER, seat=seat(),
              backend=BACKEND, server=SERVER, prompt=PROMPT,
              started_at="2026-09-24T13:00:00Z", finished_at="2026-09-24T13:20:00Z",
              wall_s=1200.4, returncode=0, timed_out=False,
              recorded_at="2026-09-24T13:20:01Z",
              reply={"stdout": {"path": "20260924T132000-opencode-x-rc0.stdout",
                                "sha256": "d" * 64, "bytes": 10230},
                     "stderr": {"path": "20260924T132000-opencode-x-rc0.stderr",
                                "sha256": "e" * 64, "bytes": 6794}})
    kw.update(over)
    return capture.build_call_record(**kw)


def session(root: bool, sid: str, export: Path, steps: int, tools: dict) -> dict:
    raw = export.read_bytes()
    import hashlib
    return {"session_id": sid, "root": root,
            "export": {"path": export.name, "sha256": hashlib.sha256(raw).hexdigest(),
                       "bytes": len(raw)},
            "steps": steps, "tool_calls": sum(tools.values()), "tools": tools,
            "compactions": 0, "decoded_tokens": 9000 + steps, "uncached_prompt_tokens": 40000,
            "context_first": 21000, "context_max": 61000, "tool_output_chars": 120000}


def write_arm(d: Path, *, bounded: bool = True, name: str | None = None, **over) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    arm = "bounded" if bounded else "plain"
    root_export = d / f"{arm}-ses_root.json"
    root_export.write_text(json.dumps({"messages": [{"info": {"role": "assistant"}}]}))
    sessions = [session(True, "ses_root", root_export, 24, {"autokernel-tools_grep": 9,
                                                           "task": 2, "bash": 3})]
    if bounded:
        scout = d / f"{arm}-ses_scout.json"
        scout.write_text(json.dumps({"messages": []}))
        sessions.append(session(False, "ses_scout", scout, 7, {"autokernel-tools_read_range": 6}))
    kw = dict(ab_id="ds41-c20-seat-ab-20260924", arm_id=f"{arm}-20260924T130000Z",
              category="CANDIDATE" if bounded else "BASELINE", scope=SCOPE, role="planner",
              producer=PRODUCER,
              driver={"path": "/mnt/raid0/llm/tmp/ak-seat-ab/driver.py", "sha256": "f" * 64},
              seat=seat(bounded), backend=BACKEND if bounded else PLAIN_BACKEND, server=SERVER,
              prompt=PROMPT, lane={"path": "/mnt/raid0/llm/tmp/ak-seat-ab/lane",
                                   "anchor_commit": ANCHOR, "edited": False},
              started_at="2026-09-24T13:00:00Z", finished_at="2026-09-24T13:30:00Z",
              wall_s=1800.2,
              call={"returncode": 0, "timed_out": False,
                    "call_id": "20260924T130000Z-4242-0a1b2c3d4e5f"},
              verdict="schema_valid", sessions=sessions, recorded_at="2026-09-24T13:31:00Z")
    kw.update(over)
    record = capture.build_arm_record(**kw)
    path = d / (name or f"result-{arm}.json")
    path.write_text(json.dumps(record, indent=2))
    return path


def write_log(path: Path, *records) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as handle:
        for r in records:
            handle.write((r if isinstance(r, str) else json.dumps(r, sort_keys=True)) + "\n")
    return path


def rehash(record: dict) -> dict:
    record["record_sha256"] = capture.record_digest(record)
    return record


#: The exact pre-hook shape `actors._record_call` wrote at e9495971 (the real 2026-09-24 line).
PRE_HOOK_LINE = json.dumps({
    "agent": "autokernel-planner", "backend": "opencode:qwen-gpu/qwen3.8-27b@high",
    "opencode_config": "/mnt/raid0/llm/tmp/ak-seat-ab/actor-opencode-planner.json",
    "prompt_chars": 75904, "returncode": -15, "ts": "2026-09-24T11:19:39Z", "wall_s": 2180.5},
    sort_keys=True)
PRE_HOOK_OK_LINE = json.dumps({
    "agent": None, "backend": "claude:claude-fable-5-1@medium", "opencode_config": None,
    "prompt_chars": 20000, "returncode": 0, "ts": "2026-09-24T11:30:00Z", "wall_s": 75.0},
    sort_keys=True)
#: The pre-hook driver result shape (`result-bounded-v1-stopped.json`).
PRE_HOOK_RESULT = {"arm": "bounded", "started": "10:43:19", "wall_s": 2180.5,
                   "hypothesis": {"abstain": "<reason>"}, "lane_edited": False,
                   "sessions": ["ses_f2cfcc068ffeVO5UxTL03LLm2p"],
                   "session_stats": [{"session": "ses_f2cfcc068ffeVO5UxTL03LLm2p",
                                      "steps": 71, "tool_calls": 70, "output_tokens": 63800}]}


# --- pre-hook: zero tuples ---------------------------------------------------------------------

def test_pre_hook_call_lines_emit_zero_tuples_even_when_they_carry_a_wall(tmp_path):
    log = write_log(tmp_path / "actor-replies" / "actor-calls.jsonl", PRE_HOOK_LINE,
                    PRE_HOOK_OK_LINE)
    assert reader.native_rows(log) == ()
    assert reader.frames_for_path(log, as_of=AS_OF) == []


def test_pre_hook_driver_result_emits_zero_tuples_even_when_it_carries_stats(tmp_path):
    path = tmp_path / "result-bounded.json"
    path.write_text(json.dumps(PRE_HOOK_RESULT))
    assert reader.native_rows(path) == ()


REAL_AB = Path("/mnt/raid0/llm/tmp/ak-seat-ab")


@pytest.mark.skipif(not REAL_AB.is_dir(), reason="real 2026-09-24 seat A/B records not on this host")
def test_the_real_2026_09_24_records_are_pre_hook_and_emit_nothing():
    """Read-only replay over the real corpus: every record predates the hook."""
    units = sorted(REAL_AB.glob("actor-replies/actor-calls.jsonl")) + sorted(
        REAL_AB.glob("result-*.json"))
    assert units, "expected the real call log / result files"
    for unit in units:
        assert reader.native_rows(unit) == (), unit


def test_mixed_log_projects_only_the_post_hook_lines(tmp_path):
    log = write_log(tmp_path / "actor-calls.jsonl", PRE_HOOK_LINE, call_record())
    natives = reader.native_rows(log)
    assert len(natives) == 1 and natives[0]["line"] == 2


# --- complete records: projected, graded by the shared ladder, capped at observation ----------

def test_complete_call_record_is_one_observation_graded_by_claim_tuple(tmp_path):
    log = write_log(tmp_path / "actor-calls.jsonl", call_record())
    (native,) = reader.native_rows(log)
    tup = reader.project(native)
    assert (tup.metric, tup.value, tup.unit) == ("actor_call_wall_s", 1200.4, "s")
    assert tup.metric_direction == "lower_better" and tup.reps == 1
    assert tup.protocol_id == "" and tup.source_class == "measurement"
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Judged", "Located")
    assert any("OBSERVATION" in r for r in reasons)
    assert tup.extra["seat_digest"] == capture.seat_digest(tup.extra["seat"])
    assert "n=1 call" in tup.claim and "not a seat comparison" in tup.claim
    frames = reader.frames_for_path(log, as_of=AS_OF)
    assert len(frames) == 3
    assert frames[2]["assertion"]["grade"] == {"Q": "Judged", "T": "Located"}


def test_complete_arm_record_projects_five_observations_with_scope_verbatim(tmp_path):
    path = write_arm(tmp_path / "ab")
    natives = reader.native_rows(path)
    tuples = [reader.project(n) for n in natives]
    assert [t.metric for t in tuples] == list(capture.ARM_METRICS)
    values = {t.metric: t.value for t in tuples}
    # totals are root + scouts: 24 + 7 steps, 14 + 6 tool calls
    assert values == {"seat_arm_wall_s": 1800.2, "seat_arm_steps": 31,
                      "seat_arm_tool_calls": 20, "seat_arm_decoded_tokens": 18031,
                      "seat_arm_compactions": 0}
    assert len({t.measurement_id for t in tuples}) == 5
    for t in tuples:
        assert ct.grade(t)[:2] == ("Judged", "Located")
        assert t.category == "CANDIDATE" and t.reps == 1
        assert SCOPE in t.claim and "n=1 arm run" in t.claim
        assert t.attestation_present is True and t.attestation_verified is True
        assert t.extra["exports_verified"] == {"ses_root": True, "ses_scout": True}


def test_plain_and_bounded_arms_do_not_collide(tmp_path):
    ids = set()
    for bounded in (True, False):
        path = write_arm(tmp_path / ("b" if bounded else "p"), bounded=bounded)
        ids |= {reader.project(n).measurement_id for n in reader.native_rows(path)}
    assert len(ids) == 10


def test_a_cited_protocol_lifts_through_the_same_ladder(tmp_path):
    """Proves the adapter grades nothing: only the tuple's elements changed."""
    path = write_arm(tmp_path / "ab", protocol_id="measurement/protocols/hypothetical.md")
    tup = reader.project(reader.native_rows(path)[0])
    assert ct.grade(tup)[:2] == ("Witnessed", "Attested")


def test_importing_the_adapter_registers_no_ladder():
    assert "autokernel-actor-seat" in ct.registered()
    assert ct.source_classes()["autokernel-actor-seat"] == "measurement"
    modules = {module for module, _ in ct.ladders().values()}
    assert not any("actor_seat" in m for m in modules)
    with pytest.raises(ct.ProjectionError, match="already has a ladder"):
        ct.register_ladder("measurement", "adapters/autokernel_actor_seat.py")(
            lambda *a: ("Judged", "T0", []))


# --- refusals ----------------------------------------------------------------------------------

@pytest.mark.parametrize("path_keys", [
    ("prompt", "sha256"), ("seat", "global_config_sha256"), ("server", "endpoint"),
    ("producer", "commit"), ("recorded_at",), ("call_id",),
])
def test_call_record_missing_a_required_field_is_refused(tmp_path, path_keys):
    rec = call_record()
    target = rec
    for key in path_keys[:-1]:
        target = target[key]
    del target[path_keys[-1]]
    rehash(rec)
    log = write_log(tmp_path / "actor-calls.jsonl", rec)
    with pytest.raises(ct.ProjectionError, match="does not re-derive"):
        reader.native_rows(log)


def test_bounded_seat_without_its_config_digest_is_refused(tmp_path):
    rec = call_record()
    rec["seat"]["config"] = None
    log = write_log(tmp_path / "actor-calls.jsonl", rehash(rec))
    with pytest.raises(ct.ProjectionError, match="seat.config must reference"):
        reader.native_rows(log)


@pytest.mark.parametrize("key", ["scope", "sessions", "verdict", "totals", "lane", "driver"])
def test_arm_record_missing_a_required_field_is_refused(tmp_path, key):
    path = write_arm(tmp_path / "ab")
    rec = json.loads(path.read_text())
    del rec[key]
    path.write_text(json.dumps(rehash(rec)))
    with pytest.raises(ct.ProjectionError, match="does not re-derive"):
        reader.native_rows(path)


def test_tampered_value_is_refused(tmp_path):
    path = write_arm(tmp_path / "ab")
    rec = json.loads(path.read_text())
    rec["wall_s"] = 60.0  # record_sha256 left stale
    path.write_text(json.dumps(rec))
    with pytest.raises(ct.ProjectionError, match="record_sha256 does not bind"):
        reader.native_rows(path)


def test_totals_that_do_not_re_derive_are_refused_even_when_rehashed(tmp_path):
    path = write_arm(tmp_path / "ab")
    rec = json.loads(path.read_text())
    rec["totals"]["steps"] = 24  # root only -- the scouts' steps silently dropped
    path.write_text(json.dumps(rehash(rec)))
    with pytest.raises(ct.ProjectionError, match="totals do not re-derive"):
        reader.native_rows(path)


def test_a_session_that_started_before_the_hook_is_refused_as_a_retrofit():
    with pytest.raises(capture.CaptureError, match="before the VB-AK-SEAT hook"):
        call_record(started_at="2026-09-24T10:43:19Z", finished_at="2026-09-24T11:19:39Z",
                    wall_s=2180.0, recorded_at="2026-09-24T11:19:40Z")


def test_a_backfilled_record_is_refused():
    with pytest.raises(capture.CaptureError, match="never backfills"):
        call_record(recorded_at="2026-09-24T14:00:00Z")


def test_the_template_echo_is_a_verdict_not_an_abstain(tmp_path):
    path = write_arm(tmp_path / "ab", verdict="template_echo")
    tup = reader.project(reader.native_rows(path)[0])
    assert "verdict template_echo" in tup.claim
    with pytest.raises(capture.CaptureError, match="verdict must be one of"):
        write_arm(tmp_path / "bad", verdict="abstained-ish")


def test_the_reader_cannot_be_bypassed_with_a_hand_built_native(tmp_path):
    with pytest.raises(ct.ProjectionError):
        reader.project({"kind": "call", "metric": "actor_call_wall_s",
                        "record": json.loads(PRE_HOOK_LINE)})


# --- censored sessions and attestation ---------------------------------------------------------

def test_timeout_and_signal_death_are_valid_records_that_project_nothing(tmp_path):
    timeout = call_record(call_id="c-timeout", returncode=-1, timed_out=True)
    killed = call_record(call_id="c-killed", returncode=-15)
    log = write_log(tmp_path / "actor-calls.jsonl", timeout, killed)
    assert reader.native_rows(log) == ()
    arm = write_arm(tmp_path / "ab", call={"returncode": -15, "timed_out": False,
                                           "call_id": None})
    assert reader.native_rows(arm) == ()


def test_timeout_must_carry_the_timeout_returncode():
    with pytest.raises(capture.CaptureError, match="timed-out call is recorded with returncode"):
        call_record(returncode=-15, timed_out=True)


def test_a_mutated_export_grades_down_and_is_not_skipped(tmp_path):
    path = write_arm(tmp_path / "ab")
    (tmp_path / "ab" / "bounded-ses_root.json").write_text("{}")
    tuples = [reader.project(n) for n in reader.native_rows(path)]
    assert len(tuples) == 5
    for t in tuples:
        assert t.attestation_present is False and t.attestation_verified is None
        assert ct.grade(t)[:2] == ("Judged", "Located")
    assert tuples[0].extra["exports_verified"]["ses_root"] is False


def test_duplicate_call_ids_in_one_log_are_refused(tmp_path):
    rec = call_record()
    log = write_log(tmp_path / "actor-calls.jsonl", rec, copy.deepcopy(rec))
    with pytest.raises(ct.ProjectionError, match="duplicate call_id"):
        reader.native_rows(log)


# --- end to end --------------------------------------------------------------------------------

def write_fixture(tmp: Path) -> Path:
    """A campaign-shaped dir: one call log (pre-hook + post-hook) and two arm results."""
    write_log(tmp / "actor-replies" / "actor-calls.jsonl", PRE_HOOK_LINE, call_record())
    write_arm(tmp, bounded=True)
    write_arm(tmp, bounded=False)
    return tmp


def test_cli_ingest_end_to_end(tmp_path, capsys):
    root = write_fixture(tmp_path / "fx")
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "ak-actor-seat",
                   "--path", str(root), "--as-of", AS_OF])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] == [] and report["rows_projected"] == 11
    supports = [r.frame for r in Ledger(ledger).read_all()
                if r.frame["frame_type"].endswith("evidence_supports_claim/v1")]
    assert {tuple(f["assertion"]["grade"].values()) for f in supports} == {("Judged", "Located")}
