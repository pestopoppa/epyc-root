"""RTG-48 A-1 — audit of the `Mech` column in
`handoffs/active/coordinator-role-failure-modes-and-refactor.md`.

For every F-row whose `Mech` cell is `MECH` or `MECH-UC`, this file pins the
mechanism as it exists TODAY and mutation-tests the claim's load-bearing
direction: **a `MECH` claim is only true if the mechanism would have REFUSED
the specific failure** — not if it merely covers the topic.

Per-row verdicts (full analysis: docs/reviews/rtg48-mech-column-audit-2026-08-23.md):

  F-03  MECH(existed-unused)  SURVIVES — anchored `_OPEN_BOX`, consumed by index_state
  F-04  MECH                 SURVIVES (code form) — `summarize_advisory_shard` N/M/K
  F-08  MECH                 SURVIVES — per-agent nudge filter at tmux_adapter.py:1950
  F-15  MECH                 DOWNGRADED to RECALL — 2f787163 is policy prose, no mechanism
  F-22  MECH(existed-unused) SURVIVES (now wired) — dispatch_gate + typed task_text
  F-27  MECH(class-cover)    DOWNGRADED to RECALL — rule covers the class, nothing refuses
  F-07  MECH-UC              SUPERSEDED then LANDED — fleet_watch pane heuristics deleted (P3-3)
  F-10  MECH-UC              LANDED — C51 b6ea8679 + C55 2076e359 wake-char submit
  F-11  MECH-UC              LANDED — fleet_watch committed, detect-only (R-16 ruling)
  F-13  MECH-UC              LANDED — fleet_watch committed + adapter `pending` detector
  F-24  MECH-UC              LANDED as SUPERSEDED — H-4 SHA deploy-marker (bc6dc77f)
  F-35  MECH-UC              LANDED — C51/C55/H-1/H-2 all committed

Mutation style: the closures under test are not patchable in place, so each
mutation is shown as (a) the REAL code path refusing the failure, then (b) the
same inputs through the exact production arithmetic with the one load-bearing
clause deleted — the failure recurs. Both directions are asserted.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import time as _time
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_BRC_SPEC = importlib.util.spec_from_file_location(
    "brc", REPO_ROOT / "scripts" / "coordination" / "backlog_row_check.py")
brc = importlib.util.module_from_spec(_BRC_SPEC)
assert _BRC_SPEC.loader is not None
_BRC_SPEC.loader.exec_module(brc)

_INDEX_SPEC = importlib.util.spec_from_file_location(
    "index_state", REPO_ROOT / "scripts" / "handoffs" / "index_state.py")
index_state = importlib.util.module_from_spec(_INDEX_SPEC)
assert _INDEX_SPEC.loader is not None
_INDEX_SPEC.loader.exec_module(index_state)


def _load_adapter(tag: str):
    spec = importlib.util.spec_from_file_location(
        f"tmux_adapter_audit_{tag}",
        REPO_ROOT / "scripts" / "coordination" / "tmux_adapter.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_sbc():
    import sys
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.coordination import session_bus_coordinator as sbc
    return sbc


def _iso_ago(seconds: float) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(timespec="seconds")


# ============================================================================
# F-03 — MECH (existed, unused): the anchored canonical counter
# ============================================================================

def test_f03_open_box_regex_is_anchored_to_line_start():
    r"""The F-03 claim names `backlog_row_check.py:184` `_OPEN_BOX = ^\s*- \[ \] `.
    The failure it refuses: an UNANCHORED `- [ ]` matching anywhere in a line."""
    assert brc._OPEN_BOX.pattern == r"^\s*- \[ \] ", brc._OPEN_BOX.pattern
    assert brc._OPEN_BOX.pattern.startswith("^")


def test_f03_mutation_unanchored_matching_counts_a_midline_box():
    """Mutation: revert to unanchored matching. A checkbox mid-line is then counted
    as an open row — the wrong-counts-all-night failure recurs. Restore: refused."""
    midline = "the sentence continues - [ ] and this is not a backlog row"
    unanchored = re.compile(r"- \[ \] ")          # the mutation
    assert unanchored.search(midline) is not None, "mutation: mid-line box is counted"
    assert brc._OPEN_BOX.match(midline) is None, "anchored regex refuses the mid-line box"


def test_f03_boxes_counter_counts_line_start_but_not_midline(tmp_path: Path):
    handoff = tmp_path / "f03-demo.md"
    handoff.write_text(
        "# Demo\n\n"
        "- [ ] a real backlog row\n"
        "prose with - [ ] a mid-line fake box\n"
        "    - [x] an indented closed child\n",
        encoding="utf-8")
    boxes = brc._boxes(handoff)
    bodies = [b for _n, _st, b, _h in boxes]
    assert bodies == ["a real backlog row", "an indented closed child"], bodies
    assert "a mid-line fake box" not in bodies


def test_f03_index_state_consumes_the_anchored_parser():
    """The handoff cites `index_state.py:126` consuming the anchored counter. Today
    `index_state.scan_handoff` iterates `brc._boxes` (index_state.py:270) — the SAME
    parser object, so a hand-rolled unanchored grep is still not what the index uses."""
    assert index_state.brc._boxes.__code__ == brc._boxes.__code__
    assert index_state.scan_handoff.__doc__ and "Box counts" in index_state.scan_handoff.__doc__


# ============================================================================
# F-04 — MECH: Reporting Units (a90870ec) — today in CODE, not prose-only
# ============================================================================

def test_f04_summary_reports_n_m_k_and_refuses_an_n_only_backlog(tmp_path: Path):
    """The exact F-04 shape: 4,602 advisory records. The mechanism
    (`summarize_advisory_shard`, session_bus_coordinator.py:3045) never reports N
    alone — M and K travel with it, so '4,602 pending picks' is structurally
    refuted by its own producer (M=9 != N=4602)."""
    sbc = _load_sbc()
    shard = tmp_path / "advisory-f04.jsonl"
    with shard.open("w", encoding="utf-8") as fh:
        for i in range(4602):
            fh.write(json.dumps({"kind": "would-assign",
                                 "task_id": f"stuck-{i % 9:02d}",
                                 "ts": "2026-08-11T00:00:00Z"}) + "\n")
    summary = sbc.summarize_advisory_shard(shard)
    assert summary["pick_records"] == 4602                       # N
    assert summary["distinct_rows"] == 9                         # M — NOT 4602
    assert summary["dispatchable_at_emission"] is None           # K — never guessed
    assert "k_method" in summary
    assert summary["malformed_lines"] == 0
    # The N-only reading ('4,602 pending picks') is what the mechanism refuses:
    # a consumer of the canonical summary cannot obtain N without M and K.
    assert summary["pick_records"] != summary["distinct_rows"]


def test_f04_mutation_no_distinct_counting_makes_4602_a_backlog_again(tmp_path: Path):
    """Mutation: replace the task_id-keyed dedup with a per-record counter (M follows
    N). The same 4,602 records then summarize as 4,602 'distinct rows' — the figure
    the fleet acted on for hours is internally consistent again; the failure recurs.
    Restore the dedup: refused."""
    sbc = _load_sbc()
    shard = tmp_path / "advisory-f04-mut.jsonl"
    with shard.open("w", encoding="utf-8") as fh:
        for i in range(4602):
            fh.write(json.dumps({"kind": "would-assign",
                                 "task_id": f"stuck-{i % 9:02d}",
                                 "ts": "2026-08-11T00:00:00Z"}) + "\n")
    summary = sbc.summarize_advisory_shard(shard)

    def mutated_no_distinct(path: Path) -> dict:
        n = 0
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if json.loads(line).get("kind") in ("would-assign", "assign", "pick"):
                    n += 1
        return {"pick_records": n, "distinct_rows": n,   # the mutation: M := N
                "dispatchable_at_emission": None}

    mutated = mutated_no_distinct(shard)
    assert mutated["distinct_rows"] == 4602, "mutation: every record reads as a distinct row"
    assert mutated["distinct_rows"] == mutated["pick_records"], \
        "mutation: the N-only headline is no longer refuted"
    assert summary["distinct_rows"] == 9, "restored: the dedup refuses the reading"


def test_f04_k_is_never_guessed_on_an_empty_shard(tmp_path: Path):
    sbc = _load_sbc()
    empty = tmp_path / "advisory-empty.jsonl"
    empty.write_text("", encoding="utf-8")
    summary = sbc.summarize_advisory_shard(empty)
    assert summary["pick_records"] == 0
    assert summary["distinct_rows"] == 0
    assert summary["dispatchable_at_emission"] is None
    assert "k_method" in summary


# ============================================================================
# F-27 — MECH (a90870ec covers the class): lane-rejection figure
# ============================================================================

def test_f27_rejection_tally_carries_its_denominator():
    """The closest thing to a mechanism on the rejection path is `_top_rejection`
    (session_bus_coordinator.py:2074): `{reason, count, of}` — count WITH its
    denominator. It reports, it does not refuse: nothing in code stops an agent
    quoting a bare rejection tally (the 5,292 figure was withdrawn by self-
    correction, and the code comment at :2076 still asserts it)."""
    sbc = _load_sbc()
    rejections = [
        {"task_id": "t1", "reason": "lane cpu not in roster lanes"},
        {"task_id": "t2", "reason": "lane cpu not in roster lanes"},
        {"task_id": "t3", "reason": "lane cpu not in roster lanes"},
        {"task_id": "t4", "reason": "lane gpu busy"},
    ]
    top = sbc._top_rejection(rejections)
    assert top == {"reason": "lane cpu not in roster lanes", "count": 3, "of": 4}
    assert sbc._top_rejection([]) is None


# ============================================================================
# F-08 — MECH: the nudge rate limit is per-agent (34a17894 / 777f826e)
# ============================================================================

_C24_SPAWN_CONFIG = {
    "roster": [{"id": "new-main", "endpoint": "tmux:agent:new-main"}],
    "tmux": {"live_session": "agent", "allow_session_creation": False},
    "caps": {"max_concurrent_mains": 6},
}


def _probe_adapter(tag: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                   ledger_rows: list[dict], agent: str = "new-main") -> dict:
    adapter = _load_adapter(f"c31_{tag}")
    adapter.LEDGER = tmp_path / f"adapter-ledger-{tag}.jsonl"
    adapter.SPAWN_SETTLE_S = 0.0
    monkeypatch.setattr(adapter, "load_config", lambda: _C24_SPAWN_CONFIG)
    monkeypatch.setattr(adapter, "_tmux", lambda *a: (0, ""))
    adapter.BUS_ROOT = tmp_path / f"bus_{tag}"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)
    (adapter.BUS_ROOT / "heartbeats" / f"{agent}.json").write_text(
        json.dumps({"agent": agent, "state": "idle", "task_id": None,
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}),
        encoding="utf-8")
    adapter.LEDGER.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in ledger_rows), encoding="utf-8")
    return adapter.probe(_C24_SPAWN_CONFIG, agent, 0.0, 900.0)


def test_f08_bystander_nudges_do_not_rate_limit_this_agent(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The F-08 failure: a nudge refusal from ONE agent's ledger was filed as a
    FLEET-WIDE HIGH defect. The mechanism (tmux_adapter.py:1950 —
    `r.get("agent") != agent`) refuses that reading: another agent's recent nudge
    must not block this one. `--min-interval-s` defaults to 600 (tmux_adapter.py:3140)."""
    p = _probe_adapter("bystander", monkeypatch, tmp_path, [
        {"ts": _iso_ago(60), "kind": "nudge", "agent": "someone-else", "detail": "not us"},
        {"ts": _iso_ago(30), "kind": "nudge", "agent": "third-agent", "detail": "also not us"},
        {"ts": _iso_ago(3600), "kind": "spawn", "agent": "new-main", "detail": "our window"},
    ])
    assert p["seconds_since_last_nudge"] is None, \
        "another agent's nudge must not rate-limit this one — the fleet-wide claim is false"
    assert p["nudges_this_window_instance"] == 0
    assert not any("rate limit" in b for b in p["blockers"])


