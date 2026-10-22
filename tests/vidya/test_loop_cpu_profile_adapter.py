"""Original direct CPU producer -> existing corpus/projector; synthetic perf only."""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapters import autokernel_corpus as corpus
from adapters import autokernel_profile as profile
from ak_cpu_profile_producers import PRODUCERS, produce_loop
from claim_tuple import ProjectionError


@pytest.fixture(scope="module", params=list(PRODUCERS))
def producer(request):
    return request.param


@pytest.fixture(scope="module")
def actual(producer, tmp_path_factory):
    """One real direct loop record per pinned capture version (and the live tree)."""
    result = produce_loop(producer, tmp_path_factory)
    path = Path(result["record"])
    return path, json.loads(path.read_text()), result


def test_original_record_routes_through_existing_measurement_and_corpus(actual):
    path, record, result = actual
    rows = corpus.rows_for_document(path, record, result["record_sha256"], corpus_root=path.parent.parent)
    assert len(rows) == 1
    claim = profile.project(rows[0])
    assert claim.source_kind == "autokernel-unified-profile-measurement"
    assert claim.value == result["sampled_period_total"]
    assert claim.protocol_id == "" and claim.extra["not_profile_verified"] is True
    assert claim.extra["not_performance_comparison"] is True
    assert claim.extra["execution_digest"] == result["execution_digest"]
    assert profile.CAPTURE_SCHEMA not in corpus.SCHEMA_TO_ADAPTER
    assert profile.LOOP_CAPTURE_SCHEMA not in corpus.SCHEMA_TO_ADAPTER
    class Ledger:
        def __init__(self): self.frames = []
        def append(self, frame): self.frames.append(frame)
    ledger = Ledger()
    report = corpus.ingest_corpus(ledger, root=path.parent.parent, as_of="2026-09-10T00:00:00Z")
    assert report["rows_projected"] == 1 and report["refused"] == 0
    assert len(ledger.frames) == 3  # original source observation + claim + owning evaluation
    assert profile.project(rows[0]) == claim  # historical reread needs no live owner


@pytest.mark.parametrize("mutation", ["claim", "request", "source", "window", "unknown"])
def test_changed_original_record_or_capture_refuses(actual, mutation):
    path, original, _ = actual
    record = copy.deepcopy(original)
    if mutation == "claim":
        record["profile_claim_tuple"]["value"] += 1
    elif mutation == "unknown":
        record["profile_verified"] = True
    else:
        body = json.loads((path.parent / record["capture"]["locator"]).read_text())
        if mutation == "source":
            body["settings"]["source_closure"]["files"][0]["sha256"] = "0" * 64
        elif mutation == "request":
            body["phases"][1]["response"]["request_hex"] = b"{}".hex()
        else:
            body["phases"][1]["response"]["end"] = 1e100
        raw = json.dumps(body).encode()
        sha = hashlib.sha256(raw).hexdigest()
        leaf = "test-only-mutated-" + mutation + ".json"
        (path.parent / leaf).write_bytes(raw)
        record["capture"] = {"locator": leaf, "sha256": sha, "verified": True}
        record["profile_claim_tuple"].update(attestation_locator=leaf, attestation_sha256=sha)
    with pytest.raises(ProjectionError):
        corpus.rows_for_document(path, record, profile._digest(record), corpus_root=path.parent)


def test_direct_shape_does_not_issue_an_integrity_row(actual):
    path, record, _ = actual
    row = profile.native_rows(record, corpus_root=path.parent)[0]
    with pytest.raises(ProjectionError):
        profile.project_integrity(row)


