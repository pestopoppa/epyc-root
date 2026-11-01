"""backlog_gen.py: fixture epyc.row.v3 rows + rowflow dry-run records (dryrun/<id>/PASS.json | FAIL-n.json) ->
BACKLOG-<bucket>.md states and unblock linkage. The keeper log is informational only.

Ported 2026-11-01 to the rowflow model. DELETED (subject no longer exists): test_failures_counted_beyond_state_window
(keeper QUAL-FAILURE memos; failures are now dryrun/<id>/FAIL-n.json files), test_schema_rechecks_are_not_qualification_runs
(READY-SKIP schema re-check vs qualification-run counting; the keeper no longer re-checks legacy schemas), the
"receipt named but file missing -> awaiting keeper" column of the old scoreboard test (no receipts; the keeper-owed state
is now a running dry run), and the per-owner worker breaker (removed with rowflow). Worker buckets are "codex-gen"
plus "handoff-<slug>"; owner strings no longer select a worker."""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.coordination import backlog_gen as bg

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts/coordination/rowflow"))
import rowflow as rf  # noqa: E402  (the same module object backlog_gen imported)

SCRIPT = Path(__file__).parents[2] / "scripts/coordination/backlog_gen.py"
GEN = bg.GENERALIST
KLOG = "ws58-calendar-keeper.log"


@pytest.fixture(autouse=True)
def _real_rowflow(monkeypatch):
    """Other suites set bg._rf = None; the state tests here need the real rowflow status machine. flow_scoreboard
    imports backlog_gen as a top-level module (a second module object), so both are patched."""
    monkeypatch.setattr(bg, "_rf", rf)
    sys.path.insert(0, str(Path(__file__).parents[2] / "scripts/coordination"))
    import backlog_gen as bg_top
    monkeypatch.setattr(bg_top, "_rf", rf)


def _row(F: Path, rid: str, lane: str = "cpu", rank=5, schema="epyc.row.v3", **kw) -> dict:
    """A published row with the fields rowflow.publish writes, on a real small launcher file (sha must match)."""
    job = F.parent / "jobs" / rid
    job.mkdir(parents=True, exist_ok=True)
    launcher = job / "launch.sh"
    launcher.write_text(f"#!/bin/bash\n# launcher for {rid}\nexec bash filler_run15.sh --id {rid} --class {lane} --min-window 300\n")
    d = {"schema": schema, "id": rid, "owner": kw.pop("owner", "codex-test"), "lane": lane,
         "regions": kw.pop("regions", "mi210_0,184-191" if lane == "gpu" else "any-cpu-quarter"),
         "launcher": {"path": str(launcher), "sha256": rf.sha256(str(launcher))},
         "engine": {"path": "/x/filler_run15.sh", "sha256": "0" * 64},
         "result_path": str(job / "out" / "results.jsonl"), "result_format": "jsonl", "decision_rule": "score>=1 on every item",
         "handoff_task": kw.pop("handoff_task", "handoffs/active/test.md:T-1"), "estimate_s": 600, "min_window_s": 300,
         "window_s": 1020, "gib": 48, "ports": [], "priority_rank": rank, "scratch_root": str(job), "keep": ["out/results.jsonl"]}
    d.update(kw)
    (F / "ready" / f"{rid}.json").write_text(json.dumps(d))
    return d


def _pass(F: Path, rid: str, when="2026-11-01T12:10:00Z"):
    d = json.loads((F / "ready" / f"{rid}.json").read_text())
    rf.atomic_json(rf.pass_path(str(F), rid), {"id": rid, "launcher_sha256": d["launcher"]["sha256"], "passed_at": when,
                                               "units": 1, "result_path": d["result_path"]})


def _fail(F: Path, rid: str, reason="gate refused"):
    d = json.loads((F / "ready" / f"{rid}.json").read_text())
    return rf.record_fail(str(F), rid, d, reason, {})


