"""PR1b: locate cited claims in their sources by machine, and record what was found honestly.

Measured motivation (2026-08-10): 667 entries are cited by active handoffs and design docs and
**5** are anchored, so a conjunctive `Verified/Anchored` policy is satisfied by almost nothing. Hand
-anchoring 2,994 claims was never going to happen; the operator ratified `T2 MachineLocated` to
receive the machine-found ones instead.

WHAT THIS IS NOT. It does not read the paper and decide the passage supports the claim — that is
the act `T3 Anchored` records, and no amount of string matching performs it. It finds a span whose
wording overlaps the claim's distinctive terms, pins it with `quote_sha256`, and stamps
`located_by: machine` so the grade caps below a human anchor no matter how complete the record is.

The matcher is deliberately conservative in one direction: it would rather return nothing than
return a plausible wrong span. A missing anchor costs recall and is recoverable on a later run; a
confident wrong anchor is a fabricated citation with a hash on it, which is the exact failure this
whole program was created over.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from canonical import normalized_quote  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX = REPO_ROOT / "research" / "intake_index.yaml"

# A span must clear ALL of these to be recorded. They are tuned to refuse, not to reach.
MIN_DISTINCTIVE_TERMS = 3      # shared rare terms between claim and span
MIN_COVERAGE = 0.45            # fraction of the claim's distinctive terms present in the span
MIN_MARGIN = 1.30              # best span must beat the runner-up by this factor
# A claim carrying magnitudes must find at least one of them in the span. Added after the
# first real run anchored a WER figure to a sentence that only NAMED the metric, and a
# token-reduction claim to a sentence whose numbers contradicted it.
MAX_SPAN_CHARS = 600

_STOP = frozenset("""
a an the and or but of to in on for with by from as at is are was were be been being it its this
that these those we they our their can could may might will would should must not no than then
we present our results show paper method approach using used use new novel propose proposed
""".split())

_TOKEN = re.compile(r"[a-z0-9][a-z0-9._+-]*")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def terms(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 2}


def fetch_text(url: str, *, timeout: int = 45) -> str | None:
    """Fetch a source as plain-ish text. arXiv goes through the HTML rendering."""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9v.]+)", url, re.I)
    candidates = []
    if m:
        bare = re.sub(r"v\d+$", "", m.group(1).removesuffix(".pdf"))
        candidates = [f"https://arxiv.org/abs/{bare}"]
    else:
        candidates = [url]
    for u in candidates:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "epyc-vidya-anchor/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                    .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 400:
            return text
    return None


# Bare years are dates, not magnitudes, and matching on "2024" would anchor half the corpus to a
# citation line.
# `(?<![A-Za-z]-)` keeps benchmark and model names out: MATH-500, Qwen3-14B and GPT-4 carry digits
# that are IDENTIFIERS, not measurements. Without it the guard passed a contradicting span because
# claim and span both said "MATH-500" — a shared name reading as a shared number, which is exactly
# the kind of near-miss the guard exists to catch.
_NUM = re.compile(r"(?<![\w.])(?<![A-Za-z]-)(\d+(?:\.\d+)?)\s*(%|x\b|k\b|b\b|pp\b|points?\b)?", re.I)
_YEARISH = re.compile(r"^(19|20|21|22|23|24|25|26)\d\d$")


def magnitudes(text: str) -> set[str]:
    """Numbers that carry meaning in a claim, normalized so 8.0 and 8 agree."""
    out = set()
    for val, _unit in _NUM.findall(text):
        if _YEARISH.match(val):
            continue
        norm = val.rstrip("0").rstrip(".") if "." in val else val
        out.add(norm)
    return out


def numeric_agreement(claim: str, span: str) -> bool:
    """True unless the claim's magnitudes are absent from, or contradicted by, the span.

    A claim with no magnitudes is unaffected. A claim WITH magnitudes needs at least one of them
    present verbatim: a span carrying only different numbers is not a weaker match, it is evidence
    the claim is somewhere else — or wrong.
    """
    want = magnitudes(claim)
    if not want:
        return True
    return bool(want & magnitudes(span))


def best_span(claim: str, document: str) -> dict | None:
    """The single best-matching sentence-span, or None when nothing clears the bars."""
    claim_terms = terms(claim)
    if len(claim_terms) < MIN_DISTINCTIVE_TERMS:
        return None                       # the claim itself is too generic to anchor safely

    sentences = [s.strip() for s in _SENT.split(document) if 40 <= len(s.strip()) <= MAX_SPAN_CHARS]
    if not sentences:
        return None

    scored = []
    for sent in sentences:
        shared = claim_terms & terms(sent)
        if len(shared) < MIN_DISTINCTIVE_TERMS:
            continue
        if not numeric_agreement(claim, sent):
            continue          # the span lacks the claim's numbers, or carries different ones
        coverage = len(shared) / len(claim_terms)
        scored.append((coverage, len(shared), sent))
    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], -x[1]))
    coverage, n_shared, sent = scored[0]
    if coverage < MIN_COVERAGE:
        return None
    # Margin: an ambiguous best match is not a match. Two sentences that fit equally well mean the
    # claim is paraphrased across the paper, and picking one would assert a location nobody chose.
    if len(scored) > 1 and scored[1][0] > 0 and coverage / scored[1][0] < MIN_MARGIN:
        return None

    return {
        "quote": sent,
        "coverage": round(coverage, 3),
        "shared_terms": n_shared,
        "quote_sha256": hashlib.sha256(normalized_quote(sent).encode("utf-8")).hexdigest(),
    }


def anchor_entry(entry: dict, *, document: str | None = None) -> list[dict]:
    """Machine anchors for one entry's claims. Never anchors a claim that already has one."""
    url = entry.get("url")
    if not isinstance(url, str) or not url.strip():
        return []
    have = {a.get("claim_index") for a in entry.get("claim_anchors") or []}
    # Enumerate the ORIGINAL list and skip non-strings in place. Filtering first and enumerating
    # the filtered list shifts every index after a non-string claim, which silently pins a quote
    # hash to the WRONG claim -- measured on the 2026-08-10 bulk run as 1 anchor in 352, on
    # intake-218. Seven entries in the index carry a non-string key_claim.
    claims = [(i, c) for i, c in enumerate(entry.get("key_claims") or []) if isinstance(c, str)]
    if not claims or all(i in have for i, _ in claims):
        return []

    doc = document if document is not None else fetch_text(url)
    if not doc:
        return []

    out = []
    for i, claim in claims:
        if i in have:
            continue
        hit = best_span(claim, doc)
        if not hit:
            continue
        out.append({
            "claim_index": i,
            "kind": "page-and-quote",
            "locator": f"matched span in {url}",
            "quote": hit["quote"],
            "quote_sha256": hit["quote_sha256"],
            "located_by": "machine",
            "match_coverage": str(hit["coverage"]),
            "verified_by": "vidya/machine_anchor",
        })
    return out


