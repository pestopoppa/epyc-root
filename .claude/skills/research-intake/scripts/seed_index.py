#!/usr/bin/env python3
"""Bootstrap the intake index from existing arXiv references across all repos.

Scans chapters, handoffs, experiments, and research notes for arXiv IDs,
deduplicates, infers categories from source location, and writes the
initial intake_index.yaml.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[4]  # epyc-root
RESEARCH_ROOT = Path("/mnt/raid0/llm/epyc-inference-research")
INDEX_PATH = ROOT / "research" / "intake_index.yaml"
TAXONOMY_PATH = ROOT / "research" / "taxonomy.yaml"

# arXiv ID pattern: YYMM.NNNNN (with optional vN version suffix)
ARXIV_RE = re.compile(r'(?:arxiv[:\s./]+|abs/|pdf/)(\d{4}\.\d{4,5})(?:v\d+)?', re.IGNORECASE)
# Also match bare IDs in markdown link contexts like [text](https://arxiv.org/abs/YYMM.NNNNN)
ARXIV_URL_RE = re.compile(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?')

# Map source directories to likely categories
DIR_CATEGORY_MAP = {
    "01-speculative-decoding": ["speculative_decoding"],
    "02-moe-optimization": ["moe_optimization"],
    "03-prompt-lookup": ["speculative_decoding"],
    "04-radix-attention": ["kv_cache"],
    "05-deprecated-approaches": ["speculative_decoding"],
    "06-benchmarking-framework": ["benchmark_methodology"],
    "07-benchmark-suite-construction": ["benchmark_methodology"],
    "08-cost-aware-rewards": ["cost_aware_routing"],
    "09-claude-debugger": ["agent_architecture"],
    "10-advanced-speculative-decoding": ["speculative_decoding"],
}

# Map handoff keywords to categories
HANDOFF_CATEGORY_HINTS = {
    "speculation": ["speculative_decoding"],
    "tree-spec": ["speculative_decoding"],
    "hsd": ["speculative_decoding"],
    "routing": ["routing_intelligence"],
    "multimodal": ["multimodal"],
    "lora": ["training_distillation"],
    "context-extension": ["context_extension"],
    "yarn": ["context_extension"],
    "benchmark": ["benchmark_methodology"],
    "worker-eval": ["benchmark_methodology"],
    "orchestrator": ["agent_architecture"],
    "swarm": ["swarm_techniques"],
    "autopilot": ["autonomous_research"],
}


def extract_arxiv_ids(text: str) -> list[tuple[str, str]]:
    """Extract arXiv IDs with surrounding context."""
    results = []
    seen = set()
    for pattern in (ARXIV_RE, ARXIV_URL_RE):
        for m in pattern.finditer(text):
            aid = m.group(1)
            if aid not in seen:
                seen.add(aid)
                start = max(0, m.start() - 80)
                end = min(len(text), m.end() + 80)
                context = text[start:end].replace("\n", " ").strip()
                results.append((aid, context))
    return results


def infer_categories(filepath: Path, filename: str) -> list[str]:
    """Infer categories from the source file path."""
    # Check chapter-based mapping
    for key, cats in DIR_CATEGORY_MAP.items():
        if key in filename:
            return cats

    # Check handoff keyword hints
    fname_lower = filename.lower()
    for hint, cats in HANDOFF_CATEGORY_HINTS.items():
        if hint in fname_lower:
            return cats

    # Check parent directory
    parent = filepath.parent.name
    if parent == "experiments":
        return ["benchmark_methodology"]

    # Default
    return ["speculative_decoding"]  # Most common in this project


def scan_directory(dirpath: Path, glob_pattern: str = "*.md") -> dict[str, dict]:
    """Scan a directory for arXiv references."""
    found: dict[str, dict] = {}
    if not dirpath.exists():
        return found

    for mdfile in dirpath.rglob(glob_pattern):
        try:
            text = mdfile.read_text(errors="replace")
        except OSError:
            continue

        for arxiv_id, context in extract_arxiv_ids(text):
            if arxiv_id not in found:
                found[arxiv_id] = {
                    "sources": [],
                    "contexts": [],
                    "categories": set(),
                }
            found[arxiv_id]["sources"].append(str(mdfile.relative_to(mdfile.parents[2]) if len(mdfile.parents) > 2 else mdfile.name))
            found[arxiv_id]["contexts"].append(context)
            cats = infer_categories(mdfile, mdfile.name)
            found[arxiv_id]["categories"].update(cats)

    return found


def merge_findings(*dicts: dict[str, dict]) -> dict[str, dict]:
    """Merge multiple scan results."""
    merged: dict[str, dict] = {}
    for d in dicts:
        for aid, info in d.items():
            if aid not in merged:
                merged[aid] = {"sources": [], "contexts": [], "categories": set()}
            merged[aid]["sources"].extend(info["sources"])
            merged[aid]["contexts"].extend(info["contexts"])
            merged[aid]["categories"].update(info["categories"])
    return merged


def build_cross_references(sources: list[str]) -> dict[str, list[str]]:
    """Build cross_references from source file paths."""
    xrefs: dict[str, list[str]] = {}
    for src in sources:
        parts = Path(src).parts
        filename = Path(src).name
        if "chapters" in parts:
            xrefs.setdefault("chapters", []).append(filename)
        elif "handoffs" in parts:
            xrefs.setdefault("handoffs", []).append(filename)
        elif "experiments" in parts:
            xrefs.setdefault("experiments", []).append(filename)
    # Deduplicate
    return {k: sorted(set(v)) for k, v in xrefs.items()}


def load_valid_categories(taxonomy_path: Path) -> set[str]:
    """Load valid category keys from taxonomy."""
    with open(taxonomy_path) as f:
        taxonomy = yaml.safe_load(f)
    return set(taxonomy.get("categories", {}).keys())


def main() -> int:
    if INDEX_PATH.exists():
        print(f"WARNING: {INDEX_PATH} already exists. Remove it first to re-seed.")
        return 1

    valid_cats = load_valid_categories(TAXONOMY_PATH)
    today = date.today().isoformat()

    # Scan all sources
    print("Scanning chapters...")
    chapters = scan_directory(RESEARCH_ROOT / "docs" / "chapters")

    print("Scanning active handoffs...")
    active_handoffs = scan_directory(ROOT / "handoffs" / "active")

    print("Scanning completed handoffs...")
    completed_handoffs = scan_directory(ROOT / "handoffs" / "completed")

    print("Scanning archived handoffs...")
    archived_handoffs = scan_directory(ROOT / "handoffs" / "archived")

    print("Scanning experiments...")
    experiments = scan_directory(RESEARCH_ROOT / "docs" / "experiments")

    print("Scanning research notes...")
    research_notes = scan_directory(ROOT / "research")

    # Merge all findings
    all_refs = merge_findings(
        chapters, active_handoffs, completed_handoffs,
        archived_handoffs, experiments, research_notes,
    )

    print(f"Found {len(all_refs)} unique arXiv IDs")

    # Build index entries
    entries = []
    for i, (arxiv_id, info) in enumerate(sorted(all_refs.items()), start=1):
        # Filter categories to valid ones
        cats = sorted(info["categories"] & valid_cats)
        if not cats:
            cats = ["speculative_decoding"]  # Fallback

        # Use first context as citation_context
        context = info["contexts"][0] if info["contexts"] else ""

        xrefs = build_cross_references(info["sources"])

        entry = {
            "id": f"intake-{i:03d}",
            "arxiv_id": arxiv_id,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "source_type": "paper",
            "title": f"arXiv:{arxiv_id}",  # Placeholder — full title requires fetching
            "categories": cats,
            "novelty": "low",
            "relevance": "medium",
            "discovered_via": "seed",
            "verdict": "already_integrated",
            "ingested_date": today,
            "citation_context": context,
        }
        if xrefs:
            entry["cross_references"] = xrefs

        entries.append(entry)

    # Write index
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w") as f:
        # Write a header comment
        f.write("# Research Intake Index\n")
        f.write("# Auto-generated by seed_index.py — do not edit header\n")
        f.write("# New entries appended by the research-intake skill\n\n")
        yaml.dump(entries, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Wrote {len(entries)} entries to {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
