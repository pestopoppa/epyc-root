"""Unit tests for src/batch_edit_parse.py (BEP-1 patchset parser + prompt rider)."""

from __future__ import annotations

import textwrap

import pytest

from src.batch_edit_parse import (
    extract_patchset_json,
    parse_patchset_from_model_output,
    build_batch_edit_instructions,
)
from src.batch_edit import EditOperation, apply_file_patch_to_text, sha256_text


def _wrap(json_body: str) -> str:
    return f"Here is my plan, reasoning done.\n\n```patchset\n{json_body}\n```\n"


# ─── extraction ──────────────────────────────────────────────────────────────────

def test_no_block_returns_none() -> None:
    assert extract_patchset_json("just prose, no block") is None
    assert parse_patchset_from_model_output("FINAL(\"x\")") is None  # falls back to REPL


def test_malformed_json_block_returns_none_from_extract() -> None:
    assert extract_patchset_json("```patchset\n{not json,}\n```") is None


# ─── valid parse ─────────────────────────────────────────────────────────────────

def test_parse_modify_and_create() -> None:
    body = textwrap.dedent("""\
        {"base_repo_sha": "abc",
         "files": [
           {"path": "m.py", "operation": "modify", "base_content_sha256": "s1",
            "hunks": [{"start_line": 2, "end_line": 2, "replacement": "B\\n"}],
            "depends_on": ["n.py"]},
           {"path": "n.py", "operation": "create", "new_content": "x\\n"}
         ]}""")
    ps = parse_patchset_from_model_output(_wrap(body))
    assert ps is not None
    assert ps.base_repo_sha == "abc"
    assert {f.path for f in ps.files} == {"m.py", "n.py"}
    m = next(f for f in ps.files if f.path == "m.py")
    assert m.operation == EditOperation.MODIFY
    assert m.depends_on == ["n.py"]
    assert m.hunks[0].start_line == 2


def test_parsed_patchset_applies_via_bep4() -> None:
    original = "a\nb\nc\n"
    body = (
        '{"files": [{"path": "f.py", "operation": "modify", '
        f'"base_content_sha256": "{sha256_text(original)}", '
        '"hunks": [{"start_line": 2, "end_line": 2, "replacement": "B\\n"}]}]}'
    )
    ps = parse_patchset_from_model_output(_wrap(body))
    out = apply_file_patch_to_text(original, ps.files[0])
    assert out == "a\nB\nc\n"  # end-to-end: parse → deterministic apply


# ─── invalid (present but malformed) raises ──────────────────────────────────────

def test_present_but_invalid_raises() -> None:
    # modify without base_content_sha256 → validate_patchset raises
    body = '{"files": [{"path": "m.py", "operation": "modify", "hunks": [{"start_line": 1, "end_line": 1, "replacement": "x"}]}]}'
    with pytest.raises(ValueError):
        parse_patchset_from_model_output(_wrap(body))


def test_file_entry_without_path_raises() -> None:
    body = '{"files": [{"operation": "create", "new_content": "x"}]}'
    with pytest.raises(ValueError, match="missing 'path'"):
        parse_patchset_from_model_output(_wrap(body))


def test_validate_false_skips_validation() -> None:
    # with validate=False a structurally-parseable but semantically-invalid set is returned as-is
    body = '{"files": [{"path": "m.py", "operation": "modify", "hunks": []}]}'
    ps = parse_patchset_from_model_output(_wrap(body), validate=False)
    assert ps is not None and ps.files[0].path == "m.py"


# ─── prompt rider ────────────────────────────────────────────────────────────────

def test_instructions_describe_the_format() -> None:
    instr = build_batch_edit_instructions()
    assert "```patchset" in instr
    assert "base_content_sha256" in instr  # stale-base protection surfaced to the model
    assert "EXACTLY ONE patch set" in instr
