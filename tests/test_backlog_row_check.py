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


# ---------------------------------------------------------------------------
# PROHIBITIONS. A fourth measured failure, and the first one this tool had
# already been built to prevent and still missed.
# ---------------------------------------------------------------------------

def test_a_bare_prohibition_is_a_standing_constraint(tmp_path: Path) -> None:
    """THE REAL INCIDENT, 2026-07-29. `document-parser-table-bench.md:144` — "**Do not
    download MinerU2.5-Pro or GLM-OCR as `odl_bench` model swaps**" — was served by the
    dispatch queue as row #23 and closed with the commit message "close OCR download
    guardrail row". The old rule needed verb AND standing condition, and a prohibition
    carries no condition, so it scored as a WEAK HINT and the row was dispatched."""
    body = ("**Do not download MinerU2.5-Pro or GLM-OCR as `odl_bench` model swaps** — "
            "the harness invokes models single-pass")
    p = _handoff(tmp_path, f"## Guardrails\n- [ ] {body}\n")
    code, reasons = _classify_row(p, 2)
    assert code == 2
    assert "PROHIBITION" in reasons[0]
    assert "cannot finish not-doing" in reasons[0]


@pytest.mark.parametrize("body", [
    "Never patch a production kernel in place",
    "Do NOT run the epsilon-greedy exploration to manufacture counterfactuals",
    "Don't import the intake-866 equivalence framing",
])
def test_prohibition_forms_all_refuse(tmp_path: Path, body: str) -> None:
    p = _handoff(tmp_path, f"## Tasks\n- [ ] {body}\n")
    assert _classify_row(p, 2)[0] == 2, body


@pytest.mark.parametrize("body", [
    "Avoid duplicating the config across both registries",
    "Prefer the codified recipe constants over remembered values",
    # NB: no standing condition here. "Refrain … *until* the first is retired" is
    # correctly refused by the older verb+condition rule, which this control is not
    # about — the first draft used that phrasing and failed for the right reason.
    "Refrain from adding a second scorer",
])
def test_softer_negatives_stay_in_the_weak_tier(tmp_path: Path, body: str) -> None:
    """THE OVER-REFUSAL CONTROL. "Avoid duplicating the config" really can be a one-off
    cleanup with a completion state. Only unambiguous negative imperatives refuse;
    marking real work undispatchable is the costlier error."""
    p = _handoff(tmp_path, f"## Tasks\n- [ ] {body}\n")
    code, reasons = _classify_row(p, 2)
    assert code == 0, body
    assert any("WEAK HINT" in r for r in reasons), "must still be flagged for a human read"


def test_a_task_that_merely_mentions_not_doing_something_is_still_dispatchable(
        tmp_path: Path) -> None:
    """The prohibition must open the row. A task whose BODY discusses a constraint is
    still a task — anchoring on `^` is what keeps this from swallowing real work."""
    p = _handoff(tmp_path, "## Tasks\n"
                 "- [ ] Add a guard so the applicator does not restart a live role\n")
    assert _classify_row(p, 2)[0] == 0


# ------------------------------------------------------------------- C41 guard scope
#
# `section_is_guarded` took the nearest preceding heading, searched the whole span for
# the guard phrase, and returned ONE blanket bool for every box under it. Wrong both
# ways, and both faces were measured on the live corpus:
#   * false REFUSAL — an inline per-box marker bled forward onto unrelated rows, and
#     PROSE ABOUT guards guarded whatever followed it. `standardized-stack-…:244`
#     ("Finish W4 swap-CI…") and `stale-open-audit-…:269` ("read-certify the remaining
#     ~918") were both real dispatchable work, refused. mainC adjudicated 6 of these.
#   * false PERMIT — a standing-constraint box outside a banner's enumeration still
#     read as guarded, so every repair pass skipped it.

def _guarded(tmp_path: Path, body: str, needle: str) -> bool:
    path = tmp_path / "h.md"
    path.write_text(body, encoding="utf-8")
    lineno = next(i for i, l in enumerate(body.splitlines(), 1) if needle in l)
    return brc.box_is_guarded(path, lineno)


