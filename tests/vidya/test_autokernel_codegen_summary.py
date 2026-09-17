"""Codegen sidecars are advisory observations, never inferred benchmark evidence."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import autokernel_codegen_summary as adapter  # noqa: E402
from adapters import autokernel_corpus  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def sidecar():
    head, tree = "a" * 40, "b" * 40
    objects = [{"relative_path": "a.hsaco", "sha256": "c" * 64,
                "bytes": 128, "disassembly_status": "ok",
                "instruction_mix": {"scalar": 2, "vector": 1, "matrix": 0,
                                    "memory": 0, "other": 0}}]
    toolchain = {"status": "unavailable", "reason": "CMakeCache.txt unavailable",
                 "objdump_stat": None}
    frame = {"backend": "llama_gpu", "build_dir": "/tmp/build", "recipe": {},
             "binary_stat": None, "toolchain": toolchain,
             "object_sha256s": ["c" * 64]}
    frame_sha = digest(frame)
    artifact_ref = f"codegen/{head}.llama_gpu.{frame_sha}.json"
    summary = {"schema": adapter.SOURCE_SCHEMA, "backend": "llama_gpu",
               "authority": "diagnostic_only", "ptx_sass_cubin": "unavailable: non-CUDA backend",
               "register_spills": None, "occupancy": None, "vectorization": None,
               "instruction_mix": objects[0]["instruction_mix"], "objects": objects,
               "status": "partial", "reason": "spills unavailable",
               "champion_head": head, "attempt_identity": "attempt-42",
               "source_tree_oid": tree, "toolchain": toolchain, "build_frame": frame,
               "build_frame_sha256": frame_sha, "artifact_ref": artifact_ref}
    summary["summary_core_sha256"] = digest(summary)
    summary["belief_claim_tuple"] = {
        "measurement_id": f"ak-codegen:attempt-42:{frame_sha}",
        "metric": "codegen_disassembly_availability", "value": 1,
        "unit": "availability indicator", "metric_direction": "higher_better",
        "category": "CANDIDATE",
        "claim": "Bounded native code-object disassembly was available for this retained build",
        "date": "2026-09-17T10:00:00+00:00", "protocol_id": "", "reps": 1,
        "reps_basis": "one retained build; not benchmark repetitions",
        "attestation_locator": artifact_ref, "attestation_sha256": "",
        "attestation_verified": None, "source_class": "measurement",
        "extra": {"authority": "diagnostic_only", "not_throughput_or_correctness": True,
                  "not_occupancy_evidence": True, "attempt_identity": "attempt-42",
                  "retained_source_commit": head, "retained_source_tree_oid": tree,
                  "backend": "llama_gpu", "toolchain": toolchain,
                  "build_frame_sha256": frame_sha,
                  "summary_core_sha256": summary["summary_core_sha256"],
                  "code_objects": [{"relative_path": "a.hsaco", "sha256": "c" * 64}],
                  "instruction_mix": objects[0]["instruction_mix"],
                  "unavailable_fields": ["register_spills", "occupancy", "vectorization"],
                  "ptx_sass_cubin": "unavailable: non-CUDA backend"}}
    return summary


def project(document):
    path = Path("/tmp/store") / document["artifact_ref"]
    rows = adapter.native_rows(document, receipt_locator=f"autokernel:{path}",
                               receipt_sha256="d" * 64, attestation_present=True)
    return adapter.project(rows[0])


def test_valid_sidecar_projects_advisory_tuple():
    row = project(sidecar())
    result = grade(row)
    assert row.value == 1
    assert result[0] == "Judged"
    assert result[1] == "Located"


def test_prehook_sidecar_is_not_reconstructed():
    doc = sidecar()
    del doc["belief_claim_tuple"]
    assert adapter.native_rows(doc) == []


def test_direct_projection_cannot_bypass_native_validation():
    with pytest.raises(ProjectionError):
        adapter.project({"tuple": sidecar()["belief_claim_tuple"]})


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(summary_core_sha256="0" * 64),
    lambda d: d.update(attempt_identity="other"),
    lambda d: d.update(source_tree_oid="e" * 40),
    lambda d: d.update(backend="llama_cpu"),
    lambda d: d.update(build_frame_sha256="f" * 64),
    lambda d: d["objects"][0].update(sha256="f" * 64),
    lambda d: d["objects"][0]["instruction_mix"].update(vector=2),
    lambda d: d["belief_claim_tuple"].update(value=9000),
    lambda d: d["belief_claim_tuple"].update(protocol_id="invented"),
    lambda d: d.update(occupancy=100),
])
def test_tampered_sidecars_refused(mutate):
    doc = copy.deepcopy(sidecar())
    mutate(doc)
    with pytest.raises(ProjectionError):
        project(doc)


def test_corpus_dispatches_one_native_sidecar(tmp_path):
    doc = sidecar()
    path = tmp_path / doc["artifact_ref"]
    path.parent.mkdir()
    path.write_text(json.dumps(doc))
    assert autokernel_corpus.SCHEMA_TO_ADAPTER[adapter.SOURCE_SCHEMA] is adapter
    rows = autokernel_corpus.rows_for_document(path, doc,
                                              hashlib.sha256(path.read_bytes()).hexdigest())
    assert len(rows) == 1
    assert autokernel_corpus._carry_verification(
        adapter.project(rows[0]), rows[0], rows[0]["receipt_sha256"]
    ).attestation_verified is None
