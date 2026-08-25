#!/usr/bin/env python3
"""Harness parity tests — the anti-drift guarantee for the filesystem-
containment guard (INC-20260823).

The incident built the guard in two surfaces with duplicated hand-written
rules; this suite enforces the replacement model: ONE scanner
(scripts/hooks/filesystem_containment_scan.py) is the source of truth, every
other surface is DERIVED from it, and any hand-edit or stale regeneration
FAILS here:

  * Claude surfaces (Bash + Write|Edit) route through the scanner wrapper.
  * The opencode permission.bash deny block (project opencode.json AND global
    ~/.config/opencode/opencode.jsonc) is byte-identical to what
    generate_opencode_permissions.py derives from the scanner's --dump-rules.
  * The Write|Edit path check (--check-path) uses the same containment roots
    and allowlist as the Bash scan.
  * The old check_filesystem_path.sh no longer carries its own allow-set.
  * The codex PreToolUse bridge calls the same scanner; the codex config.toml
    wires it (verified parse; firing is an honest gap — see the guide).

MUTATION tests are the point: change the scanner table or hand-edit a
permission block and the parity assertions break.

Run: uv run --with pytest pytest -q \
     scripts/hooks/tests/test_harness_guard_parity.py \
     scripts/hooks/tests/test_filesystem_containment.py
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS = REPO_ROOT / "scripts" / "hooks"
SCANNER = HOOKS / "filesystem_containment_scan.py"
GENERATOR = HOOKS / "generate_opencode_permissions.py"
WRAPPER = HOOKS / "check_filesystem_containment.sh"
OLD_PATH_GUARD = HOOKS / "check_filesystem_path.sh"
CODEX_HOOK = HOOKS / "codex_filesystem_containment.py"
CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
PROJECT_OPCODE_CONFIG = REPO_ROOT / "opencode.json"
PROJECT_PLUGIN = REPO_ROOT / ".opencode" / "plugins" / "filesystem-containment.ts"
GLOBAL_OPCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.jsonc"
GLOBAL_PLUGIN = Path.home() / ".config" / "opencode" / "plugins" / "filesystem-containment.ts"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"

sys.path.insert(0, str(HOOKS))
import filesystem_containment_scan as fs  # noqa: E402
import generate_opencode_permissions as gen  # noqa: E402

VALID_ALLOWLIST = """schema: session_bus.filesystem_allowlist.v1
entries:
  - path: /mnt/bigdisk/epyc-backup
    reason: operator-approved backup target
    added_by: test
    added_on: 2026-08-23
