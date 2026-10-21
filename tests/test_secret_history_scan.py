"""SEC-SECRETS-1: name-only history scan. Temp git repos with FAKE tokens; the planted values must never be echoed."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("secret_history_scan", ROOT / "scripts/audit/secret_history_scan.py")
shs = importlib.util.module_from_spec(_SPEC)
sys.modules["secret_history_scan"] = shs
_SPEC.loader.exec_module(shs)

HF = "hf_" + "Zq4Xw8Rt2Lm6Np0Vb3Ka7Hs1Jd5Gf9Cy2E"       # fake, 34 alnum after the prefix
WB = "0a1b2c3d4e5f60718293a4b5c6d7e8f901234567"          # fake 40-hex
FAKES = (HF, WB)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@example.invalid", "-c", "user.name=t",
                           *args], check=True, text=True, capture_output=True).stdout.strip()


def commit(repo: Path, rel: str, content: str, msg: str) -> str:
    f = repo / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content)
    git(repo, "add", rel)
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture()
def repo(tmp_path) -> dict:
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    out = {"path": r}
    out["clean"] = commit(r, "README.md", "hello\nWANDB_API_KEY=$WANDB_API_KEY\n", "clean")
    out["leak_hf"] = commit(r, "scripts/run.sh", f"#!/bin/sh\nexport HF_TOKEN={HF}\n", "oops hf")
    out["leak_wb"] = commit(r, "train/cfg.env", f"WANDB_API_KEY={WB}\n", "oops wandb")
    commit(r, "scripts/run.sh", "#!/bin/sh\n", "remove hf from tree")          # history-only after this
    git(r, "rm", "-q", "train/cfg.env")
    git(r, "commit", "-q", "-m", "remove wandb from tree")
    out["fixture"] = commit(r, "research/fixtures/pii_x.jsonl", f'{{"text": "HF_TOKEN={HF}"}}\n', "fixture")
    git(r, "checkout", "-q", "-b", "side")
    out["branch_leak"] = commit(r, "side.txt", f"wandb login {WB}\n", "leak on a side branch")
    git(r, "checkout", "-q", "main")
    return out


def test_finds_history_only_leaks_on_all_refs_with_commit_and_path(repo, tmp_path):
    pats = shs.load_patterns()
    res = shs.scan_repo(str(repo["path"]), pats, prefilter=True)
    got = {(f["commit"], f["path"]): f for f in res["findings"]}
    assert (repo["leak_hf"], "scripts/run.sh") in got                  # deleted from the tree, still in history
    assert (repo["leak_wb"], "train/cfg.env") in got
    assert (repo["branch_leak"], "side.txt") in got                    # non-checked-out branch
    assert not any(c == repo["clean"] for c, _ in got)                 # $WANDB_API_KEY reference is not a value
    fx = got[(repo["fixture"], "research/fixtures/pii_x.jsonl")]
    assert fx["allowlisted"] is True and got[(repo["leak_hf"], "scripts/run.sh")]["allowlisted"] is False


def test_cli_reports_names_only_and_exit_codes(repo, tmp_path, capsys):
    out = tmp_path / "report.json"
    code = shs.main(["--repo", str(repo["path"]), "--out", str(out)])
    captured = capsys.readouterr()
    assert code == 3
    blob = captured.out + captured.err + out.read_text()
    for fake in FAKES:
        assert fake not in blob, "the report must never carry a credential value"
        assert fake[:10] not in blob
    rep = json.loads(out.read_text())
    assert rep["schema"] == shs.SCHEMA and rep["real_findings"] == 3 and rep["errors"] == []
    assert all(set(f) == {"commit", "path", "pattern", "hits", "allowlisted"} for f in rep["repos"][0]["findings"])
    assert f"FINDING {repo['leak_hf']} scripts/run.sh" in captured.out


def test_clean_repo_exits_zero_and_bad_repo_exits_two(tmp_path, capsys):
    r = tmp_path / "c"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    commit(r, "a.txt", "nothing here\n", "c1")
    assert shs.main(["--repo", str(r)]) == 0
    assert shs.main(["--repo", str(tmp_path / "not-a-repo")]) == 2          # an unscannable repo is never "clean"
    assert "ERROR" in capsys.readouterr().err


def test_patterns_come_from_the_hook_and_cover_both_families():
    labels = {lab for _, lab in shs.load_patterns()}
    assert labels == set(shs.HFW_LABELS)
    assert len(shs.load_patterns(all_families=True)) > len(shs.load_patterns())


def test_hook_missing_the_patterns_refuses(tmp_path):
    hook = tmp_path / "h.sh"
    hook.write_text("SECRET_PATTERNS=(\n  $'AKIA[0-9A-Z]{16}\\tsecret\\tAWS access key ID'\n)\n")
    with pytest.raises(ValueError, match="lacks the SEC-SECRETS-1 patterns"):
        shs.load_patterns(hook)
    assert shs.main(["--repo", str(tmp_path), "--hook", str(hook)]) == 2


def test_all_families_mode_catches_other_tokens(tmp_path):
    r = tmp_path / "a"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    aws = "AKIA" + "2X4B7QZKLMNP9WCD"
    c = commit(r, "k.txt", f"aws_access_key_id = {aws}\n", "aws")
    res = shs.scan_repo(str(r), shs.load_patterns(all_families=True), prefilter=False)
    assert [(f["commit"], f["path"]) for f in res["findings"]] == [(c, "k.txt")]
    assert shs.scan_repo(str(r), shs.load_patterns(), prefilter=True)["findings"] == []
