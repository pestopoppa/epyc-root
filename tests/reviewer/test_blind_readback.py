"""RA-13 blind read-back — the properties that must survive, each with its mutation.

Every positive here is paired with a mutation that removes EXACTLY the signal under test, because a
harness whose whole job is refusal is the easiest kind of code to write vacuously: a whitelist that
accepts everything, a validator that returns early, a threshold that is never reached all pass a
naive positive test. So each pair reads: "this is accepted / and here is the single change that
makes it refused" — and where the check is an ABSENCE (no verdict field), the mutation plants the
thing that should be caught and asserts the detector fires.

The four claims under test map to the handoff rows:
  RA-13a  the brief is a positive whitelist, and its output is a description with no verdict slot
  RA-13b  no summary is citable below n>=20, and it always states its denominator
  RA-13c  a record missing judge model id, spec version, artifact hash, or context manifest is
          refused as evidence — and the manifest is checkable, so a skipped blinding is NOT
          byte-identical to a real one
"""

import dataclasses
import json
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "reviewer"))

import blind_readback as br  # noqa: E402


DIFF = "--- a/x.py\n+++ b/x.py\n@@\n-if n > 0:\n+if n >= 0:\n"

DESCRIPTION = {
    "summary": "Widens a guard from n > 0 to n >= 0.",
    "binders": ["n, bound in the enclosing scope; not defined by this artifact"],
    "preconditions": ["none stated"],
    "degenerate_cases": ["n == 0 now enters the branch where it previously did not"],
}


def make_brief(text=DIFF, kind="diff", revision="rev-1"):
    return br.build_brief(
        {"artifact": {"kind": kind, "text": text, "revision_id": revision}, "spec": br.ReadBackSpec()}
    )


def make_instrumentation(denominator=4, caught=1, false=1, agree=2):
    return br.RunInstrumentation(
        adjudicator="operator",
        denominator=denominator,
        caught_discrepancies=caught,
        false_discrepancies=false,
        agreements_with_author=agree,
    )


def make_record(brief=None, record_id="rb-0001", **kw):
    brief = brief or make_brief()
    return br.build_record(
        record_id=record_id,
        judge_model_id="glm-5.2-iq4xs",
        brief=brief,
        description=DESCRIPTION,
        instrumentation=kw.pop("instrumentation", make_instrumentation()),
        created_utc="2026-09-07T00:00:00+00:00",
        **kw,
    )


# --- RA-13a: the brief is a positive whitelist ----------------------------------------------


def test_brief_accepts_exactly_artifact_and_spec():
    """Positive: the whitelisted call shape works, so the refusals below are not blanket refusals."""
    brief = make_brief()
    assert brief.fields_supplied == ("artifact", "spec")
    assert brief.artifact.text == DIFF


def test_brief_refuses_the_task_statement():
    """Mutation: add the ask. The auditor must never see what the artifact was supposed to do."""
    with pytest.raises(br.BlindingViolation) as exc:
        br.build_brief(
            {
                "artifact": {"kind": "diff", "text": DIFF, "revision_id": "rev-1"},
                "spec": br.ReadBackSpec(),
                "task_statement": "make the guard accept zero",
            }
        )
    assert "task_statement" in str(exc.value)


def test_whitelist_refuses_a_field_name_no_blacklist_could_have_enumerated():
    """Catches a blacklist masquerading as a whitelist.

    A forbidden-field list would have to name `intent`, `task_statement`, `request`... and would
    miss this. A positive whitelist refuses it for the only auditable reason: it is not named.
    """
    with pytest.raises(br.BlindingViolation):
        br.build_brief(
            {
                "artifact": {"kind": "diff", "text": DIFF, "revision_id": "rev-1"},
                "spec": br.ReadBackSpec(),
                "what_the_author_was_going_for_here": "zero should be allowed",
            }
        )


def test_artifact_whitelist_refuses_intent_bearing_metadata():
    """Mutation at the inner boundary: intent smuggled as artifact metadata rather than a brief key."""
    with pytest.raises(br.BlindingViolation) as exc:
        br.Artifact.from_fields(
            {"kind": "diff", "text": DIFF, "revision_id": "rev-1", "author_rationale": "off-by-one"}
        )
    assert "author_rationale" in str(exc.value)


def test_artifact_whitelist_accepts_the_three_named_fields():
    """Positive pair for the artifact whitelist."""
    art = br.Artifact.from_fields({"kind": "diff", "text": DIFF, "revision_id": "rev-1"})
    assert art.sha256 == br.sha256_text(DIFF)


def test_brief_type_has_no_slot_for_anything_else():
    """Structural: two fields, so there is no attribute to smuggle intent through at all."""
    assert tuple(f.name for f in dataclasses.fields(br.AuditorBrief)) == ("artifact", "spec")


