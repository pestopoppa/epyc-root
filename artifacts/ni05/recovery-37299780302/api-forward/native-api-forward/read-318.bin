"""EV-CONF-2: per-token logprob capture, candidate confidence sources, offline AUROC/ECE tool.

Every fixture is synthetic, and nothing here touches a model server.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (
    REPO_ROOT,
    REPO_ROOT / "scripts" / "autopilot",
    REPO_ROOT / "scripts" / "benchmark",
    REPO_ROOT / "scripts" / "analysis",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import confidence_source_compare as csc  # noqa: E402
import eval_tower  # noqa: E402
import token_confidence as tc  # noqa: E402
from src.llm_primitives.stat_tests import expected_calibration_error  # noqa: E402


# ── fixtures ──────────────────────────────────────────────────────────────


def _oai_row(tok: str, lp: float, alts: list[float] | None = None) -> dict:
    """OpenAI-shape row. ``alts`` are extra alternative logprobs (top-k beyond the sampled token)."""
    top = [{"token": tok, "logprob": lp}] + [
        {"token": f"alt{i}", "logprob": a} for i, a in enumerate(alts or [])
    ]
    return {"token": tok, "logprob": lp, "bytes": list(tok.encode()), "top_logprobs": top}


def _spec_placeholder(tok: str) -> dict:
    """What llama.cpp emits for a draft-accepted token: prob 1.0, no top-k."""
    return {"token": tok, "logprob": 0.0, "bytes": list(tok.encode()), "top_logprobs": []}


def _legacy_row(tok: str, p: float) -> dict:
    return {"content": tok, "probs": [{"tok_str": tok, "prob": p}, {"tok_str": "z", "prob": 0.01}]}


def _stream(pre: list[tuple[str, float]], answer: list[tuple[str, float]]) -> list[dict]:
    rows = [_oai_row(t, lp, [lp - 2.0]) for t, lp in pre]
    rows.append(_oai_row("<answer>", -0.001, [-8.0]))
    rows += [_oai_row(t, lp, [lp - 1.0]) for t, lp in answer]
    rows.append(_oai_row("</answer>", -0.001, [-8.0]))
    return rows


# ── encoding ──────────────────────────────────────────────────────────────


def test_encode_roundtrip_clamps_and_sentinel() -> None:
    vals = [0.0, 0.0004, 1.2345, 70.0, None]
    dec = tc.decode_nonneg(tc.encode_nonneg(vals))
    assert dec[0] == 0.0
    assert dec[1] == 0.0  # sub-millinat rounds to zero
    assert dec[2] == pytest.approx(1.2345, abs=1e-3)
    assert dec[3] == pytest.approx(65.534)  # clamped below the sentinel
    assert dec[4] is None


def test_record_is_bounded_two_bytes_per_token() -> None:
    rows = [_oai_row("x", -0.1 * (i % 7), [-3.0]) for i in range(20000)]
    rec = tc.build_token_trace_record(rows, max_tokens=1000)
    assert rec is not None and rec["truncated"] is True
    assert rec["kept"] == [[0, 250], [19250, 20000]]
    assert len(__import__("base64").b64decode(rec["lp"])) == 2 * 1000
    # summaries are over the FULL stream, not the kept window
    assert rec["n_tokens"] == 20000
    assert rec["real_mean_logprob"] == pytest.approx(sum(-0.1 * (i % 7) for i in range(20000)) / 20000)
    assert len(json.dumps(rec)) < 8000


# ── parity with the legacy aggregate ──────────────────────────────────────


@pytest.mark.parametrize("shape", ["oai", "legacy"])
def test_full_geomean_matches_eval_tower_aggregate(shape: str) -> None:
    rng = random.Random(7)
    if shape == "oai":
        rows = [_oai_row(f"t{i}", -rng.random() * 2, [-5.0]) for i in range(50)]
    else:
        rows = [_legacy_row(f"t{i}", 0.2 + 0.8 * rng.random()) for i in range(50)]
    legacy = eval_tower._completion_probabilities_confidence(rows)
    trace = tc.decode_token_trace(tc.build_token_trace_record(rows))
    assert trace is not None
    assert tc.full_geomean(trace) == pytest.approx(legacy, rel=1e-12)


# ── speculative-decoding placeholders ─────────────────────────────────────


def test_spec_placeholders_excluded_from_real_sources_but_kept_for_parity() -> None:
    rows = [_oai_row("a", -1.0, [-2.0])] + [_spec_placeholder("b")] * 9
    rec = tc.build_token_trace_record(rows)
    assert rec["n_placeholder"] == 9
    assert rec["placeholder_detection"] == "topk_absent_and_logprob_zero"
    tr = tc.decode_token_trace(rec)
    assert tr.placeholder_fraction == pytest.approx(0.9)
    # legacy geomean is inflated toward 1 by the placeholders ...
    assert tc.full_geomean(tr) == pytest.approx(math.exp(-0.1))
    assert tc.full_geomean(tr) == pytest.approx(eval_tower._completion_probabilities_confidence(rows))
    # ... the real-token sources are not
    assert tc.real_token_geomean(tr) == pytest.approx(math.exp(-1.0))
    assert tc.salient_min_prob(tr) == pytest.approx(math.exp(-1.0))


def test_placeholder_detection_unavailable_without_topk() -> None:
    rows = [{"token": "a", "logprob": 0.0}, {"token": "b", "logprob": -0.5}]
    rec = tc.build_token_trace_record(rows)
    assert rec["placeholder_detection"] == "unavailable"
    assert rec["n_placeholder"] == 0
    assert "ent" not in rec  # entropy needs top-k >= 2
    tr = tc.decode_token_trace(rec)
    assert tc.high_entropy_confidence(tr) is None
    assert tc.neg_mean_entropy_confidence(tr) is None
    assert tc.real_token_geomean(tr) == pytest.approx(math.exp(-0.25))


# ── entropy ───────────────────────────────────────────────────────────────


def test_topk_entropy_lower_bound_with_residual() -> None:
    assert tc.topk_entropy([0.5, 0.5]) == pytest.approx(math.log(2))
    h = tc.topk_entropy([0.5, 0.25])  # residual 0.25 lumped
    assert h == pytest.approx(-(0.5 * math.log(0.5) + 0.25 * math.log(0.25) * 2))
    assert tc.topk_entropy([0.9]) is None


# ── answer span (SCORE-03 / SCORE-16 reuse) ───────────────────────────────


@pytest.mark.parametrize(
    "text,expected,source",
    [
        ("work 3\n<answer> 42 </answer>", "42", "extract_pattern"),
        ("so\n#### 17", "17", "hash_marker"),
        ("x \\boxed{1} then \\boxed{\\frac{1}{2}}", "\\frac{1}{2}", "boxed"),
        ("Step: 5\nThe final answer is 7\nThanks", "The final answer is 7", "final_answer_region"),
        # direct-stage `</answer>` stop: the token stream ends inside the tag
        ("180 x 3 = 540\n\n<answer> 540 \n", "540", "unterminated_answer_tag"),
    ],
)
def test_locate_answer_span(text: str, expected: str, source: str) -> None:
    s, e, src = tc.locate_answer_span(text)
    assert text[s:e] == expected
    assert src == source


def test_answer_span_token_indices_with_multibyte_tokens() -> None:
    # "é" split across two byte-level tokens; span must still map by bytes
    rows = [
        {"token": "caf", "logprob": -0.1, "bytes": list(b"caf"), "top_logprobs": [{"logprob": -0.1}, {"logprob": -3}]},
        {"token": "", "logprob": -0.2, "bytes": [0xC3], "top_logprobs": [{"logprob": -0.2}, {"logprob": -3}]},
        {"token": "", "logprob": -0.3, "bytes": [0xA9], "top_logprobs": [{"logprob": -0.3}, {"logprob": -3}]},
        {"token": " <answer>", "logprob": -0.4, "bytes": list(b" <answer>"), "top_logprobs": [{"logprob": -0.4}, {"logprob": -3}]},
        {"token": "9", "logprob": -2.0, "bytes": list(b"9"), "top_logprobs": [{"logprob": -2.0}, {"logprob": -3}]},
        {"token": "</answer>", "logprob": -0.5, "bytes": list(b"</answer>"), "top_logprobs": [{"logprob": -0.5}, {"logprob": -3}]},
    ]
    rec = tc.build_token_trace_record(rows, answer="café <answer>9</answer>")
    assert rec["answer_span"] == {"start": 4, "end": 5, "source": "extract_pattern"}
    assert rec["answer_text_match"] == "exact"
    tr = tc.decode_token_trace(rec)
    assert tc.answer_span_geomean(tr) == pytest.approx(math.exp(-2.0))


def test_custom_extract_pattern_and_answer_mismatch_provenance() -> None:
    rows = [_oai_row("ANS[", -0.1, [-3]), _oai_row("5", -0.7, [-3]), _oai_row("]", -0.1, [-3])]
    rec = tc.build_token_trace_record(rows, answer="different text", extract_pattern=r"ANS\[(.*?)\]")
    assert rec["answer_span"]["start"] == 1 and rec["answer_span"]["end"] == 2
    assert rec["answer_text_match"] == "mismatch"


def test_span_in_truncated_gap_refuses() -> None:
    rows = [_oai_row("<answer>", -0.1, [-3]), _oai_row("1", -0.1, [-3]), _oai_row("</answer>", -0.1, [-3])]
    rows += [_oai_row(" pad", -0.2, [-3]) for _ in range(100)]
    rec = tc.build_token_trace_record(rows, max_tokens=40)  # head keeps 0..10, tail 73..103
    assert rec["answer_span"] == {"start": 1, "end": 2, "source": "extract_pattern"}
    assert tc.answer_span_geomean(tc.decode_token_trace(rec)) == pytest.approx(math.exp(-0.1))
    rows2 = [_oai_row(" pad", -0.2, [-3]) for _ in range(50)] + rows[:3] + rows[3:]
    rec2 = tc.build_token_trace_record(rows2, max_tokens=40)
    assert rec2["answer_span"]["start"] == 51
    assert tc.answer_span_geomean(tc.decode_token_trace(rec2)) is None


def test_legacy_and_empty_inputs() -> None:
    assert tc.build_token_trace_record(None) is None
    assert tc.build_token_trace_record([]) is None
    assert tc.decode_token_trace(None) is None
    assert tc.decode_token_trace({"schema": "something-else"}) is None
    with pytest.raises(ValueError):
        tc.decode_token_trace({"schema": tc.TOKEN_TRACE_SCHEMA, "encoding": "zzz"})


# ── eval_tower wiring ─────────────────────────────────────────────────────


def _writer(tmp_path: Path):
    return eval_tower._EvalQuestionJsonlWriter(
        root=tmp_path, root_source="test", eval_batch_id="b", trial_id=None,
        label="evconf2", requested_n=2, concurrency=1,
    )


def test_sidecar_persists_token_logprobs_only_when_present(tmp_path: Path) -> None:
    rec = tc.build_token_trace_record(_stream([("x", -0.3)], [("4", -0.2)]), answer="")
    w = _writer(tmp_path)
    try:
        w.append_result(ordinal=1, result=eval_tower.QuestionResult(
            question_id="a", suite="math", prompt="p", expected="4", correct=True,
            confidence=0.9, confidence_source="completion_probabilities_geomean",
            token_logprobs=rec,
        ))
        w.append_result(ordinal=2, result=eval_tower.QuestionResult(
            question_id="b", suite="math", prompt="p", expected="4",
        ))
    finally:
        w.close()
    rows = [json.loads(x) for x in w.path.read_text().splitlines()]
    assert rows[0]["token_logprobs"] == rec
    assert "token_logprobs" not in rows[1]
    # the compact (journal-bound) result never carries the vector
    assert "token_logprobs" not in rows[0]["result"]


def test_capture_helper_env_off_and_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = _stream([], [("4", -0.2)])
    assert eval_tower._token_logprob_trace(rows, answer="", scoring_config={}) is not None
    monkeypatch.setenv("AUTOPILOT_EVAL_TOKEN_LOGPROBS", "0")
    assert eval_tower._token_logprob_trace(rows, answer="", scoring_config={}) is None
    monkeypatch.delenv("AUTOPILOT_EVAL_TOKEN_LOGPROBS")

    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(tc, "build_token_trace_record", boom)
    assert eval_tower._token_logprob_trace(rows, answer="", scoring_config={}) is None
    assert eval_tower._token_logprob_trace([], answer="", scoring_config={}) is None


def test_capture_helper_honours_max_tokens_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOPILOT_EVAL_TOKEN_LOGPROBS_MAX_TOKENS", "16")
    rows = [_oai_row("x", -0.1, [-3]) for _ in range(100)]
    rec = eval_tower._token_logprob_trace(rows, answer="", scoring_config={})
    assert rec["truncated"] is True and rec["kept"] == [[0, 4], [88, 100]]


# ── offline comparison tool ───────────────────────────────────────────────


def _synthetic_sidecar(path: Path, n: int = 240, seed: int = 3, legacy_only: bool = False) -> None:
    """Length-confounded fixture: the answer-token confidence carries the signal,
    while the whole-trace geomean is dominated by derivation length."""
    rng = random.Random(seed)
    lines = [json.dumps({"row_type": "batch_start"})]
    for i in range(n):
        correct = rng.random() < 0.7
        # correct: hard derivation (many moderately uncertain steps), confident answer;
        # wrong: glib derivation (near-certain filler), weak answer token diluted by it.
        length = rng.randint(20, 200) if correct else rng.randint(40, 80)
        step_nll = 0.3 if correct else 0.005
        pre = [(" w", -rng.uniform(0.0, step_nll)) for _ in range(length)]
        ans_lp = -rng.uniform(0.0, 0.25) if correct else -rng.uniform(0.5, 3.0)
        rows = _stream(pre, [("7", ans_lp)])
        conf = eval_tower._completion_probabilities_confidence(rows)
        row = {
            "row_type": "question_result",
            "ordinal": i,
            "result": {
                "correct": correct,
                "confidence": round(conf, 6),
                "confidence_source": "completion_probabilities_geomean",
                "tokens_generated": len(rows),
            },
        }
        if not legacy_only:
            row["token_logprobs"] = tc.build_token_trace_record(rows, answer="")
        lines.append(json.dumps(row))
    lines.append(json.dumps({"row_type": "question_result", "ordinal": n,
                             "result": {"correct": False, "error": True}}))
    lines.append(json.dumps({"row_type": "question_result", "ordinal": n + 1,
                             "result": {"correct": False, "disposition": "infra_failed"}}))
    path.write_text("\n".join(lines) + "\n")


def test_tool_on_legacy_sidecar_reports_baseline_only(tmp_path: Path) -> None:
    p = tmp_path / "legacy.jsonl"
    _synthetic_sidecar(p, legacy_only=True)
    rows, stats = csc.load_rows([p])
    assert stats["excluded_unscored"] == 2 and len(rows) == 240
    rep = csc.compare(rows, bootstrap=50)
    assert rep["sources"]["legacy_confidence"]["n"] == 240
    assert rep["sources"]["answer_span_geomean"]["n"] == 0
    assert rep["token_trace"]["rows_with_trace"] == 0
    xs = [r["result"]["confidence"] for r in rows]
    ys = [float(r["result"]["correct"]) for r in rows]
    assert rep["sources"]["legacy_confidence"]["ece"] == round(expected_calibration_error(xs, ys), 4)
    assert rep["sources"]["neg_length"]["ece"] is None


def test_tool_separates_answer_span_from_length_confounded_geomean(tmp_path: Path) -> None:
    p = tmp_path / "sidecar.jsonl"
    _synthetic_sidecar(p)
    out = tmp_path / "report.json"
    assert csc.main([str(p), "--out", str(out), "--bootstrap", "100", "--reweight-prevalence", "0.5"]) == 0
    rep = json.loads(out.read_text())
    src = rep["sources"]
    assert src["legacy_confidence"]["auroc"] < 0.5  # the E7c pathology, reproduced
    assert src["answer_span_geomean"]["auroc"] > 0.85
    delta = src["answer_span_geomean"]["paired_vs_baseline"]
    assert delta["delta_auroc"] > 0.3 and delta["delta_auroc_ci95"][0] > 0
    assert src["full_geomean"]["auroc"] == pytest.approx(src["legacy_confidence"]["auroc"], abs=0.02)
    assert "ece_reweighted" in src["answer_span_geomean"]
    assert rep["claim_grade"] == "observation"
    assert rep["token_trace"]["rows_with_trace"] == 240
    assert len(rep["inputs"]["files"][0]["sha256"]) == 64


def test_weighted_ece_uniform_equals_stat_tests() -> None:
    rng = random.Random(1)
    xs = [rng.random() for _ in range(300)] + [1.0, 0.0]
    ys = [float(rng.random() < x) for x in xs]
    assert csc.weighted_ece(xs, ys, [1.0] * len(xs)) == pytest.approx(expected_calibration_error(xs, ys))


def test_unterminated_answer_tag_span_excludes_tag_tokens() -> None:
    # The production direct stage stops on `</answer>`, so the stream has no closing tag.
    rows = [
        _oai_row("work", -0.3, [-2.0]),
        _oai_row("\n<answer>", -0.001, [-8.0]),
        _oai_row("54", -1.5, [-2.0]),
        _oai_row("0", -0.7, [-2.0]),
    ]
    rec = tc.build_token_trace_record(rows, answer="work\n<answer>540</answer>")
    assert rec["answer_span"] == {"start": 2, "end": 4, "source": "unterminated_answer_tag"}
    tr = tc.decode_token_trace(rec)
    assert tc.answer_span_min_prob(tr) == pytest.approx(math.exp(-1.5))


def test_unterminated_rule_ignores_custom_extract_pattern() -> None:
    assert tc.locate_answer_span("x <answer>5", r"ANS:(.*)$") is None or (
        tc.locate_answer_span("x <answer>5", r"ANS:(.*)$")[2] != "unterminated_answer_tag"
    )
