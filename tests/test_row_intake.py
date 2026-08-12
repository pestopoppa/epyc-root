"""The two receipts a queue row must carry at BIRTH — and the honest refusal.

Subject: `scripts/coordination/row_intake.py` and its three birth sites
(`backlog_queue_gen.verdicts`, `seed_queue.cmd_seed`,
`session_bus_coordinator.intake_proposals`).

WHAT THIS IS DEFENDING. `a06780f4` made the coordinator-daemon refuse to auto-dispatch
a row without `screened_by` and a resolvable `expected_occupancy`. `9bed637f` added
both to the schema. Nothing populated them, so the live queue folded to 21 rows with
zero of either and a fail-closed gate refused all of them — a correct gate with no
producer behind it, which is an off switch nobody labelled.

The dangerous fix is the obvious one: give every row a number so the gate passes. That
re-creates F-14 (seconds-long work queued at a card that needed hours) while LOOKING
like it was fixed, and it is unfalsifiable afterwards because a fabricated 0.0 and a
measured 0.0 are the same bytes. So the property under test is not "rows have
occupancy" — it is **a row that cannot be estimated carries no occupancy key at all**,
and the mutation test below is what proves that assertion can fail.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import row_intake  # noqa: E402
from scripts.coordination.session_bus import row_occupancy_h  # noqa: E402
from scripts.coordination.session_bus_coordinator import (  # noqa: E402
    _carry_row_identity,
    dispatch_gate,
    intake_proposals,
)


# ---------------------------------------------------------------- occupancy rules


def test_a_stated_duration_becomes_occupancy_with_a_quoted_basis():
    """Rule 2. The basis must quote the row's own words, so it is auditable by eye."""
    occ = row_intake.estimate_occupancy("Re-run the E5 sweep, est 2-3h", lane="cpu", gating="cpu")
    assert occ is not None
    # A RANGE reserves its upper bound: under-reserving is the F-14 failure.
    assert occ["est_h"] == 3.0
    assert occ["basis"].startswith("stated-in-row-text:")
    assert "2-3h" in occ["basis"]
    assert occ["gating"] == "cpu"

    minutes = row_intake.estimate_occupancy("takes about 90 min", lane="gpu", gating="gpu")
    assert minutes["est_h"] == 1.5

    night = row_intake.estimate_occupancy("Leave it running overnight", lane="gpu", gating="gpu")
    assert night["est_h"] == row_intake._OVERNIGHT_H


def test_a_declared_field_beats_the_prose():
    """Rule 1. Somebody's explicit judgment about THIS task outranks a text match."""
    occ = row_intake.estimate_occupancy("a ~2h thing", lane="cpu", gating="cpu", declared_h=5.0)
    assert occ["est_h"] == 5.0
    assert "declared-field:est_wall_clock_h" in occ["basis"]


def test_lane_none_gets_a_floor_and_says_it_is_a_floor():
    """Rule 3, and the argument that makes it honest rather than a guess.

    A `lane: none` row holds no inference lane, so its number cannot mis-schedule any
    hardware — the harm `expected_occupancy` exists to prevent is unreachable for it.
    That is the ONLY place a synthesised number is defensible, and `basis` has to say
    out loud that it is a floor and not a measurement.
    """
    occ = row_intake.estimate_occupancy("Update the docstring", lane="none", gating="none")
    assert occ["est_h"] == row_intake.LANE_NONE_FLOOR_H
    assert "lane-class:none" in occ["basis"]
    assert "NOT a measurement" in occ["basis"]


@pytest.mark.parametrize("text", [
    "Run the GPU sweep and record the numbers",
    "Re-check within 24h that the guard still fires",     # a DEADLINE, not occupancy
    "The 3h window closed before anyone looked",          # HISTORY, not occupancy
    "",
])
def test_an_unestimatable_hardware_row_gets_no_occupancy_at_all(text):
    """Rule 4 — the honest refusal, on exactly the rows where a guess does harm.

    A cpu/gpu row with no stated duration is where a fabricated number DOES
    mis-schedule hardware. It gets None, the field is left off, the daemon refuses it,
    and a human dispatches it by hand. That is the intended outcome.
    """
    assert row_intake.estimate_occupancy(text, lane="gpu", gating="gpu") is None


