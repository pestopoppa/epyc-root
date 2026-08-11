"""Tests for scripts/coordination/backlog_queue_gen.py.

The generator exists because `BACKLOG-DISPATCH-QUEUE.md` is hand-maintained and keys
its rows as `file.md:LINE`. Audited box-by-box on 2026-07-29 across the 73 unique refs
in its swap-in and runner-up lists: 48% already closed, 27% anchor rot, 5% blocked,
19% dispatchable. Line anchors rot within hours of an edit wave; task TEXT does not.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "bqg", REPO_ROOT / "scripts" / "coordination" / "backlog_queue_gen.py")
bqg = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bqg)


@pytest.fixture()
def handoffs(tmp_path: Path) -> Path:
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True)
    (d / "alpha.md").write_text(
        "## Tasks\n"
        "- [ ] Port the SQLite reader\n"
        "- [x] Already finished\n"
        "- [ ] Record the era boundary\n"
        "  - [x] token authored: await operator signature\n",
        encoding="utf-8")
    (d / "beta.md").write_text(
        "## Update Checklist For Any Change\n"
        "> DO NOT DISPATCH these boxes.\n"
        "- [ ] Run the focused unit tests\n",
        encoding="utf-8")
    return d


def test_verdicts_skips_closed_boxes_and_classifies_the_rest(handoffs: Path) -> None:
    rows = bqg.verdicts(handoffs)
    assert "Already finished" not in [r["text"] for r in rows], "closed boxes are not work"
    kinds = {r["text"][:20]: r["kind"] for r in rows}
    assert kinds["Port the SQLite read"] == "clean"
    assert kinds["Record the era bound"] == "blocked"
    assert kinds["Run the focused unit"] == "guarded"


def test_check_reports_each_way_a_ref_can_be_unusable(handoffs: Path, tmp_path: Path) -> None:
    q = tmp_path / "q.md"
    q.write_text(
        "- `alpha.md:2` a live one\n"          # dispatchable  -> silent
        "- `alpha.md:3` closed\n"              # ALREADY-CLOSED
        "- `alpha.md:99` off the end\n"        # ANCHOR-ROT
        "- `gamma.md:1` no such file\n"        # MISSING-FILE
        "- `alpha.md:4` era row\n"             # BLOCKED
        "- `beta.md:3` checklist\n",           # GUARDED
        encoding="utf-8")
    rotted, report = bqg.check_queue(q, handoffs)
    blob = "\n".join(report)
    assert rotted == 5
    assert "ALREADY-CLOSED alpha.md:3" in blob
    assert "ANCHOR-ROT     alpha.md:99" in blob
    assert "MISSING-FILE   gamma.md:1" in blob
    assert "BLOCKED" in blob and "GUARDED" in blob
    assert "alpha.md:2" not in blob, "a usable ref must not be reported"


def test_a_ref_the_queue_already_dispositioned_is_not_counted_against_it(
        handoffs: Path, tmp_path: Path) -> None:
    """THE REGRESSION THIS FILE EXISTS FOR. The first run reported 65 unusable refs on
    a queue where a third were rows struck through and annotated minutes earlier — the
    checker was reporting the maintainer's own bookkeeping as the defect. A checker
    that cannot read its subject's dispositions manufactures work."""
    q = tmp_path / "q.md"
    q.write_text(
        "- ~~`alpha.md:3`~~ **✅ CLOSED 2026-07-29**\n"
        "- `alpha.md:99` genuinely rotted\n",
        encoding="utf-8")
    rotted, report = bqg.check_queue(q, handoffs)
    assert rotted == 1, "only the undispositioned ref counts"
    assert "alpha.md:99" in "\n".join(report)
    assert any("skipped" in line for line in report), "the skip must be disclosed, not silent"


def test_check_on_a_missing_queue_refuses_rather_than_reporting_clean(tmp_path: Path) -> None:
    """A clean 0 for a file that does not exist reads as "the queue is healthy"."""
    rotted, report = bqg.check_queue(tmp_path / "nope.md")
    assert rotted == 0
    assert "REFUSING" in report[0]


def test_render_states_that_the_count_is_shape_not_liveness(handoffs: Path) -> None:
    """The count invites misreading as a backlog estimate. Read-certification measured
    liveness at 29-47%, so quoting ~900 as a task count restates the over-count the
    queue already suffers from. The caveat travels with the number or it is lost."""
    out = bqg.render(bqg.verdicts(handoffs))
    assert "dispatchable IN SHAPE" in out
    assert "not a backlog estimate" in out
    assert "29%" in out


def test_render_keys_rows_on_text_and_marks_the_line_as_a_hint(handoffs: Path) -> None:
    out = bqg.render(bqg.verdicts(handoffs))
    assert "Port the SQLite reader" in out
    assert "display hint" in out
    assert "claim --agent <id> --row" in out, "must steer to the durable key"