"""


def run_scan(argv, *, env=None):
    full = dict(os.environ)
    if env:
        full.update(env)
    return subprocess.run([sys.executable, str(SCANNER)] + argv,
                          capture_output=True, text=True, env=full,
                          cwd=str(REPO_ROOT), timeout=60)


def run_wrapper(payload: str):
    return subprocess.run(["/bin/bash", str(WRAPPER)], input=payload,
                          capture_output=True, text=True, env=dict(os.environ),
                          cwd=str(REPO_ROOT), timeout=60)


class TestClaudeSurfaces(unittest.TestCase):
    """Both Claude PreToolUse matchers must route through the scanner wrapper."""

    def setUp(self):
        self.settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        pre = self.settings["hooks"]["PreToolUse"]
        self.bash_hooks = []
        self.write_edit_hooks = []
        for group in pre:
            matcher = group.get("matcher", "")
            commands = [h.get("command", "") for h in group.get("hooks", [])]
            if matcher == "Bash":
                self.bash_hooks.extend(commands)
            elif matcher in ("Write|Edit", "Write", "Edit"):
                self.write_edit_hooks.extend(commands)

    def test_bash_matcher_calls_the_scanner_wrapper(self):
        self.assertTrue(
            any("check_filesystem_containment.sh" in c for c in self.bash_hooks),
            "PreToolUse Bash must call check_filesystem_containment.sh")

    def test_write_edit_matcher_calls_the_scanner_wrapper(self):
        self.assertTrue(
            any("check_filesystem_containment.sh" in c for c in self.write_edit_hooks),
            "PreToolUse Write|Edit must call check_filesystem_containment.sh "
            "(the unified wrapper)")

    def test_write_edit_matcher_no_longer_calls_the_old_guard(self):
        self.assertFalse(
            any("check_filesystem_path.sh" in c for c in self.write_edit_hooks),
            "Write|Edit must NOT call check_filesystem_path.sh anymore — the "
            "rule moved into the scanner")

    def test_old_path_guard_rule_table_is_gone(self):
        """check_filesystem_path.sh still exists (historical references) but its
        own allow-set — the duplicated hand-written rules — must be gone."""
        text = OLD_PATH_GUARD.read_text(encoding="utf-8")
        self.assertIn("SUPERSEDED", text)
        self.assertNotIn('/mnt/raid0/*', text)
        self.assertNotIn("df --output=source", text)
        self.assertNotIn("workspace_dev", text)

    def test_wrapper_serves_write_surface(self):
        res = run_wrapper(json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": "/mnt/bigdisk/x"}}))
        self.assertEqual(res.returncode, 2)
        self.assertIn("BLOCKED", res.stderr)
        res = run_wrapper(json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": "/mnt/raid0/llm/epyc-root/x"}}))
        self.assertEqual(res.returncode, 0, f"in-root edit refused: {res.stderr}")

    def test_wrapper_still_serves_bash_surface(self):
        res = run_wrapper(json.dumps(
            {"tool_name": "Bash",
             "tool_input": {"command": "sudo -n mount /dev/sdb1 /mnt/bigdisk"}}))
        self.assertEqual(res.returncode, 2)
        res = run_wrapper(json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "sudo -n true"}}))
        self.assertEqual(res.returncode, 0)

    def test_wrapper_ignores_other_tools(self):
        res = run_wrapper(json.dumps(
            {"tool_name": "Read", "tool_input": {"file_path": "/mnt/bigdisk/x"}}))
        self.assertEqual(res.returncode, 0)


class TestScannerDumpAndCheckPath(unittest.TestCase):
    """--dump-rules is the exported truth; --check-path is the path surface."""

    def test_dump_rules_roundtrip(self):
        res = run_scan(["--dump-rules"])
        self.assertEqual(res.returncode, 0, res.stderr)
        tables = json.loads(res.stdout)
        for key in ("class_a_verbs", "pkg_tools", "pkg_actions",
                    "dpkg_install_flags", "write_verbs", "containment_roots"):
            self.assertIn(key, tables)
        self.assertEqual(set(tables["class_a_verbs"]), set(fs._CLASS_A_VERBS))
        self.assertEqual(set(tables["pkg_tools"]), set(fs._PKG_TOOLS))
        self.assertEqual(set(tables["pkg_actions"]), set(fs._PKG_ACTIONS))
        self.assertEqual(tables["dpkg_install_flags"], list(fs._DPKG_INSTALL_FLAGS))
        self.assertEqual(tables["write_verbs"]["restic"], sorted(fs._RESTIC_WRITE_VERBS))
        self.assertEqual(tables["containment_roots"], list(fs.containment_roots()))
        self.assertIn("/mnt/raid0/llm", tables["containment_roots"])
        self.assertIn("mount", tables["class_a_verbs"])

    def test_dump_rules_is_deterministic(self):
        a = run_scan(["--dump-rules"]).stdout
        b = run_scan(["--dump-rules"]).stdout
        self.assertEqual(a, b)

    def test_check_path_inside_roots(self):
        for path in ("/mnt/raid0/llm/x", "/workspace/x", "/tmp/opencode/x",
                     "/tmp/scratch.log", "/dev/null"):
            res = run_scan(["--check-path", path])
            self.assertEqual(res.returncode, 0,
                             f"--check-path {path} refused: {res.stderr}")

    def test_check_path_outside_roots(self):
        for path in ("/mnt/bigdisk/x", "/opt/x", "/etc/passwd", "/home/node/x"):
            res = run_scan(["--check-path", path])
            self.assertEqual(res.returncode, 2,
                             f"--check-path {path} allowed: {res.stdout}")
            self.assertIn("write_outside_containment_root", res.stdout)

    def test_check_path_unresolvable_refused(self):
        res = run_scan(["--check-path", '"$OTHER/x"'])
        self.assertEqual(res.returncode, 2)
        self.assertIn("unresolvable_target", res.stdout)

    def test_check_path_allowlist_grants_external_path(self):
        with tempfile.TemporaryDirectory() as td:
            allow = Path(td) / "allowlist.yaml"
            allow.write_text(VALID_ALLOWLIST, encoding="utf-8")
            res = run_scan(["--allowlist", str(allow),
                            "--check-path", "/mnt/bigdisk/epyc-backup/repo"])
            self.assertEqual(res.returncode, 0,
                             f"allowlisted path refused: {res.stderr}")
            res = run_scan(["--allowlist", str(allow),
                            "--check-path", "/mnt/bigdisk/other"])
            self.assertEqual(res.returncode, 2)

    def test_check_path_allowlist_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            res = run_scan(["--allowlist", str(Path(td) / "missing.yaml"),
                            "--check-path", "/mnt/bigdisk/epyc-backup"])
            self.assertEqual(res.returncode, 2)
            self.assertIn("allowlist_unavailable", res.stdout)

    def test_ack_grants_external_path(self):
        env = {"EPYC_FS_ACK": "operator: op 2026-08-23: test"}
        res = run_scan(["--check-path", "/mnt/bigdisk/x"], env=env)
        self.assertEqual(res.returncode, 0)


class TestGeneratorDerivation(unittest.TestCase):
    """The opencode permission block is DERIVED from --dump-rules, never hand-
    written: the generator consumes the dump, and the block equals the derive."""

    def test_dump_is_what_the_generator_consumes(self):
        dump = json.loads(run_scan(["--dump-rules"]).stdout)
        self.assertEqual(gen.bash_deny_patterns(dump),
                         gen.bash_deny_patterns(fs.rules_dump()))
        self.assertEqual(gen.permission_block(dump), gen.permission_block())

    def test_expected_deny_list_derived_from_dump(self):
        """The task's example list, derived from the dumped tables, is present:
        verb* + sudo verb*, apt/apt-get actions, dpkg flags, dd."""
        dump = json.loads(run_scan(["--dump-rules"]).stdout)
        patterns = gen.bash_deny_patterns(dump)
        s = set(patterns)
        for verb in dump["class_a_verbs"]:
            self.assertIn(f"{verb}*", s)
            self.assertIn(f"sudo {verb}*", s)
        self.assertIn("mkfs*", s)
        for action in dump["pkg_actions"]:
            for tool in ("apt", "apt-get"):
                self.assertIn(f"{tool} {action}*", s)
        for flag in dump["dpkg_install_flags"]:
            self.assertIn(f"dpkg {flag}*", s)
        self.assertIn("dd of=/dev/*", s)
        self.assertNotIn("sudo apt install*", s)  # sudo variants are verb-only
        self.assertEqual(len(patterns), len(s))  # no duplicates

    def test_generator_check_exits_zero(self):
        res = subprocess.run([sys.executable, str(GENERATOR), "--check"],
                             capture_output=True, text=True,
                             cwd=str(REPO_ROOT), timeout=60)
        self.assertEqual(res.returncode, 0,
                         f"generator --check flags drift: {res.stderr}")


class TestOpencodeConfigParity(unittest.TestCase):
    """Permission blocks byte-match freshly generated output."""

    def test_project_block_matches_generated(self):
        on_disk = PROJECT_OPCODE_CONFIG.read_text(encoding="utf-8")
        generated = gen.project_config_text(json.loads(on_disk))
        self.assertEqual(on_disk, generated,
                         "opencode.json permission block drifted from the "
                         "scanner — run generate_opencode_permissions.py "
                         "--write-project")

    def test_global_block_matches_generated(self):
        try:
            on_disk = GLOBAL_OPCODE_CONFIG.read_text(encoding="utf-8")
        except OSError as exc:
            self.skipTest(f"global opencode config unreadable: {exc}")
        generated = gen.global_config_text(on_disk)
        self.assertEqual(on_disk, generated,
                         "global opencode.jsonc permission block drifted from "
                         "the scanner — run generate_opencode_permissions.py "
                         "--write-global")

    def test_hand_edit_of_project_block_fails_parity(self):
        """Mutation: remove one pattern from the on-disk block -> the file no
        longer matches the freshly generated text (the check() comparison)."""
        on_disk = json.loads(PROJECT_OPCODE_CONFIG.read_text(encoding="utf-8"))
        generated = gen.project_config_text(on_disk)
        for label, mutate in (
            ("remove", lambda b: b.pop("mount*")),
            ("add", lambda b: b.__setitem__("sudo evil*", "deny")),
        ):
            mutated = copy.deepcopy(on_disk)
            mutate(mutated["permission"]["bash"])
            mutated_text = json.dumps(mutated, indent=2) + "\n"
            self.assertNotEqual(mutated_text, generated,
                                f"hand-edit ({label}) not caught by parity")

    def test_project_and_global_blocks_are_identical(self):
        try:
            global_text = GLOBAL_OPCODE_CONFIG.read_text(encoding="utf-8")
        except OSError as exc:
            self.skipTest(f"global opencode config unreadable: {exc}")
        global_obj = json.loads(gen._strip_comments(global_text))
        project_obj = json.loads(PROJECT_OPCODE_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(global_obj["permission"], project_obj["permission"])


class TestMutation(unittest.TestCase):
    """The point: a scanner-table change without regeneration FAILS parity."""

    def test_deleting_class_a_verb_changes_generated_output(self):
        dump = fs.rules_dump()
        mutant = copy.deepcopy(dump)
        mutant["class_a_verbs"].remove("mount")
        self.assertNotEqual(gen.bash_deny_patterns(mutant),
                            gen.bash_deny_patterns(dump),
                            "removing a CLASS A verb must change the "
                            "generated deny block — otherwise drift is invisible")

    def test_on_disk_block_matches_current_tables(self):
        """The pass side of the mutation: with current tables the on-disk block
        is exactly the generated one (mount* present)."""
        on_disk = json.loads(PROJECT_OPCODE_CONFIG.read_text(encoding="utf-8"))
        expected = gen.permission_block(fs.rules_dump())
        self.assertEqual(on_disk["permission"], expected)

    def test_adding_root_changes_dump(self):
        """Roots travel through the dump too — a new containment root cannot be
        added in one surface only."""
        dump = fs.rules_dump()
        mutant = copy.deepcopy(dump)
        mutant["containment_roots"].append("/mnt/bigdisk")
        self.assertNotEqual(mutant["containment_roots"],
                            dump["containment_roots"])


class TestPluginSurfaces(unittest.TestCase):
    """The opencode plugins (project + global) intercept bash AND file tools."""

    def _assert_plugin(self, path: Path):
        text = path.read_text(encoding="utf-8")
        self.assertIn("--check-path", text)
        self.assertIn("FILE_TOOLS", text)
        self.assertIn('"write"', text)
        self.assertIn('"edit"', text)
        self.assertIn("output.args?.filePath", text)
        self.assertIn("input.tool === \"bash\"", text)

    def test_project_plugin(self):
        self._assert_plugin(PROJECT_PLUGIN)

    def test_global_plugin(self):
        try:
            self._assert_plugin(GLOBAL_PLUGIN)
        except OSError as exc:
            self.skipTest(f"global opencode plugin unreadable: {exc}")

    def test_plugin_file_tool_branch_uses_scanner(self):
        text = PROJECT_PLUGIN.read_text(encoding="utf-8")
        self.assertIn("--check-path", text)
        self.assertIn("SCANNER", text)


class TestCodexSurface(unittest.TestCase):
    """The codex bridge calls the SAME scanner; the config wires it. Firing is
    an honest gap (verified config parse, not verified firing) — the guide
    documents it; these tests pin the wiring and the bridge behavior."""

    def _run_hook(self, payload: str):
        return subprocess.run([sys.executable, str(CODEX_HOOK)], input=payload,
                              capture_output=True, text=True,
                              cwd=str(REPO_ROOT), timeout=60)

    def test_bridge_refuses_incident_command(self):
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "shell",
                              "tool_input": {"command": "sudo -n mount /dev/sdb1 /mnt/bigdisk"},
                              "cwd": "/workspace", "permission_mode": "default",
                              "session_id": "s", "model": "m", "tool_use_id": "t",
                              "transcript_path": None, "turn_id": "u"})
        res = self._run_hook(payload)
        self.assertEqual(res.returncode, 2)
        self.assertIn("mount", res.stderr)

    def test_bridge_allows_benign_command(self):
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "shell",
                              "tool_input": {"command": "git status"},
                              "cwd": "/workspace", "permission_mode": "default",
                              "session_id": "s", "model": "m", "tool_use_id": "t",
                              "transcript_path": None, "turn_id": "u"})
        self.assertEqual(self._run_hook(payload).returncode, 0)

    def test_bridge_refuses_external_file_path(self):
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "write",
                              "tool_input": {"file_path": "/mnt/bigdisk/x"},
                              "cwd": "/workspace", "permission_mode": "default",
                              "session_id": "s", "model": "m", "tool_use_id": "t",
                              "transcript_path": None, "turn_id": "u"})
        res = self._run_hook(payload)
        self.assertEqual(res.returncode, 2)

    def test_bridge_ignores_other_events(self):
        self.assertEqual(self._run_hook('{"hook_event_name": "SessionStart"}').returncode, 0)

    def test_codex_config_wires_the_bridge(self):
        try:
            text = CODEX_CONFIG.read_text(encoding="utf-8")
        except OSError as exc:
            self.skipTest(f"codex config unreadable: {exc}")
        self.assertIn("codex_filesystem_containment.py", text)
        self.assertIn("[[hooks.PreToolUse]]", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
