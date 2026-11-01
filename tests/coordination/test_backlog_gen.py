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
    # ordering: blocked first, then needs-launcher, ..., done last; rank inside a state
    states = [r["state"] for r in data["workers"]["ni"]["rows"]]
    assert states == sorted(states, key=bg.STATE_ORDER.__getitem__)
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
