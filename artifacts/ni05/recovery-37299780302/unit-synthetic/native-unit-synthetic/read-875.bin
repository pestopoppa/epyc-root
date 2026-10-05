"""Ordering contract for ``src.trace.query.query``.

``text=`` searches rank by FTS5 bm25 (most relevant first) unless the caller asks
for ``order="recency"``. Filter-only queries have no relevance score and stay
newest-first.
"""

from __future__ import annotations

import pytest

from src.trace import Event, EventSource, ensure_schema, upsert_events
from src.trace.cli import main as trace_cli_main
from src.trace.navigation import search_records
from src.trace.query import query


def _event(line: int, ts: str, summary: str, body: str) -> Event:
    return Event(
        ts_utc=ts,
        source=EventSource.AGENT_AUDIT,
        source_path="/trace/order.log",
        source_line=line,
        session_id="s",
        category="task_end",
        summary=summary,
        detail_json=f'{{"body":"{body}"}}',
    )


@pytest.fixture()
def db_path(tmp_path):
    """The most relevant document ("kraken" x4) is the OLDEST row."""
    path = tmp_path / "events.sqlite"
    conn = ensure_schema(path)
    upsert_events(
        conn,
        [
            _event(1, "2026-01-01T00:00:00+00:00", "kraken kraken kraken",
                   "kraken sighting report"),
            _event(2, "2026-02-01T00:00:00+00:00", "ship log",
                   "weather calm, crew fine, one passing mention of a kraken rumour among "
                   "many unrelated words about rope sails tar wood rations and navigation"),
            _event(3, "2026-03-01T00:00:00+00:00", "harbour note",
                   "kraken maybe, plus lots of filler text on cargo manifests tariffs "
                   "dock fees pilots tides moorings and harbour masters paperwork"),
            _event(4, "2026-04-01T00:00:00+00:00", "unrelated", "no match here"),
        ],
    )
    conn.close()
    return path


def test_text_query_ranks_most_relevant_first_even_when_older(db_path):
    rows = query(db_path=db_path, text="kraken", limit=1)
    assert [r["summary"] for r in rows] == ["kraken kraken kraken"]


def test_text_query_full_order_is_bm25(db_path):
    rows = query(db_path=db_path, text="kraken")
    assert rows[0]["summary"] == "kraken kraken kraken"
    assert {r["summary"] for r in rows} == {"kraken kraken kraken", "ship log", "harbour note"}


def test_text_query_recency_order_is_explicit(db_path):
    rows = query(db_path=db_path, text="kraken", order="recency")
    assert [r["summary"] for r in rows] == ["harbour note", "ship log", "kraken kraken kraken"]
    rows = query(db_path=db_path, text="kraken", order="recency", limit=1)
    assert [r["summary"] for r in rows] == ["harbour note"]


def test_text_query_relevance_respects_filters(db_path):
    rows = query(db_path=db_path, text="kraken", from_ts="2026-02-01T00:00:00+00:00")
    assert rows[0]["summary"] in {"ship log", "harbour note"}
    assert "kraken kraken kraken" not in {r["summary"] for r in rows}


def test_filter_only_query_stays_newest_first(db_path):
    rows = query(db_path=db_path, session_id="s")
    assert [r["summary"] for r in rows] == [
        "unrelated", "harbour note", "ship log", "kraken kraken kraken"]
    # Explicit recency is identical; relevance without text is refused.
    assert query(db_path=db_path, session_id="s", order="recency") == rows
    with pytest.raises(ValueError):
        query(db_path=db_path, session_id="s", order="relevance")


def test_invalid_order_rejected(db_path):
    with pytest.raises(ValueError):
        query(db_path=db_path, text="kraken", order="random")


def test_search_records_is_relevance_ranked_under_limit(db_path):
    rows = search_records("kraken", db_path=db_path, limit=1)
    assert [r["summary"] for r in rows] == ["kraken kraken kraken"]
    rows = search_records("kraken", db_path=db_path, limit=1, order="recency")
    assert [r["summary"] for r in rows] == ["harbour note"]


def test_cli_query_order_flag(db_path, capsys):
    import json

    assert trace_cli_main(["--db", str(db_path), "query", "--text", "kraken",
                           "--limit", "1", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["summary"] == "kraken kraken kraken"
    assert trace_cli_main(["--db", str(db_path), "query", "--text", "kraken",
                           "--order", "recency", "--limit", "1", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["summary"] == "harbour note"


def test_cli_search_records_order_flag(db_path, capsys):
    import json

    assert trace_cli_main(["--db", str(db_path), "search-records", "--text", "kraken",
                           "--order", "recency", "--limit", "1", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["summary"] == "harbour note"


def test_rrf_fusion_consumes_bm25_rank(db_path):
    rows = search_records("kraken", db_path=db_path, limit=3,
                          vector_rows=[{"id": 999, "summary": "vec-only"}])
    # Rank 1 of the lexical list and rank 1 of the vector list tie; the bm25 winner
    # must be the lexical rank-1 row, not the newest match.
    lexical_top = [r for r in rows if r.get("_rrf_sources") == ["fts"]][0]
    assert lexical_top["summary"] == "kraken kraken kraken"