_ENUMERATED = """## Outstanding Work

> **⚠ THESE TWO BOXES ARE STANDING CONSTRAINTS, NOT TASKS — DO NOT DISPATCH OR FLIP THEM.**
> Checking one asserts an ongoing constraint has been permanently satisfied.

- [ ] FIRST keep the thing switched off until an operator says otherwise
- [x] a closed box that the count must not spend
- [ ] SECOND keep the other thing under review
- [ ] THIRD a genuinely dispatchable task that the banner never claimed
"""


def test_an_enumerating_banner_covers_exactly_what_it_enumerates(tmp_path: Path) -> None:
    """The false-PERMIT face. 'THESE TWO BOXES' must reach two boxes, not the section."""
    assert _guarded(tmp_path, _ENUMERATED, "FIRST")
    assert _guarded(tmp_path, _ENUMERATED, "SECOND")
    assert not _guarded(tmp_path, _ENUMERATED, "THIRD"), \
        "a box beyond the banner's own count is NOT covered by it"


def test_the_count_is_spent_on_open_boxes_only(tmp_path: Path) -> None:
    """`classify` returns on `- [x]` before it ever asks, so closed boxes are not what
    a banner is rationing. If the closed box consumed a slot, SECOND would fall out of
    scope and a real standing constraint would go unguarded."""
    assert _guarded(tmp_path, _ENUMERATED, "SECOND")


def test_an_unenumerated_banner_still_covers_the_whole_section(tmp_path: Path) -> None:
    """The compliant path, and the one that makes this a re-scoping rather than a
    deletion: most banners in the corpus say 'THESE BOXES' with no count, and their
    behaviour is deliberately unchanged."""
    body = """## Reopen Checklist

> **⚠ THESE BOXES ARE UNCHECKED BY DESIGN — DO NOT DISPATCH OR FLIP THEM.**

- [ ] FIRST re-read the doc end to end
- [ ] LATER a box far below, still under the same heading
"""
    assert _guarded(tmp_path, body, "FIRST")
    assert _guarded(tmp_path, body, "LATER")


def test_an_inline_marker_guards_its_own_box_and_does_not_bleed_forward(
        tmp_path: Path) -> None:
    """The false-REFUSAL face, measured at `standardized-stack-…:232` guarding `:244`."""
    body = """## Work

- [ ] *(STANDING CONSTRAINT — not a dispatchable task; do not flip.)*
- [ ] LATER Finish W4 swap-CI so representative stack changes prove generated output
"""
    assert _guarded(tmp_path, body, "STANDING CONSTRAINT")
    assert not _guarded(tmp_path, body, "LATER"), \
        "a marker written on one box must not speak for the next one"


def test_prose_about_guards_is_not_a_guard(tmp_path: Path) -> None:
    """Measured at `stale-open-audit-…:269`, refused by a table cell 140 lines above
    that merely NAMES the category. The blockquote requirement is what separates a
    banner from a sentence about banners."""
    body = """## Audit

    | **NOT A TASK** — reusable checklist or standing constraint | **36** |
    (`Reopen Checklist`, `Rules For New Tests`) and standing constraints under headings.

- [ ] LATER read-certify the remaining ~918 open boxes
"""
    assert not _guarded(tmp_path, body, "LATER")


def test_a_row_that_discusses_constraints_is_not_itself_one(tmp_path: Path) -> None:
    """Why the inline check reads the box's own line ONLY. Scanning continuation lines
    looks like robustness and re-imports the same prose-vs-guard confusion one level
    down: it newly guarded C41's own filing and `stale-open-audit-…:110`, both real
    tasks whose BODIES discuss standing constraints."""
    body = """## Work

- [ ] LATER Fix the predicate so an un-enumerated box is no longer exempted
  by every tool pass. The banner says STANDING CONSTRAINTS but the seventh box
  is not covered, and DO NOT DISPATCH bleeds forward onto unrelated rows.
"""
    assert not _guarded(tmp_path, body, "LATER")


