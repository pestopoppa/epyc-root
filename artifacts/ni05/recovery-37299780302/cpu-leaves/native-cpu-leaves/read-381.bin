from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "docs" / "generate_docs_index.py"


def run_generator(root: Path, output: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--output", str(output), *extra],
        check=False,
        capture_output=True,
        text=True,
    )


def test_generate_docs_index_lists_markdown_docs(tmp_path: Path) -> None:
    (tmp_path / "docs" / "chapters").mkdir(parents=True)
    (tmp_path / "docs" / "guides").mkdir(parents=True)
    (tmp_path / "docs" / "generated").mkdir(parents=True)
    (tmp_path / "docs" / ".pytest_cache").mkdir(parents=True)
    (tmp_path / "docs" / "__pycache__").mkdir(parents=True)

    (tmp_path / "docs" / "ARCHITECTURE.md").write_text("# architecture\n", encoding="utf-8")
    (tmp_path / "docs" / "chapters" / "INDEX.md").write_text("# chapters\n", encoding="utf-8")
    (tmp_path / "docs" / "chapters" / "01-alpha.md").write_text("# alpha\n", encoding="utf-8")
    (tmp_path / "docs" / "guides" / "guide.md").write_text("# guide\n", encoding="utf-8")
    (tmp_path / "docs" / "generated" / "current_stack_summary.md").write_text(
        "# generated\n", encoding="utf-8"
    )
    (tmp_path / "docs" / ".pytest_cache" / "ignored.md").write_text("# ignored\n", encoding="utf-8")
    (tmp_path / "docs" / "__pycache__" / "ignored.md").write_text("# ignored\n", encoding="utf-8")

    output = tmp_path / "docs" / "reference" / "GENERATED_DOCS_INDEX.md"
    result = run_generator(tmp_path, output)

    assert result.returncode == 0, result.stderr

    text = output.read_text(encoding="utf-8")
    assert "# Generated Docs Index" in text
    assert "- [ARCHITECTURE.md](../ARCHITECTURE.md)" in text
    assert "- [chapters/01-alpha.md](../chapters/01-alpha.md)" in text
    assert "- [chapters/INDEX.md](../chapters/INDEX.md)" in text
    assert "- [generated/current_stack_summary.md](../generated/current_stack_summary.md)" in text
    assert "- [guides/guide.md](../guides/guide.md)" in text
    assert ".pytest_cache/ignored.md" not in text
    assert "__pycache__/ignored.md" not in text
    assert "GENERATED_DOCS_INDEX.md" not in text


def test_generate_docs_index_check_reports_staleness(tmp_path: Path) -> None:
    (tmp_path / "docs" / "chapters").mkdir(parents=True)
    (tmp_path / "docs" / "chapters" / "INDEX.md").write_text("# chapters\n", encoding="utf-8")

    output = tmp_path / "docs" / "reference" / "GENERATED_DOCS_INDEX.md"
    first = run_generator(tmp_path, output)
    assert first.returncode == 0, first.stderr

    (tmp_path / "docs" / "chapters" / "02-new.md").write_text("# new\n", encoding="utf-8")
    check = run_generator(tmp_path, output, "--check")

    assert check.returncode == 1
    assert "stale generated docs index" in check.stdout


if __name__ == "__main__":
    raise SystemExit(
        "REFUSING: pytest-fixture suite; run: "
        "python -m pytest tests/unit/test_generate_docs_index.py -q"
    )
