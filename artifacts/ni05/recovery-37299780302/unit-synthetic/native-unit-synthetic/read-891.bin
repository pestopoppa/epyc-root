"""Unit tests for TD-10 counterfactual routing evaluation.

Every test is synthetic: an in-memory snapshot DB, a handmade TD-9-shaped
receipt, a dict vector source and a tiny fake estimator. No store, no network,
no model, no sklearn. The real estimator (the probe's ``cross_fit_predict``)
gets one guarded pass on synthetic separable data to prove the wiring seam.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from src.typed_decisions.routing_counterfactual import (
    COUNTERFACTUAL_CAVEAT,
    DEFAULT_CV_SEED,
    CounterfactualError,
    DictVectorSource,
    FaissVectorSource,
    JoinedRow,
    JoinUnavailable,
    NpzVectorSource,
    SnapshotCall,
    UnavailableVectorSource,
    VectorsUnavailable,
    build_plan,
    classify_support,
    decision_breakdown,
    embedding_text_for_context,
    estimate_policy_value,
    join_receipt_to_snapshot,
    load_snapshot_calls,
    main,
    run_counterfactual,
)
from src.typed_decisions.routing_replay import prepare_state, resolve_snapshot, sample_rows


def _call(
    memory_id: str,
    embedding_idx: int,
    action: str,
    outcome: str,
    context: str | None = None,
) -> SnapshotCall:
    return SnapshotCall(
        memory_id=memory_id,
        embedding_idx=embedding_idx,
        action=action,
        outcome=outcome,
        context=context if context is not None else f"context for {memory_id}",
    )


def _write_snapshot_db(
    path: Path,
    calls: list[SnapshotCall],
    *,
    created_at: str = "2026-04-01T00:00:00+00:00",
) -> Path:
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            embedding_idx INTEGER NOT NULL,
            action TEXT NOT NULL,
            action_type TEXT NOT NULL,
            context TEXT NOT NULL,
            outcome TEXT,
            q_value REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            update_count INTEGER DEFAULT 0,
            model_id TEXT
        )
        """
    )
    con.executemany(
        "INSERT INTO memories (id, embedding_idx, action, action_type, context, outcome, "
        "q_value, created_at, updated_at, update_count, model_id) "
        "VALUES (?, ?, ?, 'routing', ?, ?, 0.5, ?, ?, 0, NULL)",
        [
            (c.memory_id, c.embedding_idx, c.action, c.context, c.outcome, created_at, created_at)
            for c in calls
        ],
    )
    con.commit()
    con.close()
    return path


def _build_receipt(
    calls: list[SnapshotCall],
    *,
    n: int,
    seed: int,
    budget: int = 200,
    choices: dict[int, str] | None = None,
    snapshot_sha: str = "a" * 64,
) -> dict:
    frame = [call for call in calls if call.action.strip()]
    routing_rows = [call.routing_row() for call in frame]
    sampled = sample_rows(routing_rows, n, seed)
    by_object = {id(routing_row): call for routing_row, call in zip(routing_rows, frame)}
    rows = []
    for position, routing_row in enumerate(sampled):
        call = by_object[id(routing_row)]
        state, _ = prepare_state(call.context, budget)
        chosen = (choices or {}).get(position, call.action)
        rows.append(
            {
                "position": position,
                "incumbent": call.action,
                "label": call.label,
                "state_sha256": hashlib.sha256(state.encode("utf-8")).hexdigest(),
                "state_chars": len(state),
                "path": "native",
                "action": chosen,
                "chosen_code": None,
                "confidence": 0.9,
                "probabilities": None,
                "native_failures": [],
                "json_failures": [],
                "prompt_sha256": "b" * 64,
                "elapsed_ms": 1.0,
            }
        )
    return {
        "receipt": "td7-routing-replay",
        "timestamp": "2026-09-18T00:00:00+00:00",
        "snapshot": {"db_sha256": snapshot_sha, "admissibility_reason": "test"},
        "config": {"n": n, "seed": seed, "state_budget_chars": budget},
        "rows": rows,
        "metric_directions": {},
    }


