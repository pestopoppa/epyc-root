"""SC69 (P1) — `Attested` means the artifact was re-read and its digest MATCHED, never that a
64-character string was typed.

`claim_tuple` length-checked `attestation_sha256` and branched on its presence; `hashlib` did not
appear in the file at all. `attestation_path="MEASUREMENT.md"` with `attestation_sha256="0"*64`
graded `Witnessed/Attested` — the top of BOTH axes, on a digest of nothing.

`grade()` is a pure function of the tuple, and hashing is I/O: putting the digest check inside
`grade()` would make grading unreproducible from a stored frame (a re-grade would depend on the
artifact's bytes at re-grade time). So the check belongs at the ADAPTER/WRITE boundary, and its
result is CARRIED IN THE TUPLE — the same shape `attestation_present` already uses for existence,
and the same shape the memento adapter already practises end-to-end (its refusal gate recomputes
the digest before projection). The carried field is the only thing that licenses `Attested`.

Design decisions pinned here:

* `attestation_verified=None` (the default) means "not checked" and never reaches `Attested`.
  Every existing adapter that recorded a self-declared digest without re-reading the artifact now
  grades `Witnessed/Anchored` on re-projection — the honest grade for a hash claim nobody checked.
* `attestation_verified=True` means a digest recomputation matched at the write boundary. Only the
  adapter's write path may set it (memento_lora is wired; the rest are follow-ups).
* `attestation_verified=False` is REFUSED, like a false identity binding: a tuple whose recorded
  digest was checked and did NOT match is internally inconsistent — the sha256 field claims the
  artifact IS that hash. Refused, never downgraded (SC56's missing-vs-false distinction).
"""
import hashlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402


def tup(**over):
    base = dict(measurement_id="sc69", metric="decode_tps", value=45.3, date="2026-08-12",
                category="CANDIDATE", claim="c", protocol_id="P-1", reps=3)
    base.update(over)
    return ct.ClaimTuple(**base)


def test_a_digest_of_nothing_never_reaches_attested():
    """CATCHES THE DEFECT: path=MEASUREMENT.md with sha256="0"*64 graded Witnessed/Attested —
    the top of both axes on a digest nobody computed from anything."""
    q, t, reasons = ct.grade(tup(attestation_path="MEASUREMENT.md",
                                 attestation_sha256="0" * 64))
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("never verified" in r for r in reasons)


def test_a_fake_digest_over_a_real_file_never_reaches_attested():
    """MUTATION for the test above: the refusal must fire on the digest, not on its all-zeros
    spelling."""
    q, t, _ = ct.grade(tup(attestation_path="MEASUREMENT.md", attestation_sha256="a" * 64))
    assert (q, t) == ("Witnessed", "Anchored")


def test_a_carried_verification_result_reaches_attested():
    """The carried result IS the licensing fact: the same tuple with the digest verified at the
    write boundary reaches the top rung, and grades reproducibly from the stored tuple alone."""
    q, t, reasons = ct.grade(tup(attestation_path="MEASUREMENT.md",
                                 attestation_sha256="a" * 64, attestation_verified=True))
    assert (q, t) == ("Witnessed", "Attested")
    assert not any("never verified" in r for r in reasons)


def test_verified_without_a_digest_is_refused():
    """A claim that something was verified, with nothing verified, is a lie about a structural
    fact — the same refusal `binding_kind` without a proposition gets."""
    with pytest.raises(ct.ProjectionError, match="attestation_verified"):
        tup(attestation_verified=True)


def test_an_admitted_mismatch_is_refused_not_downgraded():
    """False is refused, never downgraded: a tuple that records a digest WHILE recording that the
    digest did not match the artifact asserts two contradictory facts."""
    with pytest.raises(ct.ProjectionError, match="attestation_verified"):
        tup(attestation_path="MEASUREMENT.md", attestation_sha256="a" * 64,
            attestation_verified=False)


# --- the write-boundary helper ---------------------------------------------------------------

