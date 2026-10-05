"""EPD-3-R5 / R6 / R8 guards (learned-routing-controller handoff).

R5: the deprecated `type:chat` copy is annotated so it cannot be cargo-culted.
R6: the seed write loop fails closed.
R8: the failure / exploration / classification embedding conventions are built
    by the shared segment builder, byte-identical to the historical text.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestration.repl_memory import embedder as embedder_mod  # noqa: E402
from orchestration.repl_memory import memory_record as memory_record_mod  # noqa: E402
from orchestration.repl_memory import seed_loader as seed_loader_mod  # noqa: E402
from orchestration.repl_memory.embedder import TaskEmbedder  # noqa: E402
from orchestration.repl_memory.memory_record import (  # noqa: E402
    EMBED_TEXT_MAX_CHARS,
    MemoryRecord,
    join_embedding_segments,
)


def _bare_embedder() -> TaskEmbedder:
    return TaskEmbedder.__new__(TaskEmbedder)


# ── R8: the shared segment builder ────────────────────────────────────────────


class TestJoinEmbeddingSegments:
    def test_joins_in_order_and_drops_none(self):
        assert join_embedding_segments([("a", 1), ("b", None), ("c", "x")]) == "a:1 | c:x"

    def test_empty_string_is_a_mandatory_segment(self):
        assert join_embedding_segments([("query", ""), ("preview", "")]) == "query: | preview:"

    def test_never_emits_literal_none(self):
        assert "None" not in join_embedding_segments([("error", None), ("gate", "g")])

    def test_caps_the_joined_text(self):
        assert len(join_embedding_segments([("k", "x" * 5000)])) == EMBED_TEXT_MAX_CHARS
        assert join_embedding_segments([("k", "abcdef")], max_chars=4) == "k:ab"

    @pytest.mark.parametrize(
        "record, expected",
        [
            (MemoryRecord(objective=" do X ", task_type="coder", priority="interactive"),
             "type:coder | objective:do X | priority:interactive"),
            (MemoryRecord(objective="do X"), "objective:do X"),
            (MemoryRecord(objective="", task_type="", priority=""), "objective:"),
        ],
    )
    def test_task_convention_is_byte_identical(self, record, expected):
        assert record.embedding_text() == expected


# Goldens = the exact text the pre-R8 hand-built serializers produced.
FAILURE_CASES = [
    (
        {"error_type": "timeout", "gate_name": "lint", "agent_tier": "B", "failure_message": "m" * 300},
        "error:timeout | gate:lint | tier:B | message:" + "m" * 200,
    ),
    ({"gate_name": "tests"}, "gate:tests"),
    ({}, ""),
    ({"agent_tier": 2, "failure_message": "boom"}, "tier:2 | message:boom"),
]


class TestNonTaskConventionsAreByteIdentical:
    @pytest.mark.parametrize("ctx, golden", FAILURE_CASES)
    def test_failure_context(self, ctx, golden):
        assert _bare_embedder()._serialize_failure_context(ctx) == golden

    def test_failure_context_none_values_no_longer_leak(self):
        text = _bare_embedder()._serialize_failure_context(
            {"error_type": None, "gate_name": "g", "failure_message": None}
        )
        assert text == "gate:g"

    @pytest.mark.parametrize(
        "query, preview, golden",
        [
            ("find foo", "p" * 600, "query:find foo | preview:" + "p" * 500),
            ("find foo", "", "query:find foo | preview:"),
            ("find foo", None, "query:find foo | preview:"),
            ("", "ctx", "query: | preview:ctx"),
        ],
    )
    def test_exploration(self, query, preview, golden):
        assert _bare_embedder()._serialize_exploration(query, preview) == golden

    @pytest.mark.parametrize(
        "prompt, ctype, golden",
        [
            ("route me", "routing", "classify:routing | prompt:route me"),
            ("q" * 400, "summarization", "classify:summarization | prompt:" + "q" * 300),
            ("", "routing", "classify:routing | prompt:"),
        ],
    )
    def test_classification(self, prompt, ctype, golden):
        assert _bare_embedder()._serialize_classification_prompt(prompt, ctype) == golden


class TestSerializersDelegateToTheSharedBuilder:
    """Equality is not enough: a re-spelling that agrees today drifts tomorrow."""

    @pytest.mark.parametrize(
        "call",
        [
            lambda e: e._serialize_failure_context({"error_type": "x"}),
            lambda e: e._serialize_exploration("q", "p"),
            lambda e: e._serialize_classification_prompt("p", "routing"),
            lambda e: e._serialize_task_ir({"objective": "o"}),
        ],
    )
    def test_calls_the_shared_builder(self, monkeypatch, call):
        calls: list[list] = []
        original = memory_record_mod.join_embedding_segments

        def spy(segments, *a, **k):
            segments = list(segments)
            calls.append(segments)
            return original(segments, *a, **k)

        monkeypatch.setattr(embedder_mod, "join_embedding_segments", spy)
        monkeypatch.setattr(memory_record_mod, "join_embedding_segments", spy)
        call(_bare_embedder())
        assert calls, "serializer did not go through join_embedding_segments"

    def test_embedder_module_holds_the_shared_symbol(self):
        assert embedder_mod.join_embedding_segments is memory_record_mod.join_embedding_segments

    def test_no_hand_joined_convention_in_embedder(self):
        source = Path(embedder_mod.__file__).read_text()
        assert '" | ".join' not in source
        for key in ("error:", "gate:", "tier:", "message:", "query:", "preview:", "classify:", "prompt:"):
            assert f'f"{key}' not in source, key


# ── R5: the deprecated copy is annotated ──────────────────────────────────────


def test_deprecated_hand_built_conventions_are_annotated():
    """Every `objective:{` f-string under a deprecated/ tree carries EPD-3-R5."""
    offenders: list[str] = []
    found = 0
    for root in (REPO_ROOT / "scripts", REPO_ROOT / "orchestration", REPO_ROOT / "src"):
        for path in root.rglob("*.py"):
            if "deprecated" not in path.parts:
                continue
            for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if "objective:{" in line:
                    found += 1
                    if "EPD-3-R5" not in line:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert found, "no deprecated convention found — the guard is vacuous; drop it with the file"
    assert not offenders, f"unannotated deprecated embedding convention: {offenders}"


# ── R6: the seed write loop fails closed ──────────────────────────────────────


class _FakeEmbeddingStore:
    count = 0

    def __init__(self):
        self.saved = 0

    def save(self):
        self.saved += 1


class _FakeStore:
    def __init__(self, *a, **k):
        self.stored: list[dict] = []
        self.flushed = 0
        self.sqlite_path = Path("/nonexistent/episodic.db")
        self.storage_dir = Path("/nonexistent")
        self._embedding_store = _FakeEmbeddingStore()

    def get_stats(self):
        return {"total_memories": len(self.stored), "overall_avg_q": 0.0}

    def store(self, *, embedding, action, action_type, context, outcome, initial_q):
        self.stored.append(context)
        return "id"

    def flush(self):
        self.flushed += 1

    def close(self):
        pass


class _FlakyEmbedder:
    def __init__(self, fail_on: set[int] | None = None):
        self.fail_on = fail_on
        self.n = 0

    def embed_text(self, text):
        self.n += 1
        if self.fail_on is None or self.n in self.fail_on:
            raise ConnectionError("embedder down")
        return np.ones(4, dtype=np.float32)


def _seeds(k: int) -> list[dict]:
    return [
        {
            "task": f"task {i}",
            "action": f"a{i}",
            "action_type": "routing",
            "context": {"task_description": f"task {i}", "is_seed": True},
            "category": "c",
            "initial_q": 0.5,
        }
        for i in range(k)
    ]


@pytest.fixture
def rig(monkeypatch):
    store = _FakeStore()
    holder: dict = {}
    monkeypatch.setattr(seed_loader_mod, "EpisodicStore", lambda *a, **k: store)
    monkeypatch.setattr(seed_loader_mod, "TaskEmbedder", lambda *a, **k: holder["embedder"])
    monkeypatch.setattr(seed_loader_mod, "_build_seed_records", lambda: _seeds(3))
    return store, holder


def test_total_embed_outage_raises(rig):
    store, holder = rig
    holder["embedder"] = _FlakyEmbedder(fail_on=None)
    with pytest.raises(seed_loader_mod.SeedLoadError) as exc:
        seed_loader_mod.seed_memory()
    stats = exc.value.stats
    assert (stats["loaded"], stats["failed"]) == (0, 3)
    assert len(stats["failures"]) == 3
    assert "ConnectionError" in str(exc.value)
    assert store.stored == []


def test_partial_failure_flushes_loaded_rows_then_raises(rig):
    store, holder = rig
    holder["embedder"] = _FlakyEmbedder(fail_on={2})
    with pytest.raises(seed_loader_mod.SeedLoadError) as exc:
        seed_loader_mod.seed_memory()
    assert (exc.value.stats["loaded"], exc.value.stats["failed"]) == (2, 1)
    assert exc.value.stats["failures"][0]["task"] == "task 1"
    # Loaded rows are flushed so SQLite and FAISS stay in step.
    assert store.flushed == 1 and store._embedding_store.saved == 1


def test_clean_run_returns_stats(rig):
    store, holder = rig
    holder["embedder"] = _FlakyEmbedder(fail_on=set())
    stats = seed_loader_mod.seed_memory()
    assert (stats["loaded"], stats["failed"], stats["failures"]) == (3, 0, [])


def test_cli_exits_nonzero_on_seed_failure(monkeypatch, capsys):
    def boom(**kwargs):
        raise seed_loader_mod.SeedLoadError(
            {"loaded": 0, "failed": 1, "skipped": 0, "failures": [{"task": "t", "error": "E: x"}]}
        )

    monkeypatch.setattr(seed_loader_mod, "seed_memory", boom)
    monkeypatch.setattr(sys, "argv", ["seed_loader.py", "--init"])
    with pytest.raises(SystemExit) as exc:
        seed_loader_mod.main()
    assert exc.value.code == 1
    assert "SEEDING FAILED" in capsys.readouterr().err
