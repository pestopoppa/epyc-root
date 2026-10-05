"""Tests for the offline corpus health probe CLI."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

import pytest

from scripts.benchmark import corpus_health_probe as probe


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", token.lower())


def _extract_ngrams(text: str, n: int = 4) -> list[str]:
    words = [_normalize_token(word) for word in text.split()]
    words = [word for word in words if word]
    if len(words) < n:
        return []
    return [" ".join(words[idx : idx + n]) for idx in range(len(words) - n + 1)]


def _gram_to_shard(gram: str, num_shards: int) -> int:
    digest = hashlib.md5(gram.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little") % num_shards


@pytest.fixture()
def sharded_index(tmp_path: Path) -> Path:
    snippets = [
        {
            "code": "def calculate_loss predictions targets return sum squared_error",
            "source": "src/math.py",
            "hash": "abc123",
        },
        {
            "code": "def load_dataset path split train return json load",
            "source": "src/data.py",
            "hash": "def456",
        },
        {
            "code": "def train_model model data epochs loss calculate_loss",
            "source": "src/train.py",
            "hash": "ghi789",
        },
    ]

    conn = sqlite3.connect(str(tmp_path / "snippets.db"))
    conn.execute(
        "CREATE TABLE snippets (id INTEGER PRIMARY KEY, code TEXT NOT NULL, source TEXT DEFAULT '', hash TEXT NOT NULL)"
    )
    for idx, snippet in enumerate(snippets):
        conn.execute(
            "INSERT INTO snippets (id, code, source, hash) VALUES (?, ?, ?, ?)",
            (idx, snippet["code"], snippet["source"], snippet["hash"]),
        )
    conn.commit()
    conn.close()

    shard_conns: list[sqlite3.Connection] = []
    num_shards = 2
    for shard_idx in range(num_shards):
        shard_conn = sqlite3.connect(str(tmp_path / f"shard_{shard_idx:02d}.db"))
        shard_conn.execute("CREATE TABLE ngrams (gram TEXT NOT NULL, snippet_id INTEGER NOT NULL)")
        shard_conns.append(shard_conn)

    for sid, snippet in enumerate(snippets):
        for gram in _extract_ngrams(snippet["code"]):
            shard_idx = _gram_to_shard(gram, num_shards)
            shard_conns[shard_idx].execute(
                "INSERT INTO ngrams (gram, snippet_id) VALUES (?, ?)",
                (gram, sid),
            )

    for shard_conn in shard_conns:
        shard_conn.commit()
        shard_conn.close()

    (tmp_path / "meta.json").write_text(
        json.dumps({"version": 3, "format": "sharded_sqlite", "ngram_size": 4, "num_shards": num_shards}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def matching_queries() -> list[probe.ProbeQuery]:
    return [
        probe.ProbeQuery(
            id="loss",
            query="def calculate_loss predictions targets",
        ),
        probe.ProbeQuery(
            id="dataset",
            query="def load_dataset path split train",
        ),
        probe.ProbeQuery(
            id="train",
            query="def train_model model data epochs",
        ),
    ]


def test_run_probe_reports_latency_and_candidate_counts(
    sharded_index: Path,
    matching_queries: list[probe.ProbeQuery],
) -> None:
    summary = probe.run_probe(
        index_path=sharded_index,
        queries=matching_queries,
        min_score=0.0,
        p95_threshold_ms=500.0,
        min_snippets_per_query=1.0,
    )

    assert summary.query_count == 3
    assert summary.failure_count == 0
    assert summary.total_snippets_returned > 0
    assert summary.avg_snippets_returned >= 1.0
    assert summary.p50_latency_ms is not None
    assert summary.p95_latency_ms is not None
    assert summary.p95_latency_ms >= summary.p50_latency_ms
    assert summary.candidate_count_total is not None
    assert summary.candidate_count_total > 0
    assert summary.candidate_count_sampled_queries == 3
    assert summary.failure_reasons == {}
    assert summary.usable_for_online_prompt_injection is True
    assert all(record.format == "sharded_sqlite" for record in summary.records)
    assert all(record.failure_reason == "" for record in summary.records)
    assert any(record.candidate_count is not None for record in summary.records)


def test_run_probe_disabled_records_reason(
    matching_queries: list[probe.ProbeQuery],
) -> None:
    summary = probe.run_probe(
        index_path=Path("/nonexistent/index"),
        queries=matching_queries[:1],
        enabled=False,
        p95_threshold_ms=500.0,
        min_snippets_per_query=0.0,
    )

    assert summary.failure_count == 1
    assert summary.failure_reasons == {"disabled": 1}
    assert summary.usable_for_online_prompt_injection is False
    assert summary.records[0].failure_reason == "disabled"
    assert summary.records[0].snippets_returned == 0


def test_main_json_and_dry_run(tmp_path: Path, capsys) -> None:
    query_file = tmp_path / "queries.jsonl"
    query_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "loss",
                        "query": "def calculate_loss predictions targets",
                    }
                ),
                json.dumps(
                    {
                        "id": "dataset",
                        "query": "def load_dataset path split train",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    rc = probe.main(
        [
            "--index-path",
            str(tmp_path / "missing-index"),
            "--queries-file",
            str(query_file),
            "--limit",
            "1",
            "--dry-run",
            "--json",
        ]
    )

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True
    assert data["query_count"] == 1
    assert data["usable_for_online_prompt_injection"] is False
