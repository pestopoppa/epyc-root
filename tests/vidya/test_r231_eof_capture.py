"""Offline positive replay and refusal controls for the prospective native EOF adapter."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
FILING = ROOT / "data/vidya/r231-eof-native-20261118"
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import r231_eof_capture as adapter  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402
import cli  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def authored(path, value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    path.write_text(json.dumps({"payload": value, "sha256": digest(encoded)}))
    return adapter.native_rows(path)[0]


def raw_output(row, output):
    row.update(raw_output_b64=base64.b64encode(output).decode(), raw_output_sha256=digest(output))


@pytest.fixture
def native():
    pins = json.loads((FILING / "pins.json").read_bytes())
    bindir = Path(pins["binary_dir"])
    cli = str(bindir / "llama-cli")
    run_id = "a" * 32
    console = f"/example/attempts/{run_id}/console-harness"
    console_digest = digest(b"synthetic harness, no native execution")
    compiler = pins["compiler"]["current_path"]
    plan = adapter._case_plan()
    records = []
    for i, step in enumerate(plan):
        name = step["name"]
        row = dict(step, state="exited", cleanup=True, pid=100 + i, started_monotonic=2 * i,
                   ended_monotonic=2 * i + 1, rc=0, process=None)
        raw_output(row, b"synthetic")
        if i == 0:
            row["argv"] = ["/bin/bash", "/example/verify_ggml_linkage.sh", cli, str(bindir)]
            row["declared_executable_sha256"] = pins["current_tools"]["/bin/bash"]
        elif i == 2:
            row["argv"] = [compiler, "-std=c++17", "/example/harness.cpp", "-L" + str(bindir),
                           "-Wl,-rpath," + str(bindir), "-Wl,--no-as-needed", "-lllama-common", "-o", console]
            row["declared_executable_sha256"] = pins["compiler"]["current_sha256"]
        else:
            image, image_digest, required = console, console_digest, ("libllama-common.so",)
            row["argv"] = [console, name.partition("-")[0]]
            if i == 1:
                image, image_digest, required = cli, adapter.CLI_SHA, adapter.REQUIRED_MAPS
                row["rc"] = 1
                row["argv"] = [cli, "--server-base", "http://127.0.0.1:12345", "--simple-io"]
                raw_output(row, b"Select model by number: ")
            else:
                echo = b"/\x08/\x08 \x08" if name == "advanced-slash" else b""
                raw_output(row, b"READY\n" + echo + b"RESULT more=0 hex=" + step["expected_hex"].encode() + b"\r\n")
            maps = [{"path": path, "sha256": value, "inode": index + 1}
                    for index, (path, value) in enumerate(pins["original_closure"].items())
                    if Path(path).name.startswith(required)]
            row.update(declared_executable_sha256=image_digest, process=dict(
                executable=image, executable_sha256=image_digest, affinity=[0, 1, 2, 3],
                proc_start_ticks=str(i + 1), runtime_maps=maps))
        records.append(row)
    grant = (f"id={adapter.ROW} regions=0-3 start=1970-01-01T00:16Z "
             "end=1970-01-01T00:23:10Z kind=rowflow\n")
    return dict(schema=adapter.SCHEMA, id=adapter.ROW, run_id=run_id, pins=pins,
                status="COMPLETE", mode="native", model_loaded=False, inference_executed=False,
                started_at=1000, ended_at=1030, stop_at=1300, unstarted=[], records=records, plan=plan,
                console_harness_sha256=console_digest,
                grant=dict(row=adapter.ROW, regions="0-3", cpus=[0, 1, 2, 3], original=grant,
                           sha256=digest(grant.encode()), deadline=1300),
                mock=dict(host="127.0.0.1", port=12345, requests=[["GET", "/v1/models"]], cleanup=True,
                          runner_sha256=pins["sources"]["capture.py"]))


def test_complete_native_fixture_uses_shared_grade_and_scoped_consumer(native, tmp_path):
    path = tmp_path / "NATIVE.json"
    row = adapter.project(authored(path, native))
    assert grade(row)[:2] == ("Judged", "Located")
    assert row.value == 9 and row.protocol_id == "" and row.reps == 1
    assert row.applicability == {"consumer": "autokernel.planner"}
    assert len(adapter.frames_for_path(path, as_of="2026-11-18T00:00:00Z")) == 3


def test_scoped_cli_ingests_once(native, tmp_path, capsys):
    path = tmp_path / "NATIVE.json"
    authored(path, native)
    args = ["--ledger", str(tmp_path / "ledger.jsonl"), "--json", "ingest", adapter.SOURCE_KIND,
            "--path", str(path), "--as-of", "2026-11-18T00:00:00Z", "--only-new"]
    assert cli.main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert (first["rows_projected"], first["frames_emitted"], first["refused"]) == (1, 3, [])
    assert cli.main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["frames_skipped"] == 3


@pytest.mark.parametrize(("change", "reason"), [
    ("smoke", "wrong-mode"), ("partial", "incomplete"), ("pins", "pin set"),
    ("affinity", "affinity"), ("mapping", "mapped library"), ("output", "console output"),
    ("source", "original native envelope"), ("mock", "mock requests"), ("order", "ordering"),
    ("resealed_dso", "pin set"), ("duration", "wall-clock window"), ("grant", "terminal window"),
    ("duplicate_marker", "console output"), ("trailing_data", "console output"),
    ("unknown_echo", "console output"),
])
def test_resealed_faults_refuse_even_with_a_valid_outer_hash(native, tmp_path, change, reason):
    path = tmp_path / "NATIVE.json"
    if change == "smoke":
        native["mode"] = "publisher-smoke"
    elif change == "partial":
        native["status"] = "UNKNOWN"
    elif change == "pins":
        native["pins"]["sources"]["capture.py"] = "b" * 64
    elif change == "affinity":
        native["records"][1]["process"]["affinity"] = [4, 5, 6, 7]
    elif change == "mapping":
        native["records"][-1]["process"]["runtime_maps"].clear()
    elif change == "resealed_dso":
        mapping = native["records"][1]["process"]["runtime_maps"][0]
        mapping["sha256"] = "b" * 64
        native["pins"]["original_closure"][mapping["path"]] = mapping["sha256"]
    elif change == "duration":
        native["ended_at"] = native["started_at"] + 1
    elif change == "grant":
        grant = native["grant"]
        grant["original"] = grant["original"].replace("kind=rowflow", "kind=rowflow-dryrun")
        grant["sha256"] = digest(grant["original"].encode())
    elif change == "output":
        raw_output(native["records"][-1], b"READY\nRESULT more=0 hex=00\n")
    elif change in {"duplicate_marker", "trailing_data", "unknown_echo"}:
        slash = next(entry for entry in native["records"] if entry["name"] == "advanced-slash")
        original = base64.b64decode(slash["raw_output_b64"])
        edits = {"duplicate_marker": original + b"RESULT more=0 hex=0a\n",
                 "trailing_data": original + b"extra output\n",
                 "unknown_echo": original.replace(b"/\x08/\x08 \x08", b"foreign prefix")}
        raw_output(slash, edits[change])
    elif change == "order":
        native["records"][3:5] = reversed(native["records"][3:5])
    elif change == "mock":
        native["mock"]["requests"].append(["POST", "/completion"])
    row = authored(path, native)
    if change == "source":
        path.write_text('{"historical": true}')
    with pytest.raises(ProjectionError, match=reason):
        adapter.project(row)
