from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "scripts/hermes/plugins/epyc-orchestrator-overrides/__init__.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("epyc_orchestrator_overrides", PLUGIN)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._SESSION_OVERRIDES.clear()
    return module


class FakePluginContext:
    def __init__(self):
        self.commands = {}
        self.hooks = {}

    def register_command(self, *, name, handler, description, args_hint, aliases=()):
        self.commands[name] = {
            "handler": handler,
            "description": description,
            "args_hint": args_hint,
            "aliases": tuple(aliases),
        }

    def register_hook(self, name, handler):
        self.hooks[name] = handler


class EpycOrchestratorOverridesPluginTests(unittest.TestCase):
    def test_register_exposes_commands_and_pre_llm_hook(self):
        plugin = _load_module()
        ctx = FakePluginContext()

        plugin.register(ctx)

        self.assertEqual(
            set(ctx.commands),
            {"use", "escalation", "nocode", "epyc-overrides"},
        )
        self.assertEqual(ctx.commands["epyc-overrides"]["aliases"], ("epyc-routing",))
        self.assertIn("pre_llm_call", ctx.hooks)

    def test_commands_inject_session_scoped_extra_body(self):
        plugin = _load_module()

        context = {"session_id": "s1"}
        self.assertIn("architect_general", plugin._handle_use("biggest", context))
        self.assertIn("B1", plugin._handle_escalation("B1", context))
        self.assertIn("disabled", plugin._handle_nocode("", context))

        api_kwargs = {"extra_body": {"x_show_routing": True}}
        plugin._inject_overrides(session_id="s1", api_kwargs=api_kwargs)

        self.assertEqual(
            api_kwargs["extra_body"],
            {
                "x_show_routing": True,
                "x_orchestrator_role": "architect_general",
                "x_max_escalation": "B1",
                "x_disable_repl": True,
            },
        )

    def test_auto_commands_clear_only_their_own_override_family(self):
        plugin = _load_module()
        context = {"session_id": "s2"}

        plugin._handle_use("worker", context)
        plugin._handle_escalation("B2", context)
        plugin._handle_nocode("", context)
        plugin._handle_use("auto", context)
        plugin._handle_escalation("full", context)
        plugin._handle_nocode("off", context)

        api_kwargs = {"extra_body": {}}
        plugin._inject_overrides(session_id="s2", api_kwargs=api_kwargs)

        self.assertEqual(api_kwargs["extra_body"], {})


if __name__ == "__main__":
    unittest.main()
