"""Off-host synthetic and aggregate-contract checks for TD-30f report capture."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

REPORT = Path(__file__).parents[2] / "scripts/ci/td30f_public_markdown_report.py"
OUTPUT = Path(os.environ["TD30F_REPORT_OUTPUT"])
spec = importlib.util.spec_from_file_location("td30f_report", REPORT)
assert spec and spec.loader
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def test_original_aggregate_is_218_row_public_successor_and_non_gold() -> None:
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert data["schema"] == "td30f-public-markdown-replay-aggregate-v1"
    assert data["root_source_commit"] == report.ROOT_PIN
    assert data["app_source_commit"] == report.APP_PIN
    assert data["input_document_count"] == 218
    assert data["source_document_counts_by_provenance"] == {
        "active_handoff_markdown_provenance": 186,
        "wiki_markdown_provenance": 32,
    }
    assert data["input_manifest_sha256"] == report.MANIFEST_SHA256
    assert data["claims"]["false_positive_rate"] is None
    assert "not a live runtime environment" in data["claims"]["configuration_basis"]
    assert "excluded_n rows are outside" in data["claims"]["denominator_semantics"]
    assert "below six lines" in data["claims"]["stream_tail_line_exclusion"]
    assert data["claims"]["integration_replay"] == "unavailable_without_original_stream_chunk_boundaries"
    assert data["claims"]["outcome"] == "descriptive_detector_trigger_share_only"
    stream_line_exclusions = [r for r in data["strata"]
                              if r["detector"] == "streaming_three_line_block_guard"
                              and r["length_bin"] == "below_minimum_tail_lines"]
    assert len(stream_line_exclusions) == 2
    assert all(r["n"] == 0 and r["triggered_n"] is None and r["trigger_share"] is None
               for r in stream_line_exclusions)
    prohibited = {"row_id", "path", "source_sha256", "excerpt", "document_text"}
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                assert key not in prohibited
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
    list(walk(data))
    for detector in {row["detector"] for row in data["strata"]}:
        for provenance in {row["provenance_label"] for row in data["strata"]}:
            rows = [r for r in data["strata"] if r["detector"] == detector and r["provenance_label"] == provenance]
            assert len(rows) > 1
            assert sum(r["n"] + r.get("excluded_n", 0) for r in rows) == data["source_document_counts_by_provenance"][provenance]
            assert all(r["trigger_share"] is None or 0 <= r["trigger_share"] <= 1 for r in rows)


def test_word_trigram_guards_keep_strict_threshold_and_minimum_boundaries() -> None:
    quality, pipeline, _, _ = report.build_guards(Path(os.environ["TD30F_APP_ROOT"]))
    repeated9 = "a b c a b c a b c"
    # Equality is not a trigger because the pinned source uses a strict '<'.
    assert pipeline(repeated9, threshold=3 / 7) is False
    assert pipeline(repeated9, threshold=0.43) is True
    assert pipeline("a b c a b c a b c a") is True
    assert pipeline("a b c a b c a") is False  # below the 9-word guard minimum
    repeated20 = "a b c a b c a b c a b c a b c a b c a b"
    assert quality(repeated20) is True  # unique trigram ratio below pinned 0.5
    assert quality(repeated20, threshold=1 / 6) is False
    assert quality(repeated20, threshold=0.17) is True
    assert quality("a b c a b c a b c a b c a b c a b c a") is False


def test_streaming_block_controls_are_body_only_and_match_pinned_boundaries() -> None:
    _, _, streaming, _ = report.build_guards(Path(os.environ["TD30F_APP_ROOT"]))
    block = "abcdefghijklmnopqrst\n" + "ABCDEFGHIJKLMNOPQRST\n" + "01234567890123456789"
    assert len(block) == 62
    twice = block + "\n" + block + "\n" + "z" * 60
    thrice = "\n".join([block, block, block])
    assert len(twice) >= 180
    assert streaming(twice) is False
    assert streaming(twice, min_repeats=2) is True
    assert streaming(thrice) is True
    assert streaming(thrice, min_block=63) is False
    exact60 = "a" * 19 + "\n" + "b" * 19 + "\n" + "c" * 20
    assert len(exact60) == 60
    line_aligned60 = "\n".join([exact60, exact60, exact60])
    assert len(line_aligned60) == 182
    assert streaming(line_aligned60) is True
    assert streaming(line_aligned60, min_block=61) is False
    exact59 = "a" * 19 + "\n" + "b" * 19 + "\n" + "c" * 19
    assert len(exact59) == 59
    assert streaming(exact59 * 3 + "xyz") is False  # 180 characters, no qualifying 60-char block
    assert streaming(exact60 * 2 + "x" * 59) is False  # 179 characters, below the body precondition


def test_streaming_precondition_exclusions_use_tail_line_count() -> None:
    assert report.streaming_exclusion_reason("x" * 179) == "below_minimum_chars"
    assert report.streaming_exclusion_reason("x" * 180) == "below_minimum_tail_lines"
    six_lines = "\n".join(["x" * 30, *(["x" * 29] * 5)])
    assert len(six_lines) == 180 and len(six_lines.split("\n")) == 6
    assert report.streaming_exclusion_reason(six_lines) is None
    more_than_tail = "\n".join(["z"] * 2000) + "x" * 4000
    assert report.streaming_exclusion_reason(more_than_tail) == "below_minimum_tail_lines"
