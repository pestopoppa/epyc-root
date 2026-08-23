#!/usr/bin/env python3
"""Tests for the filesystem containment guard (INC-20260823).

Incident (2026-08-23): an agent ran
    sudo -n mkdir -p /mnt/bigdisk && sudo -n mount /dev/sdb1 /mnt/bigdisk
planned writes to /mnt/bigdisk/epyc-backup/, and `sudo apt-get install restic`,
against the operator directive "do not touch anything outside /mnt/raid0/llm/".
Nothing stopped it — the Bash surface had no guard (the Write|Edit-only
check_filesystem_path.sh reads tool_input.file_path; no Bash hook scanned
commands) and the opencode surface had no permissions and no plugins.

This suite tests the ONE shared scanner both surfaces call, plus the Claude
wrapper. The interesting cases are the MUTATION ones (proving the check, not
the fixture, is what refuses) and the ack ones (proving the env-ack cannot be
forged inside the command text).

Run: uv run --with pytest pytest -q scripts/hooks/tests/test_filesystem_containment.py
(For the PyYAML path of the allowlist loader, add --with pyyaml; without it the
strict parser is exercised, which is what the plain command above runs.)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS = REPO_ROOT / "scripts" / "hooks"
SCANNER = HOOKS / "filesystem_containment_scan.py"
WRAPPER = HOOKS / "check_filesystem_containment.sh"
SHIPPED_ALLOWLIST = HOOKS / "filesystem_allowlist.yaml"

sys.path.insert(0, str(HOOKS))
import filesystem_containment_scan as fs  # noqa: E402

VALID_ALLOWLIST = """schema: session_bus.filesystem_allowlist.v1
entries:
  - path: /mnt/bigdisk/epyc-backup
    reason: operator-approved backup target
    added_by: test
    added_on: 2026-08-23
