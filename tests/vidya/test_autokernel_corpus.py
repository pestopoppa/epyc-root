"""The corpus walk is a dispatcher: it routes, counts and refuses, and never grades."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import autokernel_corpus as corpus  # noqa: E402
from adapters import autokernel_gpu_screening as gpu  # noqa: E402


class _Ledger:
    def __init__(self):
        self.frames = []

    def append(self, frame):
        self.frames.append(frame)


def test_schema_map_routes_to_the_owning_adapter():
    assert corpus.SCHEMA_TO_ADAPTER[gpu.BANK_SCHEMA] is gpu
    assert corpus.SCHEMA_TO_ADAPTER[gpu.RESULT_SCHEMA] is gpu


def test_projection_schemas_are_never_routed():
    """An adapter's own OUTPUT schema must not be fed back into it as input."""
    assert gpu.PROJECTION_SCHEMA not in corpus.SCHEMA_TO_ADAPTER


def test_journal_envelopes_dispatch_on_journal_schema():
    """Journal records carry `journal_schema`, not `schema`.

    Keying only on `schema` silently drops the entire event family -- the walk
    reported 628 documents before this was handled and 3,107 after.
    """
    assert corpus._dispatch_schema({"schema": "epyc.a"}) == "epyc.a"
    assert corpus._dispatch_schema({"journal_schema": "epyc.b"}) == "epyc.b"
    assert corpus._dispatch_schema({"kind": "STOP_STATE"}) is None
    assert corpus._dispatch_schema({"schema": "not-an-epyc-id"}) is None


def test_iter_documents_reads_both_json_and_jsonl(tmp_path):
    (tmp_path / "receipt.json").write_text(json.dumps({"schema": "epyc.x", "n": 1}))
    (tmp_path / "events.jsonl").write_text(
        json.dumps({"journal_schema": "epyc.y", "n": 2}) + "\n"
        + "\n"                                    # blank lines are skipped, not fatal
        + "{ not json\n"                          # malformed lines are skipped
        + json.dumps({"kind": "STOP_STATE"}) + "\n")   # no schema -> not yielded
    (tmp_path / "unrelated.json").write_text(json.dumps({"no_schema": True}))

    found = list(corpus.iter_documents(tmp_path))
    schemas = sorted(corpus._dispatch_schema(doc) for _, doc, _ in found)
    assert schemas == ["epyc.x", "epyc.y"]
    # The jsonl locator names the line, so a refusal can be traced to one record.
    assert any("#L1" in str(path) for path, _, _ in found)


def test_a_refusal_is_counted_not_raised(tmp_path):
    """Strict readers reject records that do not rederive; the walk must continue."""
    bad = {"schema": gpu.RESULT_SCHEMA, "status": "complete"}   # missing everything else
    (tmp_path / "result.json").write_text(json.dumps(bad))
    ledger = _Ledger()
    report = corpus.ingest_corpus(ledger, root=tmp_path, as_of="2026-08-28T00:00:00Z")
    assert report["documents_matched"] == 1
    assert report["rows_projected"] == 0
    # Refused, declined, or not an entry point -- every matched document lands in
    # exactly one bucket, and none of them is an exception escaping the walk.
    assert (report["refused"] + report["schema_not_an_entry_point"]
            + report["documents_yielding_no_rows"]) == 1
    assert ledger.frames == []


def test_unsupported_schema_is_not_reported_as_a_refusal(tmp_path):
    """A mapping miss must not inflate the refusal count.

    'unsupported schema' means this dispatcher pointed a document at a reader that
    does not accept it as an entry point. Counting that as a refusal would hide the
    real ones -- the walk went from 476 apparent refusals to 234 real ones plus 242
    mapping misses once they were separated.
    """
    doc = {"schema": corpus.autokernel_aux_receipt._ARENA_INTERMEDIATE_SCHEMA}
    (tmp_path / "inner.json").write_text(json.dumps(doc))
    ledger = _Ledger()
    report = corpus.ingest_corpus(ledger, root=tmp_path, as_of="2026-08-28T00:00:00Z")
    # This reader declines by returning no rows rather than raising, so the document
    # lands in the declined bucket. Either way it must NOT be counted as a refusal.
    assert report["refused"] == 0
    assert (report["schema_not_an_entry_point"]
            + report["documents_yielding_no_rows"]) == 1


def test_dry_run_appends_nothing(tmp_path):
    (tmp_path / "x.json").write_text(json.dumps({"schema": "epyc.unclaimed"}))
    ledger = _Ledger()
    report = corpus.ingest_corpus(ledger, root=tmp_path, as_of="2026-08-28T00:00:00Z",
                                  dry_run=True)
    assert report["dry_run"] is True
    assert ledger.frames == []


def test_unwired_adapters_are_named_with_their_reason():
    """Three adapters cannot be driven from a single file. Silence would read as coverage."""
    assert set(corpus.UNWIRED) == {
        "autokernel_planner_reduction",
        "autokernel_scaffold_panel",
        "autokernel_fault_rehearsal",
    }
    assert all(reason for reason in corpus.UNWIRED.values())


def test_report_carries_the_unwired_set(tmp_path):
    ledger = _Ledger()
    report = corpus.ingest_corpus(ledger, root=tmp_path, as_of="2026-08-28T00:00:00Z")
    assert report["unwired_adapters"] == corpus.UNWIRED


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
