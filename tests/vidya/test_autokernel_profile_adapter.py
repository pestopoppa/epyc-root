from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as claims
from adapters import autokernel_profile as profile


@pytest.fixture(scope="module")
def actual_profile(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("actual-cpu-profile")
    configured = os.environ.get("EPYC_RESEARCH_ROOT")
    if not configured:
        pytest.skip("set EPYC_RESEARCH_ROOT for actual CPU profile producer conformance")
    research = Path(configured).resolve()
    sys.path.insert(0, str(research / "scripts" / "kernel_rnd"))
    try:
        from autokernel.loop.test_cpu_profile_runtime import _start, fixture
        materialized, registry, _target, config, _events, _request = fixture(tmp_path)
        controller, runtime = _start(materialized, registry)
        try:
            runtime.tick()
            entries = controller._journal.read_all()
            terminal = next(item.envelope() for item in entries
                if item.kind == profile.LIFECYCLE_KIND
                and item.payload.get("event") == "WORKER_RESULT_ACCEPTED")
            published = next(item.envelope() for item in entries
                if item.kind == profile.PROFILE_KIND
                and item.payload.get("event") == "PROFILE_VERIFIED")
        finally:
            runtime.close()
            controller.close()
        yield {"terminal": terminal, "profile": published}, Path(config["storage"])
    finally:
        sys.path.remove(str(research / "scripts" / "kernel_rnd"))


def test_actual_prospective_profile_projects_only_observation_and_integrity(actual_profile):
    native, artifact_root = actual_profile
    measurement, integrity = profile.project_journal_pair(native, corpus_root=artifact_root)
    assert claims.registered()["autokernel-unified-profile-measurement"] is profile.project_profile
    assert claims.source_classes()["autokernel-unified-profile-integrity"] == claims.VERIFIER_CLASS
    assert claims.grade(measurement)[:2] == ("Judged", "Located")
    assert claims.grade(integrity)[:2] == ("Judged", "Located")
    assert measurement.extra["applicability"] == "profile_observation_only"
    assert integrity.extra["applicability"] == "profile_receipt_integrity_only"
    assert measurement.extra["not_production_validation"] is True
    assert integrity.extra["not_production_validation"] is True
    assert measurement.protocol_id == integrity.protocol_id == ""
    assert measurement.attestation_verified is integrity.attestation_verified is True


@pytest.mark.parametrize("change", [
    "worker", "generation", "request", "transition", "target", "loaded", "metric",
    "value", "claim", "proposition",
])
def test_same_plan_and_tuple_substitutions_refuse(actual_profile, change):
    original, artifact_root = actual_profile
    native = copy.deepcopy(original)
    terminal = native["terminal"]["payload"]
    event = native["profile"]["payload"]
    if change == "worker":
        terminal["worker_id"] += "-other"
    elif change == "generation":
        terminal["worker_generation"] += 1
    elif change == "request":
        terminal["request_id"] += "-other"
    elif change == "transition":
        terminal["lineage_id"] = "0" * 64
    elif change == "target":
        event["target_revision_digest"] = "0" * 64
    elif change == "loaded":
        event["loaded_identity"]["recipe_digest"] = "0" * 64
    elif change == "metric":
        event["measurement_carrier"]["profile_claim_tuple"]["metric"] = "wall_time"
    elif change == "value":
        event["measurement_carrier"]["profile_claim_tuple"]["value"] += 1
    elif change == "claim":
        event["measurement_carrier"]["profile_claim_tuple"]["claim"] = "speedup"
    else:
        event["measurement_carrier"]["validation_claim_tuple"]["decided_proposition"] = "production valid"
    with pytest.raises(claims.ProjectionError):
        profile.project_journal_pair(native, corpus_root=artifact_root)


def test_capture_digest_and_fifo_refuse_promptly(actual_profile, tmp_path):
    original, artifact_root = actual_profile
    changed = copy.deepcopy(original)
    changed["profile"]["payload"]["artifact_identity"]["sha256"] = "0" * 64
    with pytest.raises(claims.ProjectionError, match="digest"):
        profile.project_journal_pair(changed, corpus_root=artifact_root)

    fifo = tmp_path / "capture.json"
    os.mkfifo(fifo)
    changed = copy.deepcopy(original)
    event = changed["profile"]["payload"]
    reference = event["artifact_identity"]
    reference.update(locator=fifo.name, sha256="0" * 64)
    event["target_profile_digest"] = profile._digest({
        "profile_content": event["profile_content"],
        "loaded_identity": event["loaded_identity"],
        "artifact_identity": event["artifact_identity"],
    })
    changed["profile"]["record_id"] = event["target_profile_digest"]
    with pytest.raises(claims.ProjectionError, match="regular file"):
        profile.project_journal_pair(changed, corpus_root=tmp_path)


def test_capture_refuses_symlinked_ancestor(actual_profile, tmp_path):
    original, artifact_root = actual_profile
    link = tmp_path / "linked"
    link.symlink_to(artifact_root, target_is_directory=True)
    with pytest.raises(claims.ProjectionError, match="missing or unsafe"):
        profile.project_journal_pair(original, corpus_root=link)


def test_capture_refuses_root_replacement(actual_profile, tmp_path, monkeypatch):
    original, artifact_root = actual_profile
    root = tmp_path / "store"
    root.mkdir()
    locator = original["profile"]["payload"]["artifact_identity"]["locator"]
    (root / locator).write_bytes((artifact_root / locator).read_bytes())
    moved = tmp_path / "moved-store"
    real_read = os.read
    replaced = False

    def replacing_read(fd, size):
        nonlocal replaced
        value = real_read(fd, size)
        if not replaced:
            replaced = True
            root.rename(moved)
            root.mkdir()
        return value

    monkeypatch.setattr(profile.os, "read", replacing_read)
    with pytest.raises(claims.ProjectionError, match="root changed"):
        profile.project_journal_pair(original, corpus_root=root)


def test_fixture_shape_never_becomes_a_tuple(actual_profile):
    original, artifact_root = actual_profile
    changed = copy.deepcopy(original)
    changed["profile"]["payload"]["measurement_carrier"]["profile_claim_tuple"] = {
        "fixture": True}
    with pytest.raises(claims.ProjectionError, match="missing or unknown"):
        profile.project_journal_pair(changed, corpus_root=artifact_root)


@pytest.mark.parametrize("mutation,match", [
    ("tools", "tool cardinality"),
    ("tool_null", "tool cardinality"),
    ("control_null", "tool control order"),
    ("tids", "TID set exceeds"),
    ("unknown", "missing or unknown"),
    ("total", "period totals"),
])
def test_capture_nested_bounds_and_period_totals_refuse(
        actual_profile, tmp_path, mutation, match):
    original, artifact_root = actual_profile
    changed = copy.deepcopy(original)
    event = changed["profile"]["payload"]
    locator = event["artifact_identity"]["locator"]
    capture = json.loads((artifact_root / locator).read_text())
    measured = capture["phases"][1]
    if mutation == "tools":
        measured["tools"].append(copy.deepcopy(measured["tools"][0]))
    elif mutation == "tool_null":
        measured["tools"][0] = None
    elif mutation == "control_null":
        measured["tools"][0]["controls"][0] = None
    elif mutation == "tids":
        measured["tids"] = list(range(1, 4098))
    elif mutation == "unknown":
        measured["tools"][0]["unexpected"] = True
    else:
        measured["samples"]["sampled_period_total"] += 1
    raw = json.dumps(capture, sort_keys=True, separators=(",", ":")).encode()
    (tmp_path / locator).write_bytes(raw)
    event["artifact_identity"]["sha256"] = hashlib.sha256(raw).hexdigest()
    event["target_profile_digest"] = profile._digest({
        "profile_content": event["profile_content"],
        "loaded_identity": event["loaded_identity"],
        "artifact_identity": event["artifact_identity"],
    })
    changed["profile"]["record_id"] = event["target_profile_digest"]
    with pytest.raises(claims.ProjectionError, match=match):
        profile.project_journal_pair(changed, corpus_root=tmp_path)


def test_unsampled_pinned_target_tid_is_preserved_without_fabricated_period(
        actual_profile, tmp_path):
    original, artifact_root = actual_profile
    changed = copy.deepcopy(original)
    event = changed["profile"]["payload"]
    locator = event["artifact_identity"]["locator"]
    capture = json.loads((artifact_root / locator).read_text())
    capture["phases"][1]["tids"].append(max(capture["phases"][1]["tids"]) + 1)
    raw = json.dumps(capture, sort_keys=True, separators=(",", ":")).encode()
    (tmp_path / locator).write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    event["artifact_identity"]["sha256"] = digest
    for name in ("profile_claim_tuple", "validation_claim_tuple"):
        event["measurement_carrier"][name]["attestation_sha256"] = digest
    event["target_profile_digest"] = profile._digest({
        "profile_content": event["profile_content"],
        "loaded_identity": event["loaded_identity"],
        "artifact_identity": event["artifact_identity"],
    })
    changed["profile"]["record_id"] = event["target_profile_digest"]
    measurement, integrity = profile.project_journal_pair(changed, corpus_root=tmp_path)
    assert measurement.value > 0 and integrity.value == 1


@pytest.mark.parametrize("field", ["terminal_data", "loaded_identity"])
def test_null_identity_mappings_refuse_canonically(actual_profile, field):
    original, artifact_root = actual_profile
    changed = copy.deepcopy(original)
    if field == "terminal_data":
        changed["terminal"]["payload"]["data"] = None
    else:
        event = changed["profile"]["payload"]
        event["loaded_identity"] = None
        event["target_profile_digest"] = profile._digest({
            "profile_content": event["profile_content"],
            "loaded_identity": None,
            "artifact_identity": event["artifact_identity"],
        })
        changed["profile"]["record_id"] = event["target_profile_digest"]
    with pytest.raises(claims.ProjectionError):
        profile.project_journal_pair(changed, corpus_root=artifact_root)
