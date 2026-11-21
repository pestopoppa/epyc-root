# Dive: Characterizing and Optimizing Context Compaction in Production Coding Agents (CompactionBench + APEC) (intake-2786, Stage-2b wave 3)

- Source read: OpenReview ICLR 2027 submission NWYYYlWJhJ, abstract/TLDR and ten public author-reply comments from https://api2.openreview.net/notes/search?term=CompactionBench (file w3/or_search.json)
- read_depth: PARTIAL; verification: stage1-unverified (unanchorable: the checker has no text artifact; anchors checked by hand, slug_text MANUAL)
- lane_head: 4b428f15153d0a32b37e6302849691b2212a49ab
- Entry: novelty medium, relevance medium, verdict adopt_patterns, credibility 3, bears_on intake-2761, intake-2770

## Locator record
- Aggron's bibliography DOI 10.20944/preprints202611.0780.v1 redirects to preprints.org/manuscript/202611.0780/v1: HTTP 403 Access Denied to curl even with a browser user agent (w3/pp.html).
- OpenReview submission NWYYYlWJhJ (ICLR 2027, Submission 22403, anonymous) found through the search API; its PDF (/pdf/37328c9e...) and forum return the OpenReview challenge (403); the direct notes?id= endpoint is gated too (w3/or_note.json).
- arXiv full-text search for CompactionBench: nothing.
- GitHub search, READMEs read: **t46/compactionbench** (archived, created 2026-06-11): "bet-0003", StatefulQA/AccumulatorQA with Qwen2.5 3B/7B and a ledger+refetch policy. **ayushnangia/CompactionBench** (created 2026-02-24): retention-vs-answer gap on BABILong/OOLONG-synth with Codex/Claude runners. Both are unrelated namesakes (no coding agents, Copilot, APEC or SWE-EVO).
- Metadata inconsistency: bibtex says "Fifteenth International Conference on Learning Representations", year 2026; venue id is ICLR.cc/2027.
- Not read: paper body, tables, APEC algorithm and index format, the actual reviews, released traces or code (authors promise open-sourcing).

## What APEC does (abstract + replies) versus Slipstream and Aggron
- **APEC**: asynchronous progressive compaction. Fine-grained, indexed summaries are prepared in the background and appended to a stable prefix, so compaction leaves the critical path and prefix-cache reuse is preserved. Harness-agnostic, summariser a black box. **PEC** is the same progressive summarisation done synchronously; the authors' reply says PEC "captures token cost and accuracy gains" while asynchrony "specifically removes blocking latency".
- **Slipstream** (intake-2770, async compaction plus next-k judge): asynchrony and a judge gate for summary acceptance; prefix handling is not the point.
- **Aggron** (intake-2761): selective prose-only summarisation, frozen append-only summaries (prefix stays valid), queue-time trigger during head-of-line blocking. It simulates "APEC" as compacting the whole context at 60K, which is not what this abstract describes. Aggron's gains over "APEC" are therefore not evidence about this design.
- Net: the prefix-preserving append is shared by APEC and Aggron; APEC's distinct parts are progressive segmentation, an index over summaries, and background timing.

## Claim verification (all from abstract/replies; none from tables)
| # | claim | verdict | passage |
|---|---|---|---|
| 0 | 13.5M Copilot sessions: 7.8% compact, 44.2% of tokens | LOCATED (abstract; trace not inspectable; reply says scaled to 103.7M for camera-ready) | "Although only 7.8% of sessions trigger compaction, they account for 44.2% of total token consumption." |
| 1 | CompactionBench is repeated-compaction multi-turn tasks | PARTIAL: eight SWE-EVO release tasks, 315 changelog items; authors concede selection, not multi-turn alone, causes repeated compaction; a reviewer notes 21 tasks of existing benchmarks compact at 50% trigger vs 8 here | reply LxMhoMTSn7 pt 1 |
| 2 | APEC design | LOCATED | abstract |
| 3 | cost -25.4%, time -9.6%, better quality | NARROWED: authors attribute cost/accuracy to PEC and latency to asynchrony; APEC costs more than PEC ($16.37 vs $14.75); accuracy gains 1.0-1.7 SE, to be restated as directional | replies |
| 4 | relation to Aggron | CONFIRMED by identity (Aggron cites Liu et al. 2026a) with the baseline-mismatch caveat | Aggron dive |

