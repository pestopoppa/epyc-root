from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "handoffs" / "install_timeline_hook.sh"


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), cwd=cwd, text=True, capture_output=True, check=True
    )


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts" / "handoffs").mkdir(parents=True)
    (root / "handoffs" / "active").mkdir(parents=True)
    (root / "dashboard").mkdir()
    shutil.copy2(INSTALLER, root / "scripts" / "handoffs" / INSTALLER.name)
    (root / "scripts" / "handoffs" / "build_handoff_timeline.py").write_text(
        "from pathlib import Path\n"
        "root = Path(__file__).resolve().parents[2]\n"
        "path = root / 'dashboard' / 'handoff_timeline.json'\n"
        "path.write_text(str(__import__('time').time()))\n",
        encoding="utf-8",
    )
    (root / "scripts" / "handoffs" / "index_state.py").write_text(
        "from pathlib import Path\n"
        "root = Path(__file__).resolve().parents[2]\n"
        "for rel in ('handoffs/active/.index-state.json', "
        "'handoffs/active/.index-graph.json', "
        "'handoffs/active/master-handoff-index.md'):\n"
        "    (root / rel).write_text('MUTATED')\n",
        encoding="utf-8",
    )
    _run("git", "init", "-q", cwd=root)
    _run("git", "config", "user.email", "test@example.invalid", cwd=root)
    _run("git", "config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    _run("git", "add", ".", cwd=root)
    _run("git", "commit", "-qm", "fixture", cwd=root)
    return root


def _old_block(kind: str) -> str:
    return (
        "#!/bin/sh\n\n"
        "# >>> handoff-timeline hook >>>\n"
        f"# obsolete {kind} block\n"
        "python3 scripts/handoffs/index_state.py\n"
        "# <<< handoff-timeline hook <<<\n\n"
        f"echo preserved-{kind} >/dev/null\n"
    )


def test_installer_upgrades_marked_blocks_and_preserves_chained_hooks(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path)
    hooks = root / ".git" / "hooks"
    for kind in ("post-commit", "post-merge", "post-checkout"):
        (hooks / kind).write_text(_old_block(kind), encoding="utf-8")

    first = _run("bash", "scripts/handoffs/install_timeline_hook.sh", cwd=root)
    assert first.stdout.count("upgraded handoff-timeline block") == 3

    installed = {}
    for kind in ("post-commit", "post-merge", "post-checkout"):
        text = (hooks / kind).read_text(encoding="utf-8")
        installed[kind] = text
        assert text.count("# >>> handoff-timeline hook >>>") == 1
        assert text.count("# <<< handoff-timeline hook <<<") == 1
        assert "index_state.py" not in text
        assert "build_handoff_timeline.py" in text
        assert f"preserved-{kind}" in text

    _run("bash", "scripts/handoffs/install_timeline_hook.sh", cwd=root)
    assert {
        kind: (hooks / kind).read_text(encoding="utf-8")
        for kind in installed
    } == installed


def test_worker_handoff_commit_updates_timeline_but_not_wrap_owned_indices(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path)
    forbidden = {
        rel: f"sentinel:{rel}\n"
        for rel in (
            "handoffs/active/.index-state.json",
            "handoffs/active/.index-graph.json",
            "handoffs/active/master-handoff-index.md",
        )
    }
    for rel, value in forbidden.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    _run("bash", "scripts/handoffs/install_timeline_hook.sh", cwd=root)
    timeline = root / "dashboard" / "handoff_timeline.json"
    before_timeline = timeline.read_text(encoding="utf-8")
    (root / "handoffs" / "active" / "worker.md").write_text(
        "# Worker\n\n- [x] done\n", encoding="utf-8"
    )
    _run("git", "add", "handoffs/active/worker.md", cwd=root)
    _run("git", "commit", "-qm", "worker handoff checkpoint", cwd=root)

    deadline = time.monotonic() + 3
    while timeline.read_text(encoding="utf-8") == before_timeline:
        if time.monotonic() >= deadline:
            raise AssertionError("timeline hook did not run")
        time.sleep(0.05)

    for rel, value in forbidden.items():
        assert (root / rel).read_text(encoding="utf-8") == value
