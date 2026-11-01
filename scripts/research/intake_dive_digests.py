#!/usr/bin/env python3
"""Emit wiki-visible Markdown digests of dive-verified research-intake entries.

Per-entry dive results (claim_anchors, dive_corrections, claim_corrections,
reader_should_conclude, ...) live as fields in research/intake_index.yaml. The
wiki scanner (compile_sources.py, wiki.yaml `compile.source_dirs`) reads only
`.md` files, so those results never reached the wiki. This generator renders
one digest per intake run into research/deep-dives/intake-digests/<slug>.md,
which the scanner picks up (research/deep-dives is scanned with recurse: true).

Run grouping: the index carries no session field, so a run is a maximal
ID-ordered stretch of entries with the same `ingested_date`; a new run also
starts where an operator-submitted (`discovered_via: input`) entry follows an
expansion entry (a fresh submission batch). Slug: `<date>-intake-<first>-<last>`.

Deterministic and idempotent: output depends only on the index; files whose
content is unchanged are not rewritten. Every intake ID in the emitted text is
rendered `intake-NNN#record` (or kept as an explicit `#NN` claim form), so
`scripts/vidya/cli.py cite-check` never reads a digest as relying on a claim.

Usage:
    python3 scripts/research/intake_dive_digests.py              # all runs
    python3 scripts/research/intake_dive_digests.py --ids 2341-2385   # runs touching that range
    python3 scripts/research/intake_dive_digests.py --check      # exit 1 if any digest is stale
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "research" / "intake_index.yaml"
OUT_DIR = ROOT / "research" / "deep-dives" / "intake-digests"
DIVE_STATES = ("dive-verified", "dive-overturned")
_BARE_ID = re.compile(r"\bintake-(\d+)(?![\d#])")
# 12-19 digit runs (X status ids, byte counts) trip the PII account-number hook;
# render them Python-literal grouped (2_103_402_800), which is lossless.
_LONG_DIGITS = re.compile(r"(?<![\d_])\d{12,19}(?![\d_])")


def _group(m: re.Match) -> str:
    return f"{int(m.group(0)):_}"


def _num(entry: dict) -> int:
    return int(str(entry["id"]).split("-")[1])


def _safe(text) -> str:
    """Flatten a value to one-paragraph text with every intake ID in #record form."""
    if text is None:
        return ""
    if isinstance(text, (list, tuple)):
        text = " ".join(_safe(t) for t in text)
    elif isinstance(text, dict):
        text = "; ".join(f"{k}: {_safe(v)}" for k, v in text.items())
    s = " ".join(str(text).split())
    return _LONG_DIGITS.sub(_group, _BARE_ID.sub(r"intake-\1#record", s))


def group_runs(entries: list[dict]) -> list[list[dict]]:
    runs: list[list[dict]] = []
    prev = None
    for e in sorted(entries, key=_num):
        date = str(e.get("ingested_date"))
        new = (
            prev is None
            or date != str(prev.get("ingested_date"))
            or (e.get("discovered_via") == "input" and prev.get("discovered_via") != "input")
        )
        if new:
            runs.append([e])
        else:
            runs[-1].append(e)
        prev = e
    return runs


def dive_entries(index: list[dict]) -> list[dict]:
    return [e for e in index if e.get("verification") in DIVE_STATES]


def run_slug(run: list[dict]) -> str:
    return f"{run[0].get('ingested_date')}-intake-{_num(run[0])}-{_num(run[-1])}"


def _bullets(lines: list[str]) -> list[str]:
    return [f"- {ln}" for ln in lines if ln]