def test_rendered_brief_is_exactly_spec_plus_artifact():
    """Pins the rendered bytes: any third region interpolated into the brief fails here.

    The whitelist governs what a caller may PASS; this governs what the auditor actually SEES.
    Without it, `render` could grow a "context" line and every whitelist test would still pass.
    """
    brief = make_brief()
    expected = (
        f"{br.BRIEF_SPEC_HEADER}\n"
        f"{br.SPEC_TEXT}\n"
        f"{br.BRIEF_ARTIFACT_HEADER} (kind: diff)\n"
        f"{DIFF}\n"
        f"{br.BRIEF_ARTIFACT_END}\n"
    )
    assert brief.render() == expected


def test_rendered_brief_does_not_contain_text_never_passed():
    """Mutation of the above: the ask exists in the test's scope and must not reach the render."""
    ask = "make the guard accept zero"
    brief = make_brief()
    assert ask not in brief.render()


def test_spec_text_itself_is_blind():
    """The spec ships in the context too — a spec that mentions the task would break the blinding."""
    lowered = br.SPEC_TEXT.lower()
    for leak in ("the task", "the request", "the author's intent", "requirement"):
        assert leak not in lowered


# --- RA-13a: description, never a verdict (property i) ---------------------------------------


def test_record_field_set_is_pinned():
    """A verdict field cannot be added to the record without failing a test — this is that test."""
    assert tuple(f.name for f in dataclasses.fields(br.ReadBackRecord)) == br.RECORD_FIELDS


def test_no_record_or_description_name_carries_authority():
    """Positive: nothing in the record type or the description sections is a verdict slot."""
    names = list(br.RECORD_FIELDS) + list(br.DESCRIPTION_SECTION_WHITELIST)
    names += [f.name for f in dataclasses.fields(br.ContextManifest)]
    names += [f.name for f in dataclasses.fields(br.RunInstrumentation)]
    assert br.authority_bearing_names(names) == ()


def test_authority_scanner_fires_on_a_planted_verdict_field():
    """Mutation: proves the scan above is not vacuous — it does detect the names it must."""
    planted = ("record_id", "verdict", "overall_score", "approved_by", "artifact_sha256")
    assert br.authority_bearing_names(planted) == ("verdict", "overall_score", "approved_by")


def test_description_refuses_a_verdict_section():
    """Mutation: an over-helpful auditor appends a verdict. It is refused, not stored."""
    with pytest.raises(br.RecordValidationError) as exc:
        br.validate_description({**DESCRIPTION, "verdict": "approve"})
    assert "verdict" in str(exc.value)


def test_description_accepts_whitelisted_sections():
    """Positive pair: the legitimate description validates."""
    br.validate_description(DESCRIPTION)


def test_deserialised_record_refuses_a_verdict_key():
    """The path a verdict would actually arrive by: JSON from a model, not a Python constructor."""
    payload = make_record().as_dict()
    payload["verdict"] = "approve"
    with pytest.raises(br.RecordValidationError):
        br.record_from_dict(payload)


def test_deserialised_clean_record_round_trips():
    """Positive pair for the deserialiser, so the refusal above is not a broken parser."""
    payload = make_record().as_dict()
    assert br.record_from_dict(payload).record_id == "rb-0001"


# --- RA-13c: the record format ---------------------------------------------------------------


def test_complete_record_validates():
    """Positive: a fully-formed record is evidence."""
    br.validate_record(make_record())


@pytest.mark.parametrize("missing", br.RA13C_REQUIRED_FIELDS)
def test_record_missing_any_ra13c_field_is_refused(missing):
    """Mutation, one field at a time: judge model id, spec version, artifact hash, manifest."""
    payload = make_record().as_dict()
    payload.pop(missing)
    with pytest.raises(br.RecordValidationError) as exc:
        br.record_from_dict(payload)
    assert missing in str(exc.value)


def test_missing_field_raises_rather_than_warns():
    """The defect being closed: a warned-about record still gets counted. This one must not exist."""
    payload = make_record().as_dict()
    payload["judge_model_id"] = ""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(br.RecordValidationError):
            br.record_from_dict(payload)
    assert caught == []


def test_artifact_hash_changes_when_the_artifact_changes():
    """The hash is of the exact text SHOWN; a one-character edit is a different artifact."""
    a = make_brief(text=DIFF)
    b = make_brief(text=DIFF.replace("n >= 0", "n >= 1"))
    assert a.artifact.sha256 != b.artifact.sha256
    assert a.sha256 != b.sha256


def test_artifact_hash_is_stable_for_identical_text():
    """Mutation pair: the hash must not be salted or time-dependent, or nothing can be re-derived."""
    assert make_brief().artifact.sha256 == make_brief().artifact.sha256


