"""Tests for the bash-compressor MCP server skeleton."""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass

from src import tool_output_compressor_mcp as mod


@dataclass(frozen=True)
class _CompressionResult:
    text: str
    strategy: str
    original_chars: int
    compressed_chars: int


def _call_tool(command: str, **kwargs):
    args = {"command": command, **kwargs}
    return asyncio.run(mod.mcp.call_tool("run_bash_compressed", args))


def _result_text(result) -> str:
    return result.content[0].text


def test_run_bash_compressed_runs_allowlisted_command(monkeypatch, tmp_path) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="raw output", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("TOOL_COMPRESSION_MONITOR_PATH", str(tmp_path / "telemetry.jsonl"))
    monkeypatch.setattr(
        mod,
        "_compress_output",
        lambda output, command: _CompressionResult(
            text=f"compressed {command}: {output}",
            strategy="test_strategy",
            original_chars=len(output),
            compressed_chars=len(f"compressed {command}: {output}"),
        ),
    )

    result = _call_tool("git status", timeout_s=999)

    assert _result_text(result) == "compressed git status: raw output"
    assert calls == [
        (
            ["git", "status"],
            {
                "capture_output": True,
                "text": True,
                "timeout": mod.MAX_TIMEOUT_S,
                "cwd": mod.PROJECT_ROOT,
            },
        )
    ]
    assert result.meta["tool_compression"]["compressor_strategy"] == "test_strategy"


def test_run_bash_compressed_rejects_blocked_command(monkeypatch) -> None:
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subprocess called")),
    )

    result = mod.run_bash_compressed("rm -rf .")

    assert "blocked for security" in result


def test_run_bash_compressed_rejects_unknown_git_subcommand(monkeypatch) -> None:
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subprocess called")),
    )

    result = mod.run_bash_compressed("git reset --hard")

    assert "git reset not allowed" in result


def test_run_bash_compressed_rejects_working_dir_outside_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subprocess called")),
    )

    result = mod.run_bash_compressed("pwd", working_dir=str(tmp_path))

    assert "working_dir must stay under" in result


def test_run_bash_compressed_includes_stderr_and_exit_code(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 2, stdout="out", stderr="err")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setattr(mod, "_compress_output", lambda output, command: output)

    result = mod.run_bash_compressed("python -m pytest")

    assert result == "[exit code 2]\nout\n[STDERR]\nerr"


def test_run_bash_compressed_emits_telemetry(monkeypatch, tmp_path) -> None:
    telemetry = tmp_path / "tool_compression_monitor.jsonl"

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="raw output", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("TOOL_COMPRESSION_MONITOR_PATH", str(telemetry))
    monkeypatch.setattr(
        mod,
        "_compress_output",
        lambda output, command: _CompressionResult(
            text="short",
            strategy="unit",
            original_chars=len(output),
            compressed_chars=5,
        ),
    )

    result = _call_tool("git status")

    assert _result_text(result) == "short"
    [record] = [json.loads(line) for line in telemetry.read_text().splitlines()]
    assert record["tool"] == "run_bash_compressed"
    assert record["command"] == "git status"
    assert record["pre_bytes"] == len("raw output")
    assert record["post_bytes"] == len("short")
    assert record["compressor_strategy"] == "unit"
    assert record["top_up_candidate"] is False
    assert record["followup_distance"] is None
    assert record["followup_reason"] is None
    assert record["next_turn_followup_command"] is None
    assert record["followup_source_command"] is None


def test_followup_detector_marks_repeat_within_three_turns() -> None:
    history = [
        {"tool": "run_bash_compressed", "command": "ls"},
        {"tool": "run_bash_compressed", "command": "git status"},
        {"tool": "run_bash_compressed", "command": "python -m pytest"},
        {"tool": "run_bash_compressed", "command": "git status"},
    ]

    result = mod._infer_top_up_followup("git status", history)

    assert result["top_up_candidate"] is True
    assert result["followup_distance"] == 1
    assert result["followup_reason"] == mod.TOP_UP_REASON_REPEAT
    assert result["next_turn_followup_command"] == "git status"
    assert result["followup_source_command"] == "git status"


def test_followup_detector_marks_file_view_after_listing() -> None:
    history = [{"tool": "run_bash_compressed", "command": "ls /tmp"}]

    result = mod._infer_top_up_followup("cat /tmp/file.txt", history)

    assert result["top_up_candidate"] is True
    assert result["followup_distance"] == 1
    assert result["followup_reason"] == mod.TOP_UP_REASON_LIST_VIEW
    assert result["next_turn_followup_command"] == "cat /tmp/file.txt"
    assert result["followup_source_command"] == "ls /tmp"


def test_followup_detector_marks_head_with_flags_after_listing() -> None:
    history = [{"tool": "run_bash_compressed", "command": "ls src"}]

    result = mod._infer_top_up_followup("head -20 src/tool_output_compressor_mcp.py", history)

    assert result["top_up_candidate"] is True
    assert result["followup_distance"] == 1
    assert result["followup_reason"] == mod.TOP_UP_REASON_LIST_VIEW
    assert result["next_turn_followup_command"] == "head -20 src/tool_output_compressor_mcp.py"
    assert result["followup_source_command"] == "ls src"


