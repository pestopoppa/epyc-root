"""SC3 — the constitution's claim rule, as a grading function.

The tests that matter here are the NEGATIVE ones. It is easy to write a grader that hands out
`Witnessed` when everything is present; the value is in refusing to when something is not, and in
saying which thing was missing. A grade that cannot explain itself gets ignored.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import measurement_record as mr  # noqa: E402


def base(**over):
    rec = {
        "measurement_id": "m-2026-08-12-001",
        "date": "2026-08-12",
        "metric": "decode_tps",
        "value": 45.3,
        "unit": "tok/s",
        "category": "BASELINE",
        "claim": "gemma4-26B-A4B Q4_K_M decodes at 45.3 tok/s under the canonical CPU recipe",
    }
    rec.update(over)
    return rec


# --- the grammar refuses what it cannot grade honestly ------------------------------------

def test_missing_required_field_is_refused():
    rec = base()
    del rec["category"]
    with pytest.raises(mr.MeasurementError, match="category"):
        mr.validate(rec)


def test_empty_string_counts_as_missing():
    """A present-but-blank field is the sneakier version of a missing one."""
    with pytest.raises(mr.MeasurementError, match="empty"):
        mr.validate(base(metric="   "))


def test_category_must_be_exactly_one_of_three():
    """MEASUREMENT_POLICY.md names conflating these the most expensive recurring defect here."""
    with pytest.raises(mr.MeasurementError, match="OPTIMUM"):
        mr.validate(base(category="baseline"))          # case matters
    with pytest.raises(mr.MeasurementError):
        mr.validate(base(category="OPTIMUM/BASELINE"))  # not "both"


def test_zero_reps_refused_but_absent_reps_allowed():
    with pytest.raises(mr.MeasurementError, match="positive integer"):
        mr.validate(base(reps=0))
    mr.validate(base())  # absent is legitimate: it grades down, it does not error


def test_short_digest_refused():
    with pytest.raises(mr.MeasurementError, match="64-character"):
        mr.validate(base(attestation={"path": "x.json", "sha256": "abc123"}))


# --- the grading ladder -------------------------------------------------------------------

def test_no_protocol_is_an_observation_not_a_result():
    """The load-bearing row. The constitution says a number without a protocol NEVER gates."""
    q, t, reasons = mr.grade(base())
    assert q == "Judged"
    assert any("OBSERVATION" in r for r in reasons)


def test_protocol_without_attestation_is_a_result_that_does_not_gate():
    q, t, _ = mr.grade(base(protocol_id="P-CPU-BASE-1", reps=3))
    assert (q, t) == ("Verified", "Located")


def test_named_but_unhashed_artifact_reaches_anchored_not_attested():
    q, t, reasons = mr.grade(base(protocol_id="P-CPU-BASE-1", reps=3,
                                  attestation={"path": "MEASUREMENT.md"}))
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("not hashed" in r for r in reasons)


def test_hash_over_a_missing_file_does_not_reach_attested(tmp_path, monkeypatch):
    """A digest of a file that is not there proves nothing — the whole point of T3."""
    rec = base(protocol_id="P-CPU-BASE-1", reps=3,
               attestation={"path": "does/not/exist.json", "sha256": "a" * 64})
    q, t, reasons = mr.grade(rec)
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("not on disk" in r for r in reasons)


def test_full_tuple_with_present_hashed_artifact_reaches_attested():
    rec = base(protocol_id="P-CPU-BASE-1", reps=3,
               attestation={"path": "MEASUREMENT.md", "sha256": "a" * 64})
    assert mr.grade(rec)[:2] == ("Witnessed", "Attested")


def test_attestation_path_cannot_escape_the_repo():
    """`../../etc/passwd` exists; it is not an attestation for anything in this repo."""
    rec = base(protocol_id="P", reps=1, attestation={"path": "../../etc/passwd",
                                                     "sha256": "a" * 64})
    assert not mr.artifact_exists(rec)
    assert mr.grade(rec)[1] == "Anchored"


def test_every_downgrade_names_its_own_cause():
    """A grade below Attested with no stated reason is unactionable."""
    for rec in (base(),
                base(protocol_id="P"),
                base(protocol_id="P", reps=1),
                base(protocol_id="P", reps=1, attestation={"path": "MEASUREMENT.md"})):
        q, t, reasons = mr.grade(rec)
        if (q, t) != ("Witnessed", "Attested"):
            assert reasons, f"{q}/{t} explained nothing"


# --- the write path -----------------------------------------------------------------------

def test_append_is_dry_runnable_and_stamps_grade(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "LEDGER_DIR", tmp_path)
    stored = mr.append(base(protocol_id="P-1", reps=5,
                            attestation={"path": "MEASUREMENT.md", "sha256": "a" * 64}))
    assert stored["grade"] == {"Q": "Witnessed", "T": "Attested"}
    assert len(stored["record_sha256"]) == 64
    lines = (tmp_path / "2026-08.jsonl").read_text().splitlines()
    assert json.loads(lines[0])["measurement_id"] == "m-2026-08-12-001"


def test_record_hash_covers_the_record_not_the_grade(tmp_path, monkeypatch):
    """Regrading (e.g. after an artifact is deleted) must not silently change the record id."""
    monkeypatch.setattr(mr, "LEDGER_DIR", tmp_path)
    rec = base(protocol_id="P-1", reps=5)
    a = mr.append(rec, dry_run=True)["record_sha256"]
    b = mr.append(dict(rec), dry_run=True)["record_sha256"]
    assert a == b


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "LEDGER_DIR", tmp_path)
    mr.append(base(), dry_run=True)
    assert not list(tmp_path.glob("*.jsonl"))


def test_frames_carry_the_grade_into_the_ledger():
    frames = mr.to_frames(base(protocol_id="P-1", reps=5,
                               attestation={"path": "MEASUREMENT.md", "sha256": "a" * 64}),
                          as_of="2026-08-12T00:00:00Z")
    sup = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert sup["assertion"]["grade"] == {"Q": "Witnessed", "T": "Attested"}
    assert sup["assertion"]["category"] == "BASELINE"


def test_distinct_measurements_get_distinct_claim_ids():
    """The failure this suite exists to prevent, in its cheapest form."""
    a = mr.to_frames(base(measurement_id="m-1"), as_of="t")
    b = mr.to_frames(base(measurement_id="m-2"), as_of="t")
    ids = {f["assertion"].get("claim_id") for f in a + b} - {None}
    assert len(ids) == 2
