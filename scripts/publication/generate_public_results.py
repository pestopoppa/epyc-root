#!/usr/bin/env python3
"""Generate a public-results draft from epyc-inference-research RESULTS.md.

The generator is intentionally conservative: it never turns historical numbers
into publishable claims. Rows without an explicit protocol marker are emitted
with a hold status so F6-W3 can be regenerated without hand-editing numbers.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs" / "publication" / "public-results-draft.md"
HOST_ATTESTATION_ERA_START = date(2026, 6, 12)
HISTORICAL_ATTESTATION_REVIEW_ACTION = "hold_for_historical_attestation_review"


@dataclass(frozen=True)
class ResultRow:
    section: str
    source_line: int
    entity: str
    quant_or_size: str
    metrics: str
    protocol_status: str
    scrub_status: str
    action: str


@dataclass(frozen=True)
class ProtocolRef:
    protocol_id: str
    n: str | None
    date: str | None
    attestation: str | None


def default_results_path() -> Path:
    candidates = [
        Path("/mnt/raid0/llm/epyc-inference-research"),
        ROOT / "repos" / "epyc-inference-research",
        Path("/workspace/repos/epyc-inference-research"),
    ]
    for repo in candidates:
        path = repo / "docs" / "reference" / "benchmarks" / "RESULTS.md"
        if path.exists():
            return path
    return candidates[0] / "docs" / "reference" / "benchmarks" / "RESULTS.md"


def ascii_clean(text: str) -> str:
    text = text.replace("—", "-").replace("×", "x").replace("≥", ">=")
    text = text.replace("≤", "<=").replace("→", "->").replace("❌", "FAIL")
    text = text.replace("✅", "PASS").replace("🆕", "NEW").replace("⭐", "*")
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def strip_markdown(text: str) -> str:
    text = ascii_clean(text.strip())
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("*", "")
    return re.sub(r"\s+", " ", text).strip()


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _clean_protocol_payload(payload: str) -> str:
    payload = re.sub(r"^protocol[-\s]*id\b[:=]?\s*", "", payload, flags=re.I)
    payload = re.sub(r"^protocol:\s*", "", payload, flags=re.I)
    return payload.strip()


def _parse_protocol_payload(payload: str) -> ProtocolRef | None:
    payload = _clean_protocol_payload(payload)
    match = re.search(r"\b(P-[A-Z][A-Z0-9-]*(?:/[^,\]]+)?)\b", payload, re.I)
    if not match:
        return None

    protocol_id = match.group(1).upper()
    n = _first_match(r"\b(?:n|reps)\s*[:=]?\s*(\d+)\b", payload)
    date = _first_match(r"\b(20\d{2}-\d{2}-\d{2})\b", payload)
    attestation = _first_match(r"\battest(?:ation)?\s*[:=]?\s*([A-Za-z0-9._-]{3,})\b", payload)

    return ProtocolRef(protocol_id=protocol_id, n=n, date=date, attestation=attestation)


def parse_protocol_reference(text: str) -> ProtocolRef | None:
    for bracket in re.findall(r"\[(.*?)\]", text):
        protocol = _parse_protocol_payload(bracket)
        if protocol:
            return protocol

    if re.search(r"protocol(?:-\s*id)?\b|\bprotocol:", text, flags=re.I):
        return _parse_protocol_payload(text)
    return None


def protocol_complete_for_publish(protocol: ProtocolRef) -> bool:
    return bool(protocol.n and protocol.date and protocol.attestation)


def missing_protocol_fields(protocol: ProtocolRef) -> list[str]:
    missing = []
    if not protocol.n:
        missing.append("n/reps")
    if not protocol.date:
        missing.append("date")
    if not protocol.attestation:
        missing.append("attestation")
    return missing


def protocol_date(protocol: ProtocolRef) -> date | None:
    if protocol.date is None:
        return None
    try:
        return date.fromisoformat(protocol.date)
    except ValueError:
        return None


def needs_historical_attestation_review(protocol: ProtocolRef) -> bool:
    run_date = protocol_date(protocol)
    return bool(run_date and run_date < HOST_ATTESTATION_ERA_START and not protocol.attestation)


def format_protocol(protocol: ProtocolRef | None) -> str:
    if protocol is None:
        return ""

    pieces = [protocol.protocol_id]
    if protocol.n:
        pieces.append(f"n={protocol.n}")
    if protocol.date:
        pieces.append(protocol.date)
    if protocol.attestation:
        pieces.append(f"attest {protocol.attestation}")
    return "; ".join(pieces)


SCRUB_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?<!\w)/(?:mnt|workspace|home|tmp|var)/(?:[^\s|`]+)", "local path"),
    (r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b", "loopback endpoint"),
    (r"\b(?:frontdoor|coder_escalation|architect_general|architect_coding|worker_general|ingest_long_context|toolrunner)\b", "internal role alias"),
    (r"\b(?:operator|personal[-\s]task|dashboard)\b", "operator/internal workflow term"),
)


PUBLIC_LABEL_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bfrontdoor\b", "routing entrypoint"),
    (r"\bcoder_escalation\b", "coding specialist"),
    (r"\barchitect_general\b", "architecture specialist"),
    (r"\barchitect_coding\b", "coding architect"),
    (r"\bworker_general\b", "general worker"),
    (r"\bingest_long_context\b", "long-context worker"),
    (r"\btoolrunner\b", "tool worker"),
)


def public_scrub_text(text: str) -> str:
    """Replace internal orchestration labels with public-safe display labels."""
    scrubbed = text
    for pattern, replacement in PUBLIC_LABEL_REPLACEMENTS:
        scrubbed = re.sub(pattern, replacement, scrubbed, flags=re.I)
    return scrubbed


def scrub_findings(*fields: str) -> list[str]:
    text = " ".join(fields)
    findings: list[str] = []
    for pattern, label in SCRUB_PATTERNS:
        if re.search(pattern, text, flags=re.I):
            findings.append(label)
    return findings


def scrub_status(*fields: str) -> str:
    findings = scrub_findings(*(public_scrub_text(field) for field in fields))
    if not findings:
        return "public-safe surface"
    return "needs public scrub: " + ", ".join(findings)


def apply_scrub_gate(action: str, scrub: str) -> str:
    if action == "publish_candidate" and scrub != "public-safe surface":
        return "hold_for_public_scrub"
    return action


def split_table_row(line: str) -> list[str]:
    return [strip_markdown(cell) for cell in line.strip().strip("|").split("|")]


def is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def section_path(stack: dict[int, str]) -> str:
    return " / ".join(stack[level] for level in sorted(stack))


def looks_like_result_table(headers: list[str], section: str) -> bool:
    joined = " ".join(headers + [section]).lower()
    has_entity = any(
        token in joined
        for token in ("model", "configuration", "variant", "role", "compression", "config")
    )
    has_metric = any(
        token in joined
        for token in ("t/s", "throughput", "speed", "ppl", "baseline", "optimized", "per-instance", "aggregate")
    )
    return has_entity and has_metric


def classify_protocol(section: str, row_cells: list[str], nearby: str) -> tuple[str, str]:
    evidence = " ".join([section, nearby, " ".join(row_cells)])
    protocol = parse_protocol_reference(evidence)
    if protocol:
        if protocol_complete_for_publish(protocol):
            return f"protocol-tagged [{format_protocol(protocol)}]", "publish_candidate"
        missing = ", ".join(missing_protocol_fields(protocol))
        if needs_historical_attestation_review(protocol):
            return (
                "protocol-tagged "
                f"(pre-attestation-era; missing {missing}; needs historical attestation or remeasurement) "
                f"[{format_protocol(protocol)}]",
                HISTORICAL_ATTESTATION_REVIEW_ACTION,
            )
        return f"protocol-tagged (missing {missing}) [{format_protocol(protocol)}]", "hold_for_protocol_backfill"

    evidence_l = evidence.lower()
    if "p-bench" in evidence_l or "protocol-id" in evidence_l:
        return "protocol marker present; needs structured protocol backfill", "hold_for_protocol_backfill"
    if any(token in evidence_l for token in ("verified", "benchmarked", "sweep", "quality scored", "canonical")):
        return "evidence-linked; needs protocol tag", "hold_for_protocol_backfill"
    return "unverified historical row", "hold_for_protocol_backfill"


def pick_entity(headers: list[str], row: dict[str, str]) -> str:
    for key in ("Model", "Configuration", "Variant", "Role", "Model + Draft", "Config"):
        if key in row and row[key]:
            return row[key]
    for header in headers:
        if row.get(header):
            return row[header]
    return ""


def pick_quant_or_size(row: dict[str, str]) -> str:
    parts = []
    for key in ("Quant", "Size", "Active Params", "4x RAM"):
        if row.get(key):
            parts.append(f"{key}: {row[key]}")
    return "; ".join(parts)


def pick_metrics(row: dict[str, str]) -> str:
    metric_parts = []
    for header, value in row.items():
        lower = header.lower()
        if any(
            token in lower
            for token in ("t/s", "throughput", "speed", "ppl", "baseline", "optimized", "quality", "aggregate", "per-instance")
        ):
            if value:
                metric_parts.append(f"{header}: {value}")
    return "; ".join(metric_parts)


def collect_rows(text: str) -> list[ResultRow]:
    lines = text.splitlines()
    headings: dict[int, str] = {}
    rows: list[ResultRow] = []
    i = 0
    while i < len(lines):
        heading = re.match(r"^(#{1,6})\s+(.+)$", lines[i].strip())
        if heading:
            level = len(heading.group(1))
            headings = {k: v for k, v in headings.items() if k < level}
            headings[level] = strip_markdown(heading.group(2))
            i += 1
            continue

        if i + 1 >= len(lines) or not is_table_row(lines[i]) or not is_table_row(lines[i + 1]):
            i += 1
            continue

        headers = split_table_row(lines[i])
        separator = split_table_row(lines[i + 1])
        if not is_separator_row(separator):
            i += 1
            continue

        current_section = section_path(headings)
        table_start = i
        j = i + 2
        if looks_like_result_table(headers, current_section):
            while j < len(lines) and is_table_row(lines[j]):
                cells = split_table_row(lines[j])
                if len(cells) < len(headers):
                    cells.extend([""] * (len(headers) - len(cells)))
                row_map = dict(zip(headers, cells))
                metrics = pick_metrics(row_map)
                if metrics:
                    nearby = "\n".join(lines[max(0, table_start - 4): table_start])
                    protocol_status, action = classify_protocol(current_section, cells, nearby)
                    entity = public_scrub_text(pick_entity(headers, row_map))
                    quant_or_size = public_scrub_text(pick_quant_or_size(row_map))
                    metrics = public_scrub_text(metrics)
                    display_section = public_scrub_text(current_section)
                    scrub = scrub_status(display_section, entity, quant_or_size, metrics)
                    rows.append(
                        ResultRow(
                            section=display_section,
                            source_line=j + 1,
                            entity=entity,
                            quant_or_size=quant_or_size,
                            metrics=metrics,
                            protocol_status=protocol_status,
                            scrub_status=scrub,
                            action=apply_scrub_gate(action, scrub),
                        )
                    )
                j += 1
        else:
            while j < len(lines) and is_table_row(lines[j]):
                j += 1
        i = j
    return rows


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def display_source(source: Path) -> str:
    source = source.resolve()
    candidates = [
        (ROOT.resolve(), "epyc-root"),
        (Path("/mnt/raid0/llm/epyc-inference-research"), "epyc-inference-research"),
        ((ROOT / "repos" / "epyc-inference-research"), "epyc-inference-research"),
        (Path("/workspace/repos/epyc-inference-research"), "epyc-inference-research"),
    ]
    for base, label in candidates:
        try:
            rel = source.relative_to(base.resolve())
        except ValueError:
            continue
        return f"{label}/{rel.as_posix()}"
    return source.name


def action_counts(rows: list[ResultRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.action] = counts.get(row.action, 0) + 1
    return dict(sorted(counts.items()))


def scrub_counts(rows: list[ResultRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.scrub_status] = counts.get(row.scrub_status, 0) + 1
    return dict(sorted(counts.items()))


def protocol_status_counts(rows: list[ResultRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.protocol_status] = counts.get(row.protocol_status, 0) + 1
    return dict(sorted(counts.items()))


def backfill_target_counts(rows: list[ResultRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if row.action != "hold_for_protocol_backfill":
            continue
        status = row.protocol_status
        if status.startswith("protocol-tagged (missing "):
            target = status.removeprefix("protocol-tagged (missing ").split(")", 1)[0]
        elif status == "evidence-linked; needs protocol tag":
            target = "protocol tag"
        elif status == "protocol marker present; needs structured protocol backfill":
            target = "structured protocol metadata"
        elif status == "unverified historical row":
            target = "verification decision"
        else:
            target = status
        counts[target] = counts.get(target, 0) + 1
    return dict(sorted(counts.items()))


def historical_attestation_review_counts(rows: list[ResultRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if row.action != HISTORICAL_ATTESTATION_REVIEW_ACTION:
            continue
        target = "historical attestation or remeasurement"
        counts[target] = counts.get(target, 0) + 1
    return dict(sorted(counts.items()))


def render_page(rows: list[ResultRow], source: Path) -> str:
    counts = action_counts(rows)
    scrub_summary = scrub_counts(rows)
    backfill_summary = backfill_target_counts(rows)
    historical_review_summary = historical_attestation_review_counts(rows)
    protocol_summary = protocol_status_counts(rows)
    lines = [
        "# Public Results Draft",
        "",
        "Status: generated draft, not publication-ready.",
        "",
        f"Source: `{display_source(source)}`.",
        "",
        "This page is generated from `RESULTS.md`. Rows without explicit protocol tags are held for backfill under `MEASUREMENT.md`; do not publish them as claims.",
        "",
        "## Summary",
        "",
        f"- Total rows: {len(rows)}",
    ]
    for action, count in counts.items():
        lines.append(f"- `{action}`: {count}")
    lines.append("")
    lines.append("### Protocol Backfill Summary")
    lines.append("")
    if backfill_summary:
        for target, count in backfill_summary.items():
            lines.append(f"- `{target}`: {count}")
    else:
        lines.append("- No protocol backfill targets.")
    lines.append("")
    lines.append("### Historical Attestation Review Summary")
    lines.append("")
    if historical_review_summary:
        for target, count in historical_review_summary.items():
            lines.append(f"- `{target}`: {count}")
    else:
        lines.append("- No historical attestation review targets.")
    lines.append("")
    lines.append("### Protocol Status Summary")
    lines.append("")
    for status, count in protocol_summary.items():
        lines.append(f"- `{status}`: {count}")
    lines.append("")
    lines.append("### Public Scrub Summary")
    lines.append("")
    for status, count in scrub_summary.items():
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Section | Entity | Quant/size | Metrics | Protocol status | Scrub status | Action | Source line |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                escape_cell(value)
                for value in (
                    row.section,
                    row.entity,
                    row.quant_or_size,
                    row.metrics,
                    row.protocol_status,
                    row.scrub_status,
                    row.action,
                    str(row.source_line),
                )
            )
            + " |"
        )
    lines.append("")
    lines.append("## Regeneration")
    lines.append("")
    lines.append("Run `python3 scripts/publication/generate_public_results.py` from `epyc-root`.")
    lines.append("The generated output is a triage surface, not a claim-certification mechanism.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_results_path())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Fail if output would change.")
    args = parser.parse_args(argv)

    source = args.input
    text = source.read_text(encoding="utf-8", errors="replace")
    rows = collect_rows(text)
    rendered = render_page(rows, source)

    if args.check:
        existing = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if existing != rendered:
            print(f"{args.output} is stale")
            return 1
        print(f"{args.output} is current ({len(rows)} rows)")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Public results draft: wrote {len(rows)} rows to {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
