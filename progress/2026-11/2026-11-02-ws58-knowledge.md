# 2026-11-02 — ws58 knowledge transparency: KT-1, KT-2, KT-4

Plan: `research/deep-dives/ws58-jev-20261102/knowledge-transparency.md` (operator: "Approve, go to Stage 4").
Code commit: `1eb5a93a7` (rebased; see `git log` for the final SHA on main).

## KT-1 — `lint_wiki.py` JSON passes (project-wiki skill)
- New passes `wiki_orphans`, `unsourced_bullets`, `conflicted_citations` (shells out to
  `vidya cite-check` so lint and gate cannot disagree), `contradictions` (KT-2 queue); enabled in
  `wiki.yaml`. New flags `--json`, `--json-out`, `--only`. SKILL.md lint step documents them.
- First run (full lint, 2026-11-02): 0 errors, 705 warnings. Wiki orphans 0; unsourced bullets
  2938 = 575 WARNING (section has no source list) + 2363 INFO (section-sourced only); conflicted
  citations 0 (cite-check: 3181 citations, 0 blocking); contradictions 0 (queue empty).
- Removes: manual wiki audits.

## KT-2 — contradiction gate (vidya program)
- `scripts/vidya/contradiction_gate.py`: a proposed pair is filed to
  `data/vidya/contradiction_queue.jsonl` only if both sides re-find verbatim at path:line (±5) and
  hash (sha256 of the normalised quote); pair id is order-independent, so re-proposals dedupe.
  Status is always `pending`; no code path resolves. `vidya corrections` lists pending pairs beside
  the SC13 dive corrections.
- Removes: contradictions that silently coexist.
- Belief-kernel wiring note: the queue holds adjudication *inputs*, not measurements; when the
  operator adjudicates a pair, the verdict should enter through the existing correction-review frame
  path — that wiring belongs to the vidya program owner.

## KT-4 — readable compiled pages (project-wiki skill)
- `render_wiki.py`: `restructure` (topical sections first, history to `## Compile Log`, lossless and
  idempotent by test), `index` (generated one-line current-state summary per page in INDEX.md),
  `edges` (10100 md links, 3168 intake citations, 406 ledger depends_on, 82 handoff deps →
  `/mnt/raid0/llm/tmp/wiki-kt4/edges.json`), `vault` (Obsidian view, `/mnt/raid0/llm/tmp/wiki-kt4/obsidian-vault`).
- Demonstrated on `wiki/chat-templates.md` and `wiki/cost-aware-routing.md` only; the full sweep is
  operator-cadence.
- Removes: reading append-only logs.

Tests: `tests/skills/test_project_wiki_kt.py`, `tests/vidya/test_contradiction_gate.py` (+ existing
lint and correction-queue suites): 30+ passed.
