from __future__ import annotations

import sqlite3
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from scripts.maintenance import repair_episodic_embeddings as repair


def test_diagnose_flags_stale_id_map_when_faiss_count_matches(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, 'routing')",
            [("m1",), ("m2",), ("m3",)],
        )

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=3)),
    )
    np.save(id_map_path, np.array(["old-1", "old-2", "old-3"], dtype=object))
    np.savez(
        reembedded_path,
        ids=np.array(["m1", "m2", "m3"], dtype=object),
        embeddings=np.ones((3, 1024), dtype=np.float32),
    )

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.n_faiss_vectors == 3
    assert report.n_id_map == 3
    assert report.faiss_coverage == 1.0
    assert report.overlap_live == 1.0
    assert report.id_map_matches_faiss
    assert report.id_map_overlap_live == 0.0
    assert report.orphan_count == 3
    assert not report.healthy


def test_diagnose_requires_near_complete_live_coverage(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"
    live_ids = [f"m{i}" for i in range(100)]

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, 'routing')",
            [(memory_id,) for memory_id in live_ids],
        )

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=94)),
    )
    np.save(id_map_path, np.array(live_ids[:94], dtype=object))

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.faiss_coverage == 0.94
    assert report.id_map_overlap_live == 0.94
    assert report.orphan_count == 6
    assert not report.healthy


def test_diagnose_counts_all_indexed_action_types(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, ?)",
            [("m1", "routing"), ("m2", "escalation")],
        )

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=1)),
    )
    np.save(id_map_path, np.array(["m1"], dtype=object))

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.n_db_routing == 1
    assert report.n_db_indexed == 2
    assert report.faiss_coverage == 0.5
    assert report.missing_id_count == 1
    assert report.orphan_count == 1
    assert not report.healthy


def test_diagnose_accepts_every_live_indexed_action_type(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"
    live_ids = ["routing-1", "exploration-1", "persona-1"]

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, ?)",
            [("routing-1", "routing"), ("exploration-1", "exploration"), ("persona-1", "persona")],
        )

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=3)),
    )
    np.save(id_map_path, np.array(live_ids, dtype=object))
    np.savez(reembedded_path, ids=np.array(live_ids, dtype=object))

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.n_db_indexed == 3
    assert report.missing_id_count == 0
    assert report.stale_id_count == 0
    assert report.healthy


def test_diagnose_flags_missing_routing_id_among_other_valid_types(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, ?)",
            [("routing-1", "routing"), ("exploration-1", "exploration"), ("persona-1", "persona")],
        )

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=2)),
    )
    np.save(id_map_path, np.array(["exploration-1", "persona-1"], dtype=object))

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.missing_id_count == 1
    assert report.orphan_count == 1
    assert not report.healthy


def test_diagnose_flags_genuinely_deleted_id_with_other_valid_types(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, ?)",
            [("routing-1", "routing"), ("persona-1", "persona")],
        )

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=3)),
    )
    np.save(id_map_path, np.array(["routing-1", "persona-1", "deleted-1"], dtype=object))

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.missing_id_count == 0
    assert report.stale_id_count == 1
    assert report.orphan_count == 1
    assert not report.healthy


def test_diagnose_flags_stale_extra_id_when_live_coverage_complete(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.execute("INSERT INTO memories (id, action_type) VALUES ('m1', 'routing')")

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=2)),
    )
    np.save(id_map_path, np.array(["m1", "old-stale-id"], dtype=object))
    np.savez(
        reembedded_path,
        ids=np.array(["m1"], dtype=object),
        embeddings=np.ones((1, 1024), dtype=np.float32),
    )

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.id_map_overlap_live == 1.0
    assert report.missing_id_count == 0
    assert report.stale_id_count == 1
    assert report.orphan_count == 1
    assert not report.healthy


