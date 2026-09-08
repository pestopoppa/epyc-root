from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / ".claude" / "skills" / "project-wiki" / "scripts" / "compile_sources.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "project_wiki_compile_sources",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _configure_temp_project(module, root: Path) -> None:
    module.ROOT = root
    module.CONFIG = {
        "last_compile": "wiki/.last_compile",
        "source_manifest": "wiki/source_manifest.json",
        "skip_filenames": ["INDEX.md"],
        "skip_patterns": ["*-index.md"],
        "source_dirs": [
            {"path": "handoffs/active", "type": "handoff-active", "recurse": False},
            {"path": "progress", "type": "progress", "recurse": True},
        ],
    }
    module.LAST_COMPILE_PATH = root / "wiki" / ".last_compile"
    module.SOURCE_MANIFEST_PATH = root / "wiki" / "source_manifest.json"
    module.SKIP_FILENAMES = set(module.CONFIG["skip_filenames"])
    module.SKIP_PATTERNS = module.CONFIG["skip_patterns"]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_manifest_sources_include_content_hash_and_source_set_hash(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    _write(tmp_path / "handoffs" / "active" / "alpha.md", "# Alpha\n\nFirst.\n")
    _write(tmp_path / "progress" / "2026-06" / "day.md", "# Day\n\nSecond.\n")
    _write(tmp_path / "handoffs" / "active" / "skip-index.md", "# Skip\n")

    sources = module.scan_sources(0.0, None)
    manifest = module.build_manifest(sources, "full")

    assert [source["path"] for source in sources] == [
        "handoffs/active/alpha.md",
        "progress/2026-06/day.md",
    ]
    expected_hash = hashlib.sha256("# Alpha\n\nFirst.\n".encode("utf-8")).hexdigest()
    assert sources[0]["content_hash"] == expected_hash
    assert len(manifest["source_set_hash"]) == 64
    assert manifest["kind"] == module.MANIFEST_KIND
    assert manifest["schema_version"] == module.MANIFEST_SCHEMA_VERSION
    assert manifest["writer_evidence_policy"] == module.WRITER_EVIDENCE_POLICY

    reversed_manifest = module.build_manifest(list(reversed(sources)), "full")
    assert reversed_manifest["source_set_hash"] == manifest["source_set_hash"]


def test_manifest_drift_report_rejects_missing_writer_evidence_policy(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    manifest_path = tmp_path / "wiki" / "source_manifest.json"
    _write(alpha, "# Alpha\n\nFirst.\n")
    manifest = module.build_manifest(module.scan_sources(0.0, None), "full")
    manifest.pop("writer_evidence_policy")
    module.write_manifest(manifest_path, manifest)

    report = module.build_manifest_drift_report(manifest_path)

    assert report["ok"] is False
    assert report["writer_evidence_policy_ok"] is False
    assert report["writer_evidence_policy_errors"] == [
        "writer_evidence_policy missing"
    ]


def test_manifest_drift_report_rejects_weakened_writer_evidence_policy(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    manifest_path = tmp_path / "wiki" / "source_manifest.json"
    _write(alpha, "# Alpha\n\nFirst.\n")
    manifest = module.build_manifest(module.scan_sources(0.0, None), "full")
    manifest["writer_evidence_policy"]["minimum_source_references"] = 1
    module.write_manifest(manifest_path, manifest)

    report = module.build_manifest_drift_report(manifest_path)

    assert report["ok"] is False
    assert report["writer_evidence_policy_ok"] is False
    assert report["writer_evidence_policy_errors"] == [
        "writer_evidence_policy minimum_source_references must be 3, got 1"
    ]


def test_source_set_hash_changes_when_source_content_hash_changes(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    source = tmp_path / "handoffs" / "active" / "alpha.md"
    _write(source, "# Alpha\n\nFirst.\n")

    first_hash = module.build_manifest(module.scan_sources(0.0, None), "full")[
        "source_set_hash"
    ]
    _write(source, "# Alpha\n\nChanged.\n")
    second_hash = module.build_manifest(module.scan_sources(0.0, None), "full")[
        "source_set_hash"
    ]

    assert second_hash != first_hash


def test_manifest_drift_report_detects_added_changed_and_removed_sources(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    beta = tmp_path / "handoffs" / "active" / "beta.md"
    gamma = tmp_path / "progress" / "2026-06" / "gamma.md"
    manifest_path = tmp_path / "wiki" / "source_manifest.json"
    _write(alpha, "# Alpha\n\nFirst.\n")
    _write(beta, "# Beta\n\nSecond.\n")
    module.write_manifest(
        manifest_path,
        module.build_manifest(module.scan_sources(0.0, None), "full"),
    )

    _write(alpha, "# Alpha\n\nChanged.\n")
    beta.unlink()
    _write(gamma, "# Gamma\n\nNew.\n")

    report = module.build_manifest_drift_report(manifest_path)

    assert report["ok"] is False
    assert [source["path"] for source in report["drift"]["changed"]] == [
        "handoffs/active/alpha.md"
    ]
    assert [source["path"] for source in report["drift"]["removed"]] == [
        "handoffs/active/beta.md"
    ]
    assert [source["path"] for source in report["drift"]["added"]] == [
        "progress/2026-06/gamma.md"
    ]


def test_changed_since_manifest_outputs_only_added_and_changed_sources(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    beta = tmp_path / "handoffs" / "active" / "beta.md"
    gamma = tmp_path / "progress" / "2026-06" / "gamma.md"
    manifest_path = tmp_path / "wiki" / "source_manifest.json"
    _write(alpha, "# Alpha\n\nFirst.\n")
    _write(beta, "# Beta\n\nSecond.\n")
    module.write_manifest(
        manifest_path,
        module.build_manifest(module.scan_sources(0.0, None), "full"),
    )

    _write(alpha, "# Alpha\n\nChanged.\n")
    beta.unlink()
    _write(gamma, "# Gamma\n\nNew.\n")

    manifest = module.changed_sources_since_manifest(manifest_path)

    assert [source["path"] for source in manifest["sources"]] == [
        "handoffs/active/alpha.md",
        "progress/2026-06/gamma.md",
    ]
    assert [source["path"] for source in manifest["removed_sources"]] == [
        "handoffs/active/beta.md"
    ]
    assert manifest["drift"] == {
        "added_count": 1,
        "changed_count": 1,
        "removed_count": 1,
        "has_drift": True,
    }


def _write_baseline(module, root: Path, filenames: list[tuple[Path, str]]) -> None:
    """Write files and persist a full baseline manifest for them."""
    for path, text in filenames:
        _write(path, text)
    module.write_manifest(
        module.SOURCE_MANIFEST_PATH,
        module.build_manifest(module.scan_sources(0.0, None), "full"),
    )


def _future_mtime(path: Path) -> None:
    """Stamp a file with a far-future mtime, as a lane checkout does."""
    future = time.time() + 90 * 86400
    os.utime(path, (future, future))


def test_incremental_selection_is_content_hash_not_mtime(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    beta = tmp_path / "handoffs" / "active" / "beta.md"
    _write_baseline(module, tmp_path, [
        (alpha, "# Alpha\n\nFirst.\n"),
        (beta, "# Beta\n\nSecond.\n"),
    ])

    _write(beta, "# Beta\n\nChanged.\n")
    _future_mtime(alpha)
    _future_mtime(beta)

    manifest = module.incremental_since_tracked_manifest(None)

    assert [source["path"] for source in manifest["sources"]] == [
        "handoffs/active/beta.md"
    ]
    assert manifest["total_new"] == 1
    assert manifest["drift"]["changed_count"] == 1


def test_incremental_ignores_mtime_only_changes(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    _write_baseline(module, tmp_path, [(alpha, "# Alpha\n\nFirst.\n")])

    _future_mtime(alpha)

    manifest = module.incremental_since_tracked_manifest(None)

    assert manifest["sources"] == []
    assert manifest["total_new"] == 0
    assert manifest["drift"] == {
        "added_count": 0,
        "changed_count": 0,
        "removed_count": 0,
        "has_drift": False,
    }


def test_incremental_unchanged_sources_report_zero_with_removals_carried(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    beta = tmp_path / "handoffs" / "active" / "beta.md"
    _write_baseline(module, tmp_path, [
        (alpha, "# Alpha\n\nFirst.\n"),
        (beta, "# Beta\n\nSecond.\n"),
    ])

    beta.unlink()

    manifest = module.incremental_since_tracked_manifest(None)

    assert manifest["sources"] == []
    assert manifest["total_new"] == 0
    assert [source["path"] for source in manifest["removed_sources"]] == [
        "handoffs/active/beta.md"
    ]
    assert manifest["drift"]["has_drift"] is True
    assert manifest["baseline_manifest"] == "wiki/source_manifest.json"


def test_incremental_added_source_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    gamma = tmp_path / "progress" / "2026-06" / "gamma.md"
    _write_baseline(module, tmp_path, [(alpha, "# Alpha\n\nFirst.\n")])

    _write(gamma, "# Gamma\n\nNew.\n")

    manifest = module.incremental_since_tracked_manifest(None)

    assert [source["path"] for source in manifest["sources"]] == [
        "progress/2026-06/gamma.md"
    ]
    assert manifest["total_new"] == 1


def test_incremental_type_filter_limits_emission(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    gamma = tmp_path / "progress" / "2026-06" / "gamma.md"
    _write_baseline(module, tmp_path, [
        (alpha, "# Alpha\n\nFirst.\n"),
        (gamma, "# Gamma\n\nSecond.\n"),
    ])

    _write(alpha, "# Alpha\n\nChanged.\n")
    _write(gamma, "# Gamma\n\nChanged.\n")

    manifest = module.incremental_since_tracked_manifest("handoff-active")

    assert [source["path"] for source in manifest["sources"]] == [
        "handoffs/active/alpha.md"
    ]
    assert manifest["drift"]["changed_count"] == 2


def test_incremental_without_tracked_manifest_raises(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    _write(tmp_path / "handoffs" / "active" / "alpha.md", "# Alpha\n")

    with pytest.raises(ValueError, match="manifest not found"):
        module.incremental_since_tracked_manifest(None)


def test_refresh_tracked_manifest_advances_watermark(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    alpha = tmp_path / "handoffs" / "active" / "alpha.md"
    _write_baseline(module, tmp_path, [(alpha, "# Alpha\n\nFirst.\n")])

    _write(alpha, "# Alpha\n\nChanged.\n")
    assert module.incremental_since_tracked_manifest(None)["total_new"] == 1

    refreshed = module.refresh_tracked_manifest()

    assert refreshed["mode"] == "touch"
    assert refreshed["total_new"] == 1
    assert refreshed["sources"][0]["path"] == "handoffs/active/alpha.md"
    stored = json.loads(module.SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert stored["source_set_hash"] == refreshed["source_set_hash"]
    assert stored["kind"] == module.MANIFEST_KIND
    last_compile = module.LAST_COMPILE_PATH.read_text(encoding="utf-8").strip()
    assert last_compile.endswith("Z")
    assert last_compile == stored["last_compile"]
    assert module.incremental_since_tracked_manifest(None)["total_new"] == 0


def test_refresh_tracked_manifest_refuses_without_baseline(tmp_path: Path) -> None:
    module = _load_module()
    _configure_temp_project(module, tmp_path)
    _write(tmp_path / "handoffs" / "active" / "alpha.md", "# Alpha\n")

    with pytest.raises(ValueError, match="--full --write-manifest"):
        module.refresh_tracked_manifest()
