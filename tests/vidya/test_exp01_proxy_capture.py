"""The real completed source-control filing reaches the CLI, and altered custody refuses."""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))

import cli  # noqa: E402
from adapters import exp01_proxy_capture as capture  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402

FILING = ROOT / "data/vidya/run-filings/2026-11-04/vidya-exp01-proxy-wire-20261104"
SOURCE = "exp01-proxy-capture"
AS_OF = "2026-11-17T19:45:00Z"


def _rewrite_member(filing, name, data):
    path = filing / capture.ARCHIVE
    rewritten = path.with_suffix(".new")
    with tarfile.open(path) as original, tarfile.open(rewritten, "w:gz") as edited:
        for member in original:
            if member.name.partition("/")[2] == name:
                member.size = len(data)
                stream = io.BytesIO(data)
            else:
                stream = original.extractfile(member) if member.isfile() else None
            edited.addfile(member, stream)
    rewritten.replace(path)


def _ingest(ledger, path, capsys):
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", SOURCE, "--path", str(path),
                   "--as-of", AS_OF, "--only-new"])
    assert rc == 0
    return json.loads(capsys.readouterr().out)


def test_completed_control_projects_four_located_observations_and_retry_dedups(tmp_path, capsys):
    ledger = tmp_path / "ledger.jsonl"
    report = _ingest(ledger, FILING, capsys)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (4, 12, [])
    tuples = [capture.project(row) for row in capture.native_rows(FILING)]
    assert [row.applicability["threads"] for row in tuples] == [4] * 4
    assert [row.reps for row in tuples] == [1] * 4
    assert {grade(row)[:2] for row in tuples} == {("Judged", "Located")}
    assert {row.protocol_id for row in tuples} == {""}
    assert {row.extra["mode"] for row in tuples} == {"capture-control"}
    assert all(row.extra["paired_item"] == [
        {"item": "cruxeval_output_0360", "control": False, "intervention": False}
    ] for row in tuples)
    assert _ingest(ledger, FILING, capsys)["frames_skipped"] == 12


@pytest.mark.parametrize(("change", "reason"), [
    ("resource", "resource-mismatched"),
    ("mixed", "mixed native mode"),
    ("partial", "incomplete control"),
    ("stream", "launch stdout changed"),
    ("paired", "fixed paired item"),
    ("incomplete", "extra or missing"),
    ("warrant", "write-time tuple differs"),
])
def test_refused_filing_emits_no_claims(tmp_path, capsys, change, reason):
    filing = tmp_path / "filing"
    shutil.copytree(FILING, filing)
    if change == "stream":
        _rewrite_member(filing, "launches/speed-Q4KM-1.stdout", b"changed")
    else:
        name = {"partial": "TERMINAL.json", "warrant": "NATIVE.json"}.get(change, "results.jsonl")
        path = filing / name
        if name == "results.jsonl":
            rows = [json.loads(line) for line in path.read_bytes().splitlines()]
            if change == "resource":
                rows[1]["threads"] = 24
            if change == "mixed":
                rows[1]["belief_capture"]["mode"] = "smoke"
            if change == "paired":
                rows[-1]["correct"] = True
            if change == "incomplete":
                rows.pop()
            data = "".join(json.dumps(row) + "\n" for row in rows).encode()
        else:
            row = json.loads(path.read_bytes())
            if change == "partial":
                row["state"] = "partial-or-failed"
            else:
                row["belief_measurements"][0]["protocol_id"] = "P-CPU-1"
            data = (json.dumps(row) + "\n").encode()
        path.write_bytes(data)
        _rewrite_member(filing, name, data)
    result = _ingest(tmp_path / "ledger.jsonl", filing, capsys)
    assert result["frames_emitted"] == 0
    assert reason in result["refused"][0]["reason"]


def test_r3_pre_hook_pilot_refuses_and_direct_projection_rechecks_files():
    r3 = ROOT / "docs/evidence/exp01-pilot-r3-20261104"
    with pytest.raises(ProjectionError, match="completion-binding"):
        capture.native_rows(r3)
    row, *_ = capture.native_rows(FILING)
    with pytest.raises(ProjectionError, match="measurement identity was absent"):
        capture.project({**row, "measurement_id": "invented-measurement"})


def test_scalar_and_native_hashes_cannot_override_the_timing_vector(tmp_path, capsys):
    filing = tmp_path / "filing"
    shutil.copytree(FILING, filing)

    def encoded(row):
        return (json.dumps(row) + "\n").encode()

    def sealed(identity, data):
        return {**identity, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    unit = "speed-Q4KM-1"
    with tarfile.open(filing / capture.ARCHIVE) as archive:
        origin = archive.getnames()[0]
        cells = json.load(archive.extractfile(f"{origin}/{unit}.json"))
        launch = json.load(archive.extractfile(f"{origin}/launches/{unit}.json"))
    cells[1]["avg_ts"] = 99.0
    cells[1]["samples_ts"] = [99.0]
    data = encoded(cells)
    _rewrite_member(filing, f"{unit}.json", data)
    _rewrite_member(filing, f"launches/{unit}.stdout", data)
    launch["stdout"] = sealed(launch["stdout"], data)
    _rewrite_member(filing, f"launches/{unit}.json", encoded(launch))

    path = filing / "results.jsonl"
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    rows[1]["tg"] = 99.0
    cap = rows[1]["belief_capture"]
    cap["raw"] = sealed(cap["raw"], data)
    cap["launch"] = sealed(cap["launch"], encoded(launch))
    native_rows = b"".join(map(encoded, rows))
    path.write_bytes(native_rows)
    _rewrite_member(filing, path.name, native_rows)

    packet_path = filing / "NATIVE.json"
    packet = json.loads(packet_path.read_bytes())
    speed = packet["comparison"]["speed_units"][0]
    speed["tg"] = 99.0
    packet["belief_measurements"][0]["value"] = 99.0
    packet["belief_measurements"][0]["extra"]["native_unit"] = speed
    for mapping in packet["belief_measurements"]:
        mapping["attestation_sha256"] = hashlib.sha256(native_rows).hexdigest()
    packet_path.write_bytes(encoded(packet))
    _rewrite_member(filing, packet_path.name, encoded(packet))

    report = _ingest(tmp_path / "ledger.jsonl", filing, capsys)
    assert report["frames_emitted"] == 0
    assert "native speed does not re-derive" in report["refused"][0]["reason"]
