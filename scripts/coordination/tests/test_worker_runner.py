#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for scripts/coordination/worker_runner.py (P2-1 / P2-4 / P2-6).

Every test here runs against the `stub` harness: no LLM, no tokens, no network,
no tmux (except the one test that deliberately exercises the visible-pane spawn
path in a THROWAWAY tmux session it creates and kills itself). A test suite for
the runner that needed a model to run would never be run, and a guard nobody
runs is a comment.

WHAT IS ACTUALLY BEING PROVEN, and why each one earns a test:

* Every REFUSAL is tested from the refusing side AND from the compliant side.
  A guard that also forbids its own legal idiom passes its own test and blocks
  the fleet (`feedback_guard_must_not_forbid_its_own_idiom`).
* The salvage no-loss property is tested TWICE: once positively (every dirty
  file is byte-recoverable from the ref) and once by MUTATION — a salvage that
  drops one file must RAISE, not return a plausible ref. Without the mutation
  half, the positive test would pass just as happily against a verifier that
  checks nothing (`feedback_vacuous_verification_empty_input`).
* The pane-IO prohibition (D8) is tested at the SOURCE level, because it is a
  property of the code, not of a run: no `send-keys` anywhere, and `capture-pane`
  only inside the evidence-capture function.

Run:  scripts/coordination/tests/test_worker_runner.py
  or: pytest scripts/coordination/tests/test_worker_runner.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import worker_runner as wr  # noqa: E402

REAL_BUS = Path("/workspace/coordination/session-bus")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
}


# --------------------------------------------------------------- fixtures


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                         text=True, env={**os.environ, **GIT_ENV})
    assert out.returncode == 0, f"git {args} failed: {out.stderr}"
    return out.stdout