## Principles
| principle | MI210 | Zen5 | port | consumer |
|---|---|---|---|---|
| progressive append-only indexed summaries after an unchanged prefix | slot KV stays valid; appended block prefill only | saves bandwidth-bound prefill; CF-PB-1 rewrite cost 3.4-15.7 s per pair (per the Aggron dive, @ ac1347f) | S | TOC-CMP-4-PREREG-V2 |
| background summarisation | second concurrent request needs np>=2 (kv-prefix-fork P1) | another CPU quarter | M | async arm of PREREG-V2 |

## Grounding (lane @ 4b428f1)
context-and-token-economy.md TOC-CMP-4 (L76: three arms raw tail, summary, FIFO; MDE 0.10 blocked actions per step, >=30 paired points, Pass^3). The Stage-3 plan's TOC-CMP-4-PREREG-V2 (plan lines 239-242) already contains a "prose-only plus frozen append-only summary arm" (Aggron) and an "async compaction plus next-k judge arm blocked on kv-prefix-fork P1" (Slipstream). What it lacks: any prefix-cache reuse measurement per arm, and a progressive/indexed (segment-granular) form of the append-only arm that is runnable without P1. KPF-22 / M4 (queue-time compaction): unaffected, APEC's asynchrony is per-session background work and not a queue-time trigger.

## Adversarial pass
Reviewer objections visible in the replies: (1) benchmark selection drives the compaction count, not the multi-turn conversion; (2) APEC's accuracy edge is within noise (8.66 points vs about 5.0 SE on GPT-5.6 Sol against Sync-H), authors agreed to "directional"; (3) APEC costs more than PEC (agent keeps generating while a summary is in flight); (4) fixed requirement sequence can mismatch agent state; (5) "no compaction" and fresh-session baselines requested (authors reply no-compaction hits context limit). Hosted frontier models and a hosted prefix cache: transfer to local llama.cpp slots and 27B/35B workers is untested. Everything here is author-side; no independent replication; no PDF.

## Derived-actionables ledger
| id | action | owner | bears on | disposition | reason |
|---|---|---|---|---|---|
| compactionbench-A1 | amend PREREG-V2 per below | context-and-token-economy.md | TOC-CMP-4-PREREG-V2 | task | progressive gain does not need P1; reuse tally is the mechanism metric |
| compactionbench-A2 | run CompactionBench / Copilot traces | context-and-token-economy.md | TOC-CMP-4 | decline | nothing retrievable; frontier harness |
| compactionbench-A3 | change KPF-22-QUEUE-SHARE or M4 | context-and-token-economy.md | KPF-22-QUEUE-SHARE | decline | orthogonal trigger |

## Stage-3 plan effect
**Changed box text: P3 / TOC-CMP-4-PREREG-V2; no change to M4, KPF-22-QUEUE-SHARE or P4.** Proposed exact edit to the TOC-CMP-4-PREREG-V2 line (plan line 242): replace "a prose-only plus frozen append-only summary arm, and an async compaction plus next-k judge arm blocked on kv-prefix-fork P1 (intake-2762#record, intake-2778#record, intake-2761#record, intake-2770#record)" with "a prose-only plus frozen append-only summary arm run in a progressive indexed form (fixed-size segments summarised as they close, each summary appended after the unchanged prefix and never rewritten; not blocked on kv-prefix-fork P1), a per-arm prefix-cache reuse tally (cached prompt tokens over prompt tokens from the slot logs) recorded beside accuracy and cost, and an async compaction plus next-k judge arm blocked on kv-prefix-fork P1 (intake-2762#record, intake-2778#record, intake-2761#record, intake-2770#record, intake-2786#record)". Add intake-2786 and compactionbench-A1 to the P3 "Sources and ledger rows" line. Rationale: the authors' own replies attribute the cost and accuracy gain to progressive summarisation and only latency to asynchrony, so the P1-independent arm captures the testable part; the reuse tally is the mechanism APEC is about and CF-PB-1 already shows rewrites cost 3.4-15.7 s per pair on our CPU.

## Dive-surfaced sources
- t46/compactionbench, ayushnangia/CompactionBench: decline (unrelated namesakes).
- openreview.net/forum?id=NWYYYlWJhJ: re-ingest when the PDF or release is retrievable.

artifact audit: clean