def _joined(
    position: int,
    memory_id: str,
    chosen: str | None,
    incumbent: str,
    *,
    label: bool = True,
    embedding_idx: int | None = None,
) -> JoinedRow:
    return JoinedRow(
        position=position,
        memory_id=memory_id,
        embedding_idx=embedding_idx,
        context=f"context for {memory_id}",
        incumbent=incumbent,
        label=label,
        chosen=chosen,
        chosen_code=None,
        confidence=0.9,
        state_sha256="c" * 64,
        join_mode="test",
    )


class _TinyAdapter:
    """Deterministic stand-in model:

    ``P(success | x, a) = clip(1 - fit_failure_rate + 0.1*(x0 - 0.5), 0, 1)``.

    Two identical splits, every prediction admitted, so the fold summary has
    zero spread and expected values are hand-computable.
    """

    def __init__(self) -> None:
        self.fit_calls: list[dict] = []

    def group_key(self, vector: np.ndarray) -> str:
        return f"group-{float(vector[0]):.4f}"

    def support_floors(self) -> tuple[int, int]:
        return (1, 1)

    def cross_fit_predict(
        self,
        *,
        X_fit: np.ndarray,
        y_failure_fit: np.ndarray,
        groups_fit: np.ndarray,
        X_eval: np.ndarray,
        groups_eval: np.ndarray,
        seed: int,
        n_splits: int,
        test_size: float,
    ) -> dict:
        self.fit_calls.append(
            {"n_fit": len(X_fit), "n_eval": len(X_eval), "seed": seed, "n_splits": n_splits}
        )
        base = 1.0 - float(np.mean(y_failure_fit))
        p = np.clip(base + 0.1 * (np.asarray(X_eval, dtype=np.float32)[:, 0] - 0.5), 0.0, 1.0)
        per_split = [
            {"p_success": [float(value) for value in p], "oof": [True] * len(p)} for _ in range(2)
        ]
        return {
            "predictions": [float(value) for value in p],
            "per_split": per_split,
            "folds": 2,
            "n_splits": n_splits,
            "test_size": test_size,
            "seed": seed,
            "n_eval_rows": len(p),
            "n_predicted": len(p),
            "coverage": 1.0,
        }


def _two_action_calls() -> tuple[list[SnapshotCall], dict[str, np.ndarray]]:
    """Four A rows (50% success) and four B rows (75% success), 1-d vectors."""
    calls = [
        _call("a1", 0, "A", "success"),
        _call("a2", 1, "A", "success"),
        _call("a3", 2, "A", "failure"),
        _call("a4", 3, "A", "failure"),
        _call("b1", 4, "B", "success"),
        _call("b2", 5, "B", "success"),
        _call("b3", 6, "B", "success"),
        _call("b4", 7, "B", "failure"),
    ]
    vectors = {
        "a1": np.array([0.25], dtype=np.float32),
        "a2": np.array([0.75], dtype=np.float32),
        "a3": np.array([0.50], dtype=np.float32),
        "a4": np.array([0.125], dtype=np.float32),
        "b1": np.array([0.25], dtype=np.float32),
        "b2": np.array([0.75], dtype=np.float32),
        "b3": np.array([0.50], dtype=np.float32),
        "b4": np.array([0.125], dtype=np.float32),
    }
    return calls, vectors


# ── snapshot loading and join ─────────────────────────────────────────────


def test_load_snapshot_calls_reads_frozen_corpus(tmp_path: Path):
    calls = [_call("m1", 0, "frontdoor", "success"), _call("m2", 1, "SELF", "failure")]
    db = _write_snapshot_db(tmp_path / "episodic.db", calls)
    loaded = load_snapshot_calls(db)
    assert [(c.memory_id, c.embedding_idx, c.action, c.outcome) for c in loaded] == [
        ("m1", 0, "frontdoor", "success"),
        ("m2", 1, "SELF", "failure"),
    ]
    assert [c.label for c in loaded] == [True, False]


