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

    def test_quoted_target_refused(self):
        """lex() now reads a quoted path's plain text, so this is refused as
        the out-of-root write it is (2026-10-07; before, only as unresolvable).
        A quoted special character (`$`, a space) is still never interpreted."""
        self.assert_refused(run_scan('mkdir -p "/mnt/bigdisk/x"'))
        self.assert_refused(run_scan('mkdir -p "$D/x" "/mnt/raid0/llm/a b"'),
                            "unresolvable_target")

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


IN_ROOT = "/mnt/raid0/llm/epyc-root"   # a cwd inside the data root
OUT_ROOT = "/mnt/bigdisk/work"          # a cwd outside every root
OUT = "/mnt/bigdisk"


class TestOperandExtraction(unittest.TestCase):
    """2026-10-07: redirections, fd duplication and option values were read as
    write targets — and the real target was then never checked. The cwd is
    pinned on purpose: on the operator host it is usually inside a root, which
    masked the fd-dup and `git worktree add` defects (a wrong target that
    resolves into the cwd passes). Each case says which way it used to fail.
    """

    def check(self, cmds, cwd, allowed, code=None):
        for cmd in cmds:
            with self.subTest(cmd=cmd, cwd=cwd):
                v = fs.scan_command(cmd, cwd=cwd)
                self.assertEqual(v.get("verdict") == "allowed", allowed, f"{cmd!r}: {v}")
                if code is not None:
                    self.assertEqual(v.get("code"), code, f"{cmd!r}: {v}")

    def test_fd_duplication_is_not_a_file_write(self):
        """Was refused as a write to '<cwd>/1' / '<cwd>/2' / '<cwd>/&-'."""
        self.check(["echo hi 2>&1", "ls >&2", "ls 1>&2", "ls 2>&-", "exec 3>&1 4>&2",
                    "git status 2>&1 | head -5", "make >/dev/null 2>&1",
                    "out=$(ls 2>&1)"], OUT_ROOT, True)

    def test_file_forms_of_amp_redirection_are_writes(self):
        """`&>F`, `&>>F`, `>&F` (F not a number or `-`) write F; `x>F`, `>| F`
        and `>& F` used to slip past the old pattern entirely."""
        self.check([f"ls &>{OUT}/x", f"ls &>>{OUT}/x", f"ls >&{OUT}/x", f"ls >& {OUT}/x",
                    f"echo x>{OUT}/x", f"echo x >| {OUT}/x", f"exec 3<>{OUT}/x",
                    f"ls 2>&1 >{OUT}/x"], IN_ROOT, False, "write_outside_containment_root")
        self.check(["ls >&out.log"], OUT_ROOT, False)
        self.check(["ls &>/tmp/x", "cat < /etc/hosts"], OUT_ROOT, True)

    def test_redirection_words_are_not_operands(self):
        """`cp s /outside 2>/dev/null` checked '2>/dev/null' as the destination
        (inside an in-root cwd) and never '/outside' — a containment bypass."""
        self.check([f"cp secret {OUT}/x 2>/dev/null", f"cp secret {OUT}/x 2> /dev/null",
                    f"cp a {OUT}/x 2>&1", f"mv a {OUT}/x >/dev/null 2>&1",
                    f"tee {OUT}/x >/dev/null", f"2>/dev/null rm -rf {OUT}",
                    f">/dev/null cp a {OUT}/x"], IN_ROOT, False,
                   "write_outside_containment_root")
        self.check(["cp a /mnt/raid0/llm/b 2>/dev/null", "rm -rf /mnt/raid0/llm/x 2>&1",
                    "mkdir -p /mnt/raid0/llm/x 2>/dev/null",
                    "tee >(gzip > /mnt/raid0/llm/x.gz) < in"], OUT_ROOT, True)

    def test_git_worktree_add_checks_the_path_not_the_branch(self):
        """pos[-1] was the BRANCH: in-root path refused from an out-of-root cwd,
        out-of-root path ALLOWED from an in-root cwd."""
        self.check(["git worktree add /mnt/raid0/llm/wt mybranch",
                    "git worktree add -b nb /mnt/raid0/llm/wt main",
                    "git -C /mnt/raid0/llm/r worktree add ../wt -b br"], OUT_ROOT, True)
        self.check([f"git worktree add {OUT}/wt mybranch",
                    f"git worktree add -b nb {OUT}/wt main",
                    f"git worktree add --detach {OUT}/wt HEAD",
                    f"git -C /mnt/raid0/llm/r worktree add {OUT}/wt br",
                    f"git -C {OUT}/r init"], IN_ROOT, False, "write_outside_containment_root")
        self.check(["git init"], OUT_ROOT, False)   # initializes the cwd itself

    def test_git_clone_operand_forms(self):
        self.check([f"git clone https://x/y.git {OUT}/y --",
                    f"git clone -- https://x/y.git {OUT}/y",
                    f"git clone --separate-git-dir {OUT}/g https://x/y.git /mnt/raid0/llm/y"],
                   IN_ROOT, False, "write_outside_containment_root")
        self.check(["git clone https://x/y.git /mnt/raid0/llm/y --depth 1",
                    "git clone --depth 1 https://x/y.git /mnt/raid0/llm/y"], OUT_ROOT, True)
        self.check(["git clone https://x/y.git"], IN_ROOT, True)   # ./y, inside
        self.check(["git clone https://x/y.git"], OUT_ROOT, False)

    def test_target_directory_forms(self):
        """`-t` clustered (`-at DIR`), attached (`-tDIR`) or abbreviated
        (`--target=DIR`) was missed; `install -d` creates EVERY operand."""
        self.check([f"cp -t {OUT} src", f"cp -t{OUT} src", f"cp -at {OUT} src",
                    f"ln -st {OUT} src", f"mv --target={OUT} src", f"cp --targ {OUT} src",
                    f"install -m 644 -t {OUT} src",
                    f"install -d /mnt/raid0/llm/a {OUT}/b"], IN_ROOT, False)
        self.check(["cp -t /mnt/raid0/llm/d /etc/hosts"], OUT_ROOT, True)

    def test_boolean_flags_do_not_swallow_the_destination(self):
        """`rm -r /x`: -r was listed as taking a value, so /x was never checked."""
        self.check([f"rm -r {OUT}/x", f"rm -f {OUT}/x", f"rmdir -v {OUT}/x",
                    f"tee -a {OUT}/x", f"tee {OUT}/x /mnt/raid0/llm/y",
                    f"cp a --preserve {OUT}/x", f"cp a --no-target-directory {OUT}/x",
                    f"cp a -s {OUT}/x", f"cp a {OUT}/x --suf .bak",
                    f"chown u {OUT}/b /mnt/raid0/llm/a", f"chmod 644 {OUT}/b /mnt/raid0/llm/a",
                    f"cd -P {OUT} && mkdir x", f"borg create --stats {OUT}/r::a src",
                    f"borg --repo {OUT}/r create arch src",
                    f"rsync -av src/ {OUT}/d/ --exclude .git",
                    f"rclone copy /mnt/raid0/llm/x {OUT}/y --transfers 8",
                    f"tar czf {OUT}/b.tgz src", f"tar -czf {OUT}/b.tgz src",
                    f"tar -xzf x.tgz -C{OUT}", f"tar -xzf x.tgz --directory {OUT}"],
                   IN_ROOT, False, "write_outside_containment_root")
        self.check(["chown -R u:g /mnt/raid0/llm/d", "chmod +x /mnt/raid0/llm/s.sh",
                    "chmod -x /mnt/raid0/llm/s.sh", "mkdir -pm 755 /mnt/raid0/llm/x",
                    f"tar -xzf {OUT}/b.tgz -C /mnt/raid0/llm/out",   # reading an archive
                    "rsync -av --exclude .git src/ /mnt/raid0/llm/d/"], OUT_ROOT, True)

    def test_hidden_verbs_and_laundered_paths(self):
        """A lone `&` hid the next verb; `xargs -I{}` swallowed it; `"$D"/abs`
        was trimmed to `/abs`; a relative target after `cd $X` resolved
        against the OLD directory."""
        self.check([f"sleep 1 & mkdir {OUT}/x", f"xargs -I{{}} cp {{}} {OUT}/"],
                   IN_ROOT, False, "write_outside_containment_root")
        self.check(['cp a "$D"/mnt/raid0/llm/x', "cd $X && rm -rf data", "cd - && touch x"],
                   IN_ROOT, False, "unresolvable_target")
        self.check(["cd $X && rm -rf /mnt/raid0/llm/data", "sleep 5 & echo ok > /tmp/x"],
                   IN_ROOT, True)


