from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / ".claude" / "skills" / "project-wiki" / "scripts"
MODULE_PATH = SCRIPT_DIR / "wiki_writer_review.py"


def _load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "project_wiki_writer_review",
            MODULE_PATH,
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest(module) -> dict:
    return {
        "schema_version": 1,
        "kind": "project-wiki-source-manifest",
        "mode": "changed-since-manifest",
        "source_set_hash": "abc123",
        "writer_evidence_policy": dict(module.WRITER_EVIDENCE_POLICY),
        "sources": [
            {
                "path": "handoffs/active/internal-kb-rag.md",
                "title": "Internal KB RAG",
                "type": "handoff-active",
                "content_hash": "h1",
            },
            {
                "path": "progress/2026-06/2026-06-28.md",
                "title": "Progress",
                "type": "progress",
                "content_hash": "h2",
            },
        ],
    }


def test_build_writer_packet_uses_configured_role(tmp_path: Path) -> None:
    module = _load_module()
    module.ROOT = tmp_path
    _write(
        tmp_path / "wiki.yaml",
        """
wiki_writer:
  role: worker_general
  role_source: stack role alias
  temperature: 0.2
  draft_dir: wiki/drafts
  review_modes: [human, measured]
""",
    )

    packet = module.build_writer_packet(_manifest(module), category="knowledge-management")

    assert packet["kind"] == module.PACKET_KIND
    assert packet["writer"]["role"] == "worker_general"
    assert packet["writer"]["role_source"] == "stack role alias"
    assert packet["adoption_gate"]["minimum_source_references"] == 3
    assert [source["path"] for source in packet["sources"]] == [
        "handoffs/active/internal-kb-rag.md",
        "progress/2026-06/2026-06-28.md",
    ]
    assert len(packet["packet_hash"]) == 64


def test_build_writer_packet_rejects_weak_manifest_policy(tmp_path: Path) -> None:
    module = _load_module()
    module.ROOT = tmp_path
    manifest = _manifest(module)
    manifest["writer_evidence_policy"]["minimum_source_references"] = 1

    try:
        module.build_writer_packet(manifest)
    except ValueError as exc:
        assert "minimum_source_references must be 3" in str(exc)
    else:
        raise AssertionError("weak writer policy should fail")


def test_validate_writer_evidence_accepts_reviewed_draft(tmp_path: Path) -> None:
    module = _load_module()
    module.ROOT = tmp_path
    _write(
        tmp_path / "wiki.yaml",
        """
wiki_writer:
  role: worker_general
  review_modes: [human, measured]
""",
    )
    draft = tmp_path / "wiki" / "drafts" / "knowledge-management.md"
    evidence = tmp_path / "wiki" / "drafts" / "knowledge-management.evidence.json"
    _write(
        draft,
        """# Knowledge Management

**Category**: `knowledge_management`

## Summary

Draft.

## Source References

- [A](../handoffs/active/internal-kb-rag.md)
- [B](../progress/2026-06/2026-06-28.md)
- [C](../handoffs/completed/autowiki-incremental-kb-generator.md)
""",
    )
    evidence.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": module.EVIDENCE_KIND,
                "writer": {"role": "worker_general"},
                "confidence": "verified",
                "review": {"mode": "human", "verdict": "accept"},
                "source_references": [
                    "handoffs/active/internal-kb-rag.md",
                    "progress/2026-06/2026-06-28.md",
                    "handoffs/completed/autowiki-incremental-kb-generator.md",
                ],
            }
        ),
        encoding="utf-8",
    )

    report = module.validate_writer_evidence(draft, evidence)

    assert report == {
        "schema_version": 1,
        "kind": "project-wiki-writer-validation",
        "draft_path": "wiki/drafts/knowledge-management.md",
        "evidence_path": "wiki/drafts/knowledge-management.evidence.json",
        "ok": True,
        "errors": [],
    }


def test_validate_writer_evidence_rejects_unreviewed_draft(tmp_path: Path) -> None:
    module = _load_module()
    module.ROOT = tmp_path
    draft = tmp_path / "wiki" / "drafts" / "bad.md"
    evidence = tmp_path / "wiki" / "drafts" / "bad.evidence.json"
    _write(draft, "# Bad\n\n## Summary\n\nNo category or references.\n")
    evidence.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": module.EVIDENCE_KIND,
                "writer": {"role": "architect_general"},
                "confidence": "draft",
                "review": {"mode": "auto", "verdict": "accept"},
                "source_references": [],
            }
        ),
        encoding="utf-8",
    )

    report = module.validate_writer_evidence(draft, evidence)

    assert report["ok"] is False
    assert "missing **Category** metadata" in report["errors"]
    assert "evidence confidence must be 'verified'" in report["errors"]
    assert "evidence writer.role must be 'worker_general', got 'architect_general'" in report["errors"]
