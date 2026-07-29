#!/usr/bin/env python3
"""Enforce companion contract updates for stack-fact reader migrations.

Stack topology facts have repeatedly regressed when one reader was updated
without the other readers and parity contracts moving in the same change. This
check is intentionally narrow: it only inspects staged path names, and fails
when a known stack-fact reader/source file is staged without a known companion
reader-agreement or parity test.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path, PurePosixPath


STACK_FACT_SOURCE_FILES = frozenset(
    {
        "scripts/server/orchestrator_stack.py",
        "scripts/server/stack_manifest.py",
        "scripts/server/stack_numa.py",
        "scripts/server/stack_numa_mode.py",
        "scripts/validate/stack_change_guard.py",
        "src/api/routes/dashboard_topology.py",
        "src/cli_orch.py",
        "src/config/stack_templates.py",
        "src/registry/stack_priors.py",
        "src/runtime/instance_topology.py",
    }
)

STACK_FACT_COMPANION_FILES = frozenset(
    {
        "tests/unit/test_build_server_command_helpers.py",
        "tests/unit/test_cli_orch.py",
        "tests/unit/test_dashboard_helpers.py",
        "tests/unit/test_dynamic_stack_evidence_packet.py",
        "tests/unit/test_stack_change_guard.py",
        "tests/unit/test_stack_manifest_imports.py",
        "tests/unit/test_stack_numa_reader_agreement.py",
        "tests/unit/test_stack_priors_compiler.py",
        "tests/unit/test_stack_templates_v2.py",
        "tests/unit/test_topology_concurrency.py",
    }
)

KNOWN_REPO_NAMES = frozenset({"epyc-orchestrator", "epyc-root"})


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )


def staged_paths(repo_root: Path) -> list[str]:
    proc = _run_git(
        repo_root,
        ["diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z"],
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or "git diff --cached failed")
    return [path for path in proc.stdout.split("\0") if path]


def normalize_changed_path(path: str, repo_root: Path | None = None) -> str:
    path = path.replace("\\", "/").removeprefix("./")
    path_obj = Path(path)
    if repo_root is not None and path_obj.is_absolute():
        try:
            path = path_obj.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            path = path_obj.as_posix()

    pure = PurePosixPath(path)
    parts = pure.parts
    for repo_name in KNOWN_REPO_NAMES:
        if repo_name in parts:
            idx = parts.index(repo_name)
            if idx + 1 < len(parts):
                return "/".join(parts[idx + 1 :])

    return pure.as_posix()


def check_stack_fact_migration_discipline(
    changed_paths: list[str],
    *,
    repo_root: Path | None = None,
) -> list[str]:
    normalized = {
        normalize_changed_path(path, repo_root=repo_root) for path in changed_paths
    }
    source_hits = sorted(normalized & STACK_FACT_SOURCE_FILES)
    companion_hits = sorted(normalized & STACK_FACT_COMPANION_FILES)
    if not source_hits or companion_hits:
        return []

    companions = "\n".join(f"  - {path}" for path in sorted(STACK_FACT_COMPANION_FILES))
    sources = "\n".join(f"  - {path}" for path in source_hits)
    return [
        "\n".join(
            [
                "[check_stack_fact_migration_discipline] blocked stack-fact migration",
                "",
                "Changed stack-fact reader/source files:",
                sources,
                "",
                "Stage at least one companion reader-agreement or parity contract:",
                companions,
                "",
                "Reason: multiply-read stack facts must move with an invariant or",
                "reader-agreement update so partial reader migrations do not land.",
            ]
        )
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="git repository whose staged paths should be inspected",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="changed paths to inspect; defaults to staged paths",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root
    if repo_root is None:
        proc = _run_git(Path.cwd(), ["rev-parse", "--show-toplevel"])
        repo_root = Path(proc.stdout.strip()) if proc.returncode == 0 else Path.cwd()
    repo_root = repo_root.resolve()

    try:
        changed = list(args.paths) if args.paths else staged_paths(repo_root)
    except RuntimeError as exc:
        print(
            f"[check_stack_fact_migration_discipline] {exc}",
            file=sys.stderr,
        )
        return 2

    errors = check_stack_fact_migration_discipline(changed, repo_root=repo_root)
    if errors:
        print("\n\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