def test_numeric_and_word_counts_are_both_understood(tmp_path: Path) -> None:
    for count in ("2", "TWO", "two"):
        body = f"""## Work

> **⚠ THESE {count} BOXES ARE STANDING CONSTRAINTS — DO NOT DISPATCH OR FLIP THEM.**

- [ ] FIRST a standing rule
- [ ] SECOND another standing rule
- [ ] THIRD a real task
"""
        assert _guarded(tmp_path, body, "FIRST"), count
        assert _guarded(tmp_path, body, "SECOND"), count
        assert not _guarded(tmp_path, body, "THIRD"), count


def test_a_wrapped_banner_still_yields_its_count(tmp_path: Path) -> None:
    """The live banner wraps over nine blockquote lines and states its count on the
    first. Reading only the matching line would lose the count on the other shape."""
    body = """## Work

> **⚠ DO NOT DISPATCH OR FLIP THEM.**
> Every open box here is a rule with no completion state.
> THESE TWO BOXES ARE STANDING CONSTRAINTS, noted by `auditor`.

- [ ] FIRST a standing rule
- [ ] SECOND another standing rule
- [ ] THIRD a real task
"""
    assert _guarded(tmp_path, body, "FIRST")
    assert not _guarded(tmp_path, body, "THIRD")


def test_audit_guards_finds_a_standing_constraint_that_was_flipped(tmp_path: Path) -> None:
    """C41 follow-up. `box_is_guarded` can only speak about OPEN boxes — `classify`
    returns on `- [x]` before it asks — so a standing constraint ALREADY flipped closed
    is invisible to every pass. That is exactly how `model-stack-…:339` sat closed under
    a DO-NOT-FLIP banner. In a section whose banner forbids flipping, any `- [x]` is
    suspicious by construction, so the rule needs no cleverness.
    """
    (tmp_path / "guarded.md").write_text("""## Outstanding Work

> **⚠ THESE BOXES ARE STANDING CONSTRAINTS — DO NOT DISPATCH OR FLIP THEM.**

- [ ] keep the thing switched off until an operator says otherwise
- [x] FLIPPED treat the helper modules as frozen
""", encoding="utf-8")
    (tmp_path / "plain.md").write_text("""## Work

- [x] an ordinary finished task in a section with no banner
""", encoding="utf-8")

    hits = brc.closed_boxes_under_a_guard(tmp_path)
    assert [(p.name, n) for p, n, _ in hits] == [("guarded.md", 6)], hits
    assert "FLIPPED" in hits[0][2]


def test_audit_guards_is_silent_when_nothing_is_flipped_under_a_banner(
        tmp_path: Path) -> None:
    """The compliant path. A guarded section with only OPEN boxes must report nothing,
    or the check becomes noise and stops being read — and an unguarded section's closed
    boxes are none of its business."""
    (tmp_path / "clean.md").write_text("""## Outstanding Work

> **⚠ THESE BOXES ARE UNCHECKED BY DESIGN — DO NOT DISPATCH OR FLIP THEM.**

- [ ] a standing rule
- [ ] another standing rule

## Delivered

- [x] a real task, closed, in a section with no banner
""", encoding="utf-8")
    assert brc.closed_boxes_under_a_guard(tmp_path) == []


# --------------------------------------------------------------------------------
# 2026-08-11 (`mainC`) — a banner must reach a section's DESCENDANTS, and the
# corruption invariant must NOT inherit that reach. Both pinned, because they are
# deliberately different and a future reader will be tempted to unify them.
# --------------------------------------------------------------------------------


def _phased(tmp_path):
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan.md").write_text(
        "## Phased Work Plan\n"
        "> **⛔ CLOSED APPENDIX — DEPRIORITIZED PLAN. Do not dispatch from the phases below.**\n"
        "\n"
        "### Phase 0\n"
        "- [ ] Shelved step one\n"
        "- [x] A read that really was done\n"
        "\n"
        "### Phase 1\n"
        "- [ ] Shelved step two\n"
        "\n"
        "## Live Work\n"
        "- [ ] A genuinely dispatchable task\n",
        encoding="utf-8")
    return d / "plan.md"


