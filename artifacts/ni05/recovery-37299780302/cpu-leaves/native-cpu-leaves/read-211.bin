"""Tests for corpus retrieval service — corpus-augmented prompt stuffing.

Covers CorpusRetriever singleton lifecycle, query/format logic,
graceful degradation, the extract_code_query helper, and v3 sharded format.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.services.corpus_retrieval import (
    CodeSnippet,
    CorpusConfig,
    CorpusRetriever,
    extract_code_query,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset singleton before each test."""
    CorpusRetriever.reset_instance()
    yield
    CorpusRetriever.reset_instance()


@pytest.fixture()
def mini_index(tmp_path: Path) -> Path:
    """Create a minimal corpus index for testing."""
    snippets = [
        {
            "file": "src/math.py",
            "start_line": 1,
            "code": "def calculate_loss(predictions, targets):\n    return sum((p - t) ** 2 for p, t in zip(predictions, targets))",
            "hash": "abc123",
        },
        {
            "file": "src/data.py",
            "start_line": 10,
            "code": "def load_dataset(path, split='train'):\n    with open(path) as f:\n        return json.load(f)\n    # Extra lines\n    pass",
            "hash": "def456",
        },
        {
            "file": "src/train.py",
            "start_line": 20,
            "code": "def train_model(model, data, epochs=10):\n    for epoch in range(epochs):\n        loss = calculate_loss(model(data), data.targets)\n        loss.backward()",
            "hash": "ghi789",
        },
    ]

    # Build a simple n-gram index with normalized tokens
    import re
    ngram_index: dict[str, list[int]] = {}
    for idx, snip in enumerate(snippets):
        raw_words = snip["code"].lower().split()
        words = [re.sub(r"[^a-z0-9_]", "", w) for w in raw_words]
        words = [w for w in words if w]
        for i in range(len(words) - 3):
            gram = " ".join(words[i:i + 4])
            if gram not in ngram_index:
                ngram_index[gram] = []
            if idx not in ngram_index[gram]:
                ngram_index[gram].append(idx)

    (tmp_path / "snippets.json").write_text(json.dumps(snippets))
    (tmp_path / "ngram_index.json").write_text(json.dumps(ngram_index))
    (tmp_path / "meta.json").write_text(json.dumps({
        "version": 1,
        "ngram_size": 4,
        "num_snippets": len(snippets),
        "num_ngrams": len(ngram_index),
    }))
    return tmp_path


# ── Disabled / Not Configured ─────────────────────────────────────────────


class TestReturnsEmptyWhenNotConfigured:
    """Retriever returns empty when not configured."""

    def test_disabled_config(self):
        config = CorpusConfig(enabled=False)
        retriever = CorpusRetriever(config)
        result = retriever.retrieve("def calculate_loss")
        assert result == []

    def test_default_config_is_disabled(self):
        config = CorpusConfig()
        assert config.enabled is False
        retriever = CorpusRetriever(config)
        assert retriever.retrieve("anything") == []

    def test_format_empty_snippets(self):
        retriever = CorpusRetriever(CorpusConfig())
        assert retriever.format_for_prompt([]) == ""


# ── Non-Lookup Role ───────────────────────────────────────────────────────


