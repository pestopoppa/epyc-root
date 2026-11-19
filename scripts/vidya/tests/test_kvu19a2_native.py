import hashlib
import json
import struct

import pytest

from adapters import kvu19a2_native as native
import cli
import ingest_sources
import loop_beliefs


def test_prospective_writer_projects_observed_and_preserves_unknown(tmp_path):
    producer = tmp_path / "producer.py"
    producer.write_text("# synthetic producer\n")
    raw = tmp_path / "raw.bin"
    raw.write_bytes(struct.pack("<ff", 1.0, float("nan")))
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    observed = {"observed": True, "arm": "base", "case": "D576", "nan_elements": 1,
                "raw_path": str(raw), "raw_sha256": digest, "source_archive_sha256": "a" * 64,
                "executable_sha256": "b" * 64, "hip_sha256": "c" * 64, "mapped_ggml": {},
                "gpu_vram_observed": None, "source_build_binding": "unproven"}
    missing = {"observed": False, "arm": "candidate", "case": "D576", "nan_elements": None,
               "missing_reason": "interrupted"}
    result, sidecar = native.record_run(tmp_path / "out", run_id="synthetic", producer=str(producer), observations=[observed, missing])
    assert json.loads(result.read_text())["observations"][1] == missing
    rows = native.native_rows(sidecar)
    assert len(rows) == 1
    claim = native.project(rows[0])
    assert claim.value == 1 and claim.protocol_id == "" and claim.reps == 1
    assert native.frames_for_sidecar(sidecar, as_of="2026-11-02T23:59:59Z")
    with pytest.raises(FileExistsError):
        native.record_run(tmp_path / "out", run_id="synthetic", producer=str(producer), observations=[observed])


def test_capture_refuses_false_count_and_preserves_missing(tmp_path):
    producer = tmp_path / "producer.py"
    producer.write_text("# synthetic producer\n")
    raw = tmp_path / "raw.bin"
    raw.write_bytes(struct.pack("<f", 2.0))
    obs = {"observed": True, "arm": "base", "case": "D576", "nan_elements": 1,
           "raw_path": str(raw), "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
           "source_archive_sha256": "a" * 64, "executable_sha256": "b" * 64,
           "hip_sha256": "c" * 64, "mapped_ggml": {}}
    with pytest.raises(ValueError, match="count mismatch"):
        native.record_run(tmp_path / "bad", run_id="bad", producer=str(producer), observations=[obs])
    result, sidecar = native.record_run(tmp_path / "unknown", run_id="unknown", producer=str(producer),
                                        observations=[{"observed": False, "nan_elements": None,
                                                       "missing_reason": "interrupted"}])
    assert result.exists() and sidecar is None


def test_registered_ingest_positive_and_tamper_refusal(tmp_path):
    producer = tmp_path / "producer.py"
    producer.write_text("# synthetic producer\n")
    raw = tmp_path / "raw.bin"
    raw.write_bytes(struct.pack("<f", 2.0))
    obs = {"observed": True, "arm": "base", "case": "D576", "nan_elements": 0,
           "raw_path": str(raw), "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
           "source_archive_sha256": "a" * 64, "executable_sha256": "b" * 64,
           "hip_sha256": "c" * 64, "mapped_ggml": {}}
    result, sidecar = native.record_run(tmp_path / "run", run_id="synthetic-ingest",
                                        producer=str(producer), observations=[obs])
    assert "kvu19a2-native" in cli._FILE_SOURCES
    assert set(cli._FILE_SOURCES) == set(ingest_sources.SOURCES)
    report = ingest_sources.ingest(None, "kvu19a2-native", [sidecar.parent],
                                   as_of="2026-11-02T23:59:59Z", dry_run=True)
    assert report["units_projected"] == 1 and report["rows_projected"] == 1
    assert report["frames_emitted"] > 0
    row = json.loads(sidecar.read_text())
    row["value"] = 1
    native.ns.seal(row)  # A valid self-hash must not hide disagreement with native evidence.
    sidecar.write_text(json.dumps(row) + "\n")
    refused = ingest_sources.ingest(None, "kvu19a2-native", [sidecar],
                                    as_of="2026-11-02T23:59:59Z", dry_run=True)
    assert len(refused["refused"]) == 1 and refused["frames_emitted"] == 0
    # A historical native result alone is not a producer-written sidecar.
    prehook_dir = tmp_path / "historical"
    prehook_dir.mkdir()
    (prehook_dir / "result.json").write_text(result.read_text())
    prehook = ingest_sources.ingest(None, "kvu19a2-native", [prehook_dir],
                                    as_of="2026-11-02T23:59:59Z", dry_run=True)
    assert prehook["units_matched"] == 0 and prehook["frames_emitted"] == 0


def test_prospective_verified_gpu_scope_reaches_host_planning_tier(tmp_path):
    producer = tmp_path / "producer.py"
    producer.write_text("# synthetic producer\n")
    raw = tmp_path / "raw.bin"
    raw.write_bytes(struct.pack("<f", 2.0))
    log = tmp_path / "native.log"
    log.write_text("Device 0: AMD Instinct MI210, gfx90a:sramecc+\n")
    obs = {"observed": True, "arm": "base", "case": "D576", "nan_elements": 0,
           "raw_path": str(raw), "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
           "source_archive_sha256": "a" * 64, "executable_sha256": "b" * 64,
           "hip_sha256": "c" * 64, "mapped_ggml": {"/libggml-hip.so": "c" * 64},
           "mapping_sample_present": True, "samples": [{"kfd": True, "vram_bytes": 1024}],
           "log_path": str(log), "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
           "applicability": {"backend": "gpu", "device": "gfx90a"}}
    _, sidecar = native.record_run(tmp_path / "scoped", run_id="synthetic-planning",
                                   producer=str(producer), observations=[obs])
    frames = native.frames_for_sidecar(sidecar, as_of="2026-11-02T23:59:59Z")
    target = loop_beliefs.Target.from_mapping({"model_file": "synthetic.gguf", "backend": "gpu", "device": "gfx90a"})
    context = loop_beliefs.collect(frames, [target], as_of="2026-11-02T23:59:59Z")
    assert context["matched_any"]
    assert any(row["source_kind"] == "kvu19a2-native" and row["tier"] == "host" for row in context["rows"])
    assert native.project(native.native_rows(sidecar)[0]).applicability == {"backend": "gpu", "device": "gfx90a"}
    # No verified HIP/memory evidence means the writer must refuse a GPU scope.
    obs["samples"] = [{"kfd": True, "vram_bytes": None}]
    with pytest.raises(ValueError, match="applicability"):
        native.record_run(tmp_path / "no-vram", run_id="bad", producer=str(producer), observations=[obs])
