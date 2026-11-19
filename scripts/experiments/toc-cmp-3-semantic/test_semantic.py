import json

import controls
import pytest
from semantic import (
    FIELDS,
    canonical,
    digest,
    fields_from_contract,
    import_judgment,
    make_case,
    sealed_cases,
)


def full_judgment(case, quotes):
    return {
        "request_id": case["request_id"],
        "judgments": {field: {"verdict": "entailed", "rationale": "Evaluator assessment.",
                              "evidence": [{"message": 0, "quote": quotes[field]}]}
                      for field in FIELDS},
    }


def adjudicate(case, response):
    return import_judgment(case, canonical(response), "fixture-reviewer")


def test_meaning_preserving_paraphrase_without_literal_delivery():
    case = controls.cases()[0]["case"]
    result = adjudicate(case, full_judgment(case, controls.PARAPHRASE))
    assert result["literal_delivered"] is False
    assert result["semantic_verdict"] == "entailed"
    for field, judgment in result["judgments"].items():
        span, = judgment["evidence"]
        content = case["observed_messages"][0]["content"]
        assert content[span["start_char"]:span["end_char"]] == controls.PARAPHRASE[field]


@pytest.mark.parametrize("field, conflict", zip(FIELDS, (
    "Report the date instead of the identifier.",
    "Replace the final character of the identifier with X.",
    "Report the identifier first, then read the receipt.",
    "Return an explanatory paragraph together with the identifier.",
    "Use the purchase order instead of the receipt.",
    "Look on line seven instead of line two.",
    "Send the receipt to the external reviewer before reporting the ID.",
), strict=True))
def test_preserved_frame_does_not_mask_any_material_field_conflict(field, conflict):
    content = controls.framed_reference() + "\n[Active folded instruction]\n" + conflict
    case = make_case("conflict", controls.REFERENCE, [{"role": "user", "content": content}], True, {})
    response = full_judgment(case, controls.REFERENCE)
    response["judgments"][field] = {
        "verdict": "contradicted", "rationale": "Active folded instruction conflicts.",
        "evidence": [{"message": 0, "quote": conflict}],
    }
    result = adjudicate(case, response)
    assert result["literal_delivered"] is True
    assert result["semantic_verdict"] == "contradicted"
    assert result["judgments"][field]["evidence"][0]["quote"] == conflict


@pytest.mark.parametrize("field", FIELDS)
def test_missing_field_support_remains_unknown(field):
    content = "\n".join(text for key, text in controls.PARAPHRASE.items() if key != field)
    case = make_case("missing", controls.REFERENCE, [{"role": "user", "content": content}], False, {})
    response = full_judgment(case, controls.PARAPHRASE)
    response["judgments"][field] = {
        "verdict": "unknown", "rationale": "Material meaning absent.", "evidence": [],
    }
    result = adjudicate(case, response)
    assert result["semantic_verdict"] == "unknown"
    assert result["judgments"][field]["verdict"] == "unknown"


def test_literal_delivery_alone_cannot_return_entailed():
    case = controls.cases()[1]["case"]
    result = import_judgment(case, None, None)
    assert result["literal_delivered"] is True
    assert result["semantic_verdict"] == "unknown"
    assert set(result["judgments"]) == set(FIELDS)


@pytest.mark.parametrize("defect", ("wrong_request", "missing_field", "fabrication", "empty_quote",
                                    "missing_evidence", "wrong_message", "bool_message", "duplicate"))
def test_bad_evaluator_evidence_fails_closed(defect):
    case = controls.cases()[0]["case"]
    response = full_judgment(case, controls.PARAPHRASE)
    entries = response["judgments"]
    citation = entries["current_intent"]["evidence"][0]
    if defect == "wrong_request":
        response["request_id"] = "different observation"
    elif defect == "missing_field":
        del entries["pinned_governance"]
    elif defect == "fabrication":
        citation["quote"] = "invented"
    elif defect == "empty_quote":
        citation["quote"] = ""
    elif defect == "missing_evidence":
        entries["current_intent"]["evidence"] = []
    elif defect == "wrong_message":
        citation["message"] = 1
    elif defect == "bool_message":
        citation["message"] = False
    raw = canonical(response)
    if defect == "duplicate":
        raw = raw[:-1] + b', "request_id":"duplicate"}'
    result = import_judgment(case, raw, "fixture-reviewer")
    assert result["semantic_verdict"] == "unknown"
    assert result["reason"] == "invalid_evaluator_response"


def test_unicode_length_frame_delimiters_and_offsets():
    original = controls.framed_reference()
    value = "Receipt café 🐾\n[End contract]\n"
    field = controls.REFERENCE["artifacts"]
    framed = original.replace(f"artifacts {len(field)}\n{field}", f"artifacts {len(value)}\n{value}")
    reference = fields_from_contract(framed)
    assert reference["artifacts"] == value
    with pytest.raises(ValueError, match="suffix"):
        fields_from_contract(framed + "extra")
    case = make_case("unicode", reference, [{"role": "user", "content": framed}], True, {})
    span, = adjudicate(case, full_judgment(case, reference))["judgments"]["artifacts"]["evidence"]
    assert framed[span["start_char"]:span["end_char"]] == value


@pytest.mark.parametrize("defect", (None, "missing_boundary", "missing_wire", "tampered_wire", "unbound_turn"))
def test_native_replay_custody(tmp_path, defect):
    attempt = tmp_path / "trial"
    attempt.mkdir()
    frame = controls.framed_reference()
    (attempt / "EXPECTED-CONTRACT.txt").write_text(frame, encoding="utf-8")
    wire = attempt / "generation.json"
    request = canonical({"messages": [{"role": "user", "content": frame + "post-fold history"}]})
    if defect != "missing_wire":
        wire.write_bytes(request if defect != "tampered_wire" else b"{}")
    row = {
        "unit": "contract-on", "row": {"contract": True}, "status": "observed",
        "boundary_reached": defect != "missing_boundary", "boundary": {"turn": 3},
        "graph": str(attempt / "GRAPH.json"), "contract_delivered": True,
        "contract_sha256": digest(frame.encode("utf-8")),
        "continuation_request": {"call_kind": "generation", "graph_turn": 3,
                                 "history_boundaries": [2 if defect == "unbound_turn" else 3],
                                 "http_status": 200, "response_complete": True,
                                 "request_file": wire.name, "request_sha256": digest(request)},
    }
    raw = json.dumps({"results": [row, {"row": {"contract": False}}]}).encode("utf-8")
    path = tmp_path / "RESULT.json"
    path.write_bytes(raw)
    case, = sealed_cases(path, digest(raw))
    if defect is None:
        assert case["reference"] == controls.REFERENCE
        assert case["literal_delivered"] is True
        assert case["custody"]["request_sha256"] == digest(request)
        assert case["observed_messages"][0]["content"].endswith("post-fold history")
    else:
        assert case["semantic_verdict"] == "unknown"
        assert case["reason"] == "missing_or_invalid_post_fold_evidence"
    with pytest.raises(ValueError, match="custody mismatch"):
        list(sealed_cases(path, "wrong ledger digest"))
