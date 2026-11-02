# Knowledge transparency: wiki, belief kernel, episodic memory (ws58 intake, source 3)

Sources:
- **intake-2617..2621** (new): the Ryven X Article, the noze.it summary, claude-obsidian, obsidian-second-brain, and The AI Operator write-up (Stage-2b wave 1).
- **intake-268** (re-encounter): the Karpathy "LLM Wiki" gist.
- **intake-270** (re-encounter): the qmd search engine.

Dive tables: [wiki3-dive.md](wiki3-dive.md) and [wiki3b-dive.md](wiki3b-dive.md). Our-store survey: read-only, done 2026-11-02 against epyc-root origin/main.

## Corrections to the operator summary

- **Folder layout.** `raw/ wiki/ output/` and "using only wiki/" come from the Ryven article (intake-2617), not from the gist. The gist describes three layers (raw, wiki, schema) plus `index.md` and `log.md`.
- **Scale limits.** The gist's "~100 sources, ~hundreds of pages" is an offhand remark. The AI Operator's "breaks past 50-100 sources" is also anecdotal (intake-2621). Neither was measured.
- **Lint and contradictions.**
  - claude-obsidian's lint is deterministic. It explicitly does not claim semantic contradiction detection.
  - obsidian-second-brain finds contradictions with LLM subagents and then *auto-resolves* them. That is the opposite of operator transparency.
  - Its saving mechanism is a quote gate: a contradiction that cannot quote both sides verbatim is dropped (intake-2620).
- **Ryven.** The author says the walkthrough was not run end to end.

## Honest comparison: our wiki versus the LLM-wiki pattern

**What we do better:**
- Every wiki citation resolves to an intake entry with quote-hashed claim anchors.
- `cite-check` gates refuted, conflicted and dangling citations, and the belief kernel folds conflicts into a served CONFLICTED verdict (`scripts/vidya/fold.py:144,223`). Neither the gist nor claude-obsidian has graded claims with retraction impact (`vidya impact`).
- Compilation is incremental and keyed on content hashes (`wiki/source_manifest.json`).

**What we do worse:**
1. **Pages are append-only logs.**
   - Each category page grows by "Compiled Update" sections, and line 5 of `wiki/agent-architecture.md` is a single multi-KB "Last compiled" history line.
   - This is the failure The AI Operator describes: old and new facts sit side by side with nothing saying which is current.
2. **No human index-first navigation.**
   - `wiki/INDEX.md` exists, but nothing gives a one-line-per-page current-state summary.
   - No hub page shows the wiki or the ledger.
3. **Lint has gaps.**
   - `lint_wiki.py` has seven passes: handoff orphans, stale entries, handoff status contradictions, un-actioned intake, missing cross-refs, page structure, and relative-link targets.
   - It does not check for wiki-page orphans, unsourced bullets, or wiki claims whose cited claim is CONFLICTED or refuted.
   - It runs on the CLI only and is not surfaced on the :8100 hub.
4. **Not Obsidian-ready.**
   - About 9,800 relative Markdown links, no `[[wikilinks]]`, and no `.obsidian/`.
   - Opened as a vault rooted at `/workspace`, relative links resolve and Obsidian draws edges, but intake entries, claims and memory files are not nodes.
5. **Episodic stores are opaque.**
   - `MEMORY.md` is over its size limit and is truncated on load.
   - Progress files, transcripts and bus logs are reachable only by grep. kb-search indexes markdown in wiki, handoffs, research, progress and chapters, but not memory, the ledger or the bus.
6. **Provenance chains are recorded but not walkable.**
   - Frames carry `provenance.replay_key.read_set` and measurement rows carry commit, path and producer.
   - `vidya query/impact` answer one claim at a time on the CLI. No UI goes claim → evidence → run → commit.

## Recommended build path (minimal, ordered)

| ID | Owner (proposed) | Deliverable |
|---|---|---|
| KT-1 | project-wiki skill (`.claude/skills/project-wiki/scripts/lint_wiki.py`) | Add three deterministic lint passes: wiki-page orphans (no inbound link and absent from INDEX); unsourced bullets in Compiled Update sections (no `intake-` or path citation); and wiki citations whose claim `cite-check` reports CONFLICTED or refuted. Emit JSON as well as text. |
| KT-2 | vidya-belief-substrate-program.md | Add a contradiction gate in the style of `verify_quotes`. An LLM-proposed contradiction between two wiki/ledger statements is filed into the `corrections` queue only if both sides carry path, line and a verbatim quote that re-finds and hashes. Nothing auto-resolves; the operator adjudicates. |
| KT-3 | hub dashboard owner (`dashboard/`) | Add a **Knowledge** page that reads the KT-1 JSON plus a `vidya` export. It shows store counts and freshness, lint and conflict totals, and a claim browser (claim → tuple and grade → supporting and refuting frames → run artifact → commit, plus the "cited by" reverse lookup and the `impact` preview). It needs a registry entry, a `/api/health` probe and a freshness envelope, per `dashboard/README.md`. |
| KT-4 | project-wiki skill | Make compiled pages readable: move the "Last compiled" history to a log section, and keep a one-line current-state summary per page in INDEX (the gist's index-first pattern). Generate the edge list (md links, `intake-NNN#claim` citations, ledger `depends_on`, handoff deps) as JSON for the KT-3 graph. Optionally emit an Obsidian-compatible stub vault under `/mnt/raid0/llm/tmp/` for anyone who prefers Obsidian. Generated output only; never hand-maintained. |
| KT-5 | agent memory owner (operator-facing) | Split `MEMORY.md` into category index files under the size limit, and include memory and progress files in the KT-3 map's search, reusing kb-search's index rather than a new one. |

Ordering:
- KT-1 comes first, because KT-3 consumes it.
- KT-2 is independent and safe to run in parallel.
- KT-4's edge list feeds the KT-3 graph.
- KT-5 is independent.

Minimum-rigor note: all five are deterministic infrastructure. The conformance checks are lint fixtures with known orphans, unsourced bullets and a conflicted citation, plus a hub freshness probe. KT-2's LLM step is proposal-only and gated by quote hashes.

## Can one GUI serve both loop design/debugging and knowledge inspection?

**Yes, as one hub page family over one typed graph model, but not as one view.**
- A loop spec (states, transitions, stop reasons, thresholds) and a provenance chain (claim → evidence → run → commit) are both typed node-edge graphs with per-node detail.
- Both need the same three affordances: render the graph, step through saved records (loop replay, or a claim's evidence over time), and show "what changes if X changes" (threshold divergence, or `vidya impact` retraction).
- Build one shared renderer and detail panel (the inline-SVG precedent in `cockpit.html`, or vendored Mermaid for state diagrams), fed by two data contracts that stay with their producers: the loop spec and journals for JEV-5, and the KT-1/KT-4 JSON plus the vidya export for KT-3.

Two things stay separate:
- the editing paths: loop specs take threshold patches, while knowledge takes adjudications through the `corrections` queue;
- the pages themselves, so each keeps its own registry entry and freshness envelope.

Obsidian stays optional: a generated vault is fine for browsing, but it cannot show ledger grades, conflicts or loop replay.