def main() -> int:
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=10, help="entries to attempt")
    ap.add_argument("--only-cited", action="store_true",
                    help="restrict to entries cited by handoffs/design docs")
    ap.add_argument("--out", help="write proposed anchors to this JSON file")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between fetches")
    args = ap.parse_args()

    entries = yaml.safe_load(INDEX.read_text()) or []
    cited: set[str] = set()
    if args.only_cited:
        import subprocess
        out = subprocess.run(
            ["git", "grep", "-oh", "-E", r"intake-[0-9]{1,4}", "--",
             "handoffs/active", "docs/design", "research/deep-dives"],
            capture_output=True, text=True, cwd=REPO_ROOT).stdout.split()
        cited = set(out)

    todo = [e for e in entries
            if (not args.only_cited or e["id"] in cited)
            and e.get("key_claims")
            and len(e.get("claim_anchors") or []) < len(e.get("key_claims") or [])
            and isinstance(e.get("url"), str) and e["url"].strip()]
    todo = todo[:args.limit]

    proposed, attempted, no_doc = {}, 0, 0
    for e in todo:
        attempted += 1
        doc = fetch_text(e["url"])
        if not doc:
            no_doc += 1
            print(f"  {e['id']}: source not retrievable")
            time.sleep(args.delay)
            continue
        anchors = anchor_entry(e, document=doc)
        if anchors:
            proposed[e["id"]] = anchors
        print(f"  {e['id']}: {len(anchors)} of {len(e.get('key_claims') or [])} claims anchored")
        time.sleep(args.delay)

    total = sum(len(v) for v in proposed.values())
    print(f"\nattempted {attempted} entries; {no_doc} sources unreachable; "
          f"{total} machine anchors proposed across {len(proposed)} entries")
    if args.out:
        Path(args.out).write_text(json.dumps(proposed, indent=1, sort_keys=True))
        print(f"written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
