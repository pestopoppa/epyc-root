from __future__ import annotations

from pathlib import Path

import yaml

from src.workload_model import capture_workload_class, infer_workload_class, load_traffic_classes


def test_repo_workload_model_declares_required_traffic_classes() -> None:
    classes = load_traffic_classes()

    assert set(classes) == {"interactive", "eval_batch", "campaign"}
    assert classes["interactive"].contention_priority == "foreground"
    assert classes["eval_batch"].queue_budget_ms_default == 90000
    assert classes["campaign"].serving_class == "scheduled_background"


def test_workload_class_inference_uses_existing_metadata() -> None:
    assert infer_workload_class(source="chat") == "interactive"
    assert infer_workload_class(priority="background") == "eval_batch"
    assert infer_workload_class(batch_id="b1") == "eval_batch"
    assert infer_workload_class(concurrency_batch_id="cb1") == "eval_batch"
    assert infer_workload_class(source="eval_tower") == "eval_batch"
    assert infer_workload_class(campaign_id="k7") == "campaign"
    assert infer_workload_class(source="kbrag") == "campaign"
    assert infer_workload_class(explicit="campaign", source="chat") == "campaign"


def test_capture_workload_class_prefers_explicit_field() -> None:
    assert capture_workload_class({"task_type": "chat", "workload_class": "campaign"}) == "campaign"
    assert capture_workload_class({"task_type": "chat", "source": "eval_tower"}) == "eval_batch"
    assert capture_workload_class({"task_type": "chat"}) == "interactive"


def test_load_traffic_classes_rejects_missing_required_class(tmp_path: Path) -> None:
    path = tmp_path / "workload_model.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "traffic_classes": [
                    {
                        "id": "interactive",
                        "display_name": "Interactive",
                        "serving_class": "foreground",
                        "contention_priority": "foreground",
                        "latency_slo": {"queue_budget_ms_default": 5000},
                    }
                ]
            }
        )
    )

    try:
        load_traffic_classes(path)
    except ValueError as exc:
        assert "missing traffic classes" in str(exc)
    else:
        raise AssertionError("missing traffic classes should fail validation")
