"""The measurement ingestion contract: one grammar, one grader, many projections.

The conformance tests at the bottom are the point of this file. Unit tests on the ladder only
prove the ladder is self-consistent; what actually failed in this program was two adapters each
implementing the ladder privately and drifting apart. So the structural tests assert that no
adapter grows its own copy back.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402

VIDYA = ROOT / "scripts" / "vidya"


def tup(**over):
    base = dict(measurement_id="m1", metric="decode_tps", value=45.3, date="2026-08-12",
                category="CANDIDATE", claim="c")
    base.update(over)
    return ct.ClaimTuple(**base)


# --- the grammar refuses what it cannot label ----------------------------------------------

def test_identity_fields_are_structural():
    for name in ("measurement_id", "metric", "claim"):
        with pytest.raises(ct.ProjectionError, match=name):
            tup(**{name: "  "})


def test_gradable_elements_are_not_structural():
    """A measurement missing a date/protocol/reps is a real measurement with a LOW GRADE.

    An earlier draft required `date` in __post_init__, which made dateless runs unrepresentable —
    deleting the very thing the ladder exists to describe. Caught by the sealed-manifest tests.
    """
    t = tup(date="", protocol_id="", reps=None)
    assert ct.grade(t)[0] == "Judged"


def test_category_must_be_one_of_autokernels_three():
    with pytest.raises(ct.ProjectionError, match="OPTIMUM"):
        tup(category="candidate")


def test_metric_direction_is_constrained():
    with pytest.raises(ct.ProjectionError, match="metric_direction"):
        tup(metric_direction="bigger")


def test_zero_reps_is_not_a_measurement():
    with pytest.raises(ct.ProjectionError, match="positive integer"):
        tup(reps=0)


def test_short_digest_refused():
    with pytest.raises(ct.ProjectionError, match="64-character"):
        tup(attestation_sha256="abc")


# --- the single ladder ----------------------------------------------------------------------

def test_no_protocol_is_an_observation():
    q, t, reasons = ct.grade(tup())
    assert (q, t) == ("Judged", "T0")
    assert any("OBSERVATION" in r for r in reasons)


def test_an_observation_that_names_where_it_came_from_is_located():
    """The exact case the two former implementations disagreed on (Judged/T0 vs Judged/Located)."""
    assert ct.grade(tup(attestation_locator="run-7#trial-3"))[:2] == ("Judged", "Located")


def test_protocol_without_attestation_does_not_gate():
    assert ct.grade(tup(protocol_id="P-1", reps=3))[:2] == ("Verified", "Located")


def test_named_but_unhashed_reaches_anchored():
    q, t, reasons = ct.grade(tup(protocol_id="P-1", reps=3, attestation_path="MEASUREMENT.md"))
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("not hashed" in r for r in reasons)


def test_full_tuple_with_present_hashed_artifact_reaches_attested():
    assert ct.grade(tup(protocol_id="P-1", reps=3, attestation_path="MEASUREMENT.md",
                        attestation_sha256="a" * 64))[:2] == ("Witnessed", "Attested")


def test_hash_over_a_missing_file_does_not_attest():
    q, t, reasons = ct.grade(tup(protocol_id="P-1", reps=3, attestation_path="nope/x.json",
                                 attestation_sha256="a" * 64))
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("not on disk" in r for r in reasons)


def test_an_explicit_presence_override_wins_over_the_path():
    """A sealed manifest attests to its `authority/*` files, not to itself, so the projector
    decides presence. Without this the ladder downgraded every sealed run to Anchored."""
    t = tup(protocol_id="P-1", reps=3, attestation_locator="manifest:run-1",
            attestation_sha256="a" * 64, attestation_present=True)
    assert ct.grade(t)[:2] == ("Witnessed", "Attested")


def test_attempted_denominator_is_stated_in_the_reasons():
    _, _, reasons = ct.grade(tup(protocol_id="P-1", reps=55, reps_basis="attempted:total",
                                 attestation_path="MEASUREMENT.md", attestation_sha256="a" * 64))
    assert any("ATTEMPTED" in r for r in reasons)


def test_path_cannot_escape_the_repo_but_a_sibling_repo_is_reachable():
    assert not ct.artifact_present(tup(attestation_path="../../etc/passwd"))
    assert not ct.artifact_present(tup(attestation_path="/etc/passwd"))


def test_every_downgrade_names_its_cause():
    for t in (tup(), tup(protocol_id="P"), tup(protocol_id="P", reps=1),
              tup(protocol_id="P", reps=1, attestation_path="MEASUREMENT.md")):
        q, tt, reasons = ct.grade(t)
        if (q, tt) != ("Witnessed", "Attested"):
            assert reasons, f"{q}/{tt} explained nothing"


# --- conformance: no adapter may grow its own ladder ---------------------------------------

ADAPTER_FILES = sorted((VIDYA / "adapters").glob("*.py")) + [VIDYA / "measurement_record.py"]


def _declared_ladder_files() -> set[str]:
    """Modules that legitimately decide grades, because they registered a source-class ladder."""
    import adapters.research_intake  # noqa: F401  (registers the literature ladder on import)

    return {Path(module).name for module, _ in ct.ladders().values()}


@pytest.mark.parametrize("path", ADAPTER_FILES, ids=lambda p: p.name)
def test_only_a_declared_ladder_may_decide_a_grade(path):
    """Structural guard on the failure that actually happened.

    A second SOURCE CLASS is legitimate — literature is graded by verification status and caps at
    Verified by construction, which is a different rule, not a drifted copy of the measurement one.
    A second implementation of ONE class's rule is the defect. So the check is not "nobody grades"
    but "only a module that declared itself the ladder for a class grades", which is precisely the
    line `measurement_record` and `sealed_manifest` crossed on 2026-08-12.
    """
    if path.name in _declared_ladder_files():
        return
    offenders = [line.strip() for line in path.read_text().splitlines()
                 if re.search(r"return\s+.*[\"'](Witnessed|Verified|Judged)[\"']", line)]
    assert not offenders, (
        f"{path.name} decides a grade without declaring a ladder: {offenders[:3]} — project into a "
        "ClaimTuple and let claim_tuple.grade() decide, or register a new source class explicitly")


def test_each_source_class_has_exactly_one_ladder():
    _declared_ladder_files()
    classes = ct.ladders()
    assert set(classes) >= {"measurement", "literature"}
    assert len({m for m, _ in classes.values()}) == len(classes), "two classes share a module"


def test_a_second_ladder_for_one_class_is_refused():
    with pytest.raises(ct.ProjectionError, match="already has a ladder"):
        ct.register_ladder("measurement", "somewhere/else.py")(lambda *a: ("Witnessed", "T0", []))


def test_the_literature_ladder_can_never_reach_witnessed():
    """An intake entry is a record of what someone else reported. No amount of careful reading
    turns it into a protocol-admissible measurement."""
    from adapters.research_intake import grade_for_entry

    for verification in ("stage1-unverified", "dive-verified", "dive-overturned", None):
        g, _ = grade_for_entry({"verification": verification, "url": "https://x"})
        assert g.q_name != "Witnessed"


def test_the_two_former_graders_now_agree_everywhere():
    """Regression on the concrete divergence, driven through both public entry points."""
    import measurement_record as mr
    from adapters import sealed_manifest as sm

    sealed = {"status": "SEALED", "capture_schema_version": "v2",
              "observational_provenance": {"sealed_at_utc": "2026-08-12T00:00:00Z"},
              "arms": {"a": {"counts": {"n": 3}}}, "runner_sha256": "a" * 64}
    rec = dict(measurement_id="m", date="2026-08-12", metric="x", value=1, unit="u",
               category="BASELINE", claim="c", protocol_id="v2", reps=3,
               attestation={"locator": "manifest:x", "sha256": "a" * 64})
    # Same tuple content, two doors into the ladder: the Q axis must not depend on the door.
    assert mr.grade(rec)[0] == sm.grade(sealed, artifacts_present=False)[0] == "Witnessed"


def test_registry_rejects_a_duplicate_projection_name():
    @ct.register("conformance-probe")
    def _p(x):
        return tup()

    with pytest.raises(ct.ProjectionError, match="already registered"):
        ct.register("conformance-probe")(lambda x: tup())


def test_shared_frame_emission_carries_the_grade_and_the_labels():
    frames = ct.to_frames(tup(protocol_id="P-1", reps=3), as_of="t", adapter_id="probe/v1")
    sup = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert sup["assertion"]["grade"] == {"Q": "Verified", "T": "Located"}
    assert sup["assertion"]["category"] == "CANDIDATE"
    assert sup["assertion"]["metric_direction"] == "higher_better"


def test_frame_ids_derive_from_the_measurement_id():
    """One claim per measurement — the identity property that collided twice this program."""
    a = ct.to_frames(tup(measurement_id="m1"), as_of="t", adapter_id="p")
    b = ct.to_frames(tup(measurement_id="m2"), as_of="t", adapter_id="p")
    ids = {f["assertion"].get("claim_id") for f in a + b} - {None}
    assert len(ids) == 2
