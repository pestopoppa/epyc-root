"""Tests for archive-source surface static audit."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import archive_source_surface_audit as audit_mod  # noqa: E402


def _write_surface(root: Path, requirement: audit_mod.SurfaceRequirement) -> None:
    path = root / requirement.path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(requirement.must_contain), encoding="utf-8")


def test_archive_source_surface_audit_passes_on_current_repo() -> None:
    report = audit_mod.build_archive_source_surface_audit(REPO_ROOT)

    assert report["ok"] is True
    assert report["failed_count"] == 0
    assert report["surface_count"] == len(audit_mod.REQUIREMENTS)


def test_archive_source_surface_audit_reports_missing_fragment(tmp_path: Path) -> None:
    for requirement in audit_mod.REQUIREMENTS:
        _write_surface(tmp_path, requirement)
    first = audit_mod.REQUIREMENTS[0]
    path = tmp_path / first.path
    path.write_text("ARCHIVE_SOURCE_JOURNAL_ALL\n", encoding="utf-8")

    report = audit_mod.build_archive_source_surface_audit(tmp_path)
    failed = [result for result in report["results"] if not result["ok"]]

    assert report["ok"] is False
    assert report["failed_count"] == 1
    assert failed[0]["name"] == first.name
    assert "ARCHIVE_SOURCE_STATE" in failed[0]["missing"]


def test_cli_json_strict_returns_one_on_failed_audit(tmp_path: Path, capsys) -> None:
    for requirement in audit_mod.REQUIREMENTS:
        _write_surface(tmp_path, requirement)
    (tmp_path / audit_mod.REQUIREMENTS[1].path).write_text("", encoding="utf-8")

    rc = audit_mod.main(["--root", str(tmp_path), "--json", "--strict"])
    out = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert out["ok"] is False
    assert out["failed_count"] == 1


def test_render_markdown_includes_failed_surface(tmp_path: Path) -> None:
    for requirement in audit_mod.REQUIREMENTS:
        _write_surface(tmp_path, requirement)
    (tmp_path / audit_mod.REQUIREMENTS[2].path).write_text("", encoding="utf-8")

    rendered = audit_mod.render_markdown(
        audit_mod.build_archive_source_surface_audit(tmp_path)
    )

    assert "# AutoPilot Archive Source Surface Audit" in rendered
    assert "safety_gate_uses_journal_archive_context" in rendered
    assert "- Status: failed" in rendered
