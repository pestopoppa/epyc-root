from __future__ import annotations

import asyncio
import inspect
import json
import sqlite3

import numpy as np
import pytest

from scripts.maintenance import reseed_episodic_store as reseed


class _Embedder:
    def __init__(self, values: np.ndarray):
        self.values = values

    def embed_batch(self, _texts: list[str]) -> np.ndarray:
        return self.values


def test_checked_batch_prefers_parallel_pool() -> None:
    values = np.ones((2, 1024), dtype=np.float32)

    class Parallel:
        def embed_batch_sync(self, texts: list[str]) -> np.ndarray:
            assert texts == ["a", "b"]
            return values

    embedder = _Embedder(np.zeros((2, 1024), dtype=np.float32))
    embedder._parallel_client = Parallel()

    result = reseed._checked_batch(embedder, ["a", "b"])

    assert np.allclose(np.linalg.norm(result, axis=1), 1.0)


def test_balanced_batch_round_robins_servers() -> None:
    calls: list[tuple[str, str]] = []

    class Parallel:
        config = type("Config", (), {"server_urls": ["a", "b", "c"]})()

        async def _get_client(self):
            return object()

        async def _embed_single_server(self, _client, url: str, text: str):
            calls.append((url, text))
            return np.ones(1024, dtype=np.float32)

        async def close(self) -> None:
            await asyncio.sleep(0)

    result = reseed._balanced_parallel_batch(Parallel(), ["x", "y", "z", "w"])

    assert result.shape == (4, 1024)
    assert calls == [("a", "x"), ("b", "y"), ("c", "z"), ("a", "w")]


def _write_persisted_state(
    tmp_path, id_map: list[str], rows: list[tuple[str, int | None]]
) -> None:
    import faiss

    index = faiss.IndexFlatIP(1024)
    if id_map:
        index.add(np.ones((len(id_map), 1024), dtype=np.float32))
    faiss.write_index(index, str(tmp_path / "embeddings.faiss"))
    np.save(tmp_path / "id_map.npy", np.array(id_map, dtype=object), allow_pickle=True)
    con = sqlite3.connect(tmp_path / "episodic.db")
    try:
        con.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, embedding_idx INTEGER)")
        con.executemany("INSERT INTO memories VALUES (?, ?)", rows)
        con.commit()
    finally:
        con.close()


def test_checked_batch_normalizes_and_rejects_invalid_vectors() -> None:
    values = np.ones((2, 1024), dtype=np.float32)
    result = reseed._checked_batch(_Embedder(values), ["a", "b"])
    assert result.shape == (2, 1024)
    assert np.allclose(np.linalg.norm(result, axis=1), 1.0)

    with pytest.raises(reseed.ReseedVerificationError, match="zero vector"):
        reseed._checked_batch(_Embedder(np.zeros((1, 1024), dtype=np.float32)), ["a"])
    with pytest.raises(reseed.ReseedVerificationError, match="shape"):
        reseed._checked_batch(_Embedder(np.ones((1, 3), dtype=np.float32)), ["a"])


def test_strict_embedder_disables_every_semantic_fallback() -> None:
    embedder = reseed._strict_embedder()
    try:
        assert embedder.config.use_fallback is False
        assert embedder.config.allow_subprocess is False
        assert embedder._parallel_client.config.use_fallback is False
    finally:
        embedder.close()


def test_strict_embedder_accepts_temporary_maintenance_fleet(monkeypatch) -> None:
    monkeypatch.setenv(
        "RESEED_EMBEDDER_URLS",
        "http://127.0.0.1:18090,http://127.0.0.1:18091",
    )
    monkeypatch.setenv("RESEED_BATCH_SIZE", "32")

    embedder = reseed._strict_embedder()
    try:
        assert embedder._parallel_client.config.server_urls == [
            "http://127.0.0.1:18090",
            "http://127.0.0.1:18091",
        ]
        assert embedder._parallel_client.config.use_fallback is False
        assert reseed._batch_size() == 32
    finally:
        embedder.close()


@pytest.mark.parametrize("value", ["0", "-1", "not-an-integer"])
def test_reseed_batch_size_rejects_invalid_values(monkeypatch, value: str) -> None:
    monkeypatch.setenv("RESEED_BATCH_SIZE", value)

    with pytest.raises(ValueError, match="RESEED_BATCH_SIZE"):
        reseed._batch_size()


def test_strict_embedder_fails_when_every_server_path_fails(monkeypatch) -> None:
    embedder = reseed._strict_embedder()
    monkeypatch.setattr(
        embedder._parallel_client,
        "embed_sync",
        lambda _text: (_ for _ in ()).throw(RuntimeError("down")),
    )
    monkeypatch.setattr(embedder, "_check_server", lambda: False)
    try:
        with pytest.raises(RuntimeError, match="fallback disabled"):
            embedder.embed_text("must not become a hash embedding")
    finally:
        embedder.close()


def test_faiss_publication_precedes_sqlite_commit() -> None:
    source = inspect.getsource(reseed.reseed)
    assert source.index('ix_tmp.replace(sessions / "embeddings.faiss")') < source.index(
        "con.commit()"
    )
    assert source.index("con.commit()") < source.index("verify_persisted")


def test_apply_rejects_partial_limit_before_any_embedding(tmp_path) -> None:
    with pytest.raises(ValueError, match="--limit is unsafe"):
        reseed.reseed(tmp_path, apply=True, limit=1)


def test_verify_persisted_accepts_deindexed_telemetry_rows(tmp_path) -> None:
    _write_persisted_state(tmp_path, ["task-1"], [("task-1", 0), ("telemetry-1", None)])

    assert reseed.verify_persisted(tmp_path, {"task-1"}) == {
        "ntotal": 1,
        "id_map_len": 1,
        "desync": 0,
        "bad": 0,
    }


@pytest.mark.parametrize(
    ("id_map", "rows", "expected_ids", "match"),
    [
        (["task-1"], [("task-1", 0), ("telemetry-1", 0)], {"task-1"}, "non-task"),
        (["task-1"], [("task-1", 0)], {"missing-task"}, "membership"),
        (["task-1"], [("task-1", -1)], {"task-1"}, "do not resolve"),
        (["task-1"], [("task-1", 1)], {"task-1"}, "do not resolve"),
        (
            ["task-2", "task-1"],
            [("task-1", 0), ("task-2", 1)],
            {"task-1", "task-2"},
            "do not resolve",
        ),
        (["task-1", "task-1"], [("task-1", 0)], {"task-1"}, "duplicate"),
    ],
)
def test_verify_persisted_rejects_invalid_membership_or_pointers(
    tmp_path, id_map, rows, expected_ids, match
) -> None:
    _write_persisted_state(tmp_path, id_map, rows)

    with pytest.raises(reseed.ReseedVerificationError, match=match):
        reseed.verify_persisted(tmp_path, expected_ids)


def test_cosine_probe_selects_only_task_rows() -> None:
    from scripts.maintenance.verify_episodic_reseed_cosine import _task_rows

    rows = [
        ("task-1", 0, json.dumps({"objective": "build a scheduler"})),
        ("telemetry-1", None, json.dumps({"event_type": "tool_call"})),
    ]
    assert _task_rows(rows) == [rows[0]]
