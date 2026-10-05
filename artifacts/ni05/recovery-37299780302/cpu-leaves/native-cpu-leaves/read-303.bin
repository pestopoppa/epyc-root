"""Tests for the episodic store integrity gate.

Each test builds a store exhibiting one of the defects measured during the
2026-07-05 -> 2026-07-27 incident and asserts the corresponding check fires. The
point is not to test the happy path — a monitor that only ever passes is
indistinguishable from no monitor, which is exactly what we had for 22 days.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import faiss
import numpy as np
import pytest

CHECKER = Path(__file__).resolve().parents[2] / "scripts/maintenance/check_episodic_integrity.py"


def _unit_rows(n: int, dim: int = 16, *, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal((n, dim)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def build_store(
    d: Path,
    *,
    n: int = 40,
    id_map_len: int | None = None,
    idx_shift: int = 0,
    collapse: bool = False,
) -> Path:
    """Write a minimal but structurally faithful store.

    id_map_len < n reproduces the index-ahead desync; idx_shift reproduces the
    mis-resolving mapping; collapse reproduces distinct objectives sharing a
    vector.
    """
    d.mkdir(parents=True, exist_ok=True)
    vecs = _unit_rows(n)
    if collapse:
        vecs = np.tile(vecs[0], (n, 1))

    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    faiss.write_index(index, str(d / "embeddings.faiss"))

    ids = [str(i) for i in range(n)]
    np.save(d / "id_map.npy", np.array(ids[: id_map_len if id_map_len is not None else n], dtype=object))

    con = sqlite3.connect(d / "episodic.db")
    con.execute("CREATE TABLE memories (id TEXT, embedding_idx INT, context TEXT, created_at TEXT)")
    con.executemany(
        "INSERT INTO memories VALUES (?,?,?,?)",
        [
            (ids[i], (i + idx_shift) % n, json.dumps({"objective": f"distinct objective {i}"}), f"2026-07-28T00:{i:02d}:00")
            for i in range(id_map_len if id_map_len is not None else n)
        ],
    )
    con.commit()
    con.close()
    return d


def run_checker(store: Path, *extra: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(CHECKER), "--sessions-dir", str(store), "--json", *extra],
        capture_output=True,
        text=True,
    )
    return proc.returncode, json.loads(proc.stdout)


def by_name(report: dict) -> dict[str, dict]:
    return {c["check"]: c for c in report["checks"]}


class TestHealthyStorePasses:
    def test_clean_store_exits_zero(self, tmp_path):
        rc, report = run_checker(build_store(tmp_path / "clean"))
        assert rc == 0
        assert report["ok"] is True
        assert all(c["pass"] for c in report["checks"])


class TestEachDefectIsCaught:
    """One test per defect the incident actually exhibited."""

    def test_index_ahead_desync_fails(self, tmp_path):
        """The unrecoverable direction: index has vectors id_map cannot name."""
        rc, report = run_checker(build_store(tmp_path / "desync", id_map_len=35))
        assert rc == 1
        c = by_name(report)["index_id_map_sync"]
        assert c["pass"] is False
        assert c["desync"] == 5
        assert "UNRECOVERABLE" in c["detail"]

    def test_mis_resolving_mapping_fails(self, tmp_path):
        """The incident itself: embedding_idx resolves to some OTHER row."""
        rc, report = run_checker(build_store(tmp_path / "shift", idx_shift=7))
        assert rc == 1
        c = by_name(report)["embedding_idx_roundtrip"]
        assert c["pass"] is False
        assert c["failed"] == c["checked"]

    def test_vector_collapse_fails(self, tmp_path):
        """Distinct objectives sharing one vector — 47 did during the incident."""
        rc, report = run_checker(build_store(tmp_path / "collapse", collapse=True))
        assert rc == 1
        c = by_name(report)["vector_diversity"]
        assert c["pass"] is False
        assert c["distinct_vectors"] == 1
        assert c["distinct_objectives"] == 40


class TestDiversityDenominator:
    """The check's own bug, pinned.

    First version divided distinct vectors by ROW COUNT. Benchmark traffic
    replays the same objectives constantly (500 recent rows carried 57 distinct
    objectives), so that denominator flagged a perfectly healthy store as
    collapsing. The denominator must be distinct objectives.
    """

    def test_repeated_objectives_are_not_flagged_as_collapse(self, tmp_path):
        d = tmp_path / "replay"
        d.mkdir()
        # 3 distinct objectives, each repeated 20x, each with its own vector
        base = _unit_rows(3)
        vecs = np.vstack([base[i % 3] for i in range(60)])
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
        faiss.write_index(index, str(d / "embeddings.faiss"))
        np.save(d / "id_map.npy", np.array([str(i) for i in range(60)], dtype=object))
        con = sqlite3.connect(d / "episodic.db")
        con.execute("CREATE TABLE memories (id TEXT, embedding_idx INT, context TEXT, created_at TEXT)")
        con.executemany(
            "INSERT INTO memories VALUES (?,?,?,?)",
            [(str(i), i, json.dumps({"objective": f"objective {i % 3}"}), f"2026-07-28T00:{i:02d}:00")
             for i in range(60)],
        )
        con.commit()
        con.close()

        rc, report = run_checker(d)
        c = by_name(report)["vector_diversity"]
        assert c["distinct_vectors"] == 3
        assert c["distinct_objectives"] == 3
        assert c["diversity"] == 1.0, "healthy replay must not read as collapse"
        assert c["pass"] is True
        assert rc == 0


class TestSemanticSkipIsLoudNotSilent:
    def test_unreachable_embedder_skips_without_passing_silently(self, tmp_path):
        rc, report = run_checker(
            build_store(tmp_path / "noembed"), "--semantic",
            "--embedder-url", "http://127.0.0.1:9/embedding",
        )
        c = by_name(report)["semantic_self_match"]
        assert c["skipped"] is True
        assert c["pass"] is None
        assert "unreachable" in c["detail"]
        # a skip must not fail the gate — BGE may still be booting — but it is visible
        assert rc == 0

    def test_required_semantic_fails_when_embedder_is_unavailable(self, tmp_path):
        rc, report = run_checker(
            build_store(tmp_path / "required-noembed"), "--semantic", "--require-semantic",
            "--embedder-url", "http://127.0.0.1:9/embedding",
        )
        c = by_name(report)["semantic_self_match"]
        assert c["pass"] is False
        assert "unreachable" in c["detail"]
        assert rc == 1

    def test_required_semantic_passes_with_a_healthy_cosine(self, tmp_path):
        store = build_store(tmp_path / "semantic-clean", n=1)
        vector = faiss.read_index(str(store / "embeddings.faiss")).reconstruct(0).tolist()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - required stdlib handler name
                body = json.dumps({"embedding": vector}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            rc, report = run_checker(
                store,
                "--semantic",
                "--require-semantic",
                "--embedder-url",
                f"http://127.0.0.1:{server.server_port}/embedding",
            )
        finally:
            server.shutdown()
            thread.join()
        c = by_name(report)["semantic_self_match"]
        assert c["pass"] is True
        assert c["mean_cosine"] == pytest.approx(1.0)
        assert rc == 0


class TestSemanticSelfMatchUsesThePublishConvention:
    """The gate must reconstruct with the function that PUBLISHED the vector.

    Origin 2026-08-12 (backlog B5 / EPD-3). The semantic block hand-built
    ``type:{t} | objective:{o}`` while the live index was published by
    ``reseed_episodic_store.py`` through
    ``record_from_legacy_context(ctx).embedding_text()``, which also emits
    ``priority:{p}``. Measured on the live store: 34,938 of 64,019 rows (54.6%)
    carry ``priority: "interactive"``, so on more than half the store the
    DECISIVE check compared each stored vector against a string that was never
    embedded. A re-spelling of a convention is not the convention.

    This asserts the request BODY, not the verdict — the verdict cannot see the
    difference, which is precisely why the drift survived.
    """

    @staticmethod
    def _serve(store: Path, ctx: dict) -> tuple[list[str], int, dict]:
        con = sqlite3.connect(store / "episodic.db")
        con.execute("UPDATE memories SET context = ?", (json.dumps(ctx),))
        con.commit()
        con.close()

        vector = faiss.read_index(str(store / "embeddings.faiss")).reconstruct(0).tolist()
        seen: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - required stdlib handler name
                length = int(self.headers.get("Content-Length") or 0)
                seen.append(json.loads(self.rfile.read(length))["content"])
                body = json.dumps({"embedding": vector}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            rc, report = run_checker(
                store,
                "--semantic",
                "--require-semantic",
                "--embedder-url",
                f"http://127.0.0.1:{server.server_port}/embedding",
            )
        finally:
            server.shutdown()
            thread.join()
        return seen, rc, report

    def test_priority_bearing_row_is_reconstructed_with_its_priority(self, tmp_path):
        """The 54.6% majority shape: task_type + objective + priority."""
        sys.path.insert(0, str(CHECKER.parents[2]))
        from orchestration.repl_memory.memory_record import record_from_legacy_context

        ctx = {
            "record_version": 1,
            "task_type": "chat",
            "objective": "route this task",
            "priority": "interactive",
            "source": "legacy",
        }
        store = build_store(tmp_path / "semantic-priority", n=1)
        seen, rc, report = self._serve(store, ctx)

        expected = record_from_legacy_context(ctx).embedding_text()
        assert "priority:interactive" in expected, (
            "fixture is wrong: the publish convention must emit a priority segment for "
            "this context, or this test proves nothing"
        )
        assert seen == [expected], (
            "the gate did not send the text the publish path embeds. Sent: "
            f"{seen!r}; publish convention: {expected!r}"
        )
        assert by_name(report)["semantic_self_match"]["pass"] is True
        assert rc == 0

    def test_priority_less_row_is_reconstructed_without_one(self, tmp_path):
        """The other 45.4%: benchmark/external rows carry no priority at all.

        The fix must not go the other way and staple a priority onto rows that
        were embedded without one.
        """
        sys.path.insert(0, str(CHECKER.parents[2]))
        from orchestration.repl_memory.memory_record import record_from_legacy_context

        ctx = {
            "record_version": 1,
            "task_type": "chat",
            "objective": "answer this benchmark question",
            "source": "external",
        }
        store = build_store(tmp_path / "semantic-no-priority", n=1)
        seen, _rc, _report = self._serve(store, ctx)

        expected = record_from_legacy_context(ctx).embedding_text()
        assert "priority:" not in expected
        assert seen == [expected]

    def test_task_description_only_row_is_not_skipped(self, tmp_path):
        """The publish path falls back to `task_description`; the gate must too.

        The old block read `objective` only, so a row carrying its task text under
        the other historical key was silently dropped from the sample rather than
        checked — the check reported on a subset it never named.
        """
        sys.path.insert(0, str(CHECKER.parents[2]))
        from orchestration.repl_memory.memory_record import record_from_legacy_context

        ctx = {"task_description": "legacy key carries the task text", "source": "external"}
        store = build_store(tmp_path / "semantic-task-description", n=1)
        seen, _rc, report = self._serve(store, ctx)

        expected = record_from_legacy_context(ctx).embedding_text()
        assert seen == [expected]
        assert report is not None and by_name(report)["semantic_self_match"]["sampled"] == 1


class TestAutopilotGateBlocks:
    """The gate must refuse to start AutoPilot on a broken store."""

    @pytest.mark.parametrize("kwargs", [{"id_map_len": 35}, {"idx_shift": 7}, {"collapse": True}])
    def test_broken_store_exits_nonzero(self, tmp_path, kwargs):
        rc, _ = run_checker(build_store(tmp_path / "b", **kwargs))
        assert rc == 1, "a non-zero exit is what _enforce_episodic_integrity_gate keys on"
