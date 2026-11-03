"""2026-11-03 session review item 9: AskUserQuestion is denied by the harness when the answer is already known, the
question bundles items, the operator just gave an imperative, or the session owns a live launch."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "..", "scripts", "hooks", "check_question_discipline.py")
sys.path.insert(0, os.path.dirname(HOOK))
import check_question_discipline as cq  # noqa: E402


def q(options, n=1):
    return {"tool_name": "AskUserQuestion", "session_id": "s1", "transcript_path": "/nonexistent",
            "tool_input": {"questions": [{"question": "which?", "options": [{"label": o} for o in options]}] * n}}


class Verdicts(unittest.TestCase):
    def test_one_plain_item_passes(self):
        self.assertIsNone(cq.verdict(q(["A", "B"]), flags="/nonexistent", last_text="what do you think?"))

    def test_more_than_one_item_is_denied(self):
        v = cq.verdict(q(["A", "B"], n=3), flags="/nonexistent", last_text="")
        self.assertTrue(v.startswith("BLOCKED: 3 items in one question; fix:"), v)

    def test_recommended_option_is_denied(self):
        v = cq.verdict(q(["A (Recommended)", "B"]), flags="/nonexistent", last_text="")
        self.assertIn("marked Recommended/default", v)
        v = cq.verdict({"tool_input": {"questions": [{"options": [{"label": "A", "description": "the default"}]}]}}, flags="/nonexistent", last_text="")
        self.assertIn("marked Recommended/default", v)

    def test_operator_imperative_is_denied(self):
        for text in ("run YARN r5 NOW. Nothing else", "JUST RUN THE READIED TASK", "THE MACHINE IS IDLE. DO SOMETHING!"):
            v = cq.verdict(q(["A", "B"]), flags="/nonexistent", last_text=text)
            self.assertTrue(v and "imperative" in v, (text, v))
        self.assertIsNone(cq.verdict(q(["A", "B"]), flags="/nonexistent", last_text="can you summarise the options?"))

    def test_live_launch_of_this_session_is_denied(self):
        with tempfile.TemporaryDirectory() as flags:
            os.makedirs(os.path.join(flags, "dryrun", "row-x"))
            os.makedirs(os.path.join(flags, "grants"))
            json.dump({"id": "row-x", "session_id": "s1"}, open(os.path.join(flags, "dryrun", "row-x", "DIRECT.json"), "w"))
            v = cq.verdict(q(["A", "B"]), flags=flags, last_text="")
            self.assertIn("owns a live launch (row-x)", v)
            self.assertIsNone(cq.verdict(dict(q(["A", "B"]), session_id="other"), flags=flags, last_text=""))
            json.dump({"id": "row-x", "session_id": "s1", "ended": "t"}, open(os.path.join(flags, "dryrun", "row-x", "DIRECT.json"), "w"))
            self.assertIsNone(cq.verdict(q(["A", "B"]), flags=flags, last_text=""))

    def test_last_user_text_reads_the_transcript(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"type": "user", "message": {"content": "first"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}}) + "\n")
            f.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}) + "\n")
            f.write(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "RUN IT NOW"}]}}) + "\n")
            f.write(json.dumps({"type": "user", "message": {"content": "<system-reminder>not the operator</system-reminder>"}}) + "\n")
        try:
            self.assertEqual(cq.last_user_text(f.name), "RUN IT NOW")
        finally:
            os.remove(f.name)
        self.assertEqual(cq.last_user_text("/nonexistent"), "")

    def test_malformed_input_and_other_tools_pass(self):
        self.assertIsNone(cq.verdict({"tool_input": {}}, flags="/nonexistent", last_text=""))
        self.assertIsNone(cq.verdict({"tool_input": {"questions": "x"}}, flags="/nonexistent", last_text=""))


class Process(unittest.TestCase):
    def run_hook(self, payload, env=None):
        e = dict(os.environ, ROWFLOW_FLAGS="/nonexistent")
        e.update(env or {})
        return subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True, env=e)

    def test_exit_2_with_one_line_on_deny_and_0_otherwise(self):
        r = self.run_hook(json.dumps(q(["A (Recommended)"])))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1)
        self.assertTrue(r.stderr.startswith("BLOCKED:"))
        self.assertEqual(self.run_hook(json.dumps(q(["A", "B"]))).returncode, 0)
        self.assertEqual(self.run_hook("not json").returncode, 0)
        self.assertEqual(self.run_hook(json.dumps(dict(q(["A (Recommended)"]), tool_name="Bash"))).returncode, 0)


if __name__ == "__main__":
    unittest.main()
