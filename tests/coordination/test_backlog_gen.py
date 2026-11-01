"""backlog_gen.py: fixture READY rows + keeper log lines -> BACKLOG-<worker>.md states and unblock linkage."""
import json
import subprocess
import sys
from pathlib import Path

from scripts.coordination import backlog_gen as bg

SCRIPT = Path(__file__).parents[2] / "scripts/coordination/backlog_gen.py"


def _flags(tmp_path: Path):
    F = tmp_path / "flags"
    for d in ("ready", "grants", "filing-done", "ready/armed"):
        (F / d).mkdir(parents=True)
    receipt = tmp_path / "QUAL-ok.json"
    receipt.write_text("{}")

    def ready(rid, owner, **kw):
        d = {"id": rid, "owner": owner, "priority_rank": kw.pop("rank", 5), "regions": kw.pop("regions", "any-cpu-quarter"),
             "schema": kw.pop("schema", "epyc.ready.v2"), "hold": kw.pop("hold", None)}
        d.update(kw)
        (F / "ready" / f"{rid}.json").write_text(json.dumps(d))

    ready("ni-qualified", "codex-ni", rank=1, qualification={"receipt": str(receipt)})
    ready("ni-needsqual", "codex-ni", rank=2)
    ready("ni-held", "codex-ni", rank=3, hold="q3 patch unverified")
    ready("ni-skipped", "codex-ni", rank=4, regions="mi210_0,184-191")
    ready("ni-oldschema", "codex-ni", rank=6, schema=None)
    ready("ni-running", "codex-ni", rank=7, qualification={"receipt": str(receipt)})
    (F / "grants" / "ni-running.grant").write_text("")
    ready("ni-done", "codex-ni", rank=8)
    (F / "grants" / "ni-done.ended").write_text("")
    ready("ni-withdrawn", "codex-ni", rank=9)
    (F / "ready" / "ni-withdrawn.withdrawn").write_text("")
    ready("c3-qualified-after-skip", "codex3", rank=1, qualification={"receipt": str(receipt)})
    ready("rf-row", "codex-refactor-01a16fc3", rank=1, blocked_by=["port 8099 collides with the hub"])

    (F / "ws58-calendar-keeper.log").write_text("\n".join([
        "2026-11-01T12:00:00Z READY-SKIP qual-failed " + str(F / "ready/ni-skipped.json") + ": qual:row expected exactly one 18-cell record",
        "2026-11-01T12:00:01Z READY-SKIP c3-qualified-after-skip: hold=old (left in place; the worker fixes or withdraws it)",
        "2026-11-01T12:10:00Z READY-QUAL " + str(F / "ready/c3-qualified-after-skip.json") + ": " + str(receipt),
        "2026-11-01T12:11:00Z IDLE-ALARM free for >=2 checks: q3",
        "2026-11-01T12:12:00Z READY-RESULT ni-running: QUEUED pid 1 | OK",
    ]) + "\n")
    (F / "WORK-ni-code.md").write_text("\n".join([
        bg.B_MARK, "## old section", bg.E_MARK, "# ni: code queue",
        "- [S] handoffs/active/a.md:10 — **FIX-1 — repair the 18-cell record writer** [unblocks: ni-skipped]",
        "- [M] handoffs/active/b.md:20 — **OTHER-2 — unrelated refactor**", ""]))
    (F / "WORK-codex3-code.md").write_text("# codex3: code queue\n- [S] handoffs/active/c.md:1 — **C3-1 — thing**\n")
    (F / "unblocks.json").write_text(json.dumps({"migrate ni-oldschema manifest to epyc.ready.v2": ["ni-oldschema"]}))
    pri = {"schema": "backlog_priority.v1", "rows": {
        "INF-9": {"kind": "non-inference", "tier": 1, "rank": 3, "basis": "T1 ... write the KPF launcher", "unblocks": ["RTG-1"], "blocker": ""},
        "RTG-1": {"kind": "inference-prep", "tier": 0, "rank": 1, "basis": "x", "unblocks": [], "blocker": ""}},
        "inference_prep": [
            {"rank": 1, "filler": "kpf-r12", "row": "RTG-1", "kind": "inference-prep", "owner": "Codex NI / KPF18", "blocker": "missing launcher"},
            {"rank": 2, "filler": "kpf-r11", "row": "RTG-1", "kind": "inference-prep", "owner": "codex-ni-01a16d6b", "blocker": "harness fix: rc1 framing_pass=false"},
            {"rank": 3, "filler": "ni-qualified", "row": "RTG-1", "kind": "inference-prep", "owner": "codex-ni", "blocker": "harness fix"}]}
    (tmp_path / "backlog-priority.json").write_text(json.dumps(pri))
    return F, tmp_path / "backlog-priority.json"


