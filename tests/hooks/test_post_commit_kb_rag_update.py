from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "post_commit_kb_rag_update.sh"


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    orchestrator = tmp_path / "orchestrator"
    compile_script = root / ".claude" / "skills" / "project-wiki" / "scripts" / "compile_sources.py"
    cli = orchestrator / "scripts" / "kb_rag" / "cli.py"
    (orchestrator / "src" / "retrieval").mkdir(parents=True)
    compile_script.parent.mkdir(parents=True)
    cli.parent.mkdir(parents=True)
    compile_script.write_text(
        "import json, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "if '--changed-since-manifest' in args:\n"
        "    cursor = pathlib.Path(args[args.index('--changed-since-manifest') + 1])\n"
        "    if not cursor.exists():\n"
        "        print(f'ERROR: manifest not found: {cursor}', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "manifest = {'sources': [{'path': 'handoffs/active/worker.md'}], "
        "'removed_sources': []}\n"
        "print(json.dumps(manifest))\n"
        "if '--write-manifest' in args:\n"
        "    out = pathlib.Path(args[args.index('--write-manifest') + 1])\n"
        "    out.parent.mkdir(parents=True, exist_ok=True)\n"
        "    out.write_text(json.dumps(manifest))\n",
        encoding="utf-8",
    )
    cli.write_text(
        "import pathlib, sys\n"
        "pathlib.Path(__file__).with_name('update-ran').write_text(' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    cursor = root / ".git" / "kb-rag" / "source_manifest.json"
    return root, orchestrator, cursor


def test_direct_hook_uses_private_cursor_and_preserves_wrap_surfaces(
    tmp_path: Path,
) -> None:
    root, orchestrator, cursor = _fixture(tmp_path)
    forbidden = {
        "handoffs/active/.index-state.json": "index-state\n",
        "handoffs/active/.index-graph.json": "index-graph\n",
        "handoffs/active/master-handoff-index.md": "master-generated-block\n",
        "wiki/source_manifest.json": json.dumps({"wrap": "manifest"}) + "\n",
        "wiki/.last_compile": "2026-08-13T00:00:00Z\n",
    }
    for rel, value in forbidden.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "KB_RAG_ORCHESTRATOR": str(orchestrator),
            "KB_RAG_PYTHON": sys.executable,
        }
    )
    shutil.copy2(HOOK, root / "post_commit_kb_rag_update.sh")
    result = subprocess.run(
        ["bash", str(root / "post_commit_kb_rag_update.sh")],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert cursor.exists()
    assert (orchestrator / "scripts" / "kb_rag" / "update-ran").exists()
    for rel, value in forbidden.items():
        assert (root / rel).read_text(encoding="utf-8") == value
