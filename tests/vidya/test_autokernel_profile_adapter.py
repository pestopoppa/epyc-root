from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import claim_tuple as claims
from adapters import autokernel_profile as profile
from ak_cpu_profile_producers import PRODUCERS, produce_bundle

LEGACY = profile.LEGACY_CAPTURE.name
SAMPLED = profile.SAMPLED_CPU_CAPTURE.name


@pytest.fixture(scope="module", params=list(PRODUCERS))
def producer(request):
    return request.param


@pytest.fixture(scope="module")
def actual_profile(producer, tmp_path_factory):
    """One real PROFILE_VERIFIED bundle per pinned capture version (and the live tree)."""
    return produce_bundle(producer, tmp_path_factory)


def _version(producer):
    return PRODUCERS[producer][1]


def _republish(changed, raw, tmp_path, *, tuples=False):
    """Store changed capture bytes and re-derive the publication's own digests over them."""
    event = changed["profile"]["payload"]
    locator = event["artifact_identity"]["locator"]
    (tmp_path / locator).write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    event["artifact_identity"]["sha256"] = digest
    if tuples:
        for name in ("profile_claim_tuple", "validation_claim_tuple"):
            event["measurement_carrier"][name]["attestation_sha256"] = digest
    event["target_profile_digest"] = profile._digest({
        "profile_content": event["profile_content"],
        "loaded_identity": event["loaded_identity"],
        "artifact_identity": event["artifact_identity"],
    })
    changed["profile"]["record_id"] = event["target_profile_digest"]


def _capture(native, artifact_root):
    locator = native["profile"]["payload"]["artifact_identity"]["locator"]
    return json.loads((artifact_root / locator).read_text())


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


_IDENTITY = "profile publication and original terminal identity differ"
_SCOPE = "target profile exceeds the original CPU observation scope"
_TUPLES = "producer-authored profile tuples do not rederive"
# The refusal each substitution must reach, per capture version. Journal identity, scope and
# tuple joins are version-independent checks, so both versions refuse at the same named check;
# what differs per version is the scope and limitation text the tuple is rederived against.
SUBSTITUTION_REFUSALS = {
    version: {"worker": _IDENTITY, "generation": _IDENTITY, "request": _IDENTITY,
              "transition": _IDENTITY, "target": _SCOPE,
              "loaded": "target profile digest does not rederive", "metric": _TUPLES,
              "value": _TUPLES, "claim": _TUPLES, "proposition": _TUPLES}
    for version in (LEGACY, SAMPLED)
}


def test_actual_producer_capture_version_and_pinned_source(actual_profile, producer):
    native, artifact_root = actual_profile
    _commit, version, pinned = PRODUCERS[producer]
    capture = _capture(native, artifact_root)
    assert profile.capture_version(capture["phases"]) is version
    assert capture["limitations"] == list(version.limitations)
    rows = profile.native_rows(native, corpus_root=artifact_root)
    digest = rows[0]["capture_source_digest"]
    assert digest == pinned if pinned else digest in version.bundle_source_digests
    measurement, integrity = profile.project_journal_pair(native, corpus_root=artifact_root)
    assert measurement.extra["limitations"] == list(version.limitations)
    if version.sampled_cpu:
        topology = [phase["topology"]["topology_digest"] for phase in capture["phases"]]
        for claim in (measurement, integrity):
            assert claim.extra["capture_version"] == SAMPLED
            assert claim.extra["sampled_cpu_topology_digests"] == topology
    else:
        for claim in (measurement, integrity):
            assert "capture_version" not in claim.extra
            assert "sampled_cpu_topology_digests" not in claim.extra