# ------------------------------------------- the property, and its mutation test


def _assert_never_fabricates_a_zero(estimator) -> None:
    """The property, factored out so a MUTANT can be run through the same assertions.

    Two halves, and both are needed:
      * unestimatable input -> `None`, i.e. the caller emits no key;
      * anything returned at all -> a POSITIVE `est_h`, never 0.0.
    A zero would pass `dispatch_gate`'s `is None` check only to be refused by its
    `<= 0` check — but it would read to every human and every report downstream as an
    answered question, which is worse than an absent field.
    """
    unestimatable = estimator("Run the GPU sweep", lane="gpu", gating="gpu")
    assert unestimatable is None, (
        f"an unestimatable hardware row must yield None, got {unestimatable!r} — "
        f"a fabricated number here is exactly the F-14 defect")
    for text, lane, gating in [("Re-run the sweep, est 2h", "cpu", "cpu"),
                               ("Update the docstring", "none", "none")]:
        occ = estimator(text, lane=lane, gating=gating)
        assert occ is not None and occ["est_h"] > 0, (
            f"{text!r} produced {occ!r}: an occupancy that is present must be positive")


def test_the_estimator_never_fabricates_a_zero():
    _assert_never_fabricates_a_zero(row_intake.estimate_occupancy)


def test_mutation_a_fabricated_zero_is_CAUGHT_by_the_property_above():
    """MUTATION CHECK, collected by pytest — the assertion above is load-bearing.

    Without this, `test_the_estimator_never_fabricates_a_zero` could be passing for the
    wrong reason (an estimator that returns None for everything passes half of it
    vacuously). Here the exact defect the design forbids — "give every row a number so
    the gate goes green" — is INSTALLED as a mutant and the property is required to
    reject it. A mutant that slipped through would mean the guard is decoration.
    """
    def fabricates_zero(text, *, lane=None, gating=None, declared_h=None):
        real = row_intake.estimate_occupancy(text, lane=lane, gating=gating,
                                             declared_h=declared_h)
        return real if real is not None else {"est_h": 0.0, "basis": "default"}

    with pytest.raises(AssertionError, match="must yield None"):
        _assert_never_fabricates_a_zero(fabricates_zero)

    # And the second half: an estimator that answers everything with a plausible
    # non-zero constant is also caught, because the unestimatable row must be None.
    def fabricates_one_hour(text, *, lane=None, gating=None, declared_h=None):
        return {"est_h": 1.0, "basis": "guess"}

    with pytest.raises(AssertionError, match="must yield None"):
        _assert_never_fabricates_a_zero(fabricates_one_hour)


def test_the_daemon_gate_refuses_a_row_with_no_occupancy_key():
    """The whole point of refusing to fabricate: the gate then does its job."""
    screened = {"task_id": "T-1", "screened_by": "backlog_row_check.py ... verdict=DISPATCHABLE"}
    ok, code, _reason = dispatch_gate(dict(screened))
    assert not ok and code == "no-occupancy-estimate"
    assert row_occupancy_h(screened) is None

    screened["expected_occupancy"] = {"est_h": 2.0, "basis": "stated-in-row-text:'2h'"}
    ok, _code, _reason = dispatch_gate(screened)
    assert ok, "a row carrying both receipts must be dispatchable"


# ------------------------------------------------------------------ the screener


def _stub_screener(tmp_path: Path, verdict: str, exit_code: int, marker: str) -> Path:
    """A screener that prints the real verdict grammar on stdout and prose on stderr."""
    script = tmp_path / "stub_screener.py"
    script.write_text(
        "import sys\n"
        f"print('verdict={verdict} ref=x.md:1 exit={exit_code}')\n"
        f"print({marker!r}, file=sys.stderr)\n"
        f"sys.exit({exit_code})\n", encoding="utf-8")
    return script


def test_screen_parses_the_verdict_line_and_records_a_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(row_intake, "SCREENER",
                        _stub_screener(tmp_path, "DISPATCHABLE", 0, "detail"))
    result = row_intake.screen(row="anything")
    assert result.verdict == "DISPATCHABLE" and result.ready and not result.needs_reanchor
    assert "backlog_row_check.py" in result.receipt
    assert "verdict=DISPATCHABLE" in result.receipt and "exit=0" in result.receipt