def test_join_reconstructs_sample_and_maps_embedding_idx(tmp_path: Path):
    calls = [_call(f"m{index}", index, "A" if index % 2 else "B", "success") for index in range(12)]
    db = _write_snapshot_db(tmp_path / "episodic.db", calls)
    receipt = _build_receipt(calls, n=5, seed=7)
    joined, report = join_receipt_to_snapshot(receipt, calls)
    assert report["mode"] == "reconstructed_sample_state_sha256"
    assert report["n_joined"] == 5
    assert report["mismatches"] == 0
    assert len({row.memory_id for row in joined}) == 5
    for row in joined:
        call = next(call for call in calls if call.memory_id == row.memory_id)
        assert row.embedding_idx == call.embedding_idx
        assert row.incumbent == call.action
        assert row.label == call.label
        assert row.chosen == call.action
    assert db.exists()


def test_join_refuses_hash_mismatch(tmp_path: Path):
    calls = [_call(f"m{index}", index, "A" if index % 2 else "B", "success") for index in range(8)]
    receipt = _build_receipt(calls, n=8, seed=1)
    receipt["rows"][2]["state_sha256"] = "0" * 64
    with pytest.raises(JoinUnavailable, match="refusing a guessed join"):
        join_receipt_to_snapshot(receipt, calls)


def test_join_refuses_receipt_without_join_key_names_live_rerun():
    receipt = {
        "rows": [
            {"position": 0, "incumbent": "A", "label": True},
            {"position": 1, "incumbent": "B", "label": False},
        ],
        "config": {},
    }
    with pytest.raises(JoinUnavailable, match="live-rerun"):
        join_receipt_to_snapshot(receipt, [_call("m1", 0, "A", "success")])


def test_join_direct_embedding_idx_mode():
    calls = [_call("m1", 3, "A", "success"), _call("m2", 4, "B", "failure")]
    receipt = {
        "rows": [
            {
                "position": 0,
                "embedding_idx": 3,
                "incumbent": "A",
                "label": True,
                "action": "B",
            },
            {
                "position": 1,
                "embedding_idx": 4,
                "incumbent": "B",
                "label": False,
                "action": "A",
            },
        ],
        "config": {},
    }
    joined, report = join_receipt_to_snapshot(receipt, calls)
    assert report["mode"] == "receipt_embedding_idx"
    assert [row.memory_id for row in joined] == ["m1", "m2"]
    assert [row.chosen for row in joined] == ["B", "A"]
    receipt["rows"][1]["incumbent"] = "A"
    with pytest.raises(JoinUnavailable):
        join_receipt_to_snapshot(receipt, calls)


# ── support classification ────────────────────────────────────────────────


def test_classify_support_flags_single_class_tiny_and_uncovered():
    calls = [
        _call("a1", 0, "A", "success"),
        _call("a2", 1, "A", "failure"),
        _call("b1", 2, "B", "success"),
        _call("b2", 3, "B", "success"),
        _call("c1", 4, "C", "success"),
        _call("d1", 5, "D", "success"),
    ]
    vectors = {key: np.zeros(2, dtype=np.float32) for key in ("a1", "a2", "b1", "b2", "c1")}
    support = classify_support(calls, vectors, min_rows=2, min_positives=1)
    assert support["A"].evaluable is True
    assert support["A"].reason is None
    assert support["B"].evaluable is False
    assert support["B"].reason == "single_outcome_class"
    assert support["C"].evaluable is False
    assert support["C"].reason == "insufficient_rows"
    assert support["D"].evaluable is False
    assert support["D"].reason == "insufficient_rows"
    assert support["D"].n_rows == 0


# ── value estimation with the tiny fake estimator ─────────────────────────


