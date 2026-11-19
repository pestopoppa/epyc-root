"""Exercise the registered source with synthetic captures and a scratch ledger."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import cli
from adapters import gpu_pool_native
from ledger import Ledger
from test_gpu_pool_native import fixture as native_fixture


def _argv(ledger, capture):
    return ["--ledger", str(ledger.path), "--json", "ingest", "gpu-pool-native",
            "--path", str(capture), "--as-of", datetime.now(timezone.utc).isoformat(),
            "--only-new"]


def test_registered_ingest_preserves_candidate_local_counts(tmp_path, capsys):
    request, native = native_fixture(tmp_path)
    native["grant"] = {"smoke": False}
    capture = tmp_path / "belief.json"
    gpu_pool_native.write_capture(capture, request, native)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    argv = _argv(ledger, capture)
    result = subprocess.run([sys.executable, "-I", cli.__file__, *argv], cwd=tmp_path,
                            capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (1, 3, [])

    frames = [row.frame for row in ledger.read_all()]
    source, = (frame["assertion"] for frame in frames
               if frame["frame_type"].endswith("source_observed/v1"))
    claim, = (frame["assertion"] for frame in frames
              if frame["frame_type"].endswith("claim_proposed/v1"))
    support, = (frame["assertion"] for frame in frames
                if frame["frame_type"].endswith("evidence_supports_claim/v1"))
    assert source["applicability"] == {"op": native["runs"][0]["op"],
                                       "build_sha": request["identity"]["source"]["commit"],
                                       "candidate_sha256": gpu_pool_native.digest(request["identity"]),
                                       "run_id": request["row_id"], "scope_basis": "native"}
    assert source["title"] == "native_supported_pass_count"
    assert "records 1 native supported passes, 1 unsupported and 1 failures" in claim["display_text"]
    assert support["metric_direction"] == "higher_better" and support["protocol_id"] == ""
    assert support["grade"] == {"Q": "Judged", "T": "Located"}
    assert cli.main(argv) == 0
    assert json.loads(capsys.readouterr().out)["frames_skipped"] == 3
    assert ledger.verify() == [] and len(ledger.read_all()) == 3


@pytest.mark.parametrize("historical", [{"schema": gpu_pool_native.NATIVE}, [{"op": "ROPE"}]])
def test_pre_hook_records_decline(tmp_path, capsys, historical):
    capture = tmp_path / "results.json"
    capture.write_text(json.dumps(historical))
    ledger = Ledger(tmp_path / "ledger.jsonl")
    assert cli.main(_argv(ledger, capture)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["units_matched"] == 1 and report["declined"] == [str(capture)]
    assert report["rows_projected"] == report["frames_emitted"] == 0
    assert report["refused"] == [] and not ledger.path.exists()


@pytest.mark.parametrize(("case", "reason"), [
    ("smoke", "grant.smoke to be false"),
    ("missing-mode", "grant.smoke to be false"),
    ("nonboolean-mode", "grant.smoke to be false"),
    ("tampered-log", "raw log changed"),
    ("tampered-sidecar", "capture digest mismatch"),
    ("malformed-sidecar", "cannot read native GPU pool capture"),
])
def test_registered_ingest_refuses_unqualified_capture(tmp_path, capsys, case, reason):
    request, native = native_fixture(tmp_path)
    if case != "missing-mode":
        native["grant"] = {"smoke": {"smoke": True, "nonboolean-mode": 0}.get(case, False)}
    capture = tmp_path / "belief.json"
    record = gpu_pool_native.write_capture(capture, request, native)
    if case == "tampered-log":
        log = Path(native["runs"][0]["log"])
        log.write_text(log.read_text().replace(" OK", " FAIL"))
    elif case == "tampered-sidecar":
        record["native"]["runs"][0]["passed"] += 1
        capture.write_text(json.dumps(record))
    elif case == "malformed-sidecar":
        capture.write_text("{")

    ledger = Ledger(tmp_path / "ledger.jsonl")
    assert cli.main(_argv(ledger, capture)) == 0
    report = json.loads(capsys.readouterr().out)
    refused, = report["refused"]
    assert refused["unit"] == str(capture) and reason in refused["reason"]
    assert report["rows_projected"] == report["frames_emitted"] == 0
    assert not ledger.path.exists()
