"""Pure mocked tests for the proposed clean-only scanner; never invoke git clean."""
from __future__ import annotations

from pathlib import Path
import subprocess

from check_git_clean_untracked import classify, main
import check_git_clean_untracked as guard
from io import StringIO
import json
from unittest.mock import patch
import pytest


def _runner_for(status: bytes, *, config: bytes = b"true", fail_status: bool = False):
    calls = []

    def run(repo: Path, args: list[str]):
        calls.append((repo, args))
        assert "clean" not in args, "guard must never execute git clean"
        if args[0] == "config":
            return subprocess.CompletedProcess(args, 0 if config else 1, config, b"")
        assert args[0] == "status", args
        if fail_status:
            return subprocess.CompletedProcess(args, 128, b"", b"status failed")
        return subprocess.CompletedProcess(args, 0, status, b"")

    return run, calls


def test_clean_tree_with_force_allows():
    run, calls = _runner_for(b"")
    assert classify("git clean -ffdx", cwd="/tmp", run_git=run)[0] == "allow"
    assert len(calls) == 1 and calls[0][1][0] == "status"


def test_untracked_file_blocks():
    run, _ = _runner_for(b"?? orphan.txt\0")
    assert classify("git clean -f", cwd="/tmp", run_git=run)[0] == "block"


def test_ignored_file_blocks_under_x():
    run, calls = _runner_for(b"!! ignored.bin\0")
    assert classify("git clean -fx", cwd="/tmp", run_git=run)[0] == "block"
    assert "--ignored=matching" in calls[0][1]


def test_ignored_only_x_uppercase_blocks_only_ignored():
    run, _ = _runner_for(b"?? orphan.txt\0!! ignored.bin\0")
    assert classify("git clean -fX", cwd="/tmp", run_git=run)[0] == "block"


def test_dry_run_never_queries_status():
    def unexpected(*_args):
        raise AssertionError("dry-run must not query or execute git")

    assert classify("git clean -ffdx -n", cwd="/tmp", run_git=unexpected)[0] == "allow"


def test_dash_c_repo_is_the_status_target():
    repo = Path("/tmp/target").resolve()
    run, calls = _runner_for(b"?? orphan.txt\0")
    assert classify("git -C /tmp/target clean -fd", cwd="/tmp", run_git=run)[0] == "block"
    assert calls[0][0] == repo


def test_quoted_documentation_is_not_invocation():
    def unexpected(*_args):
        raise AssertionError("quoted documentation is not a command")

    assert classify("echo 'git clean -ffdx'", cwd="/tmp", run_git=unexpected)[0] == "allow"
    assert classify("git status --short clean", cwd="/tmp", run_git=unexpected)[0] == "allow"


def test_heredoc_and_comment_documentation_are_not_invocations():
    def unexpected(*_args):
        raise AssertionError("documentation must not query Git")

    assert classify("cat <<'EOF'\ngit clean -ffdx\nEOF", cwd="/tmp", run_git=unexpected)[0] == "allow"
    assert classify("printf ok # git clean -ffdx", cwd="/tmp", run_git=unexpected)[0] == "allow"


def test_wrapper_is_ambiguous_and_refused():
    def unexpected(*_args):
        raise AssertionError("ambiguous wrapper must refuse before probing")

    verdict, reason = classify("sudo git clean -ffdx", cwd="/tmp", run_git=unexpected)
    assert verdict == "block" and "wrapped" in reason


def test_bash_c_payload_is_scanned_recursively():
    run, _ = _runner_for(b"?? orphan.txt\0")
    verdict, reason = classify("bash -c 'git clean -ffdx'", cwd="/tmp", run_git=run)
    assert verdict == "block" and "could remove" in reason


def test_command_substitution_is_scanned_recursively():
    run, _ = _runner_for(b"?? orphan.txt\0")
    verdict, reason = classify('echo "$(git clean -ffdx)"', cwd="/tmp", run_git=run)
    assert verdict == "block" and "could remove" in reason


def test_backtick_substitution_is_scanned_recursively():
    run, _ = _runner_for(b"?? orphan.txt\0")
    verdict, reason = classify('echo `git clean -ffdx`', cwd="/tmp", run_git=run)
    assert verdict == "block" and "could remove" in reason


