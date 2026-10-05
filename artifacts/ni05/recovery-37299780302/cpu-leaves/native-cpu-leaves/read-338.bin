"""Evidence-plane W4 instrument repair coverage."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import eval_tower  # noqa: E402
from eval_tower import EvalTower, QuestionResult  # noqa: E402


class _PrefixRng:
    def sample(self, population, k):  # noqa: ANN001
        return list(population[:k])


def _authorize_core(monkeypatch, tmp_path: Path, core_id: str = "core_v2") -> Path:
    eras_path = tmp_path / "instrument_eras.yaml"
    eras_path.write_text(
        "\n".join(
            [
                "eras:",
                "  - id: E4-unit",
                '    from: "2000-01-01T00:00:00Z"',
                "    scope: autopilot_quality",
                f'    core_id: "{core_id}"',
                '    policy_version: "unit-test"',
            ]
        )
        + "\n"
    )
    monkeypatch.setenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", str(eras_path))
    return eras_path


def test_programmatic_scorer_runs_with_empty_expected(monkeypatch) -> None:
    tower = EvalTower()

    def _fake_call(**_kwargs):  # noqa: ANN001
        return {
            "answer": "This response is intentionally non-empty.",
            "tokens_generated": 7,
            "model": "fake",
        }

    monkeypatch.setattr(eval_tower, "call_orchestrator_forced", _fake_call)

    with eval_tower.httpx.Client(timeout=1) as client:
        result = tower._eval_question(
            {
                "id": "ifeval-empty-expected",
                "suite": "instruction_precision",
                "prompt": "Write any non-empty answer.",
                "expected": "",
                "scoring_method": "programmatic",
                "scoring_config": {"verifier": "non_empty"},
            },
            client,
        )

    assert result.correct is True


def test_empty_expected_still_blocks_plain_exact_match(monkeypatch) -> None:
    tower = EvalTower()

    def _fake_call(**_kwargs):  # noqa: ANN001
        return {
            "answer": "A non-empty answer must not auto-pass.",
            "tokens_generated": 7,
            "model": "fake",
        }

    monkeypatch.setattr(eval_tower, "call_orchestrator_forced", _fake_call)

    with eval_tower.httpx.Client(timeout=1) as client:
        result = tower._eval_question(
            {
                "id": "exact-empty-expected",
                "suite": "general",
                "prompt": "Write any non-empty answer.",
                "expected": "",
                "scoring_method": "exact_match",
            },
            client,
        )

    assert result.correct is False


def test_empty_expected_text_scorer_is_not_scoreable() -> None:
    assert not eval_tower._is_scoreable_question(
        {
            "id": "dead-text",
            "expected": "",
            "scoring_method": "substring",
        }
    )
    assert eval_tower._is_scoreable_question(
        {
            "id": "expected-free-programmatic",
            "expected": "",
            "scoring_method": "programmatic",
        }
    )


def test_code_execution_requires_executable_oracle() -> None:
    assert not eval_tower._is_scoreable_question(
        {
            "id": "code-without-tests",
            "expected": "def solve",
            "scoring_method": "code_execution",
            "scoring_config": {"language": "python"},
        }
    )
    assert not eval_tower._is_scoreable_question(
        {
            "id": "commented-asserts",
            "expected": "",
            "scoring_method": "code_execution",
            "scoring_config": {
                "language": "python",
                "test_code": "# assert add(1, 2) == 3\n",
            },
        }
    )
    assert eval_tower._is_scoreable_question(
        {
            "id": "stdin-tests",
            "expected": "",
            "scoring_method": "code_execution",
            "scoring_config": {
                "language": "python",
                "test_code": "TEST_CASES = [('1\\n', '1\\n')]",
            },
        }
    )


def test_sampling_replaces_unscoreable_items_from_same_suite() -> None:
    suite_qs = [
        {
            "id": "dead-text",
            "expected": "",
            "scoring_method": "substring",
        },
        {
            "id": "valid-text",
            "expected": "answer",
            "scoring_method": "substring",
        },
        {
            "id": "valid-programmatic",
            "expected": "",
            "scoring_method": "programmatic",
        },
    ]

    sample = eval_tower._sample_scoreable_questions(
        "instruction_precision",
        suite_qs,
        per_suite=2,
        rng=_PrefixRng(),
    )

    assert [q["id"] for q in sample] == ["valid-text", "valid-programmatic"]


def test_eval_sample_globally_backfills_when_suite_underfills() -> None:
    pool = {
        "usaco": [
            {
                "id": "dead-usaco-a",
                "suite": "usaco",
                "expected": "",
                "scoring_method": "code_execution",
                "scoring_config": {"language": "python"},
            },
            {
                "id": "dead-usaco-b",
                "suite": "usaco",
                "expected": "",
                "scoring_method": "substring",
            },
        ],
        "math": [
            {
                "id": f"valid-math-{i}",
                "suite": "math",
                "expected": str(i),
                "scoring_method": "exact_match",
            }
            for i in range(6)
        ],
    }

    sample = eval_tower._sample_scoreable_eval_questions(
        pool,
        n=4,
        rng=random.Random(7),
    )

    assert len(sample) == 4
    assert len({id(q) for q in sample}) == 4
    assert all(eval_tower._is_scoreable_question(q) for q in sample)
    assert {q["suite"] for q in sample if "suite" in q}.isdisjoint({"usaco"})
    assert not {q["id"] for q in sample} & {"dead-usaco-a", "dead-usaco-b"}


def test_eval_question_records_chat_response_routed_to(monkeypatch) -> None:
    tower = EvalTower()

    def _fake_call(**_kwargs):  # noqa: ANN001
        return {
            "answer": "FRIEND",
            "routed_to": "worker_vision",
            "tokens_generated": 1,
        }

    monkeypatch.setattr(eval_tower, "call_orchestrator_forced", _fake_call)

    with eval_tower.httpx.Client(timeout=1) as client:
        result = tower._eval_question(
            {
                "id": "vl-route-telemetry",
                "suite": "vl",
                "prompt": "what is written in the image?",
                "expected": "FRIEND",
                "scoring_method": "exact_match",
                "image_path": "/tmp/example.png",
            },
            client,
        )

    assert result.route_used == "worker_vision"


def test_instruction_route_labels_map_to_runtime_roles() -> None:
    from src.roles import Role

    assert EvalTower._instruction_role_from_route("frontdoor", Role) == Role.FRONTDOOR
    assert EvalTower._instruction_role_from_route("worker", Role) == Role.WORKER_GENERAL
    assert EvalTower._instruction_role_from_route("architect", Role) == Role.ARCHITECT_GENERAL
    assert EvalTower._instruction_role_from_route("unknown_model_id", Role) is None


def test_instruction_token_accounting_uses_active_prompts_not_prompt_library() -> None:
    prompt_library_tokens = sum(
        md.stat().st_size for md in (REPO_ROOT / "orchestration" / "prompts").rglob("*.md")
    )
    prompt_library_tokens //= 4
    tower = EvalTower()
    active_tokens = tower._count_instruction_tokens(
        [
            QuestionResult(
                question_id="frontdoor-q",
                suite="general",
                prompt="2+2?",
                expected="4",
                route_used="frontdoor",
            ),
            QuestionResult(
                question_id="worker-q",
                suite="general",
                prompt="Name the color of snow.",
                expected="white",
                route_used="worker",
            ),
        ]
    )

    assert active_tokens > 0
    assert active_tokens < prompt_library_tokens


def test_t0_sentinel_suites_are_namespaced_without_mutating_source(monkeypatch) -> None:
    sentinels = [
        {
            "id": "sentinel-a",
            "suite": "general",
            "prompt": "A",
            "expected": "A",
            "scoring_method": "exact_match",
        },
        {
            "id": "sentinel-b",
            "suite": "math",
            "prompt": "B",
            "expected": "B",
            "scoring_method": "exact_match",
        },
    ]
    tower = EvalTower()
    tower._sentinels = sentinels

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=q["id"] == "sentinel-a",
                tokens_generated=1,
                elapsed_s=1.0,
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t0()

    assert result.per_suite_quality == {
        "sentinel_general": 3.0,
        "sentinel_math": 0.0,
    }
    assert sentinels[0]["suite"] == "general"
    assert sentinels[1]["suite"] == "math"


def test_eval_t1_uses_designed_core_when_enabled(tmp_path, monkeypatch) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "core_v2", "source": "unit"},
        {
            "id": "core-a",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
        },
        {
            "id": "core-b",
            "suite": "coder",
            "prompt": "Return x",
            "expected": "x",
            "scoring_method": "exact_match",
        },
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    _authorize_core(monkeypatch, tmp_path)

    captured = {}

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        captured["ids"] = [q["id"] for q in questions]
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=1,
                elapsed_s=1.0,
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = EvalTower().eval_t1(n=999, seed=123)

    assert captured["ids"] == ["core-a", "core-b"]
    assert result.core_id == "core_v2"
    assert result.n_questions == 2
    assert result.details["core_selection"] == "designed_core"
    assert result.details["core_metadata"]["source"] == "unit"
    assert result.details["requested_n"] == 999
    assert result.details["base_core_questions"] == 2


def test_eval_t1_designed_core_requires_matching_instrument_era(tmp_path, monkeypatch) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    core_path.write_text(
        json.dumps({"__core_metadata__": True, "core_id": "core_v2"})
        + "\n"
        + json.dumps(
            {
                "id": "core-a",
                "suite": "math",
                "prompt": "2+2?",
                "expected": "4",
                "scoring_method": "exact_match",
            }
        )
        + "\n"
    )
    eras_path = tmp_path / "instrument_eras.yaml"
    eras_path.write_text(
        "\n".join(
            [
                "eras:",
                "  - id: E3b",
                '    from: "2000-01-01T00:00:00Z"',
                "    scope: autopilot_quality",
                '    note: "pre-core quality era"',
            ]
        )
        + "\n"
    )
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    monkeypatch.setenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", str(eras_path))

    def _fail_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        raise AssertionError("designed core should fail closed before evaluation")

    monkeypatch.setattr(EvalTower, "_eval_batch", _fail_eval_batch)

    result = EvalTower().eval_t1(n=50, seed=42)

    assert result.core_id == "core_v2"
    assert result.quality == 0
    assert result.reliability == 0
    assert result.details["core_selection"] == "designed_core"
    assert result.details["core_era_guard"]["status"] == "missing_core_era"
    assert "human-owned E4/core row" in result.details["core_error"]


def test_eval_t1_missing_designed_core_fails_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(tmp_path / "missing.jsonl"))
    _authorize_core(monkeypatch, tmp_path)

    result = EvalTower().eval_t1(n=50, seed=42)

    assert result.core_id == "core_v2"
    assert result.quality == 0
    assert result.reliability == 0
    assert result.details["core_selection"] == "designed_core"
    assert result.details["core_path"] == str(tmp_path / "missing.jsonl")
    assert "not found" in result.details["core_error"]


def test_eval_t1_core_path_without_core_id_fails_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_T1_CORE_ID", raising=False)
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(tmp_path / "core_v2.jsonl"))

    result = EvalTower().eval_t1(n=50, seed=42)

    assert result.quality == 0
    assert result.reliability == 0
    assert result.details["core_selection"] == "designed_core"
    assert "requires AUTOPILOT_T1_CORE_ID" in result.details["core_error"]


def test_eval_t1_designed_core_rejects_metadata_mismatch(tmp_path, monkeypatch) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "wrong_core"},
        {
            "id": "core-a",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
        },
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    _authorize_core(monkeypatch, tmp_path)

    result = EvalTower().eval_t1(n=50, seed=42)

    assert result.core_id == "core_v2"
    assert result.quality == 0
    assert result.reliability == 0
    assert "does not match requested" in result.details["core_error"]


def test_eval_t1_designed_core_rejects_unscoreable_rows(tmp_path, monkeypatch) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "core_v2"},
        {
            "id": "dead-core-row",
            "suite": "general",
            "prompt": "Write anything.",
            "expected": "",
            "scoring_method": "substring",
        },
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    _authorize_core(monkeypatch, tmp_path)

    result = EvalTower().eval_t1(n=50, seed=42)

    assert result.core_id == "core_v2"
    assert result.quality == 0
    assert result.reliability == 0
    assert "unscoreable" in result.details["core_error"]


def test_eval_t1_designed_core_can_reference_question_pool_ids(tmp_path, monkeypatch) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "core_v2"},
        {"id": "math/q-from-pool"},
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    _authorize_core(monkeypatch, tmp_path)
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "q-from-pool",
                "suite": "math",
                "prompt": "3+4?",
                "expected": "7",
                "scoring_method": "exact_match",
            }
        ]
    }

    captured = {}

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        captured["ids"] = [q["id"] for q in questions]
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=1,
                elapsed_s=1.0,
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t1()

    assert captured["ids"] == ["q-from-pool"]
    assert result.core_id == "core_v2"
    assert result.details["base_core_questions"] == 1


def test_eval_t1_legacy_sampling_records_core_id(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_T1_CORE_ID", raising=False)
    monkeypatch.delenv("AUTOPILOT_T1_CORE_PATH", raising=False)
    tower = EvalTower()
    # Every row in the production pool carries a difficulty tier (79,479/79,479 as of
    # 2026-08-04), so a fixture pool without one does not model the real instrument —
    # and since the draw is now tier-stratified, an untiered fixture draws nothing.
    tower._pool = {
        "math": [
            {
                "id": f"pool-math-{tier}",
                "suite": "math",
                "tier": tier,
                "prompt": f"1+{tier}?",
                "expected": str(1 + tier),
                "scoring_method": "exact_match",
            }
            for tier in (1, 2, 3)
        ],
        "coder": [
            {
                "id": f"pool-coder-{tier}",
                "suite": "coder",
                "tier": tier,
                "prompt": f"Return x{tier}",
                "expected": f"x{tier}",
                "scoring_method": "exact_match",
            }
            for tier in (1, 2, 3)
        ],
    }

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=1,
                elapsed_s=1.0,
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t1(n=3, seed=42)

    # Derived from the sampler's declared policy rather than restated: the core_id is the
    # INSTRUMENT'S identity, so it has to change when the draw changes. Pinning the old
    # literal would have let a genuinely different question set keep the old identity —
    # and with it the old baseline and the old frontier.
    rotation = result.details["test_profile"]["tier_mix_provenance"]["core_rotation_index"]
    assert result.core_id == (
        f"tier_stratified_{eval_tower.EVAL_TIER_MIX_POLICY}_seed_42_n3_rot{rotation}"
    )
    assert result.details["core_selection"] == "tier_stratified"
    # The rotation block must be part of the instrument's identity, or every rotation
    # would be reported as corruption of an unchanged core_id by the drift ledger.
    assert f"_rot{rotation}" in result.core_id
    assert result.details["test_profile"]["tier_mix_provenance"]["tier_mix_targets"] == {
        str(k): v for k, v in eval_tower.declared_tier_targets(3).items()
    }
    assert result.details["base_core_questions"] == 3
    assert len(result.details["dataset_content_sha256"]) == 64
    assert result.details["dataset_sha256"] == result.details["dataset_content_sha256"]
    assert result.details["test_profile"]["tier"] == 1
    # The profile's core_id must agree with the result's — two spellings of one identity
    # drifting apart is how a renamed instrument keeps an old baseline.
    assert result.details["test_profile"]["core_id"] == result.core_id
    assert result.details["test_profile"]["n_questions"] == 3
    # One question per tier at n=3: the declared mix is honoured, not merely recorded.
    assert result.details["question_tier_mix"] == {"1": 1, "2": 1, "3": 1}
    assert "test_profile_json" in result.details
    assert result.details["eval_execution_instrument_id"] == (
        eval_tower.EVAL_EXECUTION_INSTRUMENT_ID
    )
    assert result.details["eval_scoring_schedule_id"] == (eval_tower.EVAL_SCORING_SCHEDULE_ID)
    assert len(result.details["eval_execution_profile_sha256"]) == 64


def test_dataset_content_sha256_includes_suite_and_scoring_oracle() -> None:
    base = [
        {
            "id": "q1",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
            "scoring_config": {"extract_pattern": r"ANSWER:\s*(\d+)"},
        }
    ]
    changed_oracle = [dict(base[0], scoring_config={"extract_pattern": r"####\s*(\d+)"})]
    changed_suite = [dict(base[0], suite="coder")]

    assert eval_tower.dataset_content_sha256(base) != eval_tower.dataset_content_sha256(
        changed_oracle
    )
    assert eval_tower.dataset_content_sha256(base) != eval_tower.dataset_content_sha256(
        changed_suite
    )


def test_eval_instrument_stamp_warns_on_core_id_drift() -> None:
    eval_tower._DATASET_SHA_BY_CORE_ID.clear()
    q1 = [{"id": "q1", "suite": "math", "prompt": "2+2?", "expected": "4"}]
    q2 = [{"id": "q2", "suite": "math", "prompt": "3+3?", "expected": "6"}]

    first = eval_tower._stamp_eval_instrument(
        eval_tower.EvalResult(tier=1, quality=3.0, speed=1.0, cost=0.0, reliability=1.0),
        questions=q1,
        core_id="core-v",
        test_profile={"tier": 1},
    )
    second = eval_tower._stamp_eval_instrument(
        eval_tower.EvalResult(tier=1, quality=3.0, speed=1.0, cost=0.0, reliability=1.0),
        questions=q2,
        core_id="core-v",
        test_profile={"tier": 1},
    )

    assert "instrument_drift_warning" not in first.details
    warning = second.details["instrument_drift_warning"]
    assert warning["core_id"] == "core-v"
    assert warning["previous_dataset_content_sha256"] == first.details["dataset_content_sha256"]
    assert warning["current_dataset_content_sha256"] == second.details["dataset_content_sha256"]


def test_durable_instrument_ledger_detects_execution_scheduler_drift(monkeypatch, tmp_path) -> None:
    eval_tower._DATASET_SHA_BY_CORE_ID.clear()
    monkeypatch.setattr(
        eval_tower, "_INSTRUMENT_LEDGER_PATH", tmp_path / "eval_instrument_ledger.json"
    )
    questions = [{"id": "q1", "suite": "math", "prompt": "2+2?", "expected": "4"}]
    monkeypatch.setattr(eval_tower, "EVAL_EXECUTION_INSTRUMENT_ID", "scheduler-v1")
    eval_tower._stamp_eval_instrument(
        eval_tower.EvalResult(tier=1, quality=3.0, speed=1.0, cost=0.0, reliability=1.0),
        questions=questions,
        core_id="core-execution",
        test_profile={"tier": 1},
    )

    monkeypatch.setattr(eval_tower, "EVAL_EXECUTION_INSTRUMENT_ID", "scheduler-v2")
    second = eval_tower._stamp_eval_instrument(
        eval_tower.EvalResult(tier=1, quality=3.0, speed=1.0, cost=0.0, reliability=1.0),
        questions=questions,
        core_id="core-execution",
        test_profile={"tier": 1},
    )

    drift = second.details["instrument_drift_across_restart"]
    assert drift["changed_content"] is False
    assert drift["changed_execution_instrument"] is True
    assert drift["previous_execution_instrument_id"] == "scheduler-v1"
    assert drift["current_execution_instrument_id"] == "scheduler-v2"


def test_instrument_transition_message_names_policy_axis_not_stable_dataset() -> None:
    level, message = eval_tower._instrument_drift_log_message(
        {
            "changed_content": False,
            "changed_tier_mix": False,
            "changed_execution_instrument": False,
            "changed_scoring_schedule": True,
            "previous_dataset_content_sha256": "same-sha",
            "current_dataset_content_sha256": "same-sha",
            "previous_tier_mix": {"1": 100},
            "current_tier_mix": {"1": 100},
            "previous_execution_instrument_id": "lanes-v2",
            "current_execution_instrument_id": "lanes-v2",
            "previous_scoring_schedule_id": "judge-v3",
            "current_scoring_schedule_id": "judge-v4",
        }
    )

    assert level == eval_tower.logging.WARNING
    assert "axes=scoring_schedule" in message
    assert "judge-v3" in message and "judge-v4" in message
    assert "DIFFERENT question sets" not in message


def test_instrument_transition_message_keeps_dataset_drift_loud() -> None:
    level, message = eval_tower._instrument_drift_log_message(
        {
            "changed_content": True,
            "changed_tier_mix": False,
            "changed_execution_instrument": False,
            "changed_scoring_schedule": False,
            "previous_dataset_content_sha256": "old-sha",
            "current_dataset_content_sha256": "new-sha",
        }
    )

    assert level == eval_tower.logging.ERROR
    assert "DATASET INSTRUMENT DRIFT" in message
    assert "old-sha" in message and "new-sha" in message


def test_eval_t1_w6_audit_block_appends_trial_seeded_questions(
    tmp_path,
    monkeypatch,
) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "core_v2"},
        {
            "id": "core-a",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
        },
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_BLOCK", "1")
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_N", "2")
    _authorize_core(monkeypatch, tmp_path)
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "audit-math",
                "suite": "math",
                "prompt": "3+4?",
                "expected": "7",
                "scoring_method": "exact_match",
            },
        ],
        "coder": [
            {
                "id": "audit-coder",
                "suite": "coder",
                "prompt": "Return x",
                "expected": "x",
                "scoring_method": "exact_match",
            },
        ],
    }

    captured = []

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        captured.extend((q["id"], q["eval_partition"]) for q in questions)
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=q["eval_partition"] == "core",
                tokens_generated=1,
                elapsed_s=1.0,
                eval_partition=q["eval_partition"],
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t1(n=999, seed=123, trial_id=17)

    assert captured[0] == ("core-a", "core")
    assert sorted(captured[1:]) == [
        ("audit-coder", "audit"),
        ("audit-math", "audit"),
    ]
    assert result.core_id == "core_v2"
    assert result.n_questions == 1
    assert result.quality == 3.0
    assert result.details["base_core_questions"] == 1
    assert result.details["base_audit_questions"] == 2
    assert result.details["audit_policy"]["active"] is True
    assert result.details["audit_policy"]["shadow_only"] is True
    assert result.details["audit_policy"]["trial_id"] == 17
    assert result.details["audit_policy"]["actual_n"] == 2
    assert result.details["audit_shadow_only"] is True
    assert result.details["audit_shadow_total_n_questions"] == 3
    assert result.details["audit_shadow_decision_n_questions"] == 1
    assert result.details["partition_counts"] == {"core": 1, "audit": 2}
    assert result.details["partition_quality"] == {"core": 3.0, "audit": 0.0}
    assert len(result.question_results) == 3
    audit_rows = [row for row in result.question_results if row["partition"] == "audit"]
    assert {row["suite"] for row in audit_rows} == {"math", "coder"}


def test_eval_t1_w6_audit_block_can_count_audit_in_decision_metrics(
    tmp_path,
    monkeypatch,
) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "core_v2"},
        {
            "id": "core-a",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
        },
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_BLOCK", "1")
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_N", "2")
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_SHADOW_ONLY", "0")
    _authorize_core(monkeypatch, tmp_path)
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "audit-math",
                "suite": "math",
                "prompt": "3+4?",
                "expected": "7",
                "scoring_method": "exact_match",
            },
        ],
        "coder": [
            {
                "id": "audit-coder",
                "suite": "coder",
                "prompt": "Return x",
                "expected": "x",
                "scoring_method": "exact_match",
            },
        ],
    }

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=q["eval_partition"] == "core",
                tokens_generated=1,
                elapsed_s=1.0,
                eval_partition=q["eval_partition"],
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t1(n=999, seed=123, trial_id=17)

    assert result.n_questions == 3
    assert result.quality == 1.0
    assert result.details["audit_policy"]["shadow_only"] is False
    assert "audit_shadow_only" not in result.details


def test_eval_t1_w6_audit_block_honors_cadence(tmp_path, monkeypatch) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "core_v2"},
        {
            "id": "core-a",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
        },
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_BLOCK", "1")
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_N", "2")
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS", "2")
    _authorize_core(monkeypatch, tmp_path)

    captured = []

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        captured.extend((q["id"], q["eval_partition"]) for q in questions)
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=1,
                elapsed_s=1.0,
                eval_partition=q["eval_partition"],
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = EvalTower().eval_t1(n=999, seed=123, trial_id=17)

    assert captured == [("core-a", "core")]
    assert result.details["base_audit_questions"] == 0
    assert result.details["audit_policy"]["active"] is False
    assert result.details["audit_policy"]["skip_reason"] == "trial_not_on_audit_cadence"


def test_eval_t1_w6_audit_block_requires_trial_id(tmp_path, monkeypatch) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    rows = [
        {"__core_metadata__": True, "core_id": "core_v2"},
        {
            "id": "core-a",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
        },
    ]
    core_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_BLOCK", "1")
    _authorize_core(monkeypatch, tmp_path)

    result = EvalTower().eval_t1(n=999, seed=123)

    assert result.quality == 0
    assert result.reliability == 0
    assert result.core_id == "core_v2"
    assert "requires a trial_id" in result.details["audit_error"]


def test_eval_t2_non_promotion_excludes_legacy_t1_core_qids(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_T1_CORE_ID", raising=False)
    monkeypatch.delenv("AUTOPILOT_T1_CORE_PATH", raising=False)
    monkeypatch.delenv("AUTOPILOT_TOOL_SENTINELS", raising=False)
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": f"q-{idx:03d}",
                "suite": "math",
                "prompt": f"question {idx}",
                "expected": str(idx),
                "scoring_method": "exact_match",
            }
            for idx in range(105)
        ]
    }
    t1_core_ids = {
        q["id"]
        for q in eval_tower._sample_scoreable_eval_questions(
            tower._pool,
            eval_tower.EVAL_T1_SPEC_N,
            random.Random(42),
        )
    }
    captured: list[str] = []

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        captured.extend(q["id"] for q in questions if q.get("eval_partition") == "core")
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=1,
                elapsed_s=1.0,
                eval_partition=q["eval_partition"],
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t2(n=5, seed=42)

    assert len(captured) == 5
    assert set(captured).isdisjoint(t1_core_ids)
    assert result.details["t1_core_exclusion_policy"]["source"] == "legacy_pool_seed"
    assert result.details["t1_core_exclusion_policy"]["actual_n"] == 100
    assert result.details["t1_core_exclusion_policy"]["actual_t2_core_n"] == 5
    assert (
        result.details["test_profile"]["t1_core_exclusion_policy"]["core_id"]
        == "legacy_pool_seed_42_n100"
    )


def test_eval_t2_promotion_eval_uses_trial_seed_and_excludes_recent_qids(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(eval_tower, "PROMOTION_EVAL_MIN_N", 2)
    monkeypatch.setattr(eval_tower, "PROMOTION_EVAL_MAX_N", 5)
    monkeypatch.setenv("AUTOPILOT_SEQ_PROMOTION_EVAL_N", "3")
    health_path = tmp_path / "item_health.json"
    health_path.write_text(
        json.dumps(
            {
                "windows": {
                    "last_100_trials": {
                        "suite_summary": [
                            {
                                "suite": "broken",
                                "artifact_verdict": "artifact",
                                "flags": ["pinned_zero_or_broken"],
                            }
                        ]
                    }
                }
            }
        )
    )
    monkeypatch.setenv("AUTOPILOT_SEQ_PROMOTION_SUITE_HEALTH_PATH", str(health_path))
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "recent-math",
                "suite": "math",
                "prompt": "old",
                "expected": "old",
                "scoring_method": "exact_match",
            },
            {
                "id": "fresh-math",
                "suite": "math",
                "prompt": "2+2?",
                "expected": "4",
                "scoring_method": "exact_match",
            },
        ],
        "coder": [
            {
                "id": "fresh-coder",
                "suite": "coder",
                "prompt": "Return x",
                "expected": "x",
                "scoring_method": "exact_match",
            },
            {
                "id": "fresh-coder-2",
                "suite": "coder",
                "prompt": "Return y",
                "expected": "y",
                "scoring_method": "exact_match",
            },
        ],
        "broken": [
            {
                "id": "broken-item",
                "suite": "broken",
                "prompt": "broken",
                "expected": "broken",
                "scoring_method": "exact_match",
            },
        ],
    }

    captured: list[str] = []

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        captured.extend(q["id"] for q in questions)
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=1,
                elapsed_s=1.0,
                eval_partition=q["eval_partition"],
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    recent_stable_qid = eval_tower._stable_question_qid("math", "old")

    result = tower.eval_t2(
        promotion_eval=True,
        trial_id=42,
        exclude_qids={recent_stable_qid},
    )

    assert "recent-math" not in captured
    assert "broken-item" not in captured
    assert set(captured) == {"fresh-math", "fresh-coder", "fresh-coder-2"}
    assert result.core_id == "w8_promotion_eval_v1_trial_42_n3"
    assert result.details["promotion_eval_policy"] == {
        "enabled": True,
        "version": "w8-promotion-eval-v1",
        "trial_id": 42,
        "requested_n": 3,
        "min_n": 2,
        "max_n": 5,
        "seed": eval_tower._promotion_eval_seed(42, 3),
        "recent_exclusion_qids": 1,
        "recency_window_days": 60,
        "suite_health": {
            "path": str(health_path),
            "status": "ok",
            "excluded_suites": ["broken"],
            "reasons": {"broken": "artifact"},
        },
        "actual_n": 3,
    }


def test_eval_t2_promotion_eval_fails_closed_without_trial_id(monkeypatch) -> None:
    monkeypatch.setattr(eval_tower, "PROMOTION_EVAL_MIN_N", 2)
    monkeypatch.setattr(eval_tower, "PROMOTION_EVAL_MAX_N", 5)
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "fresh-math",
                "suite": "math",
                "prompt": "2+2?",
                "expected": "4",
                "scoring_method": "exact_match",
            },
        ],
    }

    result = tower.eval_t2(promotion_eval=True)

    assert result.quality == 0
    assert result.reliability == 0
    assert result.details["promotion_eval_policy"]["enabled"] is True
    assert "requires a trial_id" in result.details["promotion_eval_policy"]["error"]


def test_eval_t2_nonpromotion_excludes_t1_core_and_caller_qids(
    tmp_path,
    monkeypatch,
) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    core_path.write_text(
        json.dumps({"__core_metadata__": True, "core_id": "core_v2"})
        + "\n"
        + json.dumps(
            {
                "id": "t1-core",
                "suite": "math",
                "prompt": "core prompt",
                "expected": "core",
                "scoring_method": "exact_match",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "t1-core",
                "suite": "math",
                "prompt": "core prompt",
                "expected": "core",
                "scoring_method": "exact_match",
            },
            {
                "id": "caller-excluded",
                "suite": "math",
                "prompt": "caller prompt",
                "expected": "caller",
                "scoring_method": "exact_match",
            },
            {
                "id": "fresh",
                "suite": "math",
                "prompt": "fresh prompt",
                "expected": "fresh",
                "scoring_method": "exact_match",
            },
        ]
    }
    monkeypatch.setattr(EvalTower, "_load_tool_sentinels", lambda self: [])
    captured: list[str] = []

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        captured.extend(q["id"] for q in questions)
        return [
            QuestionResult(
                question_id=q["id"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=1,
                elapsed_s=1.0,
                eval_partition=q["eval_partition"],
            )
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t2(
        n=2,
        seed=42,
        exclude_qids={"caller-excluded"},
    )

    assert captured == ["fresh"]
    assert result.quality == 3.0
    policy = result.details["t1_core_exclusion_policy"]
    assert policy["source"] == "designed_core"
    assert policy["excluded_t1_core_qids"] >= 1
    assert policy["caller_excluded_qids"] == 1
    assert policy["actual_t2_core_n"] == 1


def test_eval_t2_nonpromotion_fails_closed_when_t1_core_exhausts_pool(
    tmp_path,
    monkeypatch,
) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    core_path.write_text(
        json.dumps({"__core_metadata__": True, "core_id": "core_v2"})
        + "\n"
        + json.dumps(
            {
                "id": "t1-core",
                "suite": "math",
                "prompt": "core prompt",
                "expected": "core",
                "scoring_method": "exact_match",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", "core_v2")
    monkeypatch.setenv("AUTOPILOT_T1_CORE_PATH", str(core_path))
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "t1-core",
                "suite": "math",
                "prompt": "core prompt",
                "expected": "core",
                "scoring_method": "exact_match",
            }
        ]
    }

    result = tower.eval_t2(n=1, seed=42)

    assert result.quality == 0
    assert result.reliability == 0
    policy = result.details["t1_core_exclusion_policy"]
    assert policy["actual_t2_core_n"] == 0
    assert "0 scoreable non-T1-core" in policy["error"]
