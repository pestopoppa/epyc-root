"""verdict_count reads the verdict field of the unified tick suffix (handoff standard decision 1)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import verdict_count as vc  # noqa: E402


def test_unified_verdict_field():
    line = "- [x] **INF-99-A** run the screen ✅ 2026-11-19 [belief: clm_u1] REJECT -2% decode"
    t = vc.parse_tick(line)
    assert t["form"] == "unified" and vc.verdict_of(t["verdict"]) == "REJECT"
    assert vc.TAG.search(line)
