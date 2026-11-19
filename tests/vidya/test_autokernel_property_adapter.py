"""SC18: property residuals enter only through complete durable evaluation events."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_evaluation_event as ake  # noqa: E402
from adapters import autokernel_property as akp  # noqa: E402
from autokernel_event_fixture import envelope, event, mutated, sha  # noqa: E402


def test_old_event_without_write_side_payload_is_not_backfilled():
    assert akp.native_rows(event(properties=False)) == ()


def test_journal_projection_preserves_coordinates_and_recomputed_event_attestation():
    source = envelope()
    row = akp.native_rows(source)[0]
    tup = akp.project(row)
    assert tup.metric == "softmax_invariants/v1"
    assert tup.value == 2.5e-08
    assert tup.metric_direction == "lower_better"
    assert tup.extra["suite_seed"] == 4711
    assert tup.extra["shape_id"] == "SOFT_MAX(type=f32,ne=[83,2,1,1])#0"
    assert tup.extra["source_sha256"] == sha("candidate-source")
    assert tup.attestation_sha256 == ake.content_hash(source["payload"])
    assert ct.grade(tup)[:2] == ("Witnessed", "Attested")


def test_distinct_measurements_have_distinct_claim_identity():
    source = envelope()
    second = copy.deepcopy(
        source["payload"]["correctness"][akp.GATE_ID]["measurements"][0])
    second["shape_id"] = "SOFT_MAX(type=f32,ne=[127,1,1,1])#1"
    source["payload"]["correctness"][akp.GATE_ID]["measurements"].append(second)
    identities = {akp.project(row).measurement_id for row in akp.native_rows(source)}
    assert len(identities) == 2


def test_input_transform_is_part_of_claim_and_identity():
    source = envelope()
    identity = akp.project(akp.native_rows(source)[0])
    source["payload"]["correctness"][akp.GATE_ID]["measurements"][0][
        "input_transform"] = "x3"
    transformed = akp.project(akp.native_rows(source)[0])
    assert transformed.extra["input_transform"] == "x3"
    assert "transform x3" in transformed.claim
    assert transformed.measurement_id != identity.measurement_id


@pytest.mark.parametrize(("path", "value"), [
    (("payload", "correctness", akp.GATE_ID, "measurements", 0, "suite_seed"), 99),
    (("payload", "correctness", akp.GATE_ID, "measurements", 0, "residual"), 2e-4),
    (("payload", "correctness", akp.GATE_ID, "measurements", 0, "passed"), False),
    (("payload", "correctness", akp.GATE_ID, "measurements", 0, "input_transform"), "x9"),
    (("payload", "correctness", akp.GATE_ID, "outcome"), "pass"),
    (("payload", "status"), "invalid"),
])
def test_property_verdict_coordinate_event_identity_and_void_mutations_fail_closed(path, value):
    assert akp.native_rows(mutated(envelope(), path, value)) == ()


def test_source_binary_mutation_changes_event_attestation_and_property_identity():
    original = akp.project(akp.native_rows(envelope())[0])
    changed = mutated(envelope(), ("payload", "artifact", "binary_sha256"),
                      sha("other-binary"))
    projected = akp.project(akp.native_rows(changed)[0])
    assert projected.extra["binary_sha256"] == sha("other-binary")
    assert projected.attestation_sha256 != original.attestation_sha256
    assert projected.measurement_id != original.measurement_id


def test_project_refuses_mutated_intermediate_measurement_or_digest():
    row = akp.native_rows(envelope())[0]
    forged = copy.deepcopy(row)
    forged["measurement"]["residual"] = 0.0
    with pytest.raises(ct.ProjectionError, match="mutated (measurement|event_sha256)"):
        akp.project(forged)
    forged = copy.deepcopy(row)
    forged["event_sha256"] = "a" * 64
    with pytest.raises(ct.ProjectionError, match="mutated event_sha256"):
        akp.project(forged)


def test_diagnostic_marker_projects_observation_and_refuses_claim_warrant():
    source = envelope()
    event = source["payload"]
    event.update({"backend": "llama_cpu", "device_state": None, "status": "inconclusive", "tier": "T0",
                  "quality": {}, "stability": {}, "mechanism": {}})
    event["correctness"] = {akp.GATE_ID: event["correctness"][akp.GATE_ID]}
    event["claim_grammar"].update({"protocol_id": akp.DIAGNOSTIC_RECIPE_ID, "category": "CANDIDATE"})
    event["correctness"][akp.GATE_ID]["requires_anchor"] = False
    event["performance"].update({"raw_samples": [], "paired_blocks": 0, "estimate": None})
    event["performance"]["search_discipline"].update({
        "record_class": akp.DIAGNOSTIC_RECORD_CLASS, "speed_rank_admissible": False})
    assert (rows := akp.native_rows(source))
    tup = akp.project(rows[0])
    assert tup.category == "CANDIDATE"
    assert tup.protocol_id == ""
    assert ct.grade(tup)[:2] == ("Judged", "Located")
    for path, value in (
        (("status",), "pass"),
        (("claim_grammar", "protocol_id"), "other/v1"),
        (("claim_grammar", "category"), "BASELINE"),
        (("quality",), {"gate": "PASS"}),
    ):
        assert akp.native_rows(mutated(source, ("payload", *path), value)) == ()


def test_explicit_cli_accepts_journal_retry_and_counts_invalid_prospective_vector(tmp_path):
    import json
    import subprocess

    sample = tmp_path / "journal"
    sample.mkdir()
    journal_path = sample / "events.jsonl"
    journal_path.write_text(json.dumps(envelope()) + "\n")
    args = [sys.executable, "-B", str(ROOT / "scripts/vidya/cli.py"), "--json",
            "ingest", "autokernel-property", "--root", str(sample),
            "--ledger", str(tmp_path / "local-ledger.jsonl"),
            "--only-new", "--as-of", "2026-11-18T09:00:00Z"]

    def ingest():
        return json.loads(subprocess.check_output(args, text=True))

    first = ingest()
    assert first["by_adapter"] == {"autokernel_property": 1}
    assert first["rows_projected"] == 1 and first["refused"] == 0
    assert first["frames_emitted"] == 3
    retry = ingest()
    assert retry["frames_emitted"] == 0 and retry["refused"] == 0

    bad = mutated(envelope(), ("payload", "correctness", akp.GATE_ID,
                               "measurements", 0, "suite_seed"), 19)
    journal_path.write_text(json.dumps(bad) + "\n" + json.dumps(envelope(properties=False)) + "\n")
    invalid = ingest()
    assert invalid["refused"] == 1 and invalid["rows_projected"] == invalid["frames_emitted"] == 0
    assert invalid["documents_yielding_no_rows"] == 1
