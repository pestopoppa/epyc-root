"""Candidate generation for cross-entry claim identity (R4b-authoring).

Spec: docs/design/vidya-pilot-spec.md §3 (claim_alias frame); the measurement that motivates it is
in research/deep-dives/vidya-r4-r5-corroboration-and-decay.md §R4.

R4 measured 100% of beliefs fragile because claim ids are minted per entry: two sources citing the
same fact produce two different claims, so `disjoint_supports >= 2` is unsatisfiable by
construction. The `claim_alias` frame fixes that, and the fold already applies it -- but only for
aliases somebody wrote down, and nobody was going to hand-scan 4,191 claims for 8.8M pairs.

**This module does not decide anything.** It proposes. The judgment that two differently-worded
claims denote the same proposition is exactly what the spec keeps out of the deterministic fold,
so the output here is a review worksheet with every row `pending`, and only a human flipping a row
to `same` produces a frame. The generator's job is to make that human's job small and ranked
rather than impossible: recall over precision, with a cheap reject.

Two properties are load-bearing and both are enforced by tests:

* **Same-entry pairs are never proposed.** Two claims from one entry are two claims that entry
  makes; aliasing them would fabricate corroboration out of a single source, which is the precise
  failure the corroboration statistic exists to detect. This is the one hard filter.
* **Scoring is deterministic.** No model call, no randomness, no dict-ordering dependence -- the
  same index produces the same worksheet, so a review can be resumed or audited later.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Iterable

__all__ = [
    "normalize_terms",
    "generate_candidates",
    "worksheet_from_candidates",
    "aliases_from_worksheet",
    "WorksheetError",
]

FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"

# Deliberately small. A long curated stopword list is a tuning knob that silently changes recall
# between runs; these are the terms that appear in the majority of research-claim prose and carry
# no discriminating power anywhere in this corpus.
_STOPWORDS = frozenset("""
a an the and or but of to in on for with by from as at is are was were be been being it its this
that these those we they our their can could may might will would should must not no than then
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._+-]*")

# A term shared by a large fraction of the corpus is not evidence of shared subject matter; it is
# vocabulary. Blocking on rare terms only is also what keeps this O(corpus) instead of O(n^2):
# without it, 4,191 claims is 8.8M pairs, nearly all of them "both mention 'model'".
_MAX_DOCUMENT_FRACTION = 0.05
_MIN_SHARED_TERMS = 2


class WorksheetError(ValueError):
    """A review worksheet is malformed or carries an unrecognized decision."""


def normalize_terms(text: str) -> frozenset[str]:
    """Lowercase, tokenize, drop stopwords.

    Weaker than `canonical.normalized_quote` on purpose, and in the opposite direction: that
    function must not change meaning because it feeds an anchor hash, while this one only feeds a
    *suggestion* a human will read in full. Over-normalizing here costs a false candidate the
    reviewer rejects in a second; under-normalizing there would silently match two different
    quotations.
    """
    return frozenset(t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS)


def _claims_from_frames(frames: Iterable[dict]) -> dict[str, dict]:
    """Claim id -> {text, terms, source_id, entry}. Last frame wins on a repeated id."""
    out: dict[str, dict] = {}
    for frame in frames:
        if frame.get("frame_type") != FT_CLAIM:
            continue
        assertion = frame.get("assertion") or {}
        cid = assertion.get("claim_id")
        text = assertion.get("display_text")
        if not isinstance(cid, str) or not isinstance(text, str) or not text.strip():
            continue
        out[cid] = {
            "claim_id": cid,
            "text": text,
            "terms": normalize_terms(text),
            "source_id": assertion.get("source_id") or "",
            "entry": _entry_of(cid),
        }
    return out


