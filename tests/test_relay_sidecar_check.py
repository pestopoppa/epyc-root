"""SEC-ART-9: relay and sidecar check against a mocked HF tree/revision/model API."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("relay_sidecar_check", ROOT / "scripts/utils/relay_sidecar_check.py")
rc = importlib.util.module_from_spec(_SPEC)
sys.modules["relay_sidecar_check"] = rc
_SPEC.loader.exec_module(rc)

RELAY, UP = "relay/Model-GGUF", "vendor/Model-GGUF"
RELAY_SHA, UP_SHA = "1" * 40, "2" * 40


def lfs(path, oid, size=10):
    return {"type": "file", "path": path, "oid": "git-" + oid[:4], "size": 1, "lfs": {"oid": oid * 64 if len(oid) == 1 else oid, "size": size}}


def plain(path, oid):
    return {"type": "file", "path": path, "oid": oid, "size": 5}


UPSTREAM_TREE = [lfs("m-Q4.gguf", "a"), lfs("m-Q8.gguf", "b"), plain("README.md", "r1"), {"type": "directory", "path": "d"}]


def fake_api(relay_tree, card=None, up_tree=None):
    seen = []

    def fetch(url):
        seen.append(url)
        if url.endswith(f"/api/models/{RELAY}"):
            return {"cardData": card if card is not None else {"base_model": UP}}
        if f"/{RELAY}/revision/" in url:
            return {"sha": RELAY_SHA}
        if f"/{UP}/revision/" in url:
            return {"sha": UP_SHA}
        if f"/{RELAY}/tree/{RELAY_SHA}" in url:
            return relay_tree
        if f"/{UP}/tree/{UP_SHA}" in url:
            return up_tree if up_tree is not None else UPSTREAM_TREE
        raise AssertionError(url)
    fetch.seen = seen
    return fetch


def test_byte_identical_subset_is_clean():
    out = rc.check(RELAY, UP, fetch=fake_api([lfs("m-Q4.gguf", "a"), plain("README.md", "r1")]))
    assert out["verdict"] == "clean" and out["relay_only"] == [] and out["changed"] == []
    assert out["matched"] == ["README.md", "m-Q4.gguf"] and out["upstream_only"] == ["m-Q8.gguf"]
    assert out["relay"]["revision"] == RELAY_SHA and out["upstream"]["revision"] == UP_SHA


def test_sidecar_the_upstream_lacks_is_listed_and_flagged_tensor_like():
    tree = [lfs("m-Q4.gguf", "a"), lfs("m-Q8.gguf", "b"), lfs("refusal_direction.gguf", "e"), plain("notes.txt", "n1")]
    out = rc.check(RELAY, UP, fetch=fake_api(tree))
    assert out["verdict"] == "relay_extras"
    extras = {r["path"]: r for r in out["relay_only"]}
    assert set(extras) == {"refusal_direction.gguf", "notes.txt"}
    assert extras["refusal_direction.gguf"]["tensor_like"] is True and extras["notes.txt"]["tensor_like"] is False
    assert any("FILE UPSTREAM LACKS: refusal_direction.gguf [tensor-like]" in line for line in rc.render(out))


def test_every_lfs_oid_is_compared_and_changed_file_is_reported():
    out = rc.check(RELAY, UP, fetch=fake_api([lfs("m-Q4.gguf", "a"), lfs("m-Q8.gguf", "9")]))
    assert out["verdict"] == "content_differs"
    assert out["changed"] == [{"path": "m-Q8.gguf", "relay_id": "9" * 64, "upstream_id": "b" * 64, "lfs": True}]


def test_renamed_copy_of_upstream_bytes_is_not_an_extra():
    out = rc.check(RELAY, UP, fetch=fake_api([lfs("m-Q4.gguf", "a"), lfs("copy-of-q8.gguf", "b")]))
    assert out["verdict"] == "clean"
    assert out["relay_only"][0]["renamed_from"] == ["m-Q8.gguf"]


def test_no_overlap_is_not_called_clean():
    out = rc.check(RELAY, UP, fetch=fake_api([lfs("requant-IQ2.gguf", "7")]))
    assert out["verdict"] == "no_overlap" and rc.VERDICT_EXIT["no_overlap"] == 4
    assert any("byte identity is NOT established" in line for line in rc.render(out))
    assert rc.check(RELAY, UP, fetch=fake_api([]))["verdict"] == "no_overlap"


def test_upstream_taken_from_card_only_when_unambiguous():
    f = fake_api([lfs("m-Q4.gguf", "a")])
    out = rc.check(RELAY, None, fetch=f)
    assert out["upstream"]["hf_repo"] == UP and out["upstream"]["claimed_from"] == "cardData.base_model"
    for card in ({}, {"base_model": [UP, "x/y"]}, {"base_model": "not a repo"}):
        with pytest.raises(ValueError, match="pass --upstream"):
            rc.check(RELAY, None, fetch=fake_api([], card=card))


def test_bad_repo_id_and_unresolvable_ref_refused():
    with pytest.raises(ValueError, match="ORG/REPO"):
        rc.check("../etc", UP, fetch=fake_api([]))

    def broken(url):
        return {"sha": "main"}
    with pytest.raises(ValueError, match="no 40-hex commit sha"):
        rc.check(RELAY, UP, fetch=broken)


def test_merge_into_review_keeps_other_fields_and_creates_file(tmp_path):
    out = rc.check(RELAY, UP, fetch=fake_api([lfs("m-Q4.gguf", "a")]))
    rec = tmp_path / "review.json"
    rec.write_text(json.dumps({"schema": "model-review-record/1", "reviewer": "op"}))
    rc.merge_into_review(rec, out)
    got = json.loads(rec.read_text())
    assert got["reviewer"] == "op" and got["relay_sidecar_check"]["verdict"] == "clean"
    fresh = tmp_path / "new.json"
    rc.merge_into_review(fresh, out)
    assert json.loads(fresh.read_text())["relay_sidecar_check"]["schema"] == rc.SCHEMA
    assert not list(tmp_path.glob("*.tmp.*"))


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    tree = [lfs("m-Q4.gguf", "a"), lfs("sidecar.gguf", "e")]
    f = fake_api(tree)
    orig = rc.check
    monkeypatch.setattr(rc, "check", lambda *a, **k: orig(*a, **{**k, "fetch": f}))
    review = tmp_path / "r.json"
    code = rc.main(["--repo", RELAY, "--upstream", UP, "--review-record", str(review)])
    assert code == 3 and "sidecar.gguf" in capsys.readouterr().out
    assert json.loads(review.read_text())["relay_sidecar_check"]["verdict"] == "relay_extras"
    monkeypatch.setattr(rc, "check", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    assert rc.main(["--repo", RELAY, "--upstream", UP]) == 2
