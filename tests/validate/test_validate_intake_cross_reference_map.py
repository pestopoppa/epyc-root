"""Regression tests for the research-intake cross-reference-map validator."""

import importlib.util
from pathlib import Path


VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/research-intake/scripts/validate_intake.py"
)
SPEC = importlib.util.spec_from_file_location("validate_intake", VALIDATOR_PATH)
validate_intake = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(validate_intake)


def test_cross_reference_map_accepts_active_and_completed_handoffs(tmp_path, monkeypatch):
    root = tmp_path / "root"
    active = root / "handoffs/active"
    completed = root / "handoffs/completed"
    chapters = tmp_path / "chapters"
    experiments = tmp_path / "experiments"
    for directory in (active, completed, chapters, experiments):
        directory.mkdir(parents=True)
    (active / "live.md").touch()
    (completed / "done.md").touch()
    (chapters / "chapter.md").touch()
    (experiments / "experiment.md").touch()
    map_path = tmp_path / "map.md"
    map_path.write_text(
        "## Category → File Mapping\n"
        "- **Chapters**: `chapter.md`\n"
        "- **Handoffs**: `live.md`, `completed/done.md`\n"
        "- **Experiments**: `experiment.md`\n"
        "## File Locations\n"
        "- **Handoffs**: `not-a-reference.md`\n"
    )
    monkeypatch.setattr(validate_intake, "ROOT", root)

    errors = validate_intake.validate_cross_reference_map(
        map_path,
        {"chapters": chapters, "experiments": experiments, "handoffs": [active, completed]},
    )

    assert errors == []


def test_cross_reference_map_reports_missing_mapping_target(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    map_path = tmp_path / "map.md"
    map_path.write_text("## Category → File Mapping\n- **Handoffs**: `missing.md`\n")
    monkeypatch.setattr(validate_intake, "ROOT", root)

    errors = validate_intake.validate_cross_reference_map(
        map_path,
        {"chapters": tmp_path, "experiments": tmp_path, "handoffs": [tmp_path / "handoffs"]},
    )

    assert errors == ["cross-reference-map: handoffs 'missing.md' not found"]
