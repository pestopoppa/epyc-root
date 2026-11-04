"""folded_resolve: retired handoff names resolve through handoffs/active/.folded.json."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import folded_resolve as fr  # noqa: E402

FOLDED = {
    "files": {
        "old-a.md": {"target": "new-a.md", "track": "old-a"},
        "old-b.md": {"target": "new-b.md", "track": None},
        "old-c.md": "new-c.md",
    },
    "ids": {"X-1": {"target": "X-9", "track": "t"}, "X-2": "X-8"},
}


class Resolve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "handoffs" / "active").mkdir(parents=True)
        (self.root / "handoffs" / "active" / ".folded.json").write_text(json.dumps(FOLDED))

    def tearDown(self):
        self.tmp.cleanup()

    def test_folded_name_redirects(self):
        self.assertEqual(fr.resolve_handoff_file("handoffs/active/old-a.md", self.root),
                         "handoffs/active/new-a.md")
        self.assertEqual(fr.resolve_handoff_file("old-c.md", self.root), "handoffs/active/new-c.md")

    def test_anchor_only_when_track_present(self):
        self.assertEqual(fr.resolve_handoff_file("old-a.md", self.root, with_anchor=True),
                         "handoffs/active/new-a.md#track-old-a")
        self.assertEqual(fr.resolve_handoff_file("old-b.md", self.root, with_anchor=True),
                         "handoffs/active/new-b.md")

    def test_unfolded_and_existing_unchanged(self):
        self.assertEqual(fr.resolve_handoff_file("handoffs/active/keep.md", self.root),
                         "handoffs/active/keep.md")
        (self.root / "handoffs" / "active" / "old-a.md").write_text("x")
        self.assertEqual(fr.resolve_handoff_file("handoffs/active/old-a.md", self.root),
                         "handoffs/active/old-a.md")

    def test_archived_name_resolves_to_completed(self):
        (self.root / "handoffs" / "completed").mkdir()
        (self.root / "handoffs" / "completed" / "done.md").write_text("x")
        self.assertEqual(fr.resolve_handoff_file("handoffs/active/done.md", self.root),
                         "handoffs/completed/done.md")

    def test_row_ids(self):
        self.assertEqual(fr.resolve_row_id("X-1", self.root), "X-9")
        self.assertEqual(fr.resolve_row_id("X-2", self.root), "X-8")
        self.assertEqual(fr.resolve_row_id("Y-1", self.root), "Y-1")

    def test_missing_folded_file_is_identity(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(fr.resolve_handoff_file("handoffs/active/old-a.md", Path(d)),
                             "handoffs/active/old-a.md")

    def test_dedupe_keeps_order(self):
        self.assertEqual(fr.dedupe(["a", "b", "a"]), ["a", "b"])


class BackfillRoutesResolveInRepo(unittest.TestCase):
    def test_every_manual_route_resolves_to_existing_file(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML unavailable")
        spec = importlib.util.spec_from_file_location("backfill_dispositions",
                                                      SCRIPTS / "backfill_dispositions.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        root = mod.ROOT
        folded = fr.load_folded(root)
        for iid, routes in mod.MANUAL_INTEGRATED_ROUTES.items():
            for route in routes:
                out = fr.resolve_handoff_file(route, root, folded)
                self.assertTrue((root / out).exists(), f"{iid}: {route} -> {out}")


if __name__ == "__main__":
    unittest.main()
