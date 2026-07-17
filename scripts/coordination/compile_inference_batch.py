#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Consolidated inference-batch manifest compiler — batch-infra item B1 / Wave-1 W0a.

Reads the hand-authored entry files under ``coordination/inference-batch/entries/*.yaml``,
validates each against ``inference_batch.schema.json`` (jsonschema Draft-07) plus three
semantic lint rules, and emits the compiled manifest + a source lock.

Target interpreter: ``/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`` (it carries
jsonschema >= 4.26 and pyyaml >= 6). The sibling ``batch_ledger.py`` is stdlib-only; only
this compiler needs the two third-party deps (for Draft-07 validation and YAML parsing).

Lint rules (enforced separately from the JSON Schema so failures are reported distinctly):
  1. provenance.owning_handoff is a non-empty string.
  2. provenance.checkbox is a non-empty string.
  3. outcomes.gate_table has at least one row.

Subcommands / flags::

    compile              validate all entries, then emit manifest.yaml + sources.lock.json
    validate             validate all entries; exit nonzero if ANY entry is invalid
    simulate | --simulate
                         validate, build an in-memory manifest, and walk pick-next over an
                         EMPTY ledger — printing the order it WOULD execute. Pure dry logic;
                         no inference, no ledger writes, no side effects.

Outputs (compile):
  * coordination/inference-batch/manifest.yaml    — sorted, entry_hash-stamped entries
  * coordination/inference-batch/sources.lock.json — git SHAs of the 3 repos + resolved
                                                      checkbox refs per entry
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from jsonschema import Draft7Validator

# Import the sibling ledger library (works whether run as a script or imported).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import batch_ledger  # noqa: E402

MANIFEST_SCHEMA_VERSION = "inference_batch.manifest.v1"
SOURCES_LOCK_SCHEMA_VERSION = "inference_batch.sources_lock.v1"
ENTRY_SCHEMA_VERSION = "inference_batch.entry.v1"

REPO_ROOT = _HERE.parents[1]  # scripts/coordination -> scripts -> epyc-root
DEFAULT_SCHEMA = _HERE / "inference_batch.schema.json"
DEFAULT_ENTRIES_DIR = REPO_ROOT / "coordination" / "inference-batch" / "entries"
DEFAULT_OUT_DIR = REPO_ROOT / "coordination" / "inference-batch"

# The three repos whose SHAs + referenced checkboxes the source lock freezes.
DEFAULT_REPOS: Dict[str, Path] = {
    "epyc-root": REPO_ROOT,
    "epyc-orchestrator": Path("/mnt/raid0/llm/epyc-orchestrator"),
    "epyc-inference-research": Path("/mnt/raid0/llm/epyc-inference-research"),
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Loading + validation
# ---------------------------------------------------------------------------
def load_schema(schema_path: Path) -> Draft7Validator:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def load_entries(entries_dir: Path) -> List[Tuple[Path, dict]]:
    """Load every ``*.yaml``/``*.yml`` under ``entries_dir`` in filename order.

    A file may hold a single entry mapping or a list of entry mappings."""
    out: List[Tuple[Path, dict]] = []
    for path in sorted(Path(entries_dir).glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
            continue
        if isinstance(data, list):
            for item in data:
                out.append((path, item))
        else:
            out.append((path, data))
    return out


def lint_entry(entry: dict) -> List[str]:
    """The three semantic lint rules. Returns a list of human-readable failures."""
    errors: List[str] = []
    prov = entry.get("provenance") or {}
    if not str(prov.get("owning_handoff") or "").strip():
        errors.append("lint: provenance.owning_handoff must be a non-empty string")
    if not str(prov.get("checkbox") or "").strip():
        errors.append("lint: provenance.checkbox must be a non-empty string")
    gate_table = (entry.get("outcomes") or {}).get("gate_table") or []
    if len(gate_table) < 1:
        errors.append("lint: outcomes.gate_table must have at least one row")
    return errors


def validate_entry(entry: dict, validator: Draft7Validator) -> List[str]:
    """Return all schema + lint errors for one entry (empty list == valid)."""
    errors: List[str] = []
    for err in sorted(validator.iter_errors(entry), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"schema: {loc}: {err.message}")
    errors.extend(lint_entry(entry))
    return errors


def validate_all(
    entries: List[Tuple[Path, dict]], validator: Draft7Validator
) -> Tuple[List[Tuple[Path, dict]], Dict[str, List[str]]]:
    """Validate every entry. Returns (valid_entries, {label: [errors]} for invalid).

    Also flags duplicate task_ids as an error against the offending entry."""
    valid: List[Tuple[Path, dict]] = []
    invalid: Dict[str, List[str]] = {}
    seen: Dict[str, Path] = {}
    for path, entry in entries:
        tid = entry.get("task_id", "<no task_id>")
        label = f"{path.name}::{tid}"
        errs = validate_entry(entry, validator)
        if tid in seen:
            errs.append(f"duplicate task_id {tid!r} (first seen in {seen[tid].name})")
        elif isinstance(tid, str):
            seen[tid] = path
        if errs:
            invalid[label] = errs
        else:
            valid.append((path, entry))
    return valid, invalid


# ---------------------------------------------------------------------------
# Manifest + source lock construction
# ---------------------------------------------------------------------------
def build_manifest(entries: List[dict]) -> dict:
    """Sort entries deterministically and stamp each with its entry_hash."""
    stamped: List[dict] = []
    for entry in sorted(entries, key=batch_ledger.sort_key):
        clean = {k: v for k, v in entry.items() if k != "entry_hash"}
        stamped.append({**clean, "entry_hash": batch_ledger.canonical_hash(clean)})
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "entry_schema_version": ENTRY_SCHEMA_VERSION,
        "generated_at": _utcnow_iso(),
        "entry_count": len(stamped),
        "entries": stamped,
    }


def _git(args: List[str], cwd: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def repo_lock(repos: Dict[str, Path]) -> Dict[str, dict]:
    locks: Dict[str, dict] = {}
    for name, path in repos.items():
        sha = _git(["rev-parse", "HEAD"], path)
        porcelain = _git(["status", "--porcelain"], path)
        locks[name] = {
            "path": str(path),
            "sha": sha,
            "dirty": bool(porcelain) if porcelain is not None else None,
        }
    return locks


def resolve_checkbox_refs(
    entries: List[dict], repo_root: Path
) -> List[dict]:
    """For each entry, resolve provenance.owning_handoff + checkbox against the tree.

    Best-effort: records whether the owning handoff file exists and the line number of
    the first occurrence of the checkbox string. This is the 'resolved checkbox refs'
    half of the source lock. Live verification of *checkbox state* is a later wave."""
    refs: List[dict] = []
    for entry in entries:
        prov = entry.get("provenance") or {}
        owning = str(prov.get("owning_handoff") or "")
        checkbox = str(prov.get("checkbox") or "")
        handoff_path = (repo_root / owning) if owning else None
        exists = bool(handoff_path and handoff_path.is_file())
        line: Optional[int] = None
        if exists and checkbox:
            try:
                for idx, text in enumerate(
                    handoff_path.read_text(encoding="utf-8").splitlines(), 1
                ):
                    if checkbox in text:
                        line = idx
                        break
            except OSError:
                line = None
        refs.append(
            {
                "task_id": entry.get("task_id"),
                "owning_handoff": owning,
                "checkbox": checkbox,
                "also_flips": list(prov.get("also_flips") or []),
                "handoff_exists": exists,
                "checkbox_line": line,
                "resolved": bool(exists and line is not None),
            }
        )
    return refs


def build_sources_lock(
    entries: List[dict], repos: Dict[str, Path], repo_root: Path
) -> dict:
    return {
        "schema_version": SOURCES_LOCK_SCHEMA_VERSION,
        "generated_at": _utcnow_iso(),
        "repos": repo_lock(repos),
        "checkbox_refs": resolve_checkbox_refs(entries, repo_root),
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def _print_invalid(invalid: Dict[str, List[str]]) -> None:
    for label, errs in invalid.items():
        print(f"  INVALID {label}", file=sys.stderr)
        for e in errs:
            print(f"    - {e}", file=sys.stderr)


def cmd_validate(args: argparse.Namespace) -> int:
    validator = load_schema(args.schema)
    entries = load_entries(args.entries_dir)
    valid, invalid = validate_all(entries, validator)
    print(f"entries: {len(entries)}  valid: {len(valid)}  invalid: {len(invalid)}")
    if invalid:
        _print_invalid(invalid)
        return 1
    print("OK: all entries valid (schema + lint).")
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    validator = load_schema(args.schema)
    entries = load_entries(args.entries_dir)
    valid, invalid = validate_all(entries, validator)
    if invalid:
        print(
            f"REFUSING TO COMPILE: {len(invalid)} invalid ent(y/ies).", file=sys.stderr
        )
        _print_invalid(invalid)
        return 1

    valid_entries = [e for _, e in valid]
    manifest = build_manifest(valid_entries)
    sources_lock = build_sources_lock(valid_entries, args.repos, args.repo_root)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.yaml"
    lock_path = out_dir / "sources.lock.json"
    manifest_path.write_text(
        yaml.safe_dump(
            manifest, sort_keys=False, default_flow_style=False, allow_unicode=True
        ),
        encoding="utf-8",
    )
    lock_path.write_text(json.dumps(sources_lock, indent=2) + "\n", encoding="utf-8")

    print(f"compiled {manifest['entry_count']} entr(y/ies)")
    print(f"  manifest:     {manifest_path}")
    print(f"  sources lock: {lock_path}")
    unresolved = [
        r["task_id"] for r in sources_lock["checkbox_refs"] if not r["resolved"]
    ]
    if unresolved:
        print(
            f"  note: {len(unresolved)} checkbox ref(s) unresolved "
            f"(handoff/checkbox not found): {', '.join(map(str, unresolved))}"
        )
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    validator = load_schema(args.schema)
    entries = load_entries(args.entries_dir)
    valid, invalid = validate_all(entries, validator)
    if invalid:
        print("REFUSING TO SIMULATE: invalid entries present.", file=sys.stderr)
        _print_invalid(invalid)
        return 1

    manifest = build_manifest([e for _, e in valid])
    result = batch_ledger.simulate(manifest)  # empty in-memory ledger

    print("=== --simulate: pick-next ordering over an EMPTY ledger (no inference) ===")
    print(f"entries: {manifest['entry_count']}")
    if not result["order"]:
        print("(nothing schedulable)")
    for i, step in enumerate(result["order"], 1):
        deps = ", ".join(step["depends_on"]) if step["depends_on"] else "-"
        print(
            f"  {i:>2}. {step['task_id']:<24} "
            f"phase={step['phase']} priority={step['priority']} deps=[{deps}]"
        )
    if result["unscheduled"]:
        print(
            "UNSCHEDULED (unsatisfiable deps / cycle): "
            + ", ".join(result["unscheduled"])
        )
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compile_inference_batch.py",
        description="Compile / validate / simulate the consolidated inference-batch manifest.",
    )
    p.add_argument(
        "--entries-dir", type=Path, default=DEFAULT_ENTRIES_DIR,
        help="directory of *.yaml entry files (default: %(default)s)",
    )
    p.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT_DIR,
        help="output directory for manifest.yaml + sources.lock.json",
    )
    p.add_argument(
        "--schema", type=Path, default=DEFAULT_SCHEMA,
        help="path to inference_batch.schema.json",
    )
    p.add_argument(
        "--simulate", action="store_true",
        help="force simulate mode (pick-next dry-run over an empty ledger)",
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser("compile", help="validate + emit manifest.yaml + sources.lock.json")
    sub.add_parser("validate", help="validate all entries; nonzero exit if any invalid")
    sub.add_parser("simulate", help="dry pick-next ordering over an empty ledger")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # Resolve repo set + root for the source lock (fixed defaults; not CLI-exposed).
    args.repos = DEFAULT_REPOS
    args.repo_root = REPO_ROOT

    mode = "simulate" if args.simulate else args.command
    if mode == "simulate":
        return cmd_simulate(args)
    if mode == "validate":
        return cmd_validate(args)
    if mode == "compile":
        return cmd_compile(args)
    build_parser().print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