def test_diagnose_keeps_live_store_healthy_with_stale_training_artifact(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"
    live_ids = ["m1", "m2", "m3"]

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, 'routing')",
            [(memory_id,) for memory_id in live_ids],
        )

    faiss_path.touch()
    monkeypatch.setitem(
        sys.modules,
        "faiss",
        types.SimpleNamespace(read_index=lambda _path: types.SimpleNamespace(ntotal=3)),
    )
    np.save(id_map_path, np.array(live_ids, dtype=object))
    np.savez(
        reembedded_path,
        ids=np.array(["m1", "legacy-1", "legacy-2"], dtype=object),
        embeddings=np.ones((3, 1024), dtype=np.float32),
    )

    report = repair.diagnose(db_path, faiss_path, reembedded_path, id_map_path)

    assert report.faiss_coverage == 1.0
    assert report.id_map_overlap_live == 1.0
    assert report.missing_id_count == 0
    assert report.stale_id_count == 0
    assert report.orphan_count == 0
    assert report.healthy
    assert report.overlap_live == pytest.approx(1 / 3)
    assert report.reembedded_missing_count == 2
    assert report.reembedded_stale_count == 2


def test_main_passes_explicit_id_map_to_pre_and_post_repair_diagnostics(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "custom-id-map.npy"
    reembedded_path = tmp_path / "reembedded.npz"
    calls: list[tuple[Path, Path, Path, Path]] = []
    reports = iter(
        [
            repair.HealthReport(1, 0, 0, 0.0, 0.0, False, 1),
            repair.HealthReport(1, 1, 0, 0.0, 1.0, True, 0),
        ]
    )

    def fake_diagnose(
        db: Path, faiss: Path, reembedded: Path, id_map: Path
    ) -> repair.HealthReport:
        calls.append((db, faiss, reembedded, id_map))
        return next(reports)

    monkeypatch.setattr(repair, "diagnose", fake_diagnose)
    monkeypatch.setattr(repair, "print_report", lambda _report: None)
    monkeypatch.setattr(repair, "run_repair", lambda **_kwargs: 1)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "repair_episodic_embeddings.py",
            "--repair",
            "--db",
            str(db_path),
            "--faiss",
            str(faiss_path),
            "--id-map",
            str(id_map_path),
            "--reembedded",
            str(reembedded_path),
            "--min-orphans",
            "0",
        ],
    )

    assert repair.main() == 0
    assert calls == [(db_path, faiss_path, reembedded_path, id_map_path)] * 2


def test_run_repair_refuses_stale_snapshot(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        repair,
        "diagnose",
        lambda *_args, **_kwargs: repair.HealthReport(
            n_db_routing=100,
            n_faiss_vectors=10,
            n_reembedded=10,
            overlap_live=0.1,
            faiss_coverage=0.1,
            healthy=False,
            orphan_count=90,
            n_db_indexed=100,
        ),
    )
    rebuild_calls: list[object] = []

    monkeypatch.setattr(repair, "_live_memory_count", lambda *_args, **_kwargs: 1200)
    monkeypatch.setattr(repair.subprocess, "call", lambda _cmd: 0)
    monkeypatch.setattr(
        repair,
        "rebuild_faiss",
        lambda *args, **kwargs: rebuild_calls.append((args, kwargs)),
    )

    with pytest.raises(SystemExit, match="refusing to swap a stale FAISS snapshot"):
        repair.run_repair(
            db_path=tmp_path / "episodic.db",
            faiss_path=tmp_path / "embeddings.faiss",
            id_map_path=tmp_path / "id_map.npy",
            reembedded_path=tmp_path / "reembedded.npz",
            max_db_growth=1000,
        )

    assert rebuild_calls == []


def test_run_repair_allows_stale_snapshot_guard_to_be_disabled(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        repair,
        "diagnose",
        lambda *_args, **_kwargs: repair.HealthReport(
            n_db_routing=100,
            n_faiss_vectors=10,
            n_reembedded=10,
            overlap_live=0.1,
            faiss_coverage=0.1,
            healthy=False,
            orphan_count=90,
        ),
    )
    monkeypatch.setattr(repair.subprocess, "call", lambda _cmd: 0)
    monkeypatch.setattr(repair, "rebuild_faiss", lambda **_kwargs: (42, tmp_path, tmp_path))

    assert (
        repair.run_repair(
            db_path=tmp_path / "episodic.db",
            faiss_path=tmp_path / "embeddings.faiss",
            id_map_path=tmp_path / "id_map.npy",
            reembedded_path=tmp_path / "reembedded.npz",
            max_db_growth=-1,
        )
        == 42
    )


