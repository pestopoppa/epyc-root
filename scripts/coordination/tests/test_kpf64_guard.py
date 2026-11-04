if __name__ == "__main__":
    raise SystemExit("Run this file with pytest; direct execution is refused.")

import json
from pathlib import Path

import pytest

from scripts.coordination.kvfork.kpf64_guard.preflight import find_unreachable


def write_sample(tmp_path, parents, children):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    rows = []
    for parent in parents:
        pid = parent["id"]
        listed = parent.get("listed_children", [])
        session = {"id": pid, "replayable": parent.get("replayable", True),
                   "turns": [{} for _ in range(parent.get("turns", 0))],
                   "children": listed}
        (sessions / f"{pid}.json").write_text(json.dumps(session))
        rows.append({"id": pid, "parent": None, "replayable": session["replayable"],
                     "children": parent.get("declared_count", len(listed))})
    rows.extend(children)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": "kpf64.sessions.v2", "sessions": rows}))
    return manifest, sessions


def kinds(problems):
    return {p["type"] for p in problems}


def test_virtual_parent_allows_large_parent_turn_and_replayable_valid_index(tmp_path):
    manifest, sessions = write_sample(
        tmp_path,
        [
            {"id": "virtual", "replayable": False, "turns": 0,
             "listed_children": [{"id": "v.c00", "parent_turn": 10**9}]},
            {"id": "replay", "replayable": True, "turns": 4,
             "listed_children": [{"id": "r.c00", "parent_turn": 3}]},
        ],
        [{"id": "v.c00", "parent": "virtual", "requests": 2},
         {"id": "r.c00", "parent": "replay", "requests": 3}],
    )
    assert find_unreachable(manifest, sessions) == []


def test_replayable_parent_rejects_index_equal_to_retained_length(tmp_path):
    manifest, sessions = write_sample(
        tmp_path,
        [{"id": "replay", "replayable": True, "turns": 2,
          "listed_children": [{"id": "r.c00", "parent_turn": 2}]}],
        [{"id": "r.c00", "parent": "replay", "requests": 5}],
    )
    problems = find_unreachable(manifest, sessions)
    assert [(p["type"], p["child"], p["parent_turn"]) for p in problems
            if p["type"] == "unreachable_parent_turn"] == [("unreachable_parent_turn", "r.c00", 2)]


@pytest.mark.parametrize("bad_index", [None, True, False, -1, 1.0, "2"])
def test_all_parents_reject_missing_boolean_noninteger_and_negative_indices(tmp_path, bad_index):
    child = {"id": "v.c00"}
    if bad_index is not None:
        child["parent_turn"] = bad_index
    manifest, sessions = write_sample(
        tmp_path,
        [{"id": "virtual", "replayable": False, "turns": 0, "listed_children": [child]}],
        [{"id": "v.c00", "parent": "virtual", "requests": 1}],
    )
    problems = find_unreachable(manifest, sessions)
    assert "invalid_parent_turn" in kinds(problems)
    assert not any(p["type"] == "unreachable_parent_turn" for p in problems)


def test_manifest_child_missing_from_parent_is_rejected(tmp_path):
    manifest, sessions = write_sample(
        tmp_path,
        [{"id": "virtual", "replayable": False, "turns": 0, "listed_children": []}],
        [{"id": "v.c00", "parent": "virtual", "requests": 1}],
    )
    assert "manifest_child_missing_from_parent" in kinds(find_unreachable(manifest, sessions))


def test_duplicate_child_id_in_parent_is_rejected(tmp_path):
    c = {"id": "v.c00", "parent_turn": 5}
    manifest, sessions = write_sample(
        tmp_path,
        [{"id": "virtual", "replayable": False, "turns": 0, "listed_children": [c, c]}],
        [{"id": "v.c00", "parent": "virtual", "requests": 1}],
    )
    assert "duplicate_child_id" in kinds(find_unreachable(manifest, sessions))


def test_unknown_child_in_parent_is_rejected(tmp_path):
    manifest, sessions = write_sample(
        tmp_path,
        [{"id": "virtual", "replayable": False, "turns": 0,
          "listed_children": [{"id": "v.unknown", "parent_turn": 5}]}],
        [],
    )
    assert "unknown_child" in kinds(find_unreachable(manifest, sessions))


def test_child_listed_under_wrong_parent_is_rejected(tmp_path):
    manifest, sessions = write_sample(
        tmp_path,
        [{"id": "p1", "replayable": False, "turns": 0,
          "listed_children": [{"id": "c", "parent_turn": 1}]},
         {"id": "p2", "replayable": False, "turns": 0, "listed_children": []}],
        [{"id": "c", "parent": "p2", "requests": 1}],
    )
    assert "child_parent_mismatch" in kinds(find_unreachable(manifest, sessions))


def test_manifest_child_with_missing_parent_row_is_rejected(tmp_path):
    manifest, sessions = write_sample(
        tmp_path,
        [{"id": "virtual", "replayable": False, "turns": 0, "listed_children": []}],
        [{"id": "orphan.c00", "parent": "missing", "requests": 1}],
    )
    problems = find_unreachable(manifest, sessions)
    assert any(p["type"] == "orphan_manifest_parent" and p["child"] == "orphan.c00"
               for p in problems)


def test_manifest_parent_id_cannot_escape_sessions_directory(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (tmp_path / "outside.json").write_text(json.dumps({"turns": [], "children": []}))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sessions": [{"id": "../outside", "parent": None}]}))
    problems = find_unreachable(manifest, sessions)
    assert any(p["type"] == "unsafe_session_id" and p["child"] == "../outside"
               for p in problems)


def test_frozen_family_input_rejects_exact_eight_opencode_children():
    root = Path("/mnt/raid0/llm/tmp/qb2-kpf64/sessions-families-n4-cap161k")
    manifest = root / "manifest.json"
    if not manifest.is_file():
        pytest.skip("frozen KPF-64 family input is unavailable on this host")
    problems = find_unreachable(manifest, root)
    unreachable = [p for p in problems if p["type"] == "unreachable_parent_turn"]
    assert len(unreachable) == 8
    assert {p["child"] for p in unreachable} == {f"opencode-01.c{i:02d}" for i in range(8)}
    assert {p["parent_turn"] for p in unreachable} == {94, 95, 96, 97, 98, 104, 105, 110}
    assert {p["child_requests"] for p in unreachable} == {7, 10, 23, 24, 28, 38}