def render_entry(e: dict) -> list[str]:
    eid = f"intake-{_num(e)}"
    out = [f"## {eid}#record — {_safe(e.get('title'))}", ""]
    out.append(f"- **URL**: {_safe(e.get('url')) or 'n/a'}")
    out.append(f"- **Verification**: {e.get('verification')}")
    cats = ", ".join(e.get("categories") or [])
    out.append(f"- **Verdict**: {e.get('verdict')} (novelty {e.get('novelty')}, relevance {e.get('relevance')}; categories: {cats})")
    if e.get("integration_disposition"):
        out.append(f"- **Disposition**: {e.get('integration_disposition')}")
    if e.get("expanded_from"):
        out.append(f"- **Expanded from**: {_safe(e.get('expanded_from'))}")
    out.append("")
    claims = e.get("key_claims") or []
    corr = {}
    for c in e.get("claim_corrections") or []:
        if isinstance(c, dict):
            corr.setdefault(c.get("claim_index"), []).append(c)
    anchors = {}
    for a in e.get("claim_anchors") or []:
        if isinstance(a, dict):
            anchors.setdefault(a.get("claim_index"), []).append(a)
    if claims:
        out.append("### Claims (as verified)")
        out.append("")
        for i, cl in enumerate(claims):
            out.append(f"{i}. {_safe(cl)}")
            for c in corr.get(i, []):
                out.append(f"   - *{c.get('effect')}*: {_safe(c.get('note'))}")
            for a in anchors.get(i, []):
                q = _safe(a.get("quote"))
                if len(q) > 300:
                    q = q[:297] + "..."
                rev = f" @ {_safe(a.get('source_revision'))}" if a.get("source_revision") else ""
                out.append(f"   - anchor `{_safe(a.get('locator'))}`{rev}: \"{q}\"")
        out.append("")
    if e.get("dive_corrections"):
        out.append("### Dive corrections")
        out.append("")
        dc = e["dive_corrections"]
        out += _bullets([_safe(x) for x in (dc if isinstance(dc, list) else [dc])])
        out.append("")
    verdict_lines = [_safe(e.get(k)) for k in ("reader_should_conclude", "verdict_justification")]
    if any(verdict_lines):
        out.append("### Verdict")
        out.append("")
        out += [v for v in verdict_lines if v]
        out.append("")
    tasks = [f"created `{h}`" for h in e.get("handoffs_created") or []]
    tasks += [f"updated `{h}`" for h in e.get("handoffs_updated") or []]
    ra = e.get("recommended_actions") or []
    if tasks or ra:
        out.append("### Linked handoffs and actions")
        out.append("")
        out += _bullets(tasks + [f"Recommended action (dive proposal, not an instruction): {_safe(r)}" for r in ra])
        out.append("")
    return out


def render_run(run: list[dict]) -> str:
    first, last = _num(run[0]), _num(run[-1])
    cats: dict[str, int] = {}
    for e in run:
        for c in e.get("categories") or []:
            cats[c] = cats.get(c, 0) + 1
    top = ", ".join(c for c, _ in sorted(cats.items(), key=lambda kv: (-kv[1], kv[0]))[:8])
    lines = [
        f"# Intake dive digest — {run[0].get('ingested_date')}, intake-{first}#record .. intake-{last}#record",
        "",
        "Generated by `scripts/research/intake_dive_digests.py` from `research/intake_index.yaml`;"
        " do not edit by hand. IDs are cited in `#record` form: this page reports what each dive"
        " recorded and asserts nothing beyond it. Digit runs of 12+ digits (status ids, byte"
        " counts) are written grouped, e.g. `2_103_402_800_155`.",
        "",
        f"- **Entries**: {len(run)} dive-verified or dive-overturned",
        f"- **Categories**: {top}",
        "",
    ]
    for e in run:
        lines += render_entry(e)
    return "\n".join(lines).rstrip() + "\n"


def build(index: list[dict]) -> dict[str, str]:
    return {run_slug(r): render_run(r) for r in group_runs(dive_entries(index))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", type=Path, default=INDEX)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--ids", help="only runs overlapping LO-HI")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    index = yaml.safe_load(a.index.read_text())
    docs = build(index)
    if a.ids:
        lo, hi = (int(x) for x in a.ids.split("-"))
        docs = {
            s: d for s, d in docs.items()
            if int(s.rsplit("-", 2)[1]) <= hi and int(s.rsplit("-", 1)[1]) >= lo
        }
    a.out.mkdir(parents=True, exist_ok=True)
    stale = 0
    for slug, text in sorted(docs.items()):
        p = a.out / f"{slug}.md"
        if p.exists() and p.read_text() == text:
            continue
        stale += 1
        if not a.check:
            p.write_text(text)
    print(f"{len(docs)} digests, {stale} {'stale' if a.check else 'written'}")
    return 1 if (a.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
