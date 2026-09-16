"""VB-MHS-OPS: mutation-guard verdict rates + eval-leakage guard operability -> ClaimTuple.

The fixture under ``fixtures/mhs_guard/orchestration`` was WRITTEN BY THE PRODUCER CODE of
orchestrator ``sub/gate-frontier-20260916`` (``fixtures/mhs_guard/regen.py``: the real
``EvalLeakageMonitor``, ``ExperimentJournal``, ``rejected_mutation_ledger`` and the real
``prompt_forge`` reason builders), so the reader is tested against the producer's bytes.

Pinned:
* the field names and reason prefixes the reader relies on (and, when the producer source is
  reachable in git, that the producer still writes them -- a producer change breaks loudly);
* rates re-derive from the fixture; vocabulary-unavailable rejections leave the leakage
  denominator only; unscreened skips and pre-guard rejects leave every denominator;
* pre-hook data, open windows and open alarm intervals project nothing;
* grading is ``claim_tuple.grade()``'s, never the adapter's;
* rows this producer could not have written are refused.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import mhs_guard as adapter  # noqa: E402

FIXTURE = HERE / "fixtures" / "mhs_guard" / "orchestration"
HOOK = "2026-09-17T10:00:00+00:00"
AS_OF = "2026-09-19T00:00:00Z"
ORCH = Path("/workspace/repos/epyc-orchestrator")
PRODUCER_REFS = ("origin/sub/gate-frontier-20260916", "sub/gate-frontier-20260916", "origin/main")


def copy_fixture(tmp: Path) -> Path:
    """A writable copy of the producer-written journal dir (used by test_ingest_sources)."""
    dest = tmp / "orchestration"
    shutil.copytree(FIXTURE, dest)
    return dest


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _rates(unit=FIXTURE, since=HOOK) -> dict[str, ct.ClaimTuple]:
    return {n["reason_class"]: adapter.project(n)
            for n in adapter.native_rows(unit, since=since)}


# --- producer contract ---------------------------------------------------------------------------

def test_fixture_rows_carry_every_pinned_field():
    ledger = _lines(FIXTURE / adapter.LEDGER_FILENAME)
    journal = _lines(FIXTURE / "autopilot_journal.jsonl")
    assert ledger and all(set(adapter.LEDGER_FIELDS) <= set(r) for r in ledger)
    trials = [r for r in journal if "trial_id" in r]
    assert trials and all(set(adapter.TRIAL_FIELDS) <= set(r) for r in trials)
    events = [r for r in journal if r.get("type") == adapter.EVENT_TYPE]
    assert {e["event"] for e in events} == set(adapter.EVENT_FIELDS)
    for e in events:
        assert set(adapter.EVENT_FIELDS[e["event"]]) <= set(e), e["event"]
        assert e["alarm_key"] == adapter.ALARM_KEY and e["actor"] == adapter.EVENT_ACTOR
        assert "timestamp" in e and "ts" not in e  # append_ledger_event stamps `timestamp`
    details = {r["gate_detail"].split(":")[0] + ":" for r in ledger
               if r["rejecting_gate"] == adapter.GUARD_GATE}
    assert set(adapter.REASON_PREFIXES.values()) <= details


def test_pinned_vocabulary_is_exactly_this():
    assert adapter.LEDGER_FIELDS == ("schema_version", "writer", "timestamp", "trial_id",
                                     "rejecting_gate", "gate_detail", "artifact_kind")
    assert adapter.TRIAL_FIELDS == ("trial_id", "timestamp", "action_type", "outcome_status")
    assert adapter.EVENT_FIELDS == {
        "preflight_failed": ("error", "problem_paths", "sources", "elapsed_s"),
        "alarm_raised": ("consecutive", "threshold", "error", "problem_paths",
                         "alarm_delivered"),
        "alarm_cleared": ("after_consecutive", "alarm_delivered"),
    }
    assert adapter.REASON_PREFIXES == {
        "eval_instance_leakage": "eval_instance_leakage:",
        "eval_leakage_vocabulary_unavailable": "eval_leakage_vocabulary_unavailable:",
        "effect_risk_gate": "effect_risk_gate:",
    }
    assert (adapter.GUARD_GATE, adapter.PRE_GUARD_GATES) == ("transfer_safety",
                                                            frozenset({"syntax_validation"}))


def _producer_source(path: str) -> str | None:
    for ref in PRODUCER_REFS:
        try:
            out = subprocess.run(["git", "-C", str(ORCH), "show", f"{ref}:{path}"],
                                 capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        if out.returncode == 0:
            return out.stdout
    return None


def test_producer_source_still_writes_the_pinned_vocabulary():
    monitor = _producer_source("scripts/autopilot/eval_leakage_monitor.py")
    forge = _producer_source("scripts/autopilot/species/prompt_forge.py")
    ledger = _producer_source("scripts/autopilot/rejected_mutation_ledger.py")
    actions = _producer_source("scripts/autopilot/actions.py")
    if not all((monitor, forge, ledger, actions)):
        pytest.skip("producer source not reachable in the orchestrator clone")
    assert f'LEDGER_EVENT_TYPE = "{adapter.EVENT_TYPE}"' in monitor
    assert f'ALARM_KEY = "{adapter.ALARM_KEY}"' in monitor
    assert f'"actor": "{adapter.EVENT_ACTOR}"' in monitor
    for event, fields in adapter.EVENT_FIELDS.items():
        call = re.search(r'self\._journal\(\s*"%s",(?P<body>.*?)\)\n' % event, monitor, re.S)
        assert call, f"producer no longer journals {event}"
        for name in fields:
            assert f"{name}=" in call["body"], (event, name)
    for prefix in adapter.REASON_PREFIXES.values():
        assert f'f"{prefix}' in forge, prefix
    for name in adapter.LEDGER_FIELDS:
        assert f'"{name}":' in ledger, name
    assert 'rejecting_gate="transfer_safety"' in actions
    assert 'gate_detail=str(getattr(mutation, "safety_reason", "unsafe"))' in actions
    code = actions.split("def _action_code_mutation", 1)[1]
    assert code.index('rejecting_gate="syntax_validation"') < code.index(
        'rejecting_gate="transfer_safety"'), "syntax check no longer precedes the guard"


# --- verdict rates -------------------------------------------------------------------------------

def test_rates_re_derive_from_the_producer_rows():
    rates = _rates()
    assert set(rates) == set(adapter.REASON_CLASSES)
    leak = rates["eval_instance_leakage"]
    # screened = 101,102,103,104,105,109; 104 was vocabulary-unavailable -> held out of leakage
    assert (leak.value, leak.reps) == (0.2, 5)
    for cls in ("eval_leakage_vocabulary_unavailable", "effect_risk_gate",
                "other_transfer_safety"):
        assert (rates[cls].value, rates[cls].reps) == (round(1 / 6, 6), 6), cls
    extra = leak.extra
    assert extra["unscreened_skips"] == [106] and extra["pre_guard_rejects"] == [108]
    assert extra["other_gate_rejects"] == 1  # 105: safety_gate revert, screened, not a guard reject
    assert extra["window_start"] == HOOK and extra["window_end"] == "2026-09-18T00:00:00+00:00"
    assert len(extra["window_rows_sha256"]) == 64
    assert "held out" in leak.claim


def test_grade_is_the_shared_ladder_and_identity_is_unique():
    tuples = list(_rates().values())
    for tup in tuples:
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ct._measurement_ladder(tup)[:2]
        assert q == "Judged"  # no codified protocol: an OBSERVATION
        frames = ct.to_frames(tup, as_of=AS_OF, adapter_id=adapter.ADAPTER_ID,
                              authority=adapter.AUTHORITY)
        assert len(frames) == 3
    assert len({t.measurement_id for t in tuples}) == len(tuples)
    assert ct.source_classes()[adapter.VERDICT_PROJECTION] == ct.MEASUREMENT_CLASS
    assert ct.source_classes()[adapter.OPS_PROJECTION] == ct.MEASUREMENT_CLASS


def test_pre_hook_data_gets_zero_rows(monkeypatch):
    monkeypatch.delenv(adapter.HOOK_SINCE_ENV, raising=False)
    assert adapter.HOOK_SINCE == ""  # set only when the producer is live
    assert adapter.native_rows(FIXTURE) == ()  # epoch unknown -> decline everything
    assert adapter.native_rows(FIXTURE, since="2026-09-18T12:00:00+00:00") == ()
    # an epoch before trial 100 admits its guard-shaped reject; the real epoch does not
    early = {n["reason_class"]: n for n in
             adapter.native_rows(FIXTURE, since="2026-09-17T08:00:00+00:00")}
    assert early["eval_instance_leakage"]["rejections"] == 2
    assert _rates()["eval_instance_leakage"].extra["rejections"] == 1
    monkeypatch.setenv(adapter.HOOK_SINCE_ENV, HOOK)
    assert len(adapter.native_rows(FIXTURE)) == 4


def test_malformed_epoch_is_refused(monkeypatch):
    monkeypatch.setenv(adapter.HOOK_SINCE_ENV, "2026-09-17 10:00")  # naive
    with pytest.raises(ct.ProjectionError, match="tz-aware"):
        adapter.native_rows(FIXTURE)


def test_open_window_and_idle_window_project_nothing(tmp_path):
    unit = copy_fixture(tmp_path)
    journal = unit / "autopilot_journal.jsonl"
    rows = _lines(journal)
    # drop everything on 2026-09-18: nothing closes the 09-17 window any more
    journal.write_text("".join(json.dumps(r) + "\n" for r in rows
                               if not str(r.get("timestamp", "")).startswith("2026-09-18")))
    assert adapter.native_rows(unit, since=HOOK) == ()
    # a closed window whose only mutation rows are unscreened is idle, not a 0 % rate
    only = [r for r in rows if r.get("trial_id") in (106, 110)]
    journal.write_text("".join(json.dumps(r) + "\n" for r in only))
    (unit / adapter.LEDGER_FILENAME).write_text("")
    assert adapter.native_rows(unit, since=HOOK) == ()


def test_missing_ledger_declines(tmp_path):
    unit = copy_fixture(tmp_path)
    (unit / adapter.LEDGER_FILENAME).unlink()
    assert adapter.native_rows(unit, since=HOOK) == ()


def test_foreign_or_unjoinable_ledger_rows_are_refused(tmp_path):
    unit = copy_fixture(tmp_path)
    ledger = unit / adapter.LEDGER_FILENAME
    good = _lines(ledger)
    bad = dict(good[1], writer="llm")
    ledger.write_text("".join(json.dumps(r) + "\n" for r in [bad]))
    with pytest.raises(ct.ProjectionError, match="harness record"):
        adapter.native_rows(unit, since=HOOK)
    orphan = dict(good[1], trial_id=999)
    ledger.write_text(json.dumps(orphan) + "\n")
    with pytest.raises(ct.ProjectionError, match="no post-hook mutation row"):
        adapter.native_rows(unit, since=HOOK)
    ledger.write_text("".join(json.dumps(r) + "\n" for r in [good[1], good[1]]))
    with pytest.raises(ct.ProjectionError, match="second record"):
        adapter.native_rows(unit, since=HOOK)
    missing = {k: v for k, v in good[1].items() if k != "gate_detail"}
    ledger.write_text(json.dumps(missing) + "\n")
    with pytest.raises(ct.ProjectionError, match="gate_detail"):
        adapter.native_rows(unit, since=HOOK)


def test_projection_refuses_a_rate_that_does_not_re_derive():
    native = next(n for n in adapter.native_rows(FIXTURE, since=HOOK)
                  if n["reason_class"] == "eval_instance_leakage")
    with pytest.raises(ct.ProjectionError, match="held out"):
        adapter.project(dict(native, denominator=6))  # vocabulary failures folded back in
    with pytest.raises(ct.ProjectionError):
        adapter.project(dict(native, rejections=7))
    with pytest.raises(ct.ProjectionError):
        adapter.project(dict(native, kind="something"))
    with pytest.raises(ct.ProjectionError):
        adapter.project(dict(native, reason_class="static"))


# --- operability ---------------------------------------------------------------------------------

def test_operability_projects_preflight_and_closed_interval_only():
    tuples = [adapter.project_ops(n) for n in adapter.ops_native_rows(FIXTURE)]
    by_metric = {t.metric: t for t in tuples}
    assert len(tuples) == 2
    pre = by_metric["autopilot.eval_leakage_guard.preflight_failed"]
    assert pre.value == 1 and pre.extra["error"] == "eval_id_source_missing:question_pool.jsonl"
    alarm = by_metric["autopilot.eval_leakage_guard.alarm_open_s"]
    assert alarm.value == 1800.0
    assert (alarm.extra["raised_at"], alarm.extra["cleared_at"]) == (
        "2026-09-17T10:05:00+00:00", "2026-09-17T10:35:00+00:00")
    for tup in tuples:
        assert ct.grade(tup)[0] == "Judged"
    # the 2026-09-18 raise never cleared: reported, never projected
    open_ = adapter.open_alarm_intervals(FIXTURE)
    assert [o["raised_at"] for o in open_] == ["2026-09-18T02:00:00+00:00"]


def _events(unit: Path) -> tuple[Path, list[dict], list[dict]]:
    journal = unit / "autopilot_journal.jsonl"
    rows = _lines(journal)
    return journal, [r for r in rows if r.get("type") != adapter.EVENT_TYPE], \
        [r for r in rows if r.get("type") == adapter.EVENT_TYPE]


def _write(journal: Path, rows: list[dict]) -> None:
    journal.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_orphan_clear_and_foreign_events_are_refused(tmp_path):
    unit = copy_fixture(tmp_path)
    journal, trials, events = _events(unit)
    cleared = next(e for e in events if e["event"] == "alarm_cleared")
    _write(journal, trials + [cleared])
    with pytest.raises(ct.ProjectionError, match="no open alarm_raised"):
        adapter.ops_native_rows(unit)
    _write(journal, trials + [dict(events[0], event="alarm_snoozed")])
    with pytest.raises(ct.ProjectionError, match="unknown"):
        adapter.ops_native_rows(unit)
    _write(journal, trials + [dict(events[0], actor="someone")])
    with pytest.raises(ct.ProjectionError, match="not written by"):
        adapter.ops_native_rows(unit)
    _write(journal, trials + [{k: v for k, v in events[1].items() if k != "consecutive"}])
    with pytest.raises(ct.ProjectionError, match="consecutive"):
        adapter.ops_native_rows(unit)


def test_superseded_raise_has_no_observed_end(tmp_path):
    """A restart resets the monitor, so raise, raise, clear closes only the second."""
    unit = copy_fixture(tmp_path)
    journal, trials, events = _events(unit)
    raised = [e for e in events if e["event"] == "alarm_raised"]
    cleared = next(e for e in events if e["event"] == "alarm_cleared")
    first = dict(raised[0], timestamp="2026-09-17T09:30:00+00:00")
    _write(journal, trials + [first, raised[0], cleared])
    natives = adapter.ops_native_rows(unit)
    assert [adapter.project_ops(n).value for n in natives] == [1800.0]
    assert adapter.open_alarm_intervals(unit)[0]["superseded_by"]


def test_journal_without_guard_events_projects_nothing(tmp_path):
    unit = copy_fixture(tmp_path)
    journal, trials, _ = _events(unit)
    _write(journal, trials)
    assert adapter.ops_native_rows(unit) == ()
    assert adapter.ops_native_rows(tmp_path / "empty") == ()
