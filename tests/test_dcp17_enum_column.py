import json, pathlib
from scripts.research import dcp14_enum_column as m

FIX = pathlib.Path(__file__).parent / "fixtures" / "dcp14_enum" / "events.jsonl"


def _events():
    return [json.loads(l) for l in FIX.read_text().splitlines() if l.strip()]


def test_enum_count_rules():
    assert m.enum_count("1. a\n2) b\n(3) c\n- d\n* e\n  - [ ] f\nplain 1. not\n") == 6
    assert m.enum_count(None) is None


def test_column_appears_on_fixture_pair():
    r = m.report(_events())
    ok = [p for p in r["pairs"] if p["status"] == "ok"]
    assert len(ok) == 1
    p = ok[0]
    assert (p["parent_role"], p["delegate_role"]) == ("architect_general", "worker_general")
    assert (p["parent_enum"], p["worker_input_enum"], p["worker_response_enum"]) == (3, 2, 2)


def test_truncated_separate_and_orphan_reported():
    r = m.report(_events())
    assert r["status_counts"] == {"ok": 1, "truncated": 1}
    assert r["no_parent_prompt"] == {"worker_general": 1}
