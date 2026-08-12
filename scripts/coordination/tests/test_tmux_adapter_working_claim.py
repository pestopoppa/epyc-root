#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""C52 — a `state: working` heartbeat must be CORROBORATED before it refuses a nudge.

    python -m pytest scripts/coordination/tests/test_tmux_adapter_working_claim.py

THE INCIDENT THIS PINS, 2026-08-12. `mainB` finished a GPU sweep and settled at an
empty composer. Its heartbeat still read `state: working, task_id:
gpu-continuous-occupancy-A3-sweep-pid-4133649`; pid 4133649 was already dead. Every
nudge refused on `heartbeat says working`. Six retries over two minutes, all refused;
the MI210 read 0% for thirteen minutes because work could not be delivered to the main
holding the grant. Nobody else could clear the flag either — single-writer discipline
means only mainB may write mainB's heartbeat, and it could not, because being told to
is what the guard refused.

C35's quiescence override could not rescue it, and the reason is the whole test file.
There is a BAND — quieter than `--quiet-s` (20s) and not yet quiet enough for the 120s
override — in which a settled main passes every guard except the one it cannot clear;
the refusal messages place the incident squarely in it. The band is wider in practice
than the C35 calibration assumed, too: a main with fanned-out subagents renders a live
elapsed-time row per subagent that ticks once a second whether or not the main's own
thread is doing anything (observed directly on live panes sitting at empty composers),
so for such a main `quiet_for` may never rise at all. The quiet-check cannot answer "is
it working"; only a signal that could have contradicted the claim can.

Three verdicts, and the third is not a polite spelling of the other two: corroborated
(refuse), contradicted (deliver), undetermined (refuse, and SAY so). Every case below
is one of those, plus the mutation that shows the deadlock returns without the fix.

The basename is unique on purpose — see the C10 note in the sibling suites.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "scripts" / "coordination" / "tmux_adapter.py"
SESSION = f"tmuxwc-test-{os.getpid()}"

# The real heartbeat from the incident. The pid lives inside the task_id, which is the
# convention the fleet actually writes — not a field the schema declares.
INCIDENT_TASK_ID = "gpu-continuous-occupancy-A3-sweep-pid-4133649"
# A pid that cannot be running: above the kernel's maximum, so it can never be
# allocated and the case can never flake into "alive" on a busy host.
IMPOSSIBLE_PID = 4194305

CONFIG = {
    "flags": {"codex_sendkeys": "on"},
    "roster": [{"id": "mainB", "endpoint": "tmux:agent:mainB"}],
    "tmux": {"live_session": "agent", "allow_session_creation": False},
    "caps": {"max_concurrent_mains": 6},
}


