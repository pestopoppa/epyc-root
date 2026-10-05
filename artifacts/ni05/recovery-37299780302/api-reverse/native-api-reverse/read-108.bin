from __future__ import annotations

from src.llm_primitives.backend import (
    _infer_topology_role_for_urls,
    _normalise_role_urls,
)


def test_normalise_role_urls_strips_full_marker() -> None:
    assert _normalise_role_urls("full:http://localhost:8070, http://localhost:8080") == (
        "http://localhost:8070",
        "http://localhost:8080",
    )


def test_infer_topology_role_for_shared_url_alias() -> None:
    role_urls = {
        "frontdoor": (
            "http://localhost:8070",
            "http://localhost:8080",
            "http://localhost:8180",
        ),
        "coder_escalation": (
            "http://localhost:8070",
            "http://localhost:8080",
            "http://localhost:8180",
        ),
    }

    assert _infer_topology_role_for_urls(
        "coder_escalation",
        role_urls,
        {"frontdoor"},
    ) == "frontdoor"


def test_infer_topology_role_leaves_unique_role_unchanged() -> None:
    role_urls = {
        "frontdoor": ("http://localhost:8070",),
        "ingest_long_context": ("http://localhost:8085",),
    }

    assert _infer_topology_role_for_urls(
        "ingest_long_context",
        role_urls,
        {"frontdoor"},
    ) == "ingest_long_context"