def test_followup_detector_ignores_non_followup_patterns() -> None:
    history = [
        {"tool": "run_bash_compressed", "command": "ls /tmp"},
        {"tool": "run_bash_compressed", "command": "git status"},
        {"tool": "run_bash_compressed", "command": "echo hi"},
    ]

    result = mod._infer_top_up_followup("python -m pytest", history)

    assert result["top_up_candidate"] is False
    assert result["followup_distance"] is None
    assert result["followup_reason"] is None
    assert result["next_turn_followup_command"] is None
    assert result["followup_source_command"] is None


def test_run_bash_compressed_marks_session_followup(monkeypatch, tmp_path) -> None:
    telemetry = tmp_path / "tool_compression_monitor.jsonl"

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="raw output", stderr="")

    telemetry.write_text(
        '{"timestamp": "2026-06-14T00:00:00Z", "tool": '
        '"run_bash_compressed", "command": "git status", '
        '"session_id": "session-1"}\n'
    )
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("TOOL_COMPRESSION_MONITOR_PATH", str(telemetry))
    monkeypatch.setenv("TOOL_COMPRESSION_SESSION_ID", "session-1")
    monkeypatch.setenv("TOOL_COMPRESSION_SESSION_PATH", str(telemetry))
    monkeypatch.setattr(
        mod,
        "_compress_output",
        lambda output, command: _CompressionResult(
            text="short",
            strategy="unit",
            original_chars=len(output),
            compressed_chars=5,
        ),
    )

    _call_tool("git status")

    _, record = [json.loads(line) for line in telemetry.read_text().splitlines()]
    assert record["top_up_candidate"] is True
    assert record["followup_distance"] == 1
    assert record["followup_reason"] == mod.TOP_UP_REASON_REPEAT
    assert record["session_id"] == "session-1"


def test_run_bash_compressed_filters_history_to_current_session(monkeypatch, tmp_path) -> None:
    telemetry = tmp_path / "tool_compression_monitor.jsonl"

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="raw output", stderr="")

    telemetry.write_text(
        "\n".join(
            [
                '{"timestamp": "2026-06-14T00:00:00Z", "tool": '
                '"run_bash_compressed", "command": "git status"}',
                '{"timestamp": "2026-06-14T00:00:01Z", "tool": '
                '"run_bash_compressed", "command": "git status", '
                '"session_id": "session-2"}',
                "",
            ]
        )
    )
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("TOOL_COMPRESSION_MONITOR_PATH", str(telemetry))
    monkeypatch.setenv("TOOL_COMPRESSION_SESSION_ID", "session-1")
    monkeypatch.setenv("TOOL_COMPRESSION_SESSION_PATH", str(telemetry))
    monkeypatch.setattr(
        mod,
        "_compress_output",
        lambda output, command: _CompressionResult(
            text="short",
            strategy="unit",
            original_chars=len(output),
            compressed_chars=5,
        ),
    )

    _call_tool("git status")

    *_, record = [json.loads(line) for line in telemetry.read_text().splitlines()]
    assert record["top_up_candidate"] is False
    assert record["followup_source_command"] is None


_FAKE_PAT = "github_pat_11ABCDEFG0AbCdEfGhIjKl_xyzABCDEF"


def test_run_bash_compressed_redacts_credentials_in_compressed_output(monkeypatch, tmp_path) -> None:
    # TOC-RD-1: tokens in command output never reach the compressor or the returned text.
    seen_by_compressor = []

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=f"GH token: {_FAKE_PAT}\nok", stderr="")

    def fake_compress(output, command):
        seen_by_compressor.append(output)
        text = f"compressed: {output}"
        return _CompressionResult(text, "unit", len(output), len(text))

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("TOOL_COMPRESSION_MONITOR_PATH", str(tmp_path / "telemetry.jsonl"))
    monkeypatch.setattr(mod, "_compress_output", fake_compress)

    result = _call_tool("git log")

    text = _result_text(result)
    assert _FAKE_PAT not in text
    assert "[REDACTED:github_fine_grained_pat]" in text
    assert seen_by_compressor and all(_FAKE_PAT not in s for s in seen_by_compressor)
    assert result.structured_content is None or _FAKE_PAT not in json.dumps(result.structured_content)


def test_compressor_middleware_redacts_final_text(monkeypatch, tmp_path) -> None:
    # Even if compression (or an unredacted upstream result) yields a credential, the
    # returned text is redacted; truncated PEM blocks are covered too.
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="plain output", stderr="")

    def fake_compress(output, command):
        text = f"{output}\n-----BEGIN ED25519 PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA\n{_FAKE_PAT}"
        return _CompressionResult(text, "unit", len(output), len(text))

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("TOOL_COMPRESSION_MONITOR_PATH", str(tmp_path / "telemetry.jsonl"))
    monkeypatch.setattr(mod, "_compress_output", fake_compress)

    text = _result_text(_call_tool("git status"))

    assert text == "plain output\n[REDACTED:ssh_private_key]"


def test_run_bash_compressed_direct_call_redacts_without_middleware(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=f"auth failed for {_FAKE_PAT}")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    result = mod.run_bash_compressed("git status")

    assert _FAKE_PAT not in result
    assert result == "[exit code 1]\n\n[STDERR]\nauth failed for [REDACTED:github_fine_grained_pat]"
