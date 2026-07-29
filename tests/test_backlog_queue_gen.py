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
