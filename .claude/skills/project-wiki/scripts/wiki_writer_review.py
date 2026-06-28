#!/usr/bin/env python3
"""Prepare and validate model-written project-wiki drafts.

This script is intentionally inference-free. It defines the local writer role
and the adoption gate for future AutoWiki-style article drafts, but it does not
call a model or write wiki pages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from compile_sources import WRITER_EVIDENCE_POLICY
except ImportError:
    WRITER_EVIDENCE_POLICY = {
        "policy_version": 1,
        "applies_to": "generated-wiki-article-writes",
        "minimum_confidence": "verified",
        "minimum_source_references": 3,
        "requires_source_reference_section": True,
        "requires_structural_lint": True,
        "requires_human_or_measured_review": True,
    }


ROOT = Path(__file__).resolve().parents[4]
SCHEMA_VERSION = 1
PACKET_KIND = "project-wiki-writer-packet"
EVIDENCE_KIND = "project-wiki-writer-evidence"

DEFAULT_WRITER_CONFIG = {
    "role": "worker_general",
    "role_source": "orchestrator stack role; model id resolves at execution time",
    "temperature": 0.2,
    "draft_dir": "wiki/drafts",
    "review_modes": ["human", "measured"],
}


def load_writer_config() -> dict:
    """Load writer config from wiki.yaml, with conservative defaults."""
    config = dict(DEFAULT_WRITER_CONFIG)
    path = ROOT / "wiki.yaml"
    if not HAS_YAML or not path.exists():
        return config
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return config
    writer = data.get("wiki_writer", {})
    if isinstance(writer, dict):
        config.update({k: v for k, v in writer.items() if v is not None})
    return config


def _resolve(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _source_reference_count(markdown: str) -> int:
    headings = list(re.finditer(r"^##\s+(Source References|References)\s*$", markdown, re.MULTILINE))
    if not headings:
        return 0
    start = headings[-1].end()
    next_heading = re.search(r"^##\s+", markdown[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(markdown)
    section = markdown[start:end]
    return len(re.findall(r"\[[^\]]+\]\([^)]+\)", section))


def validate_draft_structure(markdown: str) -> list[str]:
    """Return structural errors that block generated article adoption."""
    errors: list[str] = []
    h1_count = len(re.findall(r"^#\s+.+", markdown, re.MULTILINE))
    if h1_count != 1:
        errors.append(f"expected exactly one H1 heading, found {h1_count}")
    if not re.search(r"^\*\*Category\*\*:\s*`?[^`\n]+`?\s*$", markdown, re.MULTILINE):
        errors.append("missing **Category** metadata")
    if not re.search(r"^##\s+Summary\s*$", markdown, re.MULTILINE):
        errors.append("missing ## Summary")
    if _source_reference_count(markdown) < WRITER_EVIDENCE_POLICY["minimum_source_references"]:
        errors.append(
            "source-reference section must contain at least "
            f"{WRITER_EVIDENCE_POLICY['minimum_source_references']} markdown links"
        )
    return errors


def validate_manifest_for_writer(manifest: dict) -> list[str]:
    """Return manifest errors that block model-written draft preparation."""
    errors: list[str] = []
    if manifest.get("kind") != "project-wiki-source-manifest":
        errors.append("manifest kind must be 'project-wiki-source-manifest'")
    policy = manifest.get("writer_evidence_policy")
    if not isinstance(policy, dict):
        errors.append("writer_evidence_policy missing")
    else:
        for key, expected in WRITER_EVIDENCE_POLICY.items():
            if policy.get(key) != expected:
                errors.append(
                    "writer_evidence_policy "
                    f"{key} must be {expected!r}, got {policy.get(key)!r}"
                )
    if not isinstance(manifest.get("sources"), list):
        errors.append("manifest sources must be a list")
    return errors


def build_writer_packet(
    manifest: dict,
    *,
    category: str | None = None,
    source_limit: int | None = None,
) -> dict:
    """Build a reviewable writer packet from a source manifest."""
    errors = validate_manifest_for_writer(manifest)
    if errors:
        raise ValueError("; ".join(errors))
    config = load_writer_config()
    sources = list(manifest.get("sources", []))
    if source_limit is not None:
        sources = sources[:source_limit]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": PACKET_KIND,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "category": category,
        "writer": {
            "role": config["role"],
            "role_source": config["role_source"],
            "temperature": config["temperature"],
        },
        "draft_dir": config["draft_dir"],
        "adoption_gate": {
            "evidence_kind": EVIDENCE_KIND,
            "required_confidence": WRITER_EVIDENCE_POLICY["minimum_confidence"],
            "minimum_source_references": WRITER_EVIDENCE_POLICY["minimum_source_references"],
            "review_modes": config["review_modes"],
            "requires_structural_lint": True,
            "requires_human_or_measured_review": True,
        },
        "manifest": {
            "source_set_hash": manifest.get("source_set_hash"),
            "mode": manifest.get("mode"),
            "total_sources": len(manifest.get("sources", [])),
        },
        "sources": sources,
    }
    packet_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["packet_hash"] = packet_hash
    return payload


def validate_writer_evidence(draft_path: Path, evidence_path: Path) -> dict:
    """Validate a generated draft plus sidecar evidence without adopting it."""
    config = load_writer_config()
    evidence = _read_json(evidence_path)
    draft = draft_path.read_text(encoding="utf-8")
    errors = validate_draft_structure(draft)

    if evidence.get("kind") != EVIDENCE_KIND:
        errors.append(f"evidence kind must be {EVIDENCE_KIND!r}")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"evidence schema_version must be {SCHEMA_VERSION}")
    writer = evidence.get("writer")
    if not isinstance(writer, dict):
        errors.append("evidence writer must be an object")
    elif writer.get("role") != config["role"]:
        errors.append(
            f"evidence writer.role must be {config['role']!r}, got {writer.get('role')!r}"
        )
    if evidence.get("confidence") != WRITER_EVIDENCE_POLICY["minimum_confidence"]:
        errors.append(
            "evidence confidence must be "
            f"{WRITER_EVIDENCE_POLICY['minimum_confidence']!r}"
        )
    review = evidence.get("review")
    allowed_modes = set(config["review_modes"])
    if not isinstance(review, dict):
        errors.append("evidence review must be an object")
    else:
        if review.get("mode") not in allowed_modes:
            errors.append(
                f"evidence review.mode must be one of {sorted(allowed_modes)!r}"
            )
        if review.get("verdict") != "accept":
            errors.append("evidence review.verdict must be 'accept'")
    references = evidence.get("source_references")
    min_refs = WRITER_EVIDENCE_POLICY["minimum_source_references"]
    if not isinstance(references, list) or len(references) < min_refs:
        errors.append(f"evidence source_references must include at least {min_refs} paths")

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "project-wiki-writer-validation",
        "draft_path": str(draft_path.relative_to(ROOT)) if draft_path.is_relative_to(ROOT) else str(draft_path),
        "evidence_path": str(evidence_path.relative_to(ROOT)) if evidence_path.is_relative_to(ROOT) else str(evidence_path),
        "ok": not errors,
        "errors": errors,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Emit a writer packet from a source manifest.")
    plan.add_argument("--manifest", required=True, help="Project-wiki source manifest.")
    plan.add_argument("--category", help="Target wiki category slug.")
    plan.add_argument("--source-limit", type=int, help="Limit sources included in packet.")
    plan.add_argument("--output", help="Optional output JSON path.")

    validate = sub.add_parser("validate", help="Validate a draft plus writer evidence.")
    validate.add_argument("--draft", required=True, help="Draft markdown file.")
    validate.add_argument("--evidence", required=True, help="Writer evidence JSON.")
    validate.add_argument("--output", help="Optional validation report JSON path.")

    args = parser.parse_args()
    try:
        if args.command == "plan":
            packet = build_writer_packet(
                _read_json(_resolve(args.manifest)),
                category=args.category,
                source_limit=args.source_limit,
            )
            if args.output:
                _write_json(_resolve(args.output), packet)
            json.dump(packet, sys.stdout, indent=2, sort_keys=True)
            print()
            return 0

        report = validate_writer_evidence(_resolve(args.draft), _resolve(args.evidence))
        if args.output:
            _write_json(_resolve(args.output), report)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        print()
        return 0 if report["ok"] else 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