def _entry_of(claim_id: str) -> str:
    """Entry a claim belongs to, from the adapter's `clm_<entry>_<nn>` id shape.

    Falls back to the whole id, which makes an unrecognized id its own entry -- so the same-entry
    filter fails *closed* (proposes nothing) rather than open (proposes everything) on ids this
    module was not built for.
    """
    m = re.match(r"^(clm_.+)_(\d+)$", claim_id)
    return m.group(1) if m else claim_id


def _index_entry_of(claim_id: str) -> str:
    """`clm_intake_374_03` -> `intake-374`. Empty for ids this module was not built for."""
    m = re.match(r"^clm_intake_(\d+)_\d+$", claim_id)
    return f"intake-{m.group(1)}" if m else ""


def _score(a: dict, b: dict, idf: dict[str, float]) -> tuple[float, list[str]]:
    """IDF-weighted Jaccard over normalized terms, in [0, 1].

    Weighted rather than plain because two claims sharing "gfp" and "specialization" are a far
    better candidate than two sharing "results" and "improvement", and a plain Jaccard cannot tell
    those apart. Returned alongside the shared terms so the worksheet can show the reviewer *why*
    a pair was proposed -- an unexplained ranked list is one the reviewer has to re-derive.
    """
    shared = a["terms"] & b["terms"]
    if not shared:
        return 0.0, []
    union = a["terms"] | b["terms"]
    num = sum(idf.get(t, 0.0) for t in shared)
    den = sum(idf.get(t, 0.0) for t in union)
    score = num / den if den else 0.0
    top = sorted(shared, key=lambda t: (-idf.get(t, 0.0), t))[:6]
    return score, top


def locator_map(index_entries: Iterable[dict]) -> dict[str, str]:
    """Entry id -> a locator key shared by every entry pointing at the same underlying source.

    Needed because `source_id` in the ledger is minted per *entry* (`src_intake_418`), which is the
    same structural defect as per-entry claim ids one level up: two entries for one arXiv paper get
    two source ids, so aliasing their claims would read as two independent supports. The alias
    generator found a live instance on its first run (intake-418 and intake-797 are both
    arXiv:2604.08224), which is why this exists rather than trusting `source_id`.
    """
    out: dict[str, str] = {}
    for entry in index_entries:
        eid = entry.get("id")
        if not isinstance(eid, str):
            continue
        arxiv = entry.get("arxiv_id")
        url = entry.get("url")
        if isinstance(arxiv, str) and arxiv.strip():
            out[eid] = f"arxiv:{_bare_arxiv(arxiv)}"
            continue
        if isinstance(url, str) and url.strip():
            # An arXiv URL and a bare arXiv id are the same source. Folding them to one key is
            # what makes the duplicate detectable: the first version of this function keyed them
            # separately and missed intake-418 / intake-797, which are the same paper recorded
            # once with `arxiv_id` and once with only a URL.
            m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9v.]+)", url, re.I)
            out[eid] = f"arxiv:{_bare_arxiv(m.group(1))}" if m else f"url:{_norm_url(url)}"
    return out


def _bare_arxiv(value: str) -> str:
    """`2604.08224v2` / ` 2604.08224 ` -> `2604.08224`. Versions are the same paper."""
    return re.sub(r"v\d+$", "", value.strip().lower().removesuffix(".pdf"))


def _norm_url(url: str) -> str:
    u = url.strip().lower().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def _locator_of(claim_id: str, locators: dict[str, str]) -> str:
    """Locator key for a claim, via its entry id. Empty when unknown -- never a guess."""
    entry = _entry_of(claim_id)
    # claim ids carry the entry with underscores: clm_intake_418_04 -> intake-418
    m = re.match(r"^clm_intake_(\d+)$", entry)
    return locators.get(f"intake-{m.group(1)}", "") if m else ""


