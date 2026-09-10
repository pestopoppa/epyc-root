"""Original direct CPU producer -> existing corpus/projector; synthetic perf only."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
from adapters import autokernel_corpus as corpus
from adapters import autokernel_profile as profile
from claim_tuple import ProjectionError


@pytest.fixture(scope="module")
def actual(tmp_path_factory):
    configured = os.environ.get("EPYC_RESEARCH_ROOT")
    if not configured:
        pytest.skip("set EPYC_RESEARCH_ROOT for original direct CPU producer")
    research = Path(configured).resolve()
    root = tmp_path_factory.mktemp("direct-cpu-profile")
    code = (
        "import json,sys; from pathlib import Path; "
        "from autokernel.loop.test_loop_cpu_profile import produce; "
        "result,_,_=produce(Path(sys.argv[1])); print(json.dumps(result))")
    completed = subprocess.run([sys.executable, "-c", code, str(root)], cwd=research,
        env={**os.environ, "PYTHONPATH": str(research / "scripts/kernel_rnd")},
        capture_output=True, text=True, timeout=60, check=False)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    path = Path(result["record"])
    return path, json.loads(path.read_text()), result


def test_original_record_routes_through_existing_measurement_and_corpus(actual):
    path, record, result = actual
    rows = corpus.rows_for_document(path, record, result["record_sha256"], corpus_root=path.parent.parent)
    assert len(rows) == 1
    claim = profile.project(rows[0])
    assert claim.source_kind == "autokernel-unified-profile-measurement"
    assert claim.value == result["sampled_period_total"]
    assert claim.protocol_id == "" and claim.extra["not_profile_verified"] is True
    assert claim.extra["not_performance_comparison"] is True
    assert claim.extra["execution_digest"] == result["execution_digest"]
    assert profile.CAPTURE_SCHEMA not in corpus.SCHEMA_TO_ADAPTER
    assert profile.LOOP_CAPTURE_SCHEMA not in corpus.SCHEMA_TO_ADAPTER
    class Ledger:
        def __init__(self): self.frames = []
        def append(self, frame): self.frames.append(frame)
    ledger = Ledger()
    report = corpus.ingest_corpus(ledger, root=path.parent.parent, as_of="2026-09-10T00:00:00Z")
    assert report["rows_projected"] == 1 and report["refused"] == 0
    assert len(ledger.frames) == 3  # original source observation + claim + owning evaluation
    assert profile.project(rows[0]) == claim  # historical reread needs no live owner


@pytest.mark.parametrize("mutation", ["claim", "request", "source", "window", "unknown"])
def test_changed_original_record_or_capture_refuses(actual, mutation):
    path, original, _ = actual
    record = copy.deepcopy(original)
    if mutation == "claim":
        record["profile_claim_tuple"]["value"] += 1
    elif mutation == "unknown":
        record["profile_verified"] = True
    else:
        body = json.loads((path.parent / record["capture"]["locator"]).read_text())
        if mutation == "source":
            body["settings"]["source_closure"]["files"][0]["sha256"] = "0" * 64
        elif mutation == "request":
            body["phases"][1]["response"]["request_hex"] = b"{}".hex()
        else:
            body["phases"][1]["response"]["end"] = 1e100
        raw = json.dumps(body).encode()
        sha = hashlib.sha256(raw).hexdigest()
        leaf = "test-only-mutated-" + mutation + ".json"
        (path.parent / leaf).write_bytes(raw)
        record["capture"] = {"locator": leaf, "sha256": sha, "verified": True}
        record["profile_claim_tuple"].update(attestation_locator=leaf, attestation_sha256=sha)
    with pytest.raises(ProjectionError):
        corpus.rows_for_document(path, record, profile._digest(record), corpus_root=path.parent)


def test_direct_shape_does_not_issue_an_integrity_row(actual):
    path, record, _ = actual
    row = profile.native_rows(record, corpus_root=path.parent)[0]
    with pytest.raises(ProjectionError):
        profile.project_integrity(row)
