"""Unit tests for the one-shot edit transaction (src/edit_transaction.py).

Covers parsing, the TRANSACTIONAL apply (snapshot -> write/delete -> self-check -> promote/rollback),
path-safety, and the end-to-end run() with a stub LLM. No inference.
"""
from __future__ import annotations

import pytest

from src.edit_transaction import (
    parse_edit_response, apply_edit_transaction, assemble_context, build_edit_prompt,
    run_edit_transaction, edit_transaction_enabled, _safe_join,
    EditScopeError, DEFAULT_MAX_BYTES,
    EDIT_TRANSACTION_OUTCOME_COUNTS, reset_outcome_counts_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_edit_transaction_outcome_counts():
    reset_outcome_counts_for_tests()
    yield
    reset_outcome_counts_for_tests()


# ── parsing ────────────────────────────────────────────────────────────
def test_parse_full_file_blocks():
    text = "<<<FILE: calc.py>>>\ndef add(a, b):\n    return a + b\n<<<END>>>\n<<<DELETE: old.py>>>"
    files, deletes = parse_edit_response(text)
    assert files == {"calc.py": "def add(a, b):\n    return a + b"}
    assert deletes == ["old.py"]


def test_parse_fence_fallback():
    files, _ = parse_edit_response("### utils.py\n```python\nX = 1\n```")
    assert files.get("utils.py") == "X = 1\n"


def test_parse_empty_or_prose():
    assert parse_edit_response("") == ({}, [])
    assert parse_edit_response("just prose, no blocks") == ({}, [])


# ── transactional apply ────────────────────────────────────────────────
def test_apply_success_keeps(tmp_path):
    (tmp_path / "calc.py").write_text("def double(x):\n    return x * 2\n")
    res = apply_edit_transaction(tmp_path, {"calc.py": "def double(x):\n    return x*2\ndef square(x):\n    return x*x\n"}, [])
    assert res.ok and res.written == ["calc.py"]
    assert "square" in (tmp_path / "calc.py").read_text()


def test_apply_rolls_back_on_syntax_error(tmp_path):
    (tmp_path / "calc.py").write_text("ORIGINAL = 1\n")
    res = apply_edit_transaction(tmp_path, {"calc.py": "def broken(:\n    pass\n"}, [])
    assert not res.ok and "Error" in res.error
    assert (tmp_path / "calc.py").read_text() == "ORIGINAL = 1\n"  # rolled back


def test_apply_rollback_undoes_partial_transaction(tmp_path):
    # one good edit + one syntactically-broken new file -> the WHOLE transaction rolls back.
    (tmp_path / "a.py").write_text("A = 1\n")
    res = apply_edit_transaction(tmp_path, {"a.py": "A = 2\n", "b.py": "def x(:\n"}, [])
    assert not res.ok
    assert (tmp_path / "a.py").read_text() == "A = 1\n"   # restored
    assert not (tmp_path / "b.py").exists()              # creation undone


def test_apply_runs_functional_verifier_after_self_check(tmp_path):
    (tmp_path / "calc.py").write_text("def square(x):\n    return 0\n")

    def verifier(root):
        ns = {}
        exec((root / "calc.py").read_text(), ns)
        return ns["square"](5) == 25

    res = apply_edit_transaction(
        tmp_path,
        {"calc.py": "def square(x):\n    return x * x\n"},
        [],
        verify_fn=verifier,
    )
    assert res.ok
    assert "return x * x" in (tmp_path / "calc.py").read_text()


def test_apply_rolls_back_on_functional_verifier_failure(tmp_path):
    (tmp_path / "calc.py").write_text("def square(x):\n    return 0\n")

    def verifier(root):
        ns = {}
        exec((root / "calc.py").read_text(), ns)
        return False, f"square(5)={ns['square'](5)}"

    res = apply_edit_transaction(
        tmp_path,
        {"calc.py": "def square(x):\n    return x + x\n"},
        [],
        verify_fn=verifier,
    )
    assert not res.ok
    assert "functional verifier failed" in res.error
    assert "square(5)=10" in res.error
    assert (tmp_path / "calc.py").read_text() == "def square(x):\n    return 0\n"


def test_apply_rolls_back_on_functional_verifier_exception(tmp_path):
    (tmp_path / "a.py").write_text("A = 1\n")
    (tmp_path / "gone.py").write_text("GONE = 1\n")

    def verifier(_root):
        raise AssertionError("task verifier rejected output")

    res = apply_edit_transaction(
        tmp_path,
        {"a.py": "A = 2\n", "new.py": "NEW = 1\n"},
        ["gone.py"],
        verify_fn=verifier,
    )
    assert not res.ok
    assert "task verifier rejected output" in res.error
    assert (tmp_path / "a.py").read_text() == "A = 1\n"
    assert (tmp_path / "gone.py").read_text() == "GONE = 1\n"
    assert not (tmp_path / "new.py").exists()


def test_apply_delete(tmp_path):
    (tmp_path / "helpers.py").write_text("def greet():\n    return 'hi'\n")
    res = apply_edit_transaction(tmp_path, {"utils.py": "def greet():\n    return 'hi'\n"}, ["helpers.py"])
    assert res.ok and not (tmp_path / "helpers.py").exists() and res.deleted == ["helpers.py"]
    assert (tmp_path / "utils.py").exists()


def test_apply_nothing_parsed(tmp_path):
    res = apply_edit_transaction(tmp_path, {}, [])
    assert not res.ok and "no valid file blocks" in res.error


# ── path safety ────────────────────────────────────────────────────────
def test_path_escape_aborts_whole_transaction(tmp_path):
    # FAIL-CLOSED (review #4): any unsafe path aborts the ENTIRE transaction — even the safe edit is
    # not applied, preserving the all-or-nothing safety claim for an agent-facing edit surface.
    res = apply_edit_transaction(tmp_path, {"../escape.py": "X=1\n", "/abs_escape.py": "Y=1\n",
                                            "ok.py": "Z=1\n"}, [])
    assert not res.ok
    assert "../escape.py" in res.rejected and "/abs_escape.py" in res.rejected
    assert res.written == []                              # nothing applied
    assert not (tmp_path / "ok.py").exists()              # the safe one was NOT written either
    assert not (tmp_path.parent / "escape.py").exists()   # escape did not write outside


def test_safe_join(tmp_path):
    assert _safe_join(tmp_path, "a/b.py") is not None       # nested preserved
    assert _safe_join(tmp_path, "../x.py") is None
    assert _safe_join(tmp_path, "/etc/passwd") is None


def test_apply_preserves_nested_paths(tmp_path):
    res = apply_edit_transaction(tmp_path, {"pkg/sub/mod.py": "VALUE = 7\n"}, [])
    assert res.ok and (tmp_path / "pkg" / "sub" / "mod.py").read_text() == "VALUE = 7\n"


# ── assemble + end-to-end with a stub LLM ──────────────────────────────
def test_assemble_and_prompt(tmp_path):
    (tmp_path / "calc.py").write_text("X = 1\n")
    ctx = assemble_context(tmp_path, ["calc.py"])
    assert ctx == {"calc.py": "X = 1\n"}
    prompt = build_edit_prompt("Add square", ctx)
    assert "Add square" in prompt and "calc.py" in prompt and "<<<FILE:" in prompt


def test_assemble_explicit_targets_are_deterministic_and_bounded(tmp_path):
    (tmp_path / "b.py").write_text("B = 2\n")
    (tmp_path / "a.py").write_text("A = 1\n")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "c.py").write_text("C = 3\n")

    ctx = assemble_context(tmp_path, ["b.py", "a.py", "b.py", "nested/../nested/c.py"])
    assert list(ctx) == ["a.py", "b.py", "nested/c.py"]
    assert ctx["a.py"] == "A = 1\n"
    assert "C = 3" in ctx["nested/c.py"]


