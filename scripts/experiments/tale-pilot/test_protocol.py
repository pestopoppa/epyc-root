"""Offline controls for the sealed PRB-T4 CPU pilot."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner as run


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs, cls.cases = run.verify()

    def test_exact_registered_cases_and_prompts(self):
        self.assertEqual([row["id"] for row in self.cases], [
            "gsm8k_01029", "olympiadbench_algebra_2501", "mmlu_pro_chemistry_03738",
            "leetcode_flip-game",
        ])
        for case in self.cases:
            baseline = run.request_body(case, "baseline")
            self.assertEqual(baseline["messages"][0]["content"], case["prompt"])
            self.assertEqual((baseline["temperature"], baseline["seed"], baseline["max_tokens"]),
                             (0.3, 42, 512))
            self.assertEqual(run.request_body(case, "estimator")["max_tokens"], 32)
            self.assertTrue(run.request_body(case, "tale", 4096)["messages"][0]["content"].endswith(
                "use less than 4096 tokens."))
        self.assertEqual(len(run.schedule(self.cases, False)), 16)
        self.assertEqual(run.schedule(self.cases, True), [(self.cases[0], "baseline")])

    def test_estimator_clamp_and_net_cost(self):
        self.assertEqual(run.estimate("Budget: [[9999]]"), {"beta": 4096, "fallback": False})
        self.assertEqual(run.estimate("Budget: [[2]]"), {"beta": 10, "fallback": False})
        self.assertEqual(run.estimate("unknown"), {"beta": 100, "fallback": True})
        rows = []
        for arm, prompt, completion, wall in [
            ("baseline", 100, 32, 12), ("static", 120, 20, 10),
            ("estimator", 200, 5, 4), ("tale", 145, 10, 8),
        ]:
            rows.append(dict(arm=arm, suite="math", status="captured", wall_s=wall,
                             usage=dict(prompt_tokens=prompt, completion_tokens=completion,
                                        total_tokens=prompt + completion),
                             finish_reason="length", correct=None, beta=12, fallback=False))
        row = run.metrics(rows)["math"]["tale"]
        self.assertEqual(row["including_estimator"], {
            "prompt_tokens": 345, "completion_tokens": 15, "total_tokens": 360, "wall_s": 12,
        })
        self.assertEqual(row["delta_from_baseline"]["completion_tokens"], -17)
        self.assertEqual(row["delta_from_baseline"]["total_tokens"], 228)

    def test_known_source_scores_and_confined_refusal(self):
        expected = ("#### 34", self.cases[1]["expected"], self.cases[2]["expected"])
        for case, text in zip(self.cases[:3], expected, strict=True):
            self.assertIs(run.score(None, case, text)["correct"], True)
        with patch.object(run.os, "access", return_value=False):
            self.assertIsNone(run.score(None, self.cases[3], "anything")["correct"])

    def test_stop_preserves_failing_cell_and_no_retry(self):
        outcomes = []
        with tempfile.TemporaryDirectory() as tmp:
            window = Path(tmp)
            with (patch.object(run.live, "check_window"), patch.object(run, "custody"),
                  patch.object(run, "capture", side_effect=TimeoutError("fixture")) as capture):
                with self.assertRaises(TimeoutError):
                    run.run_attempts(window, run.schedule(self.cases, False), None, "fixture",
                                     self.inputs, time.time() + 60, outcomes)
            self.assertEqual(capture.call_count, 1)
            self.assertEqual(len(outcomes), 1)
            self.assertEqual(outcomes[0]["status"], "UNKNOWN")
            self.assertEqual(run.read_json(window / "attempt-00/OUTCOME.json"), outcomes[0])
            self.assertFalse((window / "attempt-01").exists())

    def test_smoke_predicate_rejects_stale_and_tampered_control(self):
        case = self.cases[0]
        request = run.request_body(case, "baseline")
        response = {"object": "chat.completion", "model": request["model"],
                    "choices": [{"finish_reason": "length", "message": {
                        "role": "assistant", "content": "#### 34"}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 4, "total_tokens": 104},
                    "__verbose": {"tokens": [1, 2, 3, 4]}}
        with tempfile.TemporaryDirectory() as tmp:
            dry = Path(tmp)
            window = dry / run.SMOKE_DIR / "window-fixture"
            result = window / "SMOKE.json"
            window.mkdir(parents=True)
            with patch.dict(run.os.environ, {"FILLER_DRYRUN_DIR": tmp,
                                            "FILLER_SMOKE_T0": str(time.time() - 10),
                                            "FILLER_DEADLINE": str(int(time.time()) + 60),
                                            "FILLER_ID": run.ROW,
                                            "FILLER_STOPFILE": str(dry / "STOP"),
                                            "FILLER_PIDFILE": str(dry / "PIDS")}):
                def fixture_capture(attempt, body, *_):
                    run.atomic_json(attempt / "REQUEST.json", body)
                    run.atomic_json(attempt / "RESPONSE.json", response)
                    run.atomic_json(attempt / "HTTP.json", {"status": 200})
                    return run.read_terminal(json.dumps(response).encode(), body)

                process = Mock(pid=12345, returncode=0)
                process.poll.return_value = 0
                with (patch.object(run.live, "check_window"),
                      patch.object(run.live, "bind_four_cores", return_value=[0, 1, 2, 3]),
                      patch.object(run.live, "file_port_available", return_value=True),
                      patch.object(run.owner, "listen_inodes", return_value=set()),
                      patch.object(run.subprocess, "run", return_value=Mock(stdout=b"linkage fixture")),
                      patch.object(run.subprocess, "Popen", return_value=process),
                      patch.object(run.live, "server_ready", return_value={"pid": process.pid}),
                      patch.object(run, "custody"), patch.object(run, "capture", side_effect=fixture_capture)):
                    self.assertEqual(run.run_window(window, True), 0)
                self.assertEqual(run.smoke(), 0)
                self.assertFalse(run.qualified(result, True, time.time() + 60))
                (window / "attempt-00/RESPONSE.json").write_text("{}\n")
                self.assertEqual(run.smoke(), 1)


if __name__ == "__main__":
    unittest.main()
