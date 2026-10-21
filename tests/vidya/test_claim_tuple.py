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


def test_present_hashed_but_unverified_artifact_reaches_anchored_not_attested():
    """SC69: Attested means the artifact was re-read and its digest MATCHED. A recorded
    64-character digest that nothing re-derived is a claim about the artifact, not a
    verification of it — this test is the mutation pair for the one below."""
    q, t, reasons = ct.grade(tup(protocol_id="P-1", reps=3, attestation_path="MEASUREMENT.md",
                                 attestation_sha256="a" * 64))
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("never verified" in r for r in reasons)


def test_full_tuple_with_a_verified_digest_reaches_attested():
    assert ct.grade(tup(protocol_id="P-1", reps=3, attestation_path="MEASUREMENT.md",
                        attestation_sha256="a" * 64,
                        attestation_verified=True))[:2] == ("Witnessed", "Attested")


def test_hash_over_a_missing_file_does_not_attest():
    q, t, reasons = ct.grade(tup(protocol_id="P-1", reps=3, attestation_path="nope/x.json",
                                 attestation_sha256="a" * 64))
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("not on disk" in r for r in reasons)


def test_an_explicit_presence_override_wins_over_the_path():
    """A sealed manifest attests to its `authority/*` files, not to itself, so the projector
    decides presence. Without this the ladder downgraded every sealed run to Anchored."""
    t = tup(protocol_id="P-1", reps=3, attestation_locator="manifest:run-1",
            attestation_sha256="a" * 64, attestation_present=True,
            attestation_verified=True)
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
    line `measurement_record` and `sealed_manifest` crossed on 2026-08-10.
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


def test_absent_applicability_preserves_legacy_frame_bytes():
    from canonical import canonical_bytes
    from frames import make_frame

    legacy = tup()
    frames = ct.to_frames(legacy, as_of="t", adapter_id="probe/v1")
    expected_source = make_frame(
        frame_type="epyc.vidya/frame/source_observed/v1",
        assertion={"source_id": "src_m1", "locator": "measurement:m1",
                   "source_kind": "measurement", "title": "decode_tps",
                   "revision_observed": "2026-08-12"},
        provenance={"method": "probe/v1", "about": "m1", "retrofit": False},
        actor="probe/v1", authority_scope="measurement", created_at="t")
    q, t, reasons = ct.grade(legacy)
    expected = [expected_source, make_frame(
        frame_type="epyc.vidya/frame/claim_proposed/v1",
        assertion={"claim_id": "clm_m1", "display_text": "c", "source_id": "src_m1"},
        provenance={"method": "probe/v1", "derived_from": "src_m1", "about": "m1"},
        actor="probe/v1", authority_scope="measurement", created_at="t"), make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={"claim_id": "clm_m1", "evidence_id": "evd_m1", "grade": {"Q": q, "T": t},
                   "source_id": "src_m1", "protocol_id": "", "reps": None,
                   "category": "CANDIDATE", "metric_direction": "higher_better"},
        provenance={"evidence": "evd_m1", "about": "clm_m1", "method": "probe/v1",
                    "grade_reasons": reasons, "reps_basis": ""},
        actor="probe/v1", authority_scope="measurement", created_at="t")]
    assert canonical_bytes(frames) == canonical_bytes(expected)
    assert canonical_bytes(frames) == canonical_bytes(ct.to_frames(
        tup(applicability={}), as_of="t", adapter_id="probe/v1"))
    assert all("applicability" not in frame["assertion"] for frame in frames)


def test_applicability_roundtrips_in_source_without_changing_grade_or_fold():
    from frames import validate_frame
    from fold import fold

    scope = {"model_file": "/models/m.gguf", "quant": "Q8_0", "backend": "hip",
             "device": "ROCm0", "context_tokens": 8192,
             "kernel": {"commit": "native-commit"}, "run_id": "run-1",
             "run_expected_keys": ["arm-a:decode", "arm-b:decode"]}
    plain = ct.to_frames(tup(), as_of="t", adapter_id="probe/v1")
    scoped = ct.to_frames(tup(applicability=scope), as_of="t", adapter_id="probe/v1")
    assert scoped[0]["assertion"]["applicability"] == scope
    assert scoped[1:] == plain[1:]
    for frame in scoped:
        validate_frame(frame)
    assert ct.grade(tup(applicability=scope)) == ct.grade(tup())
    assert fold(scoped, as_of="t").state_hash() == fold(plain, as_of="t").state_hash()


