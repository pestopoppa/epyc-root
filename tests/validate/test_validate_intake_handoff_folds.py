"""Historical intake references resolve through committed folds to real tracks."""

import importlib.util
import json
from pathlib import Path

import pytest


VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/research-intake/scripts/validate_intake.py"
)
SPEC = importlib.util.spec_from_file_location("validate_intake_folds", VALIDATOR_PATH)
validate_intake = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(validate_intake)


@pytest.fixture
def refs(tmp_path, monkeypatch):
    root = tmp_path / "root"
    active = root / "handoffs/active"
    completed = root / "handoffs/completed"
    maps = root / "docs/design/backlog-refactor-2026-11"
    for directory in (active, completed, maps):
        directory.mkdir(parents=True)
    monkeypatch.setattr(validate_intake, "ROOT", root)
    return root, active, completed, maps


def fold_map(refs, route, redirects):
    folds = [
        {"destination": f"handoffs/active/{target.split('#')[0]}",
         "redirects": {"files": {source: target}}}
        for source, target in redirects
    ]
    (refs[3] / f"fold-list-{route}.json").write_text(json.dumps({
        "schema": f"brf-fold-list-{route}.v1", "folds": folds,
    }))


def errors_for(refs, ref, consumer):
    root, active, completed, _ = refs
    dirs = {"chapters": root, "experiments": root, "handoffs": [active, completed]}
    if consumer == "map":
        map_path = root / "map.md"
        map_path.write_text(f"## Category → File Mapping\n- **Handoffs**: `{ref}`\n")
        return validate_intake.validate_cross_reference_map(map_path, dirs)
    entry = {
        "id": "intake-001", "arxiv_id": None, "url": "https://example.test/source",
        "source_type": "blog", "title": "Example", "categories": ["example"],
        "novelty": "medium", "relevance": "medium", "discovered_via": "input",
        "verdict": "worth_investigating", "ingested_date": "2026-08-05",
        "cross_references": {"handoffs": [ref]},
    }
    return validate_intake.validate_index([entry], {"example"}, dirs)


@pytest.mark.parametrize("consumer", ["index", "map"])
@pytest.mark.parametrize("prefix", ["", "active/", "handoffs/active/"])
def test_chained_fold_preserves_lifted_member_track(refs, consumer, prefix):
    fold_map(refs, "1a", [("old.md", "intermediate.md#track:old")])
    fold_map(refs, "1b", [("intermediate.md", "owner.md#track:intermediate")])
    (refs[1] / "owner.md").write_text("## Track: intermediate\n\n## Track: old\n")
    assert errors_for(refs, prefix + "old.md", consumer) == []


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_rename_then_fold_acquires_anchor_track(refs, consumer):
    fold_map(refs, "1a", [("old.md", "renamed.md")])
    fold_map(refs, "1b", [("renamed.md", "owner.md#track:renamed")])
    (refs[1] / "owner.md").write_text("## Track: renamed\n")
    assert errors_for(refs, "old.md", consumer) == []


@pytest.mark.parametrize("consumer", ["index", "map"])
@pytest.mark.parametrize("text, expected", [
    ("# Owner\n", "missing '## Track: old'"),
    ("```markdown\n## Track: old\n```\n", "missing '## Track: old'"),
    ("```\n```markdown\n## Track: old\n```\n", "missing '## Track: old'"),
    ("## Track: old\n\n## Track: old\n", "ambiguous '## Track: old'"),
])
def test_fold_requires_unique_real_track_not_a_completed_stub(refs, consumer, text, expected):
    fold_map(refs, "1a", [("old.md", "owner.md#track:old")])
    (refs[2] / "old.md").write_text("# Historical pointer\n")
    (refs[1] / "owner.md").write_text(text)
    assert expected in "\n".join(errors_for(refs, "old.md", consumer))


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_fold_rejects_missing_final_owner_even_when_stub_exists(refs, consumer):
    fold_map(refs, "1a", [("old.md", "missing.md#track:old")])
    (refs[2] / "old.md").touch()
    assert "dangling committed fold target" in "\n".join(errors_for(refs, "old.md", consumer))


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_conflicting_committed_redirects_are_not_arbitrarily_selected(refs, consumer):
    fold_map(refs, "1a", [("old.md", "one.md#track:old")])
    fold_map(refs, "1b", [("old.md", "two.md#track:old")])
    for name in ("one.md", "two.md"):
        (refs[1] / name).write_text("## Track: old\n")
    assert "ambiguous committed fold mapping" in "\n".join(errors_for(refs, "old.md", consumer))


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_fold_cycles_fail_closed(refs, consumer):
    fold_map(refs, "1a", [("one.md", "two.md")])
    fold_map(refs, "1b", [("two.md", "one.md")])
    assert "cyclic committed fold mapping" in "\n".join(errors_for(refs, "one.md", consumer))


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_unknown_stem_is_not_guessed_from_matching_track(refs, consumer):
    (refs[1] / "owner.md").write_text("## Track: unknown\n")
    assert "not found" in "\n".join(errors_for(refs, "unknown.md", consumer))


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_duplicate_basenames_require_explicit_path(refs, consumer):
    for directory in refs[1:3]:
        (directory / "same.md").touch()
    assert "ambiguous handoff basename" in "\n".join(errors_for(refs, "same.md", consumer))
    assert errors_for(refs, "completed/same.md", consumer) == []