def test_estimate_policy_value_wiring_with_tiny_adapter():
    calls, vectors = _two_action_calls()
    eval_rows = [
        _joined(0, "e1", "A", "B", label=True),
        _joined(1, "e2", "B", "A", label=False),
        _joined(2, "e3", "A", "A", label=True),
        _joined(3, "e4", "B", "A", label=True),
    ]
    eval_vectors = {
        "e1": np.array([0.25], dtype=np.float32),
        "e2": np.array([0.75], dtype=np.float32),
        "e3": np.array([0.50], dtype=np.float32),
        "e4": np.array([0.125], dtype=np.float32),
    }
    adapter = _TinyAdapter()
    result = estimate_policy_value(
        eval_rows, calls, {**vectors, **eval_vectors}, adapter, seed=7, n_splits=3, test_size=0.5
    )
    assert result["status"] == "estimated"
    assert result["n_evaluable_rows"] == 4
    assert result["n_covered_rows"] == 4
    assert result["n_agreement_rows"] == 1
    assert result["n_disagreement_rows"] == 3
    assert result["typed"]["success_mean"] == pytest.approx(0.615625)
    assert result["incumbent"]["success_mean"] == pytest.approx(0.553125)
    assert result["delta_typed_minus_incumbent"]["mean"] == pytest.approx(0.0625)
    assert result["regret_incumbent_minus_typed"]["mean"] == pytest.approx(-0.0625)
    assert result["typed"]["fold_summary"]["folds"] == 2
    assert result["delta_typed_minus_incumbent"]["fold_summary"]["ci95"] == pytest.approx(
        [0.0625, 0.0625]
    )
    assert result["estimator"]["coverage"] == 1.0
    assert result["estimator"]["seed"] == 7
    assert result["estimator"]["n_splits"] == 3
    assert result["per_action"]["A"]["support"]["evaluable"] is True
    assert result["per_action"]["B"]["n_eval_as_chosen"] == 2
    assert result["per_action"]["A"]["mean_p_success_as_chosen"] == pytest.approx((0.475 + 0.5) / 2)
    assert result["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT
    assert all(call["n_splits"] == 3 for call in adapter.fit_calls)


def test_estimate_excludes_unevaluable_and_unresolved_rows():
    calls, vectors = _two_action_calls()
    calls.append(_call("s1", 8, "SINGLE", "success"))
    calls.append(_call("s2", 9, "SINGLE", "success"))
    vectors["s1"] = np.array([0.3], dtype=np.float32)
    vectors["s2"] = np.array([0.4], dtype=np.float32)
    eval_rows = [
        _joined(0, "e1", "A", "B"),
        _joined(1, "e2", "SINGLE", "A"),
        _joined(2, "e3", None, "A"),
        _joined(3, "e4", "A", "SINGLE"),
        _joined(4, "e5", "A", "A"),
    ]
    eval_vectors = {
        "e1": np.array([0.25], dtype=np.float32),
        "e2": np.array([0.75], dtype=np.float32),
        "e3": np.array([0.50], dtype=np.float32),
        "e4": np.array([0.125], dtype=np.float32),
        "e5": np.array([0.60], dtype=np.float32),
    }
    result = estimate_policy_value(
        eval_rows, calls, {**vectors, **eval_vectors}, _TinyAdapter(), seed=1
    )
    assert result["n_input_rows"] == 5
    assert result["n_evaluable_rows"] == 2
    assert result["excluded"]["by_reason"] == {
        "chosen_action_unevaluable": 1,
        "incumbent_action_unevaluable": 1,
        "unresolved_chosen": 1,
    }
    assert result["unevaluable_actions"]["SINGLE"]["reason"] == "single_outcome_class"
    assert "SINGLE" not in result["per_action"]


def test_estimate_all_rows_unevaluable_reports_status_not_numbers():
    calls = [_call("s1", 0, "SINGLE", "success"), _call("s2", 1, "SINGLE", "success")]
    vectors = {key: np.zeros(1, dtype=np.float32) for key in ("s1", "s2")}
    rows = [_joined(0, "s1", "SINGLE", "SINGLE"), _joined(1, "s2", "SINGLE", "SINGLE")]
    result = estimate_policy_value(rows, calls, vectors, _TinyAdapter(), seed=1)
    assert result["status"] == "no_evaluable_rows"
    assert "typed" not in result
    assert result["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT


def test_decision_breakdown_flags_thin_disagreement_support():
    calls, _ = _two_action_calls()
    calls.append(_call("s1", 8, "SINGLE", "success"))
    calls.append(_call("s2", 9, "SINGLE", "success"))
    rows = [
        _joined(0, "e1", "A", "A"),
        _joined(1, "e2", "B", "A"),
        _joined(2, "e3", "SINGLE", "A"),
        _joined(3, "e4", None, "A"),
    ]
    breakdown = decision_breakdown(rows, calls, min_rows=1, min_positives=1)
    assert breakdown["n_rows"] == 4
    assert breakdown["n_agreement"] == 1
    assert breakdown["n_disagreement"] == 2
    assert breakdown["n_unresolved"] == 1
    assert breakdown["disagreements_by_incumbent_to_chosen"] == {"A->B": 1, "A->SINGLE": 1}
    assert breakdown["expected_unevaluable_actions"] == ["SINGLE"]
    assert breakdown["n_rows_touching_expected_unevaluable_action"] == 1
    assert breakdown["expected_evaluability_by_action"]["SINGLE"] == "single_outcome_class"
    assert breakdown["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT


# ── vector sources ────────────────────────────────────────────────────────


def test_npz_vector_source_coverage_and_generation_refusal(tmp_path: Path):
    calls = [_call("m1", 0, "A", "success"), _call("m2", 1, "A", "failure")]
    good = tmp_path / "good.npz"
    np.savez(
        good,
        ids=np.array(["m1", "m2"], dtype=object),
        embeddings=np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    )
    vectors, report = NpzVectorSource(path=good).resolve(calls)
    assert set(vectors) == {"m1", "m2"}
    assert report["coverage"] == 1.0
    assert vectors["m1"].shape == (2,)

    foreign = tmp_path / "foreign.npz"
    np.savez(
        foreign,
        ids=np.array(["other"], dtype=object),
        embeddings=np.array([[1.0, 0.0]], dtype=np.float32),
    )
    with pytest.raises(VectorsUnavailable, match="0/2"):
        NpzVectorSource(path=foreign).resolve(calls)
    with pytest.raises(VectorsUnavailable, match="does not exist"):
        NpzVectorSource(path=tmp_path / "missing.npz").resolve(calls)


def test_faiss_vector_source_requires_verified_alignment(tmp_path: Path):
    faiss = pytest.importorskip("faiss")
    calls = [_call("m0", 0, "A", "success"), _call("m1", 1, "A", "failure")]
    index = faiss.IndexFlatIP(2)
    index.add(np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32))
    faiss_path = tmp_path / "embeddings.faiss"
    faiss.write_index(index, str(faiss_path))

    with pytest.raises(VectorsUnavailable, match="id_map"):
        FaissVectorSource(faiss_path=faiss_path).resolve(calls)

    id_map = tmp_path / "id_map.npy"
    np.save(id_map, np.array(["m0", "m1"], dtype=object))
    vectors, report = FaissVectorSource(faiss_path=faiss_path, id_map_path=id_map).resolve(calls)
    assert set(vectors) == {"m0", "m1"}
    assert report["id_map_aligned"] == 2
    assert report["id_map_mismatched"] == 0

    bad_map = tmp_path / "bad_id_map.npy"
    np.save(bad_map, np.array(["other0", "other1"], dtype=object))
    with pytest.raises(VectorsUnavailable, match="alignment is 0"):
        FaissVectorSource(faiss_path=faiss_path, id_map_path=bad_map).resolve(calls)

    positional, report = FaissVectorSource(faiss_path=faiss_path, allow_positional=True).resolve(
        calls
    )
    assert set(positional) == {"m0", "m1"}
    assert report["unverified_positions"] == 2


def test_embedding_text_for_context_matches_canonical_convention():
    context = json.dumps(
        {"task_type": "chat", "objective": "  write code  ", "priority": "interactive"}
    )
    assert embedding_text_for_context(context) == (
        "type:chat | objective:write code | priority:interactive"
    )
    assert embedding_text_for_context(json.dumps({"objective": "only this"})) == (
        "objective:only this"
    )
    assert embedding_text_for_context("not json") == "objective:"
    assert embedding_text_for_context(json.dumps([1, 2])) == "objective:"


# ── top-level receipt ─────────────────────────────────────────────────────


def _receipt_fixture(tmp_path: Path) -> tuple[Path, list[SnapshotCall], dict, dict]:
    calls, vectors = _two_action_calls()
    db = _write_snapshot_db(tmp_path / "frozen.db", calls)
    receipt = _build_receipt(calls, n=6, seed=5)
    eval_vectors = {
        "a1": np.array([0.25], dtype=np.float32),
        "a2": np.array([0.75], dtype=np.float32),
        "a3": np.array([0.50], dtype=np.float32),
        "a4": np.array([0.125], dtype=np.float32),
        "b1": np.array([0.25], dtype=np.float32),
        "b2": np.array([0.75], dtype=np.float32),
        "b3": np.array([0.50], dtype=np.float32),
        "b4": np.array([0.125], dtype=np.float32),
    }
    return db, calls, receipt, {**vectors, **eval_vectors}


def test_run_counterfactual_receipt_shape_metric_directions_and_caveat(tmp_path: Path):
    db, calls, receipt, vectors = _receipt_fixture(tmp_path)
    snapshot = resolve_snapshot(db)
    loaded = load_snapshot_calls(db)
    out = tmp_path / "counterfactual.json"
    result = run_counterfactual(
        snapshot=snapshot,
        calls=loaded,
        receipt=receipt,
        vector_source=DictVectorSource(vectors),
        adapter=_TinyAdapter(),
        receipt_path=out,
    )
    assert result["status"] == "estimated"
    assert result["join"]["mode"] == "reconstructed_sample_state_sha256"
    assert result["join"]["n_joined"] == 6
    assert result["join"]["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT
    assert result["vector_source"]["coverage"] == 1.0
    assert result["vector_source"]["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT
    assert result["metric_directions"]["policy_value.regret_incumbent_minus_typed.mean"] == (
        "lower_is_better"
    )
    assert result["policy_value"]["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT
    assert result["policy_value"]["estimator"]["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT
    assert result["live_run_requirements"][0]["item"] == "decisions"
    assert result["live_run_requirements"][0]["status"] == "present"
    assert len(result["rows"]) == 6
    assert out.exists()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written == result
    assert written["receipt"] == "td10-routing-counterfactual"
    assert written["label_provenance"]["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT


def test_run_counterfactual_vectors_unavailable_writes_requirements(tmp_path: Path):
    db, calls, receipt, _ = _receipt_fixture(tmp_path)
    snapshot = resolve_snapshot(db)
    out = tmp_path / "blocked.json"
    result = run_counterfactual(
        snapshot=snapshot,
        calls=load_snapshot_calls(db),
        receipt=receipt,
        vector_source=UnavailableVectorSource(reason="no vectors here"),
        adapter=_TinyAdapter(),
        receipt_path=out,
    )
    assert result["status"] == "vectors-unavailable"
    assert "policy_value" not in result
    assert result["join"]["mode"] == "reconstructed_sample_state_sha256"
    assert len(result["rows"]) == 6
    assert all(isinstance(row["embedding_idx"], int) for row in result["rows"])
    assert result["decision_breakdown"]["n_rows"] == 6
    assert result["vector_source"]["reason"] == "no vectors here"
    requirements = {item["item"]: item for item in result["live_run_requirements"]}
    assert requirements["decisions"]["status"] == "present"
    assert requirements["embeddings"]["status"] == "needed"
    assert "--vectors embed" in requirements["embeddings"]["command"]
    assert result["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "vectors-unavailable"


def test_run_counterfactual_join_failure_is_explicit(tmp_path: Path):
    db, calls, receipt, vectors = _receipt_fixture(tmp_path)
    receipt["rows"][0]["incumbent"] = "WRONG"
    result = run_counterfactual(
        snapshot=resolve_snapshot(db),
        calls=load_snapshot_calls(db),
        receipt=receipt,
        vector_source=DictVectorSource(vectors),
        adapter=_TinyAdapter(),
    )
    assert result["status"] == "join-unavailable"
    assert "refusing a guessed join" in result["join"]["reason"]
    requirements = {item["item"]: item for item in result["live_run_requirements"]}
    assert requirements["decisions"]["status"] == "needed"
    assert requirements["embeddings"]["status"] == "unknown"


# ── probe seam and CLI gates ──────────────────────────────────────────────


def test_probe_cross_fit_predict_is_oof_and_directional():
    pytest.importorskip("sklearn")
    from src.typed_decisions.routing_counterfactual import load_probe_module

    probe = load_probe_module()
    X, y_failure, groups = [], [], []
    for group in range(8):
        for member in range(3):
            X.append([group / 8.0 + 0.01 * member, 0.0])
            y_failure.append(1 if group >= 4 else 0)
            groups.append(f"g{group}")
    X = np.asarray(X, dtype=np.float32)
    y_failure = np.asarray(y_failure, dtype=np.int64)
    groups = np.asarray(groups, dtype=object)
    result = probe.cross_fit_predict(
        X, y_failure, groups, X, groups, seed=3, n_splits=8, test_size=0.5
    )
    assert result["folds"] >= 1
    assert 0.0 < result["coverage"] <= 1.0
    scored = [
        (float(result["predictions"][index]), int(y_failure[index]))
        for index in range(len(y_failure))
        if result["predictions"][index] is not None
    ]
    assert scored
    successes = [value for value, label in scored if label == 0]
    failures = [value for value, label in scored if label == 1]
    if successes and failures:
        assert np.mean(successes) > np.mean(failures)


def test_main_refuses_missing_and_inadmissible_snapshot(tmp_path: Path, capsys):
    assert main(["--snapshot", str(tmp_path / "missing.db"), "--dry-run"]) == 1
    assert "does not exist" in capsys.readouterr().err

    calls = [_call("m1", 0, "A", "success"), _call("m2", 1, "B", "failure")]
    fresh = _write_snapshot_db(tmp_path / "fresh.db", calls, created_at="2026-09-20T00:00:00+00:00")
    assert main(["--snapshot", str(fresh), "--dry-run"]) == 1
    assert "not admissible" in capsys.readouterr().err


def test_main_live_rerun_gate_and_dry_run_plan(tmp_path: Path, capsys):
    calls = [_call("m1", 0, "A", "success"), _call("m2", 1, "B", "failure")]
    db = _write_snapshot_db(tmp_path / "frozen.db", calls)
    assert main(["--snapshot", str(db), "--live-rerun"]) == 2
    assert "needs --live" in capsys.readouterr().err

    assert main(["--snapshot", str(db), "--live-rerun", "--dry-run"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["dry_run"] is True
    assert plan["receipt"] == "td10-routing-counterfactual-plan"
    assert plan["raw_support"]["A"]["n_rows"] == 1
    assert plan["counterfactual_caveat"] == COUNTERFACTUAL_CAVEAT

    with pytest.raises(SystemExit) as excinfo:
        main(["--snapshot", str(db)])
    assert excinfo.value.code == 2


def test_build_plan_reports_join_status_without_fitting(tmp_path: Path):
    db, calls, receipt, _ = _receipt_fixture(tmp_path)
    snapshot = resolve_snapshot(db)
    plan = build_plan(
        snapshot=snapshot,
        calls=load_snapshot_calls(db),
        receipt=receipt,
        vector_source=DictVectorSource({}),
        cv_seed=DEFAULT_CV_SEED,
        cv_splits=5,
        cv_test_size=0.25,
    )
    assert plan["dry_run"] is True
    assert plan["join"]["mode"] == "reconstructed_sample_state_sha256"
    assert "policy_value" not in plan


def test_unavailable_source_raises_with_reason():
    with pytest.raises(VectorsUnavailable, match="none"):
        UnavailableVectorSource(reason="--vectors none: no source").resolve([])


def test_counterfactual_error_hierarchy():
    assert issubclass(JoinUnavailable, CounterfactualError)
    assert issubclass(VectorsUnavailable, CounterfactualError)
