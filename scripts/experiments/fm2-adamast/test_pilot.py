"""Run with a Python that has openai and httpx, using a local AdaMAST checkout.

Set FM2_ADAMAST_CHECKOUT if the pinned commit is in another clone. All requests
go to a loopback HTTP fixture and use a synthetic trace.
"""

import base64
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

import pilot

PACKET_SOURCE = Path(__file__).resolve().parent
ADAMAST_REV = "3c83d81c85937f5e8911fd96daa2ca38c1ad2585"
DEFAULT_CHECKOUT = "/mnt/raid0/llm/worktrees/rtg34-fm-20261110-scratch/adamast-upstream"
VALID_REPLY = '{"failure_modes":[],"none_apply":true}'
UNIT_ID = "claude-fixture"


@contextmanager
def fixture_endpoint(content, status=200):
    requests = []
    response = json.dumps({
        "id": "chatcmpl-fm2-fixture", "object": "chat.completion", "created": 1, "model": "local-fm2",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
    }).encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.append((self.path, self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1", requests, response
        finally:
            server.shutdown()
            thread.join()


class PilotTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        checkout = Path(os.environ.get("FM2_ADAMAST_CHECKOUT", DEFAULT_CHECKOUT))
        if not checkout.exists():
            raise unittest.SkipTest("set FM2_ADAMAST_CHECKOUT to a local clone containing the pinned commit")
        try:
            import httpx  # noqa: F401
            import openai  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"use a Python with the OpenAI transport dependencies: {exc}") from exc
        scratch = Path(os.environ.get("FM2_TEST_ROOT", "/mnt/raid0/llm/tmp/coordination-and-churn-pipeline/tests"))
        scratch.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix="fm2-pilot-test-", dir=scratch)
        cls.addClassCleanup(directory.cleanup)
        cls.root = Path(directory.name)
        cls.code = cls.root / "code"
        cls.code.mkdir()
        archive = subprocess.check_output(["git", "-C", str(checkout), "archive", ADAMAST_REV, "adamast"])
        subprocess.run(["tar", "-x", "-C", str(cls.code)], input=archive, check=True)
        subprocess.run(["git", "apply", str(PACKET_SOURCE / "adamast_local.patch")], cwd=cls.code, check=True)
        shutil.copyfile(PACKET_SOURCE / "fm2_transport.py", cls.code / "fm2_transport.py")
        traces = cls.root / "inputs" / "traces"
        traces.mkdir(parents=True)
        cls.trace = traces / f"{UNIT_ID}.jsonl"
        cls.trace.write_text(json.dumps({
            "problem_id": UNIT_ID, "task": "Check the synthetic receipt",
            "raw_trajectory": '{"role":"assistant","content":"I checked the receipt."}',
            "metadata": {"stratum": "claude|2026-11|main", "source_sha256": "a" * 64},
        }) + "\n")
        (cls.code / "pins.json").write_text(json.dumps({"smoke_unit": UNIT_ID}))
        (cls.root / "SOURCE.sha256").write_text("synthetic test packet\n")

    def setUp(self):
        self.output = self.root / self._testMethodName
        self.output.mkdir()
        for name, value in {"CODE": self.code, "ROOT": self.root, "capture_runtime": dict}.items():
            patcher = patch.object(pilot, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        path_patch = patch.object(sys, "path", [str(self.code), *sys.path])
        path_patch.start()
        self.addCleanup(path_patch.stop)
        environment = patch.dict(os.environ, {
            "OPENAI_API_KEY": "mock-local",
            "FM2_SERVER_PID": str(os.getpid()),
            "FM2_SERVER_LOG": "mock-server",
            "FILLER_DRYRUN": "1",
            "FILLER_DRYRUN_DIR": str(self.output),
            "FILLER_DRYRUN_RESULT_PATH": str(self.output / "native-result.json"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        environment.start()
        self.addCleanup(environment.stop)

    def test_valid_smoke_journals_exact_bodies_and_resumes_without_a_call(self):
        with fixture_endpoint(VALID_REPLY) as (endpoint, requests, response):
            with patch.dict(os.environ, ADAMAST_BASE_URL=endpoint):
                self.assertEqual(pilot.smoke(), 1)
                self.assertEqual(pilot.run(), 0)
                self.assertEqual(pilot.smoke(), 0)
                self.assertEqual(pilot.run(), 0)
            [(path, body)] = requests
            self.assertEqual(path, "/v1/chat/completions")
            unit = self.output / "unit"
            request = pilot.load(unit / "request.json")
            reply = pilot.load(unit / "response.json")
            self.assertEqual(base64.b64decode(request["body_b64"]), body)
            self.assertEqual(base64.b64decode(reply["body_b64"]), response)
            self.assertLessEqual(request["sent_at"], reply["received_at"])
            payload = json.loads(body)
            self.assertEqual(payload["response_format"], {"type": "json_object"})
            self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
            self.assertEqual(payload["max_completion_tokens"], 768)
            self.assertFalse((self.root / "out").exists())

    def test_malformed_model_reply_is_preserved_and_never_repaired(self):
        with fixture_endpoint("malformed mode receipt") as (endpoint, requests, response):
            with patch.dict(os.environ, ADAMAST_BASE_URL=endpoint):
                self.assertEqual(pilot.run(), 5)
                self.assertEqual(pilot.smoke(), 1)
                self.assertEqual(pilot.run(), 5)
            self.assertEqual(len(requests), 1)
            unit = self.output / "unit"
            self.assertEqual(pilot.load(unit / "receipt.json")["status"], "parse_or_schema_failure")
            self.assertEqual(base64.b64decode(pilot.load(unit / "response.json")["body_b64"]), response)
            self.assertTrue(pilot.load(unit / "diagnosis.json")["diagnoses"][0]["judge_metadata"]["warnings"])
            self.assertFalse((self.output / "native-result.json").exists())

    def test_transport_failure_does_not_retry(self):
        with fixture_endpoint(VALID_REPLY, status=500) as (endpoint, requests, _):
            with patch.dict(os.environ, ADAMAST_BASE_URL=endpoint):
                self.assertEqual(pilot.run(), 5)
            self.assertEqual(len(requests), 1)
            unit = self.output / "unit"
            self.assertEqual(pilot.load(unit / "receipt.json")["status"], "transport_or_reply_failure")
            self.assertEqual(pilot.load(unit / "response.json")["status"], 500)

    def test_interrupted_request_is_not_sent_again(self):
        unit = self.output / "unit"
        unit.mkdir()
        (unit / "request.json").write_text('{"fixture":"previously journaled"}\n')
        with fixture_endpoint(VALID_REPLY) as (endpoint, requests, _):
            with patch.dict(os.environ, ADAMAST_BASE_URL=endpoint):
                self.assertEqual(pilot.run(), 5)
            self.assertEqual(requests, [])
            self.assertEqual(pilot.load(unit / "receipt.json")["status"], "interrupted")


class PilotStatisticsTest(unittest.TestCase):
    def test_wilson_bounds_and_empty_denominator(self):
        self.assertIsNone(pilot.wilson95(0, 0))
        lower, upper = pilot.wilson95(0, 3)
        self.assertAlmostEqual(lower, 0.0)
        self.assertAlmostEqual(upper, 0.561497, places=6)

    def test_futility_starts_at_eight_and_excludes_exactly_one_quarter(self):
        good = {"ok": True}
        bad = {"ok": False}
        self.assertFalse(pilot.failed([bad] * 7))
        self.assertFalse(pilot.failed([bad] * 2 + [good] * 6))
        self.assertTrue(pilot.failed([bad] * 3 + [good] * 5))


if __name__ == "__main__":
    unittest.main()