class TestReturnsEmptyForNonLookupRole:
    """build_corpus_context gates on lookup-enabled roles."""

    def test_build_corpus_context_disabled(self):
        from src.prompt_builders.builder import build_corpus_context

        # Default config has enabled=False
        result = build_corpus_context(
            role="architect_general",
            task_description="Design a system",
        )
        assert result == ""

    def test_build_corpus_context_requires_role_corpus_flag(
        self,
        mini_index: Path,
        monkeypatch,
        caplog,
    ):
        from src.prompt_builders import builder

        fake_registry = SimpleNamespace(
            get_corpus_config=lambda: {
                "enabled": True,
                "index_path": str(mini_index),
                "max_snippets": 3,
                "max_chars": 3000,
            },
            get_role=lambda _role: SimpleNamespace(
                acceleration=SimpleNamespace(corpus_retrieval=False)
            ),
        )
        monkeypatch.setattr(builder, "_get_corpus_registry", lambda: fake_registry)

        with caplog.at_level(logging.DEBUG, logger="src.prompt_builders.builder"):
            result = builder.build_corpus_context(
                role="coder_escalation",
                task_description="return sum((p - t) ** 2 for predictions targets",
                task_id="task-1",
                request_id="req-1",
            )

        assert result == ""
        event = caplog.records[-1].corpus_retrieval
        assert event["status"] == "skipped"
        assert event["reason"] == "role_disabled"
        assert event["role"] == "coder_escalation"
        assert event["task_id"] == "task-1"
        assert event["request_id"] == "req-1"

    def test_build_corpus_context_uses_enabled_role_registry_config(
        self,
        mini_index: Path,
        monkeypatch,
        caplog,
    ):
        from src.prompt_builders import builder

        fake_registry = SimpleNamespace(
            get_corpus_config=lambda: {
                "enabled": True,
                "index_path": str(mini_index),
                "max_snippets": 3,
                "max_chars": 3000,
            },
            get_role=lambda _role: SimpleNamespace(
                acceleration=SimpleNamespace(corpus_retrieval=True)
            ),
        )
        monkeypatch.setattr(builder, "_get_corpus_registry", lambda: fake_registry)

        with caplog.at_level(logging.INFO, logger="src.prompt_builders.builder"):
            result = builder.build_corpus_context(
                role="coder_escalation",
                task_description=(
                    "return sum((p - t) ** 2 for p, t in zip(predictions, targets)"
                ),
                task_id="task-2",
            )

        assert "<reference_code" in result
        assert "calculate_loss" in result
        event = caplog.records[-1].corpus_retrieval
        assert event["status"] == "injected"
        assert event["snippet_count"] >= 1
        assert event["context_chars"] == len(result)
        assert event["query_ngrams"] > 0
        assert event["index_path"] == str(mini_index)

    def test_build_corpus_context_allows_task_scoped_worker_code_task(
        self,
        mini_index: Path,
        monkeypatch,
        caplog,
    ):
        from src.prompt_builders import builder

        fake_registry = SimpleNamespace(
            get_corpus_config=lambda: {
                "enabled": True,
                "index_path": str(mini_index),
                "max_snippets": 3,
                "max_chars": 3000,
                "task_scoped_roles": ["worker_general"],
            },
            get_role=lambda _role: SimpleNamespace(
                acceleration=SimpleNamespace(corpus_retrieval=False)
            ),
        )
        monkeypatch.setattr(builder, "_get_corpus_registry", lambda: fake_registry)

        with caplog.at_level(logging.INFO, logger="src.prompt_builders.builder"):
            result = builder.build_corpus_context(
                role="worker_general",
                task_description=(
                    "Implement Python code that returns sum((p - t) ** 2 "
                    "for p, t in zip(predictions, targets)"
                ),
                task_id="task-worker-code",
            )

        assert "<reference_code" in result
        assert "calculate_loss" in result
        event = caplog.records[-1].corpus_retrieval
        assert event["status"] == "injected"
        assert event["role"] == "worker_general"
        assert event["role_corpus_scope"] == "code_task"
        assert event["corpus_task_scope"] == "code"

    def test_build_corpus_context_skips_task_scoped_worker_non_code_task(
        self,
        mini_index: Path,
        monkeypatch,
        caplog,
    ):
        from src.prompt_builders import builder

        fake_registry = SimpleNamespace(
            get_corpus_config=lambda: {
                "enabled": True,
                "index_path": str(mini_index),
                "max_snippets": 3,
                "max_chars": 3000,
                "task_scoped_roles": ["worker_general"],
            },
            get_role=lambda _role: SimpleNamespace(
                acceleration=SimpleNamespace(corpus_retrieval=False)
            ),
        )
        monkeypatch.setattr(builder, "_get_corpus_registry", lambda: fake_registry)

        with caplog.at_level(logging.DEBUG, logger="src.prompt_builders.builder"):
            result = builder.build_corpus_context(
                role="worker_general",
                task_description="Summarize the governance tradeoffs in plain English",
                task_id="task-worker-general",
            )

        assert result == ""
        event = caplog.records[-1].corpus_retrieval
        assert event["status"] == "skipped"
        assert event["reason"] == "task_scope_disabled"
        assert event["role"] == "worker_general"
        assert event["corpus_task_scope"] == "code"

    def test_build_corpus_context_suppresses_slow_retrieval(
        self,
        mini_index: Path,
        monkeypatch,
        caplog,
    ):
        from src.prompt_builders import builder

        fake_registry = SimpleNamespace(
            get_corpus_config=lambda: {
                "enabled": True,
                "index_path": str(mini_index),
                "max_snippets": 3,
                "max_chars": 3000,
                "slow_query_ms": 0.000001,
            },
            get_role=lambda _role: SimpleNamespace(
                acceleration=SimpleNamespace(corpus_retrieval=True)
            ),
        )
        monkeypatch.setattr(builder, "_get_corpus_registry", lambda: fake_registry)

        with caplog.at_level(logging.WARNING, logger="src.prompt_builders.builder"):
            result = builder.build_corpus_context(
                role="coder_escalation",
                task_description=(
                    "return sum((p - t) ** 2 for p, t in zip(predictions, targets)"
                ),
            )

        assert result == ""
        event = caplog.records[-1].corpus_retrieval
        assert event["status"] == "slow_query"
        assert event["reason"] == "retrieval_latency_exceeded"
        assert event["snippet_count"] >= 1