def test_states_and_linkage(tmp_path):
    F, pri = _flags(tmp_path)
    data = bg.build(str(F), str(pri), str(F / "ws58-calendar-keeper.log"))
    ni = {r["id"]: r for r in data["workers"]["ni"]["rows"]}
    assert ni["ni-qualified"]["state"] == "qualified-armed"
    assert ni["ni-needsqual"]["state"] == "needs-qualification"
    assert ni["ni-held"]["state"] == "blocked" and ni["ni-held"]["reasons"][0].startswith("hold:")
    assert ni["ni-skipped"]["state"] == "blocked" and ni["ni-skipped"]["lane"] == "gpu"
    assert any("FIX-1" in t for t in ni["ni-skipped"]["tasks"]), "WORK line with [unblocks:] must attach"
    assert any("migrate ni-oldschema" in t for t in ni["ni-oldschema"]["tasks"]), "unblocks.json must attach"
    assert ni["ni-running"]["state"] == "running"
    assert ni["ni-done"]["state"] == "done"
    assert "ni-withdrawn" not in ni
    assert ni["kpf-r12"]["state"] == "needs-launcher" and any("INF-9" in t for t in ni["kpf-r12"]["tasks"])
    assert ni["kpf-r11"]["state"] == "blocked" and ni["kpf-r11"]["reasons"] == ["harness fix: rc1 framing_pass=false"]
    assert ni["ni-qualified"]["row"] == "RTG-1", "READY id joins the handoff row through inference_prep.filler"
    # the keeper's later READY-QUAL supersedes the earlier READY-SKIP
    c3 = {r["id"]: r for r in data["workers"]["codex3"]["rows"]}
    assert c3["c3-qualified-after-skip"]["state"] == "qualified-armed"
    rf = {r["id"]: r for r in data["workers"]["refactor"]["rows"]}
    assert rf["rf-row"]["state"] == "blocked" and "port 8099" in rf["rf-row"]["reasons"][0]
    # ordering (rule 1): advanceable rows first, starved-lane rows first among them; then parked/armed/running/done
    rows = data["workers"]["ni"]["rows"]
    adv = [r for r in rows if r["state"] in bg.ADVANCEABLE]
    assert rows[:len(adv)] == adv
    rest = [r["state"] for r in rows[len(adv):]]
    assert rest == sorted(rest, key=bg.STATE_ORDER.__getitem__)
    assert data["workers"]["ni"]["qual"] == {"cpu": 1, "gpu": 0, "host": 0}
    md = bg.render("ni", data)
    assert "[FLOOR] CPU: 1" in md and "[FLOOR] GPU: 0" in md
    assert "- [blocked] gpu rank=4 **ni-skipped**" in md
    assert "OTHER-2" in md, "non-inference tasks not linked to a row are still listed"
    assert md.index("ni-skipped") < md.index("OTHER-2")


def test_write_and_dry_run_modes(tmp_path):
    F, pri = _flags(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--flags", str(F), "--priority", str(pri), "--out", str(out), "--dry-run"],
                       capture_output=True, text=True, check=True)
    assert "BACKLOG-ni.md" in r.stdout and not list(out.iterdir()), "dry run writes nothing"
    assert "## old section" in (F / "WORK-ni-code.md").read_text()
    subprocess.run([sys.executable, "-I", str(SCRIPT), "--flags", str(F), "--priority", str(pri), "--out", str(out)],
                   capture_output=True, text=True, check=True)
    assert sorted(p.name for p in out.iterdir()) == ["BACKLOG-codex3.md", "BACKLOG-ni.md", "BACKLOG-refactor.md"]
    w = (F / "WORK-ni-code.md").read_text()
    assert "## old section" not in w and "BACKLOG-ni.md" in w and "[BLOCKED] gpu rank=4 ni-skipped" in w
    assert "FIX-1" in w, "existing code-queue lines are preserved"
    assert (out / "BACKLOG-refactor.md").read_text().count("rf-row") == 1


def test_flow_scoreboard_counts(tmp_path):
    import datetime as dt
    from scripts.coordination import flow_scoreboard as fs
    F, pri = _flags(tmp_path)
    now = dt.datetime(2026, 11, 1, 13, 0, tzinfo=dt.timezone.utc)
    rows, state = fs.compute(str(F), str(pri), str(F / "ws58-calendar-keeper.log"), {}, now)
    assert rows["codex3"]["armed"] == 1 and rows["ni"]["armed"] == 0
    assert rows["ni"]["blocked_rows"] >= 5 and rows["ni"]["closed"] == 0
    assert rows["ni"]["idle_h"] == round(120 / 3600, 2), "one cpu IDLE-ALARM charged to a worker with a blocked cpu row"
    assert rows["codex3"]["idle_h"] == 0
    # a blocked row that disappears counts as a closed blocking task
    (F / "ready" / "ni-held.json").unlink()
    rows2, _ = fs.compute(str(F), str(pri), str(F / "ws58-calendar-keeper.log"), state, now)
    assert rows2["ni"]["closed"] == 1
    assert "| codex3 | 1 |" in fs.render(rows2, now)