def _flags(tmp_path: Path):
    F = tmp_path / "flags"
    for d in ("ready", "grants", "filing-done", "dryrun"):
        (F / d).mkdir(parents=True)
    _row(F, "gen-qualified", rank=1)
    _pass(F, "gen-qualified")
    _row(F, "gen-needsqual", rank=10)
    _row(F, "gen-blockedby", rank=3, blocked_by=["port 8099 collides with the hub"])
    _row(F, "gen-failed", lane="gpu", rank=4)
    _fail(F, "gen-failed", "no VRAM in use during the dry run")
    _row(F, "gen-dryrunning", rank=5)
    rf.atomic_json(rf.running_path(str(F), "gen-dryrunning"), {"pid": os.getpid(), "started": "2026-11-01T12:00:00Z"})
    _row(F, "gen-oldschema", rank=6, schema="epyc.ready.v2")
    _row(F, "gen-running", lane="gpu", rank=7)
    _pass(F, "gen-running", when="2026-10-31T22:00:00Z")
    (F / "grants" / "gen-running.grant").write_text("regions=mi210_0,184-191 start=t end=t\n")
    _row(F, "gen-done", rank=8)
    (F / "grants" / "gen-done.ended").write_text("rc=0\n")
    _row(F, "gen-withdrawn", rank=9)
    (F / "ready" / "gen-withdrawn.withdrawn").write_text("")

    (F / KLOG).write_text("\n".join([
        "2026-11-01T12:00:00Z DRYRUN-START gen-failed regions=mi210_0,184-191",
        "2026-11-01T12:05:00Z DRYRUN-RESULT FAIL gen-failed no VRAM in use during the dry run",
        "2026-11-01T12:10:00Z DRYRUN-RESULT PASS gen-qualified 1 unit(s)",
        "2026-11-01T12:10:30Z ROW-ARM ARMED gen-qualified queue=q2 regions=any-cpu-quarter",
        "2026-11-01T12:11:00Z IDLE-ALARM free for >=2 checks: q3",
        "2026-11-01T12:12:00Z DRYRUN-RESULT WAIT gen-needsqual lane busy",
    ]) + "\n")
    (F / f"WORK-{GEN}-code.md").write_text("\n".join([
        bg.B_MARK, "## old section", bg.E_MARK, "# codex-gen: code queue",
        "- [S] handoffs/active/a.md:10 — **FIX-1 — read VRAM through rocm-smi in the launcher** [unblocks: gen-failed]",
        "- [S] handoffs/active/b.md:20 — **OTHER-2 — unrelated small cleanup**", ""]))
    (F / "WORK-codex3-code.md").write_text("# codex3 (closed): code queue\n- [S] handoffs/active/c.md:1 — **C3-1 — thing**\n")
    (F / "unblocks.json").write_text(json.dumps({"migrate gen-oldschema manifest to epyc.row.v3": ["gen-oldschema"]}))
    pri = {"schema": "backlog_priority.v1", "rows": {
        "INF-9": {"kind": "non-inference", "tier": 1, "rank": 3, "basis": "T1 ... write the KPF launcher", "unblocks": ["RTG-1"], "blocker": ""},
        "RTG-1": {"kind": "inference-prep", "tier": 0, "rank": 1, "basis": "x", "unblocks": [], "blocker": ""}},
        "inference_prep": [
            {"rank": 1, "filler": "kpf-r12", "row": "RTG-1", "kind": "inference-prep", "owner": "Codex NI / KPF18", "blocker": "missing launcher"},
            {"rank": 2, "filler": "kpf-r11", "row": "RTG-1", "kind": "inference-prep", "owner": "codex-ni-01a16d6b", "blocker": "harness fix: rc1 framing_pass=false"},
            {"rank": 3, "filler": "gen-qualified", "row": "RTG-1", "kind": "inference-prep", "owner": "codex-test", "blocker": "harness fix"}]}
    (tmp_path / "backlog-priority.json").write_text(json.dumps(pri))
    return F, tmp_path / "backlog-priority.json"


def _build(F, pri, **kw):
    return bg.build(str(F), str(pri), str(F / KLOG), **kw)