# ── Format Respects Max Chars ─────────────────────────────────────────────


class TestFormatRespectsMaxChars:
    """format_for_prompt truncates to max_chars budget."""

    def test_respects_budget(self):
        config = CorpusConfig(enabled=True, max_chars=200)
        retriever = CorpusRetriever(config)

        snippets = [
            CodeSnippet(code="x" * 500, file="a.py", start_line=1, score=0.9),
            CodeSnippet(code="y" * 500, file="b.py", start_line=1, score=0.8),
        ]
        result = retriever.format_for_prompt(snippets)
        assert len(result) <= 300  # Allow some overhead for delimiters
        assert "<reference_code" in result
        assert "</reference_code>" in result

    def test_single_snippet_under_budget(self):
        config = CorpusConfig(enabled=True, max_chars=3000)
        retriever = CorpusRetriever(config)

        snippets = [
            CodeSnippet(code="print('hello')", file="test.py", start_line=1, score=0.9),
        ]
        result = retriever.format_for_prompt(snippets)
        assert "print('hello')" in result
        assert "test.py:1" in result


# ── Deduplication ─────────────────────────────────────────────────────────


class TestDeduplicatesNearIdentical:
    """Retriever deduplicates snippets with same hash."""

    def test_dedup_by_hash(self, mini_index: Path):
        config = CorpusConfig(
            enabled=True,
            index_path=str(mini_index),
            min_score=0.0,
            max_snippets=10,
        )
        retriever = CorpusRetriever(config)

        # All snippets should be unique (different hashes in fixture)
        snippets = retriever.retrieve("def calculate_loss predictions targets")
        hashes = [s.hash for s in snippets if s.hash]
        assert len(hashes) == len(set(hashes))


# ── Graceful Degradation ─────────────────────────────────────────────────


class TestGracefulWhenSoftmatchaNotInstalled:
    """Retriever degrades gracefully with missing dependencies."""

    def test_missing_index(self):
        config = CorpusConfig(
            enabled=True,
            index_path="/nonexistent/path/to/index",
        )
        retriever = CorpusRetriever(config)
        result = retriever.retrieve("anything")
        assert result == []

    def test_corrupted_index(self, tmp_path: Path):
        (tmp_path / "snippets.json").write_text("not valid json {{{")
        (tmp_path / "ngram_index.json").write_text("{}")
        (tmp_path / "meta.json").write_text('{"version": 1, "ngram_size": 4}')

        config = CorpusConfig(enabled=True, index_path=str(tmp_path))
        retriever = CorpusRetriever(config)
        result = retriever.retrieve("test query")
        assert result == []

    def test_build_corpus_context_import_error(self):
        """build_corpus_context handles ImportError gracefully."""
        from src.prompt_builders.builder import build_corpus_context

        with patch.dict("sys.modules", {"src.services.corpus_retrieval": None}):
            # Should return "" when module can't be imported
            result = build_corpus_context(
                role="frontdoor",
                task_description="test",
            )
            assert result == ""


# ── Singleton Behavior ────────────────────────────────────────────────────


