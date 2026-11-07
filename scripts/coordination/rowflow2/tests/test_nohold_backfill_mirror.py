"""rowflow2 mirror of the 2026-11-07 keeper fixes (operator "Approve + deploy"): exact-name operator holds and
backfill-if-fits with NO reservation when the top row's start is unknown / expired / beyond the longest busy window."""
import os

from rf2 import rf, spec

NOW = 1_000_000.0
H = 3600.0
Q01 = frozenset(range(0, 48))


def lsa(end):
    return [rf.Grant("lsa-dense", frozenset(range(0, 24)), start=NOW - H, end=end),
            rf.Grant("lsa-pca", frozenset(range(24, 48)), start=NOW - H, end=end)]


def wide():
    return spec("c7-wide", cpus="0-95", rank=10, est=1.5 * H)


def test_short_rows_backfill_before_the_wide_start():
    p = rf.admit([wide(), spec("q2", cpus="q2", rank=50, est=2 * H)], lsa(NOW + 10 * H), NOW)
    assert [g.id for g in p.grants] == ["q2"] and p.hold and p.hold.id == "c7-wide"


def test_long_row_waits_while_the_start_is_known():
    p = rf.admit([wide(), spec("q2-long", cpus="q2", rank=50, est=20 * H)], lsa(NOW + 10 * H), NOW)
    assert p.grants == []


def test_expired_or_unknown_end_reserves_nothing_and_control():
    # parse_grant maps a missing/unparsable end to `now`: unknown and expired look the same - neither may block
    p = rf.admit([wide(), spec("q2-long", cpus="q2", rank=50, est=20 * H)], lsa(NOW), NOW)
    assert [g.id for g in p.grants] == ["q2-long"] and p.hold is None
    old = rf.NO_RESERVE_UNKNOWN
    rf.NO_RESERVE_UNKNOWN = False   # negative control: the pre-fix hold (eta = now) blocks every lower row
    try:
        p = rf.admit([wide(), spec("q2-long", cpus="q2", rank=50, est=20 * H)], lsa(NOW), NOW)
    finally:
        rf.NO_RESERVE_UNKNOWN = old
    assert p.grants == []


def test_operator_hold_names(tmp_path):
    f = str(tmp_path)
    open(os.path.join(f, "HOLD-ADMISSIONS"), "w").close()
    os.symlink("HOLD-ADMISSIONS", os.path.join(f, "HOLD_ADMISSIONS.lifted-symlink"))
    open(os.path.join(f, "HOLD_X.disabled"), "w").close()
    os.remove(os.path.join(f, "HOLD-ADMISSIONS"))
    assert rf.operator_holds(f) == []
    why, _ = rf.admission_hold(f, free_gib=400.0)
    assert why is None
    open(os.path.join(f, "HOLD_EMERGENCY"), "w").close()
    why, _ = rf.admission_hold(f, free_gib=400.0)
    assert why and "HOLD_EMERGENCY" in why
