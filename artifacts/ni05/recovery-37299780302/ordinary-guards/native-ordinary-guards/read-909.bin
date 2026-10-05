from __future__ import annotations

import json

import vidya_planner_bridge as bridge


def test_empty_resolution_ledger_skips_subprocess(tmp_path, monkeypatch):
    ledger = tmp_path / "resolutions.jsonl"
    ledger.write_text("")

    def forbidden(*args, **kwargs):  # pragma: no cover - assertion explains the contract
        raise AssertionError("subprocess must not run for an empty ledger")

    monkeypatch.setattr(bridge.subprocess, "run", forbidden)
    assert "none" in bridge.build_settled_ground_block(resolutions_path=ledger)


def test_lookup_output_is_forwarded(tmp_path, monkeypatch):
    ledger = tmp_path / "resolutions.jsonl"
    ledger.write_text('{"hypothesis_id":"h1"}\n')
    lookup = tmp_path / "lookup.py"
    lookup.write_text("# fixture")

    class Result:
        returncode = 0
        stdout = "  Read-only Vidya check\n  - [h1] standing=sealed\n"
        stderr = ""

    monkeypatch.setattr(bridge.subprocess, "run", lambda *args, **kwargs: Result())
    text = bridge.build_settled_ground_block(
        resolutions_path=ledger, lookup_path=lookup
    )
    assert "standing=sealed" in text


def test_lookup_failure_is_not_misreported_as_empty(tmp_path, monkeypatch):
    ledger = tmp_path / "resolutions.jsonl"
    ledger.write_text('{"hypothesis_id":"h1"}\n')
    lookup = tmp_path / "lookup.py"
    lookup.write_text("# fixture")

    class Result:
        returncode = 2
        stdout = ""
        stderr = "broken fold"

    monkeypatch.setattr(bridge.subprocess, "run", lambda *args, **kwargs: Result())
    text = bridge.build_settled_ground_block(
        resolutions_path=ledger, lookup_path=lookup
    )
    assert "UNAVAILABLE" in text
    assert "broken fold" in text


def test_kvq_lookup_output_is_forwarded(tmp_path, monkeypatch):
    lookup = tmp_path / "kvq.py"
    lookup.write_text("# fixture")

    class Result:
        returncode = 0
        stdout = json.dumps({
            "schema": "epyc.vidya.kvq_planner_context.v1",
            "status": "available", "reason": "", "run": "run-1",
            "frontier": 12, "state_hash": "abc",
            "claim_ids": [f"kvq-{i}" for i in range(12)],
            "text": "  KV-quant bench: q8_0/q8_0, 2k, Judged/Located\n"
                    + "\n".join(f"claim_id=kvq-{i}" for i in range(12)),
        })
        stderr = ""

    def fake_run(*args, **kwargs):
        assert "--json" in args[0]
        return Result()

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)
    text = bridge.build_kvq_evidence_block(lookup_path=lookup)
    assert "Judged/Located" in text
    assert bridge.build_kvq_context(lookup_path=lookup)["claim_ids"] == [
        f"kvq-{i}" for i in range(12)
    ]


def test_kvq_lookup_failure_is_explicit(tmp_path, monkeypatch):
    lookup = tmp_path / "kvq.py"
    lookup.write_text("# fixture")

    class Result:
        returncode = 2
        stdout = ""
        stderr = "broken fold"

    monkeypatch.setattr(bridge.subprocess, "run", lambda *args, **kwargs: Result())
    assert "UNAVAILABLE" in bridge.build_kvq_evidence_block(lookup_path=lookup)


def test_kvq_malformed_manifest_fails_closed(tmp_path, monkeypatch):
    lookup = tmp_path / "kvq.py"
    lookup.write_text("# fixture")

    class Result:
        returncode = 0
        stdout = json.dumps({"schema": "epyc.vidya.kvq_planner_context.v1",
                             "status": "available", "text": "looks available",
                             "claim_ids": ["only-one"]})
        stderr = ""

    monkeypatch.setattr(bridge.subprocess, "run", lambda *args, **kwargs: Result())
    result = bridge.build_kvq_context(lookup_path=lookup)
    assert result["status"] == "unavailable"
    assert result["claim_ids"] == []