def test_starved_lane_first(tmp_path):
    F, pri = _flags(tmp_path)
    # give ni a second qualified CPU row: CPU is at floor, GPU (0) is starved
    receipt = tmp_path / "QUAL-ok.json"
    (F / "ready" / "ni-qualified2.json").write_text(json.dumps(
        {"id": "ni-qualified2", "owner": "codex-ni", "priority_rank": 1, "regions": "any-cpu-quarter",
         "schema": "epyc.ready.v2", "qualification": {"receipt": str(receipt)}}))
    data = bg.build(str(F), str(pri), str(F / "ws58-calendar-keeper.log"))
    ni = data["workers"]["ni"]
    assert ni["starved"] == ["gpu"]
    assert ni["rows"][0]["id"] == "ni-skipped", "starved-lane (gpu) row beats higher-priority cpu rows"
    assert [r["id"] for r in ni["rows"][1:3]] == ["kpf-r12", "kpf-r11"], "then global priority (rank 1, 2)"


def test_lineage_stem_and_supersedes():
    assert bg.id_stem("codex-hil15-s0-micron-v12-20261031") == "codex-hil15-s0-micron"
    assert bg.id_stem("ct21-rearm-r1-20261028") == "ct21"
    assert bg.id_stem("kpf-r12") == "kpf"


def _fail_lines(F, ids):
    with open(F / "ws58-calendar-keeper.log", "a") as f:
        for i, rid in enumerate(ids):
            f.write(f"2026-11-01T13:0{i}:00Z QUAL-FAILURE qual-failed {F}/ready/{rid}.json: gate {i} refused\n")


def test_park_at_three_and_escalation_file(tmp_path):
    F, pri = _flags(tmp_path)
    for rid, extra in (("c3-foo-v1-20261030", {}), ("c3-foo-v2-20261031", {}),
                       ("c3-renamed", {"supersedes": "c3-foo-v2-20261031"}), ("c3-bar-v1", {"lineage": "bar"})):
        d = {"id": rid, "owner": "codex3", "priority_rank": 4, "regions": "any-cpu-quarter", "schema": "epyc.ready.v2"}
        d.update(extra)
        (F / "ready" / f"{rid}.json").write_text(json.dumps(d))
    _fail_lines(F, ["c3-foo-v1-20261030", "c3-foo-v2-20261031"])
    data = bg.build(str(F), str(pri), str(F / "ws58-calendar-keeper.log"))
    c3 = {r["id"]: r for r in data["workers"]["codex3"]["rows"]}
    assert c3["c3-renamed"]["lineage"] == "c3-foo" and c3["c3-renamed"]["lineage_fails"] == 2
    assert c3["c3-renamed"]["state"] == "needs-qualification" and not data["parked"]
    _fail_lines(F, ["c3-renamed", "c3-bar-v1"])
    data = bg.build(str(F), str(pri), str(F / "ws58-calendar-keeper.log"))
    c3 = {r["id"]: r for r in data["workers"]["codex3"]["rows"]}
    assert all(c3[i]["state"] == "parked" for i in ("c3-foo-v1-20261030", "c3-foo-v2-20261031", "c3-renamed"))
    assert c3["c3-bar-v1"]["state"] == "blocked" and c3["c3-bar-v1"]["lineage_fails"] == 1
    assert list(data["parked"]) == ["c3-foo"]
    assert "PARKED NEEDS-OPERATOR" in bg.render("codex3", data)
    out = tmp_path / "out"
    out.mkdir()
    bg.run_once(str(F), str(pri), str(F / "ws58-calendar-keeper.log"), str(out), dry_run=False)
    esc = (F / "operator-escalations" / "c3-foo.md").read_text()
    assert esc.count("\n- 2026-11-01T13") == 3 and "## Options" in esc and "c3-renamed" in esc
    # lineage_reset re-admits
    d = json.loads((F / "ready" / "c3-renamed.json").read_text())
    d["lineage_reset"] = 3
    (F / "ready" / "c3-renamed.json").write_text(json.dumps(d))
    data = bg.build(str(F), str(pri), str(F / "ws58-calendar-keeper.log"))
    assert not data["parked"]