def test_blocked_and_guarded_rows_are_absent_from_the_generated_bench(
        handoffs: Path) -> None:
    """The whole point: what the generator emits is what a main may safely pull."""
    out = bqg.render(bqg.verdicts(handoffs))
    assert "Record the era boundary" not in out
    assert "Run the focused unit tests" not in out


# --------------------------------------------------------------------------------
# 2026-08-11 (`mainC`) — verbatim text, the positive do-not-dispatch signal, and the
# invariant it makes possible. Each test below pins a property that was a MEASURED
# defect, not a hypothetical one.
# --------------------------------------------------------------------------------


@pytest.fixture()
def wordy(tmp_path: Path) -> Path:
    """A handoff whose box text is longer than the old 150-char truncation."""
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True)
    long_tail = "consequences that matter " * 12          # ~300 chars
    (d / "wordy.md").write_text(
        "## Tasks\n"
        f"- [ ] Adopt the six-point disclosure standard and {long_tail}END-SENTINEL\n",
        encoding="utf-8")
    return d


def test_render_emits_the_box_text_verbatim_and_untruncated(wordy: Path) -> None:
    """The queue's paraphrase is what made 379 rotted refs unrecoverable by text.

    A truncated row is a paraphrase by another name: it cannot be matched back to
    the box it names, which is the whole point of keying on text.
    """
    out = bqg.render(bqg.verdicts(wordy))
    assert "END-SENTINEL" in out, "box text was truncated — the key is no longer the text"


def test_render_prints_a_claim_key_matching_the_claim_verb(wordy: Path) -> None:
    """A displayed command that takes a DIFFERENT lock than it prints is a defect."""
    rows = bqg.verdicts(wordy)
    out = bqg.render(rows)
    assert bqg.brc.claim_key(rows[0]["text"]) in out


def test_verdicts_separates_a_declared_guard_from_our_own_inference(handoffs: Path) -> None:
    """`declared_no_dispatch` must come from the HANDOFF, never from text shape."""
    rows = {(r["file"], r["line"]): r for r in bqg.verdicts(handoffs)}
    guarded = rows[("beta.md", 3)]
    assert guarded["declared_no_dispatch"] is True
    assert rows[("alpha.md", 2)]["declared_no_dispatch"] is False


def test_quarantine_reports_but_does_not_withhold_from_the_bench(tmp_path: Path) -> None:
    """Report-only, deliberately: refusing real work is the costlier error.

    The first `_PROCEDURAL` cut matched 11 rows and every one was a ONE-OFF rerun.
    Had quarantine withheld, that cut would have silently deleted 11 real tasks.
    """
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True)
    (d / "p.md").write_text(
        "## Pickup\n"
        "- [ ] Check llama.cpp upstream for any new CPU ukernel PRs\n",
        encoding="utf-8")
    rows = bqg.verdicts(d)
    assert len(bqg.quarantine(rows)) == 1, "undeclared recurring step should be named"
    assert "for any new CPU ukernel PRs" in bqg.render(rows), "must NOT be withheld"


def test_a_one_off_rerun_is_not_quarantined_as_a_procedure(tmp_path: Path) -> None:
    """The discriminator is a standing condition, never the verb.

    'Re-run the 27 confounded E5 cells' is a task; 'before each pickup' is a rule.
    """
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True)
    (d / "r.md").write_text(
        "## Tasks\n"
        "- [ ] Re-run the 27 confounded E5 cells on declared placement\n",
        encoding="utf-8")
    assert bqg.quarantine(bqg.verdicts(d)) == []


def test_audit_procedures_flags_a_closed_box_under_a_guard(tmp_path: Path, monkeypatch) -> None:
    """THE INVARIANT — the thing absence-based screening structurally could not do.

    The measured case it stands in for: four boxes in a per-change checklist flipped
    on 2026-07-14, ELEVEN DAYS before any sweep, referenced by no queue row at all.
    """
    d = tmp_path / "handoffs" / "active"
    d.mkdir(parents=True)
    (d / "chk.md").write_text(
        "## Update Checklist For Any Model-Stack Change\n"
        "> **⚠ DO NOT DISPATCH OR FLIP THEM.**\n"
        "- [ ] Identify the change type\n"
        "- [x] Compile stack priors\n",
        encoding="utf-8")
    monkeypatch.setitem(bqg.TREES, "active", d)
    total, report = bqg.audit_procedures(["active"])
    assert total == 1
    assert any("Compile stack priors" in line for line in report)


def test_audit_procedures_labels_history_as_report_only(tmp_path: Path, monkeypatch) -> None:
    """In completed/archived a flipped box may be a CORRECT record of a run."""
    d = tmp_path / "handoffs" / "completed"
    d.mkdir(parents=True)
    (d / "old.md").write_text("## Done\n- [x] Something\n", encoding="utf-8")
    monkeypatch.setitem(bqg.TREES, "completed", d)
    _, report = bqg.audit_procedures(["completed"])
    assert any("REPORT ONLY" in line for line in report)