def test_assemble_explicit_targets_reject_unsafe_paths(tmp_path):
    (tmp_path / "ok.py").write_text("OK = 1\n")
    with pytest.raises(EditScopeError, match="unsafe target file rejected"):
        assemble_context(tmp_path, ["ok.py", "../escape.py"])


def test_run_edit_transaction_with_stub_llm(tmp_path):
    (tmp_path / "calc.py").write_text("def double(x):\n    return x * 2\n")

    def stub(prompt):
        assert "Current file contents:" in prompt  # context was assembled into the prompt
        return "<<<FILE: calc.py>>>\ndef double(x):\n    return x*2\ndef square(x):\n    return x*x\n<<<END>>>"

    res, raw = run_edit_transaction(stub, "Add square(x) to calc.py", tmp_path, ["calc.py"])
    assert res.ok and "square" in (tmp_path / "calc.py").read_text()


def test_run_edit_transaction_review_is_default_inert(tmp_path):
    (tmp_path / "calc.py").write_text("VALUE = 1\n")

    calls = {"review": 0}

    def stub(_prompt):
        return "<<<FILE: calc.py>>>\nVALUE = 2\n<<<END>>>"

    def review(_context):
        calls["review"] += 1
        return {
            "risks": [],
            "blocking_issues": ["should not run"],
            "confidence": 1.0,
            "recommended_delta": "rerun",
        }, {}

    res, raw = run_edit_transaction(
        stub,
        "Edit value",
        tmp_path,
        ["calc.py"],
        review_before_commit=review,
    )

    assert raw
    assert res.ok
    assert calls["review"] == 0
    assert res.consult_events == []
    assert (tmp_path / "calc.py").read_text() == "VALUE = 2"


