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
    evidence = " ".join([section, nearby, " ".join(row_cells)]).lower()
    if "p-bench" in evidence or "protocol-id" in evidence:
        return "protocol-tagged", "publish_candidate"
    if any(token in evidence for token in ("verified", "benchmarked", "sweep", "quality scored", "canonical")):
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


def render_page(rows: list[ResultRow], source: Path) -> str:
    lines = [
        "# Public Results Draft",
        "",
        "Status: generated draft, not publication-ready.",
        "",
        f"Source: `{display_source(source)}`.",
        "",
        "This page is generated from `RESULTS.md`. Rows without explicit protocol tags are held for backfill under `MEASUREMENT.md`; do not publish them as claims.",
        "",
        "| Section | Entity | Quant/size | Metrics | Protocol status | Action | Source line |",
        "|---|---|---|---|---|---|---|",
    ]
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
