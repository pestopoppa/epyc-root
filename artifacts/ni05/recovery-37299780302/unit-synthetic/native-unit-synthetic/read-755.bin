"""Unit tests for benchmark seeding_checkpoint helper module."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_checkpoint_test", _ROOT / "seeding_checkpoint.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_checkpoint_test"] = _MOD
_SPEC.loader.exec_module(_MOD)


def test_prompt_hash_is_stable_and_truncated():
    h1 = _MOD._prompt_hash("hello world")
    h2 = _MOD._prompt_hash("hello world")
    h3 = _MOD._prompt_hash("different")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 12


def test_atomic_append_appends_with_newline(tmp_path: Path):
    path = tmp_path / "out.jsonl"
    _MOD._atomic_append(path, "line1")
    _MOD._atomic_append(path, "line2")
    assert path.read_text().splitlines() == ["line1", "line2"]


def test_load_checkpoint_missing_file_returns_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_MOD, "EVAL_DIR", tmp_path)
    assert _MOD.load_checkpoint("missing") == []


def test_checkpoint_result_and_load_checkpoint_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_MOD, "EVAL_DIR", tmp_path)

    rr = _MOD.RoleResult(
        role="frontdoor",
        mode="direct",
        answer="42",
        passed=True,
        elapsed_seconds=1.5,
    )
    comp = _MOD.ComparativeResult(
        suite="math",
        question_id="q1",
        prompt="What is 6*7?",
        expected="42",
        role_results={"frontdoor": rr},
    )

    _MOD.checkpoint_result("sess-a", comp)
    loaded = _MOD.load_checkpoint("sess-a")
    assert len(loaded) == 1
    assert loaded[0].question_id == "q1"
    assert loaded[0].role_results["frontdoor"].answer == "42"


def test_load_checkpoint_skips_invalid_lines(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_MOD, "EVAL_DIR", tmp_path)
    path = tmp_path / "sess-b.jsonl"

    valid = {
        "suite": "math",
        "question_id": "q2",
        "prompt": "p",
        "expected": "e",
        "role_results": {
            "frontdoor": {
                "role": "frontdoor",
                "mode": "direct",
                "answer": "ok",
                "passed": True,
                "elapsed_seconds": 0.1,
            }
        },
    }
    missing_required = {"suite": "math"}  # KeyError when reconstructing

    path.write_text("\n".join([json.dumps(valid), "", "{bad json", json.dumps(missing_required)]))

    loaded = _MOD.load_checkpoint("sess-b")
    assert len(loaded) == 1
    assert loaded[0].question_id == "q2"


def test_load_seen_questions_handles_seen_and_session_files(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_MOD, "EVAL_DIR", tmp_path)

    (tmp_path / "seen_questions.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"prompt_id": "p-seen"}),
                "",
                "{bad json",
                json.dumps({"prompt_id": ""}),
            ]
        )
    )
    (tmp_path / "sess-c.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"question_id": "q-seen"}),
                "",
                "{bad json",
                json.dumps({"question_id": ""}),
            ]
        )
    )

    seen = _MOD.load_seen_questions()
    assert seen == {"p-seen", "q-seen"}


def test_load_seen_questions_missing_eval_dir_returns_empty(tmp_path: Path, monkeypatch):
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(_MOD, "EVAL_DIR", missing)
    assert _MOD.load_seen_questions() == set()


def test_record_seen_appends_entry(tmp_path: Path, monkeypatch):
    eval_dir = tmp_path / "eval"
    seen_file = eval_dir / "seen_questions.jsonl"
    monkeypatch.setattr(_MOD, "EVAL_DIR", eval_dir)
    monkeypatch.setattr(_MOD, "SEEN_FILE", seen_file)

    _MOD.record_seen("prompt-1", "suite-a", "sess-x")

    lines = seen_file.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["prompt_id"] == "prompt-1"
    assert entry["suite"] == "suite-a"
    assert entry["session"] == "sess-x"
    assert isinstance(entry["timestamp"], str)
