"""Tests for TD-21.28: corpus_quality_gate judged-pair extraction.

Before: `judge_pair` extracted the judge's 8 numeric A/B fields with a
single-shot fence regex (`r"```(?:json)?\\s*(\\{.*?\\})\\s*```"`) + bare
`json.loads` + a generic `KeyError` catch, and on any miss silently returned
`None` -- the pair was dropped from the judged set with no counter, so the
gate's own denominator (`avg_delta`/`gate_pass`) moved without a trace.

After: `fish_json` (fence-aware, string-aware balanced-bracket fallback) +
full Draft 2020-12 schema validation of the 8 required numeric fields. The
judge backend is `claude -p` (external CLI, no HTTP endpoint), so the shared
`parse_with_repair` idiom cannot reach it -- this is deterministic-fish-only,
per the TD-21 dispatch's HARD RULES. Every drop is now counted in
`JUDGE_PARSE_COUNTS` (never left to shrink the denominator invisibly).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


_BENCH = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
_SPEC = importlib.util.spec_from_file_location(
    "corpus_quality_gate_test_td2128",
    _BENCH / "corpus_quality_gate.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["corpus_quality_gate_test_td2128"] = _MOD
_SPEC.loader.exec_module(_MOD)


VALID_SCORES = {
    "a_correctness": 8, "a_completeness": 7, "a_quality": 9, "a_originality": 6,
    "b_correctness": 5, "b_completeness": 5, "b_quality": 5, "b_originality": 5,
    "notes": "ok",
}


def _fake_run(stdout: str, returncode: int = 0):
    def run(*_args, **_kwargs):
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="boom" if returncode else "")

    return run


def _reset_counts():
    _MOD.JUDGE_PARSE_COUNTS["parsed"] = 0
    _MOD.JUDGE_PARSE_COUNTS["failed"] = 0


class TestJudgePairHappyPath:
    def setup_method(self):
        _reset_counts()

    def test_clean_json_response_is_parsed_and_counted(self, monkeypatch):
        monkeypatch.setattr(_MOD.subprocess, "run", _fake_run(json.dumps(VALID_SCORES)))
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is not None
        assert jr.prompt_id == "p1"
        assert jr.raw_scores == VALID_SCORES
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 1, "failed": 0}

    def test_fenced_json_response_is_fished(self, monkeypatch):
        fenced = f"Here is my evaluation:\n```json\n{json.dumps(VALID_SCORES)}\n```\n"
        monkeypatch.setattr(_MOD.subprocess, "run", _fake_run(fenced))
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is not None
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 1, "failed": 0}

    def test_bare_fence_with_trailing_prose_is_fished(self, monkeypatch):
        # No language tag, and prose both before and after the block --
        # the balanced-bracket fallback must still find it.
        reply = f"Sure, here you go:\n{json.dumps(VALID_SCORES)}\nLet me know if you need more."
        monkeypatch.setattr(_MOD.subprocess, "run", _fake_run(reply))
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is not None
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 1, "failed": 0}


class TestJudgePairFailureIsCountedNotSilent:
    def setup_method(self):
        _reset_counts()

    def test_non_json_reply_is_dropped_and_counted(self, monkeypatch):
        monkeypatch.setattr(_MOD.subprocess, "run", _fake_run("I refuse to answer in JSON."))
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is None
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 0, "failed": 1}

    def test_missing_required_field_is_schema_invalid_and_counted(self, monkeypatch):
        incomplete = dict(VALID_SCORES)
        del incomplete["b_originality"]
        monkeypatch.setattr(_MOD.subprocess, "run", _fake_run(json.dumps(incomplete)))
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is None
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 0, "failed": 1}

    def test_wrong_type_field_is_schema_invalid_and_counted(self, monkeypatch):
        # The old bare json.loads + KeyError catch would have accepted this
        # (a string) and only failed later doing arithmetic on it, or worse,
        # raised uncaught. Schema validation catches the type up front.
        bad = dict(VALID_SCORES)
        bad["a_correctness"] = "high"
        monkeypatch.setattr(_MOD.subprocess, "run", _fake_run(json.dumps(bad)))
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is None
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 0, "failed": 1}

    def test_claude_cli_nonzero_exit_is_counted(self, monkeypatch):
        monkeypatch.setattr(_MOD.subprocess, "run", _fake_run("", returncode=1))
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is None
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 0, "failed": 1}

    def test_timeout_is_counted(self, monkeypatch):
        import subprocess as real_subprocess

        def raise_timeout(*_args, **_kwargs):
            raise real_subprocess.TimeoutExpired(cmd="claude", timeout=120)

        monkeypatch.setattr(_MOD.subprocess, "run", raise_timeout)
        jr = _MOD.judge_pair("p1", "task", "baseline out", "corpus out")
        assert jr is None
        assert _MOD.JUDGE_PARSE_COUNTS == {"parsed": 0, "failed": 1}