def test_a_parent_banner_reaches_boxes_in_child_sections(tmp_path) -> None:
    """The blind spot that made phased plans undeclarable.

    Measured on cpu-shape-specialized-gemv-decode.md: a CLOSED APPENDIX banner under
    `## Phased Work Plan` covered ZERO of the 36 open boxes beneath it, because
    `### Phase 0` opened a new section three lines later.
    """
    p = _phased(tmp_path)
    assert brc.box_is_guarded(p, 5) is True, "banner must reach `### Phase 0`"
    assert brc.box_is_guarded(p, 9) is True, "banner must reach `### Phase 1`"


def test_a_sibling_section_banner_does_not_leak_forward(tmp_path) -> None:
    """Scope still ends at the section boundary — this is not a blanket widening."""
    p = _phased(tmp_path)
    assert brc.box_is_guarded(p, 13) is False, "`## Live Work` is a sibling, not a descendant"


def test_the_corruption_invariant_keeps_the_FLAT_span(tmp_path) -> None:
    """A deprioritized plan's `- [x]` boxes are correct history, not corruption.

    Dispatch exclusion is generous; a corruption ACCUSATION is conservative. If these
    two ever share a scope rule, the 6 completed boxes under the GEMV appendix get
    reported as defects forever.
    """
    p = _phased(tmp_path)
    hits = brc.closed_boxes_under_a_guard(p.parent)
    assert hits == [], "a parent banner must NOT make child [x] boxes read as corruption"


def test_audit_standing_finds_a_flipped_rule_with_no_banner(tmp_path) -> None:
    """The miss that took the count 7 -> 11, then 12.

    Only 7 files in handoffs/active/ carry a guard phrase, so a rule flipped closed
    in an unbannered file is invisible to box_is_guarded, to --audit-guards, and to
    every dispatch pass. `inference` independently confirmed one such box
    (autokernel-research-loop.md:2659) that the banner-based pass cannot see.
    """
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True)
    (d / "plain.md").write_text(
        "## Notes\n"                                   # NO banner anywhere
        "- [x] Do not download the OCR models as bench swaps\n"
        "- [x] Keep routing default-off until an operator decision\n"
        "- [x] Port the SQLite reader\n",              # ordinary finished task
        encoding="utf-8")
    hits = brc.closed_standing_constraints(d)
    found = {(ln, kind) for _p, ln, kind, _b in hits}
    assert (2, "PROHIBITION") in found
    assert (3, "STANDING") in found
    assert not any(ln == 4 for ln, _ in found), "an ordinary finished task is not a constraint"


def test_audit_standing_reuses_classify_predicates_not_new_ones(tmp_path) -> None:
    """A second definition of 'standing constraint' would be a second source of truth.

    Pins the reuse: anything classify() would REFUSE to dispatch as a standing
    constraint while open must be recognised by this audit once closed. That
    equivalence is the whole point — the tool already knew how to spot these and
    structurally never asked the question of a closed box.
    """
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True)
    text = "Keep production routing default-off until an explicit operator decision"
    (d / "open.md").write_text(f"## S\n- [ ] {text}\n", encoding="utf-8")
    (d / "closed.md").write_text(f"## S\n- [x] {text}\n", encoding="utf-8")

    code, _ = brc.classify(d / "open.md", 2, " ", text, "S")
    assert code == 2, "classify must refuse this while OPEN"
    assert [h[1] for h in brc.closed_standing_constraints(d)] == [2], \
        "the same text, once CLOSED, must be caught by the audit"


# --------------------------------------------------------------------------------
# 2026-08-12 — the two screener blind spots `mainD` found by working the bench.
# Both are DECLARATIONS the row makes about itself, which a form-based screen could
# not read. Each is pinned in BOTH directions, because mainD's C41 caveat is that a
# loosened pattern refuses real work: "a row that says the word OPERATOR in its body
# is not an operator row; a row whose text STARTS with OPERATOR: is."
# --------------------------------------------------------------------------------


def _one_row(tmp_path, text):
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True, exist_ok=True)
    (d / "r.md").write_text(f"## Open\n- [ ] {text}\n", encoding="utf-8")
    return d / "r.md"


