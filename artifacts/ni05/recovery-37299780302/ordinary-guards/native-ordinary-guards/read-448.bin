from __future__ import annotations

import argparse
import json
from pathlib import Path


def test_paths_from_source_manifest_resolves_relative_paths(tmp_path: Path) -> None:
    from scripts.kb_rag import cli

    root = tmp_path / "root"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "kind": "project-wiki-source-manifest",
                "sources": [
                    {"path": "wiki/knowledge-management.md"},
                    {"path": str(root / "handoffs" / "active" / "absolute.md")},
                    {"path": ""},
                    {},
                ],
                "removed_sources": [{"path": "progress/old.md"}],
            }
        ),
        encoding="utf-8",
    )

    paths, removed = cli._paths_from_source_manifest(manifest, manifest_root=root)

    assert paths == [
        str((root / "wiki" / "knowledge-management.md").resolve()),
        str((root / "handoffs" / "active" / "absolute.md").resolve()),
    ]
    assert removed == [str((root / "progress" / "old.md").resolve())]


def test_update_command_accepts_project_wiki_manifest(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from scripts.kb_rag import cli

    root = tmp_path / "root"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "kind": "project-wiki-source-manifest",
                "sources": [{"path": "handoffs/active/internal-kb-rag.md"}],
                "removed_sources": [{"path": "progress/old.md"}],
            }
        ),
        encoding="utf-8",
    )
    calls: dict = {}

    class FakeConfig:
        @classmethod
        def from_yaml(cls, path):
            calls["config_path"] = path
            return "config"

    def fake_update_files(paths, config, index_dir):
        calls["paths"] = paths
        calls["config"] = config
        calls["index_dir"] = index_dir
        return {"ok": True, "files_processed": len(paths)}

    def fake_remove_files(paths, index_dir):
        calls["removed_paths"] = paths
        calls["removed_index_dir"] = index_dir
        return {"ok": True, "files_removed": len(paths)}

    monkeypatch.setattr(cli, "CorpusConfig", FakeConfig)
    monkeypatch.setattr(cli, "update_files", fake_update_files)
    monkeypatch.setattr(cli, "remove_files", fake_remove_files)

    rc = cli._cmd_update(
        argparse.Namespace(
            config=None,
            files=["/already/absolute.md"],
            index_dir=tmp_path / "idx",
            manifest=str(manifest),
            manifest_root=str(root),
        )
    )

    assert rc == 0
    assert calls["paths"] == [
        "/already/absolute.md",
        str((root / "handoffs" / "active" / "internal-kb-rag.md").resolve()),
    ]
    assert calls["removed_paths"] == [str((root / "progress" / "old.md").resolve())]
    assert calls["config"] == "config"
    output = json.loads(capsys.readouterr().out)
    assert output["manifest_paths"] == 1
    assert output["manifest_removed_paths"] == 1
    assert output["manifest_removed_result"] == {"ok": True, "files_removed": 1}


def test_update_command_accepts_removed_only_manifest(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from scripts.kb_rag import cli

    root = tmp_path / "root"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "kind": "project-wiki-source-manifest",
                "sources": [],
                "removed_sources": [{"path": "progress/old.md"}],
            }
        ),
        encoding="utf-8",
    )
    calls: dict = {}

    class FakeConfig:
        @classmethod
        def from_yaml(cls, path):
            return "config"

    def fail_update_files(paths, config, index_dir):
        raise AssertionError("removed-only manifest should not update files")

    def fake_remove_files(paths, index_dir):
        calls["removed_paths"] = paths
        return {"ok": True, "files_removed": len(paths)}

    monkeypatch.setattr(cli, "CorpusConfig", FakeConfig)
    monkeypatch.setattr(cli, "update_files", fail_update_files)
    monkeypatch.setattr(cli, "remove_files", fake_remove_files)

    rc = cli._cmd_update(
        argparse.Namespace(
            config=None,
            files=None,
            index_dir=tmp_path / "idx",
            manifest=str(manifest),
            manifest_root=str(root),
        )
    )

    assert rc == 0
    assert calls["removed_paths"] == [str((root / "progress" / "old.md").resolve())]
    output = json.loads(capsys.readouterr().out)
    assert output["files_processed"] == 0
    assert output["manifest_removed_result"] == {"ok": True, "files_removed": 1}
