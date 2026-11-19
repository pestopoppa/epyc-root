"""Pick identity is the task TEXT, not file:line: shifting a box's line must not change its task_id."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seed_queue as sq  # noqa: E402

BOX = "- [ ] **P2 — benchmark the decode sweep on mi210** and record t/s"


def _ids(body):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "h.md"
        p.write_text(body)
        return sq.extract(p)


class SeedQueueIdentity(unittest.TestCase):
    def test_line_shift_keeps_task_id(self):
        a = _ids(BOX + "\n")[0]
        b = _ids("intro\n\nmore prose\n" + BOX + "\n")[0]
        self.assertNotEqual(a["line_no"], b["line_no"])
        self.assertEqual(a["task_id"], b["task_id"])
        self.assertNotIn("-L", a["task_id"])
        self.assertTrue(b["spec_ref"].endswith(f"#L{b['line_no']}"))  # hint only

    def test_text_change_changes_task_id(self):
        self.assertNotEqual(_ids(BOX + "\n")[0]["task_id"], _ids(BOX + " twice\n")[0]["task_id"])

    def test_identical_texts_stay_distinct(self):
        r = _ids(BOX + "\n" + BOX + "\n")
        self.assertEqual(len({i["task_id"] for i in r}), 2)

    def test_whitespace_and_markup_normalized(self):
        self.assertEqual(sq.text_identity("**a**  `b`  c"), sq.text_identity("a b c"))


class SeedQueueTextDedup(unittest.TestCase):
    """An old `-L<lineno>` proposal with the same text must not be re-proposed under its new text-hash id."""

    def _run(self, outbox_lines, queue_lines=()):
        import io, json, contextlib
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "outbox").mkdir()
            (d / "outbox" / "mainA.jsonl").write_text("".join(json.dumps(m) + "\n" for m in outbox_lines))
            (d / "queue.jsonl").write_text("".join(json.dumps(m) + "\n" for m in queue_lines))
            ho = d / "handoffs"
            ho.mkdir()
            (ho / "h.md").write_text(BOX + "\n")
            old = (sq.BUS_ROOT, sq.HANDOFFS, sq.row_intake.screen, sq.row_intake.estimate_occupancy)
            sq.BUS_ROOT, sq.HANDOFFS = d, ho

            class R:
                ready, verdict, receipt, needs_reanchor = True, "DISPATCHABLE", "r", False
            sq.row_intake.screen = lambda row: R()
            sq.row_intake.estimate_occupancy = lambda *a, **k: None
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = sq.main(["--handoff", "h.md", "--agent", "t"])
            finally:
                sq.BUS_ROOT, sq.HANDOFFS, sq.row_intake.screen, sq.row_intake.estimate_occupancy = old
            out = d / "outbox" / "t.jsonl"
            return rc, buf.getvalue(), (out.read_text() if out.exists() else "")

    def test_old_lineno_proposal_suppresses_reseed(self):
        summary = _ids(BOX + "\n")[0]["summary"]
        rc, out, written = self._run([{"kind": "task-propose", "task_id": "h--P2-L999",
                                       "payload": {"summary": summary}}])
        self.assertEqual(rc, 0)
        self.assertEqual(written, "")
        self.assertIn("h--P2-L999", out)

    def test_unseeded_text_is_proposed(self):
        rc, out, written = self._run([{"kind": "task-propose", "task_id": "h--P2-L999",
                                       "payload": {"summary": "something else entirely"}}])
        self.assertEqual(rc, 0)
        self.assertIn(_ids(BOX + "\n")[0]["task_id"], written)

    def test_queue_row_with_text_dedups(self):
        summary = _ids(BOX + "\n")[0]["summary"]
        rc, out, written = self._run([], [{"task_id": "h--P2-L5", "task_text": summary, "status": "READY"}])
        self.assertEqual(written, "")


if __name__ == "__main__":
    unittest.main()