def test_whitespace_edit_still_changes_the_hash():
    """Catches a normalising hash: 'same modulo whitespace' is not the same text shown."""
    assert make_brief(text=DIFF).artifact.sha256 != make_brief(text=DIFF + "\n").artifact.sha256


def test_manifest_admitting_an_extra_field_is_refused():
    """A record that ADMITS intent was in context is refused as evidence, not accepted with a note."""
    brief = make_brief()
    manifest = dataclasses.replace(
        brief.context_manifest(), fields_supplied=("artifact", "spec", "task_statement")
    )
    with pytest.raises(br.RecordValidationError) as exc:
        make_record(brief=brief, context_manifest=manifest)
    assert "blinding did not hold" in str(exc.value)


def test_manifest_with_exactly_the_whitelist_is_accepted():
    """Positive pair: the honest manifest passes."""
    make_brief().context_manifest().validate(artifact_revision="rev-1")


def test_stale_context_revision_is_refused():
    """Property (iii): a context opened for an earlier revision is a contaminated context."""
    brief = make_brief(revision="rev-2")
    manifest = dataclasses.replace(brief.context_manifest(), context_revision="rev-1")
    with pytest.raises(br.RecordValidationError) as exc:
        make_record(brief=brief, context_manifest=manifest)
    assert "stale" in str(exc.value)


def test_context_carrying_prior_revisions_is_refused():
    """Property (iii), the other half: progressive contamination across iterations."""
    brief = make_brief(revision="rev-2")
    manifest = dataclasses.replace(brief.context_manifest(), prior_revisions_in_context=("rev-1",))
    with pytest.raises(br.RecordValidationError):
        make_record(brief=brief, context_manifest=manifest)


def test_non_fresh_context_is_refused():
    """Property (iii), stated directly: the attestation cannot be false and still validate."""
    brief = make_brief()
    manifest = dataclasses.replace(brief.context_manifest(), fresh_context=False)
    with pytest.raises(br.RecordValidationError):
        make_record(brief=brief, context_manifest=manifest)


def test_a_skipped_blinding_is_not_byte_identical_to_a_real_one():
    """The exact defect RA-13c closes.

    The source stores only the model name, so a captain who pasted the whole task into the auditor's
    context produces a record indistinguishable from a blinded run. Here the manifest pins the hash
    of the rendered brief, so the contaminated context yields a different record — and one that
    cannot survive re-derivation against the blinded brief.
    """
    blinded = make_brief()
    contaminated_context = blinded.render() + "\n=== WHY ===\nmake the guard accept zero\n"
    contaminated_hash = br.sha256_text(contaminated_context)

    assert contaminated_hash != blinded.sha256

    record = make_record(brief=blinded)
    faked = dataclasses.replace(record.context_manifest, brief_sha256=contaminated_hash)
    forged = dataclasses.replace(record, context_manifest=faked)
    with pytest.raises(br.RecordValidationError) as exc:
        br.verify_brief_binding(forged, blinded)
    assert "brief hash mismatch" in str(exc.value)


def test_brief_binding_verifies_for_the_real_brief():
    """Positive pair: re-derivation from the brief actually shown succeeds."""
    brief = make_brief()
    br.verify_brief_binding(make_record(brief=brief), brief)


def test_brief_binding_detects_a_swapped_artifact():
    """A record re-pointed at a different artifact is refused even though every field is present."""
    record = make_record(brief=make_brief())
    other = make_brief(text=DIFF.replace("n >= 0", "n >= 2"))
    with pytest.raises(br.RecordValidationError) as exc:
        br.verify_brief_binding(record, other)
    assert "artifact hash mismatch" in str(exc.value)


# --- RA-13b: write-time instrumentation and the citability floor -----------------------------


def test_instrumentation_counts_partition_the_denominator():
    """Positive: caught + false + agreements == denominator, so no rate can be silently inflated."""
    make_instrumentation(denominator=4, caught=1, false=1, agree=2).validate()


def test_instrumentation_with_an_undercounted_denominator_is_refused():
    """Mutation: shrink the denominator by one and every rate would read high. Refused."""
    with pytest.raises(br.RecordValidationError) as exc:
        make_instrumentation(denominator=3, caught=1, false=1, agree=2).validate()
    assert "partition" in str(exc.value)


def test_instrumentation_requires_a_human_adjudicator():
    """Property (i) at write time: the description carries no authority, so a run with no human
    comparer produced no result to record."""
    inst = dataclasses.replace(make_instrumentation(), adjudicator="")
    with pytest.raises(br.RecordValidationError):
        inst.validate()