@pytest.mark.parametrize("verdict", sorted(row_intake.REANCHOR_VERDICTS - {"NO_VERDICT"}))
def test_an_unresolvable_row_is_not_ready_and_is_flagged_for_re_anchoring(tmp_path, monkeypatch,
                                                                         verdict):
    monkeypatch.setattr(row_intake, "SCREENER", _stub_screener(tmp_path, verdict, 3, "detail"))
    result = row_intake.screen(row="anything")
    assert not result.ready and result.needs_reanchor


def test_a_screener_that_prints_no_verdict_line_is_a_failure_not_a_pass(tmp_path, monkeypatch):
    """"No verdict at all" must never read as "fine" — `emit_verdict` is unconditional,
    so its absence means the screener did not run or crashed."""
    script = tmp_path / "silent.py"
    script.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    monkeypatch.setattr(row_intake, "SCREENER", script)
    result = row_intake.screen(row="anything")
    assert result.verdict == "NO_VERDICT" and not result.ready and result.needs_reanchor


def test_the_screeners_stderr_is_NOT_swallowed(tmp_path, monkeypatch, capfd):
    """The 2026-08-12 defect, asserted at the file-descriptor level.

    `out=$(backlog_row_check.py --ref "$x" 2>/dev/null)` turns a rotted anchor into an
    empty string and a discarded exit code — indistinguishable from a clean pass, while
    anchor rot runs at 34.5% queue-wide. `row_intake.screen` must therefore INHERIT
    stderr, never capture or redirect it. `capfd` reads the real fd, so this cannot
    pass on a Python-level fake.
    """
    marker = "SCREENER-PROSE-MUST-REACH-STDERR"
    monkeypatch.setattr(row_intake, "SCREENER",
                        _stub_screener(tmp_path, "ANCHOR_ROT", 3, marker))
    row_intake.screen(ref="x.md:1")
    captured = capfd.readouterr()
    assert marker in captured.err, "the screener's stderr was swallowed"
    # The verdict line is a return value, so it is captured and must NOT leak to the
    # caller's stdout — otherwise a generator's output would be corrupted by it.
    assert "verdict=" not in captured.out


def test_mutation_capturing_stderr_makes_the_check_above_fail(tmp_path, monkeypatch, capfd):
    """MUTATION CHECK, collected by pytest. Install the swallowing idiom and prove the
    assertion notices. Without this, the test above would pass on any implementation
    whatsoever — including one that never runs the screener at all."""
    marker = "SWALLOWED-PROSE"
    monkeypatch.setattr(row_intake, "SCREENER",
                        _stub_screener(tmp_path, "ANCHOR_ROT", 3, marker))
    real_run = subprocess.run

    def swallowing_run(argv, **kwargs):
        kwargs["stderr"] = subprocess.DEVNULL          # the exact defect
        return real_run(argv, **kwargs)

    monkeypatch.setattr(row_intake.subprocess, "run", swallowing_run)
    row_intake.screen(ref="x.md:1")
    assert marker not in capfd.readouterr().err, (
        "the mutant did not change observable behaviour, so the stderr assertion "
        "proves nothing")


def test_the_in_repo_screen_path_contains_no_stderr_suppression():
    """A source-level tripwire against the idiom coming back by copy-paste."""
    src = (REPO_ROOT / "scripts" / "coordination" / "row_intake.py").read_text(encoding="utf-8")
    body = src.split("def screen(", 1)[1].split("\ndef ", 1)[0]
    code = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    code = code.split('"""', 2)[-1]                       # drop the docstring's prose
    for banned in ("stderr=subprocess", "stderr=None", "capture_output"):
        assert banned not in code, f"row_intake.screen must never write {banned}"


# ------------------------------------------------------- intake: the birth site


def _propose(task_id: str, **payload) -> dict:
    return {task_id: [{"kind": "task-propose", "from": "seeder", "task_id": task_id,
                       "payload": payload}]}


