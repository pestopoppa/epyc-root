"""LOOP-58 mirror: publish refuses the legacy-migration placeholders unless the row is legacy-mapped."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import rowflow2 as r  # noqa: E402

BASE = {"id": "x-20261109", "owner": "ws58", "handoff_task": "t", "launcher": "/bin/true", "stop_file": "/tmp/x.stop", "cpus": "q0",
        "threads": 4, "gpu": "none", "quiet": False, "ram_gib": 1.0, "disk_gib": 1.0, "estimate_s": 600.0, "min_window_s": 0.0,
        "decision_rule": "rc == 0", "priority_rank": 1.0}


def errs(**kw):
    return r.validate({**BASE, **kw}, launcher_exists=lambda p: True)


def test_real_rule_admitted():
    assert errs() == []


def test_migrated_placeholder_refused():
    assert any("MIGRATED:" in e for e in errs(decision_rule="MIGRATED: decision_rule missing in legacy manifest; owner to fill"))


def test_migrated_placeholder_allowed_when_legacy():
    assert errs(decision_rule="MIGRATED: x", legacy={"regions": "q0", "shape": "quarter"}) == []


def test_result_needs_spec_cannot_enter_rowflow2():
    """rowflow2 specs have no result_path, so the placeholder path is refused as an unknown field."""
    assert any("unknown field result_path" in e for e in errs(result_path="/x/RESULT-NEEDS-SPEC.jsonl"))
