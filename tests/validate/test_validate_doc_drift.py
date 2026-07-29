from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate" / "validate_doc_drift.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "validate_doc_drift_under_test",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_manifest_drift_passes_when_manifest_is_current(monkeypatch) -> None:
    module = _load_module()
    compiler = SimpleNamespace(
        SOURCE_MANIFEST_PATH=Path("wiki/source_manifest.json"),
        build_manifest_drift_report=lambda path: {
            "ok": True,
            "writer_evidence_policy_errors": [],
            "manifest_path": str(path),
            "drift": {"added": [], "changed": [], "removed": []},
        },
    )
    monkeypatch.setattr(module, "load_project_wiki_compile_sources", lambda: compiler)

    assert module.check_source_manifest_drift() == []


def test_source_manifest_drift_summarizes_changed_sources(monkeypatch) -> None:
    module = _load_module()
    compiler = SimpleNamespace(
        SOURCE_MANIFEST_PATH=Path("wiki/source_manifest.json"),
        build_manifest_drift_report=lambda path: {
            "ok": False,
            "manifest_path": str(path),
            "saved_source_set_hash": "old",
            "current_source_set_hash": "new",
            "writer_evidence_policy_errors": [],
            "drift": {
                "added": [{"path": "progress/2026-06/new.md"}],
                "changed": [{"path": "handoffs/active/internal-kb-rag.md"}],
                "removed": [{"path": "docs/removed.md"}],
            },
        },
    )
    monkeypatch.setattr(module, "load_project_wiki_compile_sources", lambda: compiler)

    errors = module.check_source_manifest_drift()

    assert errors[0] == (
        "source-manifest-drift: wiki/source_manifest.json stale "
        "(added=1 changed=1 removed=1; saved=old current=new)"
    )
    assert errors[1] == (
        "source-manifest-drift: added sources: progress/2026-06/new.md"
    )
    assert errors[2] == (
        "source-manifest-drift: changed sources: "
        "handoffs/active/internal-kb-rag.md"
    )
    assert errors[3] == "source-manifest-drift: removed sources: docs/removed.md"


def test_source_manifest_drift_reports_policy_errors(monkeypatch) -> None:
    module = _load_module()
    compiler = SimpleNamespace(
        SOURCE_MANIFEST_PATH=Path("wiki/source_manifest.json"),
        build_manifest_drift_report=lambda path: {
            "ok": False,
            "manifest_path": str(path),
            "saved_source_set_hash": "same",
            "current_source_set_hash": "same",
            "writer_evidence_policy_errors": [
                "writer_evidence_policy missing",
            ],
            "drift": {
                "added": [],
                "changed": [],
                "removed": [],
            },
        },
    )
    monkeypatch.setattr(module, "load_project_wiki_compile_sources", lambda: compiler)

    errors = module.check_source_manifest_drift()

    assert errors[0] == "source-manifest-drift: writer_evidence_policy missing"
    assert errors[1] == (
        "source-manifest-drift: wiki/source_manifest.json stale "
        "(added=0 changed=0 removed=0; saved=same current=same)"
    )


def test_source_manifest_drift_reports_manifest_errors(monkeypatch) -> None:
    module = _load_module()

    def fail() -> object:
        raise ValueError("manifest not found: wiki/source_manifest.json")

    monkeypatch.setattr(module, "load_project_wiki_compile_sources", fail)

    assert module.check_source_manifest_drift() == [
        "source-manifest-drift: manifest not found: wiki/source_manifest.json"
    ]