class TestSingleton:
    """CorpusRetriever singleton lifecycle."""

    def test_same_instance(self):
        a = CorpusRetriever.get_instance()
        b = CorpusRetriever.get_instance()
        assert a is b

    def test_reset_creates_new(self):
        a = CorpusRetriever.get_instance()
        CorpusRetriever.reset_instance()
        b = CorpusRetriever.get_instance()
        assert a is not b


# ── Retrieval Quality ─────────────────────────────────────────────────────


class TestRetrieval:
    """End-to-end retrieval from mini index."""

    def test_retrieves_matching_snippets(self, mini_index: Path):
        config = CorpusConfig(
            enabled=True,
            index_path=str(mini_index),
            min_score=0.0,
        )
        retriever = CorpusRetriever(config)
        # Use text that overlaps with snippet content to produce matching 4-grams
        snippets = retriever.retrieve(
            "return sum((p - t) ** 2 for p, t in zip(predictions, targets))"
        )
        assert len(snippets) > 0
        # First result should be the calculate_loss snippet
        assert "calculate_loss" in snippets[0].code

    def test_empty_query_returns_empty(self, mini_index: Path):
        config = CorpusConfig(
            enabled=True,
            index_path=str(mini_index),
        )
        retriever = CorpusRetriever(config)
        result = retriever.retrieve("a")  # Too short for 4-grams
        assert result == []

    def test_scores_are_descending(self, mini_index: Path):
        config = CorpusConfig(
            enabled=True,
            index_path=str(mini_index),
            min_score=0.0,
            max_snippets=10,
        )
        retriever = CorpusRetriever(config)
        snippets = retriever.retrieve("def calculate_loss predictions targets return sum")
        if len(snippets) > 1:
            for i in range(len(snippets) - 1):
                assert snippets[i].score >= snippets[i + 1].score


# ── extract_code_query ────────────────────────────────────────────────────


class TestExtractCodeQuery:
    """Code query extraction from task descriptions."""

    def test_strips_instruction_words(self):
        result = extract_code_query("Please implement a function to calculate loss")
        assert "please" not in result
        assert "implement" not in result
        assert "calculate" in result or "loss" in result

    def test_keeps_snake_case(self):
        result = extract_code_query("Write a calculate_loss function")
        assert "calculate_loss" in result

    def test_keeps_camel_case(self):
        result = extract_code_query("Fix the calculateLoss method")
        assert "calculateloss" in result

    def test_empty_after_stripping_falls_back(self):
        result = extract_code_query("Please write the code")
        # Should fall back to truncated lowercase
        assert len(result) > 0

    def test_preserves_identifiers(self):
        result = extract_code_query("Update the REPLEnvironment class")
        assert "replenvironment" in result


# ── V3 Sharded Format ─────────────────────────────────────────────────


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", token.lower())


def _extract_ngrams(text: str, n: int = 4) -> list[str]:
    raw_words = text.lower().split()
    words = [_normalize_token(w) for w in raw_words]
    words = [w for w in words if w]
    if len(words) < n:
        return []
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def _gram_to_shard(gram: str, num_shards: int) -> int:
    h = hashlib.md5(gram.encode()).digest()
    return int.from_bytes(h[:4], "little") % num_shards


