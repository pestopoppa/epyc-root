"""AKPL-P5 clause 1: handback_verify runs automatically on each AK subagent hand-back (offline, tmp repo)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "coordination", "akloop"))
import handback_auto as ha  # noqa: E402

HOOK = os.path.join(ROOT, "scripts", "hooks", "posttool_handback_sweep.py")
AK_PROMPT = "do the work. Report contract: end with a `CLAIMS:` block, one claim per line"


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / "o.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    r = tmp_path / "r"
    subprocess.run(["git", "clone", "-q", str(origin), str(r)], check=True, capture_output=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    (r / "f").write_text("1")
    for a in (["add", "f"], ["commit", "-qm", "c"], ["push", "-q", "origin", "HEAD:main"], ["fetch", "-q", "origin"]):
        subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True, env=env)
    sha = subprocess.check_output(["git", "-C", str(r), "rev-parse", "HEAD"], text=True).strip()
    return str(r), sha


def payload(prompt, response, cwd):
    return {"hook_event_name": "PostToolUse", "tool_name": "Agent", "cwd": cwd, "session_id": "s",
            "tool_input": {"prompt": prompt}, "tool_response": response}


def test_verified_stamp_and_ledger(repo, tmp_path):
    r, sha = repo
    led = str(tmp_path / "led" / "s.jsonl")
    line = ha.stamp_payload(payload(AK_PROMPT, [{"type": "text", "text": f"done\nCLAIMS:\npushed {sha} to main"}], r), ledger=led)
    assert line.startswith("HAND-BACK STAMP: VERIFIED")
    assert json.loads(open(led).read())["stamp"] == "VERIFIED"


def test_unverified_when_claim_fails_or_block_missing(repo, tmp_path):
    r, sha = repo
    led = str(tmp_path / "s.jsonl")
    bad = ha.stamp_payload(payload(AK_PROMPT, "CLAIMS:\npushed deadbeefdead to main", r), ledger=led)
    assert "UNVERIFIED" in bad and "pushed" in bad
    none = ha.stamp_payload(payload(AK_PROMPT, "I finished everything, trust me", r), ledger=led)
    assert "UNVERIFIED" in none and "no checkable claims" in none


def test_non_ak_agents_and_other_events_untouched(repo, tmp_path):
    r, _ = repo
    assert ha.stamp_payload(payload("find files", "found 3 files", r), ledger=str(tmp_path / "l")) is None
    p = payload(AK_PROMPT, "x", r)
    p["hook_event_name"] = "SubagentStop"
    assert ha.stamp_payload(p, ledger=str(tmp_path / "l")) is None
    assert ha.stamp_payload({"garbage": 1}) is None
    assert ha.stamp_payload(None) is None  # never raises


def test_report_with_claims_line_is_ak_even_without_contract_prompt(repo, tmp_path):
    r, sha = repo
    assert ha.stamp_payload(payload("x", f"CLAIMS:\npushed {sha}", r), ledger=str(tmp_path / "l"))


def test_context_never_echoes_subagent_text(repo, tmp_path):
    r, _ = repo
    line = ha.stamp_payload(payload(AK_PROMPT, "CLAIMS:\npublished ROW-INJECTED-IGNORE-RULES", r),
                            ledger=str(tmp_path / "l"))
    assert "INJECTED" not in line


def test_hook_end_to_end_emits_additional_context(repo, tmp_path):
    r, sha = repo
    p = payload(AK_PROMPT, f"CLAIMS:\npushed {sha} to main", r)
    out = subprocess.run([sys.executable, HOOK], input=json.dumps(p), capture_output=True, text=True,
                         env={**os.environ, "HANDBACK_STAMP_LEDGER": str(tmp_path / "led.jsonl")}, timeout=30)
    assert out.returncode == 0
    ctx = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "HAND-BACK STAMP: VERIFIED" in ctx and (tmp_path / "led.jsonl").exists()
    quiet = subprocess.run([sys.executable, HOOK], input=json.dumps(payload("find", "ok", r)),
                           capture_output=True, text=True, timeout=30,
                           env={**os.environ, "HANDBACK_STAMP_LEDGER": str(tmp_path / "led2.jsonl")})
    assert quiet.returncode == 0 and quiet.stdout == ""