def test_run_repair_rechecks_growth_at_pre_swap(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        repair,
        "diagnose",
        lambda *_args, **_kwargs: repair.HealthReport(
            n_db_routing=100,
            n_faiss_vectors=10,
            n_reembedded=10,
            overlap_live=0.1,
            faiss_coverage=0.1,
            healthy=False,
            orphan_count=90,
            n_db_indexed=100,
        ),
    )
    live_counts = iter([100, 101])

    def fake_rebuild_faiss(**kwargs):
        kwargs["pre_swap_check"]()
        return (100, tmp_path, tmp_path)

    monkeypatch.setattr(repair, "_live_memory_count", lambda *_args, **_kwargs: next(live_counts))
    monkeypatch.setattr(repair.subprocess, "call", lambda _cmd: 0)
    monkeypatch.setattr(repair, "rebuild_faiss", fake_rebuild_faiss)

    with pytest.raises(SystemExit, match="phase=pre-swap"):
        repair.run_repair(
            db_path=tmp_path / "episodic.db",
            faiss_path=tmp_path / "embeddings.faiss",
            id_map_path=tmp_path / "id_map.npy",
            reembedded_path=tmp_path / "reembedded.npz",
        )


def test_run_repair_prefers_incremental_missing_id_append(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "episodic.db"
    faiss_path = tmp_path / "embeddings.faiss"
    id_map_path = tmp_path / "id_map.npy"
    reembedded_path = tmp_path / "reembedded.npz"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT)")
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, ?)",
            [("m1", "routing"), ("m2", "routing"), ("m3", "escalation")],
        )
    faiss_path.touch()
    np.save(id_map_path, np.array(["m1"], dtype=object), allow_pickle=True)
    np.savez(
        reembedded_path,
        ids=np.array(["m1", "m3"], dtype=object),
        embeddings=np.ones((2, 1024), dtype=np.float32),
        actions=np.array(["worker_general", "frontdoor"], dtype=object),
        q_values=np.array([0.5, 0.6], dtype=np.float32),
        contexts=np.array(["{}", "{}"], dtype=object),
    )

    monkeypatch.setattr(
        repair,
        "diagnose",
        lambda *_args, **_kwargs: repair.HealthReport(
            n_db_routing=2,
            n_faiss_vectors=1,
            n_reembedded=2,
            overlap_live=0.5,
            faiss_coverage=0.5,
            healthy=False,
            orphan_count=1,
            n_id_map=1,
            id_map_overlap_live=0.5,
            id_map_matches_faiss=True,
            n_db_indexed=3,
        ),
    )
    invoked: dict[str, object] = {}

    def fake_invoke_reembed(**kwargs):
        invoked["ids_file"] = kwargs["only_ids_file"]
        invoked["output_path"] = kwargs["output_path"]
        np.savez(
            kwargs["output_path"],
            ids=np.array(["m2", "m3"], dtype=object),
            embeddings=np.ones((2, 1024), dtype=np.float32),
            actions=np.array(["worker_general", "frontdoor"], dtype=object),
            q_values=np.array([0.9, 0.8], dtype=np.float32),
            contexts=np.array(["{}", "{}"], dtype=object),
        )

    appended: dict[str, object] = {}

    def fake_append_missing_faiss_vectors(**kwargs):
        appended["ids_to_append"] = kwargs["ids_to_append"]
        return len(kwargs["ids_to_append"])

    monkeypatch.setattr(repair, "_invoke_reembed", fake_invoke_reembed)
    monkeypatch.setattr(repair, "append_missing_faiss_vectors", fake_append_missing_faiss_vectors)
    monkeypatch.setattr(repair, "merge_reembedded_npz", lambda **_kwargs: 1)

    assert repair.run_repair(db_path, faiss_path, id_map_path, reembedded_path) == 2
    assert appended["ids_to_append"] == {"m2", "m3"}
    assert Path(invoked["ids_file"]).read_text().splitlines() == ["m2", "m3"]
