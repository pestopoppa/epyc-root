"""Paired lint and staged-index controls for the warn-only SIGPIPE scanner."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

CHECKER = Path(__file__).parents[1] / "check_sigpipe_grep_q.py"
SPEC = importlib.util.spec_from_file_location("check_sigpipe_grep_q", CHECKER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


class SigpipeGrepQTests(unittest.TestCase):
    def test_warns_on_strings_pipeline_with_pipefail(self):
        text = "set -euo pipefail\nstrings binary | grep -q token\n"
        findings = MODULE.lint_text(text, "launch.sh")
        self.assertEqual(1, len(findings))
        self.assertIn("SIGPIPE (141)", findings[0])
        self.assertIn("grep -c", findings[0])
        self.assertIn("grep without -q", findings[0])

    def test_warns_on_combined_grep_options_and_continuation(self):
        text = "set -o pipefail\nnm binary | \\\n  /usr/bin/grep -Fq -- target\n"
        self.assertEqual(1, len(MODULE.lint_text(text, "gate.bash")))

    def test_does_not_treat_grep_pattern_or_file_argument_as_option(self):
        text = (
            "set -o pipefail\n"
            "producer | grep -e '-q'\n"
            "producer | grep --regexp '-q'\n"
            "producer | grep --regexp=-q\n"
            "producer | grep -f -q\n"
            "producer | grep --file '-q'\n"
            "producer | grep --file=-q\n"
        )
        self.assertEqual([], MODULE.lint_text(text, "options.sh"))

    def test_no_warning_without_pipefail(self):
        self.assertEqual([], MODULE.lint_text("strings binary | grep -q token\n", "plain.sh"))

    def test_no_warning_for_safe_count_redirection_or_file_input(self):
        text = (
            "set -o pipefail\n"
            "count=$(producer | grep -c token)\n"
            "producer | grep token > /dev/null\n"
            "grep -q token input.txt\n"
        )
        self.assertEqual([], MODULE.lint_text(text, "safe.sh"))

    def test_ignores_comment_and_quoted_pipe(self):
        text = "set -o pipefail\nprintf '%s' 'a|b' # producer | grep -q x\n"
        self.assertEqual([], MODULE.lint_text(text, "quoted.sh"))

    def test_pipefail_reset_stops_later_warning(self):
        text = "set -o pipefail\nset +o pipefail\nproducer | grep -q token\n"
        self.assertEqual([], MODULE.lint_text(text, "reset.sh"))

    def test_pipefail_enabled_before_same_line_pipeline(self):
        text = "set -euo pipefail; strings binary | grep -q token\n"
        self.assertEqual(1, len(MODULE.lint_text(text, "same-line.sh")))

    def test_main_reads_staged_unsafe_blob_not_safe_worktree(self):
        with tempfile.TemporaryDirectory(prefix="sigpipe-staged-unsafe-") as tmp:
            repo = Path(tmp)
            git(repo, "init", "--quiet")
            path = repo / "probe.sh"
            path.write_text("set -o pipefail\n# SECRET_STAGED_ONLY\nproducer | grep -q needle\n")
            git(repo, "add", "probe.sh")
            path.write_text("set -o pipefail\n# SAFE_WORKTREE_ONLY\necho safe\n")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(0, MODULE.main([str(repo)]))
            self.assertIn("probe.sh:3", stderr.getvalue())
            self.assertIn("SIGPIPE (141)", stderr.getvalue())
            self.assertNotIn("SAFE_WORKTREE_ONLY", stderr.getvalue())
            self.assertNotIn("SECRET_STAGED_ONLY", stderr.getvalue())

    def test_main_ignores_unsafe_worktree_when_staged_blob_is_safe(self):
        with tempfile.TemporaryDirectory(prefix="sigpipe-staged-safe-") as tmp:
            repo = Path(tmp)
            git(repo, "init", "--quiet")
            path = repo / "probe.sh"
            path.write_text("set -o pipefail\nproducer | grep token > /dev/null\n")
            git(repo, "add", "probe.sh")
            path.write_text("set -o pipefail\nproducer | grep -q SECRET_WORKTREE_ONLY\n")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(0, MODULE.main([str(repo)]))
            self.assertEqual("", stderr.getvalue())

    def test_main_fails_open_on_git_scan_error_without_source_leak(self):
        with tempfile.TemporaryDirectory(prefix="sigpipe-not-git-") as tmp:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(0, MODULE.main([tmp]))
            self.assertIn("scan skipped (CalledProcessError)", stderr.getvalue())
            self.assertNotIn("SECRET", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
