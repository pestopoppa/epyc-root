"""Unit tests for the shared chat-completions-roles source of truth (review finding #5 2026-05-27).

The chat route's template-skip logic and the backend router must agree on this set; before the
shared module they carried divergent inline defaults. The env var is unset in prod, so the
generated stack-prior default is load-bearing.
"""
from src import chat_completions_roles as cc_roles
from src.chat_completions_roles import chat_completions_roles
from src.roles import Role


def test_default_comes_from_live_stack_priors(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES", raising=False)
    monkeypatch.setattr(
        "src.chat_completions_roles._live_chat_completions_roles",
        lambda: {
            "coder_escalation",
            "frontdoor",
            "toolrunner",
            "worker_general",
            "worker_math",
            "worker_summarize",
        },
    )

    roles = chat_completions_roles()

    assert roles == {
        "coder_escalation",
        "frontdoor",
        "toolrunner",
        "worker_general",
        "worker_math",
        "worker_summarize",
    }


def test_degraded_fallback_is_narrow_when_priors_missing(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES", raising=False)
    monkeypatch.setattr("src.chat_completions_roles._live_chat_completions_roles", lambda: set())
    monkeypatch.setattr(
        cc_roles,
        "HOT_SERVERS",
        (
            {"port": 8070, "roles": ["frontdoor", "coder_escalation", "worker_summarize"]},
            {"port": 8072, "roles": ["worker_general", "worker_explore", "worker_math", "toolrunner"]},
            {"port": 8083, "roles": ["architect_general"]},
            {"port": 8085, "roles": ["ingest_long_context"]},
            {"port": 8086, "roles": ["worker_vision"]},
            {"port": 8090, "roles": ["embedder"]},
        ),
    )
    monkeypatch.setattr(cc_roles, "WARM_SERVERS", ({"port": 8102, "roles": ["worker_fast"]},))
    monkeypatch.setattr(
        cc_roles,
        "ROLE_LAUNCH_META",
        {
            "frontdoor": {
                "mode": "default",
                "shared_with_first_n": ["coder_escalation", "worker_summarize"],
            },
            "worker_general": {
                "mode": "worker_pool",
                "worker_type": "explore",
                "shared_with_first_n": ["worker_explore", "worker_math", "toolrunner"],
            },
            "architect_general": {"mode": "default"},
            "ingest_long_context": {"mode": "default"},
            "worker_vision": {"mode": "vision"},
            "embedder": {"mode": "embedding"},
            "worker_fast": {"mode": "worker_pool", "worker_type": "fast"},
        },
    )

    assert chat_completions_roles() == {
        str(Role.FRONTDOOR),
        str(Role.CODER_ESCALATION),
        str(Role.WORKER_GENERAL),
        str(Role.WORKER_MATH),
        str(Role.WORKER_SUMMARIZE),
        str(Role.TOOLRUNNER),
    }


def test_degraded_fallback_preserves_manifest_order_and_alias_policy(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES", raising=False)
    monkeypatch.setattr("src.chat_completions_roles._live_chat_completions_roles", lambda: set())
    monkeypatch.setattr(
        cc_roles,
        "HOT_SERVERS",
        (
            {"roles": ["worker_explore", "worker_math", "architect_general"]},
            {"roles": ["coder_escalation", "frontdoor"]},
            {"roles": ["toolrunner", "worker_vision"]},
        ),
    )
    monkeypatch.setattr(cc_roles, "WARM_SERVERS", ())
    monkeypatch.setattr(
        cc_roles,
        "ROLE_LAUNCH_META",
        {
            "frontdoor": {
                "mode": "default",
                "shared_with_first_n": ["coder_escalation"],
            },
            "worker_general": {
                "mode": "worker_pool",
                "worker_type": "explore",
                "shared_with_first_n": ["worker_explore", "worker_math", "toolrunner"],
            },
            "architect_general": {"mode": "default"},
            "worker_vision": {"mode": "vision"},
        },
    )

    assert chat_completions_roles() == {
        str(Role.WORKER_GENERAL),
        str(Role.WORKER_MATH),
        str(Role.CODER_ESCALATION),
        str(Role.FRONTDOOR),
        str(Role.TOOLRUNNER),
    }


def test_env_override_and_whitespace(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES", " foo , bar ,")
    assert chat_completions_roles() == {"foo", "bar"}
