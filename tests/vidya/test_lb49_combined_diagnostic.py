"""Strict LB4.9 custody/CLI controls; no synthetic measurement warrant.

The real roundtrip uses the prospectively captured plumbing smoke when retained on this
host (or LB49_NATIVE_SIDECAR). No inference, producer execution or canonical-ledger writes.
Malformed/pre-hook controls always run, including on hosts without the private capture.
"""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import lb49_combined_diagnostic as adapter
from claim_tuple import ProjectionError, grade, source_classes
import cli


@pytest.mark.parametrize("body", ["", "{}\n", "{\n"])
def test_empty_legacy_and_malformed_native_sidecars_refuse(tmp_path, body):
    path = tmp_path / "beliefs.jsonl"
    path.write_text(body)
    with pytest.raises(ProjectionError, match="LB49_NATIVE_REFUSED"):
        adapter.native_rows(path)


@pytest.fixture
def captured_sidecar():
    override = os.environ.get("LB49_NATIVE_SIDECAR")
    if override:
        path = Path(override)
    else:
        packet = Path("/mnt/raid0/llm/tmp/codex-ni-lb49-combined-ready-20261030")
        pointer = packet / "SMOKE-COMPLETE.json"
        if not pointer.is_file():
            pytest.skip("prospective native smoke absent; set LB49_NATIVE_SIDECAR")
        path = Path(json.loads(pointer.read_text())["result"]).with_name("beliefs.jsonl")
    if not path.is_file():
        pytest.skip("prospective native smoke sidecar absent")
    return path


def test_real_native_cli_reingest_and_shared_observation_grade(tmp_path, capsys, captured_sidecar):
    natives = adapter.native_rows(captured_sidecar)
    assert len(natives) == 68
    assert source_classes()[adapter.SOURCE_KIND] == "measurement"
    for native in natives:
        tup = adapter.project(native)
        assert grade(tup)[:2] == ("Judged", "Located")
        assert tup.protocol_id == "" and tup.reps == 1
    args = ["--ledger", str(tmp_path / "ledger.jsonl"), "--json", "ingest",
            adapter.SOURCE_KIND, "--path", str(captured_sidecar), "--only-new",
            "--as-of", adapter.now()]
    assert cli.main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["rows_projected"] == 68 and first["frames_emitted"] == 204
    assert not first["refused"]
    assert cli.main(args) == 0
    again = json.loads(capsys.readouterr().out)
    assert again["frames_emitted"] == 0 and again["frames_skipped"] == 204


def _mutations():
    return {
        "legacy": lambda r: r.update(schema="legacy"),
        "partial": lambda r: r.update(status="partial"),
        "native_failure": lambda r: r["result"]["phases"][0].update(rc=1),
        "cleanup": lambda r: r["result"]["phases"][1].update(cleanup_verified=False),
        "birth": lambda r: r["result"]["phases"][1].update(birth_ticks="0"),
        "window": lambda r: r["result"]["phases"][1].update(started_at="2099-01-01T00:00:00+00:00"),
        "runtime": lambda r: r["result"]["phases"][2].update(runtime="/wrong/runtime"),
        "missing_case": lambda r: r["result"]["opcases_rows"].pop(),
        "metric_join": lambda r: r["result"]["comparison"]["records"][0]["per_step"][0].update(max_abs_logit_delta=999),
        "prompt": lambda r: r["declaration"]["plan"]["teacher_forcing"]["prompts"].__setitem__(0, "changed"),
        "artifact": lambda r: r["artifacts"][0].update(sha256="0" * 64),
        "protocol": lambda r: r["declaration"].update(protocol_id="invented"),
    }


@pytest.mark.parametrize("case", sorted(_mutations()))
def test_real_native_control_refuses_without_altering_original(captured_sidecar, case):
    rows = adapter.native_rows(captured_sidecar)
    receipt = Path(rows[0]["row"]["results_path"])
    record = copy.deepcopy(adapter.read_native(receipt))
    _mutations()[case](record)
    record["row_sha256"] = adapter.content_hash({k: v for k, v in record.items() if k != "row_sha256"})
    # The receipt's parent is part of its native input/output joins. A temporary control
    # lives beside it; the original receipt, sidecar, source and native artifacts stay intact.
    with tempfile.NamedTemporaryFile(mode="w", prefix="lb49-control-", suffix=".json",
                                     dir=receipt.parent) as handle:
        json.dump(record, handle)
        handle.flush()
        with pytest.raises((ValueError, OSError, KeyError, TypeError)):
            adapter.read_native(Path(handle.name))


def test_real_sidecar_value_cannot_be_forged(captured_sidecar):
    native = copy.deepcopy(adapter.native_rows(captured_sidecar)[0])
    native["row"]["value"] = 999
    with pytest.raises(ProjectionError):
        adapter.project(native)


def test_nine_shard_selection_is_source_bound_and_order_independent(tmp_path):
    # This tests a selector, not a fabricated native measurement or warrant.
    entries = [f"/canonical/model-{i:05d}-of-00009.gguf" for i in range(1, 10)]
    job = tmp_path / "job.py"
    job.write_text(f"MODEL=Path({entries[0]!r})\nmodel='/canonical/gemma.gguf' if smoke else str(MODEL)\n")
    source = adapter.identity(job)
    for offset in range(9):
        order = entries[offset:] + entries[:offset]
        decl = {"sources": [source], "smoke": False, "model_pins": dict.fromkeys(order, {})}
        assert adapter.selected_entry(decl) == entries[0]
        decl["selected_entry_model"] = entries[0]
        assert adapter.selected_entry(decl) == entries[0]
        decl["selected_entry_model"] = entries[3]
        with pytest.raises(ValueError, match="selected entry conflicts"):
            adapter.selected_entry(decl)


def test_native_ascii_framing_keeps_arbitrary_display_bytes_unchanged(tmp_path):
    log = tmp_path / "native.log"
    original = b"token display:\xef\xff\nNATIVE_REQUEST_BEGIN mode=baseline\nCOMBINED_CAPTURE_COMPLETE\n"
    log.write_bytes(original)
    assert "NATIVE_REQUEST_BEGIN mode=baseline" in adapter.native_log_text(log)
    assert "COMBINED_CAPTURE_COMPLETE" in adapter.native_log_text(log)
    assert log.read_bytes() == original