@pytest.fixture()
def sharded_index(tmp_path: Path) -> Path:
    """Create a mini v3 sharded corpus index for testing."""
    num_shards = 4  # small for tests
    snippets_data = [
        {
            "code": "def calculate_loss(predictions, targets):\n    return sum((p - t) ** 2 for p, t in zip(predictions, targets))",
            "source": "src/math.py",
            "hash": "abc123",
            "language": "python",
        },
        {
            "code": "def load_dataset(path, split='train'):\n    with open(path) as f:\n        return json.load(f)\n    # Extra lines\n    pass",
            "source": "src/data.py",
            "hash": "def456",
            "language": "python",
        },
        {
            "code": "def train_model(model, data, epochs=10):\n    for epoch in range(epochs):\n        loss = calculate_loss(model(data), data.targets)\n        loss.backward()",
            "source": "src/train.py",
            "hash": "ghi789",
            "language": "python",
        },
    ]

    # Create snippets.db
    snippets_db = tmp_path / "snippets.db"
    conn = sqlite3.connect(str(snippets_db))
    conn.execute("""CREATE TABLE snippets (
        id INTEGER PRIMARY KEY, code TEXT NOT NULL,
        source TEXT DEFAULT '', hash TEXT NOT NULL, language TEXT DEFAULT ''
    )""")
    conn.execute("CREATE INDEX idx_snippets_hash ON snippets(hash)")
    for i, s in enumerate(snippets_data):
        conn.execute(
            "INSERT INTO snippets (id, code, source, hash, language) VALUES (?, ?, ?, ?, ?)",
            (i, s["code"], s["source"], s["hash"], s["language"]),
        )
    conn.commit()
    conn.close()

    # Create shard DBs
    shard_conns = []
    for i in range(num_shards):
        shard_path = tmp_path / f"shard_{i:02d}.db"
        sc = sqlite3.connect(str(shard_path))
        sc.execute("CREATE TABLE ngrams (gram TEXT NOT NULL, snippet_id INTEGER NOT NULL)")
        shard_conns.append(sc)

    # Populate ngrams across shards
    for sid, s in enumerate(snippets_data):
        grams = _extract_ngrams(s["code"])
        for gram in grams:
            shard_id = _gram_to_shard(gram, num_shards)
            shard_conns[shard_id].execute(
                "INSERT INTO ngrams (gram, snippet_id) VALUES (?, ?)", (gram, sid),
            )

    # Create indexes and close
    for sc in shard_conns:
        sc.execute("CREATE INDEX idx_ngrams_gram ON ngrams(gram)")
        sc.commit()
        sc.close()

    # Write meta.json
    (tmp_path / "meta.json").write_text(json.dumps({
        "version": 3,
        "format": "sharded_sqlite",
        "ngram_size": 4,
        "num_shards": num_shards,
        "num_snippets": len(snippets_data),
    }))
    return tmp_path


class TestShardedRetrieval:
    """End-to-end retrieval from v3 sharded index."""

    def test_auto_detects_sharded_format(self, sharded_index: Path):
        config = CorpusConfig(enabled=True, index_path=str(sharded_index), min_score=0.0)
        retriever = CorpusRetriever(config)
        retriever._ensure_loaded()
        assert retriever._format == "sharded_sqlite"
        assert retriever._num_shards == 4

    def test_retrieves_matching_snippets(self, sharded_index: Path):
        config = CorpusConfig(enabled=True, index_path=str(sharded_index), min_score=0.0)
        retriever = CorpusRetriever(config)
        snippets = retriever.retrieve(
            "return sum((p - t) ** 2 for p, t in zip(predictions, targets)"
        )
        assert len(snippets) > 0
        assert "calculate_loss" in snippets[0].code

    def test_scores_descending(self, sharded_index: Path):
        config = CorpusConfig(
            enabled=True, index_path=str(sharded_index), min_score=0.0, max_snippets=10,
        )
        retriever = CorpusRetriever(config)
        snippets = retriever.retrieve("def calculate_loss predictions targets return sum")
        if len(snippets) > 1:
            for i in range(len(snippets) - 1):
                assert snippets[i].score >= snippets[i + 1].score

    def test_dedup_by_hash(self, sharded_index: Path):
        config = CorpusConfig(
            enabled=True, index_path=str(sharded_index), min_score=0.0, max_snippets=10,
        )
        retriever = CorpusRetriever(config)
        snippets = retriever.retrieve("def calculate_loss predictions targets")
        hashes = [s.hash for s in snippets if s.hash]
        assert len(hashes) == len(set(hashes))

    def test_empty_query_returns_empty(self, sharded_index: Path):
        config = CorpusConfig(enabled=True, index_path=str(sharded_index))
        retriever = CorpusRetriever(config)
        assert retriever.retrieve("a") == []

    def test_missing_shard_fails_gracefully(self, tmp_path: Path):
        """If a shard file is missing, loading fails gracefully."""
        (tmp_path / "shard_00.db").write_text("")  # exists but no shard_01, etc.
        (tmp_path / "meta.json").write_text(json.dumps({
            "version": 3, "num_shards": 4, "ngram_size": 4,
        }))
        config = CorpusConfig(enabled=True, index_path=str(tmp_path))
        retriever = CorpusRetriever(config)
        assert retriever.retrieve("anything") == []

    def test_format_for_prompt_works(self, sharded_index: Path):
        config = CorpusConfig(
            enabled=True, index_path=str(sharded_index), min_score=0.0,
        )
        retriever = CorpusRetriever(config)
        snippets = retriever.retrieve(
            "return sum((p - t) ** 2 for p, t in zip(predictions, targets)"
        )
        result = retriever.format_for_prompt(snippets)
        assert "<reference_code" in result


