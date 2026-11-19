"""Synthetic legacy traces for TOC-SP-5 coverage and denominator rules."""

import json

from scripts.analysis.toc_sp5_gate import analyze_sp5_corpus


def write_trace(root, name, content):
    traces = root / "results" / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    (traces / f"{name}.jsonl").write_text(content)


def turn(index, **fields):
    return json.dumps({"role": "coder_escalation", "turn": index, **fields}) + "\n"


def test_missing_corpus_keeps_fixed_denominator(tmp_path):
    result = analyze_sp5_corpus(tmp_path / "absent")
    assert result["missing_traces"] == 62
    assert result["max_prompt_chars"] is None
    gate = result["occupancy"]["coder_escalation"]
    assert gate["threshold_shares"] == "UNKNOWN"
    assert gate["windows"][":8070 slot"]["bounds"]["0.60"]["conditional_share_interval"] == [0, 1]


def test_zero_visible_spills_do_not_produce_zero_follow_rate(tmp_path):
    write_trace(tmp_path, "t1-off", turn(1, prompt_tail="ordinary output", extracted_code="x = 1"))
    spill = analyze_sp5_corpus(tmp_path)["spill"]
    assert spill["header_turns"] == spill["spill_path_reference_turns"] == 0
    assert spill["prompt_tail_turns"] == 1
    for metric in ("task_follow_rate", "size_decile_follows_per_spill", "post_elision_rereads", "post_elision_reruns"):
        assert spill[metric]["value"] == "UNKNOWN"
        assert spill[metric]["status"] == "blocked on the TOC-SP-6 artifact build"


def test_partial_and_unparsable_traces_remain_unknown(tmp_path):
    write_trace(tmp_path, "t1-off", turn(1, prompt_chars=32_768))
    write_trace(tmp_path, "t1-on", turn(1, prompt_chars=10) + turn(2))
    write_trace(tmp_path, "t2-off", turn(1) + "bad JSON")
    result = analyze_sp5_corpus(tmp_path)
    assert result["complete_prompt_chars_traces"] == 1
    assert result["unparsable_traces"] == 1
    assert result["missing_traces"] == 59
    assert result["cohort_denominator"] == 62
    gate = result["occupancy"]["coder_escalation"]["windows"][":8070 slot"]["bounds"]["0.50"]
    assert gate["conditional_excluded"] == 1
    assert gate["conditional_unknown"] == 61
