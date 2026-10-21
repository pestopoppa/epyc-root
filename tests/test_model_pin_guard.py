"""SEC-ART-7: re-pull drift check. Mocked HF tree/revision API and a fixture registry; no network, no live registry."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("safe_download", ROOT / "scripts/utils/safe_download.py")
sd = importlib.util.module_from_spec(_SPEC)
sys.modules["safe_download"] = sd
_SPEC.loader.exec_module(sd)
guard = sd._load_pin_guard()

PINNED = "a" * 40
MOVED = "b" * 40
OID = "c" * 64
OID_NEW = "d" * 64
REPO = "org/repo"


def sh(script: str) -> list[str]:
    return ["/bin/bash", "-c", script]


def tree(oid: str) -> list[dict]:
    return [{"type": "file", "path": "q/model-Q4_K_M.gguf", "oid": "g1", "size": 4, "lfs": {"oid": oid, "size": 4}},
            {"type": "file", "path": "README.md", "oid": "g2", "size": 1}]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Fixture registry (one pinned role + one unpinned) and an HF API stub whose upstream state the test sets."""
    models = tmp_path / "models" / REPO
    models.mkdir(parents=True)
    reg = {"roles": {
        "pinned": {"model": {"path": str(models / "model-Q4_K_M.gguf"), "hf_repo": REPO,
                             "hf_revision": PINNED, "sha256": OID}},
        "unpinned": {"model": {"path": str(tmp_path / "other.gguf")}},
    }}
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(reg))
    state = {"sha": PINNED, "oid": OID, "calls": []}

    def fake(url):
        state["calls"].append(url)
        if "/revision/" in url:
            return {"sha": state["sha"]}
        return tree(state["oid"])
    monkeypatch.setattr(sd, "hf_get_json", fake)

    def run(*extra, repo=REPO, dest=None, review=None):
        ran = tmp_path / "ran"
        if ran.exists():
            ran.unlink()
        args = ["--dest", str(dest or models), "--allow-tmp", "--ledger", str(tmp_path / "l.jsonl"),
                "--provenance-ledger", str(tmp_path / "prov.jsonl"), "--registry", str(reg_path)]
        if repo:
            args += ["--hf-repo", repo]
        if review:
            args += ["--review-record", str(review)]
        rc = sd.main([*args, *extra, "--", *sh(f"touch {ran}")])
        return rc, ran.exists()

    return type("E", (), {"state": state, "run": staticmethod(run), "tmp": tmp_path, "models": models,
                          "reg_path": reg_path})


def review(tmp_path, **over) -> Path:
    rec = {"schema": guard.REVIEW_SCHEMA, "hf_repo": REPO, "to_revision": MOVED, "decision": "approve",
           "reviewer": "operator", "reviewed_at": "2026-10-21T00:00:00Z"}
    rec.update(over)
    p = tmp_path / "review.json"
    p.write_text(json.dumps(rec))
    return p


def test_matching_pin_proceeds_and_records_ledger(env):
    rc, ran = env.run()
    assert rc == 0 and ran
    assert (env.tmp / "prov.jsonl").exists()


def test_commit_drift_refuses_before_the_download_runs(env, capsys):
    env.state["sha"] = MOVED                                  # repo advanced; the file itself is unchanged
    rc, ran = env.run()
    assert rc == 2 and not ran
    err = capsys.readouterr().err
    assert "commit drift" in err and PINNED in err and MOVED in err and "REFUSED" in err
    assert not (env.tmp / "prov.jsonl").exists()


def test_lfs_oid_drift_at_the_pinned_commit_refuses(env, capsys):
    env.state["oid"] = OID_NEW                                # same commit, different oid: tampered/mocked API
    rc, ran = env.run()
    assert rc == 2 and not ran
    err = capsys.readouterr().err
    assert "oid drift" in err and OID in err and OID_NEW in err


def test_pinned_oid_missing_from_tree_refuses(env, monkeypatch, capsys):
    monkeypatch.setattr(sd, "hf_get_json", lambda url: {"sha": PINNED} if "/revision/" in url
                        else [{"type": "file", "path": "other.gguf", "oid": "x", "size": 1, "lfs": {"oid": OID_NEW}}])
    rc, ran = env.run()
    assert rc == 2 and not ran and "matches no LFS file" in capsys.readouterr().err