def test_verify_attestation_matches_a_real_digest(tmp_path, monkeypatch):
    monkeypatch.setattr(ct, "REPO_ROOT", tmp_path)
    (tmp_path / "run.json").write_text("{}")
    real = hashlib.sha256(b"{}").hexdigest()
    assert ct.verify_attestation(
        tup(attestation_path="run.json", attestation_sha256=real))


def test_verify_attestation_refuses_a_tampered_artifact(tmp_path, monkeypatch):
    """MUTATION for the match test: the helper must detect the artifact MOVING, which is the
    whole point of re-reading it — a digest over a file that changed proves nothing."""
    monkeypatch.setattr(ct, "REPO_ROOT", tmp_path)
    (tmp_path / "run.json").write_text("{}")
    assert not ct.verify_attestation(
        tup(attestation_path="run.json", attestation_sha256="0" * 64))


def test_verify_attestation_refuses_a_missing_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(ct, "REPO_ROOT", tmp_path)
    assert not ct.verify_attestation(
        tup(attestation_path="run.json", attestation_sha256="0" * 64))


def test_verify_attestation_refuses_an_escaping_path(tmp_path, monkeypatch):
    monkeypatch.setattr(ct, "REPO_ROOT", tmp_path)
    assert not ct.verify_attestation(tup(attestation_path="../../etc/passwd",
                                         attestation_sha256="0" * 64))


def test_grade_never_opens_the_artifact():
    """The purity pin: grading must stay reproducible from a stored tuple alone. A tuple whose
    artifact is ABSENT but whose presence is carried (a sealed manifest attests to files the
    projector already checked) can still grade Attested on the carried verification."""
    q, t, _ = ct.grade(tup(attestation_locator="manifest:run-1", attestation_sha256="a" * 64,
                           attestation_present=True, attestation_verified=True))
    assert (q, t) == ("Witnessed", "Attested")


# --- the memento adapter is the wired producer -----------------------------------------------

def _memento_row(tmp_path, metrics_text="{}"):
    """A memento native row whose attestation pins the canonical content of a real metrics file
    on disk -- the producer shape the adapter's refusal gate recomputes."""
    import json

    from adapters import memento_lora as ml

    metrics_path = tmp_path / "stage1_metrics.json"
    metrics_path.write_text(metrics_text)
    content = json.loads(metrics_path.read_text())
    return {
        "measurement_id": "memento_sft_stage", "metric": "sft_seconds_per_sample",
        "value": 1.5, "unit": "s/sample", "metric_direction": "lower_better",
        "category": "BASELINE",
        "claim": "memento stage-1 belief: the adapter provably updated",
        "protocol_id": ml.PROTOCOL_ID, "reps": 8, "reps_basis": "scored",
        "extra": {
            "date": "2026-09-07", "attestation_locator": "stage1_metrics.json",
            "attestation_path": str(metrics_path),
            "attestation_sha256": ml._content_hash(content),
            "adapter_integrity": {"lora_B_total": 128, "lora_B_nonzero": 128,
                                  "all_tensors_finite": True},
        },
    }


def test_the_memento_adapter_carries_a_real_verification(tmp_path):
    """memento_lora already recomputes the digest at its write boundary -- the row's model for
    the placement. Its projections must now carry the result, or its full tuples would grade
    below what its own refusal gate proved."""
    from adapters import memento_lora as ml

    out = ml.project(_memento_row(tmp_path))
    assert out.attestation_verified is True
    assert ct.grade(out)[:2] == ("Witnessed", "Attested")


def test_the_memento_adapter_refuses_a_moved_record_in_project_too(tmp_path):
    """MUTATION for the test above: project() is the bypass guard for native_rows, so a row whose
    attested record has moved must not project at all -- a caller that skips the gate cannot
    claim a verification that is false."""
    from adapters import memento_lora as ml

    row = _memento_row(tmp_path, metrics_text='{"samples_seen": 1}')
    (tmp_path / "stage1_metrics.json").write_text('{"samples_seen": 2}')
    with pytest.raises(ml.ProjectionError, match="attestation mismatch"):
        ml.project(row)
