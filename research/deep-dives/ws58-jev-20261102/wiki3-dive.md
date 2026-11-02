# wiki3 dive: LLM Wiki / second-brain (2026-11-02)
Scratch only. Evidence files in src/. Locators for tweet = tw.txt (fxtwitter article blocks, line = block order), noze = noze.txt (tag-stripped).

## Reachability / versions
- Karpathy gist: raw reachable (11985 B, etag 353f6eb6...316d). GitHub gist API 500'd; revisions page lists 442a...(ac46de1ad27f92b28ac95459c782c07f6b8c964a) as a revision hash (unverified which is HEAD). Gist body line 1 "LLM Wiki".
- X post: api.fxtwitter returned the article text ((imryven X Article), created 2026-10-27, title "How to Build a Second Brain With Claude and Obsidian That Gets Smarter With..." ); author self-states he has not run it.
- noze.it: reachable, page dated 28 Apr 2026; a short secondary summary of the gist.
- claude-obsidian: HEAD 2e545563172f97f02ecaaaab376ceea1246a0583 (2026-10-22), MIT.
- obsidian-second-brain: HEAD f79c64f3f03ee25ec1660c8a30ebe7f4f8e044ff (2026-10-28), MIT.

## Claim tables (quote_sha256 = sha256 of the utf-8 quote)
| src | claim | verdict | locator | quote | quote_sha256 |
|---|---|---|---|---|---|
| gist | compile-once vs RAG | CONFIRMED | gist.md:9 gist rev ac46de1(?) | the LLM is rediscovering knowledge from scratch on every question. There's no accumulation. | 30da92d0d943a13a80ddbeb08888c6c2d68a72b4b5f6f38c6825a830cac750af |
| gist | layers; schema | PARTIAL | gist.md:33  | The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for Codex) that tells the LLM how the wiki is structured | b8d53e91a6e3f9d1e9400bf68a20116841209ec6c528d9612525416618fd69e7 |
| gist | index-first + scale ~100 sources | CONFIRMED | gist.md:47  | This works surprisingly well at moderate scale (~100 sources, ~hundreds of pages) and avoids the need for embedding-based RAG infrastructure. | 84a854a265d1da26b9dde8197a150861aff314fffea374d66aa0099bb60fde5e |
| gist | lint contents | CONFIRMED | gist.md:41  | contradictions between pages, stale claims that newer sources have superseded, orphan pages with no inbound links | 171eaa9980f2ae3852ce2a545ea70fb1dbeb3d6b214c9b7172f29c30ac5728fe |
| gist | graph view | CONFIRMED | gist.md:59  | **Obsidian's graph view** is the best way to see the shape of your wiki | 82ecfdac67a4470c7d8d1afe4a8878840e954a52ed0ad9e124c8724e2b991eb9 |
| gist | file answers back | CONFIRMED | gist.md:39  | **good answers can be filed back into the wiki as new pages.** | 303dc84d58cecbfc2c131a6fff52e82f78838b22ec1fad468f72390ed787fd49 |
| tweet | using only wiki/ | CONFIRMED | tw.txt:63 fxtwitter (imryven X Article) | Using only wiki/, what are the three best arguments I've collected about [topic]? | 6d770ab580512c3ead709b1d53e06d6ebc9100081a55f9a07495fd54deb98a37 |
| tweet | say when not covered | CONFIRMED | tw.txt:63  | If the wiki doesn't cover part of it, say so. | 65cf90353c88e8a428ce9fbb1ab582b839bc3f92719ae1c2ff992eed8e116a75 |
| tweet | CLAUDE.md context not enforcement | CONFIRMED | tw.txt:109  | Anthropic's documentation says plainly that CLAUDE.md is context, not enforced configuration. | 99e35a29b3d19cfe8c85363ae222457d634bf11b69b23ba51fd0d54dcdc6d2ed |
| tweet | nightly ingest | CONFIRMED | tw.txt:94  | Check raw/ for files not yet ingested. | 70a8f76e2a8a968de4748db971bc45246b9a9adeb184c8d1c565c8eb91c706e5 |
| tweet | weekly lint | CONFIRMED | tw.txt:101  | List pages that contradict each other, pages with no links, ideas that appear in several places but have no page, and claims with no source in raw/. | 069df1ff55dad8b565ce8841511313cef8697fd98ad52d2664f0ebf2016e6584 |
| tweet | skills replace bloated CLAUDE.md | CONFIRMED | tw.txt:75  | Anthropic's own advice is to move multi-step procedures out of CLAUDE.md and into skills | 984205c008dac966219906b4203fd111ec59ef4539a9a9197217ba8075325cd0 |
| tweet | failure modes | CONFIRMED | tw.txt:103  | Four ways this breaks (and the fix) | 3aa7aad7ade8ef77373d789b5a8214668ef5e1f5e319c50f585ddd4fcb9a2986 |
| tweet | author did not run it | PARTIAL(limitation) | tw.txt:132  | I have not run this walkthrough end to end | e4d3b398cc1ec852cd59c80634e85ee61b0214bcdc613d5233b82edef6bb9702 |
| noze | compile vs RAG | CONFIRMED | noze.txt:12 fetched 2026-11-02; page dated 28 Apr 2026 | The model, Andrej Karpathy writes in a gist published on 4 April 2026, “rediscovers knowledge from scratch on every question. There’s no accumulation.” | 468544936b0553d9011fa1b01fe7ce5ec93c82962a003212491aad278bc815f0 |
| noze | ingest 10-15 pages | CONFIRMED | noze.txt:18  | a new document arrives, the LLM reads it and updates 10-15 related wiki pages | 605df3757bdd21664e672e05db36f812107dfd19bd85dbbc65ffdc68d7007a1b |
| noze | lint | CONFIRMED | noze.txt:18  | lint (periodic passes that surface contradictions, orphan links and gaps) | 662c0a5ebc3cbb5280a5280a1971d771580f84b081684d49f688785d789b4e3d |
| noze | scale limit / raw/ wiki/ output/ | NOT-FOUND-IN-SOURCE | noze.txt | (none: no ~100-source limit, no output/ dir stated) | - |
| co | lint is deterministic, NOT semantic contradiction | OVERTURNED(summary: lint finds contradictions) | co/skills/wiki-lint/SKILL.md:50 claude-obsidian 2e54556 MIT | do not claim that it performed ⏎ semantic, stylistic, or prose-level contradiction analysis | c16c526bcae55809b7488a3f8c06c63d4e571c92e329bec4fc5ee65a720fa624 |
| co | unsourced/provenance + orphans | PARTIAL | co/skills/wiki-lint/SKILL.md:47  | It reports such categories as dead or ambiguous links, orphan pages, required | adcaeed984856bf88e855d75a2207054e32e8649f34aebfd605d9bbaee614af8 |
| co | claim ledger states | CONFIRMED(extension) | co/skills/wiki/references/provenance.md:42  | Assessment is `accepted`, `provisional`, `contested`, `unsupported`, or | d1bc8ed44f20c0e6540b485bc22b7b3d775e2826baa5e858355880fd58d83bc3 |
| co | only-wiki + say not covered | CONFIRMED | co/skills/wiki-query/SKILL.md:107  | If the vault cannot answer, name the missing evidence and stop. | 404232373c350e2eed9612821cf79d0f7714ebd0015a7787eb3f638052e8f8a8 |
| co | index-first | CONFIRMED | co/skills/wiki-query/SKILL.md:33  | read `wiki/hot.md` and `wiki/index.md`, then verify the directly | 5f8ff55cf78ab7729ddfd687126d07cdb0cfa23ab46fb1e34f1e812e23ebcc4f |
| co | file answers back = separate op | PARTIAL | co/skills/wiki-query/SKILL.md:110  | This skill never creates a note, updates an index, logs a query, refreshes a | a38f49495e43a3f728c14d78581454f945e881f5c05f5bc7f32ef9296e286595 |
| osb | claims it evolves Karpathy; auto-resolves contradictions | PARTIAL(contradicts gist's flag-for-human) | osb/README.md:117 obsidian-second-brain f79c64f MIT | `/obsidian-reconcile` resolves them automatically | 0484b752113cb1e66a7ce59b4cc77cd7437547300c11e0bf03200df91f5493e0 |
| osb | nightly/weekly/health schedule | CONFIRMED | osb/README.md:603  | | `health` | Sundays 9 PM | Vault health audit | | 7069a9c4890cc3117a982ffbf17ee9867af7f23f39b0afeaece24c2ffca18bf9 |
| osb | contradiction proven only by verbatim quote | CONFIRMED(extension) | osb/scripts/verify_quotes.py:6  | A contradiction a model reports but cannot quote is ⏎ dropped, never acted on. | 909b8ee0faf4e1fc9aab29e2f0b61cd054a5de88093a1fa6bf848a6699f4dd71 |
| osb | contradiction detection is an LLM subagent scan | CONFIRMED | osb/commands/obsidian-health.md:29  | scan Key Decisions sections and reference/concept notes | eeec06009c6a3881d888e2525c69efb95f0e9fd92504a695cecfaeb99c5ab0ee |

Notes on the operator summary: "raw/ wiki/ output/ CLAUDE.md" dir names come from the X article, not the gist (gist says "Raw sources", "wiki", "schema" as layers; has index.md + log.md, no output/). "Few hundred pages / ~100 sources" is the gist's own wording ("~100 sources, ~hundreds of pages") and is a soft remark, not a measured limit; noze does not state it. The "wiki answers only from wiki/, say so" rule is the X article's prompt, not the gist. "Skills replace bloated CLAUDE.md" and "200 lines" are the article citing Anthropic docs (not independently checked).

## Mechanisms useful for a transparent wiki / claim ledger / episodic memory
1. Lint implementation (key finding): claude-obsidian lint = deterministic parser (scripts/claude-obsidian.py lint) reporting dead/ambiguous links, orphan pages, frontmatter gaps, empty sections, stale index entries, and source/claim-ledger contract violations; explicitly NO semantic contradiction detection, read-only, repair is a separate hashed transaction bundle (expected SHA-256 per target, review, apply, re-lint). obsidian-second-brain splits: scripts/vault_health.py (deterministic orphans, duplicates, missing frontmatter, wanted-notes = linked-but-unwritten ranked by demand, source_payload / source_quality checks) + LLM subagents for contradictions, stale claims, concept gaps (terms in 3+ notes without a page). So: orphan = deterministic; unsourced = deterministic only where a ledger/field exists (claude-obsidian ledgers; osb source_quality); contradiction = LLM, optionally gated.
2. Contradiction proof gate (osb scripts/verify_quotes.py): each side of a claimed contradiction must give path+line+verbatim quote (>= min length, NFC-normalised, path inside vault); unquotable contradictions are dropped, never acted on. Directly analogous to our quote_sha256 / cite-check discipline; adoptable as-is for a contradiction lint over wiki + .vidya ledger.
3. Provenance ledgers (claude-obsidian wiki/meta/ledgers/{source,claim}-ledger.json, references/provenance.md): separate ingestion manifest, source ledger (identity, authority official/primary/secondary/community/synthetic/unknown, SHA-256, refresh_due; staleness computed not stored; independence_key so correlated sources don't count as corroboration) and claim ledger (accepted/provisional/contested/unsupported/deprecated; accepted needs a fresh active non-synthetic source; high-risk needs two independent; contradictions preserved, no silent winner). Closest external analogue to our claim tuples; the independence_key and compute-staleness rules are worth comparing with claim_tuple.grade().
4. Index-first navigation: wiki/index.md catalog (+ hot.md orientation cache, per-depth read budgets 12/48/128 KiB), fallback chain index -> BM25 retrieve -> text search, with the fallback named in the answer. log.md with `## [date] op | title` prefix greppable.
5. Graph views: Obsidian graph/Canvas; osb generates a canvas (hubs centred, colour by type, orphans highlighted) and link_graph.py typed edges (`relations:` frontmatter) with lint for unknown types, dangling targets, contradiction cycles. For us: a hub page rendering the claim->evidence->run->commit chain is a typed-edge graph; same lint set applies.
6. Freshness policy (osb OKM): every stored fact is timeless, dated, or a pointer with "as of"; freshness_lint.py enforces. Maps to our "no hand-written liveness" rule.
7. Rewrite gate: osb treats ingested source as data, existing-note rewrites are proposals needing confirmation unless vault opts into rewrite_policy=unattended.

## Limitations / adversarial points
- Gist is explicitly abstract ("intentionally abstract"); scale claim is anecdotal. Article is a how-to, self-declared untested, relies on prompt-level rules ("CLAUDE.md is context, not enforced") - hard rules need hooks/permissions.
- osb README markets automatic contradiction resolution and AI-first notes "for LLM retrieval, not human review" - opposite of human transparency; its auto-reconcile is the failure mode the gist's lint-then-human flags. Mitigated only by the quote verifier and confirm policy. README marketing counts (8 agents/48 commands vs article's 43) drift.
- LLM-judged contradiction/stale-claim lint is non-deterministic; "weekly lint" in the article is a prompt, not code. Only claude-obsidian's lint is reproducible, and it deliberately does not do semantics.
- Prompt-injection: both repos treat vault pages/sources as untrusted data (explicit text) - good practice, not proof.
- Stars/popularity not verified; both repos are 2026 projects by single authors; not run.

## Dive-surfaced sources
- https://theaioperator.io/p/i-rebuilt-karpathys-llm-wiki-heres (osb README: "append-only breaks at scale", 3 bugs in v1) - would settle the scale-limit / failure-at-scale claim with an experience report.
- https://github.com/tobi/qmd (gist: hybrid BM25/vector local search over markdown) - would settle what to do past the index-only scale.
- osb references/freshness-policy.md + scripts/freshness_lint.py, scripts/link_graph.py, scripts/verify_quotes.py (in clone) - concrete lint code to read in full.
- claude-obsidian skills/wiki/references/operation-transactions.md, scripts/claude-obsidian.py lint core - hashed repair-transaction contract.
- Gist comment implementations (SwarmVault, WeKnora, Keppi, llmwiki-cli, OmegaWiki, Lore; via noze) - would settle prior art for provenance/graph UIs.
- Anthropic Claude Code docs (CLAUDE.md <200 lines, "context not enforced") - would verify the article's attributed claims.
