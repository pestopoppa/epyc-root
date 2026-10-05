"""SearXNG web-search configuration tests."""

import importlib

from src.tools.web import search as search_mod


def test_default_searxng_url_matches_managed_service_port(monkeypatch):
    """Default to the managed SearXNG Docker service, not the embedder port."""
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    reloaded = importlib.reload(search_mod)
    assert reloaded._SEARXNG_URL == "http://localhost:8888"


def test_searxng_relevance_guard_rejects_off_topic_bing_junk():
    results = [
        {
            "title": "Tickets - The Championships, Wimbledon",
            "url": "https://www.wimbledon.com/en_GB/tickets",
            "snippet": "A ticket to Wimbledon is your ticket to the unexpected.",
        },
        {
            "title": "Buy Wimbledon Tickets",
            "url": "https://wimbledontix.com/buy-wimbledon-tickets/",
            "snippet": "Compare official and resale Wimbledon tickets.",
        },
    ]

    assert not search_mod._results_pass_relevance_guard(
        "current Python 3.13.5 release notes JSON decoder strict control characters",
        results,
    )


def test_searxng_relevance_guard_rejects_current_only_python_release_junk():
    results = [
        {
            "title": "Current | Future of Banking",
            "url": "https://current.com/",
            "snippet": "Mobile banking and credit-building services for Current members.",
        },
        {
            "title": "Electric current - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Electric_current",
            "snippet": "Electric current is the flow of charged particles.",
        },
    ]

    assert not search_mod._results_pass_relevance_guard(
        "current Python 3.13.5 release date",
        results,
    )


def test_searxng_relevance_guard_accepts_on_topic_results():
    results = [
        {
            "title": "Python Release Python 3.13.5",
            "url": "https://www.python.org/downloads/release/python-3135/",
            "snippet": "Python 3.13.5 is the newest maintenance release.",
        },
        {
            "title": "JSON decoder strict control characters",
            "url": "https://docs.python.org/3/library/json.html",
            "snippet": "The JSONDecoder strict parameter controls control characters.",
        },
    ]

    assert search_mod._results_pass_relevance_guard(
        "current Python 3.13.5 release notes JSON decoder strict control characters",
        results,
    )


def test_web_search_falls_back_when_searxng_results_are_low_relevance(monkeypatch):
    monkeypatch.setattr(search_mod, "_SEARXNG_DEFAULT", True)
    monkeypatch.setattr(
        search_mod,
        "_search_searxng",
        lambda *args, **kwargs: [
            {
                "title": "Tickets - The Championships, Wimbledon",
                "url": "https://www.wimbledon.com/en_GB/tickets",
                "snippet": "A ticket to Wimbledon is your ticket to the unexpected.",
            }
        ],
    )
    monkeypatch.setattr(
        search_mod,
        "_search_duckduckgo",
        lambda query, max_results=5: [
            {
                "title": "Python Release Python 3.13.5",
                "url": "https://www.python.org/downloads/release/python-3135/",
                "snippet": "Python 3.13.5 is now available with JSON decoder fixes.",
            }
        ],
    )

    result = search_mod.web_search(
        "current Python 3.13.5 release notes JSON decoder strict control characters",
        max_results=5,
    )

    assert result["success"] is True
    assert result["backend"] == "duckduckgo"
    assert result["results"][0]["title"] == "Python Release Python 3.13.5"


def test_web_search_falls_back_when_searxng_returns_no_results(monkeypatch):
    monkeypatch.setattr(search_mod, "_SEARXNG_DEFAULT", True)
    monkeypatch.setattr(search_mod, "_search_searxng", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        search_mod,
        "_search_duckduckgo",
        lambda query, max_results=5: [
            {
                "title": "Python Release Python 3.13.5",
                "url": "https://www.python.org/downloads/release/python-3135/",
                "snippet": "Python 3.13.5 is now available with JSON decoder fixes.",
            }
        ],
    )

    result = search_mod.web_search(
        "current Python 3.13.5 release notes JSON decoder strict control characters",
        max_results=5,
    )

    assert result["success"] is True
    assert result["backend"] == "duckduckgo"
    assert result["results"][0]["url"] == "https://www.python.org/downloads/release/python-3135/"


def test_web_search_fails_when_all_backends_return_no_relevant_results(monkeypatch):
    monkeypatch.setattr(search_mod, "_SEARXNG_DEFAULT", True)
    monkeypatch.setattr(
        search_mod,
        "_search_searxng",
        lambda *args, **kwargs: [
            {
                "title": "Tickets - The Championships, Wimbledon",
                "url": "https://www.wimbledon.com/en_GB/tickets",
                "snippet": "A ticket to Wimbledon is your ticket to the unexpected.",
            }
        ],
    )
    monkeypatch.setattr(search_mod, "_search_duckduckgo", lambda query, max_results=5: [])

    result = search_mod.web_search(
        "current Python 3.13.5 release notes JSON decoder strict control characters",
        max_results=5,
    )

    assert result["success"] is False
    assert result["backend"] == "duckduckgo"
    assert result["result_count"] == 0
    assert "No relevant search results" in result["error"]


def test_web_search_fails_when_fallback_results_are_low_relevance(monkeypatch):
    monkeypatch.setattr(search_mod, "_SEARXNG_DEFAULT", True)
    monkeypatch.setattr(search_mod, "_search_searxng", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        search_mod,
        "_search_duckduckgo",
        lambda query, max_results=5: [
            {
                "title": "Tickets - The Championships, Wimbledon",
                "url": "https://www.wimbledon.com/en_GB/tickets",
                "snippet": "A ticket to Wimbledon is your ticket to the unexpected.",
            }
        ],
    )

    result = search_mod.web_search(
        "current Python 3.13.5 release notes JSON decoder strict control characters",
        max_results=5,
    )

    assert result["success"] is False
    assert result["backend"] == "duckduckgo"
    assert result["result_count"] == 0
    assert "No relevant search results" in result["error"]