def make_bus(tmp: Path, **pool_overrides) -> Path:
    """A complete, isolated session bus: roster, schema, directories."""
    bus = tmp / "bus"
    for sub in ("outbox", "inbox", "heartbeats", "cursors", "claims", "tokens"):
        (bus / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(REAL_BUS / "session_bus.schema.json", bus / "session_bus.schema.json")

    pool = {
        "enabled": True,
        "pool_root": str(tmp / "pool"),
        "runtime_root": str(tmp / "runtime"),
        "provider": None,                       # no pin in tests (stub harness)
        "rule8_amendment_ack": "TEST-ACK-RULE8",
        "lease_s": 60,
        "grace_s": 2,
        "poll_s": 0.1,
        "spawn_timeout_s": 10,
        "post_report_grace_s": 300,
        "stub_cmd": str(tmp / "stub_worker.py"),
    }
    pool.update(pool_overrides)
    cfg = {
        "schema_version": "session_bus.config.v1",
        "roster": [
            {"id": "workerpool", "role": "main", "lanes": ["none"],
             "endpoint": "exec:worker_runner", "drain": "boundary"},
            {"id": "coordinator-agent", "role": "coordinator-agent", "lanes": ["none"],
             "endpoint": "monitor:file", "drain": "push"},
            {"id": "auditor", "role": "reviewer", "lanes": ["none"],
             "endpoint": "monitor:file", "drain": "boundary"},
        ],
        "worker_harness": "stub",
        "worker_pool": pool,
        "tmux": {"live_session": "agent", "allow_session_creation": False},
    }
    import yaml
    (bus / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return bus


def make_pool(tmp: Path, lanes=("lane0",)) -> Path:
    """A real git repo plus real `git worktree` lanes under a pool root."""
    origin = tmp / "origin"
    origin.mkdir(parents=True, exist_ok=True)
    _git(origin, "init", "-q", "-b", "main")
    (origin / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(origin, "add", "seed.txt")
    _git(origin, "commit", "-q", "-m", "seed")
    pool = tmp / "pool"
    pool.mkdir(parents=True, exist_ok=True)
    for lane in lanes:
        _git(origin, "worktree", "add", "-q", "-b", lane, str(pool / lane))
    return pool


STUB_TEMPLATE = textwrap.dedent('''\
    #!/usr/bin/env python3
    """Test-only stub worker. Reads the brief, does what the scenario says."""
    import argparse, json, os, sys, time
    from pathlib import Path

    p = argparse.ArgumentParser()
    p.add_argument("--brief", required=True)
    p.add_argument("--report", required=True)
    a = p.parse_args()
    brief = json.loads(Path(a.brief).read_text())
    run_dir = Path(a.report).parent
    worktree = Path(brief["worktree"])
    progress = run_dir / "progress.jsonl"

    SCENARIO = {scenario!r}
    ids = [r["task_id"] for r in brief["rows"]]

    def note(task_id, event):
        with progress.open("a") as fh:
            fh.write(json.dumps({{"task_id": task_id, "event": event}}) + "\\n")

    if SCENARIO == "hang_midbatch":
        note(ids[0], "start"); note(ids[0], "complete")
        Path(a.report).write_text(json.dumps({{
            "schema_version": "worker_report.v1", "batch_id": brief["batch_id"],
            "harness": "stub", "subagents_spawned": 3, "tokens_used": 1000,
            "denials": [], "rows": [{{"task_id": ids[0], "outcome": "pass",
                                     "summary": "did the first row", "commits": [],
                                     "artifacts": []}}],
        }}))
        note(ids[1], "start")
        (worktree / "wip-from-dead-worker.txt").write_text("half-finished work\\n")
        time.sleep(3600)
        sys.exit(0)

    rows = [{{"task_id": t, "outcome": {outcome!r}, "summary": {summary!r},
             "commits": [], "artifacts": []}} for t in ids]
    Path(a.report).write_text(json.dumps({{
        "schema_version": {schema!r}, "batch_id": brief["batch_id"], "harness": "stub",
        "subagents_spawned": {subagents}, "tokens_used": {tokens},
        "denials": {denials!r}, "rows": rows,
    }}))
    sys.exit(0)
''')


def write_stub(tmp: Path, *, scenario="pass", outcome="pass", summary="stub summary",
               subagents=3, tokens=1000, denials=(), schema="worker_report.v1") -> Path:
    path = tmp / "stub_worker.py"
    path.write_text(STUB_TEMPLATE.format(
        scenario=scenario, outcome=outcome, summary=summary, subagents=subagents,
        tokens=tokens, denials=list(denials), schema=schema), encoding="utf-8")
    path.chmod(0o755)
    return path


def install_screener(monkeypatch, verdict="still-needed"):
    """P2-2 is being built in parallel by another agent, so the real module may
    or may not exist on disk when this suite runs. Every test that needs a
    DEFINITE verdict injects one; the tests that probe the absent/broken cases
    inject absence instead. Neither depends on what happens to be on disk."""
    import types
    mod = types.ModuleType("scripts.coordination.premise_screener")
    mod.screen_premise = lambda row: {"verdict": verdict, "evidence": "fixture evidence",
                                      "reason": "fixture"}
    monkeypatch.setitem(sys.modules, "scripts.coordination.premise_screener", mod)
    return mod


def assignment(tmp: Path, rows) -> Path:
    path = tmp / "assignment.json"
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return path


def outbox(bus: Path) -> list[dict]:
    path = bus / "outbox" / "workerpool.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def status_of(bus: Path, task_id: str) -> str | None:
    for row in outbox(bus):
        if row.get("task_id") == task_id and row.get("kind") in {"task-complete", "requeue"}:
            return (row.get("payload") or {}).get("status")
    return None


def row_payload(bus: Path, task_id: str) -> dict:
    for row in outbox(bus):
        if row.get("task_id") == task_id and row.get("kind") in {"task-complete", "requeue"}:
            return row.get("payload") or {}
    return {}


# ------------------------------------------------------------- lane guards


def test_lane_must_be_under_pool_root(tmp_path):
    make_pool(tmp_path)
    cfg = dict(wr.DEFAULTS, pool_root=str(tmp_path / "pool"))
    outside = tmp_path / "mains" / "mainA"
    outside.mkdir(parents=True)
    (outside / ".git").write_text("gitdir: /nowhere\n")
    with pytest.raises(wr.RefusalError, match="not under the pool root"):
        wr.resolve_lane(cfg, str(outside))


def test_lane_refuses_orphan_paths(tmp_path):
    pool = make_pool(tmp_path)
    orphan = pool / "lane9.orphan"
    orphan.mkdir()
    cfg = dict(wr.DEFAULTS, pool_root=str(pool))
    with pytest.raises(wr.RefusalError, match=r"\*\.orphan\*"):
        wr.resolve_lane(cfg, "lane9.orphan")


def test_lane_missing_fails_loudly(tmp_path):
    pool = make_pool(tmp_path)
    cfg = dict(wr.DEFAULTS, pool_root=str(pool))
    with pytest.raises(wr.RefusalError, match="does not exist"):
        wr.resolve_lane(cfg, "lane3")


def test_lane_must_be_a_git_worktree(tmp_path):
    pool = make_pool(tmp_path)
    (pool / "lane1").mkdir()
    cfg = dict(wr.DEFAULTS, pool_root=str(pool))
    with pytest.raises(wr.RefusalError, match="not a git worktree"):
        wr.resolve_lane(cfg, "lane1")


def test_lane_compliant_path_is_accepted(tmp_path):
    """The other half of every refusal test: the LEGAL idiom must still pass."""
    pool = make_pool(tmp_path)
    cfg = dict(wr.DEFAULTS, pool_root=str(pool))
    assert wr.resolve_lane(cfg, "lane0") == (pool / "lane0").resolve()


# ------------------------------------------------------------ D1 bounds


def test_bounds_refuse_raised_concurrency():
    with pytest.raises(wr.RefusalError, match="max_concurrent"):
        wr.check_bounds(dict(wr.DEFAULTS, max_concurrent=5))


def test_bounds_refuse_raised_batch_cap():
    with pytest.raises(wr.RefusalError, match="batch_cap"):
        wr.check_bounds(dict(wr.DEFAULTS, batch_cap=4))


def test_bounds_refuse_raised_token_ceiling():
    with pytest.raises(wr.RefusalError, match="token_ceiling"):
        wr.check_bounds(dict(wr.DEFAULTS, token_ceiling_per_batch=500_000))


def test_bounds_accept_ratified_values_and_lower():
    wr.check_bounds(dict(wr.DEFAULTS))
    wr.check_bounds(dict(wr.DEFAULTS, max_concurrent=2, batch_cap=1,
                         token_ceiling_per_batch=50_000))


def test_provider_pin_refuses_rerouting_env():
    with pytest.raises(wr.RefusalError, match="CLAUDE_CODE_USE_BEDROCK"):
        wr.check_provider_pin(dict(wr.DEFAULTS, provider="anthropic-paid"),
                              env={"CLAUDE_CODE_USE_BEDROCK": "1"})


def test_provider_pin_passes_clean_env():
    wr.check_provider_pin(dict(wr.DEFAULTS, provider="anthropic-paid"), env={})


def test_rule8_ack_gate_refuses_until_acked():
    with pytest.raises(wr.RefusalError, match="rule8_amendment_ack"):
        wr.check_rule8_ack(dict(wr.DEFAULTS))
    wr.check_rule8_ack(dict(wr.DEFAULTS, rule8_amendment_ack="RATIFY-RULE8-2026xxxx"))


# ------------------------------------------------------- lane lock / caps


def test_one_worker_per_worktree(tmp_path):
    pool = make_pool(tmp_path)
    first = wr.LaneLock(pool / "lane0").acquire()
    try:
        with pytest.raises(wr.RefusalError, match="already held"):
            wr.LaneLock(pool / "lane0").acquire()
        assert wr.live_lane_count(pool) == 1
    finally:
        first.release()
    # released: the lane is immediately reusable, and a stale FILE does not keep
    # counting as a live worker
    assert wr.live_lane_count(pool) == 0
    wr.LaneLock(pool / "lane0").acquire().release()


def test_lane_lock_is_the_file_the_daemon_reads(tmp_path):
    """`_free_pool_lane` in session_bus_coordinator.py reads <lane>/.worker.lock
    and takes the FIRST whitespace token as a pid. Two files would let the
    daemon see a lane as free while a worker held it."""
    pool = make_pool(tmp_path)
    lock = wr.LaneLock(pool / "lane0").acquire()
    try:
        path = pool / "lane0" / ".worker.lock"
        assert path.exists(), "the daemon looks for <lane>/.worker.lock"
        assert int(path.read_text().split()[0]) == os.getpid()
        # and the runner's own lock is never mistaken for the worker's work
        assert ".worker.lock" not in wr.dirty_paths(pool / "lane0")
    finally:
        lock.release()


def test_concurrency_cap_refuses_at_four(tmp_path):
    pool = make_pool(tmp_path, lanes=("lane0", "lane1", "lane2", "lane3"))
    held = [wr.LaneLock(pool / f"lane{i}").acquire() for i in range(4)]
    try:
        with pytest.raises(wr.RefusalError, match="cap is 4"):
            wr.check_concurrency(dict(wr.DEFAULTS), pool)
    finally:
        for lock in held:
            lock.release()
    wr.check_concurrency(dict(wr.DEFAULTS), pool)


# ------------------------------------------------------------------ brief


def test_brief_carries_identity_and_sourced_constraints(tmp_path):
    brief = wr.build_brief(
        [{"task_id": "T1", "task_text": "do the thing", "row_ref": "handoffs/x.md:12",
          "screened_by": "backlog_row_check@abc", "expected_occupancy": {"est_h": 0.5},
          "constraints": [{"text": "no GPU", "source": "MEASUREMENT.md:44"}, "vibes"]}],
        batch_id="B1", lane="lane0", worktree=Path("/w"), report_path=Path("/w/r.json"),
        cfg=dict(wr.DEFAULTS), lease_expires_ts="2026-08-16T00:00:00+00:00")
    row = brief["rows"][0]
    assert row["task_text"] == "do the thing"
    assert row["row_ref_hint"] == "handoffs/x.md:12"     # a hint, named as one
    assert row["screened_by"] == "backlog_row_check@abc"
    assert row["expected_occupancy"] == {"est_h": 0.5}
    assert row["constraints"][0]["source"] == "MEASUREMENT.md:44"
    assert row["constraints"][1]["source"] == "unsourced"   # visible, not silent


def test_brief_refuses_over_4kb(tmp_path):
    with pytest.raises(wr.RefusalError, match="cap 4096"):
        wr.build_brief([{"task_id": "T1", "task_text": "x" * 5000}], batch_id="B",
                       lane="lane0", worktree=Path("/w"), report_path=Path("/w/r.json"),
                       cfg=dict(wr.DEFAULTS), lease_expires_ts="t")


def test_brief_refuses_row_without_task_text():
    with pytest.raises(wr.RefusalError, match="task_text"):
        wr.build_brief([{"task_id": "T1", "task_text": "  "}], batch_id="B", lane="lane0",
                       worktree=Path("/w"), report_path=Path("/w/r.json"),
                       cfg=dict(wr.DEFAULTS), lease_expires_ts="t")


# -------------------------------------------------------- P2-6 batching


def test_batch_cap_and_single_source(tmp_path):
    cfg = dict(wr.DEFAULTS)
    rows = [{"task_id": f"T{i}", "task_text": "t", "source_handoff": "h.md"} for i in range(4)]
    with pytest.raises(wr.RefusalError, match="exceeds the P2-6 cap"):
        wr.check_batch(rows, cfg)
    mixed = [{"task_id": "T1", "task_text": "t", "source_handoff": "a.md"},
             {"task_id": "T2", "task_text": "t", "source_handoff": "b.md"}]
    with pytest.raises(wr.RefusalError, match="mixes source handoffs"):
        wr.check_batch(mixed, cfg)
    wr.check_batch(rows[:3], cfg)              # the compliant case still passes


def test_duplicate_task_ids_refused():
    dup = [{"task_id": "T1", "task_text": "a", "source_handoff": "h.md"},
           {"task_id": "T1", "task_text": "b", "source_handoff": "h.md"}]
    with pytest.raises(wr.RefusalError, match="unique"):
        wr.check_batch(dup, dict(wr.DEFAULTS))


# ------------------------------------------------------ premise screener


def test_absent_screener_is_unknown_not_go(tmp_path, monkeypatch):
    """The module does not exist yet (P2-2 is being built in parallel). An
    import failure must read as UNKNOWN — never as permission to proceed."""
    monkeypatch.setitem(sys.modules, "scripts.coordination.premise_screener", None)
    verdict = wr.screen_premise_safe({"task_id": "T1", "task_text": "x"})
    assert verdict["verdict"] == "unknown"
    assert "premise_screener" in verdict["reason"]


def test_throwing_screener_is_unknown(monkeypatch):
    import types
    mod = types.ModuleType("scripts.coordination.premise_screener")
    mod.screen_premise = lambda row: (_ for _ in ()).throw(RuntimeError("boom"))
    monkeypatch.setitem(sys.modules, "scripts.coordination.premise_screener", mod)
    assert wr.screen_premise_safe({"task_id": "T1"})["verdict"] == "unknown"


def test_garbage_verdict_is_unknown(monkeypatch):
    import types
    mod = types.ModuleType("scripts.coordination.premise_screener")
    mod.screen_premise = lambda row: {"verdict": "probably fine"}
    monkeypatch.setitem(sys.modules, "scripts.coordination.premise_screener", mod)
    assert wr.screen_premise_safe({"task_id": "T1"})["verdict"] == "unknown"


def test_still_needed_passes_through(monkeypatch):
    import types
    mod = types.ModuleType("scripts.coordination.premise_screener")
    mod.screen_premise = lambda row: {"verdict": "still-needed", "evidence": "q", "reason": "r"}
    monkeypatch.setitem(sys.modules, "scripts.coordination.premise_screener", mod)
    assert wr.screen_premise_safe({"task_id": "T1"})["verdict"] == "still-needed"


def test_unknown_verdict_parks_and_spawns_nothing(tmp_path, monkeypatch):
    make_pool(tmp_path)
    write_stub(tmp_path)
    bus = make_bus(tmp_path)
    monkeypatch.setitem(sys.modules, "scripts.coordination.premise_screener", None)
    spawned = []
    monkeypatch.setattr(wr, "spawn_worker", lambda *a, **k: spawned.append(a))
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "premise check me",
                                  "source_handoff": "h.md"}])
    rc = wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                  "--assignment", str(path), "--spawn-mode", "direct"])
    assert rc == 0
    assert spawned == [], "a parked row must not spawn a worker"
    kinds = [(r["kind"], (r.get("payload") or {}).get("parked_reason")) for r in outbox(bus)]
    assert ("requeue", "premise-unknown") in kinds
    assert any(k == "task-propose" for k, _ in kinds), "no routed fix task emitted"
    # the claim must be released, or the row is parked AND locked forever
    assert not list((bus / "claims").glob("*.json"))