@pytest.mark.parametrize("scope", [None, [], {"unexpected": "value"},
    {"model_file": None}, {"quant": ""}, {"backend": 0}, {"device": []},
    {"context_tokens": True}, {"context_tokens": 0}, {"kernel": {}},
    {"run_id": " "}, {"run_expected_keys": []}, {"run_expected_keys": [1]},
    {"run_expected_keys": ["a", "a"]}])
def test_malformed_native_applicability_is_refused(scope):
    with pytest.raises(ct.ProjectionError, match="applicability"):
        tup(applicability=scope)


@pytest.mark.parametrize("kernel", [{"bad": float("nan")}, {"bad": object()}, {1: "bad"}])
def test_applicability_kernel_must_be_canonical_json(kernel):
    with pytest.raises(ct.ProjectionError, match="applicability is not canonical JSON"):
        tup(applicability={"kernel": kernel})


@pytest.mark.parametrize("scope", ["{}", "{'kernel': {'commit': 'native'}}"])
def test_packaged_constructor_preserves_legacy_dependency_graph(scope):
    import subprocess
    code = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
from scripts.vidya.claim_tuple import ClaimTuple
assert 'canonical' not in sys.modules and 'scripts.vidya.canonical' not in sys.modules
ClaimTuple(measurement_id='m', metric='m', value=1, date='d', category='CANDIDATE',
           claim='c', applicability={scope})
if {scope} == {{}}:
    assert 'canonical' not in sys.modules and 'scripts.vidya.canonical' not in sys.modules
    assert 'frames' not in sys.modules and 'scripts.vidya.frames' not in sys.modules
