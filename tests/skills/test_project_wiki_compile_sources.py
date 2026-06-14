from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path


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
        "skip_filenames": ["INDEX.md"],
        "skip_patterns": ["*-index.md"],
        "source_dirs": [
            {"path": "handoffs/active", "type": "handoff-active", "recurse": False},
            {"path": "progress", "type": "progress", "recurse": True},
        ],
    }
    module.LAST_COMPILE_PATH = root / "wiki" / ".last_compile"
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

    reversed_manifest = module.build_manifest(list(reversed(sources)), "full")
    assert reversed_manifest["source_set_hash"] == manifest["source_set_hash"]


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
