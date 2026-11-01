from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
import science_quota as sq

FIXTURE = Path(__file__).parent / "fixtures" / "loop49" / "science-receipts.jsonl"
AS_OF = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def actual_records():
    return sq.read_jsonl(FIXTURE)


def test_legacy_filed_receipts_without_loop49_terminal_proof_are_unscored():
    summary = sq.summarize(actual_records(), AS_OF, timedelta(hours=24))
    assert summary["kind"] == "epyc.science-quota.v1"
    # These are genuine historical records, but have no LOOP49 grant/ended or
    # sealed qualification evidence. They are visible, and correctly unscored.
    assert summary["owners"] == {
        "NI": {"science_score": 0, "verdict_rows": 0, "failed_runs": 0, "unscored_rows": 2,
               "unscored_reasons": {"terminal-ended-grant-evidence-missing": 2}},
        "codex3": {"science_score": 0, "verdict_rows": 0, "failed_runs": 0, "unscored_rows": 1,
                   "unscored_reasons": {"terminal-ended-grant-evidence-missing": 1}},
    }


def test_only_a_qualified_production_verdict_scores_positive():
    # Pure policy input only; aggregate fixtures remain verbatim real receipts.
    for outcome in ("COMPLETE", "PARTIAL", "DIAGNOSTIC-RESULT"):
        assert sq.policy_score(phase="production", outcome=outcome, granted=True,
                               qualified=True, verdict="matches-predeclared-rule") == 1
    assert sq.policy_score(phase="production", outcome="DIAGNOSTIC-RESULT", granted=True,
                           qualified=True, verdict=" ") == 0


@pytest.mark.parametrize("record", [
    {"phase": "qualification", "outcome": "COMPLETE", "granted": True, "qualified": True, "verdict": "PASS"},
    {"phase": "ready", "outcome": "READY", "granted": False, "qualified": False, "verdict": None},
    {"phase": "ready", "outcome": "READY-WAIT-DISK", "granted": False, "qualified": False, "verdict": None},
    {"phase": "production", "outcome": "PARTIAL", "granted": True, "qualified": True, "verdict": None},
    {"phase": "production", "outcome": "REFUSED-PRE-GRANT", "granted": False, "qualified": False, "verdict": None},
])
def test_non_verdict_rows_do_not_score(record):
    # Score policy is tested directly; no synthetic record enters a rollup.
    assert sq.policy_score(**record) == 0


@pytest.mark.parametrize("mutation", [
    {"owner": " "},
    {"event_time": "2026-10-31T23:00:00"},
    {"source_receipt": {"path": "receipt.FILED", "sha256": "bad"}},
    {"granted": "true"},
    {"outcome": "READY-PER-HOUR"},
])
def test_invalid_records_fail_closed(mutation):
    record = deepcopy(actual_records()[0])
    record.update(mutation)
    with pytest.raises(sq.InvalidRecord):
        sq.validate(record)


def test_future_event_refuses_whole_rollup():
    record = deepcopy(actual_records()[0])
    record["event_time"] = "2026-11-02T00:00:00Z"
    with pytest.raises(sq.InvalidRecord, match="event_time-in-future"):
        sq.summarize([record], AS_OF, timedelta(hours=24))


def test_duplicate_run_id_refuses_double_counting():
    record = actual_records()[0]
    with pytest.raises(sq.InvalidRecord, match="duplicate-run-id"):
        sq.summarize([record, deepcopy(record)], AS_OF, timedelta(hours=24))


def test_changed_source_receipt_body_cannot_score():
    record = deepcopy(actual_records()[0])
    record["source_receipt"]["body"] += "changed\n"
    assert sq.score(sq.validate(record)) == 0


def test_forged_normalized_outcome_and_verdict_cannot_score_real_failed_receipt():
    record = deepcopy(actual_records()[0])
    record.update(outcome="COMPLETE", verdict="meets-predeclared-rule", qualified=True)
    verified = sq.validate(record)
    assert verified["_source_valid"] is False
    assert sq.score(verified) == 0


def test_collect_uses_real_filed_bytes_and_terminal_instead_of_supplied_claims(tmp_path):
    filed_dir, ended_dir, manifests = (tmp_path / name for name in ("filing-done", "grants", "manifests"))
    filed_dir.mkdir(); ended_dir.mkdir(); manifests.mkdir()
    source = Path(__file__).parent / "fixtures" / "loop49" / "codex3-paw-compact-a-20261030.FILED"
    filed = filed_dir / source.name
    filed.write_bytes(source.read_bytes())
    run_id = source.name.removesuffix(".FILED")
    ended = ended_dir / f"{run_id}.ended"
    ended.write_text(
        "rc=127 time=2026-10-31T04:19:01Z reason=harness\npartial=false\n"
        "native_complete=false\nphase=qualification\ngranted=true\n"
        f"id={run_id}\nowner=forged-owner\n"
    )
    records = sq.collect_records(filed_dir, ended_dir, manifests,
                                 nonce_store="/missing", allowlist="/missing",
                                 policy="/missing", flags_dir="/missing")
    assert len(records) == 1
    record = records[0]
    assert record["id"] == run_id
    assert record["owner"] == "forged-owner"  # owner is terminal-derived
    assert record["phase"] == "qualification"  # caller's production claim cannot enter
    assert record["granted"] is True
    assert record["outcome"] == "FAILED-RUN"  # derived from retained filing bytes
    assert record["qualified"] is False
    assert sq.score(sq.validate(record)) == 0


def test_collect_preserves_legacy_filing_without_terminal_as_unscored(tmp_path):
    filed_dir, ended_dir, manifests = (tmp_path / name for name in ("filing-done", "grants", "manifests"))
    filed_dir.mkdir(); ended_dir.mkdir(); manifests.mkdir()
    source = Path(__file__).parent / "fixtures" / "loop49" / "yarn-oolong-s2-host256-eligible26-v32-20261031.FILED"
    (filed_dir / source.name).write_bytes(source.read_bytes())
    record, = sq.collect_records(filed_dir, ended_dir, manifests,
                                 nonce_store="/missing", allowlist="/missing",
                                 policy="/missing", flags_dir="/missing")
    assert record["outcome"] == "PARTIAL"
    assert record["verdict"] == "PARTIAL-no-acceptance"
    assert sq.score(sq.validate(record)) == 0