def test_states_and_linkage(tmp_path):
    F, pri = _flags(tmp_path)
    data = _build(F, pri)
    g = {r["id"]: r for r in data["workers"][GEN]["rows"]}
    assert g["gen-qualified"]["state"] == "qualified-armed", "PASS.json with the current launcher sha"
    assert g["gen-needsqual"]["state"] == "needs-qualification", "no dry run yet (the DRYRUN-RESULT WAIT line is informational)"
    assert g["gen-blockedby"]["state"] == "blocked" and "port 8099" in g["gen-blockedby"]["reasons"][0]
    assert g["gen-failed"]["state"] == "blocked" and g["gen-failed"]["lane"] == "gpu" and g["gen-failed"]["cause"] == "worker"
    assert any(t.startswith("fix: fix dry-run failure of gen-failed") for t in g["gen-failed"]["tasks"]), "the FAIL record is the owner's fix task"
    assert any("FIX-1" in t for t in g["gen-failed"]["tasks"]), "WORK line with [unblocks:] must attach"
    assert g["gen-dryrunning"]["state"] == "blocked" and g["gen-dryrunning"]["cause"] == "keeper"
    assert g["gen-oldschema"]["state"] == "blocked" and "legacy manifest" in g["gen-oldschema"]["reasons"][0]
    assert any("migrate gen-oldschema" in t for t in g["gen-oldschema"]["tasks"]), "unblocks.json must attach"
    assert g["gen-running"]["state"] == "running"
    assert g["gen-done"]["state"] == "done"
    assert "gen-withdrawn" not in g
    assert g["kpf-r12"]["state"] == "needs-launcher" and any("INF-9" in t for t in g["kpf-r12"]["tasks"])
    assert g["kpf-r11"]["state"] == "blocked" and g["kpf-r11"]["reasons"] == ["harness fix: rc1 framing_pass=false"]
    assert g["gen-qualified"]["row"] == "RTG-1", "READY id joins the handoff row through inference_prep.filler"
    assert g["gen-needsqual"]["row"] == "T-1", "a v3 row joins its handoff row through handoff_task"
    # ordering (rule 1): advanceable rows first, starved-lane rows first among them; then parked/armed/running/done
    rows = data["workers"][GEN]["rows"]
    adv = [r for r in rows if r["state"] in bg.ADVANCEABLE]
    assert rows[:len(adv)] == adv
    rest = [r["state"] for r in rows[len(adv):]]
    assert rest == sorted(rest, key=bg.STATE_ORDER.__getitem__)
    assert data["workers"][GEN]["qual"] == {"cpu": 1, "gpu": 0, "host": 0}
    assert data["ready_by_lane"] == {"cpu": 1, "gpu": 1, "host": 0}, "qualified-armed + running count as ready"
    md = bg.render(GEN, data)
    assert "[FLOOR] CPU: 1" in md and "[FLOOR] GPU: 1" in md
    assert "- [blocked] gpu rank=4 **gen-failed**" in md
    assert "OTHER-2" in md, "non-inference tasks not linked to a row are still listed"
    assert "C3-1" in md, "closed legacy queues are re-routed to codex-gen"
    assert md.index("gen-failed") < md.index("OTHER-2")
    assert md.index("FIX-1") < md.index("OTHER-2"), "a task that unblocks a row ranks before one that unblocks nothing"


def test_write_and_dry_run_modes(tmp_path):
    F, pri = _flags(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--flags", str(F), "--priority", str(pri), "--out", str(out), "--dry-run"],
                       capture_output=True, text=True, check=True)
    assert f"BACKLOG-{GEN}.md" in r.stdout and not list(out.iterdir()), "dry run writes nothing"
    assert "## old section" in (F / f"WORK-{GEN}-code.md").read_text()
    subprocess.run([sys.executable, "-I", str(SCRIPT), "--flags", str(F), "--priority", str(pri), "--out", str(out)],
                   capture_output=True, text=True, check=True)
    assert sorted(p.name for p in out.iterdir()) == [f"BACKLOG-{GEN}.md"]
    w = (F / f"WORK-{GEN}-code.md").read_text()
    assert "## old section" not in w and f"BACKLOG-{GEN}.md" in w and "[BLOCKED] gpu rank=4 gen-failed" in w
    assert "FIX-1" in w, "existing code-queue lines are preserved"
    assert (out / f"BACKLOG-{GEN}.md").read_text().count("**gen-blockedby**") == 1


