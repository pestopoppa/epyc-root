"""SC5: wiki pages as DEPENDENTS of intake claims — never as claims of their own.

A wiki page is compiled *from* sources the index already holds. Ingesting it as a claim would count
one source twice: the paper would support its own intake claim, and then the wiki page's restatement
of that paper would support a second claim, and a naive support count would read two independent
witnesses where there is one paper. That is precisely the double-counting the locator-keyed support
fix exists to prevent, so the operator's ruling (2026-08-11) was that wiki pages become dependency
edges, not beliefs.

**Nothing here is written to the ledger, and that is the design, not a shortcut.** The ledger records
observations that cannot be re-derived. A wiki page's citations can: they are in the file, the file
is in git, and the edge is recomputable at any `as_of` by reading it. Appending them would mean
either inventing a source-level edge frame or minting one structural "claim" per page — and that
second option would put 28 things in the belief set that are not beliefs, which is the category
error this substrate exists to catch. So the edges live here, as a projection over the fold.

What the projection answers: **when an intake claim decays, which compiled pages are now stale?**
A page is flagged when an entry it cites has lost all support, carries an unreviewed correction, or
resolves to nothing at all.

Merged ids are resolved forward. The wiki cites ids written before this session's dedup, and a
merged id resolves to *nothing* rather than to the wrong paper — deliberately, since renumbering
was refused for exactly that reason. `merged_ids` on the surviving entry makes it recoverable, and
an id that reaches neither an entry nor the merge map is reported as dangling rather than dropped.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "wiki"
INDEX = REPO / "research" / "intake_index.yaml"

# The `#NN` suffix is the PRECISE citation form (`intake-896#03` = claim 3 of that entry). It is
# optional and rare today, and `citation_gate` exists partly to make it worth writing: an entry-level
# citation inherits every defect of every claim in the entry, so precision is what buys a clean gate.
_CITE = re.compile(r"\bintake-(\d+)(?:#(\d+))?\b")
# `intake-710/711` is one citation naming two entries. Reading only the first silently halves the
# graph, which would understate staleness -- the direction that hides problems.
#
# The `(?!\.\d)` guard is load-bearing and was added 2026-08-10 after `citation_gate` reported a
# dangling citation to `intake-2602`, an entry that does not exist. The source text was
# `(intake-374/378/2602.11149 synthesis)` -- a two-entry run followed by an arXiv id -- and the
# unguarded run pattern ate `/2602` out of `2602.11149`. A run member followed by `.<digit>` is the
# head of an arXiv identifier, never an entry number.
# The `\b` before the lookahead stops the engine backtracking into a PARTIAL number: without it,
# `/2602.11149` fails on `2602` and then happily matches `260`, inventing a different bogus entry.
_RUN = re.compile(r"\bintake-(\d+)((?:/\d+\b(?!\.\d))+)")


def source_id(num: str) -> str:
    return f"src_intake_{int(num):03d}"


def cited_refs(text: str) -> set[tuple[str, int | None]]:
    """Every citation a document makes, as `(entry number, claim index or None)`.

    ONE scanner for the whole program. `cited_ids` is a projection of this, and `citation_gate`
    reads it directly rather than writing a second regex -- the two-graders defect of 2026-08-10
    started exactly that way, with a rule reimplemented next to its original.

    A claim index on the run form (`intake-710/711#02`) is ambiguous about which entry it indexes,
    so the run members are recorded at entry granularity and the index is dropped rather than
    guessed at.
    """
    refs: set[tuple[str, int | None]] = set()
    run_members: set[str] = set()
    for m in _RUN.finditer(text):
        run_members.add(m.group(1))
        run_members.update(part for part in m.group(2).split("/") if part)
    for m in _CITE.finditer(text):
        num = str(int(m.group(1)))
        if num in {str(int(n)) for n in run_members}:
            continue
        refs.add((num, int(m.group(2)) if m.group(2) else None))
    refs.update((str(int(n)), None) for n in run_members if n)
    return refs


def cited_ids(text: str) -> set[str]:
    """Every intake number a page names, including the `intake-710/711` run form."""
    return {num for num, _ in cited_refs(text)}


def scan_wiki(root: Path = WIKI) -> dict[str, set[str]]:
    """page path -> intake numbers it cites."""
    pages: dict[str, set[str]] = {}
    for page in sorted(root.glob("*.md")):
        ids = cited_ids(page.read_text(encoding="utf-8", errors="ignore"))
        if ids:
            pages[str(page.relative_to(REPO))] = ids
    return pages


def merge_redirects() -> dict[str, str]:
    """absorbed id -> surviving id, read from `merged_ids` on the survivor.

    Parsed as TEXT. `intake_index.yaml` is never round-tripped through safe_load/safe_dump in this
    program -- a load/dump cycle reorders keys and reflows every string in a 1,068-entry file,
    producing a diff nobody can review.
    """
    redirects: dict[str, str] = {}
    current: str | None = None
    in_merged = False
    for raw in INDEX.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^- id:\s*intake-(\d+)", raw) or re.match(r"^\s*- id:\s*intake-(\d+)", raw)
        if m:
            current = str(int(m.group(1)))
            in_merged = False
            continue
        if re.match(r"^\s*merged_ids:\s*$", raw):
            in_merged = True
            continue
        if in_merged:
            item = re.match(r"^\s*-\s*(?:intake-)?(\d+)\s*$", raw)
            if item and current:
                redirects[str(int(item.group(1)))] = current
                continue
            if raw.strip() and not raw.lstrip().startswith("#"):
                in_merged = False
    return redirects


def live_entry_ids() -> set[str]:
    ids = set()
    for raw in INDEX.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*- id:\s*intake-(\d+)", raw)
        if m:
            ids.add(str(int(m.group(1))))
    return ids


def resolve(num: str, redirects: dict[str, str], live: set[str]) -> tuple[str | None, str]:
    """Return (resolved id, how). `how` is one of direct / merged / dangling."""
    if num in live:
        return num, "direct"
    seen = set()
    cur = num
    while cur in redirects and cur not in seen:
        seen.add(cur)
        cur = redirects[cur]
        if cur in live:
            return cur, "merged"
    return None, "dangling"


def stale_sources(fold_result) -> tuple[set[str], set[str], dict[str, list[str]]]:
    """Return (sources present in the ledger, sources with surviving support, corrected claims).

    `present` is separate from `supported` on purpose. An entry with no claims in the ledger at all
    is a COVERAGE GAP; an entry whose claims have all fallen to Q0 is DECAY. Reporting both as
    "lost all support" reads as rot where there was never anything to rot -- the first draft of this
    function did exactly that, and flagged intake-12 and intake-335 as decayed when neither has ever
    had a claim ingested.
    """
    present: set[str] = set()
    supported: set[str] = set()
    flagged: dict[str, list[str]] = defaultdict(list)
    for claim_id, belief in fold_result.beliefs.items():
        src = getattr(belief, "source_id", None) or ""
        if not src:
            m = re.match(r"clm_intake_(\d+)_", claim_id)
            src = source_id(m.group(1)) if m else ""
        if not src:
            continue
        present.add(src)
        if belief.pro.q_name != "Q0":
            supported.add(src)
        if getattr(belief, "needs_review", False) or belief.corrections:
            flagged[src].append(claim_id)
    return present, supported, dict(flagged)


def report(fold_result) -> dict:
    pages = scan_wiki()
    redirects = merge_redirects()
    live = live_entry_ids()
    present, supported, flagged = stale_sources(fold_result)

    rows = []
    for page, nums in sorted(pages.items()):
        dangling, uningested, unsupported, corrected, ok, merged = [], [], [], [], [], []
        for num in sorted(nums, key=int):
            resolved, how = resolve(num, redirects, live)
            if resolved is None:
                dangling.append(num)
                continue
            if how == "merged":
                merged.append(f"{num}->{resolved}")
            sid = source_id(resolved)
            if sid in flagged:
                corrected.append(resolved)
            elif sid not in present:
                uningested.append(resolved)
            elif sid not in supported:
                unsupported.append(resolved)
            else:
                ok.append(resolved)
        rows.append({
            "page": page, "cited": len(nums), "ok": len(ok),
            "merged": merged, "dangling": dangling, "uningested": uningested,
            "unsupported": unsupported, "corrected": corrected,
            # Only DECAY makes a page stale. An uningested entry says the substrate has not read
            # that paper yet -- a gap in us, not a defect in the page.
            "stale": bool(dangling or unsupported or corrected),
        })
    return {
        "pages": len(pages),
        "edges": sum(len(v) for v in pages.values()),
        "stale_pages": sum(1 for r in rows if r["stale"]),
        "uningested_edges": sum(len(r["uningested"]) for r in rows),
        "rows": rows,
    }


def main() -> int:
    from fold import fold
    from ledger import Ledger

    frames = [r.frame for r in Ledger(str(REPO / ".vidya" / "ledger.jsonl")).read_all()]
    res = fold(frames, as_of="2026-08-10T16:00:00Z")
    rep = report(res)

    print(f"wiki pages citing intake entries : {rep['pages']}")
    print(f"dependency edges                 : {rep['edges']}")
    print(f"pages with a stale dependency    : {rep['stale_pages']}")
    print(f"edges into never-ingested entries: {rep['uningested_edges']}  (coverage gap, not decay)")
    print()
    for row in rep["rows"]:
        if not row["stale"]:
            continue
        print(f"  {row['page']}  ({row['cited']} cited)")
        for key, label in (("dangling", "resolves to nothing"),
                           ("unsupported", "entry has lost all support (decay)"),
                           ("corrected", "entry carries an unreviewed correction")):
            if row[key]:
                shown = ", ".join(str(x) for x in row[key][:8])
                more = f" (+{len(row[key]) - 8})" if len(row[key]) > 8 else ""
                print(f"     {label}: {shown}{more}")
    merged_total = sum(len(r["merged"]) for r in rep["rows"])
    if merged_total:
        print(f"\n{merged_total} citation(s) resolved forward through the merge map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
