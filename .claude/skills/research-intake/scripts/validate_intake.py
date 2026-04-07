#!/usr/bin/env python3
"""Validate the research intake index and taxonomy."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[4]  # epyc-root
RESEARCH = ROOT / "research"
INDEX_PATH = RESEARCH / "intake_index.yaml"

REQUIRED_FIELDS = {
    "id", "arxiv_id", "url", "source_type", "title", "categories",
    "novelty", "relevance", "discovered_via", "verdict", "ingested_date",
}
SOURCE_TYPES = {"paper", "blog", "repo"}
NOVELTY_VALUES = {"high", "medium", "low", "duplicate"}
RELEVANCE_VALUES = {"high", "medium", "low", "none"}
DISCOVERED_VIA_VALUES = {"seed", "input", "expansion", "search"}
VERDICT_VALUES = {
    "new_opportunity", "already_integrated", "worth_investigating",
    "not_applicable", "superseded", "adopt_patterns", "adopt_component",
}

# Default paths — overridden by wiki.yaml if present
_RESEARCH_ROOT_DEFAULT = "/mnt/raid0/llm/epyc-inference-research"


def _expand_path(p: str) -> Path:
    """Expand ${ENV_VAR:-default} patterns and return a Path."""
    return Path(os.path.expandvars(p))


def load_wiki_config() -> dict:
    """Load wiki.yaml from repo root. Returns empty dict if not found."""
    wiki_path = ROOT / "wiki.yaml"
    if wiki_path.exists():
        with open(wiki_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _get_crossref_dirs(config: dict) -> dict:
    """Build CROSSREF_DIRS from wiki.yaml config, falling back to defaults."""
    xref = config.get("cross_references", {})
    research_root = os.environ.get("EPYC_RESEARCH_ROOT", _RESEARCH_ROOT_DEFAULT)

    chapters_path = xref.get("chapters", {}).get("path", f"{research_root}/docs/chapters")
    experiments_path = xref.get("experiments", {}).get("path", f"{research_root}/docs/experiments")

    handoff_paths_cfg = xref.get("handoffs", {}).get("paths",
        ["handoffs/active", "handoffs/completed", "handoffs/archived"])
    handoff_paths = []
    for p in handoff_paths_cfg:
        expanded = _expand_path(p)
        handoff_paths.append(expanded if expanded.is_absolute() else ROOT / expanded)

    return {
        "chapters": _expand_path(chapters_path),
        "handoffs": handoff_paths,
        "experiments": _expand_path(experiments_path),
    }


def _get_taxonomy_path(config: dict) -> Path:
    """Get taxonomy path from wiki.yaml config, falling back to default."""
    tax_cfg = config.get("taxonomy", {})
    legacy = tax_cfg.get("legacy", "research/taxonomy.yaml")
    legacy_path = ROOT / legacy
    return legacy_path


def _load_aliases(config: dict) -> dict[str, str]:
    """Load category aliases from wiki/SCHEMA.md if it exists.

    Parses the Aliases table in SCHEMA.md. Each row maps one or more
    alias keys to a canonical category.
    Returns: {alias: canonical} mapping.
    """
    aliases = {}
    tax_cfg = config.get("taxonomy", {})
    schema_rel = tax_cfg.get("source", "wiki/SCHEMA.md")
    schema_path = ROOT / schema_rel
    if not schema_path.exists():
        return aliases

    with open(schema_path) as f:
        content = f.read()

    # Find the Aliases section and parse table rows
    in_aliases = False
    for line in content.splitlines():
        if line.strip().startswith("## Aliases"):
            in_aliases = True
            continue
        if in_aliases and line.strip().startswith("## "):
            break  # next section
        if not in_aliases:
            continue
        # Parse table rows: | alias1, alias2 | canonical |
        m = re.match(r'\|\s*`?([^|`]+?)`?\s*\|\s*`?([^|`]+?)`?\s*\|', line)
        if m:
            alias_part = m.group(1).strip()
            canonical = m.group(2).strip()
            # Skip header rows
            if alias_part in ("Alias", "---", "-----"):
                continue
            # Handle comma-separated aliases
            for alias in alias_part.split(","):
                alias = alias.strip().strip("`")
                if alias and alias not in ("Alias", "---"):
                    aliases[alias] = canonical

    return aliases


def load_yaml(path: Path) -> object:
    with open(path) as f:
        return yaml.safe_load(f)


def validate_taxonomy(taxonomy: dict) -> list[str]:
    errors = []
    cats = taxonomy.get("categories", {})
    if not cats:
        errors.append("Taxonomy has no categories defined")
    for key, val in cats.items():
        if not isinstance(val, dict):
            errors.append(f"Category '{key}' is not a mapping")
            continue
        for field in ("label", "description", "related_chapters"):
            if field not in val:
                errors.append(f"Category '{key}' missing field '{field}'")
    return errors


def validate_index(entries: list[dict], valid_categories: set[str],
                   crossref_dirs: dict | None = None) -> list[str]:
    errors = []
    seen_ids = set()
    seen_arxiv = set()
    prev_num = 0

    for i, entry in enumerate(entries):
        eid = entry.get("id", f"<missing at index {i}>")

        # Required fields
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            errors.append(f"{eid}: missing required fields: {missing}")

        # ID format and sequencing
        if isinstance(eid, str) and eid.startswith("intake-"):
            try:
                num = int(eid.split("-", 1)[1])
                if num != prev_num + 1:
                    errors.append(f"{eid}: ID not sequential (expected intake-{prev_num + 1:03d})")
                prev_num = num
            except ValueError:
                errors.append(f"{eid}: malformed ID number")
        else:
            errors.append(f"Entry {i}: ID must start with 'intake-'")

        # Uniqueness
        if eid in seen_ids:
            errors.append(f"{eid}: duplicate ID")
        seen_ids.add(eid)

        arxiv_id = entry.get("arxiv_id")
        if arxiv_id is not None:
            if arxiv_id in seen_arxiv:
                errors.append(f"{eid}: duplicate arxiv_id '{arxiv_id}'")
            seen_arxiv.add(arxiv_id)

        # Enum validation
        st = entry.get("source_type")
        if st and st not in SOURCE_TYPES:
            errors.append(f"{eid}: invalid source_type '{st}'")

        nov = entry.get("novelty")
        if nov and nov not in NOVELTY_VALUES:
            errors.append(f"{eid}: invalid novelty '{nov}'")

        rel = entry.get("relevance")
        if rel and rel not in RELEVANCE_VALUES:
            errors.append(f"{eid}: invalid relevance '{rel}'")

        dv = entry.get("discovered_via")
        if dv and dv not in DISCOVERED_VIA_VALUES:
            errors.append(f"{eid}: invalid discovered_via '{dv}'")

        ver = entry.get("verdict")
        if ver and ver not in VERDICT_VALUES:
            errors.append(f"{eid}: invalid verdict '{ver}'")

        # Credibility score validation (optional field)
        cred = entry.get("credibility_score")
        if cred is not None:
            if not isinstance(cred, int) or cred < 0 or cred > 6:
                errors.append(f"{eid}: credibility_score must be integer 0-6, got {cred!r}")

        # Contradicting evidence validation (optional field)
        contra = entry.get("contradicting_evidence")
        if contra is not None:
            if not isinstance(contra, list):
                errors.append(f"{eid}: contradicting_evidence must be a list, got {type(contra).__name__}")
            elif not all(isinstance(s, str) for s in contra):
                errors.append(f"{eid}: contradicting_evidence must contain only strings")

        # Category validation
        cats = entry.get("categories", [])
        if not isinstance(cats, list) or len(cats) == 0:
            errors.append(f"{eid}: categories must be a non-empty list")
        else:
            for cat in cats:
                if cat not in valid_categories:
                    errors.append(f"{eid}: unknown category '{cat}'")

        # Cross-reference file existence (warn, don't error)
        xrefs = entry.get("cross_references", {})
        if isinstance(xrefs, dict) and crossref_dirs:
            for ref_type, ref_list in xrefs.items():
                if not isinstance(ref_list, list):
                    continue
                for ref_file in ref_list:
                    if ref_type == "chapters" and "chapters" in crossref_dirs:
                        path = crossref_dirs["chapters"] / ref_file
                        if not path.exists():
                            errors.append(f"{eid}: cross-ref chapter '{ref_file}' not found")
                    elif ref_type == "handoffs" and "handoffs" in crossref_dirs:
                        found = any(
                            (d / ref_file).exists() for d in crossref_dirs["handoffs"]
                        )
                        if not found:
                            errors.append(f"{eid}: cross-ref handoff '{ref_file}' not found")
                    elif ref_type == "experiments" and "experiments" in crossref_dirs:
                        path = crossref_dirs["experiments"] / ref_file
                        if not path.exists():
                            errors.append(f"{eid}: cross-ref experiment '{ref_file}' not found")

    return errors


def main() -> int:
    errors = []
    config = load_wiki_config()

    # Validate taxonomy
    taxonomy_path = _get_taxonomy_path(config)
    if not taxonomy_path.exists():
        print(f"ERROR: Taxonomy not found at {taxonomy_path}")
        return 1
    taxonomy = load_yaml(taxonomy_path)
    errors.extend(validate_taxonomy(taxonomy))
    valid_categories = set(taxonomy.get("categories", {}).keys())

    # Load aliases from SCHEMA.md (extends valid categories without modifying taxonomy.yaml)
    aliases = _load_aliases(config)
    if aliases:
        # Add alias keys and their canonical targets to valid set
        valid_categories.update(aliases.keys())
        valid_categories.update(aliases.values())
        print(f"INFO: Loaded {len(aliases)} category aliases from SCHEMA.md")

    # Validate index
    if not INDEX_PATH.exists():
        print(f"WARNING: Index not found at {INDEX_PATH} — skipping index validation")
        if errors:
            for e in errors:
                print(f"  ERROR: {e}")
            return 1
        print("OK: Taxonomy valid, no index to validate")
        return 0

    data = load_yaml(INDEX_PATH)
    entries = data if isinstance(data, list) else data.get("entries", [])
    if not entries:
        print("WARNING: Index is empty")
    else:
        crossref_dirs = _get_crossref_dirs(config)
        errors.extend(validate_index(entries, valid_categories, crossref_dirs))

    if errors:
        print(f"FAILED: {len(errors)} error(s) found:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"OK: Taxonomy valid, {len(entries)} index entries validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