@pytest.mark.parametrize("consumer", ["index", "map"])
@pytest.mark.parametrize("separator", [":", "-"])
def test_explicit_track_is_verified_in_both_consumers(refs, consumer, separator):
    (refs[1] / "owner.md").write_text("## Track: present\n")
    assert errors_for(refs, f"owner.md#track{separator}present", consumer) == []
    assert "missing '## Track: absent'" in "\n".join(
        errors_for(refs, f"owner.md#track{separator}absent", consumer)
    )


@pytest.mark.parametrize("consumer", ["index", "map"])
@pytest.mark.parametrize("fragment", ["arbitrary-heading", "track-", "track:"])
def test_non_track_or_empty_fragments_are_rejected(refs, consumer, fragment):
    (refs[1] / "owner.md").write_text("# Owner\n\n## Arbitrary Heading\n")
    assert "handoff fragment must name" in "\n".join(
        errors_for(refs, f"owner.md#{fragment}", consumer)
    )


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_committed_meq_anchor_rename_requires_existing_owner(refs, consumer):
    fold_map(refs, "1a", [])
    path = refs[3] / "fold-list-1a.json"
    data = json.loads(path.read_text())
    data["excluded"] = {"model_evaluation_queue_BRF-T1-MEQ": ["anchor.md"]}
    path.write_text(json.dumps(data))
    (refs[1] / ".folded.json").write_text(json.dumps({"files": {
        "anchor.md": {"target": "queue.md", "track": None},
        # A registry row outside the committed 1a carve-out is not a fallback.
        "unknown.md": {"target": "queue.md", "track": None},
    }}))
    assert "dangling committed fold target" in "\n".join(errors_for(refs, "anchor.md", consumer))
    (refs[1] / "queue.md").write_text("# Queue\n\nWhole former anchor body.\n")
    assert errors_for(refs, "anchor.md", consumer) == []
    assert "not found" in "\n".join(errors_for(refs, "unknown.md", consumer))


@pytest.mark.parametrize("consumer", ["index", "map"])
def test_meq_rename_then_same_file_body_fold_requires_its_track(refs, consumer):
    fold_map(refs, "1a", [])
    path = refs[3] / "fold-list-1a.json"
    data = json.loads(path.read_text())
    data["excluded"] = {"model_evaluation_queue_BRF-T1-MEQ": ["anchor.md"]}
    path.write_text(json.dumps(data))
    (refs[1] / ".folded.json").write_text(json.dumps({"files": {
        "anchor.md": {"target": "queue.md", "track": None},
    }}))
    (refs[3] / "fold-list-1b.json").write_text(json.dumps({
        "schema": "brf-fold-list-1b.v1", "folds": [{
            "destination": "handoffs/active/queue.md", "redirects": {"files": {}},
            "tracks": [{"kind": "anchor body -> track", "from_file": "queue.md", "track": "queue"}],
        }],
    }))
    owner = refs[1] / "queue.md"
    owner.write_text("# Queue\n")
    assert "missing '## Track: queue'" in "\n".join(errors_for(refs, "anchor.md", consumer))
    owner.write_text("# Queue\n\n## Track: queue\n")
    assert errors_for(refs, "anchor.md", consumer) == []
