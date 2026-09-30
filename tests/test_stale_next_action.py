#!/usr/bin/env python3
"""Fixture test for scripts/handoffs/stale_next_action.py — task ids of any dash depth.

Stdlib ``unittest`` only; runs with ``python3 tests/test_stale_next_action.py`` and under pytest.

WHY THIS FILE EXISTS. Until 2026-09-29 the id regex allowed at most three dash-separated parts,
so ``VB-KVQ-V10-DICT`` was read as ``VB-KVQ-V10``. That falsely flagged EVL-47 (its 3-part
prefix is ticked, the named 4-part task is open) and hid a real stale row, EVL-14, whose
``EV-RI-EXEC-1`` was read as ``EV-RI-EXEC`` and resolved to no box. Both directions are pinned.
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TOOL = _REPO / "scripts" / "handoffs" / "stale_next_action.py"

_spec = importlib.util.spec_from_file_location("stale_next_action", _TOOL)
sna = importlib.util.module_from_spec(_spec)
sys.modules["stale_next_action"] = sna
_spec.loader.exec_module(sna)

HANDOFF = """# Fixture handoff

- [x] **VB-KVQ-V10 — the 3-part parent, ticked.**
- [ ] **VB-KVQ-V10-DICT — the 4-part child, open.**
- [x] **EV-RI-EXEC-1 — a 4-part task, ticked.**
- [ ] **EV-4b — the next open task.**
- [x] **TD-1c — a 2-part task, ticked.**
"""

INDEX = """# Fixture index

| ID | Track | Handoff | Next action | Deps |
|---|---|---|---|---|
| ROW-1 | t | [h](fixture-handoff.md) | VB-KVQ-V10-DICT: make the adapter accept stats dicts | — |
| ROW-2 | t | [h](fixture-handoff.md) | EV-RI-EXEC-1 — implement the evaluator preflight | — |
| ROW-3 | t | [h](fixture-handoff.md) | EV-4b — the next open task | — |
| ROW-4 | t | [h](fixture-handoff.md) | TD-1c — already done | — |
"""


class IdRegex(unittest.TestCase):
    def test_four_part_id_is_read_whole(self):
        self.assertEqual(sna.ID_RE.findall("then VB-KVQ-V10-DICT and VB-KVQ-V10-RECONSIDER"),
                         ["VB-KVQ-V10-DICT", "VB-KVQ-V10-RECONSIDER"])
        self.assertEqual(sna.ID_RE.findall("EV-RI-EXEC-1 — implement"), ["EV-RI-EXEC-1"])

    def test_shorter_ids_unchanged(self):
        self.assertEqual(sna.ID_RE.findall("EVL-42, RTG-1f, EPD-3-R5, UTM-P1a.2, TD-1c"),
                         ["EVL-42", "RTG-1f", "EPD-3-R5", "UTM-P1a.2", "TD-1c"])

    def test_bare_word_is_not_an_id(self):
        self.assertEqual(sna.ID_RE.findall("repoint the judge 42 times"), [])


class Scan(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.active = Path(self._tmp.name)
        (self.active / "fixture-handoff.md").write_text(HANDOFF)
        (self.active / "fixture-index.md").write_text(INDEX)

    def tearDown(self):
        self._tmp.cleanup()

    def test_rows(self):
        flagged = {row_id: named for _, row_id, named, _ in sna.scan(self.active)}
        # ROW-1 names an OPEN 4-part task whose 3-part prefix is ticked: not stale.
        self.assertNotIn("ROW-1", flagged)
        # ROW-2 names a TICKED 4-part task: stale, and the id is read whole.
        self.assertEqual(flagged.get("ROW-2"), ["EV-RI-EXEC-1"])
        self.assertNotIn("ROW-3", flagged)
        self.assertEqual(flagged.get("ROW-4"), ["TD-1c"])
        self.assertEqual(set(flagged), {"ROW-2", "ROW-4"})


if __name__ == "__main__":
    unittest.main()
