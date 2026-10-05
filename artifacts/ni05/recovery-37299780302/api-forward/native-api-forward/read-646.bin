from __future__ import annotations

from scripts.tasks import select_real_suite_v1 as selector


def _row(
    task_id: str,
    class_id: str,
    *,
    outcome: str = "success",
    wall_s: float = 1.0,
    duplicate_count: int = 1,
    prompt: str | None = None,
) -> dict:
    row = {
        "schema_version": "real_task_record.v1",
        "task_id": task_id,
        "class": class_id,
        "source": "orchestrator_progress_jsonl",
        "task_type": "chat",
        "outcome": outcome,
        "route_taken": ["frontdoor"],
        "wall_s": wall_s,
        "duplicate_count": duplicate_count,
        "training_eligible": True,
        "synthetic_like": False,
        "privacy_class": "local_private",
        "task_record_ref": {"path": "logs/progress/2026-06-20.jsonl", "line": 1},
    }
    if prompt is not None:
        row["prompt"] = prompt
    return row


def test_class_quotas_cover_fifty_across_all_classes() -> None:
    quotas = selector.class_quotas(50)

    assert sum(quotas.values()) == 50
    assert quotas["benchmark_eval_measurement"] == 8
    assert set(quotas) == set(selector.CLASS_ORDER)


def test_select_rows_balances_classes_and_excludes_prompt_keys() -> None:
    rows = []
    for class_id in selector.CLASS_ORDER:
        for idx in range(10):
            rows.append(
                _row(
                    f"{class_id}-{idx}",
                    class_id,
                    outcome="failure" if idx < 4 else "success",
                    wall_s=float(idx),
                    duplicate_count=idx + 1,
                    prompt="private" if idx == 9 else None,
                )
            )

    selected, quotas = selector.select_rows(rows, total=50)

    assert len(selected) == 50
    assert {row["class"] for row in selected} == set(selector.CLASS_ORDER)
    by_class = {class_id: 0 for class_id in selector.CLASS_ORDER}
    for row in selected:
        by_class[row["class"]] += 1
        assert "prompt" not in row
        assert "prompt_ref" not in row
        assert not selector.find_prompt_keys(row)
    assert by_class == quotas
    assert sum(1 for row in selected if row["outcome"] == "failure") >= 20


def test_is_candidate_rejects_synthetic_and_prompt_bearing_rows() -> None:
    assert selector.is_candidate(_row("ok", "code_change_implementation"))
    assert not selector.is_candidate(_row("prompt", "code_change_implementation", prompt="private"))

    synthetic = _row("synthetic", "code_change_implementation")
    synthetic["synthetic_like"] = True
    assert not selector.is_candidate(synthetic)

    off_taxonomy = _row("off", "uncategorized_chat")
    assert not selector.is_candidate(off_taxonomy)