def test_pinned_versions_are_closed():
    assert profile.SAMPLED_CPU_LIMITATIONS[:-2] == profile.LEGACY_LIMITATIONS[:-1]
    assert profile.SAMPLED_CPU_LIMITATIONS[-1] == profile.LEGACY_LIMITATIONS[-1]
    assert len(profile.SAMPLED_CPU_LIMITATIONS) == len(profile.LEGACY_LIMITATIONS) + 1
    # Closed = exactly the rolling pins (VB-AK-PIN-REPIN appends; nothing else can widen the allow-list), and the
    # two original pins are never dropped: captures keep their identity.
    assert profile.SAMPLED_CPU_CAPTURE.bundle_source_digests == set(profile.SAMPLED_CPU_ROLLING_PINS.values())
    assert {"54b4a0ef0df78ddda4ed22802ad84bd498381c00d329fe999c99b7e3678f9686",
            "69dea977d0b0c62e30e5cb7f128e2b26090fcda510b436ec3c357d107146ca19"} <= \
        profile.SAMPLED_CPU_CAPTURE.bundle_source_digests
    assert profile.SAMPLED_CPU_CAPTURE.loop_source_digests == \
        profile.SAMPLED_CPU_CAPTURE.bundle_source_digests
    assert not profile.SAMPLED_CPU_CAPTURE.bundle_source_digests & (
        profile.LEGACY_CAPTURE.bundle_source_digests | profile.LEGACY_CAPTURE.loop_source_digests)
    assert profile.LEGACY_CAPTURE.phase_fields == profile._PHASE_FIELDS
    assert profile.LEGACY_CAPTURE.sample_fields == profile._SAMPLE_FIELDS
    assert profile.SAMPLED_CPU_CAPTURE.phase_fields - profile._PHASE_FIELDS == {"topology"}
    assert profile.SAMPLED_CPU_CAPTURE.sample_fields - profile._SAMPLE_FIELDS == {
        "location_periods"}


@pytest.mark.parametrize("change", [
    "worker", "generation", "request", "transition", "target", "loaded", "metric",
    "value", "claim", "proposition",
])
def test_same_plan_and_tuple_substitutions_refuse(actual_profile, producer, change):
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
    expected = SUBSTITUTION_REFUSALS[_version(producer).name][change]
    with pytest.raises(claims.ProjectionError, match=f"^{re.escape(expected)}$"):
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


@pytest.mark.parametrize("field,match", [
    ("terminal_data", "not an original accepted worker result"),
    ("loaded_identity", "loaded identity must be an object"),
])
def test_null_identity_mappings_refuse_canonically(actual_profile, field, match):
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
    with pytest.raises(claims.ProjectionError, match=match):
        profile.project_journal_pair(changed, corpus_root=artifact_root)


def test_widened_kept_scope_refuses_under_either_version(actual_profile, tmp_path):
    original, artifact_root = actual_profile
    changed = copy.deepcopy(original)
    event = changed["profile"]["payload"]
    event["profile_content"]["kept_scope"].append("an unsampled field became a claim")
    _republish(changed, (artifact_root / event["artifact_identity"]["locator"]).read_bytes(),
               tmp_path)
    with pytest.raises(claims.ProjectionError, match=f"^{re.escape(_SCOPE)}$"):
        profile.project_journal_pair(changed, corpus_root=tmp_path)


def _mutate_topology_digest(capture):
    topology = capture["phases"][1]["topology"]
    first = str(topology["logical_cpus"][0])
    topology["cpu_to_numa_node"][first] += 1


def _mutate_location_node(capture):
    row = capture["phases"][1]["samples"]["location_periods"][0]
    row["numa_node"] += 1


def _strip_sample_cpu(capture, phases):
    for index in phases:
        command = capture["phases"][index]["tools"][0]["command"]
        command.remove(profile.SAMPLED_CPU_FLAG)


def _add_sample_cpu(capture):
    for phase in capture["phases"]:
        command = phase["tools"][0]["command"]
        command.insert(command.index("-T") + 1, profile.SAMPLED_CPU_FLAG)