def test_f08_mutation_removing_the_agent_filter_reinstates_the_fleetwide_defect(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mutation: delete the `r.get("agent") != agent` clause from `_times(kind)`
    (tmux_adapter.py:1950). The SAME ledger then reads this agent's rate limit off
    a bystander's nudge — 30s < the 600s default — so the fleet-wide HIGH defect
    claim becomes TRUE again. The real code path refuses it (previous test);
    the mutated arithmetic does not."""
    rows = [
        {"ts": _iso_ago(60), "kind": "nudge", "agent": "someone-else", "detail": "not us"},
        {"ts": _iso_ago(30), "kind": "nudge", "agent": "third-agent", "detail": "also not us"},
        {"ts": _iso_ago(3600), "kind": "spawn", "agent": "new-main", "detail": "our window"},
    ]
    p = _probe_adapter("mutfleet", monkeypatch, tmp_path, rows)
    assert p["seconds_since_last_nudge"] is None      # real code: refused

    # The production closure (tmux_adapter.py:1941-1961) with the one clause deleted.
    def _ts(row: dict):
        try:
            return datetime.fromisoformat(str(row.get("ts"))).timestamp()
        except (TypeError, ValueError):
            return None

    agent = "new-main"
    mutated_times = []
    for r in rows:                                    # mutation: agent filter REMOVED
        if r.get("kind") == "nudge":
            t = _ts(r)
            if t is not None:
                mutated_times.append(t)
    spawn_at = max((_ts(r) for r in rows if r.get("kind") == "spawn"), default=None)
    recent = [t for t in mutated_times if spawn_at is None or t >= spawn_at]
    since = max(0.0, _time.time() - max(recent)) if recent else None
    assert since is not None and since < 600, \
        "mutation: the fleet-wide refusal is now a fleet-wide rate limit"
    # The mutated reading is the bystander's 30s nudge — the exact 'fleet-wide'
    # appearance the coordinator filed as a HIGH defect (all five agents came off
    # the 600s limit together and every refusal quoted a near-identical age).
    assert 20 <= since <= 50


def test_f08_own_nudge_still_rate_limits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Positive control — the first test cannot be satisfied by deleting the rate
    limit: THIS agent's own nudge inside the interval must still block it."""
    p = _probe_adapter("own", monkeypatch, tmp_path, [
        {"ts": _iso_ago(3600), "kind": "spawn", "agent": "new-main", "detail": "our window"},
        {"ts": _iso_ago(60), "kind": "nudge", "agent": "someone-else", "detail": "not us"},
        {"ts": _iso_ago(45), "kind": "nudge", "agent": "new-main", "detail": "OURS"},
    ])
    assert p["seconds_since_last_nudge"] is not None
    assert 35 <= p["seconds_since_last_nudge"] <= 60, \
        "must be OUR 45s nudge, not the bystander's 60s one"
    assert p["nudges_this_window_instance"] == 1


# ============================================================================
# F-15 — MECH (2f787163): fan-out policy. Rule or mechanism?
# ============================================================================

def test_f15_fanout_policy_commit_touches_only_prose_files():
    """`2f787163` (2026-08-12) — the row claims MECH. Its file list is policy docs
    only: CLAUDE.md, agents/*, a guide and the owning handoff. No script, no check,
    no test, no validator. Nothing in that commit can refuse serial work — the
    claim is a rule, not a mechanism. (The row itself admits the detector gap:
    RTG-49 / handoffs/active/fleet-fanout-measurement.md.)"""
    out = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "2f787163"],
        capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        pytest.skip("2f787163 not present in this checkout")
    files = out.stdout.splitlines()
    assert files, "commit must exist"
    assert not any(f.startswith("scripts/") or f.endswith(".py") for f in files), files