def test_zero_denominator_is_refused():
    """A rate with no denominator is not a measurement."""
    with pytest.raises(br.RecordValidationError):
        br.RunInstrumentation(
            adjudicator="operator",
            denominator=0,
            caught_discrepancies=0,
            false_discrepancies=0,
            agreements_with_author=0,
        ).validate()


def test_summary_refuses_below_the_floor():
    """RA-13b: 19 valid runs is not citable, and the refusal is an error, not a flagged number."""
    records = [make_record(record_id=f"rb-{i:04d}") for i in range(19)]
    with pytest.raises(br.NotCitableError) as exc:
        br.citable_summary(records)
    message = str(exc.value)
    assert "n=19" in message
    assert "n>=20" in message
    assert "denominator=76" in message


def test_summary_is_citable_at_the_floor():
    """Mutation pair: one more run and it emits — so the refusal is the threshold, not a stub."""
    records = [make_record(record_id=f"rb-{i:04d}") for i in range(20)]
    summary = br.citable_summary(records)
    assert summary.n_runs == 20
    assert summary.citable is True


def test_citable_summary_states_its_denominator():
    """No read-back result may be cited without a stated denominator, so it is not optional output."""
    records = [make_record(record_id=f"rb-{i:04d}") for i in range(20)]
    payload = br.citable_summary(records).as_dict()
    assert payload["denominator"] == 80
    assert "n=20" in payload["denominator_statement"]
    assert payload["agreement_rate"] == pytest.approx(40 / 80)
    assert payload["caught_rate"] == pytest.approx(20 / 80)


def test_summary_has_no_verdict_field():
    """The meter reports rates; whether the mechanism is good remains a human judgement."""
    assert br.authority_bearing_names([f.name for f in dataclasses.fields(br.CitableSummary)]) == ()


def test_an_invalid_record_does_not_count_toward_n():
    """Mutation of the floor test: 20 records, one not evidence, so n=19 and it refuses again.

    Catches the shortcut of counting rows instead of validating them — which is how an unmeasured
    control becomes a cited one.
    """
    records = [make_record(record_id=f"rb-{i:04d}") for i in range(20)]
    records[3] = dataclasses.replace(records[3], judge_model_id="")
    with pytest.raises(br.NotCitableError) as exc:
        br.citable_summary(records)
    assert "n=19" in str(exc.value)


def test_provisional_summary_is_marked_not_citable():
    """Progress is visible below the floor, but never as a citable number."""
    payload = br.provisional_summary([make_record(record_id=f"rb-{i:04d}") for i in range(5)])
    assert payload["citable"] is False
    assert payload["n_runs"] == 5
    assert payload["denominator"] == 20
    assert "RA-13b" in payload["reason"]


def test_provisional_summary_is_not_a_citable_summary_type():
    """Mutation pair: a consumer cannot mistake one for the other by duck-typing."""
    payload = br.provisional_summary([make_record()])
    assert not isinstance(payload, br.CitableSummary)


# --- persistence + CLI ------------------------------------------------------------------------


def test_written_record_reloads_and_validates(tmp_path):
    """Write-time persistence: RA-13b cannot be retrofitted, so the record lands per run."""
    path = br.write_record(make_record(), root=tmp_path)
    assert json.loads(path.read_text())["artifact_sha256"] == br.sha256_text(DIFF)
    assert [r.record_id for r in br.load_records(tmp_path)] == ["rb-0001"]


def test_invalid_record_on_disk_is_skipped_not_loaded(tmp_path):
    """Mutation pair: a record that is not evidence must not be silently repaired into the tally."""
    br.write_record(make_record(), root=tmp_path)
    bad = make_record(record_id="rb-0002").as_dict()
    bad.pop("context_manifest")
    (tmp_path / "rb-0002.json").write_text(json.dumps(bad))
    assert [r.record_id for r in br.load_records(tmp_path)] == ["rb-0001"]


def test_cli_summarize_refuses_below_the_floor(tmp_path, capsys):
    """Exit code 3 is the refusal, so a caller cannot pipe a below-floor number into a claim."""
    for i in range(3):
        br.write_record(make_record(record_id=f"rb-{i:04d}"), root=tmp_path)
    assert br.main(["summarize", "--records-dir", str(tmp_path)]) == 3
    out = capsys.readouterr()
    assert json.loads(out.out)["citable"] is False
    assert "REFUSED" in out.err


def test_cli_brief_emits_only_the_whitelisted_context(tmp_path, capsys):
    """The operator-facing path: what gets pasted into the auditor is the brief and nothing else."""
    artifact = tmp_path / "change.diff"
    artifact.write_text(DIFF)
    assert br.main(["brief", "--artifact-file", str(artifact), "--kind", "diff", "--revision", "r1"]) == 0
    assert capsys.readouterr().out == make_brief(revision="r1").render()
