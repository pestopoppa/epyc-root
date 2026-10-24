"""VB-GNX-REINDEX-1 write side: the GitNexus index receipt is read from the index's own meta.json and self-hashed."""
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gitnexus_index_receipt", ROOT / "scripts" / "gitnexus-index-receipt.py")
rcpt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rcpt)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    (repo / "f").write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", "f"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"],
                   check=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    (repo / ".gitnexus").mkdir()
    (repo / ".gitnexus" / "meta.json").write_text(json.dumps({
        "repoPath": str(repo), "lastCommit": head, "indexedAt": "2026-10-24T01:09:19.625Z", "branch": "main",
        "schemaVersion": 4, "stats": {"files": 3, "nodes": 10, "edges": 20, "communities": 1, "processes": 2,
                                      "embeddings": 0}}))
    return repo, head


def test_receipt_reads_meta_and_self_hashes(tmp_path):
    repo, head = _repo(tmp_path)
    out = tmp_path / "out" / "index_receipt.json"
    assert rcpt.main(["--repo", str(repo), "--out", str(out)]) == 0
    r = json.loads(out.read_text())
    assert r["indexed_commit"] == head == r["git_head"] and r["fresh_at_head"] is True
    assert r["stats"]["nodes"] == 10 and r["stats"]["edges"] == 20 and r["index_branch"] == "main"
    assert r["origin_main"] is None and "no fetch" in r["origin_main_basis"]      # absent, never filled
    assert rcpt.verify(r)
    r["stats"]["nodes"] = 11
    assert not rcpt.verify(r)


def test_stale_index_is_reported_not_hidden(tmp_path):
    repo, head = _repo(tmp_path)
    meta = json.loads((repo / ".gitnexus" / "meta.json").read_text())
    meta["lastCommit"] = "0" * 40
    (repo / ".gitnexus" / "meta.json").write_text(json.dumps(meta))
    r = rcpt.build(repo)
    assert r["fresh_at_head"] is False and r["git_head"] == head and rcpt.verify(r)