def test_flow_scoreboard_counts(tmp_path):
    from scripts.coordination import flow_scoreboard as fs
    F, pri = _flags(tmp_path)
    now = dt.datetime(2026, 11, 1, 13, 0, tzinfo=dt.timezone.utc)
    rows, state = fs.compute(str(F), str(pri), str(F / KLOG), {}, now)
    g = rows[GEN]
    assert g["armed"] == 1, "gen-qualified's PASS.json passed_at is today; gen-running passed yesterday"
    assert g["armed_log"] == 1 and g["dryrun_fail"] == 1
    assert g["open_fix"] == 1, "gen-failed: FAIL record with the launcher sha unchanged"
    assert g["blocked_rows"] >= 4 and g["closed"] == 0 and g["parked"] == 0
    assert g["awaiting_keeper"] == 1 and g["awaiting_ids"] == ["gen-dryrunning"]
    assert g["idle_h"] == round(120 / 3600, 2), "one cpu IDLE-ALARM charged to a bucket with a blocked cpu row"
    # the fix task closes when the launcher changes (rowflow retries; the FAIL no longer matches the sha)
    Path(json.loads((F / "ready" / "gen-failed.json").read_text())["launcher"]["path"]).write_text("#!/bin/bash\n# fixed\n")
    rows2, state = fs.compute(str(F), str(pri), str(F / KLOG), state, now)
    assert rows2[GEN]["open_fix"] == 0
    # a blocked row that disappears counts as a closed blocking task
    (F / "ready" / "gen-blockedby.json").unlink()
    rows3, _ = fs.compute(str(F), str(pri), str(F / KLOG), state, now)
    assert rows3[GEN]["closed"] >= 1
    assert f"| {GEN} | 1 |" in fs.render(rows3, now)
    # yesterday's PASS is not counted
    rows4, _ = fs.compute(str(F), str(pri), str(F / KLOG), {}, now + dt.timedelta(days=1))
    assert rows4[GEN]["armed"] == 0


def test_starved_lane_first(tmp_path):
    F, pri = _flags(tmp_path)
    # a second qualified CPU row: CPU is at floor (2), GPU (1 running) is starved
    _row(F, "gen-qualified2", rank=1)
    _pass(F, "gen-qualified2")
    data = _build(F, pri)
    g = data["workers"][GEN]
    assert data["ready_by_lane"] == {"cpu": 2, "gpu": 1, "host": 0}
    assert g["starved"] == ["gpu"]
    assert g["rows"][0]["id"] == "gen-failed", "starved-lane (gpu) row beats higher-priority cpu rows"
    assert [r["id"] for r in g["rows"][1:3]] == ["kpf-r12", "kpf-r11"], "then global priority (rank 1, 2)"


def test_lineage_stem_and_supersedes(tmp_path):
    assert bg.id_stem("codex-hil15-s0-micron-v12-20261031") == "codex-hil15-s0-micron"
    assert bg.id_stem("ct21-rearm-r1-20261028") == "ct21"
    assert bg.id_stem("kpf-r12") == "kpf"
    assert bg.id_stem("codex-hil15-s0-micron-v12-20261031") == rf.id_stem("codex-hil15-s0-micron-v12-20261031")
    F = tmp_path / "flags"
    (F / "ready").mkdir(parents=True)
    _row(F, "c3-foo-v2-20261031")
    _row(F, "c3-renamed", supersedes="c3-foo-v2-20261031")
    _row(F, "c3-chain", supersedes=["c3-renamed"])
    _row(F, "c3-orphan", supersedes="gone-v1-20261001")
    _row(F, "c3-bar-v1", lineage="bar")
    allrows = rf.rows(str(F))
    assert rf.lineage_of("c3-orphan", allrows) == "gone", "a superseded id whose row is gone still names the lineage"
    assert rf.lineage_of("c3-bar-v1", allrows) == "bar"
    assert rf.lineage_of("c3-foo-v2-20261031", allrows) == "c3-foo"