"""
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# --- P1-A (loop-belief redesign): observation carrier, new scope keys, byte identity ---------

from dataclasses import replace as _replace  # noqa: E402

from _legacy_frames import legacy_to_frames, outcome  # noqa: E402

P1_FIXTURES = ROOT / "tests" / "vidya" / "fixtures" / "belief_p1"
OBS = {"anchor_value": 21.9, "effect_rel": 0.0205, "noise_floor_rel": 0.03412,
       "decisive": False, "n_pairs": 5, "outcome": "null", "outcome_native": "measured_null",
       "outcome_reason": "within floor", "retrofit": True,
       "mechanism": {"id": "akm-ds41-mmid-qact-block-partition", "statement": "s",
                     "falsifier": "f"}}
SCOPE_P1 = {"model_file": "/m/DeepSeek-V4.1-Flash-Q4.gguf", "model_sha256": "a" * 64,
            "quant": "Q8_0", "backend": "cpu", "device": "epyc-9655",
            "kernel": {"build_path": "/b", "execution_digest": "e"},
            "build_sha": "7ef803926107", "epoch": "c42cd5615dfb", "recipe": "ds41-r",
            "np": 1, "surface": "ggml/src/x.cpp", "symbol": "ggml_iqk_try_mul_mat_id",
            "op": "MUL_MAT_ID", "shape": "4096x2048", "scope_basis": "native",
            "role": "worker", "stack_regime": "r" * 16, "config_key": "k"}


def _p1_real_tuples() -> list:
    """Every tuple the registered P1 projections produce over the real-derived fixtures."""
    import json as _json
    import hashlib as _hashlib

    from adapters import autokernel_legacy_serving as serving
    from adapters import autokernel_serving_floor as floor

    receipts = sorted((P1_FIXTURES / "serving").glob("*/serving-beliefs/*.json"))
    assert len(receipts) == 3, (
        "run tests/vidya/fixtures/belief_p1/derive_fixtures.py to derive the P1 fixtures")
    out = []
    for path in receipts:
        raw = path.read_bytes()
        kw = dict(receipt_locator=f"autokernel:{path}",
                  receipt_sha256=_hashlib.sha256(raw).hexdigest())
        doc = _json.loads(raw)
        out += [serving.project(n) for n in serving.native_rows(doc, **kw)]
        out += [serving.project_v2(n) for n in serving.native_rows_v2(doc, **kw)]
    for path in floor.floor_paths(P1_FIXTURES / "floor" / "q27b"):
        doc, digest = floor.read_floor(path)
        out += [floor.project(n) for n in floor.native_rows(
            doc, locator=f"{floor.LOCATOR_PREFIX}{path}", sha256=digest)]
    return out


def _synthetic_tuples() -> list:
    return [tup(), tup(attestation_locator="run#1"), tup(protocol_id="P-1", reps=3),
            tup(applicability={"model_file": "/m.gguf", "backend": "cpu"}),
            tup(applicability=SCOPE_P1), tup(unit="t/s", value=81.12),
            tup(source_class="verifier", decided_proposition="MUL_MAT failed on ROCm0"),
            tup(source_class="verifier", decided_proposition="c", binding_kind="identity")]


def test_p1a_byte_identity_without_observation_over_every_registered_p1_projection():
    """(a) A tuple with no observation emits the pre-P1-A bytes. Driven over the synthetic
    variants AND every v1 tuple the registered projections produce from the real fixtures; the
    session recorder in conftest.py extends this to every tuple any adapter test builds."""
    corpus = [t for t in _synthetic_tuples() + _p1_real_tuples() if not t.observation]
    assert len(corpus) >= len(_synthetic_tuples()) + 6  # 3 captures x 2 v1 arms
    kw = {"as_of": "2026-10-21T00:00:00Z", "adapter_id": "probe/v1"}
    for t in corpus:
        assert outcome(ct.to_frames, t, **kw) == outcome(legacy_to_frames, t, **kw), t.measurement_id


def test_p1a_byte_identity_holds_for_observation_stripped_p1_tuples():
    """Stripping the observation from a v2/floor tuple returns it to the old emission exactly."""
    kw = {"as_of": "t", "adapter_id": "probe/v1"}
    stripped = [_replace(t, observation={}) for t in _p1_real_tuples() if t.observation]
    assert len(stripped) == 4  # 3 v2 captures + 1 floor
    for t in stripped:
        assert outcome(ct.to_frames, t, **kw) == outcome(legacy_to_frames, t, **kw)


def test_p1a_grade_is_invariant_under_observation_for_all_fixtures():
    """(b) grade(t) == grade(replace(t, observation={})) for every fixture tuple."""
    with_obs = [t for t in _p1_real_tuples() if t.observation]
    with_obs += [tup(observation=OBS), tup(observation=OBS, protocol_id="P-1", reps=3,
                                           attestation_path="MEASUREMENT.md"),
                 tup(observation={"outcome": "refused_correctness"}, value=0,
                     source_class="verifier", decided_proposition="MUL_MAT failed on ROCm0")]
    assert len(with_obs) >= 7
    for t in with_obs:
        assert ct.grade(t) == ct.grade(_replace(t, observation={})), t.measurement_id


def test_p1a_observation_rides_on_the_evidence_frame_only():
    from frames import validate_frame

    plain = ct.to_frames(tup(), as_of="t", adapter_id="probe/v1")
    rich = ct.to_frames(tup(observation=OBS, unit="t/s"), as_of="t", adapter_id="probe/v1")
    assert rich[1] == plain[1]  # claim frame untouched
    evidence = rich[2]["assertion"]
    assert evidence["metric"] == "decode_tps" and evidence["unit"] == "t/s"
    assert evidence["value"] == "45.3"  # 12-significant-digit decimal string
    assert evidence["observation"]["effect_rel"] == "0.0205"
    assert evidence["observation"]["n_pairs"] == 5  # ints stay ints
    assert evidence["observation"]["decisive"] is False
    assert evidence["observation"]["mechanism"]["id"] == "akm-ds41-mmid-qact-block-partition"
    assert {k: v for k, v in evidence.items()
            if k not in {"metric", "value", "unit", "observation"}} == plain[2]["assertion"]
    # §6: a retrofit observation says so in the source frame's envelope, as intake does.
    assert rich[0]["provenance"]["retrofit"] is True and plain[0]["provenance"]["retrofit"] is False
    assert rich[0]["assertion"] == plain[0]["assertion"]
    for frame in rich:
        validate_frame(frame)


def test_p1a_non_retrofit_observation_keeps_the_source_frame_bytes():
    obs = {k: v for k, v in OBS.items() if k != "retrofit"}
    plain = ct.to_frames(tup(), as_of="t", adapter_id="p")
    assert ct.to_frames(tup(observation=obs), as_of="t", adapter_id="p")[0] == plain[0]


@pytest.mark.parametrize("value,encoded", [
    (0.0205, "0.0205"), (81.1165241567493, "81.1165241567"), (81.0, "81"), (1.5e-05, "1.5e-05"),
    (-0.08221, "-0.08221"), (22, 22), (True, True), ("x", "x"), (None, None)])
def test_p1a_frame_scalar_is_the_twelve_significant_digit_rule(value, encoded):
    assert ct.frame_scalar(value) == encoded
    if isinstance(encoded, str) and isinstance(value, float):
        assert float(encoded) == float(format(value, ".12g"))


def test_p1a_fold_ignores_the_observation():
    from fold import fold

    plain = ct.to_frames(tup(), as_of="t", adapter_id="p")
    rich = ct.to_frames(tup(observation=OBS), as_of="t", adapter_id="p")
    a, b = fold(plain, as_of="t"), fold(rich, as_of="t")
    assert a.beliefs["clm_m1"].as_dict() == b.beliefs["clm_m1"].as_dict()


def test_p1a_new_applicability_keys_are_accepted_and_inert():
    t = tup(applicability=SCOPE_P1)
    assert ct.grade(t) == ct.grade(tup())
    assert ct.to_frames(t, as_of="t", adapter_id="p")[0]["assertion"]["applicability"] == SCOPE_P1


@pytest.mark.parametrize("scope", [
    {"model_sha256": "A" * 64}, {"model_sha256": "abc"}, {"build_sha": "xyz"},
    {"build_sha": "abc12"}, {"np": 0}, {"np": True}, {"np": "1"}, {"scope_basis": "guessed"},
    {"epoch": " "}, {"recipe": 1}, {"symbol": ""}, {"shape": []}, {"stack_regime": None}])
def test_p1a_malformed_new_applicability_keys_are_refused(scope):
    with pytest.raises(ct.ProjectionError, match="applicability"):
        tup(applicability=scope)


@pytest.mark.parametrize("obs,match", [
    ([], "mapping"),
    ({"surprise": 1}, "unknown fields"),
    ({"anchor_value": float("nan")}, "finite"),
    ({"effect_rel": float("inf")}, "finite"),
    ({"noise_floor_rel": "0.03"}, "finite"),
    ({"anchor_value": True}, "finite"),
    ({"decisive": "yes"}, "boolean"),
    ({"retrofit": 1}, "boolean"),
    ({"n_pairs": 0}, "positive integer"),
    ({"n_pairs": 2.0}, "positive integer"),
    ({"outcome": "kept"}, "outcome must be one of"),
    ({"outcome_native": ""}, "outcome_native"),
    ({"outcome_reason": "x" * 301}, "outcome_reason"),
    ({"mechanism": "akm-x"}, "mechanism"),
    ({"mechanism": {"statement": "s"}}, "mechanism"),
    ({"mechanism": {"id": "a", "extra": "b"}}, "mechanism"),
    ({"mechanism": {"id": "a", "statement": "s" * 241}}, "mechanism.statement"),
    ({"mechanism": {"id": ""}}, "mechanism.id"),
    ({"serving_claim_id": "legacy-serving:abc"}, "serving_claim_id"),
    ({"serving_claim_id": "legacy-serving-v2:" + "A" * 64}, "serving_claim_id"),
])
def test_p1a_observation_validation_refuses(obs, match):
    with pytest.raises(ct.ProjectionError, match=match):
        tup(observation=obs)


@pytest.mark.parametrize("value", [None, "45.3", float("nan"), True, [1]])
def test_p1a_an_observation_requires_a_finite_numeric_value(value):
    with pytest.raises(ct.ProjectionError, match="finite numeric `value`"):
        tup(observation={"outcome": "null"}, value=value)


def test_p1a_serving_claim_id_link_is_accepted_in_both_forms():
    for ident in ("legacy-serving-v2:" + "a" * 64, "clm_legacy-serving-v2:" + "b" * 64):
        assert tup(observation={"serving_claim_id": ident}).observation["serving_claim_id"] == ident


def test_p1a_empty_observation_keeps_the_legacy_dependency_graph():
    """observation={} must not import canonical (the packaged-constructor test's property)."""
    import subprocess
    code = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
from scripts.vidya.claim_tuple import ClaimTuple
ClaimTuple(measurement_id='m', metric='m', value=1, date='d', category='CANDIDATE', claim='c',
           observation={{}})
assert 'canonical' not in sys.modules and 'scripts.vidya.canonical' not in sys.modules
"""
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
