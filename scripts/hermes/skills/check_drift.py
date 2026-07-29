#!/usr/bin/env python3
"""Validate Hermes skill docs against orchestrator x_* request overrides."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


FIELD_RE = re.compile(r"\bx_[A-Za-z0-9_]+\b")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_schema_path() -> Path:
    return Path("/mnt/raid0/llm/epyc-orchestrator/src/api/models/openai.py")


def declared_request_fields(schema_path: Path) -> set[str]:
    tree = ast.parse(schema_path.read_text(encoding="utf-8"), filename=str(schema_path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "OpenAIChatRequest":
            fields: set[str] = set()
            for stmt in node.body:
                target: ast.expr | None = None
                if isinstance(stmt, ast.AnnAssign):
                    target = stmt.target
                elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                    target = stmt.targets[0]
                if isinstance(target, ast.Name) and target.id.startswith("x_"):
                    fields.add(target.id)
            if fields:
                return fields
            raise ValueError(f"OpenAIChatRequest in {schema_path} has no x_* fields")
    raise ValueError(f"OpenAIChatRequest not found in {schema_path}")


def documented_fields(skills_dir: Path) -> tuple[set[str], dict[str, list[Path]]]:
    docs = sorted(skills_dir.rglob("*.md"))
    if not docs:
        raise ValueError(f"No markdown skill docs found under {skills_dir}")

    fields: set[str] = set()
    locations: dict[str, list[Path]] = {}
    for path in docs:
        text = path.read_text(encoding="utf-8")
        for match in FIELD_RE.findall(text):
            fields.add(match)
            locations.setdefault(match, []).append(path)
    return fields, locations


def format_locations(
    fields: set[str], locations: dict[str, list[Path]], base: Path
) -> list[str]:
    lines: list[str] = []
    for field in sorted(fields):
        refs: set[str] = set()
        for path in locations.get(field, []):
            try:
                refs.add(str(path.relative_to(base)))
            except ValueError:
                refs.add(str(path))
        refs_list = sorted(refs)
        suffix = f" ({', '.join(refs_list)})" if refs_list else ""
        lines.append(f"  - {field}{suffix}")
    return lines


def main() -> int:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema",
        type=Path,
        default=default_schema_path(),
        help="Path to orchestrator src/api/models/openai.py",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=root / "scripts/hermes/skills",
        help="Directory containing Hermes skill markdown files",
    )
    args = parser.parse_args()

    schema_path = args.schema.resolve()
    skills_dir = args.skills_dir.resolve()
    declared = declared_request_fields(schema_path)
    documented, locations = documented_fields(skills_dir)

    missing = declared - documented
    stale = documented - declared
    if missing or stale:
        print("Hermes x_* drift detected.", file=sys.stderr)
        print(f"Schema: {schema_path}", file=sys.stderr)
        print(f"Skills: {skills_dir}", file=sys.stderr)
        if missing:
            print("\nDeclared on OpenAIChatRequest but undocumented:", file=sys.stderr)
            for line in sorted(f"  - {field}" for field in missing):
                print(line, file=sys.stderr)
        if stale:
            print("\nDocumented in Hermes skills but not declared on OpenAIChatRequest:", file=sys.stderr)
            for line in format_locations(stale, locations, root):
                print(line, file=sys.stderr)
        return 1

    print(
        "Hermes x_* drift check passed: "
        f"{len(declared)} request override fields documented."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
