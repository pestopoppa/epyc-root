import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
import replay_session_oracle as replay


def _fixture(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    entries = []
    originals = []
    for name, kind, old, mode in (
        ("p.jsonl", "claude_parent", "success", "verified"),
        ("p/subagents/agent-a.jsonl", "claude_subagent", "unknown", "verified"),
        ("missing.jsonl", "claude_parent", None, "missing"),
        ("p/subagents/agent-b.jsonl", "claude_subagent", "failure", "changed"),
        ("p/subagents/agent-c.jsonl", "claude_subagent", "partial", "refused"),
    ):
        data = b"{}\n"
        sha = hashlib.sha256(data).hexdigest()
        original = dict(backend="claude", path=name, root="/raw", bytes=len(data), sha256=sha)
        originals.append(original)
        entry = dict(original, kind=kind, original_path="/raw/" + name, historical_verdict=old,
                     status="missing" if mode == "missing" else "matched")
        entries.append(entry)
        if mode == "missing":
            continue
        snapshot = inputs / "claude" / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if mode == "refused":
            target = tmp_path / "outside.jsonl"
            target.write_bytes(data)
            snapshot.symlink_to(target)
        else:
            snapshot.write_bytes(b"[]\n" if mode == "changed" else data)
        entry.update(snapshot_path=str(snapshot.relative_to(tmp_path)), frozen_sha256=sha)
    original_raw = json.dumps({"entries": originals, "cutoff": "test"}).encode()
    (inputs / "original-manifest.json").write_bytes(original_raw)
    baseline = inputs / "baseline.jsonl"
    baseline.write_text("".join(
        json.dumps({"path": entry["original_path"], "verdict": entry["historical_verdict"]}) + "\n"
        for entry in entries if entry["historical_verdict"] is not None
    ))
    manifest = inputs / "replay-inputs.json"
    manifest.write_text(json.dumps(dict(
        schema="fm4.frozen_replay_inputs.v1", cutoff="test", entries=entries,
        frozen_original_manifest_sha256=hashlib.sha256(original_raw).hexdigest(),
        historical_verdicts_sha256=replay.digest(baseline),
    )))
    return manifest, baseline


def test_replay_counts_frozen_denominator_and_refuses_mutated_inputs(tmp_path, monkeypatch):
    manifest, baseline = _fixture(tmp_path)
    calls = []

    def assess(path, *, parent_path, parent_cache):
        calls.append(path)
        if path.name == "p.jsonl":
            assert parent_path is None
            return {"verdict": "success", "signals": {"local_verdict": "success"}}
        assert parent_path == path.parents[1].with_suffix(".jsonl")
        return {"verdict": "delivered_no_outcome", "signals": {
            "local_verdict": "delivered_no_outcome",
            "parent_join": "matched", "parent_result": {"outcome": None}}}

    monkeypatch.setattr(replay.session_oracle, "assess", assess)
    out, summary_path = tmp_path / "rows.jsonl", tmp_path / "summary.json"
    summary = replay.replay(manifest, out, summary_path, baseline_path=baseline)
    assert len(calls) == 2
    assert summary["manifest_entries"] == 5
    assert summary["input_status"] == dict(verified=2, missing=1, snapshot_changed=1, snapshot_refused=1)
    assert summary["preserved_historical_verdicts"] == {"success": 1}
    assert summary["changed_historical_verdicts"] == {}
    assert summary["preserved_native_verdicts"] == {"success": 1}
    assert summary["native_before_verdicts"] == summary["assessed_verdicts"]
    assert summary["assessed_verdicts"] == {"success": 1, "delivered_no_outcome": 1}
    assert summary["parent_join_dispositions"] == {"matched": 1}
    assert summary["parent_result_outcomes"] == {"no_outcome": 1}
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert rows[0]["original_path"] == "/raw/p.jsonl"
    assert rows[0]["snapshot_path"] == "inputs/claude/p.jsonl"
    assert sum("assessment" in row for row in rows) == 2
    assert rows[1]["native_before_verdict"] == "delivered_no_outcome"
    assert rows[1]["native_assessment"]["signals"] == {"local_verdict": "delivered_no_outcome"}
    assert json.loads(summary_path.read_text()) == summary


def test_refused_parent_is_never_reopened(tmp_path, monkeypatch):
    manifest, baseline = _fixture(tmp_path)
    (manifest.parent / "claude/p.jsonl").write_bytes(b"[]\n")

    def assess(path, *, parent_path, parent_cache):
        assert path.name == "agent-a.jsonl"
        assert not parent_path.exists()
        assert parent_cache[parent_path] == {}
        return {"verdict": "delivered_no_outcome", "signals": {
            "local_verdict": "delivered_no_outcome", "parent_join": "missing"}}

    monkeypatch.setattr(replay.session_oracle, "assess", assess)
    summary = replay.replay(manifest, tmp_path / "rows", tmp_path / "summary", baseline_path=baseline)
    assert summary["parent_join_dispositions"] == {"missing": 1}


@pytest.mark.parametrize("mutation", ["change_verdict", "remove_verdict", "change_baseline"])
def test_replay_rejects_historical_verdict_provenance_mismatch(tmp_path, mutation):
    manifest, baseline = _fixture(tmp_path)
    payload = json.loads(manifest.read_text())
    if mutation == "change_verdict":
        payload["entries"][0]["historical_verdict"] = "failure"
    elif mutation == "remove_verdict":
        del payload["entries"][0]["historical_verdict"]
    else:
        baseline.write_text(baseline.read_text().replace('"success"', '"failure"'))
    manifest.write_text(json.dumps(payload))
    out = tmp_path / "rows"

    with pytest.raises(ValueError, match="historical verdict"):
        replay.replay(manifest, out, tmp_path / "summary", baseline_path=baseline)
    assert not out.exists()


@pytest.mark.parametrize("joined,expected_exit", [("partial", 0), ("failure", 1)])
def test_replay_exit_guards_native_verdict_independently_of_historical_drift(
    tmp_path, monkeypatch, joined, expected_exit
):
    manifest, baseline = _fixture(tmp_path)

    def assess(path, **_kwargs):
        if path.name == "p.jsonl":
            return {"verdict": joined, "signals": {"local_verdict": "partial"}}
        return {"verdict": "unknown", "signals": {"local_verdict": "unknown"}}

    monkeypatch.setattr(replay.session_oracle, "assess", assess)
    out, summary_path = tmp_path / "rows.jsonl", tmp_path / "summary.json"
    assert replay.main([
        "--manifest", str(manifest), "--out", str(out), "--summary", str(summary_path),
        "--baseline", str(baseline),
    ]) == expected_exit
    summary = json.loads(summary_path.read_text())
    assert summary["changed_historical_verdicts"] == {"success": 1}
    assert summary["changed_native_verdicts"] == ({"partial": 1} if expected_exit else {})
    assert summary["preserved_native_verdicts"] == ({} if expected_exit else {"partial": 1})