def generate_candidates(
    frames: Iterable[dict],
    *,
    min_score: float = 0.35,
    limit: int = 200,
    locators: dict[str, str] | None = None,
    citations: dict[str, set] | None = None,
) -> dict[str, Any]:
    """Rank cross-entry claim pairs that may denote the same proposition.

    Returns a report with the candidates and the corpus statistics behind them. The statistics are
    not decoration: a run that proposes 4 candidates from 4,191 claims and a run that proposes 4
    from 40 mean opposite things, and the second number is the one that tells a reader which
    happened.
    """
    claims = _claims_from_frames(frames)
    n = len(claims)
    if n < 2:
        return {
            "claims_considered": n,
            "pairs_scored": 0,
            "candidates": [],
            "min_score": min_score,
            "note": "fewer than two claims carry display text; nothing to compare",
        }

    postings: dict[str, list[str]] = defaultdict(list)
    for cid, rec in claims.items():
        for term in rec["terms"]:
            postings[term].append(cid)

    max_df = max(2, int(n * _MAX_DOCUMENT_FRACTION))
    # Smoothed so a term present in EVERY claim still weighs something. Plain log(n/df) is exactly
    # zero at df == n, which silently scores a two-claim corpus at 0/0 -- fine on 4,191 claims,
    # wrong on the small inputs that tests and first-run trials actually use.
    idf = {t: math.log(1 + n / len(p)) for t, p in postings.items()}

    # Blocking: only pairs co-occurring in at least _MIN_SHARED_TERMS *rare* term postings are
    # scored at all. Everything else is rejected without a comparison.
    shared_counts: dict[tuple[str, str], int] = defaultdict(int)
    for term, plist in postings.items():
        if len(plist) < 2 or len(plist) > max_df:
            continue
        ordered = sorted(plist)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                if claims[a]["entry"] == claims[b]["entry"]:
                    continue  # hard filter: never alias within one entry
                shared_counts[(a, b)] += 1

    scored: list[dict] = []
    pairs_scored = 0
    for (a, b), count in shared_counts.items():
        if count < _MIN_SHARED_TERMS:
            continue
        pairs_scored += 1
        score, top = _score(claims[a], claims[b], idf)
        if score < min_score:
            continue
        loc_a = _locator_of(a, locators or {})
        loc_b = _locator_of(b, locators or {})
        ent_a, ent_b = _index_entry_of(a), _index_entry_of(b)
        cites = citations or {}
        linked = bool(
            ent_a and ent_b
            and (ent_b in cites.get(ent_a, ()) or ent_a in cites.get(ent_b, ()))
        )
        scored.append(
            {
                "claim_a": a,
                "claim_b": b,
                "score": round(score, 4),
                "shared_terms": top,
                "text_a": claims[a]["text"],
                "text_b": claims[b]["text"],
                "source_a": claims[a]["source_id"],
                "source_b": claims[b]["source_id"],
                # An alias between two claims of the SAME source is a correct identity statement
                # and NOT corroboration -- the point of the statistic is independent support, and
                # two entries for one paper are one source wearing two ids. Surfaced on the row
                # because the reviewer is the only party who can tell "duplicate entry" from
                # "two papers by one group", and because approving these silently would
                # manufacture exactly the fake independence R4 exists to measure.
                "same_source": bool(loc_a and loc_a == loc_b),
                # One entry cites the other, so one is plausibly DERIVED from the other
                # -- a dataset card restating its own paper, a homepage restating its own
                # preprint. `same_source` cannot see this, because the locators genuinely
                # differ; the distinction matters for the same reason it does there.
                # Identity is correct, independence is not.
                "linked": linked,
                "locator_a": loc_a,
                "locator_b": loc_b,
            }
        )

    scored.sort(key=lambda c: (-c["score"], c["claim_a"], c["claim_b"]))
    return {
        "claims_considered": n,
        "blocked_pairs": len(shared_counts),
        "pairs_scored": pairs_scored,
        "candidates_above_threshold": len(scored),
        "candidates": scored[:limit],
        "min_score": min_score,
        "max_document_frequency": max_df,
    }


