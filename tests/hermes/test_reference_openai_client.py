from __future__ import annotations

import argparse
import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/hermes/reference_openai_client.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("reference_openai_client", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(**overrides):
    defaults = {
        "model": "orchestrator",
        "prompt": "Check routing.",
        "stream": False,
        "x_max_escalation": "B2",
        "x_disable_repl": True,
        "x_show_routing": False,
        "x_orchestrator_role": "frontdoor",
        "x_force_model": "",
        "demo_tool": False,
        "tools_json": [],
        "tool_choice": "",
        "tool_choice_json": "",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class ReferenceOpenAIClientTests(unittest.TestCase):
    def test_build_payload_includes_stream_and_custom_overrides(self):
        client = _load_module()

        payload = client._build_payload(
            _args(stream=True, x_show_routing=True, x_force_model="worker_general")
        )

        self.assertIs(payload["stream"], True)
        self.assertIs(payload["x_show_routing"], True)
        self.assertIs(payload["x_disable_repl"], True)
        self.assertEqual(payload["x_orchestrator_role"], "frontdoor")
        self.assertEqual(payload["x_force_model"], "worker_general")

    def test_build_payload_adds_demo_tool_and_auto_tool_choice(self):
        client = _load_module()

        payload = client._build_payload(_args(demo_tool=True))

        self.assertEqual(payload["tools"], [client.DEMO_NATIVE_TOOL])
        self.assertEqual(payload["tool_choice"], "auto")

    def test_build_payload_preserves_explicit_no_tool_choice(self):
        client = _load_module()

        payload = client._build_payload(_args(demo_tool=True, tool_choice="none"))

        self.assertEqual(payload["tools"], [client.DEMO_NATIVE_TOOL])
        self.assertEqual(payload["tool_choice"], "none")

    def test_build_payload_accepts_raw_tool_and_forced_tool_choice(self):
        client = _load_module()

        tool = '{"type":"function","function":{"name":"x","parameters":{"type":"object"}}}'
        choice = '{"type":"function","function":{"name":"x"}}'
        payload = client._build_payload(
            _args(tools_json=[tool], tool_choice_json=choice)
        )

        self.assertEqual(payload["tools"][0]["function"]["name"], "x")
        self.assertEqual(payload["tool_choice"]["function"]["name"], "x")

    def test_print_reference_keeps_standard_openai_fields_out_of_extra_body(self):
        client = _load_module()
        payload = client._build_payload(_args(stream=True, demo_tool=True))

        stream = io.StringIO()
        with redirect_stdout(stream):
            client._print_reference(
                payload, "http://127.0.0.1:8000/v1/chat/completions", "local"
            )

        output = stream.getvalue()
        sdk_section = output.split("Python (OpenAI-compatible SDK):", 1)[1]
        extra_body = sdk_section.split("extra_body=", 1)[1]
        self.assertIn("stream=True", sdk_section)
        self.assertIn("tools=", sdk_section)
        self.assertIn("tool_choice=", sdk_section)
        self.assertIn("x_max_escalation", extra_body)
        self.assertNotIn("'stream'", extra_body)
        self.assertNotIn("'tools'", extra_body)
        self.assertNotIn("'tool_choice'", extra_body)


if __name__ == "__main__":
    unittest.main()
