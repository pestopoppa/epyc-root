"""Tests for scripts/utils/safe_download.py — fake download commands in temp dirs, no network."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("safe_download", ROOT / "scripts/utils/safe_download.py")
sd = importlib.util.module_from_spec(_SPEC)
sys.modules["safe_download"] = sd
_SPEC.loader.exec_module(sd)


def sh(script: str) -> list[str]:
    return ["/bin/bash", "-c", script]


def run(tmp_path, dest, script, *extra):
    ledger = tmp_path / "ledger.jsonl"
    rc = sd.main(["--dest", str(dest), "--ledger", str(ledger), "--allow-tmp", *extra, "--", *sh(script)])
    recs = [json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
    return rc, recs


def test_failed_download_partials_are_deleted_and_logged(tmp_path):
    dest = tmp_path / "m"
    rc, recs = run(tmp_path, dest, f"mkdir -p {dest}/.cache/huggingface/download && "
                                   f"echo x > {dest}/.cache/huggingface/download/blob.incomplete && "
                                   f"echo y > {dest}/w.gguf.part && exit 7")
    assert rc == 7
    assert sd.find_partials(str(dest)) == []
    assert {r["action"] for r in recs[0]["partials"]} == {"deleted"}
    assert recs[0]["rc"] == 7 and len(recs[0]["partials"]) == 2


def test_keep_partial_keeps_on_failure_only(tmp_path):
    dest = tmp_path / "m"
    rc, recs = run(tmp_path, dest, f"mkdir -p {dest}; echo y > {dest}/w.part; exit 1", "--keep-partial")
    assert rc == 1 and (dest / "w.part").exists()
    assert recs[0]["partials"][0]["action"] == "kept-for-resume"
    rc, _ = run(tmp_path, dest, f"echo z > {dest}/v.part; exit 0", "--keep-partial")
    assert rc == 0 and not (dest / "v.part").exists()     # success: stubs have no use


def test_success_without_partials_writes_no_ledger(tmp_path):
    dest = tmp_path / "m"
    rc, recs = run(tmp_path, dest, f"mkdir -p {dest}; echo ok > {dest}/model.gguf")
    assert rc == 0 and recs == [] and (dest / "model.gguf").exists()


def test_preexisting_partial_from_another_download_is_untouched(tmp_path):
    dest = tmp_path / "m"
    dest.mkdir()
    other = dest / "concurrent.incomplete"
    other.write_text("theirs")
    old = time.time() - 3600
    os.utime(other, (old, old))
    rc, recs = run(tmp_path, dest, "exit 3")
    assert rc == 3 and other.exists() and recs == []


def test_refuses_tmp_dest_without_flag(tmp_path):
    rc = sd.main(["--dest", "/tmp/should-not-exist-sd-test", "--", "true"])
    assert rc == 2 and not os.path.exists("/tmp/should-not-exist-sd-test")


def test_project_env_defaults_replace_tmp(tmp_path, monkeypatch):
    dest = tmp_path / "m"
    out = tmp_path / "env.txt"
    monkeypatch.setenv("TMPDIR", "/tmp")
    monkeypatch.delenv("HF_HOME", raising=False)
    rc, _ = run(tmp_path, dest, f'echo "$TMPDIR $HF_HOME" > {out}')
    assert rc == 0
    assert out.read_text().split() == ["/mnt/raid0/llm/tmp", "/mnt/raid0/llm/cache/huggingface"]


def test_check_lists_partials(tmp_path, capsys):
    (tmp_path / "a.aria2").write_text("x")
    assert sd.main(["--check", str(tmp_path)]) == 3
    assert "a.aria2" in capsys.readouterr().out
    assert sd.main(["--check", str(tmp_path / "empty-nonexistent")]) == 0