# Sampled-CPU (v2) captures: each sampled field is validated, and a record that is not wholly
# one version is refused with a message naming the failed join.
SAMPLED_REFUSALS = {
    "topology_absent": (lambda c: c["phases"][1].pop("topology"),
                        "sampled CPU topology is absent"),
    "topology_digest": (_mutate_topology_digest, "sampled CPU topology digest does not rederive"),
    "topology_schema": (lambda c: c["phases"][0]["topology"].update(schema="other"),
                        "sampled CPU topology schema differs"),
    "location_absent": (lambda c: c["phases"][1]["samples"].pop("location_periods"),
                        "profile sample reduction has missing or unknown fields"),
    "location_period": (lambda c: c["phases"][1]["samples"]["location_periods"][0].update(
                            period=c["phases"][1]["samples"]["location_periods"][0]["period"] + 1),
                        "sampled CPU location periods do not rederive"),
    "location_node": (_mutate_location_node,
                      "sampled CPU location differs from its captured topology/TIDs"),
    "script_fields": (lambda c: c["phases"][1]["parser"]["command"].__setitem__(
                          c["phases"][1]["parser"]["command"].index("-F") + 1,
                          profile.LEGACY_SCRIPT_FIELDS),
                      "sampled CPU perf script fields differ from its record command"),
    "mixed_phases": (lambda c: _strip_sample_cpu(c, [1]),
                     "profile capture mixes sampled-CPU and legacy perf record phases"),
    # Claiming legacy while publishing the sampled scope: read as legacy, refused at scope.
    "claims_legacy": (lambda c: _strip_sample_cpu(c, [0, 1]), _SCOPE),
    "legacy_limitations": (lambda c: c.update(limitations=list(profile.LEGACY_LIMITATIONS)),
                           "profile capture differs from original publication"),
    "unpinned_source": (lambda c: c["source_closure"]["files"][0].update(sha256="0" * 64),
                        "CPU profile source closure is not the supported producer for capture "
                        "version " + SAMPLED),
}
# Legacy captures stay exactly as strict: no sampled field can be added after the fact.
LEGACY_REFUSALS = {
    "topology_injected": (lambda c: c["phases"][1].update(topology=None),
                          "measurement phase has missing or unknown fields"),
    "location_injected": (lambda c: c["phases"][1]["samples"].update(location_periods=[]),
                          "profile sample reduction has missing or unknown fields"),
    "claims_sampled": (_add_sample_cpu, _SCOPE),
    "sampled_limitations": (lambda c: c.update(limitations=list(profile.SAMPLED_CPU_LIMITATIONS)),
                            "profile capture differs from original publication"),
    "unpinned_source": (lambda c: c["source_closure"]["files"][0].update(sha256="0" * 64),
                        "CPU profile source closure is not the supported producer"),
}


@pytest.mark.parametrize("mutation", sorted(set(SAMPLED_REFUSALS) | set(LEGACY_REFUSALS)))
def test_capture_version_fields_refuse_per_version(actual_profile, producer, tmp_path, mutation):
    original, artifact_root = actual_profile
    table = SAMPLED_REFUSALS if _version(producer).sampled_cpu else LEGACY_REFUSALS
    if mutation not in table:
        pytest.skip(f"{mutation} applies to the other capture version")
    mutate, expected = table[mutation]
    changed = copy.deepcopy(original)
    capture = _capture(changed, artifact_root)
    mutate(capture)
    _republish(changed, json.dumps(capture, sort_keys=True, separators=(",", ":")).encode(),
               tmp_path, tuples=True)
    with pytest.raises(claims.ProjectionError, match=f"^{re.escape(expected)}$"):
        profile.project_journal_pair(changed, corpus_root=tmp_path)


def test_projected_sampled_fields_cannot_be_added_or_rewritten(actual_profile, producer):
    original, artifact_root = actual_profile
    rows = profile.native_rows(original, corpus_root=artifact_root)
    forged = copy.deepcopy(rows[0])
    if _version(producer).sampled_cpu:
        forged["sampled_cpu_topology_digests"] = ["0" * 64, "0" * 64]
        key = "sampled_cpu_topology_digests"
    else:
        forged["capture_version"] = SAMPLED
        key = "capture_version"
    with pytest.raises(claims.ProjectionError, match=f"row mutated {key}"):
        profile.project_profile(forged)