def test_eval_payload_is_scanned_recursively():
    run, _ = _runner_for(b"?? orphan.txt\0")
    verdict, reason = classify("eval 'git clean -ffdx'", cwd="/tmp", run_git=run)
    assert verdict == "block" and "could remove" in reason


def test_dynamic_command_name_fails_closed():
    def unexpected(*_args):
        raise AssertionError("dynamic command name must refuse without probing")

    verdict, reason = classify("$GIT clean -ffdx", cwd="/tmp", run_git=unexpected)
    assert verdict == "block" and "wrapped" in reason


def test_compound_cd_then_clean_refuses_before_status():
    def unexpected(*_args):
        raise AssertionError("ambiguous compound command must refuse without probing")

    verdict, reason = classify("cd /tmp; git clean -ffdx", cwd="/tmp", run_git=unexpected)
    assert verdict == "block" and "compound" in reason


def test_status_failure_fails_closed():
    run, _ = _runner_for(b"", fail_status=True)
    assert classify("git clean -f", cwd="/tmp", run_git=run)[0] == "block"


def test_force_required_true_allows_unforced_clean_without_status_query():
    run, calls = _runner_for(b"", config=b"true")
    assert classify("git clean", cwd="/tmp", run_git=run)[0] == "allow"
    assert [args[0] for _, args in calls] == ["config"]


def test_require_force_false_makes_unforced_clean_subject_to_guard():
    run, calls = _runner_for(b"?? orphan.txt\0", config=b"false")
    assert classify("git clean", cwd="/tmp", run_git=run)[0] == "block"
    assert [args[0] for _, args in calls] == ["config", "status"]


def test_clean_directory_without_d_is_not_removed():
    run, _ = _runner_for(b"?? nested/\0")
    assert classify("git clean -f", cwd="/tmp", run_git=run)[0] == "allow"


def test_newline_is_shell_command_boundary():
    verdict, reason = classify("cd /tmp\ngit clean -ffdx", cwd="/tmp",
                               run_git=lambda *_: (_ for _ in ()).throw(AssertionError()))
    assert verdict == "block" and "compound" in reason


def test_main_uses_validated_payload_cwd_instead_of_process_cwd(tmp_path, capsys):
    payload_cwd = tmp_path / "payload-repo"
    payload_cwd.mkdir()
    seen = []

    def fake_subprocess_run(argv, **kwargs):
        seen.append(argv)
        assert "clean" not in argv
        return subprocess.CompletedProcess(argv, 0, b"?? orphan.txt\0", b"")

    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "cwd": str(payload_cwd),
               "tool_input": {"command": "git clean -f"}}
    with patch.object(guard.sys, "stdin", StringIO(json.dumps(payload))), \
         patch.object(guard.subprocess, "run", fake_subprocess_run):
        assert main() == 2
    assert seen and all(argv[2] == str(payload_cwd.resolve()) for argv in seen)
    assert "BLOCKED:" in capsys.readouterr().err


def test_main_refuses_invalid_relative_payload_cwd_before_git_probe(capsys):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "cwd": "relative/repo",
               "tool_input": {"command": "git clean -f"}}
    with patch.object(guard.sys, "stdin", StringIO(json.dumps(payload))), \
         patch.object(guard.subprocess, "run", side_effect=AssertionError("must not probe")):
        assert main() == 2
    assert "BLOCKED:" in capsys.readouterr().err


@pytest.mark.parametrize("command", [
    "if true; then git clean -fd; fi",
    "for p in .; do git clean -fd; done",
    "! git clean -fd",
])
def test_control_flow_or_negation_clean_refuses_before_status(command):
    def unexpected(*_args):
        raise AssertionError("control-flow framing must refuse without probing")

    verdict, reason = classify(command, cwd="/tmp", run_git=unexpected)
    assert verdict == "block"
    assert "wrapped" in reason or "compound" in reason


def test_newline_control_flow_clean_refuses_before_status():
    def unexpected(*_args):
        raise AssertionError("newline control flow must refuse without probing")

    verdict, reason = classify("if true; then\ngit clean -fd\nfi", cwd="/tmp",
                               run_git=unexpected)
    assert verdict == "block"
    assert "compound" in reason or "wrapped" in reason