def test_run_edit_transaction_review_reruns_on_blocking_advisory(tmp_path):
    (tmp_path / "calc.py").write_text("VALUE = 1\n")
    prompts: list[str] = []

    def stub(prompt):
        prompts.append(prompt)
        if len(prompts) == 1:
            return "<<<FILE: calc.py>>>\nVALUE = 2\n<<<END>>>"
        assert "Architect review before commit found blocking issues" in prompt
        return "<<<FILE: calc.py>>>\nVALUE = 3\n<<<END>>>"

    def review(context):
        assert "VALUE = 2" in context
        return {
            "risks": ["missed requested value"],
            "blocking_issues": ["final value must be 3"],
            "confidence": 0.9,
            "recommended_delta": "write VALUE = 3",
        }, {"schema_hash": "abc123"}

    res, raw = run_edit_transaction(
        stub,
        "Set value",
        tmp_path,
        ["calc.py"],
        review_before_commit=review,
        enable_review_before_commit=True,
    )

    assert raw
    assert res.ok
    assert len(prompts) == 2
    assert res.consult_events[0]["success"] is True
    assert res.consult_events[0]["rerun_requested"] is True
    assert res.consult_events[0]["schema_hash"] == "abc123"
    assert (tmp_path / "calc.py").read_text() == "VALUE = 3"


def test_run_edit_transaction_review_denied_proceeds_with_original_draft(tmp_path):
    (tmp_path / "calc.py").write_text("VALUE = 1\n")

    def stub(_prompt):
        return "<<<FILE: calc.py>>>\nVALUE = 2\n<<<END>>>"

    def review(_context):
        raise RuntimeError("consult unavailable")

    res, raw = run_edit_transaction(
        stub,
        "Set value",
        tmp_path,
        ["calc.py"],
        review_before_commit=review,
        enable_review_before_commit=True,
    )

    assert raw
    assert res.ok
    assert res.consult_events[0]["success"] is False
    assert res.consult_events[0]["reason"] == "RuntimeError"
    assert (tmp_path / "calc.py").read_text() == "VALUE = 2"


def test_run_edit_transaction_review_gate_skips_consult(tmp_path):
    (tmp_path / "calc.py").write_text("VALUE = 1\n")
    calls = {"review": 0}

    def stub(_prompt):
        return "<<<FILE: calc.py>>>\nVALUE = 2\n<<<END>>>"

    def review(_context):
        calls["review"] += 1
        return {
            "risks": ["should not run"],
            "blocking_issues": ["should not run"],
            "confidence": 1.0,
        }, {}

    def gate(context):
        assert context["task_prompt"] == "Set value"
        assert context["draft_paths"] == ["calc.py"]
        return {"enabled": False, "reasons": ["plain_single_file_edit"]}

    res, raw = run_edit_transaction(
        stub,
        "Set value",
        tmp_path,
        ["calc.py"],
        review_before_commit=review,
        enable_review_before_commit=True,
        review_before_commit_gate=gate,
    )

    assert raw
    assert res.ok
    assert calls["review"] == 0
    assert res.consult_events == [
        {
            "interaction_type": "consult",
            "skill": "review_before_commit",
            "success": True,
            "skipped": True,
            "reason": "targeted_gate_skip",
            "gate_reasons": ["plain_single_file_edit"],
        }
    ]
    assert (tmp_path / "calc.py").read_text() == "VALUE = 2"


