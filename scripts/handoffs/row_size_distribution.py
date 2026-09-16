#!/usr/bin/env python3
"""Size distribution of top-level checkbox rows in active handoffs (promote-vs-inline bands).

Definition (the one `docs/guides/agent-workflows/handoff-index-authoring.md` → *Promote or
inline?* was derived from, 2026-09-16): a row's size is the checkbox line plus its indented
continuation lines, stopping at a blank line, a heading, another checkbox, or a line indented no
deeper than the box. Index files, README.md and CURRENT-CAMPAIGN.md are excluded.

Read-only. Run: ``python3 scripts/handoffs/row_size_distribution.py [--repo PATH] [--state open]``
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_CB = re.compile(r"^(\s*)[-*]\s*\[([ xX~])\]")
_EXCLUDE = {"README.md", "CURRENT-CAMPAIGN.md"}
BANDS = ((1, 3), (4, 11), (12, 31), (32, None))


def row_sizes(text: str) -> list[tuple[str, int, int]]:
    """``[(mark, lines, indent), ...]`` for every checkbox in ``text``."""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        m = _CB.match(lines[i])
        if not m:
            i += 1
            continue
        ind, j = len(m.group(1)), i + 1
        while j < len(lines):
            ln = lines[j]
            if (not ln.strip() or _CB.match(ln) or ln.startswith("#")
                    or len(ln) - len(ln.lstrip()) <= ind):
                break
            j += 1
        out.append((m.group(2), j - i, ind))
        i = j
    return out


def _pct(values: list[int], q: float):
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))] if v else None


def measure(repo: Path, state: str = "open") -> dict:
    want = {"open": " ", "closed": "xX"}[state]
    files = [p for p in sorted((repo / "handoffs" / "active").glob("*.md"))
             if not p.name.endswith("index.md") and p.name not in _EXCLUDE]
    sizes: list[tuple[int, str]] = []
    small = 0
    for f in files:
        rows = row_sizes(f.read_text(encoding="utf-8", errors="replace"))
        small += len(rows) <= 2
        sizes += [(n, f.name) for mark, n, ind in rows if ind == 0 and mark in want]
    lens = [n for n, _ in sizes]
    bands = []
    for lo, hi in BANDS:
        sel = [s for s in sizes if s[0] >= lo and (hi is None or s[0] <= hi)]
        bands.append({"lines": f"{lo}-{hi}" if hi else f">={lo}", "rows": len(sel),
                      "handoffs": len({h for _, h in sel})})
    return {
        "state": state, "handoffs": len(files), "rows": len(lens),
        "handoffs_with_le2_checkboxes": small,
        "percentiles": {f"p{int(q * 100)}": _pct(lens, q) for q in (.5, .75, .9, .95, .99)}
        | {"max": max(lens) if lens else None},
        "bands": bands,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--state", choices=("open", "closed"), default="open")
    args = ap.parse_args()
    print(json.dumps(measure(args.repo.resolve(), args.state), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
