"""Tests for scripts/coordination/backlog_row_check.py.

The tool exists because two measured failures cost real work on 2026-07-29: 10% of the
dispatch queue's `file.md:NNN` anchors were dead the same day it was written, and
reusable checklists / standing constraints were being served as dispatchable tasks.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from scripts.coordination import session_bus as bus

REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "brc", REPO_ROOT / "scripts" / "coordination" / "backlog_row_check.py")
brc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(brc)


@pytest.mark.parametrize("text", [
    "`seeding_legacy.py:~331` deprecated ComparativeResult path",
    "  Preserve   env override precedence  ",
    "**Promote the GPU driver scripts** into the repo",
    "MiXeD CaSe With_Underscores",
])
def test_claim_key_is_byte_identical_to_the_claim_verbs_key(text: str) -> None:
    """THE REGRESSION THIS FILE EXISTS FOR. The first draft normalised with `[*`_]`,
    which turned `seeding_legacy.py` into `seedinglegacy.py` — so the claim command the
    tool PRINTED would have taken a different lock than the row it screened. A failed
    operator-presented command is an agent defect by policy, not a typo."""
    assert bus._claim_key(brc.claim_key(text)) == bus._claim_key(text)


def test_search_key_ignores_markdown_but_keeps_underscores() -> None:
    """Search and identity are deliberately different: the queue's description column
    and the handoff body routinely differ only by `**`/backticks, so FINDING must ignore
    them — but the CLAIM key must not, or two spellings take two locks."""
    assert brc.search_key("**bold** and `code`") == brc.search_key("bold and code")
    assert "_" in brc.search_key("seeding_legacy.py")


def _md(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "handoffs" / "active"
    p.mkdir(parents=True, exist_ok=True)
    f = p / "sample.md"
    f.write_text(body, encoding="utf-8")
    return f


def test_a_closed_box_is_not_dispatchable(tmp_path: Path) -> None:
    f = _md(tmp_path, "## Tasks\n\n- [x] Already done\n")
    code, reasons = brc.classify(f, 3, "x", "Already done", "Tasks")
    assert code == 2 and "already CLOSED" in reasons[0]


def test_a_guarded_section_is_not_dispatchable_whatever_the_text_says(tmp_path: Path) -> None:
    """The guard wins even for text that reads like a perfectly ordinary task — that is
    the point of guarding a whole reusable checklist."""
    f = _md(tmp_path, "## Pickup Checklist\n\n> DO NOT DISPATCH these boxes.\n\n"
                      "- [ ] Check llama.cpp upstream for new CPU ukernel PRs\n")
    code, reasons = brc.classify(f, 5, "", "Check llama.cpp upstream for new CPU ukernel PRs",
                                 "Pickup Checklist")
    assert code == 2 and "DO-NOT-DISPATCH guard" in reasons[0]


def test_standing_constraint_text_is_caught_even_under_a_task_shaped_heading(
        tmp_path: Path) -> None:
    """The measured case: § "Outstanding Work" gives no signal at all, so heading-based
    screening cannot see it. Imperative + standing condition is the tell."""
    f = _md(tmp_path, "## Outstanding Work\n\n- [ ] Preserve env override precedence "
                      "whenever migrating consumers\n")
    code, reasons = brc.classify(
        f, 3, "", "Preserve env override precedence whenever migrating consumers", "Outstanding Work")
    assert code == 2
    assert "standing-constraint shaped" in reasons[0]


def test_an_imperative_WITHOUT_a_condition_stays_dispatchable_with_a_hint(
        tmp_path: Path) -> None:
    """The positive control, and the one that keeps this tool honest: "Keep X out of Y"
    can be a one-off cleanup. Marking real work undispatchable is the costlier error,
    so the verb alone is a HINT and never a refusal."""
    f = _md(tmp_path, "## Tasks\n\n- [ ] Keep the archive tidy\n")
    code, reasons = brc.classify(f, 3, "", "Keep the archive tidy", "Tasks")
    assert code == 0
    assert any("WEAK HINT" in r for r in reasons)


def test_a_plain_task_is_dispatchable(tmp_path: Path) -> None:
    f = _md(tmp_path, "## Tasks\n\n- [ ] Download ThinkPRM-1.5B and quantize to Q4_K_M\n")
    code, reasons = brc.classify(f, 3, "", "Download ThinkPRM-1.5B and quantize to Q4_K_M", "Tasks")
    assert code == 0 and reasons == ["reads as a dispatchable task"]


def test_an_operator_gated_row_is_flagged_but_not_refused(tmp_path: Path) -> None:
    """It may still be dispatchable — but the reader is told to confirm ownership rather
    than discovering mid-task that it is human-amendment-only."""
    f = _md(tmp_path, "## Tasks\n\n- [ ] Ratify P-GPU-1 (human-amendment-only)\n")
    code, reasons = brc.classify(f, 3, "", "Ratify P-GPU-1 (human-amendment-only)", "Tasks")
    assert code == 0
    assert any("human-amendment" in r for r in reasons)


def test_anchor_rot_reports_itself_rather_than_not_found(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    """A dead `file.md:NNN` must say ANCHOR ROT and point at --row. Reporting it as
    "not found" would read as "the task is gone" — the opposite conclusion."""
    _md(tmp_path, "## Tasks\n\nprose, not a checkbox\n")
    monkeypatch.setattr(brc, "HANDOFFS", tmp_path / "handoffs" / "active")

    assert brc.main(["--ref", "sample.md:3"]) == 3
    err = capsys.readouterr().err
    assert "ANCHOR ROT" in err and "--row" in err


def test_ambiguous_text_refuses_rather_than_picking(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    _md(tmp_path, "## Tasks\n\n- [ ] audit the thing\n- [ ] audit the thing twice\n")
    monkeypatch.setattr(brc, "HANDOFFS", tmp_path / "handoffs" / "active")

    assert brc.main(["--row", "audit the thing"]) == 4
    assert "AMBIGUOUS" in capsys.readouterr().err


def test_a_section_that_disclaims_reader_execution_warns_but_does_not_refuse(
        tmp_path: Path) -> None:
    """Measured 2026-07-29: stale-open-audit § "Recommendations (follow-up tasks — no
    checkbox flips on the audited handoffs)" holds six rows, FOUR directing work at
    other owners and TWO extending the audit itself. Two rows were claimed out of it
    before the disclaimer — which lives in the HEADING, not the row — was noticed.

    It must WARN, never refuse: refusing would have been wrong for the two rows that
    genuinely belong to the reader, and marking real work undispatchable is the
    costlier error."""
    f = _md(tmp_path, "## Recommendations (follow-up tasks — no checkbox flips on the "
                      "audited handoffs)\n\n- [ ] Re-anchor GEMV to its live tasks\n")
    code, reasons = brc.classify(f, 3, "", "Re-anchor GEMV to its live tasks",
                                 "Recommendations (follow-up tasks — no checkbox flips on the "
                                 "audited handoffs)")

    assert code == 0, "must stay dispatchable — the section mixes owners"
    assert any("OWNERSHIP" in r for r in reasons)
    assert any("verify it is yours" in r for r in reasons)


def test_an_ordinary_section_gets_no_ownership_warning(tmp_path: Path) -> None:
    """The positive control: a warning on every row is a warning nobody reads."""
    f = _md(tmp_path, "## Outstanding Tasks\n\n- [ ] Download ThinkPRM-1.5B and quantize\n")
    code, reasons = brc.classify(f, 3, "", "Download ThinkPRM-1.5B and quantize",
                                 "Outstanding Tasks")
    assert code == 0
    assert not any("OWNERSHIP" in r for r in reasons)


# ---------------------------------------------------------------------------
# CHILD-BOX BLOCKERS. The third measured failure: the dispatch queue derived its
# blocker column from PARENT boxes only, so rows whose block was recorded one
# indent down were served in the top-40 "fire at an idle main immediately" bench.
# ---------------------------------------------------------------------------

def _handoff(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "h.md"
    p.write_text(body, encoding="utf-8")
    return p


def _classify_row(path: Path, lineno: int) -> tuple[int, list[str]]:
    boxes = {n: (st, b, h) for n, st, b, h in brc._boxes(path)}
    st, b, h = boxes[lineno]
    return brc.classify(path, lineno, st, b, h)


def test_open_blocking_child_refuses_the_parent(tmp_path: Path) -> None:
    """The HG-3 shape, measured verbatim: a child box that says the row is blocked
    while the parent reads as ready."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] **HG-3 — Protected-action list** aligned with existing SafetyGate\n"
                 "  - [ ] **HG-3 is BLOCKED on HG-1, contrary to the dispatch queue.**\n")
    code, reasons = _classify_row(p, 2)
    assert code == 2
    assert "BLOCKED BY A CHILD BOX" in reasons[0]
    assert "h.md:3" in reasons[0]
    assert "still OPEN" in reasons[1]


def test_closed_blocking_child_still_refuses(tmp_path: Path) -> None:
    """The instrument-era shape: the prerequisite LANDED (`[x]` token authored) but its
    outcome — the operator signature — is still outstanding. A closed blocking child is
    not evidence the block cleared, and reading it that way re-serves the row."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] Record the instrument-era boundary for reward values\n"
                 "  - [x] **Pre-validated human-amendment token authored**: await operator signature\n")
    code, reasons = _classify_row(p, 2)
    assert code == 2
    assert "CLOSED" in reasons[1] and "not that the block cleared" in reasons[1]


def test_ordinary_children_do_not_refuse_the_parent(tmp_path: Path) -> None:
    """THE OVER-REFUSAL CONTROL. Most rows have children and almost none are blocked.
    A screen that refused any row with subtasks would be useless — and refusing real
    work is the exact failure this tool was built to avoid."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] Port the ~50-line Hermes SQLite reader\n"
                 "  - [ ] Write the reader\n"
                 "  - [x] Decide against the letta dependency\n")
    code, reasons = _classify_row(p, 2)
    assert code == 0, reasons


def test_a_blocked_sibling_does_not_block_this_row(tmp_path: Path) -> None:
    """SCOPE CONTROL. The walk must stop at the next same-indent box. Bleeding into the
    following row would refuse a dispatchable task because its NEIGHBOUR is blocked —
    turning a fix for under-refusal into a worse over-refusal."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] A genuinely dispatchable row\n"
                 "- [ ] A different row\n"
                 "  - [ ] BLOCKED on the operator\n")
    assert _classify_row(p, 2)[0] == 0, "the blocked NEIGHBOUR bled into this row"
    assert _classify_row(p, 3)[0] == 2, "the row that really owns that child was let through"


def test_the_walk_stops_at_the_next_heading(tmp_path: Path) -> None:
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] A dispatchable row\n"
                 "## Blocked work\n"
                 "  - [ ] await operator signature\n")
    assert _classify_row(p, 2)[0] == 0


@pytest.mark.parametrize("child", [
    "Count the tokens in each prompt",
    "Review the operator runbook for typos",
    "Add a blocked-state column to the dashboard",
])
def test_blocker_pattern_is_narrow_enough_to_miss_incidental_words(
        tmp_path: Path, child: str) -> None:
    """`token`, `operator` and `blocked`-as-a-noun appear constantly in this backlog.
    A loose pattern would refuse real work, so these must all stay dispatchable."""
    p = _handoff(tmp_path, f"## Tasks\n- [ ] A dispatchable row\n  - [ ] {child}\n")
    assert _classify_row(p, 2)[0] == 0, child


def test_closed_parent_still_wins_over_the_child_screen(tmp_path: Path) -> None:
    """Ordering: an already-closed row is reported as closed, not as blocked. The
    reader needs the actionable reason, and `- [x]` is the end of the story."""
    p = _handoff(tmp_path, "## Tasks\n- [ ] x\n".replace("- [ ] x", "- [x] Done already") + "  - [ ] BLOCKED on something\n")
    code, reasons = _classify_row(p, 2)
    assert code == 2 and "already CLOSED" in reasons[0]


def test_child_boxes_on_a_non_checkbox_line_returns_empty(tmp_path: Path) -> None:
    p = _handoff(tmp_path, "## Tasks\nnot a checkbox\n  - [ ] await operator signature\n")
    assert brc.child_boxes(p, 2) == []


def test_child_boxes_past_eof_is_not_an_error(tmp_path: Path) -> None:
    """Anchor rot points past the end of a shrunken file; that must not raise."""
    p = _handoff(tmp_path, "## Tasks\n- [ ] a row\n")
    assert brc.child_boxes(p, 9999) == []


def test_a_closed_child_that_records_a_RESOLVED_block_does_not_refuse(tmp_path: Path) -> None:
    """Measured false positive: `gpu-serving-tie-in-program.md:75` has the child
    "whisper is BLOCKED … ✅ RESOLVED-BY-DECISION 2026-07-29: operator chose W3".
    Closing that child WAS the resolution. Refusing here withholds ready work."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] P2-2 land the two-tenant set\n"
                 "  - [x] **whisper is BLOCKED** ✅ RESOLVED-BY-DECISION: operator chose W3 (defer)\n")
    assert _classify_row(p, 2)[0] == 0


def test_a_closed_child_merely_narrating_a_gate_does_not_refuse(tmp_path: Path) -> None:
    """Second measured false positive: "gated on" inside the prose of a DELIVERED
    protocol design (`gpu-serving-tie-in-program.md:138`). On a closed child only an
    outstanding-outcome phrasing counts, because closing usually means it was worked."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] P2-5j host-thread placement sweep\n"
                 "  - [x] **P2-5j protocol design** ✅ filed; the arms are gated on placement\n")
    assert _classify_row(p, 2)[0] == 0


def test_an_open_blocking_child_is_reported_before_a_closed_one(tmp_path: Path) -> None:
    """`reviewer-escalation-…:22` carries a closed child hedging "actionable when it
    unblocks" AND an open one stating "HG-3 is BLOCKED on HG-1, contrary to the
    dispatch queue". First-found surfaced the hedge and buried the citable fact."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] **HG-3 — Protected-action list**\n"
                 "  - [x] Scoping audit ✅ — corrected here so HG-3 is actionable when it unblocks\n"
                 "  - [ ] **HG-3 is BLOCKED on HG-1, contrary to the dispatch queue.**\n")
    code, reasons = _classify_row(p, 2)
    assert code == 2
    assert "h.md:4" in reasons[0] and "BLOCKED on HG-1" in reasons[0]
    assert "still OPEN" in reasons[1]
