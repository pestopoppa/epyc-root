#!/usr/bin/env python3
"""taskflow/extract.py — the prompt payload for ONE selected box (DESIGN.md §2.2; handoff standard Stage C, C8).

Deterministic, no LLM, read-only. Input: a `.box-index.json` record (taskflow/select.py output). Output: the box's OWN
block verbatim (exact bytes: the identity; first line hashed as `text_sha` and re-checked here), its heading chain
(`# title > ## Track > ### Backlog`), the 20 lines above it, the parsed fields (class, done when, gate, inputs, tier),
holds, row and rank, and `file:LINE` as a HINT only. A record whose live first line no longer hashes to its
`text_sha` (the file moved on since the index was built) is located again by text_sha in the same file, else by the
moves log (`handoff_ref.moved_file`), else refused -- never dispatched from a stale line number.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTEXT_LINES = 20


def _mods(root: Path):
    sys.path.insert(0, str(root / "scripts" / "handoffs"))
    sys.path.insert(0, str(root / "scripts" / "coordination"))
    import box_index as BI
    import handoff_ref as HR
    import task_lint_core as L1
    return BI, HR, L1


def locate(rec: dict, root: Path) -> tuple[Path, int] | None:
    """(file, 0-based line) of the record's box by IDENTITY: the hinted line if it still hashes to text_sha, else a
    text_sha scan of the file, else the moves log; None when the box is gone."""
    BI, HR, L1 = _mods(root)
    p = root / rec["file"]
    for cand in (p, root / "handoffs" / "active" / str(HR.moved_file(Path(rec["file"]).name, root, rec.get("text_sha"))
                                                        or "")):
        if not cand.is_file():
            continue
        lines = cand.read_text(encoding="utf-8", errors="replace").split("\n")
        h = int(rec.get("line") or 0) - 1
        if cand == p and 0 <= h < len(lines) and L1.CHECKBOX.match(lines[h]) and BI.text_sha(lines[h]) == rec["text_sha"]:
            return cand, h
        for i, l in enumerate(lines):
            if L1.CHECKBOX.match(l) and BI.text_sha(l) == rec["text_sha"]:
                return cand, i
    return None


def heading_chain(lines: list[str], i: int) -> list[str]:
    chain: dict[int, str] = {}
    for line in lines[:i]:
        m = re.match(r"^(#{1,3})\s+(.*\S)\s*$", line)
        if m:
            lvl = len(m.group(1))
            chain = {k: v for k, v in chain.items() if k < lvl}
            chain[lvl] = m.group(2)
    return [chain[k] for k in sorted(chain)]


def extract(rec: dict, root: Path | None = None) -> dict:
    root = root or REPO_ROOT
    BI, HR, L1 = _mods(root)
    loc = locate(rec, root)
    if loc is None:
        raise LookupError(f"box {rec.get('id') or rec.get('text_sha')} not found by identity (moved or edited)")
    path, i = loc
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    own, _ = L1.own_block(lines, i)
    return {"box_text": own, "text_sha": rec["text_sha"], "id": rec.get("id"),
            "heading_chain": heading_chain(lines, i), "context_above": "\n".join(lines[max(0, i - CONTEXT_LINES):i]),
            "fields": {k: rec.get(k) for k in ("class", "done_when", "gate", "inputs", "tier", "owner")},
            "holds": rec.get("holds") or [], "row": rec.get("row"), "row_rank": rec.get("row_rank"),
            "hint": f"{path.relative_to(root)}:{i + 1}"}


def main(argv=None) -> int:
    from taskflow import select as S
    doc = S.load_index()
    nxt, _ = S.select(doc)
    if not nxt:
        print("no dispatchable box")
        return 1
    print(json.dumps(extract(nxt[1]), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "coordination"))
    sys.exit(main())
