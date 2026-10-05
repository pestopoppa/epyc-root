from src.orchestration.review_consult_gate import (
    ConsultIntent,
    ConsultSignals,
    review_before_commit_gate_from_context,
    review_before_commit_targeted_gate,
    should_consult,
)


def test_review_before_commit_gate_triggers_on_parser_data_contract_edge() -> None:
    decision = review_before_commit_targeted_gate(
        task_prompt="Fix the YAML parser so comments and quoted values round-trip correctly.",
        current_paths=["src/config_loader.py"],
        draft_paths=["src/config_loader.py"],
        delete_paths=[],
        raw_model_output="<<<FILE: src/config_loader.py>>>\n...\n<<<END>>>",
    )

    assert decision.enabled is True
    assert "parser_data_contract_or_compatibility" in decision.reasons
    assert "hidden_verifier_or_transaction_risk" in decision.reasons


def test_review_before_commit_gate_triggers_on_public_registry_surface() -> None:
    decision = review_before_commit_targeted_gate(
        task_prompt="Add a plugin entry.",
        current_paths=["src/plugins/registry.py"],
        draft_paths=["src/plugins/registry.py"],
        delete_paths=[],
        raw_model_output="<<<FILE: src/plugins/registry.py>>>\n...\n<<<END>>>",
    )

    assert decision.enabled is True
    assert "public_api_registry_or_config_surface" in decision.reasons


def test_review_before_commit_gate_skips_plain_single_file_edit() -> None:
    decision = review_before_commit_targeted_gate(
        task_prompt="Rename the greeting string.",
        current_paths=["hello.py"],
        draft_paths=["hello.py"],
        delete_paths=[],
        raw_model_output="<<<FILE: hello.py>>>\nGREETING = 'hi'\n<<<END>>>",
    )

    assert decision.enabled is False
    assert decision.reasons == ()


def test_review_before_commit_gate_skips_unparsed_draft() -> None:
    decision = review_before_commit_targeted_gate(
        task_prompt="Fix parser comments.",
        current_paths=["parser.py"],
        draft_paths=[],
        delete_paths=[],
        raw_model_output="I would change the parser.",
    )

    assert decision.enabled is False
    assert decision.reasons == ("no_parsed_file_blocks",)


def test_should_consult_triggers_on_hard_tier_routing_risk_without_lexical_match() -> None:
    decision = should_consult(
        ConsultIntent(
            skill="review_before_commit",
            task_prompt="Update behavior to satisfy the hidden workflow verifier.",
            current_paths=("worker.py",),
            draft_paths=("worker.py",),
            raw_model_output="<<<FILE: worker.py>>>\nVALUE = 2\n<<<END>>>",
        ),
        ConsultSignals(
            tier=3,
            difficulty_band="hard",
            factual_risk_band="high",
            memrl_hints=("prior consult helped hidden verifier tasks",),
        ),
    )

    assert decision.enabled is True
    assert "tier_3_hard_workflow" in decision.reasons
    assert "routing_or_blast_radius_risk" in decision.reasons
    assert "difficulty_hard" in decision.reasons
    assert "memrl_consult_hint" in decision.reasons


def test_should_consult_skips_easy_low_latency_work_without_risk() -> None:
    decision = should_consult(
        ConsultIntent(
            skill="review_before_commit",
            task_prompt="Rename a constant.",
            current_paths=("hello.py",),
            draft_paths=("hello.py",),
            raw_model_output="<<<FILE: hello.py>>>\nNAME = 'x'\n<<<END>>>",
        ),
        ConsultSignals(tier=1, latency_budget_remaining_s=2.0),
    )

    assert decision.enabled is False
    assert decision.reasons == ("latency_budget_too_low",)


def test_should_consult_rejects_unsupported_skill() -> None:
    decision = should_consult(
        ConsultIntent(skill="unrelated_skill", draft_paths=("x.py",)),
        ConsultSignals(tier=3, factual_risk_band="high"),
    )

    assert decision.enabled is False
    assert decision.reasons == ("unsupported_consult_skill",)


def test_review_before_commit_gate_from_context_passes_signals() -> None:
    decision = review_before_commit_gate_from_context(
        {
            "task_prompt": "Update hidden workflow behavior.",
            "current_paths": ["worker.py"],
            "draft_paths": ["worker.py"],
            "raw_model_output": "<<<FILE: worker.py>>>\nVALUE = 2\n<<<END>>>",
            "signals": {
                "tier": 2,
                "difficulty_band": "hard",
                "factual_risk_score": 0.9,
                "memrl_hints": ["review_before_commit useful for this shape"],
            },
        }
    )

    assert decision.enabled is True
    assert "tier_2_hard_workflow" in decision.reasons
    assert "memrl_consult_hint" in decision.reasons


def test_review_before_commit_gate_from_context_accepts_single_memrl_hint_string() -> None:
    decision = review_before_commit_gate_from_context(
        {
            "task_prompt": "Update hidden workflow behavior.",
            "current_paths": ["worker.py"],
            "draft_paths": ["worker.py"],
            "raw_model_output": "<<<FILE: worker.py>>>\nVALUE = 2\n<<<END>>>",
            "signals": {
                "tier": 3,
                "difficulty_band": "hard",
                "memrl_hints": "review_before_commit useful for parser_data_contract",
            },
        }
    )

    assert decision.enabled is True
    assert "memrl_consult_hint" in decision.reasons