def test_current_exact_source_is_additive_and_retains_original_projection_identity(
        actual, producer):
    path, record, _ = actual
    _commit, version, pinned = PRODUCERS[producer]
    row = profile.native_rows(record, corpus_root=path.parent)[0]
    digest = row["capture_source_digest"]
    assert digest == pinned if pinned else digest in version.loop_source_digests
    assert profile.MATCHED_CPU_SOURCE_DIGEST == "09e804897a555d19e6b3f37ba56cbc493e5c02b57fc7bc09e41bfdf03e345fc7"
    assert profile.RUNTIME_CPU_SOURCE_DIGEST == "95dcf5179f7eb1e26b4f481e790de740577d30baebe27c939a548a1abf9ffe48"
    assert profile.CURRENT_CPU_SOURCE_DIGEST == "926f9cce5fa92598e5120006611be5d97189952907af06c7561f6f5628c3b2ba"
    assert profile.DIRECT_CPU_SOURCE_DIGEST == "6b2f6060df5b5d36980bc9ea7137168bd9ca978959b22038dfba88b12c50b146"
    assert profile.CPU_SOURCE_DIGEST == "c8c1184429e07d8d692f1e698232814169c21beeeeff88f10286f148a38feec5"


def _rewrite(path, original, mutate, leaf):
    record = copy.deepcopy(original)
    body = json.loads((path.parent / record["capture"]["locator"]).read_text())
    mutate(body)
    raw = json.dumps(body).encode()
    sha = hashlib.sha256(raw).hexdigest()
    (path.parent / leaf).write_bytes(raw)
    record["capture"] = {"locator": leaf, "sha256": sha, "verified": True}
    record["profile_claim_tuple"].update(attestation_locator=leaf, attestation_sha256=sha)
    return record


def test_direct_capture_version_projects_only_sampled_fields(actual, producer):
    path, record, _ = actual
    version = PRODUCERS[producer][1]
    body = json.loads((path.parent / record["capture"]["locator"]).read_text())
    assert profile.capture_version(body["phases"]) is version
    row = profile.native_rows(record, corpus_root=path.parent)[0]
    claim = profile.project(row)
    assert claim.extra["limitations"] == list(version.limitations)
    if version.sampled_cpu:
        assert claim.extra["capture_version"] == version.name
        assert claim.extra["sampled_cpu_topology_digests"] == [
            phase["topology"]["topology_digest"] for phase in body["phases"]]
    else:
        assert "capture_version" not in claim.extra
        assert "sampled_cpu_topology_digests" not in claim.extra
    forged = {**row, "capture_version": profile.SAMPLED_CPU_CAPTURE.name}
    forged["sampled_cpu_topology_digests"] = ["0" * 64, "0" * 64]
    with pytest.raises(ProjectionError, match="direct profile projected row changed"):
        profile.project(forged)


def _forge_topology(body):
    topology = body["phases"][1]["topology"]
    topology["cpu_to_numa_node"][str(topology["logical_cpus"][0])] += 1


def _swap_limitations(body):
    sampled = profile.SAMPLED_CPU_FLAG in body["phases"][0]["tools"][0]["command"]
    body["limitations"] = list(profile.LEGACY_LIMITATIONS if sampled
                               else profile.SAMPLED_CPU_LIMITATIONS)


@pytest.mark.parametrize("mutation,sampled_match,legacy_match", [
    ("topology", "sampled CPU topology digest does not rederive", None),
    ("limitations", "direct loop capture identity/scope differs",
     "direct loop capture identity/scope differs"),
    ("source", "direct CPU profile source closure differs for capture version "
     + profile.SAMPLED_CPU_CAPTURE.name, "direct CPU profile source closure differs"),
])
def test_direct_capture_version_refusals_are_specific(
        actual, producer, mutation, sampled_match, legacy_match):
    path, original, _ = actual
    expected = sampled_match if PRODUCERS[producer][1].sampled_cpu else legacy_match
    if expected is None:
        pytest.skip(f"{mutation} applies only to sampled-CPU captures")
    mutate = {"topology": _forge_topology, "limitations": _swap_limitations,
              "source": lambda body: body["settings"]["source_closure"]["files"][0].update(
                  sha256="0" * 64)}[mutation]
    record = _rewrite(path, original, mutate, f"test-only-version-{mutation}.json")
    with pytest.raises(ProjectionError, match=f"^{re.escape(expected)}$"):
        profile.native_rows(record, corpus_root=path.parent)
