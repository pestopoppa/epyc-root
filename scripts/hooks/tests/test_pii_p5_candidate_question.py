"""Exact public-source line exception, exercised against staged Git blobs."""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "scripts/hooks/pii_precommit.sh"
CANDIDATE = "docs/reports/p5-question-candidate-20261104/questions.json"
LINE_SHA256 = "33a0fd6e91f4f4fad0ffe945e889f1dad1a55fc95636c29be8ab75394151904b"


@pytest.fixture
def original_line():
    # Never copy the source prompt into fixtures or diagnostics.
    lines = (ROOT / CANDIDATE).read_bytes().splitlines()
    matches = [line for line in lines if hashlib.sha256(line).hexdigest() == LINE_SHA256]
    assert len(matches) == 1, "Expected exact original public-source line"
    return matches[0]


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    try:
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        yield repo
    finally:
        # Remove all staged source/secret test payloads, including on failure.
        shutil.rmtree(repo)


@pytest.mark.parametrize("case,label", [
    ("original", None),
    ("mixed-same-line", "account_number"),
    ("changed-digit", "account_number"),
    ("wrong-path", "account_number"),
    ("extra-account-line", "account_number"),
    ("secret-same-line", "secret"),
    ("secret-other-line", "secret"),
])
def test_exact_candidate_exception(git_repo, original_line, case, label):
    line = original_line
    path = CANDIDATE
    account = b"account_number: " + b"9" * 12
    # Synthetic credential shape; keep it out of test assertion diagnostics.
    secret = b"ghp_" + b"Z" * 36
    if case == "mixed-same-line":
        line += b" " + account
    elif case == "changed-digit":
        hit = re.search(rb"\b[0-9]{12,19}\b", line)
        assert hit is not None, "Expected polynomial integer in public source"
        pos = hit.start()
        digit = b"8" if line[pos:pos + 1] != b"8" else b"7"
        line = line[:pos] + digit + line[pos + 1:]
    elif case == "wrong-path":
        path = "docs/reports/other/questions.json"
    elif case == "extra-account-line":
        line += b"\n" + account
    elif case == "secret-same-line":
        line += b" " + secret
    elif case == "secret-other-line":
        line += b"\n" + secret
    target = git_repo / path
    target.parent.mkdir(parents=True)
    target.write_bytes(line + b"\n")
    subprocess.run(["git", "add", "--", path], cwd=git_repo, check=True, capture_output=True)
    # Make the working copy disagree: only the staged blob may determine outcome.
    target.write_text("clean working copy\n")
    result = subprocess.run(["bash", str(HOOK)], cwd=git_repo, capture_output=True,
                            timeout=30)
    assert result.returncode == (1 if label else 0), f"Unexpected hook exit for {case}"
    if label:
        assert ("[" + label + "]").encode() in result.stderr, f"Missing block label for {case}"
    else:
        assert b"BLOCKED:" not in result.stderr, "Original line unexpectedly blocked"
