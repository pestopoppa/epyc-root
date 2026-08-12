"""SC10: prospective AutoKernel evaluation events are strict, rederived measurements."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_evaluation_event as ake  # noqa: E402
from autokernel_event_fixture import envelope, event, mutated, rebind_capture, sha  # noqa: E402


def test_journal_envelope_projects_rederived_performance_and_exact_identities():
    source = envelope()
    row = ake.native_rows(source)[0]
    tup = ake.project(row)
    assert tup.metric == "decode_tokens_per_s"
    assert tup.value == pytest.approx(0.04000016000064)
    assert tup.reps == 2 and tup.reps_basis == "scored:paired_blocks"
    assert tup.attestation_sha256 == ake.content_hash(source["payload"])
    assert tup.attestation_locator == (
        "autokernel-journal:ak-20260812-0001:seq=42:"
        "entry=evt-journal-000042:record=ake-20260812-0001")
    assert tup.extra["source_sha256"] == sha("candidate-source")
    assert tup.extra["binary_sha256"] == sha("candidate-binary")
    assert tup.extra["model_sha256"] == sha("model")
    assert tup.extra["resource_claim_receipt"] == "rcpt-cpu-claim-0042"
    assert ct.grade(tup)[:2] == ("Witnessed", "Attested")


def test_bare_event_is_anchored_but_never_claimed_present_on_disk():
    tup = ake.project(ake.native_rows(event())[0])
    assert tup.attestation_locator == "akcap:campaign-20260812-0001"
    assert ct.grade(tup)[:2] == ("Witnessed", "Anchored")


def test_pre_hook_event_and_null_t0_estimate_are_not_backfilled():
    assert ake.native_rows(event(prospective=False)) == ()
    source = event()
    source["performance"].update({
        "raw_samples": [], "raw_samples_ref": "akcap:t0", "paired_blocks": 0,
        "estimate": None, "uncertainty": None,
    })
    assert ake.native_rows(source) == ()


def test_per_arm_repetitions_are_not_conflated_with_paired_blocks():
    source = event()
    source["performance"]["raw_samples"].append([
        2, "decode/seed-3", "selection", "anchor_first", "base", None,
        "2026-08-12T10:01:30Z", [50.1, 50.3], [52.1, 52.3],
    ])
    raw = source["performance"]["raw_samples"]
    source["performance"]["paired_blocks"] = 3
    effects = [
        ((sum(block[8]) / len(block[8])) - (sum(block[7]) / len(block[7])))
        / (sum(block[7]) / len(block[7]))
        for block in raw
    ]
    source["performance"]["estimate"] = sorted(effects)[1]
    rebind_capture(source)
    row = ake.native_rows(source)[0]
    projected = ake.project(row)
    assert source["claim_grammar"]["reps"] == 2
    assert source["performance"]["paired_blocks"] == projected.reps == 3
    assert projected.reps_basis == "scored:paired_blocks"


def test_each_arm_vector_must_carry_the_declared_per_arm_repetitions():
    source = event()
    source["performance"]["raw_samples"][0][8].append(52.1)
    rebind_capture(source)
    assert ake.native_rows(source) == ()


@pytest.mark.parametrize("status", ["invalid", "timeout", "crash", "rejected"])
def test_void_and_non_measurement_verdicts_emit_zero_rows(status):
    source = event()
    source["status"] = status
    assert ake.native_rows(source) == ()


def test_integrity_flag_makes_even_non_pass_event_non_measurement():
    source = event()
    source["status"] = "fail"
    source["integrity_flags"] = ["VOID:HOST_HEALTH_TIER_VIOLATION:FAIL"]
    assert ake.native_rows(source) == ()


def test_noncanonical_malformed_event_fails_closed_without_raising():
    source = event()
    source[1] = "non-string JSON key"
    assert ake.native_rows(source) == ()


@pytest.mark.parametrize(("path", "value"), [
    (("payload", "schema"), "epyc.autokernel.evaluation_event.v4"),
    (("payload", "claim_grammar", "metric"), "prefill_tokens_per_s"),
    (("payload", "claim_grammar", "metric_direction"), "lower_better"),
    (("payload", "claim_grammar", "reps"), 3),
    (("payload", "artifact", "source_sha256"), "0" * 64),
    (("payload", "artifact", "binary_sha256"), sha("other-binary")),
    (("payload", "anchor", "source_commit"), "0" * 40),
    (("payload", "resource_claim_receipt"), "rcpt-other-claim"),
    (("payload", "performance", "raw_samples", 0, 8, 0), 99.0),
    (("payload", "performance", "estimate"), 0.5),
    (("payload", "performance", "paired_blocks"), 3),
    (("payload", "evaluator", "id"), "mutable-evaluator"),
    (("payload", "auto_promote"), True),
    (("record_id",), "ake-other-record"),
])
def test_identity_metric_raw_vector_reduction_and_envelope_mutations_are_load_bearing(path, value):
    assert ake.native_rows(mutated(envelope(), path, value)) == ()


def test_capture_cannot_relabel_model_source_binary_claim_or_raw_material():
    for key, value in (
        ("model_sha256", sha("other-model")),
        ("source_sha256", sha("other-source")),
        ("binary_sha256", sha("other-binary")),
        ("resource_claim_receipt", "rcpt-other"),
        ("raw_samples_sha256", sha("other-raw")),
    ):
        source = envelope()
        source["payload"]["performance"]["search_discipline"]["belief_capture"][key] = value
        assert ake.native_rows(source) == ()


def test_project_revalidates_native_row_instead_of_trusting_adapter_intermediate():
    row = ake.native_rows(envelope())[0]
    forged = copy.deepcopy(row)
    forged["value"] = 99.0
    with pytest.raises(ct.ProjectionError, match="mutated value"):
        ake.project(forged)