class TestShellStructure(unittest.TestCase):
    """2026-10-07 security review of the fix above: the shell's own structure —
    escapes, continuations, heredocs, keywords, substitutions, subshells, -c
    strings, expansions, links — hid writes the operand rules never saw. Every
    refused case below was ALLOWED before (probed from both cwd kinds)."""

    check = TestOperandExtraction.check

    def test_escapes_continuations_and_quote_desync(self):
        """`\\`-newline split one command in two; `\\"`, `$'\\''` and `a\\ #`
        hid the rest of the line; `\\rm` was not rm; `.\\./` is `../`."""
        self.check([f"rsync -av \\\n  src/ \\\n  {OUT}/d/", f"mkdir -p \\\n{OUT}/x",
                    f"\\rm -rf {OUT}/x", f"r\\m -rf {OUT}/x",
                    f'echo \\" ; mkdir {OUT}/x ; echo \\"',
                    f"echo $'\\'' ; mkdir {OUT}/x ; echo $'\\''",
                    f"echo a\\ #; mkdir {OUT}/x", "cp a /mnt/raid0/llm/.\\./x"], IN_ROOT, False,
                   "write_outside_containment_root")
        self.check(["cp a /mnt/raid0/llm/my\\ file"], IN_ROOT, False, "unresolvable_target")

    def test_heredoc_markers_count_only_in_code(self):
        """A `<<EOF` in quotes, a comment or `$((1<<y))` opened a heredoc
        that blanked the real commands after it."""
        self.check([f'echo "<<EOF"\nmkdir {OUT}/x\nEOF', f"true # <<EOF\nmkdir {OUT}/x\nEOF",
                    f"echo $((1<<y))\nmkdir {OUT}/x\ny",
                    f"cat <<'EOF'\na \\\nEOF\nmkdir {OUT}/x"], IN_ROOT, False)
        # an unquoted delimiter joins `a \` + `EOF`: the mkdir line is body
        self.check([f"cat <<EOF\na \\\nEOF\nmkdir {OUT}/x\nEOF",
                    f"cat <<'EOF' > /tmp/x\nmkdir {OUT}/x\nEOF"], IN_ROOT, True)

    def test_keywords_wrappers_and_quoted_verbs_reveal_the_verb(self):
        self.check([f"for f in a; do cp $f {OUT}/; done", f"if mkdir {OUT}/x; then :; fi",
                    f"! mkdir {OUT}/x", f"exec mkdir {OUT}/x", f"eval mkdir {OUT}/x",
                    f"case a in a) rm -rf {OUT};; esac", f"f() {{ mkdir {OUT}/x; }}; f",
                    f'"mkdir" {OUT}/x', f'm"kd"ir {OUT}/x', f"sudo -nu root mkdir {OUT}/x",
                    f"env --unset=X mkdir {OUT}/x", f"numactl --interleave all mkdir {OUT}/x",
                    f"taskset 0x3 mkdir {OUT}/x", f"xargs -a list rm -rf {OUT}/x",
                    f"strace -o /tmp/l mkdir {OUT}/x", f'cp "-t" {OUT} a',
                    f'dd if=/dev/zero "of={OUT}/x"'], IN_ROOT, False,
                   "write_outside_containment_root")

    def test_substitutions_and_subshells_are_scanned_where_they_run(self):
        self.check([f"x=$(mkdir -p {OUT}/x)", f'echo "$(rm -rf {OUT})"', f"echo `rm -rf {OUT}`",
                    f"echo x > >(tee {OUT}/x)", f"cat <(mkdir {OUT}/x)"], IN_ROOT, False,
                   "write_outside_containment_root")
        self.check([f"echo '$(rm -rf {OUT})'", "diff <(ls) <(ls /tmp)", "out=$(ls 2>&1)",
                    f"(cd {OUT} && ls); touch notes"], IN_ROOT, True)
        # a cd in a subshell, a pipeline stage or the background does not persist
        self.check(["(cd /mnt/raid0/llm && ls); touch notes", "cd /mnt/raid0/llm | cat; touch n",
                    "cd /mnt/raid0/llm & touch n", "x=$(cd /mnt/raid0/llm); touch n"],
                   OUT_ROOT, False)

    def test_shell_strings_and_heredocs_fed_to_a_shell_are_commands(self):
        self.check([f"sudo sh -c 'echo x > {OUT}/f'", f'bash -lc "mkdir -p {OUT}/x"',
                    f"bash -c -x 'mkdir {OUT}/x'", f"su -c 'rm -rf {OUT}' root",
                    f"bash <<'EOF'\nmkdir {OUT}/x\nEOF", f"bash <<< 'mkdir {OUT}/x'"],
                   IN_ROOT, False, "write_outside_containment_root")
        self.check(["bash -c 'mkdir -p /mnt/raid0/llm/x && cd /mnt/raid0/llm/x && touch y'",
                    f"cat <<'EOF' > /mnt/raid0/llm/notes.md\nrm -rf {OUT}\nEOF",
                    f"python3 - <<'EOF'\nprint('{OUT}')\nEOF"], IN_ROOT, True)

    def test_runner_and_pushd_directories(self):
        self.check([f"env -C {OUT} mkdir x", f"env --chdir={OUT} mkdir x",
                    f"sudo -D {OUT} mkdir x", f"pushd {OUT} && mkdir x"], IN_ROOT, False,
                   "write_outside_containment_root")
        self.check(["popd; mkdir x", f"CDPATH={OUT} cd work && mkdir x", "sudo -i mkdir x"],
                   IN_ROOT, False, "unresolvable_target")
        self.check([f"pushd {OUT}; popd; mkdir x", f"env -C {OUT} ls > out.log"], IN_ROOT, True)

    def test_expansions_and_links(self):
        """`{/in,/out}` was one path; a glob or a same-command link was read
        as text; a hard link aliases an out-of-root file; mv deletes."""
        self.check([f"mkdir -p {{/mnt/raid0/llm/a,{OUT}/b}}", "rm -rf /tmp/{a,../mnt/bigdisk}",
                    f"ln {OUT}/f /mnt/raid0/llm/l", f"cp -l {OUT}/f /mnt/raid0/llm/l",
                    f"mv {OUT}/data /mnt/raid0/llm/"], IN_ROOT, False,
                   "write_outside_containment_root")
        self.check(["mkdir -p /mnt/raid0/llm/{a,b}/{c,d}", "cp a /mnt/raid0/llm/x{,.bak}",
                    "ln -s /usr/bin/python3 /mnt/raid0/llm/venv/bin/python"], IN_ROOT, True)
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            os.symlink(OUT, os.path.join(td, "lnk"))
            self.check([f"rm -rf {td}/ln*", f"cd {td} && rm -rf l?k"], IN_ROOT, False,
                       "write_outside_containment_root")
            self.check([f"ln -s {OUT} {td}/new && rm -rf {td}/new/x"], IN_ROOT, False,
                       "unresolvable_target")

    def test_more_write_tools(self):
        self.check([f"sed -i 's/a/b/' {OUT}/f", f"sed -i.bak -e s/a/b/ {OUT}/f",
                    f"unlink {OUT}/f", f"truncate -s 0 {OUT}/f", f"shred -u {OUT}/f",
                    f"chgrp g {OUT}/f", f"find {OUT} -delete", f"find -L {OUT} -name x -delete",
                    f"find . -exec cp {{}} {OUT}/ ';'", f"find {OUT} -exec rm {{}} +",
                    f"find . -fprint {OUT}/list",
                    f"rsync -a --remove-source-files {OUT}/x /mnt/raid0/llm/",
                    f"tar --remove-files -czf /mnt/raid0/llm/a.tgz {OUT}/x",
                    "tar -xf a.tar -C /mnt/raid0/llm -C ../bigdisk"], IN_ROOT, False,
                   "write_outside_containment_root")
        self.check(["tar xzf x.tgz", "find . -name '*.pyc' -delete"], OUT_ROOT, False)
        self.check([f"sed -n 1,5p {OUT}/f", "sed -i s/a/b/ /mnt/raid0/llm/f",
                    "find /etc -name x -exec grep -l y {} +", "find . -name '*.pyc' -delete",
                    f"tar -czf /mnt/raid0/llm/a.tgz {OUT}/x", "tar -tzf x.tgz",
                    'git clone "https://x/y.git" /mnt/raid0/llm/y',
                    'touch -d "2 days ago" /mnt/raid0/llm/x', "[[ $a > $b ]] && echo ok",
                    f'git commit -m "mkdir {OUT}; sudo mount /dev/sdb1 /mnt"',
                    'echo "sudo mount" | tee /mnt/raid0/llm/x.log', "ls 1>&2-"], IN_ROOT, True)


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

    def test_payload_cwd_drives_relative_resolution(self):
        """The Bash tool's cwd persists across calls; the wrapper resolved
        `mkdir x` against its own (project) dir, not the payload's (2026-10-07)."""
        for cwd, rc in (("/mnt/bigdisk/work", 2), ("/mnt/raid0/llm/epyc-root", 0)):
            res = self.run_wrapper(json.dumps(
                {"tool_name": "Bash", "tool_input": {"command": "mkdir x"}, "cwd": cwd}))
            self.assertEqual(res.returncode, rc, res.stderr)

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

    def test_degraded_mode_still_refuses_privileged_verbs(self):
        """Without the scanner the wrapper falls back to literal greps. The
        2026-10-23 pipefail rewrite broke their line continuations, so the
        fallback allowed the incident's own `sudo mount` (it ran the patterns as
        commands). A copy of the wrapper with no scanner beside it exercises it."""
        with tempfile.TemporaryDirectory() as tmp:
            lone = Path(tmp) / WRAPPER.name
            lone.write_text(WRAPPER.read_text())
            for cmd, rc in ((INCIDENT_CMD, 2), ("sudo apt-get install restic", 2),
                            ("dpkg -i x.deb", 2), ("ls -la /tmp", 0)):
                res = subprocess.run(
                    ["/bin/bash", str(lone)], capture_output=True, text=True, timeout=60,
                    input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}))
                self.assertEqual(res.returncode, rc, (cmd, res.stderr))
                self.assertNotIn("command not found", res.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
