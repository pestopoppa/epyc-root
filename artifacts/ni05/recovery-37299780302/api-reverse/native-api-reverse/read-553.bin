"""Every LIVE write site must produce the ONE canonical embedding text.

WHY THIS FILE EXISTS
--------------------
The 2026-07-27 contract (``memory_record.MemoryRecord.embedding_text()``) put
the embedding convention in one place, and the store was reseeded onto it. But
as of 2026-08-12 (handoff EPD-3-R2/R3) *no live writer called it*: the canonical
builder was reached only by the reseed tool and the degeneracy guard, while the
three writers that actually run re-spelled the convention and had each drifted:

* ``embedder.TaskEmbedder._serialize_task_ir`` — keyed on field PRESENCE not
  truthiness (so a TaskIR carrying ``priority: None`` emitted the literal
  ``priority:None``), no ``.strip()``, no length cap, and extra
  ``constraints:`` / ``input_types:`` segments.
* ``scripts/benchmark/seeding_injection._precompute_embedding`` — hard-coded
  ``type:chat`` for every suite, so a ``math`` row's vector described a
  convention its own stored context contradicted.
* ``seed_loader.seed_memory`` — embedded the raw task string with no prefix at
  all, which is what the 94 post-reseed ``seed`` rows carry.

So the format was guaranteed to re-drift at the next reseed. The pre-existing
``test_memory_record.py`` convention test cannot catch any of this: it compares
two ``MemoryRecord``s with identical fields, which is a property of the builder,
not of the writers.

The goldens below are the canonical text of REAL rows in the live store
(``orchestration/repl_memory/sessions/episodic.db``, read 2026-09-14), so this
file pins the writers to the format the corpus was actually published with — not
merely to each other.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts" / "benchmark") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

from orchestration.repl_memory import memory_record as memory_record_mod  # noqa: E402
from orchestration.repl_memory import seed_loader as seed_loader_mod  # noqa: E402
from orchestration.repl_memory.embedder import TaskEmbedder  # noqa: E402
from orchestration.repl_memory.memory_record import (  # noqa: E402
    embedding_text_for,
    record_from_legacy_context,
)
from scripts.benchmark import seeding_injection as seeding_injection_mod  # noqa: E402

# ---------------------------------------------------------------------------
# Goldens: stored contexts lifted verbatim from the live episodic store, with
# the canonical text the published vector was computed from.
# ---------------------------------------------------------------------------

# row 51aae08a-… shape: the live progress-log/legacy path (task_type + priority)
GOLDEN_LIVE_CONTEXT = {
    "record_version": 1,
    "task_type": "chat",
    "objective": "Answer in one sentence: what is 2+2?",
    "priority": "interactive",
    "source": "legacy",
}
GOLDEN_LIVE_TEXT = "type:chat | objective:Answer in one sentence: what is 2+2? | priority:interactive"

# row 531f4890-41e7-4f08-9eb6-37ee88c9ffc7: an eval-injected row. `task_type`
# is the SUITE (math), which is exactly what `type:chat` used to overwrite.
GOLDEN_INJECTED_OBJECTIVE = (
    "The sum of the digits of a two-digit number is $13.$ The difference between the number "
    "and the number with its digits reversed is $27.$ What is the sum of the original number "
    "and the number with its d"
)
GOLDEN_INJECTED_CONTEXT = {
    "record_version": 1,
    "task_type": "math",
    "objective": GOLDEN_INJECTED_OBJECTIVE,
    "priority": None,
    "source": "external",
    "metrics": {"question_id": "math500_Algebra_00452", "action_type": "routing"},
}
GOLDEN_INJECTED_TEXT = f"type:math | objective:{GOLDEN_INJECTED_OBJECTIVE}"

# row 80d975c1-… : a `seed` row with no task_type at all -> no `type:` segment.
GOLDEN_SEED_CONTEXT = {
    "record_version": 1,
    "task_type": None,
    "objective": "List files in a directory",
    "priority": None,
    "source": "seed",
    "metrics": {"category": "filesystem", "is_seed": True},
}
GOLDEN_SEED_TEXT = "objective:List files in a directory"

# row a30ba0aa-… shape: a `seed` row that DOES carry a task_type (routing seeds).
GOLDEN_SEED_TYPED_CONTEXT = {
    "record_version": 1,
    "task_type": "research",
    "objective": "Search for recent papers on transformer architectures",
    "priority": None,
    "source": "seed",
    "metrics": {"category": "routing", "mode": "repl", "is_seed": True},
}
GOLDEN_SEED_TYPED_TEXT = (
    "type:research | objective:Search for recent papers on transformer architectures"
)

ALL_GOLDENS = [
    (GOLDEN_LIVE_CONTEXT, GOLDEN_LIVE_TEXT),
    (GOLDEN_INJECTED_CONTEXT, GOLDEN_INJECTED_TEXT),
    (GOLDEN_SEED_CONTEXT, GOLDEN_SEED_TEXT),
    (GOLDEN_SEED_TYPED_CONTEXT, GOLDEN_SEED_TYPED_TEXT),
]


class TestGoldensPinTheStoredFormat:
    """The goldens must agree with the publish path, or they pin nothing."""

    @pytest.mark.parametrize("context,golden", ALL_GOLDENS)
    def test_canonical_builder_reproduces_the_stored_row_text(self, context, golden):
        assert record_from_legacy_context(context).embedding_text() == golden

    @pytest.mark.parametrize("context,golden", ALL_GOLDENS)
    def test_loose_field_entry_point_agrees_with_the_record(self, context, golden):
        assert (
            embedding_text_for(
                objective=context["objective"],
                task_type=context["task_type"],
                priority=context["priority"],
            )
            == golden
        )


class TestTaskIrWriter:
    """embedder._serialize_task_ir — the live query AND live write path."""

    @pytest.mark.parametrize("context,golden", ALL_GOLDENS)
    def test_serialize_task_ir_matches_golden(self, context, golden):
        embedder = TaskEmbedder.__new__(TaskEmbedder)  # no model/server needed
        task_ir = {
            "task_type": context["task_type"],
            "objective": context["objective"],
            "priority": context["priority"],
        }
        assert embedder._serialize_task_ir(task_ir) == golden

    def test_none_valued_keys_do_not_leak_literal_none(self):
        """The exact EPD-3-R2 drift: PRESENCE-keyed formatting."""
        embedder = TaskEmbedder.__new__(TaskEmbedder)
        text = embedder._serialize_task_ir(
            {"task_type": None, "objective": "do X", "priority": None}
        )
        assert text == "objective:do X"
        assert "None" not in text

    def test_extra_task_ir_fields_are_not_embedded(self):
        """constraints/input_types were a convention no other writer emitted."""
        embedder = TaskEmbedder.__new__(TaskEmbedder)
        text = embedder._serialize_task_ir(
            {
                "task_type": "coder",
                "objective": "do X",
                "constraints": ["fast", "safe"],
                "inputs": [{"type": "text"}],
            }
        )
        assert text == "type:coder | objective:do X"
        assert "constraints:" not in text and "input_types:" not in text

    def test_objective_is_stripped_and_capped(self):
        embedder = TaskEmbedder.__new__(TaskEmbedder)
        text = embedder._serialize_task_ir({"objective": "  spaced  "})
        assert text == "objective:spaced"
        long_text = embedder._serialize_task_ir({"objective": "x" * 5000})
        assert len(long_text) == memory_record_mod.EMBED_TEXT_MAX_CHARS


class _FakeResponse:
    status_code = 200

    def json(self):
        return {"embedding": [0.0, 1.0]}


class _CapturingClient:
    """Stands in for httpx.Client — records what text was sent to embed."""

    def __init__(self):
        self.sent: list[str] = []

    def post(self, url, json=None, timeout=None):  # noqa: A002 - httpx signature
        self.sent.append(json["content"])
        return _FakeResponse()


class TestInjectionWriter:
    """seeding_injection._precompute_embedding — the eval injection path."""

    def test_precompute_uses_the_rows_own_task_type(self):
        client = _CapturingClient()
        out = seeding_injection_mod._precompute_embedding(
            GOLDEN_INJECTED_OBJECTIVE, client, task_type="math"
        )
        assert out == [0.0, 1.0]
        assert client.sent == [GOLDEN_INJECTED_TEXT]
        # The defect this replaces:
        assert not client.sent[0].startswith("type:chat")

    def test_precompute_defaults_to_chat_like_the_api_side(self):
        """q_scorer.score_external_result uses `context["task_type"] or "chat"`."""
        client = _CapturingClient()
        seeding_injection_mod._precompute_embedding("do X", client)
        assert client.sent == ["type:chat | objective:do X"]

    def test_injection_text_matches_what_the_api_would_store(self):
        client = _CapturingClient()
        seeding_injection_mod._precompute_embedding(
            GOLDEN_INJECTED_OBJECTIVE, client, task_type="math"
        )
        assert client.sent[0] == record_from_legacy_context(
            GOLDEN_INJECTED_CONTEXT
        ).embedding_text()


class _FakeEmbeddingStore:
    count = 0

    def save(self):
        pass


class _FakeStore:
    """Minimal EpisodicStore stand-in; records the stored contexts."""

    def __init__(self, *args, **kwargs):
        self.stored: list[dict] = []
        self.sqlite_path = Path("/nonexistent/episodic.db")
        self.storage_dir = Path("/nonexistent")
        self._embedding_store = _FakeEmbeddingStore()

    def get_stats(self):
        return {"total_memories": len(self.stored), "overall_avg_q": 0.0}

    def store(self, *, embedding, action, action_type, context, outcome, initial_q):
        self.stored.append(context)
        return "fake-id"

    def flush(self):
        pass

    def close(self):
        pass


class _RecordingEmbedder:
    """Records every text handed to embed_text; never touches a model."""

    def __init__(self, *args, **kwargs):
        self.texts: list[str] = []

    def embed_text(self, text: str):
        self.texts.append(text)
        return np.ones(4, dtype=np.float32)


@pytest.fixture
def seeded(monkeypatch):
    """Run seed_memory against fakes and return (embedder, store)."""
    embedder = _RecordingEmbedder()
    store = _FakeStore()
    monkeypatch.setattr(seed_loader_mod, "TaskEmbedder", lambda *a, **k: embedder)
    monkeypatch.setattr(seed_loader_mod, "EpisodicStore", lambda *a, **k: store)
    return embedder, store


class TestSeedLoaderWriter:
    """seed_loader.seed_memory — the writer behind the `seed` rows."""

    def test_seed_rows_embed_the_canonical_text_not_the_raw_task(
        self, monkeypatch, seeded
    ):
        embedder, store = seeded
        monkeypatch.setattr(
            seed_loader_mod,
            "_build_seed_records",
            lambda: [
                {
                    "task": "List files in a directory",
                    "action": "list_dir('.')",
                    "action_type": "exploration",
                    "context": {
                        "task_description": "List files in a directory",
                        "category": "filesystem",
                        "is_seed": True,
                    },
                    "category": "filesystem",
                    "initial_q": 0.9,
                },
                {
                    "task": "Search for recent papers on transformer architectures",
                    "action": "worker_research",
                    "action_type": "routing",
                    "context": {
                        "task_description": (
                            "Search for recent papers on transformer architectures"
                        ),
                        "task_type": "research",
                        "category": "routing",
                        "mode": "repl",
                        "is_seed": True,
                    },
                    "category": "routing",
                    "initial_q": 0.85,
                },
            ],
        )
        stats = seed_loader_mod.seed_memory(force=False, init=False)

        assert stats["failed"] == 0, "the write loop swallows exceptions — guard it"
        assert stats["loaded"] == 2
        assert embedder.texts == [GOLDEN_SEED_TEXT, GOLDEN_SEED_TYPED_TEXT]
        # The defect this replaces: the raw task string with no prefix.
        assert "List files in a directory" not in embedder.texts

    def test_every_real_seed_record_embeds_its_own_canonical_text(self, seeded):
        """Run the FULL canonical seed set: no row may drift."""
        embedder, store = seeded
        stats = seed_loader_mod.seed_memory(force=False, init=False)

        assert stats["failed"] == 0
        # The canonical set is 94 rows (2026-09-14); a floor well below that
        # keeps the test non-vacuous without pinning the seed count.
        assert stats["loaded"] > 50, "seed set unexpectedly small — test is vacuous"
        assert len(embedder.texts) == len(store.stored) == stats["loaded"]
        for text, context in zip(embedder.texts, store.stored):
            assert text == record_from_legacy_context(context).embedding_text()
            assert text.startswith("type:") or text.startswith("objective:")


class TestWritersDelegateToTheCanonicalBuilder:
    """The drift guard: a writer that re-spells the convention fails HERE.

    Equality of output is necessary but not sufficient — a re-spelling that
    happens to agree today passes the golden tests and drifts on the next
    edit. These assertions are about the CALL, so the only way to pass is to
    delegate.
    """

    #: Every live entry point that turns task fields into embedder input.
    WRITER_MODULES = [
        (seeding_injection_mod, "embedding_text_for"),
    ]

    def test_writer_modules_hold_the_canonical_symbol(self):
        for module, name in self.WRITER_MODULES:
            assert getattr(module, name) is memory_record_mod.embedding_text_for, (
                f"{module.__name__}.{name} is not the canonical builder"
            )

    def test_embedder_module_holds_the_canonical_symbol(self):
        from orchestration.repl_memory import embedder as embedder_mod

        assert embedder_mod.embedding_text_for is memory_record_mod.embedding_text_for

    def test_serialize_task_ir_calls_the_canonical_builder(self, monkeypatch):
        from orchestration.repl_memory import embedder as embedder_mod

        seen: dict[str, object] = {}

        def spy(objective=None, task_type=None, priority=None):
            seen["args"] = (objective, task_type, priority)
            return "SENTINEL"

        monkeypatch.setattr(embedder_mod, "embedding_text_for", spy)
        embedder = TaskEmbedder.__new__(TaskEmbedder)
        out = embedder._serialize_task_ir(
            {"task_type": "coder", "objective": "do X", "priority": "batch"}
        )
        assert out == "SENTINEL"
        assert seen["args"] == ("do X", "coder", "batch")

    def test_precompute_embedding_calls_the_canonical_builder(self, monkeypatch):
        seen: dict[str, object] = {}

        def spy(objective=None, task_type=None, priority=None):
            seen["args"] = (objective, task_type, priority)
            return "SENTINEL"

        monkeypatch.setattr(seeding_injection_mod, "embedding_text_for", spy)
        client = _CapturingClient()
        seeding_injection_mod._precompute_embedding("do X", client, task_type="math")
        assert seen["args"] == ("do X", "math", None)
        assert client.sent == ["SENTINEL"]

    def test_seed_loader_calls_the_canonical_builder(self, monkeypatch, seeded):
        """seed_loader goes through MemoryRecord.embedding_text() directly."""
        embedder, _store = seeded
        monkeypatch.setattr(
            seed_loader_mod,
            "_build_seed_records",
            lambda: [
                {
                    "task": "t",
                    "action": "a",
                    "action_type": "routing",
                    "context": {"task_description": "t", "is_seed": True},
                    "category": "c",
                    "initial_q": 0.5,
                }
            ],
        )
        calls: list[str] = []
        original = memory_record_mod.MemoryRecord.embedding_text

        def spy(self):
            text = original(self)
            calls.append(text)
            return text

        monkeypatch.setattr(memory_record_mod.MemoryRecord, "embedding_text", spy)
        stats = seed_loader_mod.seed_memory(force=False, init=False)
        assert stats["failed"] == 0 and stats["loaded"] == 1
        assert calls, "seed_loader did not call MemoryRecord.embedding_text()"
        assert embedder.texts == calls

    def test_no_live_writer_hand_builds_the_convention(self):
        """No `objective:` f-string may survive outside the canonical builder."""
        roots = [
            REPO_ROOT / "orchestration",
            REPO_ROOT / "src",
            REPO_ROOT / "scripts" / "benchmark",
        ]
        canonical = REPO_ROOT / "orchestration" / "repl_memory" / "memory_record.py"
        offenders: list[str] = []
        for root in roots:
            for path in root.rglob("*.py"):
                if path == canonical or "deprecated" in path.parts:
                    continue
                for lineno, line in enumerate(
                    path.read_text(errors="replace").splitlines(), 1
                ):
                    # `objective:{` is the convention's own shape — an
                    # interpolation immediately after the segment key. Prose
                    # like `f"- objective: {x}"` (a prompt, not an embedding)
                    # has a space and is not this.
                    if "objective:{" in line:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
        assert not offenders, f"hand-built embedding text: {offenders}"