def worksheet_from_candidates(report: dict, *, generated_at: str) -> dict:
    """Turn a candidate report into a review worksheet with every decision `pending`.

    `pending` is the only legal initial value, and `aliases_from_worksheet` emits nothing for it.
    A generator that pre-filled `same` above some score would be the fold making the judgment with
    extra steps.
    """
    rows = []
    for c in report.get("candidates", []):
        rows.append(
            {
                "claim_a": c["claim_a"],
                "claim_b": c["claim_b"],
                "score": c["score"],
                "shared_terms": list(c["shared_terms"]),
                "same_source": c.get("same_source", False),
                "linked": c.get("linked", False),
                "text_a": c["text_a"],
                "text_b": c["text_b"],
                "decision": "pending",  # pending | same | different
                "reviewer": "",
                "note": "",
            }
        )
    return {
        "schema": "epyc.vidya/alias-worksheet/v1",
        "generated_at": generated_at,
        "generator": "vidya.alias_candidates/generate_candidates",
        "min_score": report.get("min_score"),
        "claims_considered": report.get("claims_considered"),
        "candidates_above_threshold": report.get("candidates_above_threshold"),
        "instructions": (
            "Set decision to 'same' only if the two texts assert the same proposition about the "
            "same subject -- not merely the same topic. Set 'different' otherwise; leave 'pending' "
            "if you did not look. Fill 'reviewer'. Only 'same' rows become claim_alias frames. "
            "A row with same_source: true is two entries for ONE source -- aliasing it is a "
            "correct identity statement but it is NOT corroboration, and it usually means the "
            "index carries a duplicate entry worth merging. A row with linked: true is "
            "two entries that cite each other -- often a paper and its own dataset card "
            "or homepage. Same proposition, but the second is a RESTATEMENT of the "
            "first, not a second witness to it."
        ),
        "rows": rows,
    }


_DECISIONS = frozenset({"pending", "same", "different"})


def aliases_from_worksheet(worksheet: dict) -> list[dict]:
    """Collect `same` rows into transitively-closed alias groups.

    Transitive closure happens here rather than in the fold because a reviewer who marks A~B and
    B~C has asserted A~C whether or not they wrote that row, and leaving it to the fold's
    union-find would make the emitted frames an incomplete record of the judgment. The frames are
    the record; they should say what was decided.
    """
    if worksheet.get("schema") != "epyc.vidya/alias-worksheet/v1":
        raise WorksheetError(f"unrecognized worksheet schema {worksheet.get('schema')!r}")
    rows = worksheet.get("rows")
    if not isinstance(rows, list):
        raise WorksheetError("worksheet.rows must be a list")

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    approved: list[dict] = []
    for i, row in enumerate(rows):
        decision = row.get("decision")
        if decision not in _DECISIONS:
            raise WorksheetError(
                f"rows[{i}]: decision must be one of {sorted(_DECISIONS)}, got {decision!r}"
            )
        if decision != "same":
            continue
        a, b = row.get("claim_a"), row.get("claim_b")
        if not isinstance(a, str) or not isinstance(b, str):
            raise WorksheetError(f"rows[{i}]: claim_a/claim_b must be strings")
        if not (row.get("reviewer") or "").strip():
            raise WorksheetError(
                f"rows[{i}]: an approved alias must name its reviewer -- an unattributed "
                "human judgment is indistinguishable from one the machine made"
            )
        approved.append(row)
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = sorted((ra, rb))
            parent[hi] = lo

    groups: dict[str, set[str]] = defaultdict(set)
    for row in approved:
        for cid in (row["claim_a"], row["claim_b"]):
            groups[find(cid)].add(cid)

    reviewers = sorted({(r.get("reviewer") or "").strip() for r in approved})
    out = []
    for root in sorted(groups):
        members = sorted(groups[root])
        notes = sorted(
            {
                (r.get("note") or "").strip()
                for r in approved
                if find(r["claim_a"]) == root and (r.get("note") or "").strip()
            }
        )
        out.append({"claim_ids": members, "reviewers": reviewers, "notes": notes})
    return out
