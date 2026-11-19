"""rowflow2 mirror of the disk pause / HOLD-ADMISSIONS (operator 2026-11-07), with a negative control."""
from rf2 import rf, spec


def test_hold_blocks_grants_and_control_grants():
    s = [spec("a1")]
    held = rf.admit(s, [], 1_000_000.0, hold="HOLD-ADMISSIONS owner=op reason=x")
    assert held.grants == [] and "admissions held" in held.skipped["a1"]
    free = rf.admit(s, [], 1_000_000.0)
    assert [g.id for g in free.grants] == ["a1"]   # negative control: no hold, the same row is granted
