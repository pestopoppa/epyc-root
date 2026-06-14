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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs" / "publication" / "public-results-draft.md"


@dataclass(frozen=True)
class ResultRow:
    section: str
    source_line: int
    entity: str
    quant_or_size: str
    metrics: str
    protocol_status: str
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
    attestation = _first_match(r"\battest(?:ation)?\s+([A-Za-z0-9._-]{3,})\b", payload)

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
                    nearby = "\n".join(lines[max(0, table_start - 4): min(len(lines), j + 4)])
                    protocol_status, action = classify_protocol(current_section, cells, nearby)
                    rows.append(
                        ResultRow(
                            section=current_section,
                            source_line=j + 1,
                            entity=pick_entity(headers, row_map),
                            quant_or_size=pick_quant_or_size(row_map),
                            metrics=metrics,
                            protocol_status=protocol_status,
                            action=action,
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


def render_page(rows: list[ResultRow], source: Path) -> str:
    counts = action_counts(rows)
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
    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Section | Entity | Quant/size | Metrics | Protocol status | Action | Source line |",
            "|---|---|---|---|---|---|---|",
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
