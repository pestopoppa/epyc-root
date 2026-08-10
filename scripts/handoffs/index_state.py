#!/usr/bin/env python3
"""index_state.py — generate handoff-index liveness state, and enforce index hygiene.

Owning handoff: handoffs/active/master-handoff-index.md (the router itself)
Companion:      docs/guides/agent-workflows/handoff-index-authoring.md (the row contract)
Reuses:         scripts/coordination/backlog_row_check.py (box parsing + classification)

WHY THIS EXISTS. Measured on 2026-08-10 across 172 active handoffs / 8 indices:

    78 of 172 handoffs (45%) were listed in 2+ indices  ->  one fact = N edits, N drifts
     7 of 172 were listed in NO index at all            ->  invisible to every session
     0 indices carried any liveness signal              ->  "does this exist" != "is this moving"

The third one is the expensive one. An index that lists a handoff tells a reader it EXISTS.
It never tells them whether anyone has advanced it. Reconstructing that by hand — mtimes, run
artifacts under /mnt/raid0/llm/tmp, counting boxes — is where the reading time actually goes,
and it is exactly what got missed when a two-week-old 227 GB operator decision (G9-disk) sat
unnoticed in a handoff body during a disk audit.

WHAT `last_advanced` MEANS, precisely, because the obvious implementation is wrong: it is the
date of the last commit that changed a CHECKBOX line, not the file mtime and not the last
commit. mtime moves when someone rewords a paragraph; the last commit moves when someone fixes
a typo. Neither is progress. A checkbox flip is the one edit that means work changed state, so
that is what gets dated. A handoff whose prose churns weekly but whose boxes have not moved
since May is exactly the thing this column exists to expose.

DELIBERATELY NOT INFERRED: whether the work is still WANTED. Form-screening cannot see that —
`backlog_queue_gen.py` measured read-certified liveness at 47% (n=19) and 29% (n=45) on rows
that all passed form checks. So `open` counts here are an upper bound on real work, and quoting
them as a backlog size would restate that same over-count. This tool reports form and recency;
a human still certifies want.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIVE = REPO_ROOT / "handoffs" / "active"
BLOCKED = REPO_ROOT / "handoffs" / "blocked"
SIDECAR = ACTIVE / ".index-state.json"
GRAPH = ACTIVE / ".index-graph.json"
MASTER = ACTIVE / "master-handoff-index.md"

BEGIN = "<!-- BEGIN GENERATED index_state -->"
END = "<!-- END GENERATED index_state -->"

# Domain indices. The master is the router and owns no rows.
DOMAIN_INDICES = [
    "inference-research-index.md",
    "routing-and-optimization-index.md",
    "research-evaluation-index.md",
    "user-facing-harness-index.md",
    "pipeline-integration-index.md",
    "reviewer-control-plane-index.md",
]
ALL_INDICES = DOMAIN_INDICES + [MASTER.name, "CURRENT-CAMPAIGN.md"]

#: Registers, not work items: they list handoffs rather than being one.
REGISTERS = set(ALL_INDICES) | {"BLOCKED.md", "README.md"}

MAX_NEXT_ACTION = 140

_SPEC = importlib.util.spec_from_file_location(
    "brc", REPO_ROOT / "scripts" / "coordination" / "backlog_row_check.py")
brc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(brc)

# `| ID | Track | [name](link.md) | next action | deps |`
#
# Cells are split on UNESCAPED pipes. A naive `[^|]*` per cell looks right and is
# wrong: a next-action seeded from a handoff can legitimately contain `\|` (e.g.
# `--spec-type ngram-simple\|ngram-cache`), and the escape still contains the pipe
# character, so the row silently fails to match — and a row that fails to match is
# indistinguishable from a handoff with no row at all. That turns a formatting nit
# into a phantom ORPHAN, i.e. the checker would under-report coverage while looking
# green on the rows it did parse. Split, don't pattern-match a fixed cell count.
_ROW_ID = re.compile(r"^\|\s*([A-Z]{3}-\d+)\s*\|")
_SPLIT = re.compile(r"(?<!\\)\|")
_LINK = re.compile(r"\(([A-Za-z0-9._/-]+\.md)\)")


def handoff_paths() -> dict[str, Path]:
    """`{filename: path}` for every live handoff — `active/` **and** `blocked/`.

    Completed and archived are deliberately absent: this is a picture of work in
    flight, and a graph that also plots 261 finished handoffs buries the ~180 that
    still need someone.

    WHEN A STEM EXISTS IN BOTH DIRECTORIES the blocked copy wins. That is not a
    tie-break, it is the repo's own convention: `active/swarm-dataset-distillation.md`
    is a 725-byte *compatibility pointer* ("retained so older active-handoff links
    stay stable. Do not add standalone work here") whose real 17.5 KB ledger lives
    in `blocked/`. Scanning `active/` alone therefore showed that row as having
    zero open tasks while the ledger it points at had three — the pointer is
    infrastructure, like an index, not a work item.
    """
    out: dict[str, Path] = {}
    for p in sorted(ACTIVE.glob("*.md")):
        if p.name not in REGISTERS:
            out[p.name] = p
    for p in sorted(BLOCKED.glob("*.md")):
        if p.name not in REGISTERS:
            out[p.name] = p          # blocked wins over an active pointer
    return out


def handoff_files() -> list[Path]:
    return sorted(handoff_paths().values())


def last_advanced(path: Path) -> str | None:
    """Date of the most recent commit that changed a checkbox line in `path`.

    `-S'- [x]'` follows the COUNT of closed boxes, so it fires on a flip and stays
    quiet for prose edits. That is the whole point — see the module docstring.
    """
    for needle in ("- [x]", "- [ ]"):
        try:
            out = subprocess.run(
                ["git", "log", "-1", "--format=%as", "-S", needle, "--", path.name],
                cwd=path.parent, capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            return None
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    return None


def scan_handoff(path: Path) -> dict:
    """Box counts for one handoff, classified so non-tasks do not inflate `open`."""
    open_n = closed_n = guarded_n = blocked_n = 0
    for lineno, state, body, head in brc._boxes(path):
        if state == "x":
            closed_n += 1
            continue
        code, reasons = brc.classify(path, lineno, state, body, head)
        # classify() is advisory: 0 == dispatchable, non-zero == refuse with a reason.
        if code == 0:
            open_n += 1
        elif any("DO-NOT-DISPATCH" in r or "reusable checklist" in r for r in reasons):
            guarded_n += 1
        else:
            blocked_n += 1
    return {"open": open_n, "closed": closed_n,
            "guarded": guarded_n, "blocked": blocked_n,
            "total": open_n + closed_n + guarded_n + blocked_n}


def parse_index_rows(index: Path) -> list[dict]:
    """Rows in the thin schema. Files not yet migrated simply yield nothing."""
    if not index.exists():
        return []
    rows = []
    for lineno, line in enumerate(index.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not _ROW_ID.match(line):
            continue
        cells = [c.strip() for c in _SPLIT.split(line.strip())]
        # leading/trailing empties from the outer pipes
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5:
            rows.append({"id": cells[0] if cells else "?", "track": "", "index": index.name,
                         "line": lineno, "handoff": None, "next_action": "",
                         "deps": [], "malformed": len(cells)})
            continue
        rid, track, handoff_cell, action, deps = cells
        links = _LINK.findall(handoff_cell)
        rows.append({
            "id": rid, "track": track, "index": index.name, "line": lineno,
            "handoff": Path(links[0]).name if links else None,
            "next_action": action,
            "deps": [d.strip() for d in deps.replace("—", "").split(",") if d.strip()],
        })
    return rows


def collect() -> dict:
    rows = [r for i in DOMAIN_INDICES for r in parse_index_rows(ACTIVE / i)]
    owner, dupes = {}, defaultdict(list)
    for r in rows:
        if not r["handoff"]:
            continue
        dupes[r["handoff"]].append(r)
        owner.setdefault(r["handoff"], r)

    handoffs = {}
    for name, p in sorted(handoff_paths().items()):
        st = scan_handoff(p)
        row = owner.get(name)
        st["last_advanced"] = last_advanced(p)
        st["state"] = "blocked" if p.parent == BLOCKED else "active"
        st["owner_index"] = row["index"] if row else None
        st["row_id"] = row["id"] if row else None
        handoffs[name] = st

    domains = defaultdict(lambda: {"handoffs": 0, "open": 0, "blocked": 0, "oldest_advance": None})
    for name, st in handoffs.items():
        d = st["owner_index"] or "UNASSIGNED"
        agg = domains[d]
        agg["handoffs"] += 1
        agg["open"] += st["open"]
        agg["blocked"] += st["blocked"]
        la = st["last_advanced"]
        if la and (agg["oldest_advance"] is None or la < agg["oldest_advance"]):
            agg["oldest_advance"] = la

    return {"schema": "index_state.v1", "handoffs": handoffs,
            "domains": dict(domains),
            "rows": {r["id"]: r for r in rows},
            "duplicates": {h: [r["index"] for r in v] for h, v in dupes.items() if len(v) > 1}}


def render_block(state: dict) -> str:
    lines = [BEGIN,
             "| Domain | Handoffs | Open | Blocked | Oldest advance |",
             "|--------|----------|------|---------|----------------|"]
    for d in sorted(state["domains"], key=lambda k: (k == "UNASSIGNED", k)):
        a = state["domains"][d]
        label = d.replace("-index.md", "").replace(".md", "")
        lines.append(f"| {label} | {a['handoffs']} | {a['open']} | {a['blocked']} | "
                     f"{a['oldest_advance'] or '—'} |")
    lines.append(END)
    return "\n".join(lines)


def write_block(state: dict) -> bool:
    """Splice the rollup into the master index. Returns True if the file changed."""
    text = MASTER.read_text(encoding="utf-8")
    block = render_block(state)
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        new = pre + block + post
    else:
        new = text.rstrip("\n") + "\n\n## Backlog state (generated)\n\n" + block + "\n"
    if new != text:
        MASTER.write_text(new, encoding="utf-8")
        return True
    return False


def build_graph(state: dict) -> dict:
    """Node/edge view of the backlog for the dashboard's graph panel.

    Nodes are index ROWS (not handoffs) so the graph and the indices share one
    identity — an `INF-11` on the board is the `INF-11` in the file.

    TWO EDGE KINDS, deliberately never merged:

    * `dep`  — from the hand-authored `Deps` column. Semantic: "this is blocked on
      that". Few, strong, and a human wrote each one.
    * `ref`  — derived: handoff A's markdown contains a link to handoff B. Factual
      and checkable ("A cites B"), with `weight` = how many times.

    Keeping them apart is the whole point. A heuristic sweep over *blocking
    language* produced 253 candidate edges and was rejected, because the phrasing
    does not disambiguate direction ("X gates Y" vs "gated by X") and a bulk import
    would have drawn authoritative-looking arrows pointing the wrong way. A link,
    by contrast, claims nothing about dependency or ordering — only that one
    document references another — so it can be derived without inventing meaning.
    Render them differently; never let a `ref` read as a `dep`.

    The other day-one signal is the LIVENESS MAP — colour by how long since a
    checkbox moved, size by open count — which the indices never carried.
    """
    now = datetime.now(timezone.utc)
    nodes, edges = [], []
    for rid, r in sorted(state["rows"].items()):
        h = r.get("handoff")
        st = state["handoffs"].get(h, {}) if h else {}
        la = st.get("last_advanced")
        age = None
        if la:
            try:
                age = (now.date() - date.fromisoformat(la)).days
            except ValueError:
                age = None
        nodes.append({
            "id": rid,
            "domain": (r["index"] or "").replace("-index.md", ""),
            "track": r["track"],
            "handoff": h,
            # Carried into the node so a hover answers "what do I do next?" without
            # a second request. It is already the one-line contract-bounded cell.
            "next_action": r["next_action"],
            "state": st.get("state", "active"),
            "open": st.get("open", 0),
            "closed": st.get("closed", 0),
            "blocked": st.get("blocked", 0),
            "last_advanced": la,
            "age_days": age,
        })
        for dep in r["deps"]:
            edges.append({"from": rid, "to": dep, "kind": "dep"})

    # Reference edges: a link in A's markdown to B's file. Derived, but not
    # inferred — the link either exists or it does not.
    by_handoff = {n["handoff"]: n["id"] for n in nodes if n["handoff"]}
    paths = handoff_paths()
    seen: dict[tuple[str, str], int] = {}
    for handoff, src in by_handoff.items():
        path = paths.get(handoff)
        if path is None:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for target in set(_LINK.findall(text)):
            name = Path(target).name
            dst = by_handoff.get(name)
            if dst and dst != src:
                seen[(src, dst)] = text.count(name)
    for (src, dst), weight in sorted(seen.items()):
        edges.append({"from": src, "to": dst, "kind": "ref", "weight": weight})

    return {
        "schema": "index_graph.v1",
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nodes": nodes,
        "edges": edges,
        "domains": sorted({n["domain"] for n in nodes}),
        "edge_kinds": {
            "dep": "hand-authored Deps column — semantic: blocked on",
            "ref": "derived: this handoff's markdown links to that one — no dependency claim",
        },
    }


def check(state: dict) -> list[str]:
    errs = []
    paths = handoff_paths()

    for h, idxs in sorted(state["duplicates"].items()):
        errs.append(f"DUPLICATE: {h} has rows in {len(idxs)} indices: {', '.join(sorted(set(idxs)))}")

    orphans = sorted(h for h, st in state["handoffs"].items() if not st["owner_index"])
    for h in orphans:
        errs.append(f"ORPHAN: {h} has no index row (invisible to dispatch)")

    for rid, r in sorted(state["rows"].items()):
        if r.get("malformed"):
            errs.append(f"SCHEMA: row {rid} ({r['index']}:{r['line']}) has {r['malformed']} cells, "
                        f"expected 5 — an unescaped pipe in a cell will do this")
        elif not r["handoff"]:
            errs.append(f"SCHEMA: row {rid} ({r['index']}:{r['line']}) has no handoff link")
        elif r["handoff"] not in paths:
            errs.append(f"DEAD LINK: row {rid} -> {r['handoff']} is in neither "
                        f"handoffs/active/ nor handoffs/blocked/")
        if len(r["next_action"]) > MAX_NEXT_ACTION:
            errs.append(f"PROSE: row {rid} next-action is {len(r['next_action'])} chars "
                        f"(max {MAX_NEXT_ACTION}) — status belongs in the handoff, not the index")
        for d in r["deps"]:
            if d not in state["rows"]:
                errs.append(f"BAD DEP: row {rid} depends on unknown id {d}")

    if MASTER.exists():
        text = MASTER.read_text(encoding="utf-8")
        if BEGIN not in text:
            errs.append("FRESHNESS: master index has no generated block — run without --check")
        elif render_block(state) not in text:
            errs.append("FRESHNESS: master index generated block is stale — run without --check")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="verify coverage/schema/freshness; write nothing; non-zero on failure")
    ap.add_argument("--summary", action="store_true", help="print the domain rollup and exit")
    ap.add_argument("--json", action="store_true", help="dump full state to stdout")
    args = ap.parse_args(argv)

    state = collect()

    if args.json:
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0

    if args.summary:
        print(render_block(state))
        n = len(state["handoffs"])
        assigned = sum(1 for s in state["handoffs"].values() if s["owner_index"])
        print(f"\n{assigned}/{n} handoffs owned · {len(state['duplicates'])} duplicated · "
              f"{n - assigned} orphaned")
        return 0

    if args.check:
        errs = check(state)
        for e in errs:
            print(e)
        print(f"\n{len(errs)} problem(s)")
        return 1 if errs else 0

    SIDECAR.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    graph = build_graph(state)
    GRAPH.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    changed = write_block(state)
    print(f"wrote {SIDECAR.relative_to(REPO_ROOT)}")
    print(f"wrote {GRAPH.relative_to(REPO_ROOT)} "
          f"({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")
    print(f"master index block: {'updated' if changed else 'unchanged'}")
    print(render_block(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