def test_park_emits_once_per_state_change(tmp_path):
    bus = make_bus(tmp_path)
    runtime = tmp_path / "runtime"
    rows = [{"task_id": "T1", "task_text": "row text"}]
    verdicts = {"T1": {"verdict": "stale", "evidence": "e", "reason": "r"}}
    first = wr.park_rows(bus, "workerpool", rows, verdicts, runtime)
    second = wr.park_rows(bus, "workerpool", rows, verdicts, runtime)
    assert len(first) == 2 and second == [], "a refusal must emit once, on state change"
    verdicts["T1"]["verdict"] = "unknown"
    assert len(wr.park_rows(bus, "workerpool", rows, verdicts, runtime)) == 2


# ---------------------------------------------------- report validation


def _report(**over):
    base = {"schema_version": "worker_report.v1", "batch_id": "B", "harness": "stub",
            "subagents_spawned": 4, "tokens_used": 10, "denials": [],
            "rows": [{"task_id": "T1", "outcome": "pass", "summary": "s"}]}
    base.update(over)
    return base


def test_report_valid_case_passes():
    assert wr.validate_report(_report(), ["T1"]) == []


def test_report_requires_subagents_spawned():
    bad = _report(); del bad["subagents_spawned"]
    assert any("subagents_spawned" in e for e in wr.validate_report(bad, ["T1"]))


