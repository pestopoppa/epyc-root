#!/usr/bin/env python3
"""Text-preserving migration for the pre-disposition intake backlog.

The migration deliberately parses YAML only for classification. It inserts new
fields into individual raw entry blocks and never serializes the full index.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
INDEX_PATH = ROOT / "research" / "intake_index.yaml"
DEFAULT_AUDIT_PATH = (
    ROOT / "artifacts" / "audit" / "intake-disposition-backfill-20260805.json"
)
ACTIONABLE_VERDICTS = {"worth_investigating", "new_opportunity"}
CUTOFF = "2026-07-28"
EXPECTED_TARGETS = 230
EXPECTED_DIRECT_ROUTES = 163

INTAKE_REFERENCE_RE = re.compile(
    r"(?i)\bintake-(\d+)((?:\s*/\s*(?:intake-)?\d+)*)"
)
ENTRY_START_RE = re.compile(r"(?m)^- id: (intake-\d+)\n")


MANUAL_INTEGRATED_ROUTES = {
    "intake-105": ["handoffs/active/autopilot-continuous-optimization.md"],
    "intake-106": ["handoffs/active/autopilot-continuous-optimization.md"],
    "intake-142": ["handoffs/active/autopilot-continuous-optimization.md"],
    "intake-148": ["handoffs/active/autopilot-continuous-optimization.md"],
    "intake-162": ["handoffs/completed/08-doc-to-lora-prototype.md"],
    "intake-164": ["handoffs/completed/08-doc-to-lora-prototype.md"],
    "intake-195": ["handoffs/completed/kv-cache-quantization.md"],
    "intake-319": ["handoffs/active/architect-model-selection-bench.md"],
    "intake-850": ["handoffs/active/reviewer-decision-plane.md"],
    "intake-851": ["handoffs/active/reviewer-calibration-accounting.md"],
    "intake-852": ["handoffs/active/reviewer-calibration-accounting.md"],
    "intake-853": [
        "handoffs/active/reviewer-decision-plane.md",
        "handoffs/active/reviewer-escalation-and-human-gate-policy.md",
    ],
    "intake-854": [
        "handoffs/active/reviewer-escalation-and-human-gate-policy.md"
    ],
    "intake-855": ["handoffs/active/reviewer-calibration-accounting.md"],
    "intake-856": [
        "handoffs/active/reviewer-model-ablations.md",
        "handoffs/active/eval-tower-verification.md",
    ],
    "intake-857": ["handoffs/active/reviewer-calibration-accounting.md"],
    "intake-858": ["handoffs/active/reviewer-decision-plane.md"],
    "intake-891": [
        "handoffs/active/intake-derived-work-2026-07-25.md",
        "handoffs/active/architect-model-selection-bench.md",
    ],
    "intake-893": ["handoffs/active/intake-derived-work-2026-07-25.md"],
}

KNOWLEDGE_ONLY = {
    "intake-169", "intake-278", "intake-279", "intake-281", "intake-291",
    "intake-312", "intake-337", "intake-346", "intake-403", "intake-540",
    "intake-587", "intake-588", "intake-595", "intake-596", "intake-613",
}
MONITOR = {
    "intake-111", "intake-165", "intake-253", "intake-280", "intake-318",
    "intake-341", "intake-348", "intake-373", "intake-416", "intake-420",
    "intake-440", "intake-457", "intake-733", "intake-811",
}
DECLINED = {"intake-898", "intake-909"}
AWAITING_DIVE = {
    "intake-115", "intake-117", "intake-131", "intake-132", "intake-239",
    "intake-526", "intake-556", "intake-604", "intake-754", "intake-765",
    "intake-766", "intake-767", "intake-768", "intake-769", "intake-770",
    "intake-771", "intake-792",
}

SPECIAL_EVIDENCE = {
    "intake-148": (
        "2026-08-05 audit: AutoResearch/PraxLab patterns and follow-ups are recorded "
        "in the AutoPilot owner, including completed failure_context and parent_trial work."
    ),
    "intake-319": (
        "2026-08-05 audit: the SuperGemma candidate was evaluated by the architect-model "
        "selection owner; routing metadata was the missing piece."
    ),
    "intake-850": (
        "2026-08-05 audit: reviewer-control-plane reference R6 grounds the adversarial "
        "CandidatePackage boundary owned by reviewer-decision-plane."
    ),
    "intake-851": (
        "2026-08-05 audit: reviewer-control-plane reference R8 grounds raw-confidence "
        "and cohort-calibration policy owned by reviewer-calibration-accounting."
    ),
    "intake-852": (
        "2026-08-05 audit: reviewer-control-plane reference R9 grounds raw-confidence "
        "and cohort-calibration policy owned by reviewer-calibration-accounting."
    ),
    "intake-853": (
        "2026-08-05 audit: reviewer-control-plane reference R10 grounds ABSTAIN and "
        "risk-coverage behavior in the decision and escalation owners."
    ),
    "intake-854": (
        "2026-08-05 audit: reviewer-control-plane reference R11 grounds the measured, "
        "opt-in rebuttal policy in the escalation owner."
    ),
    "intake-855": (
        "2026-08-05 audit: reviewer-control-plane reference R15 grounds calibrated "
        "selective authority in reviewer-calibration-accounting."
    ),
    "intake-856": (
        "2026-08-05 audit: reviewer-control-plane reference R13 supplies critique-quality "
        "evaluation prior art to the model-ablation and eval-tower owners."
    ),
    "intake-857": (
        "2026-08-05 audit: reviewer-control-plane reference R14 is retained as a "
        "training-time calibration comparison in the calibration owner."
    ),
    "intake-858": (
        "2026-08-05 audit: reviewer-control-plane reference R3 supplies iterative "
        "self-improvement prior art to reviewer-decision-plane."
    ),
    "intake-891": (
        "2026-08-05 audit: ID-15 routed the Fable-Fusion pair to a mandatory GGUF header "
        "gate, followed by completed architect-model benchmark work."
    ),
    "intake-893": (
        "2026-08-05 audit: ID-14 owns the approved container/disposable-host Fractal "
        "trial and its containment-pattern extraction."
    ),
    "intake-898": (
        "2026-08-05 audit: the evaluation owner records FrontierCS as a closed negative "
        "that should not be re-chased."
    ),
    "intake-909": (
        "2026-08-05 audit: this operator-synthesized overview remains Stage-1 unverified "
        "and has no independent source authority; primary looped-transformer sources are "
        "tracked separately."
    ),
}


def _extract_ids(text: str) -> set[str]:
    """Extract explicit and slash-shorthand intake IDs from Markdown."""
    found: set[str] = set()
    for match in INTAKE_REFERENCE_RE.finditer(text):
        numbers = [match.group(1), *re.findall(r"\d+", match.group(2))]
        found.update(f"intake-{int(number):03d}" for number in numbers)
    return found


def _reference_map(paths: list[Path], root: Path) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for base in paths:
        if not base.exists():
            continue
        for path in sorted(base.glob("*.md")):
            if path.name.endswith("index.md") or path.name == "master-handoff-index.md":
                continue
            rel = str(path.relative_to(root))
            for intake_id in _extract_ids(path.read_text(errors="replace")):
                refs.setdefault(intake_id, set()).add(rel)
    return refs


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _append_fields(
    block: str,
    disposition: str,
    evidence: str,
    routes: list[str],
) -> str:
    additions: list[str] = []
    if disposition == "awaiting_dive" and not re.search(
        r"(?m)^  verification:", block
    ):
        additions.append("  verification: stage1-unverified")
    if routes:
        empty_updated = re.search(r"(?m)^  handoffs_updated:\s*\[\]\s*$", block)
        route_lines = "  handoffs_updated:\n" + "\n".join(
            f"  - {_quote(route)}" for route in routes
        )
        if empty_updated:
            block = (
                block[:empty_updated.start()]
                + route_lines
                + block[empty_updated.end():]
            )
        elif not re.search(r"(?m)^  handoffs_updated:", block):
            additions.extend(route_lines.splitlines())
    additions.append(f"  integration_disposition: {disposition}")
    additions.append("  disposition_evidence:")
    additions.append(f"  - {_quote(evidence)}")
    suffix = "\n".join(additions) + "\n"
    return block + ("" if block.endswith("\n") else "\n") + suffix


def _default_evidence(disposition: str, wiki_refs: list[str]) -> str:
    wiki_clause = (
        f" Wiki citation(s): {', '.join(wiki_refs)}."
        if wiki_refs
        else ""
    )
    if disposition == "knowledge_only":
        return (
            "2026-08-05 audit: retained as architecture/methodology/comparison context; "
            "no repository evidence supports an implementation task."
            + wiki_clause
        )
    if disposition == "monitor":
        return (
            "2026-08-05 audit: notes or scope make this conditional/low-priority; revisit "
            "only if its feasibility, release, support, incident, or training-scope trigger changes."
            + wiki_clause
        )
    if disposition == "declined":
        return (
            "2026-08-05 audit: explicitly closed after review; no implementation route "
            "should be inferred from citation alone."
            + wiki_clause
        )
    return (
        "2026-08-05 audit: no durable handoff route or repository-grounded closure was "
        "found; a primary-source Stage-2 dive is required before task creation."
        + wiki_clause
    )


def _classify_manual(intake_id: str) -> str:
    if intake_id in MANUAL_INTEGRATED_ROUTES:
        return "integrated"
    if intake_id in KNOWLEDGE_ONLY:
        return "knowledge_only"
    if intake_id in MONITOR:
        return "monitor"
    if intake_id in DECLINED:
        return "declined"
    if intake_id in AWAITING_DIVE:
        return "awaiting_dive"
    raise KeyError(intake_id)


def migrate(root: Path, apply: bool, audit_path: Path) -> dict:
    index_path = root / "research" / "intake_index.yaml"
    original = index_path.read_text()
    loaded = yaml.safe_load(original)
    entries = loaded if isinstance(loaded, list) else loaded.get("entries", [])
    targets = {
        entry["id"]: entry
        for entry in entries
        if entry.get("verdict") in ACTIONABLE_VERDICTS
        and str(entry.get("ingested_date", "")) <= CUTOFF
        and not entry.get("handoffs_created")
        and not entry.get("handoffs_updated")
        and not entry.get("integration_disposition")
    }
    if not targets:
        return {"status": "already_migrated", "target_count": 0}
    if len(targets) != EXPECTED_TARGETS:
        raise RuntimeError(
            f"expected {EXPECTED_TARGETS} legacy targets, found {len(targets)}"
        )

    handoff_refs = _reference_map(
        [root / "handoffs" / "active", root / "handoffs" / "completed"], root
    )
    wiki_refs = _reference_map([root / "wiki"], root)
    directly_routed = {
        intake_id for intake_id in targets if handoff_refs.get(intake_id)
    }
    if len(directly_routed) != EXPECTED_DIRECT_ROUTES:
        raise RuntimeError(
            f"expected {EXPECTED_DIRECT_ROUTES} directly routed targets, "
            f"found {len(directly_routed)}"
        )

    residual = set(targets) - directly_routed
    manual = (
        set(MANUAL_INTEGRATED_ROUTES)
        | KNOWLEDGE_ONLY
        | MONITOR
        | DECLINED
        | AWAITING_DIVE
    )
    if residual != manual:
        raise RuntimeError(
            "manual classification mismatch: "
            f"missing={sorted(residual - manual)}, extra={sorted(manual - residual)}"
        )

    records: dict[str, dict] = {}
    for intake_id in sorted(targets, key=lambda value: int(value.split("-")[1])):
        direct_routes = sorted(handoff_refs.get(intake_id, set()))
        if direct_routes:
            disposition = "integrated"
            routes = direct_routes
            evidence = (
                "2026-08-05 audit: direct intake-ID citation in the routed handoff owner(s); "
                "integrated describes durable workflow routing, not a deployment claim."
            )
            basis = "direct_handoff_citation"
        else:
            disposition = _classify_manual(intake_id)
            routes = MANUAL_INTEGRATED_ROUTES.get(intake_id, [])
            evidence = SPECIAL_EVIDENCE.get(
                intake_id,
                _default_evidence(
                    disposition, sorted(wiki_refs.get(intake_id, set()))
                ),
            )
            basis = "semantic_repository_audit"
        records[intake_id] = {
            "title": targets[intake_id].get("title"),
            "relevance": targets[intake_id].get("relevance"),
            "disposition": disposition,
            "basis": basis,
            "handoffs_updated": routes,
            "wiki_citations": sorted(wiki_refs.get(intake_id, set())),
            "evidence": evidence,
        }

    matches = list(ENTRY_START_RE.finditer(original))
    blocks: list[str] = []
    migrated: set[str] = set()
    cursor = 0
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(original)
        blocks.append(original[cursor:start])
        block = original[start:end]
        intake_id = match.group(1)
        if intake_id in records:
            record = records[intake_id]
            block = _append_fields(
                block.rstrip("\n") + "\n",
                record["disposition"],
                record["evidence"],
                record["handoffs_updated"],
            )
            migrated.add(intake_id)
        blocks.append(block)
        cursor = end
    blocks.append(original[cursor:])
    if migrated != set(targets):
        raise RuntimeError(f"failed to rewrite: {sorted(set(targets) - migrated)}")
    rewritten = "".join(blocks)

    parsed = yaml.safe_load(rewritten)
    rewritten_entries = parsed if isinstance(parsed, list) else parsed.get("entries", [])
    by_id = {entry["id"]: entry for entry in rewritten_entries}
    for intake_id, record in records.items():
        entry = by_id[intake_id]
        if entry.get("integration_disposition") != record["disposition"]:
            raise RuntimeError(f"post-write disposition mismatch for {intake_id}")
        if record["handoffs_updated"] and entry.get("handoffs_updated") != record["handoffs_updated"]:
            raise RuntimeError(f"post-write routing mismatch for {intake_id}")

    summary = Counter(record["disposition"] for record in records.values())
    audit = {
        "schema": "intake-disposition-backfill-v1",
        "generated_date": datetime.now(timezone.utc).date().isoformat(),
        "cutoff": CUTOFF,
        "target_count": len(records),
        "direct_handoff_citation_count": len(directly_routed),
        "wiki_only_count": sum(
            bool(record["wiki_citations"])
            and not handoff_refs.get(intake_id)
            for intake_id, record in records.items()
        ),
        "disposition_counts": dict(sorted(summary.items())),
        "entries": records,
    }
    if apply:
        index_path.write_text(rewritten)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write index and audit artifact")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT_PATH)
    args = parser.parse_args()
    audit = migrate(args.root.resolve(), args.apply, args.audit_path.resolve())
    print(json.dumps({key: value for key, value in audit.items() if key != "entries"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
