# Web Research Content Deduplication

**Status**: COMPLETED
**Created**: 2026-03-03
**Priority**: P1 — low effort, reduces context waste
**Effort**: Low (~50 lines of new code + prompt tweaks)

## Problem

When `web_research` fetches multiple pages in parallel, overlapping content (e.g., same StackOverflow answer on multiple aggregator sites, repeated boilerplate across docs pages) is passed to the synthesis worker in full. This wastes context window and can bias synthesis toward over-represented content.

## Implementation Target

All changes in one file: `/mnt/raid0/llm/epyc-orchestrator/src/tools/web/research.py`

## Implementation Steps

### 1. Add `_dedup_pages()` function (new, ~line 107)

Insert between `_fetch_page` (ends line 104) and `_synthesize_page` (starts line 107).

```python
import hashlib  # add to imports at top

_MIN_PARAGRAPH_LEN = 80  # skip short paragraphs (nav, footers)

def _dedup_pages(
    pages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Remove duplicate paragraphs across fetched pages.

    Split each page on paragraph boundaries, normalize, SHA256-hash each
    paragraph. First-seen wins; later duplicates are removed.

    Args:
        pages: List of fetch result dicts (must have 'content' and 'url').

    Returns:
        (deduped_pages, stats) — pages with deduplicated content, and
        a dict with paragraphs_removed, chars_saved, pages_affected.
    """
    seen_hashes: set[str] = set()
    stats = {"paragraphs_removed": 0, "chars_saved": 0, "pages_affected": set()}
    result = []

    for page in pages:
        content = page.get("content", "")
        # Split on double-newline; fallback to single newline
        paragraphs = content.split("\n\n") if "\n\n" in content else content.split("\n")

        kept = []
        for para in paragraphs:
            normalized = " ".join(para.lower().split())  # lowercase + collapse whitespace
            if len(normalized) < _MIN_PARAGRAPH_LEN:
                kept.append(para)  # keep short paras (headers, etc.) unconditionally
                continue
            h = hashlib.sha256(normalized.encode()).hexdigest()
            if h in seen_hashes:
                stats["paragraphs_removed"] += 1
                stats["chars_saved"] += len(para)
                stats["pages_affected"].add(page["url"])
            else:
                seen_hashes.add(h)
                kept.append(para)

        deduped_content = "\n\n".join(kept)
        result.append({**page, "content": deduped_content})

    stats["pages_affected"] = len(stats["pages_affected"])
    return result, stats
```

**Key design decisions**:
- Paragraph-level SHA256 via stdlib `hashlib` — zero new dependencies
- Short paragraphs (<80 chars) kept unconditionally to avoid stripping headers/nav that provide structure
- Normalize: lowercase + collapse whitespace before hashing (catches formatting-only differences)
- First-seen wins — so pages must be sorted by search rank before dedup (see step 2)

### 2. Wire into `_web_research_impl()` (~line 257-261)

Currently, `to_synthesize` is built directly from `fetched.values()` which uses `as_completed` order (arbitrary). Replace with rank-ordered dedup:

**Before** (lines 258-261):
```python
    to_synthesize = [
        f for f in fetched.values()
        if f.get("success") and f.get("content", "").strip()
    ]
```

**After**:
```python
    # Preserve search-rank order (as_completed returns in arbitrary order)
    successful_pages = [
        fetched[r["url"]]
        for r in pages_to_fetch
        if r["url"] in fetched
        and fetched[r["url"]].get("success")
        and fetched[r["url"]].get("content", "").strip()
    ]

    # Dedup before synthesis — higher-ranked page content is canonical
    to_synthesize, dedup_stats = _dedup_pages(successful_pages)
```

This ensures higher-ranked search results keep their content when duplicates appear.

### 3. Update synthesis prompt (~lines 133-147)

Add anchored synthesis instructions to reduce hallucination.

**System prompt** — append before `<|im_end|>` on line 138:
```
IMPORTANT: Only use information from the retrieved content below. Do not add facts from your training data.
```

**User prompt** — change line 144 from:
```
Synthesize the relevant information from this page.
```
to:
```
Synthesize the relevant information from this page. Cite the source URL when stating specific facts.
```

### 4. Add dedup stats to return dict (~line 306)

Add dedup metrics to the return value of `_web_research_impl()`:

```python
    return {
        "success": True,
        "query": query,
        "sources": sources,
        "pages_fetched": len(to_synthesize),
        "pages_synthesized": synth_count,
        "dedup_paragraphs_removed": dedup_stats["paragraphs_removed"],
        "dedup_chars_saved": dedup_stats["chars_saved"],
        "total_elapsed_ms": total_elapsed,
    }
```

Handle the no-pages case: if `to_synthesize` is empty before dedup, set `dedup_stats = {"paragraphs_removed": 0, "chars_saved": 0, "pages_affected": 0}`.

## Known Peripheral Issues (out of scope)

Discovered during analysis — not blocking for this handoff but should be tracked:

1. **`web_research` missing from `group:web`** in `src/tool_policy.py` — cascading policy won't grant it when `group:web` is allowed. Only `web_search` and `web_fetch` are in the group.
2. **`web_research` missing from `src/tools/web/manifest.json`** — plugin loader can't hot-reload it.
3. **No retry/fallback in `src/tools/web/search.py`** — unlike `orchestration/tools/web.py` which has 2 retries + Wikipedia fallback, the search module used by `web_research` has no resilience.

## Acceptance Criteria

- [x] `_dedup_pages()` function added — pure function, paragraph-level SHA256 dedup
- [x] Pages sorted by search rank before dedup (higher rank = canonical)
- [x] Dedup wired between fetch (Step 2) and synthesis (Step 3) in `_web_research_impl()`
- [x] Anchored synthesis prompting added (only-retrieved-context + cite-source-URL)
- [x] Dedup stats (`paragraphs_removed`, `chars_saved`) included in return dict
- [x] No new dependencies (stdlib `hashlib` + `re` only)
- [ ] No regression in web_research answer quality (verify via seeding) — pending live validation

### Test Plan

Unit tests for `_dedup_pages()` (pure function, no mocking needed):
- [x] **No-op passthrough**: pages with no overlapping content → output identical to input
- [x] **Duplicate removal**: same paragraph across two pages → removed from second page
- [x] **Short paragraph exclusion**: paragraphs < 80 chars always kept (even if duplicated)
- [x] **Case/whitespace normalization**: "Hello World" and "hello  world" treated as same
- [x] **Empty pages**: pages with empty/whitespace-only content handled gracefully
- [x] **Stats consistency**: `paragraphs_removed` count matches actual removals, `chars_saved` matches removed chars
- [x] **Rank ordering preserved**: first page in list retains content, later pages lose duplicates

## References

- Implementation file: `/mnt/raid0/llm/epyc-orchestrator/src/tools/web/research.py`
- Tool policy: `/mnt/raid0/llm/epyc-orchestrator/src/tool_policy.py`
- Tool manifest: `/mnt/raid0/llm/epyc-orchestrator/src/tools/web/manifest.json`
- Explore worker (synthesis): port 8082, Qwen2.5-7B
- Original inspiration: [Multi-Agent RAG article](https://dev.to/gowtham21/multi-agent-ragbuilding-intelligent-collaborative-retrieval-systems-with-langchain-441e)