def test_report_requires_tokens_used():
    bad = _report(); del bad["tokens_used"]
    assert any("tokens_used" in e for e in wr.validate_report(bad, ["T1"]))


def test_report_requires_denials_list_even_when_empty():
    bad = _report(); del bad["denials"]
    errs = wr.validate_report(bad, ["T1"])
    assert any("denials" in e for e in errs)


def test_report_rejects_foreign_task_id():
    errs = wr.validate_report(_report(), ["T9"])
    assert any("not in this batch" in e for e in errs)


def test_report_rejects_bad_outcome_and_wrong_schema_version():
    errs = wr.validate_report(_report(rows=[{"task_id": "T1", "outcome": "great"}]), ["T1"])
    assert any("outcome" in e for e in errs)
    assert any("schema_version" in e for e in wr.validate_report(_report(schema_version="v0"), ["T1"]))


# ------------------------------------------------------- harness selection


def test_harness_global_then_lane_override(tmp_path):
    make_pool(tmp_path)
    bus = make_bus(tmp_path, lanes={"lane0": {"worker_harness": "codex"}})
    assert wr.load_pool_config(bus, None)["worker_harness"] == "stub"      # global
    assert wr.load_pool_config(bus, "lane0")["worker_harness"] == "codex"  # per-lane
    assert wr.resolve_harness(wr.load_pool_config(bus, "lane0")) == "codex"


