#!/usr/bin/env python3
"""F4 (AK audit B4): holds keyed by (session, scope), admitted by the row's owner; registry gates migrate to holds.yaml."""
import json
import os
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
sys.path.insert(0, os.path.dirname(_TESTS))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
import migrate_operator_gates_to_holds as mig  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo, flags = tmp_path / "repo", tmp_path / "flags"
    (repo / "handoffs" / "active").mkdir(parents=True)
    flags.mkdir()
    (flags / "handoff-sessions.json").write_text(json.dumps({"operator_gated_row_prefixes": [], "sessions": {}}))
    monkeypatch.setattr(pr, "REPO", str(repo))
    return repo, str(flags)


def holds(repo, text):
    (repo / "handoffs" / "active" / "holds.yaml").write_text(text)


HOLD = "holds:\n  - id: H-AKAGG\n    sessions: [akagg]\n    handoffs: [autokernel-agg.md]\n    scope: loop-launch\n    reason: AK loop paused\n"


def test_other_owner_in_held_handoff_published(env):
    repo, flags = env
    holds(repo, HOLD)
    pr.check_operator_gate({"id": "ak-r1", "owner": "autokernel", "handoff_task": "autokernel-agg.md:T1"}, flags)


def test_held_owner_refused_naming_hold(env):
    repo, flags = env
    holds(repo, HOLD)
    with pytest.raises(rf.Refused, match=r"hold 'H-AKAGG' \(scope loop-launch"):
        pr.check_operator_gate({"id": "ak-r1", "owner": "akagg", "handoff_task": "autokernel-agg.md:T1"}, flags)


def test_held_owner_refused_even_outside_handoff(env):
    repo, flags = env
    holds(repo, HOLD)
    with pytest.raises(rf.Refused, match="owner 'akagg' is held"):
        pr.check_operator_gate({"id": "x-r1", "owner": "akagg", "handoff_task": "other.md"}, flags)


def test_all_rows_scope_refuses_any_owner(env):
    repo, flags = env
    holds(repo, HOLD.replace("loop-launch", "all-rows"))
    with pytest.raises(rf.Refused, match="scope all-rows"):
        pr.check_operator_gate({"id": "ak-r1", "owner": "autokernel", "handoff_task": "autokernel-agg.md:T1"}, flags)


def test_release_by_hold_id(env):
    repo, flags = env
    holds(repo, HOLD)
    d = os.path.join(flags, "operator-ratify")
    os.makedirs(d)
    json.dump({"slug": "H-AKAGG", "by": "operator", "at": "x", "reason": "go", "rows": ["ak-"]},
              open(os.path.join(d, "H-AKAGG.json"), "w"))
    pr.check_operator_gate({"id": "ak-r1", "owner": "akagg", "handoff_task": "autokernel-agg.md:T1"}, flags)


def test_registry_gate_is_loop_launch_view(env):
    repo, flags = env
    reg = {"sessions": {"akagg": {"handoff": "handoffs/active/autokernel-agg.md", "operator_gate": {"reason": "r", "since": "s"}}}}
    open(os.path.join(flags, "handoff-sessions.json"), "w").write(json.dumps(reg))
    pr.check_operator_gate({"id": "ak-r1", "owner": "autokernel", "handoff_task": "autokernel-agg.md:T1"}, flags)
    with pytest.raises(rf.Refused, match="hold 'akagg'"):
        pr.check_operator_gate({"id": "ak-r1", "owner": "akagg", "handoff_task": "autokernel-agg.md:T1"}, flags)


def test_migration_write_once(env, tmp_path):
    repo, flags = env
    reg = {"sessions": {"akagg": {"handoff": "handoffs/active/autokernel-agg.md", "operator_gate": {"reason": "r", "since": "s"}},
                        "free": {"handoff": "handoffs/active/x.md"}}}
    open(os.path.join(flags, "handoff-sessions.json"), "w").write(json.dumps(reg))
    target = str(repo / "handoffs" / "active" / "holds.yaml")
    assert mig.main(["--flags", flags, "--holds", target, "--write"]) == 0
    hs = pr.load_holds(str(repo))
    assert [(h["id"], h["scope"]) for h in hs] == [("akagg", "loop-launch")]
    assert {"akagg", "autokernel-agg.md"} <= hs[0]["targets"]
    assert mig.main(["--flags", flags, "--holds", target, "--write"]) == 3


def test_box_index_reads_same_file(env):
    repo, flags = env
    holds(repo, HOLD)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_TESTS)), "handoffs"))
    import box_index
    from pathlib import Path
    assert [h["id"] for h in box_index.load_holds(Path(repo))] == ["H-AKAGG"]


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/coordination/tests/test_publish_row_holds_scope.py -q")