"""

INCIDENT_CMD = "sudo -n mkdir -p /mnt/bigdisk && sudo -n mount /dev/sdb1 /mnt/bigdisk"


def run_scan(cmd, *, argv=None, env=None, cwd=None):
    full = dict(os.environ)
    if env:
        full.update(env)
    return subprocess.run(
        [sys.executable, str(SCANNER)] + (argv or ["--command", cmd]),
        capture_output=True, text=True, env=full,
        cwd=str(cwd or REPO_ROOT), timeout=60)


def run_scan_stdin(payload: str, *, env=None):
    full = dict(os.environ)
    if env:
        full.update(env)
    return subprocess.run(
        [sys.executable, str(SCANNER)], input=payload,
        capture_output=True, text=True, env=full, cwd=str(REPO_ROOT), timeout=60)


def verdict_of(res) -> dict:
    try:
        return json.loads(res.stdout.splitlines()[-1] if res.stdout else "")
    except (json.JSONDecodeError, IndexError):
        return {}


def write_allowlist(tmp: Path, body: str) -> Path:
    p = tmp / "allowlist.yaml"
    p.write_text(body, encoding="utf-8")
    return p


class TestClassA(unittest.TestCase):
    """Privileged host-level operations — operator-only, refused either way."""

    def assert_refused(self, res, code=None, tool=None):
        self.assertEqual(res.returncode, 2, f"expected refusal, rc={res.returncode}: {res.stderr}")
        if code is not None:
            self.assertEqual(verdict_of(res).get("code"), code)
        if tool is not None:
            self.assertEqual(verdict_of(res).get("tool"), tool)

    def test_sudo_mount_refused(self):
        self.assert_refused(run_scan("sudo -n mount /dev/sdb1 /mnt/bigdisk"),
                            "host_level_privileged_operation", "mount")

    def test_bare_mount_refused(self):
        """No sudo needed — mount is operator-only, period."""
        self.assert_refused(run_scan("mount /dev/sdb1 /mnt/bigdisk"),
                            "host_level_privileged_operation", "mount")

    def test_sudo_mkdir_outside_root_refused(self):
        """sudo + mkdir outside root: both classes apply; refuse."""
        self.assert_refused(run_scan("sudo -n mkdir -p /mnt/bigdisk"),
                            "write_outside_containment_root", "mkdir")

    def test_apt_get_install_refused(self):
        self.assert_refused(run_scan("apt-get install -y restic"),
                            "host_level_privileged_operation", "apt-get install")

    def test_apt_install_refused(self):
        self.assert_refused(run_scan("sudo apt install tree"),
                            "host_level_privileged_operation", "apt install")

    def test_dpkg_install_refused(self):
        self.assert_refused(run_scan("dpkg -i something.deb"),
                            "host_level_privileged_operation", "dpkg -i")

    def test_systemctl_refused(self):
        self.assert_refused(run_scan("systemctl restart x"),
                            "host_level_privileged_operation", "systemctl")

    def test_dd_device_refused(self):
        self.assert_refused(run_scan("dd if=/dev/zero of=/dev/sda2 bs=1M count=10"),
                            "host_level_privileged_operation", "dd of=/dev/sda2")

    def test_mkfs_refused(self):
        self.assert_refused(run_scan("sudo mkfs.ext4 /dev/sdb1"),
                            "host_level_privileged_operation", "mkfs.ext4")

    def test_umount_refused(self):
        self.assert_refused(run_scan("umount /mnt/bigdisk"),
                            "host_level_privileged_operation", "umount")

    def test_incident_command_refused_naming_mount(self):
        res = run_scan(INCIDENT_CMD)
        self.assertEqual(res.returncode, 2)
        v = verdict_of(res)
        self.assertEqual(v.get("code"), "host_level_privileged_operation")
        self.assertEqual(v.get("tool"), "mount")

    def test_sudo_true_allowed(self):
        res = run_scan("sudo -n true")
        self.assertEqual(res.returncode, 0)

    def test_runners_and_timeouts_still_reveal_the_verb(self):
        self.assert_refused(run_scan("timeout 5s mount /dev/sdb1 /mnt/bigdisk"),
                            "host_level_privileged_operation", "mount")
        self.assert_refused(run_scan("env -i sudo mount /dev/sdb1 /mnt/bigdisk"),
                            "host_level_privileged_operation", "mount")

    def test_verb_position_not_word_anywhere(self):
        """The C21 lesson: `grep mount fstab` is not a mount invocation."""
        res = run_scan("grep mount /etc/fstab && cat /proc/mounts")
        self.assertEqual(res.returncode, 0)


class TestClassB(unittest.TestCase):
    """Writes outside the containment root — refused, path named."""

    def assert_refused(self, res, code="write_outside_containment_root"):
        self.assertEqual(res.returncode, 2, f"expected refusal, rc={res.returncode}: {res.stderr}")
        self.assertEqual(verdict_of(res).get("code"), code)

    def test_mkdir_bigdisk_refused(self):
        res = run_scan("mkdir -p /mnt/bigdisk/epyc-backup")
        self.assert_refused(res)
        self.assertIn("/mnt/bigdisk/epyc-backup", verdict_of(res).get("detail", ""))

    def test_restic_repo_outside_refused(self):
        self.assert_refused(run_scan(
            "restic backup --repo /mnt/bigdisk/epyc-backup/repo /mnt/raid0/llm"))

    def test_restic_without_repo_refused_unresolvable(self):
        self.assert_refused(run_scan("restic backup /mnt/raid0/llm"),
                            "unresolvable_target")

    def test_cp_to_opt_refused(self):
        self.assert_refused(run_scan("cp /etc/passwd /opt/x"))

    def test_tee_outside_refused(self):
        self.assert_refused(run_scan("tee /mnt/bigdisk/x"))

    def test_redirection_outside_refused(self):
        self.assert_refused(run_scan("echo hi > /mnt/bigdisk/x"))

    def test_append_outside_refused(self):
        self.assert_refused(run_scan("echo hi >> /mnt/bigdisk/x"))

    def test_rm_outside_refused(self):
        self.assert_refused(run_scan("rm -rf /mnt/bigdisk"))

    def test_tar_c_outside_refused(self):
        self.assert_refused(run_scan("tar -C /mnt/bigdisk -xzf x.tgz"))

    def test_chown_outside_refused(self):
        self.assert_refused(run_scan("chown -R daemon:daemon /mnt/bigdisk"))

    def test_borg_outside_refused(self):
        self.assert_refused(run_scan("borg create /mnt/bigdisk/repo::a /mnt/raid0/llm/data"))

    def test_rclone_remote_refused_unresolvable(self):
        self.assert_refused(run_scan("rclone copy /mnt/raid0/llm/data backup:/x"),
                            "unresolvable_target")

    def test_git_clone_outside_refused(self):
        self.assert_refused(run_scan("git clone https://github.com/x/y.git /mnt/bigdisk/y"))

    def test_variable_target_refused_unresolvable(self):
        self.assert_refused(run_scan("mkdir -p $DEST/x"), "unresolvable_target")

    def test_quoted_target_refused_unresolvable(self):
        self.assert_refused(run_scan('mkdir -p "/mnt/bigdisk/x"'), "unresolvable_target")

    def test_cd_then_relative_write_refused(self):
        """`cd /mnt/bigdisk && mkdir -p x` resolves x against the device."""
        self.assert_refused(run_scan("cd /mnt/bigdisk && mkdir -p x"))


class TestAllowed(unittest.TestCase):
    """The compliant path — a guard that forbids its own idiom is a defect."""

    def assert_allowed(self, res):
        self.assertEqual(res.returncode, 0,
                         f"expected allow, rc={res.returncode}: {res.stderr}")

    def test_mkdir_in_root_allowed(self):
        self.assert_allowed(run_scan("mkdir -p /mnt/raid0/llm/data/x"))

    def test_cp_to_workspace_allowed(self):
        self.assert_allowed(run_scan("cp x /workspace/tmp/"))

    def test_approved_scratch_allowed(self):
        self.assert_allowed(run_scan("echo x > /tmp/opencode/x"))

    def test_bare_tmp_scratch_allowed(self):
        """Chosen /tmp policy: bare /tmp/** is tolerated ephemeral scratch."""
        self.assert_allowed(run_scan("echo x > /tmp/scratch.log"))
        self.assert_allowed(run_scan("rm -rf /tmp/build-cache"))

    def test_python_script_allowed(self):
        self.assert_allowed(run_scan("python3 scripts/coordination/x.py"))

    def test_git_commit_allowed(self):
        self.assert_allowed(run_scan("git commit -m 'x' -- some/file"))

    def test_git_clone_in_root_allowed(self):
        self.assert_allowed(run_scan("git clone https://github.com/x/y.git /mnt/raid0/llm/data/y"))

    def test_restic_snapshots_read_allowed(self):
        self.assert_allowed(run_scan("restic snapshots --repo /mnt/raid0/llm/backup"))

    def test_dd_to_dev_null_allowed(self):
        self.assert_allowed(run_scan("dd if=/dev/zero of=/dev/null bs=1M count=1"))

    def test_apt_update_allowed(self):
        """Only install/remove/purge are refused — the enumerated class."""
        self.assert_allowed(run_scan("apt update"))

    def test_home_config_allowed(self):
        self.assert_allowed(run_scan("mkdir -p $HOME/.claude/x"))
        self.assert_allowed(run_scan("mkdir -p $HOME/.codex/x"))

    def test_relative_target_in_root_cwd_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            res = run_scan("mkdir -p out/x", cwd=cwd)
            self.assert_allowed(res)


class TestAck(unittest.TestCase):
    """The operator escape hatch — visible in the record, never self-authored."""

    def test_env_ack_allows_privileged_operation(self):
        env = {"EPYC_FS_ACK": "operator: op 2026-08-23: measured backup mount"}
        res = run_scan("sudo mount /dev/sdb1 /mnt/bigdisk", env=env)
        self.assertEqual(res.returncode, 0)
        v = verdict_of(res)
        self.assertEqual(v.get("verdict"), "allowed")
        self.assertIn("operator: op", v.get("ack", ""))

    def test_ack_embedded_in_command_text_still_refused(self):
        """The hook reads env, not command text — a command cannot self-authorize."""
        cmd = 'EPYC_FS_ACK="operator: self 2026-08-23: forged" sudo mount /dev/sdb1 /mnt/bigdisk'
        res = run_scan(cmd)
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "host_level_privileged_operation")

    def test_env_ack_allows_class_b_write(self):
        env = {"EPYC_FS_ACK": "operator: op 2026-08-23: emergency"}
        res = run_scan("mkdir -p /mnt/bigdisk/epyc-backup", env=env)
        self.assertEqual(res.returncode, 0)


class TestAllowlist(unittest.TestCase):
    """Operator-maintained path prefixes — CLASS B only, fail-closed on breakage."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_with(self, allowlist_path: Path, cmd: str, env=None):
        return run_scan(cmd, argv=["--allowlist", str(allowlist_path), "--command", cmd],
                        env=env)

    def test_allowlisted_prefix_allows(self):
        p = write_allowlist(self.tmp, VALID_ALLOWLIST)
        res = self.run_with(p, "mkdir -p /mnt/bigdisk/epyc-backup/x")
        self.assertEqual(res.returncode, 0,
                         f"allowlisted write refused: {res.stderr}")

    def test_unlisted_sibling_still_refused(self):
        p = write_allowlist(self.tmp, VALID_ALLOWLIST)
        res = self.run_with(p, "mkdir -p /mnt/bigdisk/other")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "write_outside_containment_root")

    def test_allowlist_never_opens_class_a(self):
        p = write_allowlist(self.tmp, VALID_ALLOWLIST)
        res = self.run_with(p, "sudo mount /dev/sdb1 /mnt/bigdisk")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "host_level_privileged_operation")

    def test_invalid_yaml_fails_closed(self):
        p = write_allowlist(self.tmp, "schema: session_bus.filesystem_allowlist.v1\nentries: [oops")
        res = self.run_with(p, "mkdir -p /mnt/bigdisk/epyc-backup")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "allowlist_unavailable")

    def test_missing_allowlist_fails_closed(self):
        res = self.run_with(self.tmp / "does-not-exist.yaml", "mkdir -p /mnt/bigdisk/epyc-backup")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "allowlist_unavailable")

    def test_wrong_schema_fails_closed(self):
        p = write_allowlist(self.tmp,
                            "schema: some_other.schema.v9\nentries: []\n")
        res = self.run_with(p, "mkdir -p /mnt/bigdisk/epyc-backup")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "allowlist_unavailable")

    def test_relative_entry_path_fails_closed(self):
        p = write_allowlist(self.tmp,
                            "schema: session_bus.filesystem_allowlist.v1\n"
                            "entries:\n  - path: relative/x\n    reason: r\n"
                            "    added_by: t\n    added_on: 2026-08-23\n")
        res = self.run_with(p, "mkdir -p /mnt/bigdisk/epyc-backup")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "allowlist_unavailable")

    def test_broken_allowlist_still_allows_in_root_writes(self):
        """Fail-closed means: no OUT-OF-ROOT writes. In-root writes stay open."""
        p = write_allowlist(self.tmp, "schema: session_bus.filesystem_allowlist.v1\nentries: [oops")
        res = self.run_with(p, "mkdir -p /mnt/raid0/llm/data/x")
        self.assertEqual(res.returncode, 0)


class TestAllowlistLoader(unittest.TestCase):
    """Unit coverage of the loader and its strict fallback parser."""

    def test_shipped_allowlist_is_valid_and_empty(self):
        prefixes = fs.load_allowlist(SHIPPED_ALLOWLIST)
        self.assertEqual(prefixes, [])

    def test_strict_parser_parses_the_documented_shape(self):
        with tempfile.TemporaryDirectory() as td:
            p = write_allowlist(Path(td), VALID_ALLOWLIST)
            self.assertEqual(fs.load_allowlist(p), [os.path.realpath("/mnt/bigdisk/epyc-backup")])

    def test_strict_parser_rejects_unknown_keys(self):
        with tempfile.TemporaryDirectory() as td:
            p = write_allowlist(Path(td), VALID_ALLOWLIST.replace("added_by: test",
                                                                  "hacked: yes"))
            self.assertIsNone(fs.load_allowlist(p))

    def test_strict_parser_rejects_tabs(self):
        with tempfile.TemporaryDirectory() as td:
            p = write_allowlist(Path(td), VALID_ALLOWLIST.replace("  - path:", "\t- path:"))
            self.assertIsNone(fs.load_allowlist(p))

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(fs.load_allowlist(Path(td) / "nope.yaml"))

    @unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "PyYAML not installed")
    def test_pyyaml_and_strict_parser_agree(self):
        """On machines with PyYAML, both loaders must parse the same file the same way."""
        import importlib
        importlib.invalidate_caches()
        import yaml
        with tempfile.TemporaryDirectory() as td:
            p = write_allowlist(Path(td), VALID_ALLOWLIST)
            strict = fs._parse_strict_yaml(p.read_text())
            data = yaml.safe_load(p.read_text())
            yaml_path = fs._validate_entries(data.get("entries"))
            self.assertEqual(strict, yaml_path)


class TestMutation(unittest.TestCase):
    """The point: the CHECK is what refuses. Remove it and the incident passes."""

    def _mutant(self, tmp: Path, old: str, new: str) -> Path:
        src = SCANNER.read_text(encoding="utf-8")
        assert old in src, f"mutation target not found in scanner source: {old!r}"
        out = tmp / "mutant_scan.py"
        out.write_text(src.replace(old, new), encoding="utf-8")
        (tmp / "shell_scan.py").write_text((HOOKS / "shell_scan.py").read_text(),
                                           encoding="utf-8")
        return out

    def _run_mutant(self, mutant: Path, cmd: str) -> int:
        res = subprocess.run(
            [sys.executable, str(mutant), "--allowlist", str(SHIPPED_ALLOWLIST),
             "--command", cmd],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=60)
        return res.returncode

    def test_commenting_out_class_a_passes_the_mount(self):
        """Disable the CLASS A check -> `sudo mount` sails through. Prove it."""
        with tempfile.TemporaryDirectory() as td:
            mutant = self._mutant(Path(td),
                                  "a = class_a_verdict(tokens, verb)",
                                  "a = None  # MUTATION: class A disabled")
            cmd = "sudo -n mount /dev/sdb1 /mnt/bigdisk"
            self.assertEqual(self._run_mutant(mutant, cmd), 0,
                             "mutant without the CLASS A check still refused — "
                             "the refusal is not coming from the check we think")
            self.assertEqual(run_scan(cmd).returncode, 2,
                             "the UNMUTATED scanner must still refuse (restore)")

    def test_commenting_out_class_b_passes_the_mkdir(self):
        """Disable the CLASS B check -> the /mnt/bigdisk mkdir sails through."""
        with tempfile.TemporaryDirectory() as td:
            mutant = self._mutant(
                Path(td),
                "b = class_b_verdict(seg, tokens, verb, verb_idx, vcwd, roots, allowlist)",
                "b = None  # MUTATION: class B disabled")
            cmd = "mkdir -p /mnt/bigdisk/epyc-backup"
            self.assertEqual(self._run_mutant(mutant, cmd), 0,
                             "mutant without the CLASS B check still refused")
            self.assertEqual(run_scan(cmd).returncode, 2,
                             "the UNMUTATED scanner must still refuse (restore)")


class TestCliShapes(unittest.TestCase):
    """Both surfaces call the scanner identically; the CLI must serve both."""

    def test_pre_tool_use_stdin_shape_refuses(self):
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": INCIDENT_CMD}})
        res = run_scan_stdin(payload)
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("tool"), "mount")

    def test_pre_tool_use_stdin_shape_allows(self):
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": "sudo -n true"}})
        self.assertEqual(run_scan_stdin(payload).returncode, 0)

    def test_plain_text_stdin_is_a_command(self):
        self.assertEqual(run_scan_stdin("mkdir -p /mnt/bigdisk").returncode, 2)

    def test_empty_input_never_produces_a_verdict(self):
        """The process_pattern_kill_scan.py defect: clean-for-unread-input is worse."""
        self.assertEqual(run_scan_stdin("").returncode, 2)
        res = run_scan("")
        self.assertEqual(res.returncode, 2)

    def test_cwd_flag_drives_relative_resolution(self):
        res = run_scan("mkdir -p x", argv=["--cwd", "/mnt/bigdisk", "--command", "mkdir -p x"])
        self.assertEqual(res.returncode, 2)
        self.assertEqual(verdict_of(res).get("code"), "write_outside_containment_root")


class TestClaudeWrapper(unittest.TestCase):
    """The PreToolUse wrapper — the Claude surface of the same scanner."""

    def run_wrapper(self, payload: str, env=None) -> subprocess.CompletedProcess:
        full = dict(os.environ)
        if env:
            full.update(env)
        return subprocess.run(["/bin/bash", str(WRAPPER)], input=payload,
                              capture_output=True, text=True, env=full,
                              cwd=str(REPO_ROOT), timeout=60)

    def test_refuses_incident_command(self):
        res = self.run_wrapper(json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": INCIDENT_CMD}}))
        self.assertEqual(res.returncode, 2)
        self.assertIn("BLOCKED", res.stderr)
        self.assertIn("mount", res.stderr)

    def test_allows_benign_command(self):
        res = self.run_wrapper(json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "sudo -n true && git status"}}))
        self.assertEqual(res.returncode, 0)

    def test_write_surface_routed_through_scanner(self):
        """Unified wrapper (2026-08-23): Write|Edit now runs --check-path with
        the SAME containment rules as Bash. The old check_filesystem_path.sh
        hand-written allow-set is gone; this file_path is outside the roots."""
        res = self.run_wrapper(json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": "/mnt/bigdisk/x"}}))
        self.assertEqual(res.returncode, 2)
        self.assertIn("BLOCKED", res.stderr)
        self.assertIn("/mnt/bigdisk/x", res.stderr)

    def test_write_in_root_allowed(self):
        res = self.run_wrapper(json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": "/mnt/raid0/llm/epyc-root/x"}}))
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_ignores_other_tools(self):
        res = self.run_wrapper(json.dumps(
            {"tool_name": "Read", "tool_input": {"file_path": "/mnt/bigdisk/x"}}))
        self.assertEqual(res.returncode, 0)

    def test_env_ack_passes_through(self):
        res = self.run_wrapper(json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "sudo mount /dev/sdb1 /mnt/bigdisk"}}),
            env={"EPYC_FS_ACK": "operator: op 2026-08-23: test"})
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
