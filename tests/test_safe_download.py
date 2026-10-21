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


# ---- SEC-ART-1: revision pinning + provenance ledger (mocked HF API, no network) ----
COMMIT = "e" * 40
OID = "f" * 64


def _fake_hf(monkeypatch, calls, fail_resolve=False):
    def fake(url):
        calls.append(url)
        if "/revision/" in url:
            if fail_resolve:
                raise OSError("offline")
            return {"sha": COMMIT}
        assert f"/tree/{COMMIT}?recursive=1&expand=1" in url
        return [{"type": "file", "path": "w.gguf", "oid": "a1", "size": 4, "lfs": {"oid": OID, "size": 4}},
                {"type": "file", "path": "config.json", "oid": "b2", "size": 2},
                {"type": "file", "path": "not-downloaded.gguf", "oid": "c3", "size": 9, "lfs": {"oid": "9" * 64, "size": 9}},
                {"type": "directory", "path": "sub"}]
    monkeypatch.setattr(sd, "hf_get_json", fake)


def test_hf_download_is_pinned_and_ledgered(tmp_path, monkeypatch):
    calls: list[str] = []
    _fake_hf(monkeypatch, calls)
    dest, prov = tmp_path / "m", tmp_path / "prov" / "dl.jsonl"
    script = (f'mkdir -p {dest}; printf abcd > {dest}/w.gguf; printf {{}} > {dest}/config.json; '
              f'echo "$@" > {tmp_path}/args')
    rc = sd.main(["--dest", str(dest), "--allow-tmp", "--ledger", str(tmp_path / "l.jsonl"),
                  "--hf-repo", "org/repo", "--revision", "main", "--provenance-ledger", str(prov),
                  "--", *sh(script + "; true"), "x"])
    assert rc == 0
    rec = [json.loads(x) for x in prov.read_text().splitlines()]
    assert len(rec) == 1 and rec[0]["schema"] == sd.LEDGER_SCHEMA
    assert rec[0]["hf_revision"] == COMMIT and rec[0]["requested_revision"] == "main"
    by = {f["path"]: f for f in rec[0]["files"]}
    assert set(by) == {"w.gguf", "config.json"}                # only files that exist under dest
    assert by["w.gguf"]["sha256"] == OID and by["w.gguf"]["lfs"] and by["w.gguf"]["size_matches_upstream"]
    assert by["config.json"]["sha256"] is None and by["config.json"]["git_oid"] == "b2"


def test_inject_revision_only_for_hf_download_and_replaces_caller_revision():
    assert sd.inject_revision(["hf", "download", "o/r", "--revision", "main"], COMMIT) == \
        ["hf", "download", "o/r", "--revision", COMMIT]
    assert sd.inject_revision(["huggingface-cli", "download", "o/r", "--revision=v1"], COMMIT)[-2:] == \
        ["--revision", COMMIT]
    assert sd.inject_revision(["curl", "-O", "u"], COMMIT) == ["curl", "-O", "u"]


def test_unresolvable_ref_is_refused_unless_no_resolve(tmp_path, monkeypatch):
    _fake_hf(monkeypatch, [], fail_resolve=True)
    prov = tmp_path / "dl.jsonl"
    base = ["--dest", str(tmp_path / "m"), "--allow-tmp", "--ledger", str(tmp_path / "l.jsonl"),
            "--hf-repo", "org/repo", "--provenance-ledger", str(prov)]
    ran = tmp_path / "ran"
    assert sd.main([*base, "--", *sh(f"touch {ran}")]) == 2 and not ran.exists()
    assert sd.main([*base, "--no-resolve", "--", *sh(f"touch {ran}")]) == 0
    assert ran.exists() and not prov.exists()                  # unpinned run records nothing


def test_failed_download_writes_no_provenance_and_bad_repo_refused(tmp_path, monkeypatch):
    _fake_hf(monkeypatch, [])
    prov = tmp_path / "dl.jsonl"
    common = ["--dest", str(tmp_path / "m"), "--allow-tmp", "--ledger", str(tmp_path / "l.jsonl"),
              "--provenance-ledger", str(prov)]
    assert sd.main([*common, "--hf-repo", "org/repo", "--", *sh("exit 5")]) == 5 and not prov.exists()
    assert sd.main([*common, "--hf-repo", "../etc", "--", *sh("true")]) == 2
