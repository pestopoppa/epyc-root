"""Offline tests for registered requests, terminal interpretation and fail-closed execution."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import prepare
import runner


class ThinkingProbeTests(unittest.TestCase):
    def setUp(self):
        self.cells = prepare.requests("pinned")
        self.terminal = {
            "object": "chat.completion",
            "model": "pinned",
            "choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "reasoning_content": "42 minus 14", "content": "42",
            }}],
            "usage": {"prompt_tokens": 40, "completion_tokens": 4, "total_tokens": 44},
            "__verbose": {"tokens": [29, 42, 6, 10]},
        }

    def test_fixed_prompt_with_only_registered_differences(self):
        bodies = [copy.deepcopy(cell["body"]) for cell in self.cells]
        self.assertEqual(tuple(cell["unit"] for cell in self.cells), prepare.ARMS)
        self.assertEqual([body.pop("chat_template_kwargs") for body in bodies],
                         [{"enable_thinking": True}, {"enable_thinking": True},
                          {"enable_thinking": False}])
        self.assertEqual([body.pop("thinking_budget_tokens", None) for body in bodies],
                         [None, 8, None])
        self.assertTrue(all(body == bodies[0] for body in bodies))
        self.assertEqual(bodies[0]["max_tokens"], 128)
        self.assertFalse(bodies[0]["stream"])
        self.assertFalse(bodies[0]["cache_prompt"])

    def test_terminal_distinguishes_omitted_and_empty_reasoning(self):
        request = self.cells[0]["body"]
        result = runner.read_terminal(json.dumps(self.terminal), request)
        self.assertTrue(result["reasoning_field_present"])
        self.assertTrue(result["reasoning_nonempty"])
        self.assertEqual(result["token_ids"], [29, 42, 6, 10])
        msg = self.terminal["choices"][0]["message"]
        msg["reasoning_content"] = ""
        result = runner.read_terminal(json.dumps(self.terminal), request)
        self.assertTrue(result["reasoning_field_present"])
        self.assertFalse(result["reasoning_nonempty"])
        del msg["reasoning_content"]
        result = runner.read_terminal(json.dumps(self.terminal), request)
        self.assertFalse(result["reasoning_field_present"])

    def test_length_finish_is_captured_for_descriptive_comparison(self):
        self.terminal["choices"][0]["finish_reason"] = "length"
        self.terminal["usage"].update(completion_tokens=128, total_tokens=168)
        result = runner.read_terminal(json.dumps(self.terminal), self.cells[0]["body"])
        self.assertEqual(result["finish_reason"], "length")
        self.assertTrue(result["reasoning_nonempty"])

    def test_terminal_rejects_missing_end_and_excess_completion(self):
        bad_stop = copy.deepcopy(self.terminal)
        bad_stop["choices"][0]["finish_reason"] = None
        too_many = copy.deepcopy(self.terminal)
        too_many["usage"].update(completion_tokens=129, total_tokens=169)
        for bad in (bad_stop, too_many):
            with self.subTest(body=bad), self.assertRaises(ValueError):
                runner.read_terminal(json.dumps(bad), self.cells[0]["body"])

    def test_first_transport_failure_preserves_unknown_and_prevents_later_calls(self):
        live = SimpleNamespace(check_window=lambda _: None, file_identity=lambda _: [1],
                               MODEL="pinned", WindowEnded=TimeoutError)
        results = []
        with tempfile.TemporaryDirectory() as tmp:
            window = Path(tmp)
            with (patch.object(runner, "own_listener"),
                  patch.object(runner, "capture", side_effect=[{"usage": {}}, OSError("lost")]) as send,
                  self.assertRaisesRegex(OSError, "lost")):
                runner.run_attempts(window, self.cells, None, None, "dummy", 1234,
                                    live, {"model_stat": [1]}, results)
            self.assertEqual(send.call_count, 2)
            self.assertEqual([row["status"] for row in results], ["captured", "UNKNOWN"])
            self.assertEqual(runner.read_json(window / "attempt-01/OUTCOME.json"),
                             results[1])
            self.assertFalse((window / "attempt-02").exists())

    def test_smoke_predicate_requires_fresh_unmodified_native_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            here = Path(tmp)
            (here / "sha256.json").write_text("{}")
            window = here / "window-test"
            attempt = window / "attempt-00"
            attempt.mkdir(parents=True)
            request = self.cells[0]["body"]
            runner.atomic_json(here / "requests.json", self.cells)
            runner.atomic_json(attempt / "REQUEST.json", request)
            runner.atomic_json(attempt / "RESPONSE.json", self.terminal)
            outcome = {"unit": prepare.ARMS[0], "status": "captured",
                       **runner.read_terminal(json.dumps(self.terminal), request)}
            runner.atomic_json(attempt / "OUTCOME.json", outcome)
            summary = window / "SMOKE.json"
            runner.atomic_json(summary, {
                "row": prepare.ROW, "smoke": True, "status": "captured",
                "window": str(window), "server_exited": True, "completed": 1,
                "packet_manifest_sha256": runner.digest(here / "sha256.json"),
                "files_sha256": {str(path.relative_to(window)): runner.digest(path)
                                 for path in attempt.iterdir()},
                "outcomes": [outcome],
            })
            with patch.object(runner, "HERE", here):
                self.assertTrue(runner.qualified(summary, prepare.ARMS[:1], smoke=True))
                self.assertFalse(runner.qualified(summary, prepare.ARMS[:1], smoke=True,
                                                  started=summary.stat().st_mtime + 1))
                (attempt / "RESPONSE.json").write_text('{"mutated": true}')
                self.assertFalse(runner.qualified(summary, prepare.ARMS[:1], smoke=True))


if __name__ == "__main__":
    unittest.main()
