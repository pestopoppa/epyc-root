"""Consumer-level tests for reward delivery propagation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
import sqlite3


_ROOT = Path(__file__).resolve().parents[2]
_BENCH = _ROOT / "scripts" / "benchmark"
_AUTO = _ROOT / "scripts" / "autopilot" / "species"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BENCH))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_batch_3way_propagates_reward_delivery_summary():
    mod = _load_module("seed_specialist_routing_test", _BENCH / "seed_specialist_routing.py")
    prompt = {"id": "q1", "suite": "general", "prompt": "2+2?", "expected": "4"}
    role_results = {"SELF:direct": SimpleNamespace(passed=True)}
    delivery = {"submitted": 2, "acknowledged": 1, "failed": 1, "failure_reasons": {"ARCHITECT": "http_503"}}

    with (
        patch.object(mod, "_check_server_health", return_value=True),
        patch.object(mod, "evaluate_question_3way", return_value=(role_results, {"SELF:direct": 1.0}, {})),
        patch.object(mod, "_inject_3way_rewards_http", return_value=delivery),
        patch.object(mod, "checkpoint_result") as checkpoint_result,
        patch.object(mod, "record_seen") as record_seen,
        patch("httpx.Client", return_value=MagicMock()),
    ):
        mod.state.shutdown = False
        results = mod.run_batch_3way(
            suites=["general"],
            sample_per_suite=1,
            seed=1,
            url="http://localhost:8000",
            timeout=30,
            session_id="sess",
            questions_override=[prompt],
        )

    assert len(results) == 1
    assert results[0].rewards_delivery == delivery
    assert results[0].rewards_injected == 1
    checkpoint_result.assert_called_once()
    record_seen.assert_called_once_with("q1", "general", "sess")


def test_seeder_run_batch_accumulates_acknowledged_rewards():
    mod = _load_module("species_seeder_test", _AUTO / "seeder.py")
    question = {"id": "q1", "suite": "general", "prompt": "2+2?", "expected": "4"}
    role_results = {"frontdoor": SimpleNamespace(passed=True)}
    delivery = {"submitted": 3, "acknowledged": 2, "failed": 1, "failure_reasons": {"architect_general": "http_503"}}
    fake_roles = [{"name": "frontdoor", "registry_key": "frontdoor", "model_role": "frontdoor", "port": 8080, "is_heavy": True, "cost_tier": 2}]
    client_cm = MagicMock()
    client = Mock()
    client_cm.__enter__.return_value = client
    client_cm.__exit__.return_value = False

    with (
        patch.object(mod, "sample_unseen_questions", return_value=[question]),
        patch.object(mod, "discover_active_roles", return_value=fake_roles),
        patch.object(mod, "evaluate_question_per_role", return_value=(role_results, {"frontdoor": 1.0}, {"avg_td_error": 0.2, "roles_tested": ["frontdoor"]})),
        patch.object(mod, "_inject_per_role_rewards_http", return_value=delivery),
        patch.object(mod.Seeder, "_get_memory_count", return_value=0),
        patch("httpx.Client", return_value=client_cm),
    ):
        seeder = mod.Seeder(url="http://localhost:8000", timeout=30, batch_size=1, dry_run=False)
        result = seeder.run_batch(n_questions=1, suites=["general"], seed=1)

    assert result.rewards_injected == 2
    assert result.rewards_delivery == [delivery]
    assert result.results[0]["rewards"] == {"frontdoor": 1.0}
    assert result.n_correct == 1
    assert result.n_role_successes == 1


def test_seeder_run_batch_counts_question_success_once_per_question():
    mod = _load_module("species_seeder_question_success_test", _AUTO / "seeder.py")
    question = {"id": "q1", "suite": "general", "prompt": "2+2?", "expected": "4"}
    fake_roles = [
        {"name": "frontdoor", "registry_key": "frontdoor", "model_role": "frontdoor", "port": 8070, "is_heavy": True, "cost_tier": 2},
        {"name": "worker_general", "registry_key": "worker_general", "model_role": "worker_general", "port": 8072, "is_heavy": False, "cost_tier": 1},
        {"name": "architect_general", "registry_key": "architect_general", "model_role": "architect_general", "port": 8083, "is_heavy": True, "cost_tier": 3},
    ]
    rewards = {
        "frontdoor": 1.0,
        "worker_general": 1.0,
        "architect_general": None,
    }
    client_cm = MagicMock()
    client_cm.__enter__.return_value = Mock()
    client_cm.__exit__.return_value = False

    with (
        patch.object(mod, "sample_unseen_questions", return_value=[question]),
        patch.object(mod, "discover_active_roles", return_value=fake_roles),
        patch.object(mod, "evaluate_question_per_role", return_value=({}, rewards, {"avg_td_error": 0.0, "roles_tested": list(rewards)})),
        patch.object(mod, "_inject_per_role_rewards_http", return_value={"acknowledged": 2}),
        patch.object(mod.Seeder, "_get_memory_count", return_value=0),
        patch("httpx.Client", return_value=client_cm),
    ):
        seeder = mod.Seeder(url="http://localhost:8000", timeout=30, batch_size=1, dry_run=False)
        result = seeder.run_batch(n_questions=1, suites=["general"], seed=1)

    assert result.n_correct == 1
    assert result.n_role_successes == 2
    assert result.per_action_stats["architect_general"] == {"total": 1, "correct": 0}


def test_seeder_run_batch_ignores_strategy_hints_without_mutating_question():
    mod = _load_module("species_seeder_hints_test", _AUTO / "seeder.py")
    question = {"id": "q1", "suite": "general", "prompt": "2+2?", "expected": "4"}
    role_results = {"frontdoor": SimpleNamespace(passed=True)}
    fake_roles = [
        {
            "name": "frontdoor",
            "registry_key": "frontdoor",
            "model_role": "frontdoor",
            "port": 8080,
            "is_heavy": True,
            "cost_tier": 2,
        }
    ]
    client_cm = MagicMock()
    client_cm.__enter__.return_value = Mock()
    client_cm.__exit__.return_value = False
    seen_prompts = []

    def _evaluate_question_per_role(*, prompt_info, **_kwargs):
        seen_prompts.append(prompt_info["prompt"])
        return (
            role_results,
            {"frontdoor": 1.0},
            {"avg_td_error": 0.2, "roles_tested": ["frontdoor"]},
        )

    with (
        patch.object(mod, "sample_unseen_questions", return_value=[question]),
        patch.object(mod, "discover_active_roles", return_value=fake_roles),
        patch.object(mod, "evaluate_question_per_role", side_effect=_evaluate_question_per_role),
        patch.object(mod, "_inject_per_role_rewards_http", return_value={"acknowledged": 1}),
        patch.object(mod.Seeder, "_get_memory_count", return_value=0),
        patch("httpx.Client", return_value=client_cm),
    ):
        seeder = mod.Seeder(
            url="http://localhost:8000",
            timeout=30,
            batch_size=1,
            dry_run=False,
        )
        result = seeder.run_batch(
            n_questions=1,
            suites=["general"],
            seed=1,
            strategy_hints="Prefer balanced suites.",
        )

    assert question["prompt"] == "2+2?"
    assert seen_prompts[0] == "2+2?"
    assert "### Planner Context" not in seen_prompts[0]
    assert "Prefer balanced suites." not in seen_prompts[0]
    assert "planner_hints_applied" not in result.results[0]


def test_seeder_memory_count_reads_sqlite_without_episodic_store_import(tmp_path):
    mod = _load_module("species_seeder_count_test", _AUTO / "seeder.py")
    db_path = tmp_path / "episodic.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT NOT NULL)"
        )
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, ?)",
            [("a", "routing"), ("b", "routing"), ("c", "escalation")],
        )
        conn.commit()

    with patch.object(mod, "_memory_db", db_path):
        seeder = mod.Seeder(dry_run=True)
        assert seeder.get_memory_count() == 2


def test_seeder_restore_state_recovers_explicit_convergence_fields():
    mod = _load_module("species_seeder_restore_test", _AUTO / "seeder.py")
    with patch.object(mod, "discover_active_roles", return_value=[]):
        seeder = mod.Seeder(dry_run=True)
    seeder.restore_state(
        {
            "td_errors": [0.2, 0.04, 0.03],
            "batch_count": 7,
            "consecutive_converged": 5,
        }
    )

    assert seeder.convergence_status()["batch_count"] == 7
    assert seeder.convergence_status()["consecutive_converged"] == 5
    assert seeder.is_converged is True
    assert seeder.export_state()["td_errors"] == [0.2, 0.04, 0.03]


def test_seeder_restore_state_reconstructs_legacy_td_error_streak():
    mod = _load_module("species_seeder_legacy_restore_test", _AUTO / "seeder.py")
    with patch.object(mod, "discover_active_roles", return_value=[]):
        seeder = mod.Seeder(dry_run=True)
    seeder.restore_state({"td_errors": [0.2, 0.03, 0.04, 0.01]})

    status = seeder.convergence_status()
    assert status["batch_count"] == 4
    assert status["consecutive_converged"] == 3
    assert status["last_td_error"] == 0.01
    assert seeder.is_converged is False