# ── Retrieval Diagnostics ───────────────────────────────────────────────


class TestRetrievalDiagnostics:
    """RetrievalDiagnostics metadata populated on every retrieve() call."""

    def test_diagnostics_on_disabled_retrieval(self):
        config = CorpusConfig(enabled=False)
        retriever = CorpusRetriever(config)
        retriever.retrieve("anything")
        diag = retriever.last_diagnostics
        assert diag is not None
        assert diag.failure_reason == "disabled"
        assert diag.loaded is False

    def test_diagnostics_on_missing_index(self):
        config = CorpusConfig(enabled=True, index_path="/nonexistent/path")
        retriever = CorpusRetriever(config)
        retriever.retrieve("anything")
        diag = retriever.last_diagnostics
        assert diag is not None
        assert diag.failure_reason in ("load_failed", "no_index")
        assert diag.loaded is False

    def test_diagnostics_on_successful_retrieval(self, mini_index: Path):
        config = CorpusConfig(
            enabled=True, index_path=str(mini_index), min_score=0.0,
        )
        retriever = CorpusRetriever(config)
        snippets = retriever.retrieve(
            "return sum((p - t) ** 2 for p, t in zip(predictions, targets)"
        )
        diag = retriever.last_diagnostics
        assert diag is not None
        assert diag.loaded is True
        assert diag.format == "json"
        assert diag.query_ngrams > 0
        assert diag.results_returned == len(snippets)
        assert diag.elapsed_ms >= 0.0
        assert diag.failure_reason == ""

    def test_diagnostics_on_sharded_retrieval(self, sharded_index: Path):
        config = CorpusConfig(
            enabled=True, index_path=str(sharded_index), min_score=0.0,
        )
        retriever = CorpusRetriever(config)
        snippets = retriever.retrieve(
            "return sum((p - t) ** 2 for p, t in zip(predictions, targets)"
        )
        diag = retriever.last_diagnostics
        assert diag is not None
        assert diag.loaded is True
        assert diag.format == "sharded_sqlite"
        assert diag.shards_queried > 0
        assert diag.shards_failed == 0
        assert diag.results_returned == len(snippets)

    def test_shard_query_error_populates_diagnostics(self, sharded_index: Path):
        """When a shard query raises, shards_failed is incremented."""
        config = CorpusConfig(
            enabled=True, index_path=str(sharded_index), min_score=0.0,
        )
        retriever = CorpusRetriever(config)
        retriever._ensure_loaded()
        assert retriever._format == "sharded_sqlite"

        # Corrupt one shard by closing its connection
        for i, conn in enumerate(retriever._shard_conns):
            if conn is not None:
                conn.close()
                retriever._shard_conns[i] = sqlite3.connect(":memory:")
                # memory db has no ngrams table — queries will raise
                break

        retriever.retrieve("def calculate_loss predictions targets return sum")
        diag = retriever.last_diagnostics
        assert diag is not None
        assert diag.shards_failed >= 1

    def test_shard_unavailable_populates_diagnostics(self, sharded_index: Path):
        """When a shard connection is None, shards_unavailable is incremented."""
        config = CorpusConfig(
            enabled=True, index_path=str(sharded_index), min_score=0.0,
        )
        retriever = CorpusRetriever(config)
        retriever._ensure_loaded()

        # Set one shard to None (simulating unavailable)
        for i, conn in enumerate(retriever._shard_conns):
            if conn is not None:
                conn.close()
                retriever._shard_conns[i] = None
                break

        retriever.retrieve("def calculate_loss predictions targets return sum")
        diag = retriever.last_diagnostics
        assert diag is not None
        assert diag.shards_unavailable >= 1
