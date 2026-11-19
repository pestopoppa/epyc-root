"""P1 acceptance AC9 as amended 2026-11-07 (operator option B of P1-AC9-TARGET-CROWDING).

KPF-18 item 7 passes when it is on the knob/target tier of the COLLECTED evidence and the section's
`Shown n of N <tier>` line counts that tier's whole collected set -- even when the bounded budget
shows none of it. It fails when absent from the collected evidence or when the count line is
missing or disagrees with the collected count.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import p1_acceptance as acc  # noqa: E402
import loop_beliefs as lb  # noqa: E402


def _row(claim_id: str, tier: str = "target", text: str = "") -> dict:
    return {"claim_id": claim_id, "tier": tier, "source_kind": "kv-prefix-fork-measurement",
            "locator": "", "text": text, "value": 1.0, "linked_claim_ids": []}


def _col(rows: list[dict]) -> dict:
    return {"rows": rows, "flagged": {b: [] for b in lb.FLAG_BUCKETS}}


def _section(shown: int, total: int, knob: tuple[int, int] = (0, 0)) -> dict:
    return {"claims": [], "section": f"... Shown {knob[0]} of {knob[1]} knob, {shown} of {total} "
                                     "target, 0 of 0 lineup, ...; bounded at 16 claims"}


def test_unshown_but_counted_item7_passes():
    kpf = _row("clm_kpf18_item7", text="KPF-18 item 7 fork on/off")
    others = [_row(f"clm_hi_{i}") for i in range(63)]
    col = _col(others + [kpf])
    hits, valued = acc._shown_value_rows(col, _section(16, 64), acc.KPF_RE, item7=True)
    assert [h["claim_id"] for h in hits] == ["clm_kpf18_item7"] and valued == []
    ok, detail = acc._counted(col, _section(16, 64), hits)
    assert ok, detail
    assert "Shown 16 of 64 target" in detail


def test_absent_from_collected_evidence_fails():
    col = _col([_row(f"clm_hi_{i}") for i in range(5)])
    hits, _ = acc._shown_value_rows(col, _section(5, 5), acc.KPF_RE, item7=True)
    ok, detail = acc._counted(col, _section(5, 5), hits)
    assert not ok and "no claim" in detail


def test_count_line_mismatch_fails():
    kpf = _row("clm_kpf18_item7", text="KPF-18 item 7")
    col = _col([kpf, _row("clm_other")])
    ok, detail = acc._counted(col, _section(1, 1), [kpf])
    assert not ok and "MISMATCH" in detail


def test_missing_count_line_fails():
    kpf = _row("clm_kpf18_item7", text="KPF-18 item 7")
    ok, detail = acc._counted(_col([kpf]), {"claims": [], "section": ""}, [kpf])
    assert not ok and "no `Shown" in detail


def test_knob_tier_hit_is_checked_against_the_knob_count():
    kpf = _row("clm_kpf18_item7", tier="knob", text="KPF-18 item 7")
    col = _col([kpf, _row("clm_t")])
    ok, detail = acc._counted(col, _section(1, 1, knob=(0, 1)), [kpf])
    assert ok and "Shown 0 of 1 knob" in detail