def test_review_record_lifts_exactly_this_drift_and_is_ledgered(env):
    env.state["sha"] = MOVED
    rc, ran = env.run(review=review(env.tmp))
    assert rc == 0 and ran
    rec = json.loads((env.tmp / "prov.jsonl").read_text().splitlines()[0])
    assert rec["drift_review"]["reviewer"] == "operator" and rec["drift_review"]["to_revision"] == MOVED


@pytest.mark.parametrize("over,why", [
    ({"to_revision": "e" * 40}, "approves revision"),         # stale approval for an older upstream state
    ({"decision": "reject"}, "need 'approve'"),
    ({"hf_repo": "someone/else"}, "not 'org/repo'"),
    ({"reviewer": ""}, "no reviewer"),
    ({"schema": "x/1"}, "schema"),
])
def test_wrong_review_record_does_not_lift(env, capsys, over, why):
    env.state["sha"] = MOVED
    rc, ran = env.run(review=review(env.tmp, **over))
    assert rc == 2 and not ran and why in capsys.readouterr().err


def test_unreadable_review_record_refuses(env, capsys):
    env.state["sha"] = MOVED
    rc, ran = env.run(review=env.tmp / "missing.json")
    assert rc == 2 and not ran and "unreadable" in capsys.readouterr().err


def test_no_resolve_on_a_registered_repo_is_unverifiable_and_refused(env, capsys, monkeypatch):
    monkeypatch.setattr(sd, "hf_get_json", lambda url: (_ for _ in ()).throw(OSError("offline")))
    rc, ran = env.run("--no-resolve")
    assert rc == 2 and not ran and "unverifiable" in capsys.readouterr().err


def test_tree_api_failure_is_a_refusal_not_a_pass(env, monkeypatch, capsys):
    def fake(url):
        if "/revision/" in url:
            return {"sha": PINNED}
        raise OSError("tree api down")
    monkeypatch.setattr(sd, "hf_get_json", fake)
    rc, ran = env.run()
    assert rc == 2 and not ran and "tree API read" in capsys.readouterr().err


def test_unregistered_repo_is_untouched(env, capsys):
    env.state["sha"] = MOVED
    rc, ran = env.run(repo="org/other", dest=env.tmp / "elsewhere")
    assert rc == 0 and ran and "nothing registered" in capsys.readouterr().err


def test_download_without_hf_repo_into_a_registered_dir_is_refused(env, capsys):
    rc, ran = env.run(repo=None)
    assert rc == 2 and not ran and "--hf-repo" in capsys.readouterr().err
    rc, ran = env.run(repo=None, review=review(env.tmp, to_revision="irrelevant"))   # generic approval lifts it
    assert rc == 0 and ran


def test_download_without_hf_repo_elsewhere_is_untouched(env):
    rc, ran = env.run(repo=None, dest=env.tmp / "scratch")
    assert rc == 0 and ran


def test_corrupt_registry_refuses_missing_registry_warns(env, capsys):
    env.reg_path.write_text("roles: [unclosed")
    rc, ran = env.run()
    assert rc == 2 and not ran and "cannot parse registry" in capsys.readouterr().err
    env.reg_path.unlink()
    rc, ran = env.run()
    assert rc == 0 and ran and "drift check skipped" in capsys.readouterr().err
    rc, ran = env.run("--require-registry")
    assert rc == 2 and not ran


def test_registry_with_no_pins_for_repo_proceeds(env, capsys):
    env.reg_path.write_text(yaml.safe_dump({"roles": {"r": {"model": {"path": "/x/y.gguf"}}}}))
    env.state["sha"] = MOVED
    rc, ran = env.run()
    assert rc == 0 and ran


def test_find_drift_pure_cases():
    pin = guard.Pin("r", "/m/model-Q4_K_M.gguf", REPO, PINNED, OID)
    assert guard.find_drift([pin], PINNED, tree(OID)) == []
    assert guard.find_drift([guard.Pin("r", "/m/m.gguf", REPO, None, None)], MOVED, None) == []   # revision-only pin absent
    both = guard.find_drift([pin], MOVED, tree(OID_NEW))
    assert len(both) == 2 and both[0].startswith("commit drift") and both[1].startswith("oid drift")
    assert guard.pins_for_repo([pin], "ORG/Repo") == [pin]       # HF repo ids are case-insensitive