def test_an_owner_prefixed_row_is_refused(tmp_path) -> None:
    """The measured instance: handoff-index-and-backlog-graph.md:44 screened DISPATCHABLE.

    It opens `**OPERATOR:` and describes a host-level cron change. Dispatchable means
    WELL-FORMED, not YOURS-TO-DO.
    """
    p = _one_row(tmp_path, "**OPERATOR: nothing restarts `hub_supervisor.sh` if it dies.** Found dead.")
    code, reasons = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 2
    assert "DECLARES ITS OWNER" in reasons[0]


def test_merely_mentioning_an_operator_is_NOT_refused(tmp_path) -> None:
    """mainD's caveat, pinned. Prefix, not substring.

    This is the exact over-reach that C41 produced twice in one hour: a row whose BODY
    discusses a thing is not a row that IS the thing.
    """
    p = _one_row(tmp_path, "Add a column recording which operator signed each ratification")
    code, _ = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 0, "a row that merely mentions an operator must stay dispatchable"


def test_a_dependency_written_into_the_row_text_is_refused(tmp_path) -> None:
    """blocking_children() looks one indent DOWN and cannot see this.

    Measured instance: "Rationalize supervision with OP-9's resolution", where OP-9 is
    an OPEN operator decision — so the row screened dispatchable while its precondition
    was undecided.
    """
    p = _one_row(tmp_path, "Rationalize supervision with OP-9's resolution: one lifecycle story")
    code, reasons = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 2
    assert "DECLARES A DEPENDENCY" in reasons[0]


def test_gated_on_a_named_reference_is_refused(tmp_path) -> None:
    """The other live shape, verbatim from the corpus: "Gated on AR-3 Package D completion"."""
    p = _one_row(tmp_path, "A/B test LateOn vs GTE-ModernColBERT-v1. Gated on AR-3 Package D completion.")
    code, _ = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 2


def test_a_bare_pending_does_not_refuse(tmp_path) -> None:
    """`pending` alone is deliberately NOT a dependency signal.

    It is a mood, not a reference, and including it would refuse real work — which this
    file's settled rule calls the costlier error. The pattern requires a NAMED reference.
    """
    p = _one_row(tmp_path, "Write the pending section of the migration guide")
    code, _ = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 0


def test_a_row_gated_on_an_unevaluated_predicate_is_refused(tmp_path) -> None:
    """mainD's THIRD signal, and the one with a live reproduction behind it.

    `model-stack-update-pipeline-audit.md:628` screened DISPATCHABLE while reading
    "Direct benchmark runtime enforcement ONLY IF promotion-gate coverage proves
    insufficient". Nobody had assessed insufficiency, so the work was UNAUTHORISED —
    and two agents pulled that row independently, hours apart, avoiding it only by
    reading the text after the tool said go.
    """
    p = _one_row(tmp_path,
                 "Direct benchmark runtime enforcement only if promotion-gate coverage "
                 "proves insufficient")
    code, reasons = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 2
    assert "GATES ITSELF" in reasons[0]


def test_a_bare_only_if_does_NOT_refuse(tmp_path) -> None:
    """The narrowness that makes the signal safe, pinned.

    59 of 1,255 open boxes contain a bare `only if`/`only after`, and most are ordinary
    sequencing notes. Refusing on the phrase alone would withhold real work — the
    costlier error by this file's settled rule. The gate must name an UNEVALUATED
    PREDICATE (prove/show/demonstrate/confirm), not merely a condition.
    """
    p = _one_row(tmp_path, "Run the export only after the nightly batch completes")
    code, _ = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 0, "a plain sequencing condition must stay dispatchable"


def test_a_proof_verb_without_an_only_gate_does_NOT_refuse(tmp_path) -> None:
    """The other half of the conjunction. Both halves are required."""
    p = _one_row(tmp_path, "Write the report that shows how the scheduler behaves under load")
    code, _ = brc.classify(p, 2, " ", brc._boxes(p)[0][2], "Open")
    assert code == 0