def test_enabled_flag_gates_execution(tmp_path, monkeypatch):
    """Schedulable != executable. With the switch off, nothing runs and nothing
    is claimed — the row stays READY and visible instead of dying on a lease."""
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path)
    bus = make_bus(tmp_path, enabled=False)
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "row", "source_handoff": "h.md"}])
    rc = wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                  "--assignment", str(path), "--spawn-mode", "direct"])
    assert rc == 2
    assert not list((bus / "claims").glob("*.json"))
    assert outbox(bus) == []


def test_pilot_override_runs_but_never_bypasses_the_rule8_ack(tmp_path, monkeypatch):
    """--pilot-override exists to break the enabled-flag circularity (prove the
    runner end-to-end before flipping the switch). It must not become a general
    bypass: the D6 rule-8 ack still gates the kill path, override or no."""
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path)
    bus = make_bus(tmp_path, enabled=False)
    argv = ["--bus-root", str(bus), "run", "--lane", "lane0", "--task-id", "T1",
            "--row-text", "row", "--spawn-mode", "direct", "--pilot-override"]
    assert wr.main(argv) == 0
    assert status_of(bus, "T1") == "DONE_PASS"

    bus2 = make_bus(tmp_path / "b2", enabled=False, rule8_amendment_ack=None,
                    pool_root=str(tmp_path / "pool"), stub_cmd=str(tmp_path / "stub_worker.py"))
    rc = wr.main(["--bus-root", str(bus2), "run", "--lane", "lane0", "--task-id", "T2",
                  "--row-text", "row two", "--spawn-mode", "direct", "--pilot-override"])
    assert rc == 2, "the pilot override must not bypass the rule-8 amendment gate"


def test_config_alias_names_resolve_to_one_bound(tmp_path):
    """config.yaml (P2-5) spells the bounds `max_concurrent_workers`,
    `max_rows_per_batch`, `lease_grace_s`. Two spellings of one cap is how a
    bound gets enforced at one value and reported at another."""
    make_pool(tmp_path)
    bus = make_bus(tmp_path)
    import yaml
    cfg_raw = yaml.safe_load((bus / "config.yaml").read_text())
    cfg_raw["worker_pool"].pop("grace_s", None)
    cfg_raw["worker_pool"].update({"max_concurrent_workers": 2, "max_rows_per_batch": 1,
                                   "lease_grace_s": 7})
    (bus / "config.yaml").write_text(yaml.safe_dump(cfg_raw), encoding="utf-8")
    cfg = wr.load_pool_config(bus, "lane0")
    assert cfg["max_concurrent"] == 2
    assert cfg["batch_cap"] == 1
    assert cfg["grace_s"] == 7


def test_lane_harness_map_overrides_global(tmp_path):
    make_pool(tmp_path)
    bus = make_bus(tmp_path, lane_harness={"lane1": "codex"})
    assert wr.load_pool_config(bus, "lane0")["worker_harness"] == "stub"
    assert wr.load_pool_config(bus, "lane1")["worker_harness"] == "codex"


def test_unknown_harness_refused(tmp_path):
    with pytest.raises(wr.RefusalError, match="not a known harness"):
        wr.resolve_harness(dict(wr.DEFAULTS, worker_harness="gpt-in-a-box"))


def test_adding_a_harness_is_a_config_entry(tmp_path):
    cfg = dict(wr.DEFAULTS, worker_harness="mine",
               harnesses={"mine": ["mytool", "--brief", "{brief_path}"]})
    assert wr.resolve_harness(cfg) == "mine"
    argv = wr.build_harness_argv("mine", cfg, {"brief_path": "/b.json"})
    assert argv == ["mytool", "--brief", "/b.json"]


def test_builtin_harness_templates_render():
    ctx = {"prompt": "p", "permissions_path": "/perm.json", "worktree": "/w",
           "brief_path": "/b.json", "report_path": "/r.json", "python": "/py",
           "stub_cmd": "/stub.py"}
    assert wr.build_harness_argv("claude", dict(wr.DEFAULTS), ctx)[0] == "claude"
    assert "--settings" in wr.build_harness_argv("claude", dict(wr.DEFAULTS), ctx)
    assert wr.build_harness_argv("codex", dict(wr.DEFAULTS), ctx)[:2] == ["codex", "exec"]
    assert wr.build_harness_argv("stub", dict(wr.DEFAULTS), ctx)[:2] == ["/py", "/stub.py"]


def test_direct_spawn_refused_for_a_real_harness(tmp_path):
    pool = make_pool(tmp_path)
    run_dir = tmp_path / "rd"; run_dir.mkdir()
    with pytest.raises(wr.RefusalError, match="D8"):
        wr.spawn_worker(["true"], run_dir, pool / "lane0", dict(wr.DEFAULTS),
                        mode="direct", harness="claude")


def test_permission_profile_is_injected_as_data(tmp_path):
    run_dir = tmp_path / "rd"; run_dir.mkdir()
    path = wr.write_permission_profile(
        dict(wr.DEFAULTS, permission_profile={"allow": ["Read", "Edit"], "deny": ["Bash(rm:*)"]}),
        run_dir)
    settings = json.loads(path.read_text())
    assert settings["permissions"]["allow"] == ["Read", "Edit"]
    assert settings["permissions"]["deny"] == ["Bash(rm:*)"]


# ------------------------------------------------------------ end to end


