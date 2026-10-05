from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "autopilot"))

import eval_tower  # noqa: E402


def test_oversized_eval_prompt_retrieves_relevant_segments_and_preserves_question() -> None:
    filler = ("ordinary unrelated material " * 180) + "\n"
    relevant = "The complete graph fixtures use K5, K10, and K20 but never K15.\n"
    prompt = "Context:\n" + filler * 20 + relevant + filler * 20
    prompt += "\nQuestion: Which complete graph was not used?\nA) K5\nB) K10\nC) K15\nD) K20"

    compact, provenance = eval_tower._compact_oversized_eval_prompt(prompt)

    assert provenance["applied"] is True
    assert provenance["original_chars"] == len(prompt)
    assert provenance["output_chars"] < len(prompt)
    assert relevant.strip() in compact
    assert compact.endswith("Question: Which complete graph was not used?\nA) K5\nB) K10\nC) K15\nD) K20")


def test_short_eval_prompt_is_unchanged() -> None:
    prompt = "Context:\nsmall\nQuestion: value?"
    compact, provenance = eval_tower._compact_oversized_eval_prompt(prompt)
    assert compact == prompt
    assert provenance == {
        "applied": False,
        "original_chars": len(prompt),
        "output_chars": len(prompt),
    }


def test_inband_placement_timeout_has_typed_provenance() -> None:
    provenance = eval_tower._inband_error_provenance(
        "[ERROR: placement timeout role=frontdoor reason=placement_topology_overlap_timeout holders=[] after 300.0s]",
        role="frontdoor",
    )
    assert provenance["class"] == "admission_timeout"
    assert provenance["code"] == "placement_topology_overlap_timeout"
    assert provenance["role"] == "frontdoor"


def test_inband_http_400_has_typed_provenance() -> None:
    provenance = eval_tower._inband_error_provenance(
        "[ERROR: Inference failed: llama-server HTTP 400]",
        role="ingest_long_context",
    )
    assert provenance["class"] == "backend_request_rejected"
    assert provenance["code"] == "llama_http_400"


def test_text_question_result_qid_retains_historical_identity() -> None:
    question = {"suite": "math", "prompt": "What is 2+2?"}

    assert eval_tower._question_result_qid(question) == eval_tower._stable_question_qid(
        "math", "What is 2+2?"
    )


def test_vision_question_result_qid_binds_image_content(tmp_path: Path) -> None:
    image_a = tmp_path / "a.png"
    image_b = tmp_path / "b.png"
    image_c = tmp_path / "c.png"
    image_a.write_bytes(b"same-image")
    image_b.write_bytes(b"same-image")
    image_c.write_bytes(b"different-image")
    base = {"suite": "vl", "prompt": "Read the formula."}

    qid_a = eval_tower._question_result_qid({**base, "image_path": str(image_a)})
    qid_b = eval_tower._question_result_qid({**base, "image_path": str(image_b)})
    qid_c = eval_tower._question_result_qid({**base, "image_path": str(image_c)})

    assert qid_a == qid_b
    assert qid_a != qid_c
