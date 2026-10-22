"""F3-LB1: the staged PII guard blocks transcript-JSON shapes and per-session projections.

Runs the REAL scripts/hooks/pii_precommit.sh against a throwaway git repo. Every transcript
line is synthesized at runtime with json.dumps, so this file itself never matches.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "scripts/hooks/pii_precommit.sh"


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "README").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "--no-verify", "-m", "init"], check=True)
    return repo


def _run_hook(repo: Path, name: str, text: str) -> subprocess.CompletedProcess:
    (repo / name).write_text(text)
    subprocess.run(["git", "-C", str(repo), "add", name], check=True)
    return subprocess.run(["bash", str(HOOK)], cwd=repo, capture_output=True, text=True, timeout=120)


CLAUDE = {"parentUuid": None, "isSidechain": False, "sessionId": "s-1", "type": "user",
          "message": {"role": "user", "content": "hi"}}
CODEX = {"timestamp": "2026-10-20T10:00:00Z", "ordinal": 3, "type": "response_item",
         "payload": {"type": "message", "role": "user", "content": []}}
OC_TOOL = {"type": "tool", "tool": "bash", "callID": "c1", "state": {"status": "completed"}}
OC_MSG = {"parentID": "msg_abc123", "role": "assistant", "tokens": {}}
OC_V1 = {"id": "prt_1", "messageID": "msg_abc", "sessionID": "ses_abc", "type": "text"}
PROJ = {"schema": "dev-harness-" + "event.v1", "harness": "codex"}


@pytest.mark.parametrize("row,name", [
    (CLAUDE, "t.jsonl"), (CODEX, "r.jsonl"), (OC_TOOL, "p.jsonl"), (OC_MSG, "m.jsonl"), (OC_V1, "v1.json"),
    (PROJ, "events.jsonl"),
])
def test_transcript_shapes_block(tmp_path, row, name):
    repo = _repo(tmp_path)
    proc = _run_hook(repo, name, json.dumps(row, separators=(",", ":")) + "\n")
    assert proc.returncode == 1, proc.stderr
    assert "[transcript]" in proc.stderr


def test_oversized_transcript_still_blocks(tmp_path):
    repo = _repo(tmp_path)
    line = json.dumps(dict(CLAUDE, message={"role": "user", "content": "y" * 2000}), separators=(",", ":"))
    proc = _run_hook(repo, "big.jsonl", (line + "\n") * 700)     # > 1 MB: secret scan skipped, shape scan not
    assert proc.returncode == 1 and "[transcript]" in proc.stderr


@pytest.mark.parametrize("text", [
    # source code that names the keys, an aggregate, and a doc line are all fine
    'row = {"parentUuid": None, "sessionId": sid}\n',
    json.dumps({"schema": "dev-harness-aggregate.v1", "counts": {"interrupts": 3}}) + "\n",
    "The Claude transcript has parentUuid and sessionId keys.\n",
])
def test_non_transcripts_pass(tmp_path, text):
    repo = _repo(tmp_path)
    proc = _run_hook(repo, "ok.txt", text)
    assert proc.returncode == 0, proc.stderr
