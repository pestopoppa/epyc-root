#!/usr/bin/env python3
"""Run the PII pre-commit hook against the held-out fixture.

The hook intentionally allow-lists research/fixtures/pii_* when run inside the
root repo, so this validator stages each fixture row as a normal file in a
temporary git repository and compares the hook's block/pass behavior with the
fixture's expected_match field.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "research" / "fixtures" / "pii_hygiene_eval.jsonl"
DEFAULT_HOOK = ROOT / "scripts" / "hooks" / "pii_precommit.sh"


def _run(cmd: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def _clear_worktree(repo: Path) -> None:
    _run(["git", "reset", "-q"], repo)
    for child in repo.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "text" not in row or "expected_match" not in row:
            raise ValueError(f"{path}:{lineno}: expected text and expected_match fields")
        rows.append(row)
    return rows


def evaluate(rows: list[dict[str, Any]], hook: Path) -> tuple[int, list[str]]:
    temp = Path(tempfile.mkdtemp(prefix="pii_fixture_eval_"))
    failures: list[str] = []
    try:
        _run(["git", "init", "-q"], temp)
        _run(["git", "config", "user.email", "fixture@example.invalid"], temp)
        _run(["git", "config", "user.name", "Fixture"], temp)

        for idx, row in enumerate(rows, 1):
            _clear_worktree(temp)
            case_path = temp / f"case_{idx:02d}.txt"
            case_path.write_text(str(row["text"]) + "\n")
            _run(["git", "add", case_path.name], temp)

            proc = _run([str(hook)], temp, check=False)
            blocked = proc.returncode != 0
            expected = bool(row["expected_match"])
            if blocked != expected:
                stderr = "\n".join(proc.stderr.strip().splitlines()[:3])
                failures.append(
                    f"case {idx}: expected_block={expected} actual_block={blocked} "
                    f"text={row['text'][:100]!r}\n{stderr}"
                )
    finally:
        shutil.rmtree(temp)

    return len(rows) - len(failures), failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--hook", type=Path, default=DEFAULT_HOOK)
    args = parser.parse_args()

    rows = load_rows(args.fixture)
    passed, failures = evaluate(rows, args.hook)
    print(f"PII fixture eval: {passed}/{len(rows)} passed")
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