def test_failures_counted_beyond_state_window(tmp_path):
    log = tmp_path / "k.log"
    log.write_text("2026-11-01T00:00:00Z QUAL-FAILURE qual-failed /x/ready/old-v1.json: early refusal\n"
                   + "2026-11-01T00:00:01Z IDLE-ALARM free: q1\n" * 10)
    st = bg.fold_keeper_log(str(log), tail=5)
    assert st["fails"]["old-v1"][0][1] == "early refusal"


def test_schema_rechecks_are_not_qualification_runs(tmp_path):
    """Negative case from the live parakeet false positive: every-2-min legacy-schema re-checks never ran the qualifier."""
    lines = []
    for i, rid in enumerate(["codex3-cs8-stt5-validation-parakeet-20261030", "codex3-cs8-stt5-validation-parakeet-r2-20261030",
                             "codex3-cs8-stt5-validation-parakeet-r3-20261030"]):
        for k in range(5):
            lines.append(f"2026-11-01T11:{10+i}:{k:02d}Z READY-SKIP qual-failed /f/ready/{rid}.json: qual:manifest schema != epyc.ready.v2")
    lines.append("2026-11-01T12:00:00Z READY-SKIP qual-failed /f/ready/x-r1.json: held")
    lines.append("2026-11-01T12:00:01Z READY-SKIP qual-failed /f/ready/x-r1.json: qual:qualification nonce already issued for id")
    log = tmp_path / "k.log"
    log.write_text("\n".join(lines) + "\n")
    for tail in (6000, 3):
        assert bg.fold_keeper_log(str(log), tail=tail)["fails"] == {}
    log.write_text("2026-11-01T12:00:00Z READY-SKIP qual-failed /f/ready/y-r1.json: qual-run-rc=2; see log\n"
                   "2026-11-01T12:01:00Z READY-SKIP y-r2: hold=keeper qualification failed rc70: launcher replaced\n"
                   "2026-11-01T12:02:00Z READY-SKIP qual-failed /f/ready/y-r3.json: qual:row y-r3: expected exactly one record\n")
    assert sorted(bg.fold_keeper_log(str(log), tail=1)["fails"]) == ["y-r1", "y-r2", "y-r3"]


def test_piloted_handoff_rows_move_to_handoff_backlog(tmp_path):
    F, pri = _flags(tmp_path)
    (F / "ready" / "yarn-oolong-s1-v9-20261101.json").write_text(json.dumps(
        {"id": "yarn-oolong-s1-v9-20261101", "owner": "codex-refactor-01a16fc3", "priority_rank": 2,
         "regions": "any-cpu-quarter", "schema": "epyc.ready.v2"}))
    (F / "WORK-ni-code.md").write_text(
        (F / "WORK-ni-code.md").read_text() + "- [L] handoffs/active/yarn-x.md:5 — **Y-1 — yarn inert**\n")
    reg = F / "handoff-sessions.json"
    reg.write_text(json.dumps({"sessions": {
        "yarn": {"handoff": "/workspace/handoffs/active/yarn-x.md", "status": "live", "row_patterns": ["yarn"]},
        "kpf": {"handoff": "handoffs/active/kpf.md", "status": "suspended", "handoff_rows": ["RTG-1"]},
        "old": {"handoff": "handoffs/active/old.md", "status": "done", "row_patterns": ["ni-"]}}}))
    data = bg.run_once(str(F), str(pri), str(F / "ws58-calendar-keeper.log"), str(F), False)
    ids = lambda w: {r["id"] for r in data["workers"][w]["rows"]}
    assert "yarn-oolong-s1-v9-20261101" in ids("handoff-yarn")
    assert "yarn-oolong-s1-v9-20261101" not in ids("refactor")
    # handoff_rows join: inference_prep entries for RTG-1 (incl. a READY manifest) leave the generalists
    assert {"kpf-r12", "kpf-r11", "ni-qualified"} <= ids("handoff-kpf")
    assert not ({"kpf-r12", "kpf-r11", "ni-qualified"} & ids("ni"))
    # a done pilot no longer captures rows
    assert "ni-held" in ids("ni")
    yb = (F / "BACKLOG-handoff-yarn.md").read_text()
    assert "Y-1 — yarn inert" in yb and "briefs/HANDOFF-yarn.md" in yb
    nb = (F / "BACKLOG-ni.md").read_text()
    assert "Y-1 — yarn inert" not in nb and "handoffs/active/yarn-x.md" in nb
    assert "Y-1" not in (F / "WORK-ni-code.md").read_text().split(bg.E_MARK)[0]


def test_no_registry_is_unchanged(tmp_path):
    F, pri = _flags(tmp_path)
    data = bg.build(str(F), str(pri), str(F / "ws58-calendar-keeper.log"))
    assert set(data["workers"]) == set(bg.WORKERS)