def test_supersedes_to_existing_row_joins_its_lineage(tmp_path):
    F = tmp_path / "flags"
    (F / "ready").mkdir(parents=True)
    _row(F, "c3-foo-v2-20261031")
    _row(F, "c3-renamed", supersedes="c3-foo-v2-20261031")
    _row(F, "c3-chain", supersedes=["c3-renamed"])
    allrows = rf.rows(str(F))
    assert rf.lineage_of("c3-renamed", allrows) == "c3-foo"
    assert rf.lineage_of("c3-chain", allrows) == "c3-foo", "supersedes chains follow to the root stem"


def test_park_at_three_and_escalation_file(tmp_path):
    F, pri = _flags(tmp_path)
    for rid, extra in (("c3-foo-v1-20261030", {}), ("c3-foo-v2-20261031", {}),
                       # explicit lineage beside supersedes: see test_supersedes_to_existing_row_joins_its_lineage (fixed 2026-11-01)
                       ("c3-renamed", {"supersedes": "c3-foo-v2-20261031", "lineage": "c3-foo"}), ("c3-bar-v1", {"lineage": "bar"})):
        _row(F, rid, rank=4, **extra)
    for rid in ("c3-foo-v1-20261030", "c3-foo-v2-20261031"):
        _fail(F, rid, f"gate refused {rid}")
    data = _build(F, pri)
    c3 = {r["id"]: r for r in data["workers"][GEN]["rows"]}
    assert c3["c3-renamed"]["lineage"] == "c3-foo" and c3["c3-renamed"]["lineage_fails"] == 2
    assert c3["c3-renamed"]["state"] == "needs-qualification" and not data["parked"]
    assert c3["c3-foo-v1-20261030"]["state"] == "blocked", "a FAIL with the launcher unchanged is the owner's fix task"
    for rid in ("c3-renamed", "c3-bar-v1"):
        _fail(F, rid, f"gate refused {rid}")
        rf.write_escalation(str(F), rid, rf.rows(str(F)))  # the keeper does this after record_fail
    data = _build(F, pri)
    c3 = {r["id"]: r for r in data["workers"][GEN]["rows"]}
    assert all(c3[i]["state"] == "parked" for i in ("c3-foo-v1-20261030", "c3-foo-v2-20261031", "c3-renamed"))
    assert c3["c3-bar-v1"]["state"] == "blocked" and c3["c3-bar-v1"]["lineage_fails"] == 1
    assert list(data["parked"]) == ["c3-foo"] and data["parked"]["c3-foo"]["worker"] == GEN
    md = bg.render(GEN, data)
    assert "- [parked] cpu rank=4 **c3-renamed**" in md and "parked=3" in md
    esc = (F / "operator-escalations" / "c3-foo.md").read_text()
    assert esc.count("\n- 20") == 3 and "PARKED NEEDS-OPERATOR" in esc and "Options:" in esc and "c3-renamed" in esc
    assert not (F / "operator-escalations" / "bar.md").exists(), "one failure never escalates"
    # lineage_reset re-admits
    d = json.loads((F / "ready" / "c3-renamed.json").read_text())
    d["lineage_reset"] = 3
    (F / "ready" / "c3-renamed.json").write_text(json.dumps(d))
    data = _build(F, pri)
    assert not data["parked"]
    assert {r["id"]: r["state"] for r in data["workers"][GEN]["rows"]}["c3-renamed"] == "needs-qualification", \
        "editing the row manifest (row sha) re-admits it for a dry run, like a launcher change"
    assert {r["id"]: r["state"] for r in data["workers"][GEN]["rows"]}["c3-foo-v1-20261030"] == "blocked", "untouched rows keep their FAIL"


