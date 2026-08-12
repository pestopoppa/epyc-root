#!/usr/bin/env python3
"""M1 + M4 (daemon half) — the scheduler must tell somebody, and residency is not work.

Two mechanisms, one failure. On the night of 2026-08-11/12 the fleet ran a full
night at ~8-9% compute utilisation with a 3h47m window at zero, while every layer
reported success:

  * M1 — the daemon emitted **4,602 `would-assign` rows** between 03:00 and
    07:59Z, 100% carrying a concrete `task_id`, resolving to 12 distinct
    `(agent, task, lane)` picks, six of them repeated **756 consecutive times**.
    It knew what every main should be doing and told nobody: the rows go to
    `advisory.jsonl`, which has no reader.
  * M4 — `mi210_state()` OR-ed utilisation with VRAM residency, so a
    loaded-but-idle model read BUSY and `_eligible` rejected every queued lane
    row behind it. An idle VRAM-resident claim did not merely waste the device;
    it positively locked the queue.

WHAT THESE TESTS ARE FOR. Half of them assert that the mechanisms DO NOT FIRE:
a well-run night, an ordinary gap between two legs of a campaign, a pick that is
dispatched inside a quarter of an hour, a fleet with nothing READY. A check that
fires on a well-run night trains everyone to ignore it, and that is the failure
mode both of these mechanisms exist to avoid — not a lesser one.

Nothing here touches the live bus, the host, or any process. Every case runs
against a `tmp_path` bus and hand-built advice rows.

Run:
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest \
        scripts/coordination/tests/test_scheduling_recommendation.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import session_bus_coordinator as sbc  # noqa: E402

ADV = sbc.ADVISORY_SCHEMA
COORD = sbc.COORDINATOR_AGENT


# --------------------------------------------------------------------------- #
# Fixtures / builders
# --------------------------------------------------------------------------- #
def config(*, authority: str = "manual", with_coordinator: bool = True) -> dict:
    roster = [{"id": "mainA", "role": "main", "lanes": ["cpu", "none"]},
              {"id": "mainB", "role": "main", "lanes": ["gpu", "none"]}]
    if with_coordinator:
        roster.append({"id": COORD, "role": "coordinator-agent", "lanes": ["none"]})
    return {"roster": roster, "coordinator_daemon": {"authority": authority}}


def would_assign(agent: str, task_id: str, lane: str = "cpu", **extra) -> dict:
    row = {"schema_version": ADV, "kind": "would-assign", "agent": agent,
           "task_id": task_id, "lane": lane, "priority": "P1", "considered": 3,
           "lane_state": sbc.LANE_FREE, "admission_note": "",
           "top_rejection": {"reason": f"lane cpu not in {agent} roster lanes",
                             "count": 12, "of": 14}}
    row.update(extra)
    return row


def would_idle(agent: str) -> dict:
    return {"schema_version": ADV, "kind": "would-idle", "agent": agent,
            "task_id": None, "lane": None, "considered": 0, "rejected": []}


def would_skip(agent: str) -> dict:
    return {"schema_version": ADV, "kind": "would-skip", "agent": agent,
            "reason": "already holds a live ASSIGNED/CLAIMED/RUNNING task"}


@pytest.fixture()
def bus(tmp_path: Path) -> Path:
    root = tmp_path / "bus"
    (root / "inbox").mkdir(parents=True)
    (root / "queue.jsonl").write_text("")
    return root


def inbox(bus_root: Path, agent: str = COORD) -> list[dict]:
    path = bus_root / "inbox" / f"{agent}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def recommendations(bus_root: Path) -> list[dict]:
    return [m for m in inbox(bus_root)
            if (m.get("payload") or {}).get("event") == sbc._RECOMMEND_EVENT]


def run_ticks(bus_root: Path, advice, n: int, *, start: float = 1_000_000.0,
              period: float = 45.0, cfg: dict | None = None, **kwargs) -> list[dict]:
    """Drive n consecutive ticks. `advice` is a list or a callable of tick index."""
    emitted: list[dict] = []
    for i in range(n):
        rows = advice(i) if callable(advice) else advice
        emitted += sbc.deliver_scheduling_recommendation(
            bus_root, cfg if cfg is not None else config(), rows, epoch=1,
            now=start + i * period, **kwargs)
    return emitted


# =========================================================================== #
# M1 — THE MECHANISM FIRES, ONCE
# =========================================================================== #
def test_a_stable_pick_is_delivered_to_the_coordinator_inbox(bus):
    """THE CENTRAL ASSERTION. A pick that survives the arming window reaches a reader."""
    advice = [would_assign("mainA", "task-006-L405", "cpu")]
    run_ticks(bus, advice, sbc._RECOMMEND_MIN_TICKS)

    recs = recommendations(bus)
    assert len(recs) == 1
    payload = recs[0]["payload"]
    assert recs[0]["to"] == COORD
    assert recs[0]["kind"] == "defect"
    # Everything that makes it actionable.
    assert [p["agent"] for p in payload["picks"]] == ["mainA"]
    assert [p["task_id"] for p in payload["picks"]] == ["task-006-L405"]
    assert [p["lane"] for p in payload["picks"]] == ["cpu"]
    assert payload["picks"][0]["why_picked"]
    assert payload["picks"][0]["top_rejection"]["reason"].startswith("lane cpu not in")
    assert payload["stable_for_ticks"] == sbc._RECOMMEND_MIN_TICKS
    assert payload["authority"] == "manual"


def test_it_is_a_recommendation_and_never_an_assignment(bus):
    """THE AUTHORITY BITE. `authority: manual` reserves assignment for the operator.

    The delivered artifact must be a `defect` addressed to `coordinator-agent`, and
    NOTHING may be addressed to the picked main, of any kind — least of all a
    `task-assign`. The queue must be untouched.
    """
    before = (bus / "queue.jsonl").read_text()
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], sbc._RECOMMEND_MIN_TICKS)

    assert recommendations(bus), "precondition: the recommendation did fire"
    assert inbox(bus, "mainA") == [], "a message was addressed to the picked main"
    assert not (bus / "inbox" / "mainA.jsonl").exists()
    assert all(m.get("kind") != "task-assign" for m in inbox(bus))
    assert (bus / "queue.jsonl").read_text() == before, "the queue was mutated"


def test_authority_assign_takes_the_same_path(bus):
    """No authority branch exists, so a raised authority changes nothing HERE.

    Under `assign`, `apply_assignment` moves the row out of READY and the
    `would-assign` row stops being emitted, which is what silences this mechanism
    — structurally, not by reading a config key. Raising authority is the
    operator's separate decision and must not turn this into an assignment path.
    """
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], sbc._RECOMMEND_MIN_TICKS,
              cfg=config(authority="assign"))
    recs = recommendations(bus)
    assert len(recs) == 1
    assert recs[0]["to"] == COORD and recs[0]["kind"] == "defect"
    assert recs[0]["payload"]["authority"] == "assign"
    assert inbox(bus, "mainA") == []


SIX_PICKS = [
    would_assign("inference", "e5-006-L405", "cpu"),
    would_assign("mainA", "e5-008-L463", "cpu"),
    would_assign("mainB", "e5-010-L511", "gpu"),
    would_assign("auditor", "e5-012-L513", "none"),
    would_assign("mainC", "e5-020-L626", "none"),
    would_assign("mainD", "e5-022-L628", "none"),
]


def test_all_six_picks_travel_in_one_row(bus):
    """The six picks that repeated 756x each collapse to ONE inbox item.

    400 ticks is ~5 h at the 45 s tick, i.e. inside one re-emit window. The
    measured 756-tick run spans 9.5 h and would therefore produce two rows, not
    one — which is the intended "still unactioned six hours later" re-raise, and
    is pinned separately by the whole-night bound below.
    """
    run_ticks(bus, SIX_PICKS, 400)
    recs = recommendations(bus)
    assert len(recs) == 1, f"400 ticks produced {len(recs)} inbox rows"
    assert len(recs[0]["payload"]["picks"]) == 6


def test_a_whole_night_of_identical_picks_is_bounded(bus):
    """THE VOLUME BITE. 4,602 advisory rows -> a handful of inbox items.

    A full 24 h of the same six picks, at the real 45 s tick: 1,920 ticks. The
    re-emit interval bounds this at 24/6 = 4 raises, plus the arming one.
    """
    run_ticks(bus, SIX_PICKS, 1920)
    assert len(recommendations(bus)) <= 5


# =========================================================================== #
# M1 — THE NON-FIRING CASES (these are the point)
# =========================================================================== #
def test_a_well_run_night_is_silent(bus):
    """NON-FIRING. Every agent already holds live work; nothing is being withheld."""
    advice = [would_skip("mainA"), would_skip("mainB"), would_idle("auditor")]
    run_ticks(bus, advice, 500)
    assert recommendations(bus) == []
    assert inbox(bus) == []


def test_an_empty_ready_queue_is_silent(bus):
    """NON-FIRING. No READY work ⇒ `would-idle` only ⇒ nothing to recommend."""
    run_ticks(bus, [would_idle("mainA"), would_idle("mainB")], 500)
    assert recommendations(bus) == []


def test_a_gap_between_two_legs_of_a_campaign_does_not_alarm(bus):
    """NON-FIRING. The pick changes every few ticks — ordinary campaign churn.

    A campaign that finishes one leg and starts the next presents a DIFFERENT
    pick each time the queue turns over. The arming counter resets on every
    change, so no pick ever survives the window and nothing is said. This is the
    false-positive that would have made the whole mechanism ignorable.
    """
    run_ticks(bus, lambda i: [would_assign("mainA", f"leg-{i // 5}", "cpu")], 400)
    assert recommendations(bus) == []


def test_a_pick_dispatched_inside_the_window_never_fires(bus):
    """NON-FIRING. Picked at tick 0, dispatched by tick 18 ⇒ never armed."""
    def advice(i):
        return [would_assign("mainA", "t-1", "cpu")] if i < 18 else [would_skip("mainA")]

    run_ticks(bus, advice, 200)
    assert recommendations(bus) == []


def test_silence_up_to_the_arming_threshold(bus):
    """NON-FIRING boundary. Exactly one tick short of the threshold says nothing."""
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], sbc._RECOMMEND_MIN_TICKS - 1)
    assert recommendations(bus) == []


def test_a_would_assign_row_without_a_task_id_is_not_a_pick(bus):
    """NON-FIRING. A row with no concrete task names no work and must not fire."""
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu") | {"task_id": None}], 200)
    assert recommendations(bus) == []


# =========================================================================== #
# M1 — DEDUPLICATION (a message repeated 756 times is a second unread sink)
# =========================================================================== #
def test_a_stable_pick_is_not_repeated(bus):
    """400 ticks (~5 h, one re-emit window) of an unchanged pick say it once."""
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], 400)
    assert len(recommendations(bus)) == 1


def test_a_changed_pick_is_re_emitted(bus):
    """The pick CHANGING is news; the pick persisting is not."""
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], sbc._RECOMMEND_MIN_TICKS)
    run_ticks(bus, [would_assign("mainA", "t-2", "cpu")], sbc._RECOMMEND_MIN_TICKS,
              start=2_000_000.0)
    recs = recommendations(bus)
    assert len(recs) == 2
    assert [r["payload"]["picks"][0]["task_id"] for r in recs] == ["t-1", "t-2"]
    assert recs[0]["payload"]["pick_sig"] != recs[1]["payload"]["pick_sig"]


def test_the_same_pick_moving_to_another_agent_is_a_new_pick(bus):
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], sbc._RECOMMEND_MIN_TICKS)
    run_ticks(bus, [would_assign("mainB", "t-1", "cpu")], sbc._RECOMMEND_MIN_TICKS,
              start=2_000_000.0)
    assert len(recommendations(bus)) == 2


def test_an_unactioned_pick_is_re_raised_after_the_quiet_interval(bus):
    """Standing unactioned for a long quiet interval is itself news, once."""
    advice = [would_assign("mainA", "t-1", "cpu")]
    run_ticks(bus, advice, 100)
    assert len(recommendations(bus)) == 1
    # ...six hours later, same pick, still nobody has acted.
    run_ticks(bus, advice, 100, start=1_000_000.0 + sbc._RECOMMEND_REEMIT_S + 60.0)
    assert len(recommendations(bus)) == 2


def test_dedupe_survives_a_lost_state_file(bus):
    """Idempotency is keyed on the notice's OWN durable trace, not on daemon state.

    A daemon restart (or a deleted state file) must not re-flood an inbox that
    already carries the notice.
    """
    advice = [would_assign("mainA", "t-1", "cpu")]
    run_ticks(bus, advice, sbc._RECOMMEND_MIN_TICKS)
    assert len(recommendations(bus)) == 1

    (bus / sbc._SCHEDULING_STATE).unlink()
    # One hour later — well inside the re-emit window, so the ONLY thing that can
    # suppress the duplicate is the inbox row already sitting there.
    run_ticks(bus, advice, sbc._RECOMMEND_MIN_TICKS, start=1_003_600.0)
    assert len(recommendations(bus)) == 1, "the inbox's own contents did not dedupe"


def test_the_arming_counter_resets_when_the_pick_clears(bus):
    """19 ticks, a quiet tick, then 19 more must NOT add up to a fire."""
    def advice(i):
        if i == 19:
            return [would_idle("mainA")]
        return [would_assign("mainA", "t-1", "cpu")]

    run_ticks(bus, advice, 38)
    assert recommendations(bus) == []


# =========================================================================== #
# M1 — FAILS CLOSED, NEVER LOUDLY
# =========================================================================== #
def test_delivery_never_raises_when_the_inbox_is_unwritable(tmp_path):
    """A reporting path that can take the tick down is worse than a missed notice.

    `inbox` is a regular FILE here, so every write beneath it raises
    NotADirectoryError. (A merely-absent `inbox/` is NOT this case: `_append_jsonl`
    creates it, and the notice is delivered normally — see the test below.)
    """
    root = tmp_path / "bus"
    root.mkdir()
    (root / "inbox").write_text("not a directory")
    rows = sbc.deliver_scheduling_recommendation(
        root, config(), [would_assign("mainA", "t-1", "cpu")], epoch=1,
        now=1.0, min_ticks=1)
    assert rows == []


def test_an_absent_inbox_directory_is_created_and_delivered_to(tmp_path):
    """CONTROL for the case above: the guard must not pass by refusing everything."""
    root = tmp_path / "bus"
    root.mkdir()
    rows = sbc.deliver_scheduling_recommendation(
        root, config(), [would_assign("mainA", "t-1", "cpu")], epoch=1,
        now=1.0, min_ticks=1)
    assert len(rows) == 1
    assert len(recommendations(root)) == 1


def test_no_coordinator_in_the_roster_means_no_delivery(bus):
    """Nothing is invented: with no coordinator-agent row there is nobody to tell."""
    run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], sbc._RECOMMEND_MIN_TICKS,
              cfg=config(with_coordinator=False))
    assert inbox(bus) == []


def test_advisory_rows_are_emitted_only_on_an_actual_delivery(bus):
    emitted = run_ticks(bus, [would_assign("mainA", "t-1", "cpu")], 200)
    kinds = [r["kind"] for r in emitted]
    assert kinds == ["scheduling-recommendation-delivered"]


# =========================================================================== #
# M4 (daemon half) — RESIDENCY ADMITS, WORK REJECTS, UNKNOWN REJECTS
# =========================================================================== #
def snapshot(**over) -> dict:
    snap = {"cpu_busy": False, "gpu_busy": False, "load_class": "quiet",
            "cpu_state": sbc.LANE_FREE, "gpu_state": sbc.LANE_FREE}
    snap.update(over)
    return snap


def ready(lane: str = "gpu", **extra) -> dict:
    row = {"task_id": "t-1", "status": "READY", "lane": lane}
    row.update(extra)
    return row


def test_a_resident_lane_admits_with_a_warning():
    """THE CENTRAL ASSERTION. A loaded-but-idle device must not reject queued rows."""
    ok, why = sbc._eligible(
        ready("gpu"), {}, snapshot(gpu_state=sbc.LANE_RESIDENT), "", None)
    assert ok is True, why
    assert "RESIDENT" in why
    assert "admission is not acquisition" in why.lower()


def test_a_busy_lane_still_rejects():
    """COMPLIANT PATH: a legitimately busy device must still reject."""
    ok, why = sbc._eligible(
        ready("gpu"), {}, snapshot(gpu_busy=True, gpu_state=sbc.LANE_BUSY), "", None)
    assert ok is False
    assert "busy" in why


def test_an_unknown_lane_still_rejects():
    """FAIL CLOSED. An unreadable probe is not a free device."""
    ok, why = sbc._eligible(
        ready("gpu"), {}, snapshot(gpu_busy=True, gpu_state=sbc.LANE_UNKNOWN), "", None)
    assert ok is False


def test_a_free_lane_admits_without_a_warning():
    ok, why = sbc._eligible(ready("gpu"), {}, snapshot(), "", None)
    assert (ok, why) == (True, "eligible")


def test_exclusive_contiguous_still_refuses_a_resident_host():
    """A host holding a resident model is not a QUIET host — unchanged from pre-M4.

    Before the split a resident device classified as `busy`, so this row was
    rejected then too. The verdict is preserved exactly; only its reason is now
    accurate.
    """
    ok, why = sbc._eligible(
        ready("cpu", contention_class="exclusive-contiguous"),
        {}, snapshot(cpu_state=sbc.LANE_RESIDENT), "", None)
    assert ok is False
    assert "quiet host" in why


def test_exclusive_contiguous_still_runs_on_an_unconfirmed_host():
    """CONTROL: M4 must not TIGHTEN scheduling either. `serial_ok` still passes."""
    ok, _ = sbc._eligible(
        ready("cpu", contention_class="exclusive-contiguous"),
        {}, snapshot(load_class="serial_ok", cpu_state=sbc.LANE_UNCONFIRMED), "", None)
    assert ok is True


# --------------------------------------------------------------------------- #
# M4 — the snapshot that feeds all of the above
# --------------------------------------------------------------------------- #
@pytest.fixture()
def no_seam(monkeypatch):
    monkeypatch.delenv("SESSION_BUS_LANE_SNAPSHOT_JSON", raising=False)


def patch_sensor(monkeypatch, *, load_class: str, device_state: str):
    import scripts.coordination.inference_load_check as ic
    monkeypatch.setattr(ic, "classify_load", lambda *a, **k: {"state": load_class})
    monkeypatch.setattr(ic, "mi210_state",
                        lambda *a, **k: {"device_state": device_state,
                                         "occupied": device_state != ic.DEVICE_FREE,
                                         "detail": device_state})


def test_snapshot_resident_gpu_is_not_gpu_busy(monkeypatch, no_seam):
    patch_sensor(monkeypatch, load_class="parked", device_state="resident")
    snap = sbc._lane_snapshot()
    assert snap["gpu_state"] == sbc.LANE_RESIDENT
    assert snap["gpu_busy"] is False
    # ...and the CPU lane is no longer locked by the GPU's residency either.
    assert snap["cpu_state"] == sbc.LANE_RESIDENT
    assert snap["cpu_busy"] is False


def test_snapshot_busy_gpu_is_gpu_busy(monkeypatch, no_seam):
    """COMPLIANT PATH: work in flight still reads busy on both lanes."""
    patch_sensor(monkeypatch, load_class="busy", device_state="busy")
    snap = sbc._lane_snapshot()
    assert snap["gpu_state"] == sbc.LANE_BUSY
    assert snap["gpu_busy"] is True
    assert snap["cpu_busy"] is True


def test_snapshot_unknown_gpu_fails_closed(monkeypatch, no_seam):
    patch_sensor(monkeypatch, load_class="serial_ok", device_state="unknown")
    snap = sbc._lane_snapshot()
    assert snap["gpu_state"] == sbc.LANE_UNKNOWN
    assert snap["gpu_busy"] is True, "an unreadable rocm-smi must not read as free"


def test_snapshot_free_gpu(monkeypatch, no_seam):
    patch_sensor(monkeypatch, load_class="quiet", device_state="free")
    snap = sbc._lane_snapshot()
    assert (snap["gpu_state"], snap["gpu_busy"]) == (sbc.LANE_FREE, False)
    assert (snap["cpu_state"], snap["cpu_busy"]) == (sbc.LANE_FREE, False)


def test_the_test_seam_still_produces_a_complete_snapshot(monkeypatch):
    """The seam omits the lane states; a partial snapshot must not skip the branch."""
    monkeypatch.setenv("SESSION_BUS_LANE_SNAPSHOT_JSON",
                       json.dumps({"cpu_busy": True, "gpu_busy": False,
                                   "load_class": "busy"}))
    snap = sbc._lane_snapshot()
    assert snap["cpu_state"] == sbc.LANE_BUSY
    assert snap["gpu_state"] == sbc.LANE_FREE


# --------------------------------------------------------------------------- #
# M4 — the rejection summary that carries L6 for free
# --------------------------------------------------------------------------- #
def test_top_rejection_reports_the_modal_reason():
    rejections = ([{"task_id": f"t{i}", "reason": "lane cpu not in mainB roster lanes"}
                   for i in range(9)]
                  + [{"task_id": "x", "reason": "status=BLOCKED"}])
    top = sbc._top_rejection(rejections)
    assert top == {"reason": "lane cpu not in mainB roster lanes", "count": 9, "of": 10}


def test_top_rejection_is_none_when_nothing_was_rejected():
    assert sbc._top_rejection([]) is None