def test_run_edit_transaction_uses_only_explicit_targets(tmp_path):
    (tmp_path / "a.py").write_text("A = 1\n")
    (tmp_path / "b.py").write_text("B = 2\n")
    (tmp_path / "c.py").write_text("C = 3\n")

    seen = {"called": False}

    def stub(prompt):
        seen["called"] = True
        assert "--- a.py ---" in prompt
        assert "--- b.py ---" in prompt
        assert "--- c.py ---" not in prompt
        assert prompt.index("--- a.py ---") < prompt.index("--- b.py ---")
        return "<<<FILE: a.py>>>\nA = 10\n<<<END>>>\n<<<FILE: b.py>>>\nB = 20\n<<<END>>>"

    res, raw = run_edit_transaction(stub, "Edit two files", tmp_path, ["b.py", "a.py", "b.py"])
    assert seen["called"]
    assert raw
    assert res.ok
    assert (tmp_path / "a.py").read_text() == "A = 10"
    assert (tmp_path / "b.py").read_text() == "B = 20"
    assert (tmp_path / "c.py").read_text() == "C = 3\n"


def test_run_edit_transaction_passes_functional_verifier(tmp_path):
    (tmp_path / "calc.py").write_text("def square(x):\n    return 0\n")

    def stub(_prompt):
        return "<<<FILE: calc.py>>>\ndef square(x):\n    return x * x\n<<<END>>>"

    def verifier(root):
        ns = {}
        exec((root / "calc.py").read_text(), ns)
        return ns["square"](6) == 36

    res, raw = run_edit_transaction(
        stub,
        "Fix square",
        tmp_path,
        ["calc.py"],
        verify_fn=verifier,
    )
    assert raw
    assert res.ok
    assert "return x * x" in (tmp_path / "calc.py").read_text()


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_EDIT_TRANSACTION", raising=False)
    assert edit_transaction_enabled() is False
    monkeypatch.setenv("ORCHESTRATOR_EDIT_TRANSACTION", "1")
    assert edit_transaction_enabled() is True