def test_end_to_end_stub_pass(tmp_path, monkeypatch):
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path, summary="SENTINEL-WORKER-PROSE")
    bus = make_bus(tmp_path)
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "churn row one",
                                  "source_handoff": "h.md", "screened_by": "brc@1"}])
    rc = wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                  "--assignment", str(path), "--spawn-mode", "direct"])
    assert rc == 0
    assert status_of(bus, "T1") == "DONE_PASS"
    payload = row_payload(bus, "T1")
    assert payload["subagents_spawned"] == 3      # the fan-out multiplier, measured
    assert payload["tokens_used"] == 1000
    # claim released, heartbeat closed out
    assert not list((bus / "claims").glob("*.json"))
    hb = json.loads((bus / "heartbeats" / "workerpool.json").read_text())
    assert hb["state"] == "idle"


def test_daemon_argv_contract(tmp_path, monkeypatch):
    """The EXACT argv `session_bus_coordinator._exec_worker_runner` builds. The
    runner is exec'd by the daemon and by nothing else, so this is THE consumer:
    a flag rename that only this suite's own invocations cover would pass every
    other test and break the pool.
    """
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path)
    bus = make_bus(tmp_path)
    argv = ["--bus-root", str(bus), "run", "--lane", "lane0", "--task-id", "RTG-99",
            "--row-text", "a churn row the daemon picked",
            "--row-ref", "handoffs/active/x.md#anchor", "--screened-by", "brc@abc",
            "--spawn-mode", "direct"]
    assert wr.main(argv) == 0
    assert status_of(bus, "RTG-99") == "DONE_PASS"


def test_audit_packet_is_pointers_only(tmp_path, monkeypatch):
    """The auditor derives the diff from git itself (P2-7). If the packet
    carried the worker's own summary, the review would be anchored on the
    assertion it exists to test."""
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path, summary="SENTINEL-WORKER-PROSE")
    bus = make_bus(tmp_path)
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "churn row one",
                                  "source_handoff": "h.md"}])
    assert wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                    "--assignment", str(path), "--spawn-mode", "direct"]) == 0
    packets = [r for r in outbox(bus) if r["kind"] == "finding"]
    assert packets, "no audit packet emitted"
    blob = json.dumps(packets[0]["payload"]["audit_packet"])
    assert "SENTINEL-WORKER-PROSE" not in blob
    assert set(packets[0]["payload"]["audit_packet"]) <= set(wr.AUDIT_POINTER_KEYS)
    assert packets[0]["assignee"] == "auditor"


def test_denied_tool_call_never_renders_as_a_pass(tmp_path, monkeypatch):
    """P2-3: a denial recorded in the report fails the row. Silent parity
    between 'ran clean' and 'was refused halfway' is the thing being removed."""
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path, denials=[{"tool": "Bash(git push:*)", "reason": "not allowed"}])
    bus = make_bus(tmp_path)
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "row", "source_handoff": "h.md"}])
    assert wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                    "--assignment", str(path), "--spawn-mode", "direct"]) == 0
    assert status_of(bus, "T1") == "FAILED"
    assert row_payload(bus, "T1")["failure_reason"] == "permission-denied"


def test_token_ceiling_breach_fails_the_batch(tmp_path, monkeypatch):
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path, tokens=300_000)
    bus = make_bus(tmp_path, token_ceiling_per_batch=250_000)
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "row", "source_handoff": "h.md"}])
    assert wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                    "--assignment", str(path), "--spawn-mode", "direct"]) == 0
    assert status_of(bus, "T1") == "FAILED"
    assert row_payload(bus, "T1")["failure_reason"] == "token-ceiling-breach"


def test_invalid_report_is_not_partially_trusted(tmp_path, monkeypatch):
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path, schema="worker_report.v0")
    bus = make_bus(tmp_path)
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "row", "source_handoff": "h.md"}])
    assert wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                    "--assignment", str(path), "--spawn-mode", "direct"]) == 0
    assert status_of(bus, "T1") == "FAILED"
    assert row_payload(bus, "T1")["failure_reason"] == "report-invalid"


def test_roster_id_missing_refuses_before_claiming(tmp_path):
    """A runner that cannot record its results must not start work it cannot
    report (P2-5 wires the `workerpool` roster row)."""
    make_pool(tmp_path)
    write_stub(tmp_path)
    bus = make_bus(tmp_path)
    import yaml
    cfg = yaml.safe_load((bus / "config.yaml").read_text())
    cfg["roster"] = [r for r in cfg["roster"] if r["id"] != "workerpool"]
    (bus / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "row", "source_handoff": "h.md"}])
    rc = wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                  "--assignment", str(path), "--spawn-mode", "direct"])
    assert rc == 2
    assert not list((bus / "claims").glob("*.json")), "refused runs must claim nothing"


def test_already_claimed_row_is_not_double_worked(tmp_path, monkeypatch):
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path)
    bus = make_bus(tmp_path)
    wr.claim_row(bus, "auditor", "row one")
    path = assignment(tmp_path, [{"task_id": "T1", "task_text": "row one",
                                  "source_handoff": "h.md"}])
    assert wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                    "--assignment", str(path), "--spawn-mode", "direct"]) == 0
    assert outbox(bus) == [], "a row claimed elsewhere must produce no results"


# --------------------------------------------- D6 kill-with-salvage (P2-4)


