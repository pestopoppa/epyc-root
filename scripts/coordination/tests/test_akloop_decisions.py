"""P6 decision-needed detector: one synthetic pipeline, every signal, per-owner filtering, package shape, read-only."""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "akloop"))
import decisions as D  # noqa: E402

NOW = time.time()


def iso(dt=0):
    return D.iso(NOW - dt)


def wj(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w"))


def wt(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(t)


@pytest.fixture()
def world(tmp_path):
    root, flags = tmp_path / "root", str(tmp_path / "flags")
    wt(root / "agents/akown.md", "## Inputs\n\n- Owned handoffs: `handoffs/active/ak.md`, `handoffs/active/ak2.md`.\n\n## Out\n")
    wt(root / "agents/other.md", "- Owned handoffs: `handoffs/active/oth.md`.\n")
    wt(root / "handoffs/active/holds.yaml", "holds:\n- id: h1\n  scope: loop-launch\n  handoffs:\n  - ak.md\n  reason: r\n")
    wj(f"{flags}/handoff-sessions.json", {"sessions": {"handoff-akown-sub": {"handoff": "handoffs/active/ak.md"}}})
    man = lambda rid, **k: wj(f"{flags}/ready/{rid}.json", {"id": rid, "owner": "akown", "result_path": f"{tmp_path}/{rid}.RESULT.json", **k})
    # parked row (lineage at 3), refusal-cap row (2), smoke repeat row, futility row, dead supersede, live row
    for rid in ("p-20261121", "c-20261121", "s-20261121", "f-20261121", "d-20261121", "ok-20261121"):
        man(rid)
    man("sup-20261121-r2", owner="akown-sub")           # owner alias via registry slug? (not in registry: other owner)
    for n, at in ((1, 5), (2, 4)):
        wj(f"{flags}/dryrun/c-20261121/FAIL-{n}.json", {"at": iso(at * 60), "kind": "launch", "fix_task": f"fix c {n}"})
        wj(f"{flags}/dryrun/s-20261121/FAIL-{n}.json", {"at": iso(at * 60), "fix_task": f"smoke {n}"})
    for n in (1, 2, 3):
        wj(f"{flags}/dryrun/p-20261121/FAIL-{n}.json", {"at": iso(n * 60), "kind": "launch", "fix_task": f"fix p {n}"})
    wj(f"{tmp_path}/f-20261121.RESULT.json", {"verdict": "FUTILITY_IDENTITY"})
    wt(f"{flags}/grants/f-20261121.ended", f"rc=0 at={iso(3600)} reason=complete\n")
    wt(f"{flags}/grants/d-20261121.ended", f"rc=75 reason=superseded-by:ghost-20261121_(free text) at={iso(3600)}\n")
    boxes = {
        "AK-1": {"file": "handoffs/active/ak.md", "line": 10, "state": "open", "gate": ["X"], "gate_open": True, "gate_unknown": [], "text": "t", "holds": ["h1"]},
        "AK-2": {"file": "handoffs/active/ak2.md", "line": 20, "state": "open", "gate": ["a b"], "gate_open": False, "gate_unknown": ["a b"], "text": "t", "holds": []},
        "OT-1": {"file": "handoffs/active/oth.md", "line": 5, "state": "open", "gate": ["Y"], "gate_open": True, "gate_unknown": [], "text": "t", "holds": []},
        "AK-3": {"file": "handoffs/active/ak.md", "line": 30, "state": "done", "gate": ["Z"], "gate_open": True, "gate_unknown": [], "text": "t", "holds": []},
    }
    holds = [{"id": "h1", "scope": "loop-launch", "handoffs": ["ak.md"], "reason": "r", "since": "2026"},
             {"id": "h2", "scope": "all-rows", "handoffs": ["oth.md"], "reason": "o"}]

    def status(rid):
        n = len(list(__import__("glob").glob(f"{flags}/dryrun/{rid}/FAIL-*.json")))
        return {"id": rid, "state": "parked" if rid.startswith("p-") else "grantable", "lineage": D.stem(rid), "lineage_fails": n if rid[0] in "pc" else 0,
                "reason": "parked: 3 refusals"}
    return dict(root=str(root), flags=flags, boxes=boxes, holds=holds, status_fn=status, now=NOW)


def run(world, owner="akown", **kw):
    return D.detect(owner, since_h=72, **{**world, **kw})


def by_kind(rep):
    out = {}
    for e in rep["events"]:
        out.setdefault(e["kind"], []).append(e)
    return out


def test_every_signal_detected_for_owner(world):
    k = by_kind(run(world))
    assert [e["subject"] for e in k["gate-open"]] == ["AK-1"]            # AK-3 done, OT-1 not this owner's
    assert [e["subject"] for e in k["gate-unknown"]] == ["AK-2"]
    assert [e["subject"] for e in k["hold-hit"]] == ["h1"]
    assert k["row-parked"][0]["facts"]["row"] == "p-20261121"
    assert k["refusal-cap"][0]["facts"]["row"] == "c-20261121" and k["refusal-cap"][0]["facts"]["of"] == 3
    assert k["smoke-fail-repeat"][0]["facts"]["smoke_fails"] == 2
    assert k["futility"][0]["facts"]["verdict"] == "FUTILITY_IDENTITY"
    assert k["supersede-dead-end"][0]["facts"]["chain"] == ["d-20261121", "ghost-20261121"]


def test_every_event_traces_to_a_concrete_signal(world):
    for e in run(world)["events"]:
        assert e["evidence"], e["kind"]
        assert all(r["path"] and (r.get("line") or r.get("record") or r.get("note")) for r in e["evidence"]), e["kind"]
    gate = by_kind(run(world))["gate-open"][0]["evidence"][0]
    assert (gate["path"], gate["line"]) == ("handoffs/active/ak.md", 10)


def test_per_owner_filtering(world):
    rep = run(world, owner="other")
    assert [e["kind"] for e in rep["events"]] == ["gate-open", "hold-hit"]
    assert {e["subject"] for e in rep["events"]} == {"OT-1", "h2"}
    assert run(world, owner="nobody")["events"] == []


def test_package_shape_three_options_recommended_first(world):
    for e in run(world)["events"]:
        p = e["package"]
        assert len(p["options"]) == 3 and p["multiSelect"] is False
        assert p["options"][0]["label"].endswith("(Recommended)")
        assert not any("(Recommended)" in o["label"] for o in p["options"][1:])
        assert all(o["description"] for o in p["options"]) and p["question"] and p["context"]
        json.dumps(p)


def test_futility_with_successor_is_not_a_decision(world):
    wj(f"{world['flags']}/ready/f-20261121-r2.json", {"id": "f-20261121-r2", "owner": "akown", "supersedes": ["f-20261121"]})
    assert "futility" not in by_kind(run(world))


def test_smoke_repeat_cleared_by_later_pass(world):
    wj(f"{world['flags']}/dryrun/s-20261121/PASS.json", {"passed_at": iso(0)})
    assert "smoke-fail-repeat" not in by_kind(run(world))


def test_old_events_outside_window_ignored(world):
    wt(f"{world['flags']}/grants/f-20261121.ended", f"rc=0 at={iso(10 * 86400)} reason=complete\n")
    assert "futility" not in by_kind(run(world))


def test_supersede_continued_by_live_lineage_row_is_not_dead(world):
    man = f"{world['flags']}/ready/d-20261121-r9.json"
    wj(man, {"id": "d-20261121-r9", "owner": "akown"})
    assert "supersede-dead-end" not in by_kind(run(world))


def test_event_ids_stable_and_read_only(world):
    def snap():
        return sorted((dp, f, os.path.getmtime(os.path.join(dp, f))) for base in (world["flags"], world["root"]) for dp, _, fs in os.walk(base) for f in fs)
    before = snap()
    a, b = run(world), run(world)
    assert [e["event_id"] for e in a["events"]] == [e["event_id"] for e in b["events"]]
    assert len({e["event_id"] for e in a["events"]}) == len(a["events"])
    assert snap() == before and a["never_sends"] is True


def test_markdown_and_cli_render(world, capsys):
    md = D.render_md(run(world))
    assert "# Decisions needed: akown" in md and "handoffs/active/ak.md:10" in md and "(Recommended)" in md
    for k in D.KINDS:
        assert k in md
