"""publish_row: the handoff_task box IDENTITY (text_sha of the first line) is recorded and re-checked (handoff standard)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_TESTS)))
sys.path.insert(0, _TESTS)
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
sys.path.insert(0, os.path.join(_ROOT, "scripts", "handoffs"))


class BoxIdentity(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, "handoffs", "active"))
        shutil.copytree(os.path.join(_ROOT, "scripts", "handoffs"), os.path.join(self.d, "scripts", "handoffs"),
                        ignore=shutil.ignore_patterns("tests", "__pycache__"))
        os.makedirs(os.path.join(self.d, "scripts", "coordination"))
        shutil.copy(os.path.join(_ROOT, "scripts", "coordination", "flip_checkbox.py"),
                    os.path.join(self.d, "scripts", "coordination"))
        self.box = "- [ ] **Q-1 — measure decode t/s of Q38FN Q8_0** stop rule: stop-on-answer"
        self.path = os.path.join(self.d, "handoffs", "active", "q.md")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_records_then_refuses_changed_first_line(self):
        spec = {"handoff_task": "q.md:Q-1"}
        ref, warn = pr.box_identity_findings(spec, self.path, self.box, self.d)
        self.assertEqual(ref, [])
        sha = spec["handoff_task_sha"]
        ref, _ = pr.box_identity_findings(spec, self.path, self.box.replace("Q8_0", "IQ4_XS"), self.d)
        self.assertTrue(ref and "identity changed" in ref[0])
        spec["handoff_task_sha"] = sha
        self.assertEqual(pr.box_identity_findings(spec, self.path, self.box, self.d)[0], [])

    def test_line_form_warns_and_index_state_warns(self):
        import box_index as bi
        rec = {"file": "handoffs/active/q.md", "id": "Q-1", "text_sha": bi.text_sha(self.box), "state": "frozen",
               "frozen_until": "OP-1", "gate_open": True, "gate": ["Q-0"], "holds": []}
        with open(os.path.join(self.d, "handoffs", "active", ".box-index.json"), "w") as fh:
            json.dump({"boxes": {"Q-1": rec}}, fh)
        _, warn = pr.box_identity_findings({"handoff_task": "q.md:12"}, self.path, self.box, self.d)
        text = " | ".join(warn)
        self.assertIn("names a LINE", text)
        self.assertIn("frozen", text)
        self.assertIn("gate still open", text)


if __name__ == "__main__":
    unittest.main()