# ── review-hardening 2026-05-27: scope caps (#1) + no-__pycache__ self-check (#3) ──────
def test_assemble_caps_filecount(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.py").write_text("X=1\n")
    assert len(assemble_context(tmp_path, max_files=10)) == 5     # within cap
    with pytest.raises(EditScopeError):
        assemble_context(tmp_path, max_files=3)                   # exceeds file cap -> fail-closed


def test_assemble_caps_bytes(tmp_path):
    (tmp_path / "big.py").write_text("X" * 1000)
    with pytest.raises(EditScopeError):
        assemble_context(tmp_path, max_bytes=100)                 # exceeds byte cap -> fail-closed


def test_caps_bound_via_stat_without_reading(tmp_path, monkeypatch):
    # #2: oversized scope is rejected via stat().st_size, WITHOUT loading file content into memory.
    import pathlib
    (tmp_path / "big.py").write_text("X" * 1000)
    monkeypatch.setattr(pathlib.Path, "read_text",
                        lambda self, *a, **k: pytest.fail("read_text called despite oversized scope"))
    with pytest.raises(EditScopeError):
        assemble_context(tmp_path, max_bytes=100)


def test_run_edit_transaction_failclosed_on_oversized_scope(tmp_path):
    # Unscoped whole-root assembly over caps must fail-closed BEFORE calling the model or writing.
    (tmp_path / "big.py").write_text("X" * (DEFAULT_MAX_BYTES + 1))
    called = {"n": 0}

    def stub(prompt):
        called["n"] += 1
        return "<<<FILE: big.py>>>\nY = 2\n<<<END>>>"

    res, _raw = run_edit_transaction(stub, "edit", tmp_path, target_files=None)
    assert not res.ok and "scope too large" in res.error
    assert called["n"] == 0                                       # model NOT called
    assert (tmp_path / "big.py").read_text().startswith("XXXX")   # original untouched


def test_self_check_no_pycache_side_effect(tmp_path):
    # compile(source, path, "exec") validates syntax WITHOUT writing __pycache__/*.pyc that the
    # snapshot/rollback wouldn't track.
    (tmp_path / "m.py").write_text("OLD = 1\n")
    res = apply_edit_transaction(tmp_path, {"m.py": "NEW = 2\n"}, [])
    assert res.ok
    assert not (tmp_path / "__pycache__").exists()
    assert list(tmp_path.rglob("*.pyc")) == []


# ── TD-21.21: unclosed trailing block, gated on finish_reason ──────────
def test_parse_missing_end_natural_stop_is_recovered():
    # The model finished the file and simply forgot the closing marker -- a NATURAL stop
    # ("eos"/"stop"/"word") is safe to close deterministically: nothing is invented, only the
    # missing structural newline+delimiter is supplied.
    text = "<<<FILE: calc.py>>>\ndef add(a, b):\n    return a + b\n"
    files, deletes = parse_edit_response(text, finish_reason="stop")
    assert files == {"calc.py": "def add(a, b):\n    return a + b"}
    assert deletes == []
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["recovered_unclosed_trailing_file"] == 1


@pytest.mark.parametrize("finish_reason", ["stop", "eos", "word"])
def test_parse_missing_end_recovered_for_every_natural_stop_value(finish_reason):
    text = "<<<FILE: calc.py>>>\nVALUE = 1\n"
    files, _ = parse_edit_response(text, finish_reason=finish_reason)
    assert files == {"calc.py": "VALUE = 1"}


@pytest.mark.parametrize("finish_reason", ["length", "limit"])
def test_parse_missing_end_length_cutoff_never_written(finish_reason):
    # A length/limit cutoff can land anywhere -- mid-token, mid-line -- so the incomplete file must
    # NEVER be written, exactly like before TD-21.21, but now the drop carries a specific reason.
    text = "<<<FILE: huge.py>>>\ndef partial(\n    x, y"
    files, deletes = parse_edit_response(text, finish_reason=finish_reason)
    assert files == {}
    assert deletes == []
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["truncated_trailing_file_dropped"] == 1


def test_parse_missing_end_unknown_reason_stays_failclosed_like_before():
    # No finish_reason wired (the pre-TD-21.21 default for every existing caller) -- identical
    # behavior to before: the unclosed trailing block is dropped, not guessed at.
    text = "<<<FILE: calc.py>>>\nVALUE = 1\n"
    files, deletes = parse_edit_response(text)
    assert files == {}
    assert deletes == []
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["unclosed_trailing_file_ambiguous"] == 1


def test_parse_happy_path_is_counted_clean_regardless_of_finish_reason():
    text = "<<<FILE: calc.py>>>\nVALUE = 1\n<<<END>>>"
    files, _ = parse_edit_response(text, finish_reason="length")
    assert files == {"calc.py": "VALUE = 1"}
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["clean"] == 1
    assert "truncated_trailing_file_dropped" not in EDIT_TRANSACTION_OUTCOME_COUNTS


def test_parse_multi_file_only_last_is_open_earlier_ones_still_written():
    # A max-context generation covering several files: the first is fully closed and must be kept
    # even when the LAST file was cut off.
    text = (
        "<<<FILE: a.py>>>\nA = 1\n<<<END>>>\n"
        "<<<FILE: b.py>>>\nB = 2 (unterminated"
    )
    files, _ = parse_edit_response(text, finish_reason="length")
    assert files == {"a.py": "A = 1"}
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["truncated_trailing_file_dropped"] == 1


def test_parse_content_containing_delimiter_lookalike_survives():
    # File content containing '<<<' that does NOT form a real header/END sequence (git conflict
    # markers, template placeholders, ASCII banners...) must round-trip byte-for-byte inside a
    # properly closed block -- this is also the concrete reason a GBNF grammar excluding '<<<END>>>'
    # from body content would be unsafe (see the module-level comment in src/edit_transaction.py).
    body = 'MARKER = "<<< not a real delimiter >>>"\nCONFLICT = "<<<<<<< HEAD"'
    text = f"<<<FILE: banner.py>>>\n{body}\n<<<END>>>"
    files, _ = parse_edit_response(text, finish_reason="stop")
    assert files == {"banner.py": body}
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["clean"] == 1


def test_parse_decoy_header_inside_closed_block_is_not_mistaken_for_unclosed():
    # A closed file whose OWN content contains the literal '<<<FILE: ...>>>' text (e.g. this very
    # module's EDIT_INSTRUCTIONS / _FILE_RE source) must not be misread as a second, unclosed,
    # trailing file -- the decoy header lives INSIDE the closed span, not after it.
    text = (
        "<<<FILE: real.py>>>\n"
        'print("<<<FILE: fake.py>>>")\n'
        'print("end of real file")\n'
        "<<<END>>>"
    )
    files, _ = parse_edit_response(text, finish_reason="stop")
    assert files == {"real.py": 'print("<<<FILE: fake.py>>>")\nprint("end of real file")'}
    assert "fake.py" not in files
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["clean"] == 1


def test_parse_delete_after_open_header_is_ambiguous_not_recovered():
    # The protocol moving on to a DELETE after an open FILE header is a different anomaly than a
    # trailing cutoff -- do not guess.
    text = "<<<FILE: partial.py>>>\nX = 1\n<<<DELETE: other.py>>>"
    files, deletes = parse_edit_response(text, finish_reason="stop")
    assert files == {}
    assert deletes == ["other.py"]
    assert EDIT_TRANSACTION_OUTCOME_COUNTS["unclosed_trailing_file_ambiguous"] == 1


def test_run_edit_transaction_recovers_missing_end_on_natural_stop(tmp_path):
    (tmp_path / "calc.py").write_text("VALUE = 1\n")

    def stub(_prompt):
        return "<<<FILE: calc.py>>>\nVALUE = 2\n"  # no <<<END>>>

    res, raw = run_edit_transaction(
        stub, "Set value", tmp_path, ["calc.py"], get_finish_reason=lambda: "stop",
    )
    assert raw
    assert res.ok
    assert res.parse_outcome == "recovered_unclosed_trailing_file"
    assert (tmp_path / "calc.py").read_text() == "VALUE = 2"


def test_run_edit_transaction_never_writes_a_length_truncated_file(tmp_path):
    (tmp_path / "calc.py").write_text("VALUE = 1\n")

    def stub(_prompt):
        return "<<<FILE: calc.py>>>\nVALUE = 2 + (unterminated"  # cut mid-expression

    res, raw = run_edit_transaction(
        stub, "Set value", tmp_path, ["calc.py"], get_finish_reason=lambda: "length",
    )
    assert raw
    assert not res.ok  # fail-closed: nothing valid to write
    assert res.parse_outcome == "truncated_trailing_file_dropped"
    assert (tmp_path / "calc.py").read_text() == "VALUE = 1\n"  # untouched


def test_run_edit_transaction_default_get_finish_reason_is_failclosed(tmp_path):
    # No get_finish_reason wired at all (matches every caller before TD-21.21) -- identical
    # behavior to before: an unclosed trailing block is dropped, not guessed at.
    (tmp_path / "calc.py").write_text("VALUE = 1\n")

    def stub(_prompt):
        return "<<<FILE: calc.py>>>\nVALUE = 2\n"

    res, raw = run_edit_transaction(stub, "Set value", tmp_path, ["calc.py"])
    assert not res.ok
    assert res.parse_outcome == "unclosed_trailing_file_ambiguous"
    assert (tmp_path / "calc.py").read_text() == "VALUE = 1\n"


def test_run_edit_transaction_rerun_path_also_reports_finish_reason(tmp_path):
    # The review-driven rerun (:401 in the handoff) is the SECOND llm_call/parse pair; it must be
    # wired to get_finish_reason too, not just the initial call.
    (tmp_path / "calc.py").write_text("VALUE = 1\n")
    calls = {"n": 0}
    reasons = {"n": 0}

    def stub(_prompt):
        calls["n"] += 1
        if calls["n"] == 1:
            return "<<<FILE: calc.py>>>\nVALUE = 2\n<<<END>>>"
        return "<<<FILE: calc.py>>>\nVALUE = 3\n"  # rerun forgets the END too

    def review(_context):
        return {
            "blocking_issues": ["must be 3"],
            "confidence": 0.9,
        }, {}

    def get_finish_reason():
        reasons["n"] += 1
        return "stop"

    res, raw = run_edit_transaction(
        stub,
        "Set value",
        tmp_path,
        ["calc.py"],
        review_before_commit=review,
        enable_review_before_commit=True,
        get_finish_reason=get_finish_reason,
    )
    assert raw
    assert res.ok
    assert res.parse_outcome == "recovered_unclosed_trailing_file"
    assert reasons["n"] == 2  # once for the initial parse, once for the rerun's parse
    assert (tmp_path / "calc.py").read_text() == "VALUE = 3"


# ── TD-21.21 coordinator fix: get_finish_reason must survive a SHARED, concurrent primitives ──
def test_run_edit_transaction_finish_reason_not_clobbered_by_concurrent_call(tmp_path):
    """`_init_primitives` (src/api/routes/chat_pipeline/routing.py:487) reuses ONE shared
    LLMPrimitives instance across concurrent requests in the same worker. Before the coordinator
    fix, `get_finish_reason` read the plain `primitives._last_inference_meta` attribute, which a
    concurrent request against the SAME instance can overwrite between this call finishing and
    this code reading it back. This test forces exactly that interleaving with two REAL
    `LLMPrimitives._real_call` invocations (fake backends, no network) on ONE shared instance:
    THIS call's own reason is "length" (truncated -- must never be written); the OTHER,
    concurrent call's reason is "stop". The two are ordered with threading.Event so the other
    call's write provably lands on the shared plain attribute AFTER this call's own backend
    response, and BEFORE this call reads back its finish reason -- the exact race window.
    `get_last_inference_meta()` (a contextvars.ContextVar, isolated per asyncio.to_thread
    context) must still report THIS call's own "length", so the trailing file is NOT written.

    The target is a `.txt` file, deliberately NOT `.py`: `apply_edit_transaction`'s
    `compile()` self-check only runs on `.py` targets, so a `.py` target would mask a
    misclassification behind that unrelated safety net (confirmed manually: swapping this
    test's `get_finish_reason` back to the pre-fix `getattr(primitives, "_last_inference_meta",
    {})` idiom DOES misclassify this race as `"recovered_unclosed_trailing_file"` and, on a
    `.txt` target, WRITES the truncated content -- exactly the corruption this fix exists to
    prevent). The `.txt` target exercises the finish-reason gating alone.
    """
    import asyncio
    import threading
    from unittest.mock import Mock

    from src.llm_primitives import LLMPrimitives
    from src.model_server import InferenceResult

    (tmp_path / "notes.txt").write_text("original\n")

    prims = LLMPrimitives(
        mock_mode=False,
        server_urls={"role_a": "http://localhost:9001", "role_b": "http://localhost:9002"},
    )
    backend_a = Mock(spec=[])
    backend_a.infer = Mock(return_value=InferenceResult(
        role="role_a", output="ignored", tokens_generated=1, generation_speed=1.0,
        elapsed_time=0.001, success=True, prompt_eval_ms=0.1, generation_ms=0.1,
        http_overhead_ms=0.0, completion_reason="length",
    ))
    backend_b = Mock(spec=[])
    backend_b.infer = Mock(return_value=InferenceResult(
        role="role_b", output="ignored", tokens_generated=1, generation_speed=1.0,
        elapsed_time=0.001, success=True, prompt_eval_ms=0.1, generation_ms=0.1,
        http_overhead_ms=0.0, completion_reason="stop",
    ))
    prims._backends["role_a"] = backend_a
    prims._backends["role_b"] = backend_b

    a_backend_done = threading.Event()
    b_backend_done = threading.Event()

    def get_finish_reason() -> str:
        meta = prims.get_last_inference_meta() or {}
        return str(meta.get("completion_reason") or "")

    def call_a_llm(_prompt: str) -> str:
        prims._real_call("edit prompt", "role_a", n_tokens=8)  # sets THIS context's meta: length
        a_backend_done.set()
        assert b_backend_done.wait(timeout=5), "concurrent call B never completed"
        # THIS call's own trailing file is genuinely truncated -- no <<<END>>>.
        return "<<<FILE: notes.txt>>>\nthis got cut off mid-sen"

    def call_b_other_request() -> None:
        assert a_backend_done.wait(timeout=5), "call A's backend response never landed"
        # Clobbers the SHARED plain `_last_inference_meta` attribute to "stop" -- AFTER A's own
        # backend responded, BEFORE A reads its finish reason back.
        prims._real_call("unrelated concurrent prompt", "role_b", n_tokens=8)
        b_backend_done.set()

    async def _run():
        return await asyncio.gather(
            asyncio.to_thread(
                run_edit_transaction, call_a_llm, "Set value", tmp_path, ["notes.txt"],
                get_finish_reason=get_finish_reason,
            ),
            asyncio.to_thread(call_b_other_request),
        )

    (res, raw), _ = asyncio.run(_run())

    # Sanity: the race actually happened -- the shared plain attribute WAS clobbered by B.
    assert prims._last_inference_meta["completion_reason"] == "stop"
    assert raw
    assert not res.ok  # fail-closed: A's own reason was "length", never "stop"
    assert res.parse_outcome == "truncated_trailing_file_dropped"
    assert (tmp_path / "notes.txt").read_text() == "original\n"  # untouched, not corrupted