def test_a_row_that_fails_its_screen_is_not_admitted_READY(tmp_path, monkeypatch):
    """It becomes INFRA_BLOCKED — visible and re-anchorable — never READY, never dropped.

    INFRA_BLOCKED is the queue's EXISTING word for "not re-assignable without a human"
    (`session_bus.schema.json#queue_row`). Nothing new was invented for this state.
    """
    monkeypatch.setattr(row_intake, "SCREENER",
                        _stub_screener(tmp_path, "ANCHOR_ROT", 3, "rotted"))
    rows, advisory = intake_proposals(tmp_path, {}, _propose(
        "T-rot", lane="none", gating="none", summary="Do a thing"), epoch=1)
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == row_intake.NEEDS_REANCHOR_STATUS == "INFRA_BLOCKED"
    assert row["status"] != "READY"
    assert "ANCHOR_ROT" in row["failure_reason"]
    assert "Re-anchor" in row["failure_reason"]
    assert row["screened_by"], "the receipt is recorded even on a refusal"
    assert any("ANCHOR_ROT" in (a.get("detail") or "") for a in advisory), \
        "a refusal must be visible in the advisory record, not an absence"


def test_a_clean_screen_admits_a_READY_row_carrying_both_receipts(tmp_path, monkeypatch):
    monkeypatch.setattr(row_intake, "SCREENER",
                        _stub_screener(tmp_path, "DISPATCHABLE", 0, "fine"))
    rows, _adv = intake_proposals(tmp_path, {}, _propose(
        "T-ok", lane="none", gating="none", summary="Update a docstring"), epoch=1)
    row = rows[0]
    assert row["status"] == "READY"
    assert row["screened_by"] and row["expected_occupancy"]["est_h"] > 0
    ok, _code, _reason = dispatch_gate(row)
    assert ok, "an admitted READY row must pass the daemon's own gate"


def test_an_unestimatable_admitted_row_carries_NO_occupancy_key(tmp_path, monkeypatch):
    """The honest half, at the birth site: no key, not a zero, and the daemon refuses it.

    This row is a HAND-DISPATCH row by construction, and the queue says so by omission
    rather than by a number nobody can defend.
    """
    monkeypatch.setattr(row_intake, "SCREENER",
                        _stub_screener(tmp_path, "DISPATCHABLE", 0, "fine"))
    rows, advisory = intake_proposals(tmp_path, {}, _propose(
        "T-gpu", lane="gpu", gating="gpu", summary="Run the sweep"), epoch=1)
    row = rows[0]
    assert row["status"] == "READY"
    assert "expected_occupancy" not in row, f"expected no key, got {row.get('expected_occupancy')!r}"
    assert row.get("est_wall_clock_h") is None
    ok, code, _reason = dispatch_gate(row)
    assert not ok and code == "no-occupancy-estimate"
    assert any("hand-dispatch-only" in (a.get("detail") or "") for a in advisory)


def test_a_proposer_supplied_receipt_is_not_re_screened(tmp_path, monkeypatch):
    """Intake COMPLETES missing receipts; it does not overwrite somebody else's."""
    def explode(**_kwargs):  # pragma: no cover — must never be called
        raise AssertionError("intake re-screened a row that already had a receipt")

    monkeypatch.setattr(row_intake, "screen", explode)
    rows, _adv = intake_proposals(tmp_path, {}, _propose(
        "T-pre", lane="cpu", gating="cpu", summary="A sweep",
        screened_by="backlog_row_check.py --row 'A sweep' @... verdict=DISPATCHABLE exit=0",
        expected_occupancy={"est_h": 4.0, "basis": "measured on 2026-08-01"}), epoch=1)
    assert rows[0]["expected_occupancy"]["est_h"] == 4.0
    assert "measured" in rows[0]["expected_occupancy"]["basis"]


# --------------------------------------- the receipts must SURVIVE a status change