def _load(tag: str, bus_root: Path):
    spec = importlib.util.spec_from_file_location(f"ta_wc_{tag}_{os.getpid()}", MODULE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.BUS_ROOT = bus_root
    m.LEDGER = bus_root / "adapter-ledger.jsonl"
    (bus_root / "heartbeats").mkdir(parents=True, exist_ok=True)
    return m


def _probe(tag: str, tmp_path: Path, *, task_id: str = INCIDENT_TASK_ID,
           state: str = "working", quiet_for: float = 30.0, pane_busy=(False, "no marker"),
           runtime=(None, "no runtime signal"), dead: str = "0", attached: str = "1"):
    """Probe one synthetic pane with every C52 input dialled in independently.

    `quiet_for` defaults to THIRTY SECONDS, which is the incident's refusal signature:
    the refusals named the heartbeat state, so the window had been quiet longer than
    `--quiet-s` (20s) — otherwise the quiet-check would have refused first and said so
    — and shorter than C35's override threshold (120s), or the override would have
    fired. That band is the deadlock's whole habitat, and every delivering case here
    sits in it, so it delivers on evidence C35 does not have.
    """
    m = _load(tag, tmp_path / tag)
    hb = m.BUS_ROOT / "heartbeats" / "mainB.json"
    hb.write_text(json.dumps({"agent": "mainB", "state": state, "task_id": task_id,
                              "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}),
                  encoding="utf-8")
    act = str(int(time.time() - quiet_for))

    def fake_tmux(*args):
        if args[0] == "display-message":
            fmt = args[-1]
            if "#{window_index}" in fmt:
                return 0, "3\tmainB"
            return 0, f"{dead}\t{act}\t{attached}"
        if args[0] == "list-windows":
            return 0, "3\tmainB"
        return 0, ""

    m._tmux = fake_tmux
    return m, m.probe(CONFIG, "mainB", 20.0, 900.0, 120.0,
                      runtime_fn=lambda cfg, a: runtime,
                      pane_busy_fn=lambda t: pane_busy)


def _working_blocker(p: dict) -> str | None:
    return next((b for b in p["blockers"] if b.startswith("heartbeat says working")), None)


# ============================================================ the incident, reconstructed


def test_stale_working_claim_with_a_dead_task_pid_is_contradicted_and_delivers(tmp_path):
    """(a) THE DEADLOCK, and the exact inputs that produced it.

    Heartbeat says working, its own published pid is gone, the pane shows no
    generation marker, and the window sits in the deadlock band (quiet for 30s: past
    the quiet-check, short of the C35 override). Pre-C52 that combination refused
    forever. It must now DELIVER.
    """
    m, p = _probe("incident", tmp_path)
    assert p["working_claim"] == "contradicted", p["heartbeat_override_reason"]
    assert p["task_pid"] == 4133649 and p["task_pid_alive"] is False
    assert _working_blocker(p) is None, p["blockers"]
    assert p["nudge_ok"] is True, p["blockers"]
    assert "4133649" in p["heartbeat_override_reason"]


def test_the_deadlock_band_is_between_the_quiet_check_and_the_c35_threshold(tmp_path):
    """The habitat, pinned so the next reader does not have to re-derive it. Below 20s
    the quiet-check refuses UNLESS H-3 corroborates (see below). At or above 120s C35
    already overrode. In between, pre-C52, a settled main was nudgeable by every guard
    except the one it could not clear.

    H-3 (2026-08-12) NARROWED THE LOWER EDGE. `window_activity` moves on cosmetic
    redraw, so a main with fanned-out subagents sits below 20s forever and the
    quiet-check was UNREACHABLE-PASS for it. The blocker is now downgraded when the
    TUI's own state line reads NOT-busy across 3 consecutive samples. The lower edge
    still refuses whenever that reading is unavailable, which is what this pins."""
    m, low = _probe("band_low", tmp_path, quiet_for=5.0,
                    pane_busy=(None, "capture-pane failed — nothing can corroborate"))
    assert any("likely mid-generation" in b for b in low["blockers"])
    # H-3's own edge, asserted here so the two are never separated: same 5s window,
    # but a readable and stable NOT-busy marker downgrades the blocker.
    m, low_corroborated = _probe("band_low_corr", tmp_path, quiet_for=5.0,
                                 pane_busy=(False, "no generation marker"))
    assert not any("likely mid-generation" in b for b in low_corroborated["blockers"])
    assert low_corroborated["quiet_corroborated_idle"] is True
    m, high = _probe("band_high", tmp_path, quiet_for=300.0, task_id="deep-queue")
    assert high["working_claim"] == "contradicted"      # C35 alone already handled this
    # And the band is where C52 does its work: no pid to check, but the pane says
    # settled twice over, so the claim is contradicted instead of wedging the main.
    m, mid = _probe("band_mid", tmp_path, quiet_for=30.0, task_id="deep-queue")
    assert mid["working_claim"] == "contradicted"
    assert mid["nudge_ok"] is True, mid["blockers"]


def test_the_quiescence_override_alone_could_not_have_rescued_the_incident(tmp_path):
    """Why C35 was not enough, asserted rather than argued: everywhere in the deadlock
    band the C35 predicate says NO, so the delivery above rests entirely on evidence
    C35 does not consult."""
    m, _ = _probe("c35gap", tmp_path)
    for quiet in (1.0, 21.0, 30.0, 119.0):
        assert m.hb_stale_override_ok(False, quiet, 120.0) is False, quiet
    assert m.hb_stale_override_ok(False, 121.0, 120.0) is True


# ============================================================ corroboration still refuses


def test_a_generating_pane_corroborates_and_the_nudge_is_still_refused(tmp_path):
    """(b) NO REGRESSION. A genuinely working main renders `esc to interrupt`; typing
    a brief into it corrupts a live generation, so it must still refuse."""
    m, p = _probe("busy", tmp_path, pane_busy=(True, "pane agent:mainB shows 'esc to interrupt'"),
                  task_id="whatever-pid-%d" % IMPOSSIBLE_PID)
    assert p["working_claim"] == "corroborated"
    assert _working_blocker(p) is not None
    assert p["nudge_ok"] is False


def test_a_compacting_session_is_corroborated_and_refused(tmp_path):
    """(c) COMPACTING IS NOT IDLE. A session compacting its context renders like an
    idle one, so it is recognised POSITIVELY — never inferred from the absence of
    business — and the nudge is refused. Both routes are asserted: the runtime rollout
    record (Codex) and the pane marker (Claude, which has no runtime signal)."""
    _, by_runtime = _probe("compact_rt", tmp_path,
                           runtime=("active", "rollout ends in 'token_count'"))
    # The runtime is authoritative and refuses ABOVE the heartbeat branch entirely, so
    # the working claim is never reached — asserted as the blocker it actually adds,
    # not as a verdict this path does not compute.
    assert any("runtime says ACTIVE" in b for b in by_runtime["blockers"]), by_runtime["blockers"]
    assert by_runtime["nudge_ok"] is False

    _, by_pane = _probe("compact_pane", tmp_path,
                        pane_busy=(True, "pane agent:mainB shows 'compacting'"))
    assert by_pane["working_claim"] == "corroborated"
    assert by_pane["nudge_ok"] is False


def test_a_live_task_pid_corroborates_even_when_the_pane_looks_idle(tmp_path):
    """Corroboration OUTRANKS contradiction. The agent's own pid is running, so the
    claim stands however quiet the pane looks — a false refusal costs a retry, typing
    into live work does not."""
    m, p = _probe("livepid", tmp_path, task_id=f"long-cpu-bench-pid-{os.getpid()}",
                  quiet_for=9999.0)
    assert p["task_pid"] == os.getpid() and p["task_pid_alive"] is True
    assert p["working_claim"] == "corroborated"
    assert p["nudge_ok"] is False


def test_a_pid_less_main_settled_at_its_prompt_is_contradicted_by_the_pane(tmp_path):
    """THE OPERATOR'S OWN FIX — "why not just look at its pane" — and the case a pid
    cannot cover, which is most of the fleet: the live heartbeats declare no pid at
    all. No generation or compaction marker AND quiet past `--quiet-s` are two
    independent readings that the main is settled, so the claim is contradicted and
    the nudge is delivered."""
    m, p = _probe("panecontra", tmp_path, task_id="deep-queue", quiet_for=30.0)
    assert p["working_claim"] == "contradicted", p["heartbeat_override_reason"]
    assert "two independent readings" in p["heartbeat_override_reason"]
    assert _working_blocker(p) is None
    assert p["nudge_ok"] is True, p["blockers"]


def test_the_quiet_check_bar_moves_only_on_a_stable_pane_reading(tmp_path):
    """SUPERSEDES `test_the_pane_contradiction_never_lowers_the_quiet_check_bar`
    (C52, 2026-08-12) — renamed rather than deleted so the reversal is visible.

    C52 asserted that the pane marker may never lower the quiet-check bar. H-3
    reversed that DELIBERATELY, on measurement: `window_activity` moves on cosmetic
    subagent redraw, so for a main that fans out the quiet-check could not be
    satisfied at all, at any threshold. What replaced the invariant is not "the bar
    is lower" but "a signal that cannot answer the question may be overruled by one
    that can, if that one PERSISTS" — so the thing to pin now is the persistence
    requirement, and that an unreadable or flapping pane still refuses."""
    m, p = _probe("panebar", tmp_path, task_id="deep-queue", quiet_for=5.0,
                  pane_busy=(None, "capture-pane failed"))
    assert p["working_claim"] == "undetermined"
    assert any("likely mid-generation" in b for b in p["blockers"])
    assert p["nudge_ok"] is False
    # And a pane that is positively BUSY refuses on both counts, unchanged: typing
    # into a live generation corrupts it, and no corroboration path may reach it.
    m, busy = _probe("panebar_busy", tmp_path, task_id="deep-queue", quiet_for=5.0,
                     pane_busy=(True, "pane shows 'esc to interrupt'"))
    assert any("likely mid-generation" in b for b in busy["blockers"])
    assert busy["quiet_corroborated_idle"] is False
    assert busy["nudge_ok"] is False


def test_an_unreadable_marker_cannot_produce_the_pane_contradiction(tmp_path):
    """`None` is not `False`. A capture that failed says nothing about the agent."""
    m, p = _probe("panenone", tmp_path, task_id="deep-queue", quiet_for=30.0,
                  pane_busy=(None, "capture-pane failed"))
    assert p["working_claim"] == "undetermined"
    assert p["nudge_ok"] is False


# ============================================================ undetermined is its own answer


def test_no_signal_either_way_is_undetermined_refuses_and_says_so(tmp_path):
    """FAIL LOUD ON 'CANNOT DETERMINE'. No pid in the task_id, no runtime answer, no
    pane marker, a recently-redrawn window: nothing corroborates and nothing
    contradicts. It must refuse — and it must not report that as the heartbeat having
    been believed, which is the phrasing that hid this defect."""
    m, p = _probe("unknown", tmp_path, task_id="deep-queue",
                  pane_busy=(None, "capture-pane on agent:mainB failed"))
    assert p["working_claim"] == "undetermined"
    assert p["task_pid"] is None
    assert p["nudge_ok"] is False
    reason = p["heartbeat_override_reason"]
    assert "UNDETERMINED" in _working_blocker(p)
    assert "not because the heartbeat was believed" in reason


# ============================================================ the guards that must not move


def test_an_idle_heartbeat_is_unaffected_and_the_claim_is_not_evaluated(tmp_path):
    m, p = _probe("idlehb", tmp_path, state="idle", quiet_for=300.0)
    assert p["working_claim"] == "n/a"
    assert _working_blocker(p) is None
    assert p["nudge_ok"] is True


def test_the_20s_quiet_check_still_refuses_a_pane_that_may_be_generating(tmp_path):
    """NOT WEAKENED — narrowed, and only where a BETTER signal exists. A window that
    produced output 1s ago is still refused whenever the TUI's own state line cannot
    say it is idle: unreadable (here) or positively busy (above). H-3 downgrades the
    blocker ONLY on a not-busy reading that held across 3 consecutive samples, which
    is the case a redrawing-but-settled main is in and a generating one never is."""
    m, p = _probe("quietcheck", tmp_path, quiet_for=1.0, attached="1",
                  pane_busy=(None, "capture-pane failed"))
    # `contradicted` via the heartbeat's own dead task pid — the working blocker is
    # gone and the QUIET-CHECK is the one still refusing, which is the point.
    assert p["working_claim"] == "contradicted"
    assert any("likely mid-generation" in b for b in p["blockers"]), p["blockers"]
    assert p["nudge_ok"] is False


def test_a_dead_pane_still_refuses_whatever_the_claim_says(tmp_path):
    m, p = _probe("deadpane", tmp_path, dead="1", quiet_for=300.0)
    assert any("pane is dead" in b for b in p["blockers"])
    assert p["nudge_ok"] is False


# ============================================================ the pid reader


@pytest.mark.parametrize(("hb", "expected"), [
    ({"task_id": INCIDENT_TASK_ID}, 4133649),
    ({"task_id": "sweep-pid-4133649"}, 4133649),
    ({"task_id": "sweep_pid_991"}, 991),
    ({"pid": 1234, "task_id": "no-pid-here-at-all"}, 1234),
    ({"task_pid": "77", "task_id": "x"}, 77),
    ({"task_id": "deep-queue"}, None),
    ({"task_id": "A4-superseded-e9566988-context-exhausted"}, None),
    (None, None),
])
def test_task_pid_is_read_from_the_field_or_the_task_id_convention(hb, expected, tmp_path):
    m = _load("pidread", tmp_path / "pidread")
    pid, why = m.heartbeat_task_pid(hb)
    assert pid == expected, why


def test_pid_alive_is_true_for_this_process_and_false_for_an_impossible_one(tmp_path):
    m = _load("pidalive", tmp_path / "pidalive")
    assert m.pid_alive(os.getpid()) is True
    assert m.pid_alive(IMPOSSIBLE_PID) is False


# ============================================================ the mutation


def test_mutation_without_corroboration_the_incident_deadlocks_again(tmp_path):
    """MUTATION, visible and counted. Replace the corroboration ladder with the
    pre-C52 rule — quiescence is the only thing that may overrule a `working` claim —
    and the incident's exact inputs refuse again, forever.

    This is the whole fix expressed as a difference: same heartbeat, same dead pid,
    same idle pane, opposite outcome.
    """
    m = _load("mutant", tmp_path / "mutant")
    hb = m.BUS_ROOT / "heartbeats" / "mainB.json"
    hb.write_text(json.dumps({"agent": "mainB", "state": "working",
                              "task_id": INCIDENT_TASK_ID,
                              "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}),
                  encoding="utf-8")
    act = str(int(time.time() - 1.0))
    m._tmux = lambda *a: (0, "3\tmainB") if a[0] == "list-windows" or "#{window_index}" in a[-1] \
        else (0, f"0\t{act}\t0")

    def pre_c52(*, pane_dead, quiet_for, override_quiet_s, **_ignored):
        if m.hb_stale_override_ok(pane_dead, quiet_for, override_quiet_s):
            return "contradicted", "window quiet"
        return "corroborated", "window was active recently — heartbeat believed"

    m.corroborate_working_claim = pre_c52
    p = m.probe(CONFIG, "mainB", 20.0, 900.0, 120.0,
                runtime_fn=lambda cfg, a: (None, "no runtime signal"),
                pane_busy_fn=lambda t: (False, "no marker"))
    assert _working_blocker(p) is not None, "the mutation must reproduce the deadlock"
    assert p["nudge_ok"] is False


# ============================================================ live: the pane marker itself


@pytest.fixture
def live_session():
    if subprocess.run(["tmux", "-V"], capture_output=True).returncode != 0:
        pytest.skip("no tmux reachable")
    subprocess.run(["tmux", "new-session", "-d", "-s", SESSION, "-n", "holder", "sleep", "600"],
                   capture_output=True, timeout=15)
    try:
        yield SESSION
    finally:
        subprocess.run(["tmux", "kill-session", "-t", SESSION], capture_output=True, timeout=15)


@pytest.mark.parametrize(("painted", "busy"), [
    ("Working (6m 01s - esc to interrupt) - 2 background terminals running", True),
    ("Compacting conversation...", True),
    ("auto mode on (shift+tab to cycle) - 1 agent", False),
])
def test_live_pane_marker_reads_a_real_pane(live_session, painted, busy, tmp_path):
    """The marker is read off a REAL pane, because "does capture-pane see this text"
    is the only part of the predicate a string fixture cannot answer."""
    m = _load("livemarker" + str(busy) + str(len(painted)), tmp_path / f"lm{len(painted)}")
    win = f"w{abs(hash(painted)) % 9999}"
    subprocess.run(["tmux", "new-window", "-d", "-t", live_session, "-n", win,
                    "sh", "-c", f"printf '%s\\n' '{painted}'; sleep 60"],
                   capture_output=True, timeout=15)
    time.sleep(0.5)
    got, why = m.pane_busy_marker(f"{live_session}:{win}")
    assert got is busy, why


def test_live_unreadable_target_is_none_not_false(live_session, tmp_path):
    """A pane that cannot be read must return None. `False` would be a positive claim
    that the agent is idle, drawn from a failed query — the fail-open shape."""
    m = _load("livemissing", tmp_path / "livemissing")
    got, why = m.pane_busy_marker(f"{live_session}-does-not-exist:0")
    assert got is None, why
