"""KB-RAG H2 — query-length instrumentation must measure the QUERY, not the cap.

Zero-inference: no ONNX session is created. Token counts come from the
`tokenizers` library only, on a synthetic vocabulary or on the checkpoint's
tokenizer.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.retrieval import colbert_encoder, kb_rag, kb_rag_query_telemetry as tel
from tests.unit.test_retrieval_prefix_convention import _build, _query, _tiny_corpus

_REAL_TOKENIZER = colbert_encoder.DEFAULT_MODEL_DIR / "tokenizer.json"


def _synthetic_tokenizer():
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from tokenizers.processors import TemplateProcessing

    words = [f"w{i}" for i in range(100)]
    vocab = {"[UNK]": 0, "[CLS]": 1, "[SEP]": 2, "[PAD]": 3, **{w: i + 4 for i, w in enumerate(words)}}
    tok = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
    tok.pre_tokenizer = Whitespace()
    tok.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 1), ("[SEP]", 2)]
    )
    return tok


@pytest.fixture()
def shared_tokenizer(monkeypatch):
    tok = _synthetic_tokenizer()
    monkeypatch.setattr(colbert_encoder, "_tokenizer", tok)
    monkeypatch.setattr(colbert_encoder, "_count_tokenizer", None)
    monkeypatch.setattr(colbert_encoder, "_do_lower_case", False)
    return tok


# ─── the non-vacuity guard ───────────────────────────────────────────────────

def test_count_is_untruncated_while_the_shared_tokenizer_stays_capped(shared_tokenizer) -> None:
    # exactly what encode() does before every call
    shared_tokenizer.enable_truncation(max_length=8)
    shared_tokenizer.enable_padding(length=8, pad_id=3, pad_token="[PAD]")
    text = " ".join(f"w{i}" for i in range(30))

    capped = len(shared_tokenizer.encode(text).ids)
    counted = colbert_encoder.count_tokens(text, role=colbert_encoder.ROLE_NONE)

    assert capped == 8, "sanity: the encode-path count is the cap, which is why H2 needs a copy"
    assert counted == 32  # 30 words + [CLS] + [SEP]
    # the shared instance is untouched, so a concurrent encode() is still truncated
    assert shared_tokenizer.truncation is not None
    assert len(shared_tokenizer.encode(text).ids) == 8


def test_count_tokens_short_text_is_not_padded(shared_tokenizer) -> None:
    shared_tokenizer.enable_padding(length=48, pad_id=3, pad_token="[PAD]")
    assert colbert_encoder.count_tokens("w1 w2", role=colbert_encoder.ROLE_NONE) == 4


def test_count_tokens_without_a_loaded_tokenizer_is_none(monkeypatch) -> None:
    monkeypatch.setattr(colbert_encoder, "_tokenizer", None)
    monkeypatch.setattr(colbert_encoder, "_count_tokenizer", None)
    assert colbert_encoder.count_tokens("anything", role=colbert_encoder.ROLE_NONE) is None


def test_count_tokens_rejects_unknown_role(shared_tokenizer) -> None:
    with pytest.raises(ValueError):
        colbert_encoder.count_tokens("w1", role="bogus")


@pytest.mark.skipif(not _REAL_TOKENIZER.exists(), reason="checkpoint tokenizer not on disk")
def test_real_tokenizer_counts_the_query_prefix(monkeypatch) -> None:
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(_REAL_TOKENIZER))
    tok.enable_truncation(max_length=48)
    monkeypatch.setattr(colbert_encoder, "_tokenizer", tok)
    monkeypatch.setattr(colbert_encoder, "_count_tokenizer", None)
    monkeypatch.setattr(colbert_encoder, "_query_prefix", "[Q] ")
    monkeypatch.setattr(colbert_encoder, "_do_lower_case", False)
    text = "why does the kb rag query cap truncate long agent questions " * 8

    none = colbert_encoder.count_tokens(text, role=colbert_encoder.ROLE_NONE)
    query = colbert_encoder.count_tokens(text, role=colbert_encoder.ROLE_QUERY)

    assert none is not None and none > 48
    assert query == none + 1, "the [Q] prefix is one trained token"


# ─── the call site ───────────────────────────────────────────────────────────

def test_query_appends_one_untruncated_record(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "qlen.jsonl"
    monkeypatch.setenv(tel.LOG_ENV, str(log))
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)

    with patch.object(kb_rag.colbert_encoder, "count_tokens", return_value=61) as counted:
        rows, seen = _query(index_dir, text="a long question about cats")

    assert rows and seen == [colbert_encoder.ROLE_QUERY]
    counted.assert_called_once_with("a long question about cats", role=colbert_encoder.ROLE_QUERY)
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(records) == 1
    rec = records[0]
    assert rec["schema"] == tel.SCHEMA
    assert rec["query_tokens"] == 61 and rec["cap"] == kb_rag._QUERY_MAX_TOKENS == 48
    assert rec["over_cap"] is True
    assert rec["prefix_convention"] == colbert_encoder.PREFIX_CONVENTION
    assert rec["query_chars"] == len("a long question about cats")
    assert "cats" not in json.dumps(rec), "the query text itself is never logged"


def test_disabled_instrument_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(tel.LOG_ENV, "off")
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)
    with patch.object(kb_rag.colbert_encoder, "count_tokens", return_value=10) as counted:
        rows, _ = _query(index_dir)
    assert rows
    counted.assert_not_called()


def test_instrument_failure_never_fails_the_query(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(tel.LOG_ENV, str(tmp_path / "qlen.jsonl"))
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)
    with patch.object(kb_rag.colbert_encoder, "count_tokens", side_effect=RuntimeError("boom")):
        rows, _ = _query(index_dir)
    assert rows
    assert not (tmp_path / "qlen.jsonl").exists()


def test_no_count_records_nothing(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "qlen.jsonl"
    monkeypatch.setenv(tel.LOG_ENV, str(log))
    with patch.object(colbert_encoder, "count_tokens", return_value=None):
        assert tel.record_query_length("q", cap=48, role="query",
                                       prefix_convention="qd-v1", index_dir="x") is None
    assert not log.exists()


# ─── the reader / reporter ───────────────────────────────────────────────────

def _rec(tokens: int, cap: int = 48, ts: str = "2026-09-16T10:00:00Z", enc: str = "/m/gte") -> dict:
    r = tel.build_record("q", query_tokens=tokens, cap=cap, role="query",
                         prefix_convention="qd-v1", encoder_model_dir=enc,
                         encoder_slot="gte_moderncolbert", index_dir="/i", ts=ts)
    return r


def _write_log(path: Path, records: list[dict], tail: str = "") -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in records) + tail)


def test_summary_percentiles_and_over_cap_rate(tmp_path: Path) -> None:
    log = tmp_path / "q.jsonl"
    values = [5, 7, 9, 10, 12, 20, 30, 49, 60, 100]
    _write_log(log, [_rec(v, ts=f"2026-09-16T10:00:{i:02d}Z") for i, v in enumerate(values)])

    report = tel.build_report(log)

    assert report["observations"] == 10
    (g,) = report["groups"]
    assert (g["n"], g["p50"], g["p95"], g["max"]) == (10, 12, 100, 100)
    assert g["over_cap_count"] == 3 and g["over_cap_rate"] == pytest.approx(0.3)
    assert g["first_ts"] == "2026-09-16T10:00:00Z" and g["last_ts"] == "2026-09-16T10:00:09Z"


def test_exactly_at_cap_is_not_over_cap(tmp_path: Path) -> None:
    log = tmp_path / "q.jsonl"
    _write_log(log, [_rec(48), _rec(49)])
    (g,) = tel.build_report(log)["groups"]
    assert g["over_cap_count"] == 1


def test_empty_log_reports_no_observations_not_zero_percent(tmp_path: Path, capsys) -> None:
    from scripts.kb_rag import query_length_report as cli

    log = tmp_path / "q.jsonl"
    log.write_text("")
    report = tel.build_report(log)
    assert report["observations"] == 0
    assert report["groups"] == [] and report["belief_measurements"] == []

    assert cli.main(["--log", str(log)]) == 0
    out = capsys.readouterr().out
    assert "UNKNOWN, not 0 %" in out
    assert cli.main(["--log", str(tmp_path / "missing.jsonl")]) == 2


def test_groups_split_by_encoder_and_cap_and_since_filters(tmp_path: Path) -> None:
    log = tmp_path / "q.jsonl"
    _write_log(log, [
        _rec(10, ts="2026-09-15T00:00:00Z"),
        _rec(50, ts="2026-09-16T00:00:00Z"),
        _rec(40, cap=32, enc="/m/lateon", ts="2026-09-16T00:00:01Z"),
    ])
    report = tel.build_report(log, since="2026-09-16T00:00:00Z")
    assert [(g["encoder_model_dir"], g["cap"], g["n"]) for g in report["groups"]] == [
        ("/m/gte", 48, 1), ("/m/lateon", 32, 1)
    ]
    assert all(g["over_cap_count"] == 1 for g in report["groups"])


def test_partial_tail_malformed_and_foreign_lines(tmp_path: Path) -> None:
    log = tmp_path / "q.jsonl"
    _write_log(log, [_rec(10), {"schema": "other"}], tail='not json\n{"schema": "epyc.kb_rag.qu')
    records, snap = tel.read_log(log)
    assert len(records) == 1
    assert snap["malformed_lines"] == 1 and snap["foreign_lines"] == 1
    # the half-written tail is outside the snapshot, so its digest stays re-derivable
    whole = log.read_bytes()
    assert snap["bytes"] == whole.rfind(b"\n") + 1


def test_belief_rows_are_observations_with_recorded_direction(tmp_path: Path) -> None:
    log = tmp_path / "q.jsonl"
    _write_log(log, [_rec(10), _rec(60)])
    report = tel.build_report(log)
    rows = report["belief_measurements"]

    assert [r["metric"] for r in rows] == [
        "kb_rag.query_over_cap_rate", "kb_rag.query_tokens_p50",
        "kb_rag.query_tokens_p95", "kb_rag.query_tokens_max",
    ]
    assert len({r["measurement_id"] for r in rows}) == 4
    for r in rows:
        assert r["protocol_id"] == ""  # observation: no protocol is invented
        assert r["metric_direction"] == "lower_better"
        assert r["reps"] == 2 and r["reps_basis"].startswith("scored")
        assert r["category"] == "BASELINE"
        assert r["extra"]["log_prefix_sha256"] == report["log"]["sha256"]
        assert "attestation_sha256" not in r  # the live log grows; no whole-file digest claim
    assert rows[0]["value"] == pytest.approx(0.5)
    assert "1 of 2" in rows[0]["claim"]
    # identity is stable for the same snapshot
    assert [r["measurement_id"] for r in tel.build_report(log)["belief_measurements"]] == [
        r["measurement_id"] for r in rows
    ]