def test_the_receipts_ride_every_rewrite_of_a_row():
    """Otherwise populating them at intake is VACUOUS.

    `fold_queue` is last-write-wins over WHOLE rows and eight sites rebuild a row field
    by field. C50b fixed that for `spec_ref` alone; `screened_by` and
    `expected_occupancy` were added later and were dropped by every one of them. A row
    would then be born screened and estimated, get assigned once, fold back to READY on
    a stale-requeue carrying neither, and be refused for ever — the same inert loop, one
    status change later.
    """
    born = {"task_id": "T", "status": "READY", "spec_ref": "h.md#L3",
            "task_text": "the identity", "screened_by": "receipt",
            "expected_occupancy": {"est_h": 2.0, "basis": "stated"},
            "est_wall_clock_h": 2.0, "owner": None, "attempt": 0}
    carried = _carry_row_identity(born)
    for field in ("spec_ref", "task_text", "screened_by", "expected_occupancy",
                  "est_wall_clock_h"):
        assert field in carried, f"{field} is dropped on rewrite — the fold destroys it"

    requeued = {"task_id": "T", "status": "STALE_REQUEUED", **carried}
    ok, _code, _reason = dispatch_gate({**requeued, "status": "READY"})
    assert ok, "a requeued row must still carry the receipts that let it be dispatched"

    # State, as opposed to identity, is correctly NOT carried.
    assert "status" not in carried and "owner" not in carried and "attempt" not in carried
    assert _carry_row_identity({}) == {} and _carry_row_identity(None) == {}


def test_seed_queue_puts_both_receipts_on_the_proposal(tmp_path, monkeypatch, capsys):
    """End to end at the other birth site: what seed_queue writes must pass the gate."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "seed_queue", REPO_ROOT / "scripts" / "coordination" / "seed_queue.py")
    seed_queue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_queue)

    handoff = tmp_path / "handoffs" / "active" / "fake.md"
    handoff.parent.mkdir(parents=True)
    handoff.write_text("# H\n\n- [ ] Update the module docstring so the schema is documented\n",
                       encoding="utf-8")
    outbox = tmp_path / "bus" / "outbox"
    outbox.mkdir(parents=True)
    monkeypatch.setattr(seed_queue, "HANDOFFS", handoff.parent)
    monkeypatch.setattr(seed_queue, "BUS_ROOT", tmp_path / "bus")
    monkeypatch.setattr(seed_queue.row_intake, "SCREENER",
                        _stub_screener(tmp_path, "DISPATCHABLE", 0, "fine"))

    args = seed_queue.build_parser().parse_args(
        ["--handoff", "fake.md", "--agent", "tester", "--priority", "P2"])
    assert seed_queue.cmd_seed(args) == 0

    lines = [json.loads(l) for l in (outbox / "tester.jsonl").read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    payload = lines[0]["payload"]
    assert payload["screened_by"] and payload["task_text"]
    assert payload["expected_occupancy"]["est_h"] == row_intake.LANE_NONE_FLOOR_H

    # And the row that intake builds from it passes the daemon's gate — the loop is
    # no longer inert.
    rows, _adv = intake_proposals(tmp_path, {}, _propose("T-e2e", **payload), epoch=1)
    ok, _code, reason = dispatch_gate(rows[0])
    assert ok, reason


def test_seed_queue_does_not_propose_a_row_the_screener_refused(tmp_path, monkeypatch, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "seed_queue2", REPO_ROOT / "scripts" / "coordination" / "seed_queue.py")
    seed_queue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_queue)

    handoff = tmp_path / "handoffs" / "active" / "fake.md"
    handoff.parent.mkdir(parents=True)
    handoff.write_text("# H\n\n- [ ] Update the module docstring so the schema is documented\n",
                       encoding="utf-8")
    (tmp_path / "bus" / "outbox").mkdir(parents=True)
    monkeypatch.setattr(seed_queue, "HANDOFFS", handoff.parent)
    monkeypatch.setattr(seed_queue, "BUS_ROOT", tmp_path / "bus")
    monkeypatch.setattr(seed_queue.row_intake, "SCREENER",
                        _stub_screener(tmp_path, "UNRESOLVABLE", 3, "gone"))

    args = seed_queue.build_parser().parse_args(["--handoff", "fake.md", "--agent", "tester"])
    assert seed_queue.cmd_seed(args) == 0
    assert not (tmp_path / "bus" / "outbox" / "tester.jsonl").exists()
    out = capsys.readouterr().out
    assert "UNRESOLVABLE" in out and "needs re-anchoring" in out