def test_piloted_handoff_rows_move_to_handoff_backlog(tmp_path):
    F, pri = _flags(tmp_path)
    _row(F, "yarn-oolong-s1-v9-20261101", rank=2, handoff_task="handoffs/active/yarn-x.md:Y-9")
    (F / f"WORK-{GEN}-code.md").write_text(
        (F / f"WORK-{GEN}-code.md").read_text() + "- [L] handoffs/active/yarn-x.md:5 — **Y-1 — yarn inert**\n")
    reg = F / "handoff-sessions.json"
    reg.write_text(json.dumps({"sessions": {
        "yarn": {"handoff": "/workspace/handoffs/active/yarn-x.md", "status": "live", "row_patterns": ["yarn"]},
        "kpf": {"handoff": "handoffs/active/kpf.md", "status": "suspended", "handoff_rows": ["RTG-1"]},
        "old": {"handoff": "handoffs/active/old.md", "status": "done", "row_patterns": ["gen-"]}}}))
    data = bg.run_once(str(F), str(pri), str(F / KLOG), str(F), False)
    assert set(data["workers"]) == {GEN, "handoff-yarn", "handoff-kpf"}
    ids = lambda w: {r["id"] for r in data["workers"][w]["rows"]}
    assert "yarn-oolong-s1-v9-20261101" in ids("handoff-yarn")
    assert "yarn-oolong-s1-v9-20261101" not in ids(GEN)
    # handoff_rows join: inference_prep entries for RTG-1 (incl. a published row) leave the generalist
    assert {"kpf-r12", "kpf-r11", "gen-qualified"} <= ids("handoff-kpf")
    assert not ({"kpf-r12", "kpf-r11", "gen-qualified"} & ids(GEN))
    # a done pilot no longer captures rows
    assert "gen-blockedby" in ids(GEN)
    yb = (F / "BACKLOG-handoff-yarn.md").read_text()
    assert "Y-1 — yarn inert" in yb and "briefs/HANDOFF-yarn.md" in yb
    nb = (F / f"BACKLOG-{GEN}.md").read_text()
    assert "Y-1 — yarn inert" not in nb and "handoffs/active/yarn-x.md" in nb
    assert "Y-1" not in (F / f"WORK-{GEN}-code.md").read_text().split(bg.E_MARK)[0]


def test_no_registry_is_unchanged(tmp_path):
    F, pri = _flags(tmp_path)
    data = _build(F, pri)
    assert set(data["workers"]) == set(bg.WORKERS) == {GEN}


def test_withdrawal_marker_suppresses_prep_only_and_manifest_prep(tmp_path):
    F, pri = _flags(tmp_path)
    # kpf-r11 has only inference_prep; gen-qualified has both a row and
    # a prep entry. Both must stay absent after their exact marker appears.
    (F / "ready/kpf-r11.withdrawn").write_text("")
    (F / "ready/gen-qualified.withdrawn").write_text("")
    # A marker for a different ID must not suppress the live prep row.
    (F / "ready/kpf-r12-other.withdrawn").write_text("")
    data = _build(F, pri)
    ids = {r["id"] for w in data["workers"].values() for r in w["rows"]}
    assert "kpf-r11" not in ids
    assert "gen-qualified" not in ids
    assert "kpf-r12" in ids


def test_withdrawn_prep_is_absent_from_piloted_handoff(tmp_path):
    F, pri = _flags(tmp_path)
    (F / "handoff-sessions.json").write_text(json.dumps({"sessions": {"kpf": {
        "handoff": "handoffs/active/kpf.md", "status": "live", "handoff_rows": ["RTG-1"]}}}))
    (F / "ready/kpf-r11.withdrawn").write_text("")
    data = _build(F, pri)
    ids = {r["id"] for w in data["workers"].values() for r in w["rows"]}
    assert "kpf-r11" not in ids
    assert "kpf-r12" in ids
    assert "kpf-r12" in {r["id"] for r in data["workers"]["handoff-kpf"]["rows"]}


def test_prep_only_terminal_receipts_do_not_reappear_as_actionable(tmp_path):
    F, pri = _flags(tmp_path)
    (F / "grants/kpf-r11.ended").write_text("rc=70\n")
    (F / "filing-done/kpf-r12.FILED").write_text("{}")
    data = _build(F, pri)
    rows = {r["id"]: r for r in data["workers"][GEN]["rows"]}
    for rid in ("kpf-r11", "kpf-r12"):
        assert rows[rid]["state"] == "done"
        assert rows[rid]["tasks"] == []