def _dirty_worktree(tmp_path) -> Path:
    """A lane with every shape of uncommitted state a dead worker could leave."""
    pool = make_pool(tmp_path)
    lane = pool / "lane0"
    (lane / "tracked.txt").write_text("committed\n", encoding="utf-8")
    (lane / "doomed.txt").write_text("will be deleted\n", encoding="utf-8")
    _git(lane, "add", "tracked.txt", "doomed.txt")
    _git(lane, "commit", "-q", "-m", "base")
    # now dirty it, the way a worker killed mid-flight would
    (lane / "tracked.txt").write_text("MODIFIED by the worker\n", encoding="utf-8")
    (lane / "brand-new.txt").write_text("untracked work\n", encoding="utf-8")
    (lane / "nested" / "deep").mkdir(parents=True)
    (lane / "nested" / "deep" / "file with spaces.md").write_text("nested\n", encoding="utf-8")
    (lane / "nested" / "deep" / "ünïcode.txt").write_text("uni\n", encoding="utf-8")
    (lane / "binary.bin").write_bytes(bytes(range(256)))
    (lane / "doomed.txt").unlink()
    return lane


def test_salvage_loses_nothing(tmp_path):
    """THE no-loss property. Every dirty file must come back byte-for-byte out
    of the salvage ref, and a deletion must stay deleted."""
    lane = _dirty_worktree(tmp_path)
    before = {rel: (lane / rel).read_bytes() for rel in wr.dirty_paths(lane)
              if (lane / rel).is_file()}
    assert len(before) == 5, f"fixture did not create the expected dirty set: {before.keys()}"

    evidence = tmp_path / "harness-transcript.log"
    evidence.write_text("worker transcript\n", encoding="utf-8")
    result = wr.salvage_worktree(lane, "T-SALVAGE",
                                evidence={"harness-transcript.log": evidence})

    assert result["verified"] is True
    listing = _git(lane, "ls-tree", "-r", "-z", "--name-only", result["salvage_ref"]).split("\0")
    for rel, data in before.items():
        assert rel in listing, f"{rel} missing from the salvage ref"
        blob = subprocess.run(["git", "-C", str(lane), "cat-file", "blob",
                               f"{result['salvage_ref']}:{rel}"], capture_output=True)
        assert blob.stdout == data, f"{rel} does not round-trip byte-for-byte"
    assert "doomed.txt" not in listing, "a deletion must be preserved as a deletion"
    assert ".salvage-evidence/harness-transcript.log" in listing

    # non-destructive: the dead worker's tree is left exactly as found
    assert (lane / "tracked.txt").read_text() == "MODIFIED by the worker\n"
    assert wr.dirty_paths(lane) == sorted(before) + ["doomed.txt"] or \
        set(wr.dirty_paths(lane)) == set(before) | {"doomed.txt"}


def test_salvage_that_loses_a_file_FAILS(tmp_path):
    """MUTATION TEST. Drop one file from the staging set and the salvage must
    RAISE — not return a plausible ref. Without this, the positive test above
    would pass just as happily against a verifier that checks nothing."""
    lane = _dirty_worktree(tmp_path)
    dropped = "brand-new.txt"
    with pytest.raises(wr.SalvageError) as exc:
        wr.salvage_worktree(lane, "T-LOSSY",
                            _stage_filter=lambda paths: [p for p in paths if p != dropped])
    assert dropped in str(exc.value)
    assert "LOSS IS FORBIDDEN" in str(exc.value)


def test_salvage_mutation_is_visible_for_every_dirty_file(tmp_path):
    """Not one lucky file: dropping ANY single path must be detected."""
    for i in range(5):
        lane = _dirty_worktree(tmp_path / f"case{i}")
        paths = [p for p in wr.dirty_paths(lane) if (lane / p).is_file()]
        target = paths[i]
        with pytest.raises(wr.SalvageError, match="LOSS IS FORBIDDEN"):
            wr.salvage_worktree(lane, f"T-LOSSY-{i}",
                                _stage_filter=lambda ps, t=target: [p for p in ps if p != t])


def test_salvage_is_rerunnable(tmp_path):
    lane = _dirty_worktree(tmp_path)
    first = wr.salvage_worktree(lane, "T-A")
    second = wr.salvage_worktree(lane, "T-B")
    assert first["files"] == second["files"]
    assert _git(lane, "rev-parse", f"{first['salvage_ref']}^{{tree}}") == \
        _git(lane, "rev-parse", f"{second['salvage_ref']}^{{tree}}")


def test_kill_owned_kills_and_verifies_death(tmp_path):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"],
                            start_new_session=True)
    try:
        record = wr.kill_owned(proc.pid, grace_s=2)
        assert record["dead"] is True
        assert record["term"] is True
        with pytest.raises(ProcessLookupError):
            os.kill(proc.pid, 0)
    finally:
        proc.poll()


def test_kill_owned_never_signals_its_own_process_group(monkeypatch):
    """No name-pattern kills and no self-immolation: if the captured pid's group
    is this runner's own group, the signal is narrowed to the single pid."""
    sent = []
    monkeypatch.setattr(wr.os, "getpgid", lambda pid: os.getpgrp())
    monkeypatch.setattr(wr.os, "killpg", lambda pgid, sig: sent.append(("group", pgid, sig)))
    monkeypatch.setattr(wr.os, "kill", lambda pid, sig: sent.append(("pid", pid, sig))
                        if sig else (_ for _ in ()).throw(ProcessLookupError()))
    record = wr.kill_owned(999999, grace_s=0.1)
    assert record["group_signalled"] is False
    assert not any(kind == "group" for kind, _, _ in sent)


