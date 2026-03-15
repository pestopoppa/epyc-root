#!/usr/bin/env python3
"""Validate the research intake index and taxonomy."""

from __future__ import annotations

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
TAXONOMY_PATH = RESEARCH / "taxonomy.yaml"

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
    "not_applicable", "superseded",
}

CROSSREF_DIRS = {
    "chapters": Path("/mnt/raid0/llm/epyc-inference-research/docs/chapters"),
    "handoffs": [ROOT / "handoffs" / "active", ROOT / "handoffs" / "completed", ROOT / "handoffs" / "archived"],
    "experiments": Path("/mnt/raid0/llm/epyc-inference-research/docs/experiments"),
}


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


def validate_index(entries: list[dict], valid_categories: set[str]) -> list[str]:
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
        if isinstance(xrefs, dict):
            for ref_type, ref_list in xrefs.items():
                if not isinstance(ref_list, list):
                    continue
                for ref_file in ref_list:
                    if ref_type == "chapters":
                        path = CROSSREF_DIRS["chapters"] / ref_file
                        if not path.exists():
                            errors.append(f"{eid}: cross-ref chapter '{ref_file}' not found")
                    elif ref_type == "handoffs":
                        found = any(
                            (d / ref_file).exists() for d in CROSSREF_DIRS["handoffs"]
                        )
                        if not found:
                            errors.append(f"{eid}: cross-ref handoff '{ref_file}' not found")
                    elif ref_type == "experiments":
                        path = CROSSREF_DIRS["experiments"] / ref_file
                        if not path.exists():
                            errors.append(f"{eid}: cross-ref experiment '{ref_file}' not found")

    return errors


def main() -> int:
    errors = []

    # Validate taxonomy
    if not TAXONOMY_PATH.exists():
        print(f"ERROR: Taxonomy not found at {TAXONOMY_PATH}")
        return 1
    taxonomy = load_yaml(TAXONOMY_PATH)
    errors.extend(validate_taxonomy(taxonomy))
    valid_categories = set(taxonomy.get("categories", {}).keys())

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
        errors.extend(validate_index(entries, valid_categories))

    if errors:
        print(f"FAILED: {len(errors)} error(s) found:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"OK: Taxonomy valid, {len(entries)} index entries validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