def test_f15_fanout_rule_exists_in_the_policy_surface():
    policy = (REPO_ROOT / "agents" / "shared" / "OPERATING_CONSTRAINTS.md").read_text(
        encoding="utf-8")
    assert "## Parallel Subagent Fan-Out" in policy
    assert "3–5 subagents" in policy or "3-5" in policy
    assert any("serial" in line.lower() for line in policy.splitlines())


# ============================================================================
# F-22 — MECH (existed, unused): backlog_row_check.py --ref and the dispatch path
# ============================================================================

def test_f22_ref_resolver_screens_a_correct_line(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """A correct `file.md:LINE` resolves to the checkbox at that line and screens it."""
    body = "# Demo\n\n- [ ] the intended row text\n\n- [x] a closed one\n"
    monkeypatch.setattr(brc, "HANDOFFS", tmp_path)
    (tmp_path / "demo.md").write_text(body, encoding="utf-8")
    code = brc.main(["--ref", "demo.md:3"])
    assert code == 0


def test_f22_ref_resolver_refuses_a_dead_anchor(tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """The ANCHOR ROT half of F-22: a line that is no longer a checkbox is REFUSED
    (exit 3, verdict ANCHOR_ROT) instead of resolving to garbage."""
    body = "# Demo\n\n- [ ] a real row at line 3\n\n- [ ] another row at line 5\n\n"
    monkeypatch.setattr(brc, "HANDOFFS", tmp_path)
    (tmp_path / "demo.md").write_text(body, encoding="utf-8")
    code = brc.main(["--ref", "demo.md:7"])          # line 7 is blank, not a checkbox
    assert code == 3


def test_f22_mutation_dead_anchor_resolves_to_garbage(tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: drop the anchor check (treat any line as a valid row). A dead
    anchor then 'resolves' to a row body that does not exist and screens it — rot
    becomes silent, which is exactly F-22's measured failure. Restore: refused."""
    body = "# Demo\n\n- [ ] a real row at line 3\n\nprose at line 5, no box\n"
    monkeypatch.setattr(brc, "HANDOFFS", tmp_path)
    (tmp_path / "demo.md").write_text(body, encoding="utf-8")
    code = brc.main(["--ref", "demo.md:5"])
    assert code == 3, "real code refuses the dead anchor"

    boxes = {n for n, _st, _b, _h in brc._boxes(tmp_path / "demo.md")}
    assert 5 not in boxes

    def mutated_resolve(ref: str):                   # the mutation: no anchor check
        _m = re.match(r"([^:]+):(\d+)$", ref)
        return tmp_path / _m.group(1), int(_m.group(2))

    _path, lineno = mutated_resolve("demo.md:5")
    assert lineno == 5 and _path.exists()
    # Under the mutation the resolver returns a verdict for a line that is NOT a row:
    line = _path.read_text(encoding="utf-8").splitlines()[lineno - 1]
    assert "- [" not in line, "the mutated resolver is reading a non-row as a row"


def test_f22_identity_substitution_is_not_refused_by_ref(tmp_path: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """The half of F-22 the --ref screener CANNOT refuse — and the honest limit of
    the claim. mainC's catch: `:327` was a DIFFERENT row. When a rotted line is
    still a checkbox, `--ref` screens the WRONG row (and can call it DISPATCHABLE);
    only text identity (`--row`, and today the typed `task_text` mandate) refuses
    the substitution. This pins the boundary so the claim is not overstated."""
    body = "# Demo\n\n- [ ] intended row, the work is real\n\n- [ ] UNRELATED other row\n"
    monkeypatch.setattr(brc, "HANDOFFS", tmp_path)
    (tmp_path / "demo.md").write_text(body, encoding="utf-8")
    code = brc.main(["--ref", "demo.md:5"])          # :5 is a checkbox — but the WRONG row
    assert code == 0
    # The same intent, resolved by TEXT, lands on the intended row:
    hits = brc.find_by_text("intended row, the work is real")
    assert hits and hits[0][1] == 3, hits


def test_f22_dispatch_path_now_refuses_unscreened_rows() -> None:
    """The F-22 wiring gap ('--ref exists and is NOT on the dispatch path') is
    closed structurally (AUD-2, 9bed637f): `check_task_assign` raises BusError
    when the dispatch identity is missing, and `dispatch_gate` refuses a queue row
    with no `screened_by` receipt."""
    import sys
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.coordination import session_bus as bus
    from scripts.coordination import session_bus_coordinator as sbc

    with pytest.raises(bus.BusError, match="task_text"):
        bus.check_task_assign({"kind": "task-assign", "payload": {"row_ref": "demo.md:3"}})

    ok, code, reason = sbc.dispatch_gate({"task_id": "X-1"})
    assert ok is False
    assert code == sbc.DISPATCH_GATE_UNSCREENED
    assert "screened_by" in reason


# ============================================================================
# F-24 — MECH-UC: bus_supervisor.sh fix + mutation harness (superseded, landed)
# ============================================================================

def test_f24_supervisor_uses_the_sha_deploy_marker_not_mtime():
    """H-4 (bc6dc77f) replaced the mtime predicate (which restarted a healthy daemon
    14 times) with a committed-tree SHA predicate. The old knob must not be live."""
    script = (REPO_ROOT / "scripts" / "coordination" / "bus_supervisor.sh").read_text(
        encoding="utf-8")
    assert "rev-parse HEAD:scripts/coordination" in script
    live_knob = re.search(r"^[^#]*STALE_SRC_SKEW_S=", script, re.M)
    assert live_knob is None, "the mtime knob must not be live (comments only)"


def test_f24_daemon_heartbeat_publishes_the_deploy_marker() -> None:
    sbc = _load_sbc()
    assert hasattr(sbc, "_source_tree_sha")
    marker = sbc._source_tree_sha()
    assert isinstance(marker, str) and len(marker) == 40
    import inspect
    hb_src = inspect.getsource(sbc._write_heartbeat)
    assert '"source_tree": _source_tree_sha()' in hb_src


def test_f24_mutation_harness_hook_exists():
    """The uncommitted M1_pattern_adjacency harness named in the row is gone —
    replaced by two landed harnesses: `BUS_SUPERVISOR_SH` env override in the
    pytest suite, and test_supervisor_stale_source.sh which FAILS if the old
    mtime predicate reappears."""
    suite = (REPO_ROOT / "scripts" / "coordination" / "tests" / "test_bus_supervisor.py"
             ).read_text(encoding="utf-8")
    assert "BUS_SUPERVISOR_SH" in suite, "the suite must run against a mutated copy"
    stale = (REPO_ROOT / "scripts" / "coordination" / "tests" /
             "test_supervisor_stale_source.sh").read_text(encoding="utf-8")
    assert "STALE_SRC_SKEW_S=" in stale
    assert "newest_source_mtime" in stale


# ============================================================================
# F-07 / F-11 / F-13 — MECH-UC: fleet_watch.sh (landed, then evolved)
# ============================================================================

def test_f071113_fleet_watch_is_committed():
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "scripts/coordination/fleet_watch.sh"],
        capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, "fleet_watch.sh must be tracked (R-1 landed as 83f204cf)"


def test_f07_fleet_watch_pane_heuristics_are_superseded_not_stubbed():
    """F-07's named mechanism (IDLE-CANDIDATE 'may be compacting' at fleet_watch.sh:60-64)
    was DELETED by P3-3, not landed as-is: pane text is now 'evidence for a human,
    never a trigger', and the three-state rule makes an unreadable instrument never
    count as idle. The compaction-misread class is refused by the stronger rule."""
    script = (REPO_ROOT / "scripts" / "coordination" / "fleet_watch.sh").read_text(
        encoding="utf-8")
    assert "IDLE-CANDIDATE" not in script or "gone with them" in script
    assert "NEVER A TRIGGER" in script
    assert "UNKNOWN" in script


def test_f071113_fleet_watch_detect_only_and_mutation_suited():
    """F-11/F-13: the detector loop is committed, detect-only (R-16 operator ruling:
    fleet_watch stays detect-only), and has its own mutation suite proving the
    detectors are not vacuous."""
    script = (REPO_ROOT / "scripts" / "coordination" / "fleet_watch.sh").read_text(
        encoding="utf-8")
    assert "DETECT AND REPORT ONLY" in script
    assert "COMPUTE-IDLE" in script
    assert (REPO_ROOT / "scripts" / "coordination" / "tests" / "test_fleet_watch_mutation.sh"
            ).exists()
    assert (REPO_ROOT / "scripts" / "coordination" / "tests" / "test_fleet_watch.sh").exists()


# ============================================================================
# F-10 / F-35 — MECH-UC: C51/C55 composer delivery (landed)
# ============================================================================

def test_f1035_submit_sends_the_wake_character_before_the_key(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """C55 (2076e359): the F-33/F-35 class is refused by sending a wake character
    (space), settling `_WAKE_SETTLE_S`, and ONLY THEN the action key. A bare Enter
    is a measured no-op on a Claude composer."""
    adapter = _load_adapter("c55")
    sent: list[list[str]] = []
    monkeypatch.setattr(adapter, "_tmux", lambda *a: (sent.append(list(a)) or (0, "")))
    monkeypatch.setattr(adapter.time, "sleep", lambda _s: None)
    rc, detail = adapter._press_key_with_wake("agent:mainC", "Enter")
    assert rc == 0, detail
    keys = [calls[3:] for calls in sent]
    assert keys == [[" "], ["Enter"]], keys
    assert len(sent) == 2, "exactly two send-keys: wake char, then the key"


def test_f1035_mutation_bare_key_sequence_is_the_measured_noop(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: skip the wake character (the pre-C55 sequence — a single bare key).
    The code's own measured record (tmux_adapter.py:764-774) says that sequence
    leaves the text exactly where it was: the F-33/F-35 failure recurs. Restore
    (previous test): the wake character is present and the composer is consumed."""
    adapter = _load_adapter("c55")
    sent: list[list[str]] = []
    monkeypatch.setattr(adapter, "_tmux", lambda *a: (sent.append(list(a)) or (0, "")))
    monkeypatch.setattr(adapter.time, "sleep", lambda _s: None)
    adapter._press_key_with_wake("agent:mainC", "Enter")
    bare = [calls[3] for calls in sent]
    assert bare == [" ", "Enter"]
    mutated_bare = [bare[-1]]                          # the mutation: only the key
    assert mutated_bare == ["Enter"]
    # The C55 block names the consequence of the bare sequence verbatim:
    src = (REPO_ROOT / "scripts" / "coordination" / "tmux_adapter.py").read_text(
        encoding="utf-8")
    assert "IGNORES A BARE KEY" in src
    assert "_WAKE_SETTLE_S = 1.0" in src


def test_f1035_failed_delivery_writes_an_undelivered_row(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """C51 (b6ea8679): a delivery failure is no longer invisible — `_fail_after_typing`
    rolls back, then records a `*-undelivered` ledger row with the strand state."""
    adapter = _load_adapter("c51")
    recorded: list[tuple] = []
    monkeypatch.setattr(adapter, "_clear_own_pending",
                        lambda target, baseline, faint_is_placeholder=False: (True, "cleared"))
    monkeypatch.setattr(adapter, "record",
                        lambda kind, agent, detail, **fields: recorded.append(
                            (kind, agent, fields)))
    rc = adapter._fail_after_typing("nudge", "mainC", "agent:mainC", "\u203a",
                                    "post-enter", "buffer not consumed")
    assert rc != 0
    assert recorded, "a failure must write a ledger row"
    kind, agent, fields = recorded[0]
    assert kind == "nudge-undelivered"
    assert agent == "mainC"
    assert fields.get("stranded") is False
    assert fields.get("rollback") == "cleared"
