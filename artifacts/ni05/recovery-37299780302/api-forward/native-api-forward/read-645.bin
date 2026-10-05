from __future__ import annotations

import json
from pathlib import Path

from scripts.tasks import reconstruct_real_suite_v1 as recon


def test_extract_task_prompt_handles_wrapped_and_raw_prompts() -> None:
    wrapped = "sys\n\nQuestion: What is 2+2?\n\nCRITICAL: answer only"

    assert recon.extract_task_prompt(wrapped) == ("What is 2+2?", "architect_question_block")
    assert recon.extract_task_prompt("Plain task") == ("Plain task", "raw_task_prompt")


def test_best_prompt_prefers_raw_worker_prompt_over_wrapper() -> None:
    entry = {
        "prompt_candidates": [
            {
                "prompt": "Question only",
                "source": "architect_question_block",
                "role": "architect_general",
            },
            {
                "prompt": "Full worker task prompt",
                "source": "raw_task_prompt",
                "role": "worker_general",
            },
        ]
    }

    assert recon.best_prompt(entry)["prompt"] == "Full worker task prompt"


def test_reconstruction_matches_question_pool_and_omits_private_text(tmp_path: Path) -> None:
    selection = tmp_path / "selection.jsonl"
    selection.write_text(
        json.dumps(
            {
                "task_id": "chat-a",
                "selection_rank": 1,
                "class": "code_change_implementation",
                "outcome": "success",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    tap = tmp_path / "tap.jsonl"
    tap.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "start",
                        "task_id": "chat-a",
                        "role": "worker_general",
                        "prompt": "Write fizzbuzz.",
                    }
                ),
                json.dumps(
                    {
                        "event": "chunk",
                        "task_id": "chat-a",
                        "role": "worker_general",
                        "text": "def fizzbuzz(): pass",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pool = tmp_path / "pool.jsonl"
    pool.write_text(
        json.dumps({"__pool_metadata__": True}) + "\n"
        + json.dumps(
            {
                "id": "fb",
                "suite": "real_suite_v1",
                "prompt": "Write fizzbuzz.",
                "expected": "prints fizzbuzz",
                "scoring_method": "llm_judge",
                "scoring_config": {"rubric": "semantic"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    args = recon.build_parser().parse_args(
        [
            "--selection",
            str(selection),
            "--tap-glob",
            str(tap),
            "--question-pool",
            str(pool),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )
    result = recon.run(args)

    rows = [json.loads(line) for line in Path(result["rows"]).read_text().splitlines()]
    assert rows[0]["prompt_recovered"] is True
    assert rows[0]["question_pool_expected_match"] is True
    assert rows[0]["yaml_materialization_status"] == "expected_backed_ready"
    assert "prompt" not in rows[0]
    assert "response_text" not in rows[0]
    assert "expected" not in rows[0]