def test_lease_expiry_kills_salvages_and_only_the_inflight_row_fails(tmp_path, monkeypatch):
    """P2-4 + P2-6 together, end to end: a three-row batch times out mid-row.
    Row 1 completed and keeps its pass. Row 2 was in progress: FAILED with a
    salvage_ref. Row 3 was never started: back to READY, UNMARKED."""
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path, scenario="hang_midbatch")
    bus = make_bus(tmp_path, lease_s=4, grace_s=2, poll_s=0.2)
    rows = [{"task_id": f"T{i}", "task_text": f"row {i}", "source_handoff": "h.md"}
            for i in (1, 2, 3)]
    path = assignment(tmp_path, rows)
    rc = wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                  "--assignment", str(path), "--spawn-mode", "direct"])
    assert rc == 0, "a salvaged timeout is a recorded outcome, not a runner failure"

    assert status_of(bus, "T1") == "DONE_PASS"
    p2 = row_payload(bus, "T2")
    assert p2["status"] == "FAILED" and p2["failure_reason"] == "lease-expired"
    assert p2["salvage_ref"].startswith("refs/salvage/")
    p3 = row_payload(bus, "T3")
    assert p3["status"] == "READY" and p3.get("unmarked") is True
    assert "failure_reason" not in p3, "an untouched row must return UNMARKED"

    # the worker's half-finished file survived the kill
    lane = tmp_path / "pool" / "lane0"
    listing = _git(lane, "ls-tree", "-r", "-z", "--name-only", p2["salvage_ref"])
    assert "wip-from-dead-worker.txt" in listing
    assert ".salvage-evidence/harness-transcript.log" in listing
    assert ".salvage-evidence/brief.json" in listing

    defects = [r for r in outbox(bus) if r["kind"] == "defect"]
    assert defects and defects[0]["payload"]["kill"]["dead"] is True
    assert defects[0]["payload"]["salvage"]["verified"] is True
    assert not list((bus / "claims").glob("*.json")), "claims must be released after salvage"


# ------------------------------------------------------- D8 source guards


def test_no_pane_io_decision_channel():
    """D8, enforced against the SOURCE. The machine never types into a pane, and
    the only place it reads one is the evidence capture whose output is written
    to a file for a human — never parsed, matched, or branched on."""
    src = Path(wr.__file__).read_text(encoding="utf-8")
    assert "send-keys" not in src, "worker_runner must never type into a pane (D8)"
    assert "send_keys" not in src
    fn_start = src.index("def capture_scrollback")
    fn_end = src.index("\ndef ", fn_start + 1)
    body = src[fn_start:fn_end]
    assert "capture-pane" in body, "the evidence path must exist"
    assert src.count("capture-pane") == body.count("capture-pane"), \
        "every mention of capture-pane must live inside capture_scrollback, the evidence-only path"


def test_runner_never_writes_the_queue():
    """Invariant 1. queue.jsonl belongs to the coordinator-daemon; a runner that
    wrote rows directly would be the second writer the protocol exists to stop."""
    # the module docstring is allowed to DISCUSS queue.jsonl; the code is not
    # allowed to open it. Split the docstring off and check the body.
    body = Path(wr.__file__).read_text(encoding="utf-8").split('"""', 2)[2]
    assert '"queue.jsonl"' not in body
    assert "'queue.jsonl'" not in body
    assert 'target="queue"' not in body


# ------------------------------------------------- visible pane (real tmux)


@pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux not installed")
def test_visible_tmux_spawn_and_collect(tmp_path, monkeypatch):
    """The D8 path for real: a throwaway session created and destroyed by this
    test (never the live `agent` session), a window that a human could watch,
    and a completion signal that is the REPORT FILE, not pane text."""
    install_screener(monkeypatch)
    make_pool(tmp_path)
    write_stub(tmp_path)
    session = f"wr-test-{os.getpid()}"
    bus = make_bus(tmp_path, tmux_session=session)
    subprocess.run(["tmux", "new-session", "-d", "-s", session, "-n", "idle", "sleep", "300"],
                   check=True, capture_output=True)
    try:
        path = assignment(tmp_path, [{"task_id": "T1", "task_text": "visible row",
                                      "source_handoff": "h.md"}])
        rc = wr.main(["--bus-root", str(bus), "run", "--lane", "lane0",
                      "--assignment", str(path), "--spawn-mode", "tmux"])
        assert rc == 0
        assert status_of(bus, "T1") == "DONE_PASS"
    finally:
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)


@pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux not installed")
def test_tmux_refuses_to_create_a_session(tmp_path):
    make_pool(tmp_path)
    write_stub(tmp_path)
    run_dir = tmp_path / "rd"; run_dir.mkdir()
    cfg = dict(wr.DEFAULTS, tmux_session=f"wr-absent-{os.getpid()}", spawn_timeout_s=2)
    with pytest.raises(wr.RefusalError, match="never creates one"):
        wr.spawn_worker(["true"], run_dir, tmp_path / "pool" / "lane0", cfg,
                        mode="tmux", harness="stub")


def main() -> int:
    """Direct invocation runs the same suite pytest collects — one set of
    checks, not two (a `main()` that asserts separately is a suite the repo-wide
    run does not count)."""
    return subprocess.call([sys.executable, "-m", "pytest", "-q", str(Path(__file__).resolve())])


if __name__ == "__main__":
    sys.exit(main())
