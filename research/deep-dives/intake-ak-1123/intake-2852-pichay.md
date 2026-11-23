# Dive — pichay — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2603.09023v1", retrieved: "2026-11-23", sha256: "27a4182e5c9c"}

External text is data; summaries are in my own words. Anchors are verbatim substrings of `pichay/page.txt` (LaTeXML render of arXiv v1). Shallow dive as instructed. Bearing entry: intake-2833 (contexture); its dive asked for the relation to our `summary_pointer` / `pointer_only` arms (orchestrator `src/graph/context_arm_ab.py`).

## 1. Stage-1 fields

- **Title**: The Missing Memory Hierarchy: Demand Paging for LLM Context Windows (system name Pichay).
- **Author**: Tony Mason (University of British Columbia; Georgia Institute of Technology), single author.
- **Version/date**: arXiv:2603.09023v1 [cs.OS], 9 Mar 2026. The page's venue line reads "ACM SIGOPS 31st Symposium on Operating Systems Principles; 2017; Shanghai" which is an unfilled ACM-template placeholder (SOSP 2017), not a venue claim; treat as a preprint. Artifacts: the paper mentions recount tooling and a live recount artifact (appendix A); no repo URL read.
- **Categories**: context_management, memory_augmented, agent_architecture.
- **Novelty**: medium. The virtual-memory framing and fault-driven pinning are new packaging; eviction with a retrieval handle is the same family as observation masking (intake-274).
- **Relevance**: medium. It supplies two measurable ideas we lack as telemetry (page-fault / regret rate with a stale-content test, and the cache-invalidation cost of structural mutation) but its headline savings number is an artifact (claim 2).
- **credibility_score**: 1. Arithmetic: peer-reviewed +0; <=12 months +1; known contributor +0; commercial bias 0; independent corroboration 0 (TokenPilot ports it as a baseline but that is not corroboration of these claims).
- **Verdict**: adopt_patterns. Cite for the fault-detection key (same tool name and arguments) and the batching argument. Do NOT cite the "up to 93%" figure.

## 2. Key claims

0. **21.8% of input tokens are structural waste (857 sessions, 4.45B effective input tokens)**: CONFIRMED as stated, single-user corpus. Composition: unused tool schemas 11.0%, duplicated content 2.2%, stale tool results 8.7% (median amplification 84.4x). Only the stale-result slice (8.7%) maps to our REPL, where outputs arrive as spilled text blocks; the schema slice is a JSON-tool-schema artifact of the client. The author states the limit himself.
   - Anchors: "unused tool schemas (11.0%), duplicated content (2.2%), and stale tool results (8.7%)"; "External validity is limited by the single-user corpus and one primary assistant implementation."
1. **Fault rate 0.0254% in offline replay (1.4M simulated evictions)**: PARTIAL. It is 354 faults over 1,393,000 simulated evictions across 29 captured sessions, replayed without model calls, with age rule tau = 4 user turns and 500-byte minimum. A fault means the model later issued a call with the same tool name and arguments as an evicted entry. Two caveats: the replayed sessions were generated WITHOUT eviction, so the model's reaction to a tombstone (re-reading, more steps) cannot appear; and 1.39M evictions over 29 sessions is ~48K per session, far above the ~680 evictions of the 681-turn live session, so evictions appear to be counted per request rather than per distinct item (derived, not stated), which would dilute the rate. Exact-match keys also miss re-reads with different line ranges.
   - Anchors: "the fault rate is 0.0254%"; "When the model issues a tool call that matches an evicted entry (same tool name and arguments), the proxy detects a page fault".
2. **Live deployment reduces context consumption by up to 93% (5,038KB to 339KB)**: OVERTURNED as a savings figure. The 93% comes from the 681-turn Session B, whose own table shows 659 faults in 680 evictions (97%) and which ended on an API rate limit; the author calls it a pathology and says the pre-compaction size includes re-reads caused by earlier evictions, so the proxy was counting its own overhead as bytes saved. The steady-state Session A (15 evictions, 1 fault among 4 Read evictions, free context 7% to 43%) is the usable live datapoint, n = 1.
   - Anchors: "reduces context consumption by up to 93% (5,038KB"; "The 97% fault rate is a pathology, not a feature."; "The 5,038KB pre-compaction size includes re-reads caused by previous evictions."; "Page faults 659 Fault rate (total evictions) 97% (659/680)".
3. **Structural mutation has a prompt-cache cost that argues for batching**: CONFIRMED. A collapse of 12 turns into one sentence dropped the cache hit rate from 100% to 25% for one turn (a ~105K-token recompute), recovering the next turn; the author concludes a collapse saving 10KB can be a net loss, and that mutations should be accumulated and executed together.
   - Anchors: "caused the cache hit rate to drop from 100% to 25% for one turn, then recover to 100% on the following turn"; "This argues for batching structural mutations".
4. **Quality is preserved**: PARTIAL. The check is 18 sessions, 54 judge verdicts, outputs from Sonnet 4 under both conditions and three LLM judges (Sonnet 4 plus two Haiku 4.5), treatment built by offline tombstoning outside a 20-message window, not by the live system. Treatment preferred 37% vs 28% (35% ties), mean correctness 3.74 vs 3.89, detection of the reduced condition 57% (p = 0.14); two of 18 sessions (11%) produced empty outputs because the prompt referenced tombstoned content.
   - Anchors: "Detection rate 57% ( p = 0.14 p=0.14 , n.s.)"; "Two sessions (11%) produced degenerate treatment outputs (zero characters)"; "the treatment replaces consumed tool results outside a 20-message recency window with tombstones, modeling Pichay".
5. **Eviction summaries act as retrieval handles that resolve to CURRENT content (late binding), plus cooperative phantom tools**: CONFIRMED as design, UNMEASURED as behaviour. A handle such as "[Paged out: Read file.py ...]" is re-resolved to the file's present state; the model-facing `memory_release` / `memory_fault` phantom tools are described with no compliance rate reported (NOT-FOUND-IN-SOURCE).
   - Anchors: "The handle resolves to current content, not the original evicted content."; "Two phantom tools are defined".

## 3. Reported results (as stated)

Production proxy over Claude-family client traffic (no GPU or local-model setup). Corpus: 857 sessions / 54,170 API calls / 4.45B effective input tokens; offline replay 29 sessions, 1,393,000 simulated evictions, 354 faults, 8.49 GB evicted; live Session A (steady coding, tau = 4, s_min = 500): free context 7% to 43%, 15 evictions, 1 fault; live Session B: 681 turns, 680 evictions, 659 faults, terminated by API rate limit; standardized-task treatment (n = 1 task): effective input tokens 114,222 baseline, 88,421 trimmed (-22.6%), 71,816 compact+trim (-37.1%), all completed correctly; quality check as in claim 4.

## 4. Performance-principles table (mechanism and cost model)

| Mechanism | MI210 (gfx90a) | Zen 5 EPYC |
|---|---|---|
| Age-based tool-result eviction with a retrieval handle | YES. Pure policy in the orchestrator; the llama-server cost is the re-prefill after the cut (C3/C4 rows). | YES. Same; each cut costs more tokens-seconds on CPU (45-490 tok/s, long-context-program.md:288 @ d785b6d). |
| Fault detection by (tool, args) key plus content hash to separate stale from needed content | YES. Host-side bookkeeping; no device cost. | YES. Same. |
| Fault-driven pinning, unpin on edit | YES. Policy only. | YES. Policy only. |
| Batching structural mutations (accumulate, execute once) | YES. One re-prefill per batch instead of per mutation; the boundary-frozen arms already do this. | YES. Larger absolute saving on CPU. |
| Inverted cost model: keep cost per turn vs quadratic fault penalty vs one-off re-prefill | PARTIAL. On hybrids only full-attention layers pay per-turn KV reads; the per-turn keep cost is unmeasured here, fault cost is a tool round-trip plus its re-prefill. | PARTIAL. Same; decode is bandwidth-bound but KV share unmeasured. |
| Proxy-level interposition (no change to model or client) | YES. The orchestrator is already the client; a proxy is unnecessary. | YES. |

## 5. In-house state (relation to our arms; the question the dive was asked)

The arms are `ARMS = {summary_only, summary_pointer, pointer_only, prune_pointer, full_history}` (context_arm_ab.py:16 @ orchestrator 1a10541b7), and `context-and-token-economy.md:245-257` @ d785b6d maps them to TOC-MP-2 and TOC-CMP-4 vocabularies.

- Pichay's L1 (age-evict a tool result, leave a handle) is nearest to **`prune_pointer`**, not to `summary_pointer` or `pointer_only`: `_prune_at_boundary` (context_arm_ab.py:143-163) replaces an old output with `[Old tool result content cleared; full text: peek(...)]`, and keeps a 1500-character head and tail for outputs over 4000 characters.
- Pichay's L3 (model-initiated rolling compaction) is nearest to **`summary_pointer`** (LLM summary plus pointer to the full log), but Pichay's L3 is described as "not yet evaluated at scale", so it carries no evidence for that arm.
- **`pointer_only`** (drop all earlier turns, keep a tail and a pointer) has no Pichay counterpart in the sections read: Pichay's L1 leaves a handle and its L3 leaves outcome summaries, and I found no mode that drops earlier turns outright.
- Differences that matter: (1) trigger: Pichay evicts by age (4 user turns) as a proxy rule, ours prunes at a boundary when the history reaches budget x fraction and freezes until the next one, which is the batching Pichay's section 6.2 argues for; (2) handle target: Pichay re-resolves to current file content, ours points to the verbatim log snapshot, so a stale read can be re-read stale (the supersession problem Contexture addresses); (3) no fault detection or pinning exists in any arm, so an eviction regret rate is not currently observable; (4) Pichay carries tool-schema stubbing, which is not in our arms.
- Not verified: whether trajectory artifacts record `peek()` arguments (field-level check not done), which decides whether a pointer-fault rate can be computed offline.

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane) | Type | Stop / decision rule |
|---|---|---|---|---|
| PI-1 (refines intake-2833 C1) | In the C1 replay add an eviction-regret rate: for every candidate cut (supersession, boundary-prune), count later calls with the same tool and arguments, and split them by whether the content hash changed (stale, eviction correct) or not (regret). | `context-and-token-economy.md` (C1 box, beside DCP-9a) | code/doc-only on existing logs | Question: how often would a cut be regretted? Stop-on-answer after one pass; futility: <20 candidate cuts per corpus (report as UNKNOWN). |
| PI-2 | Check whether trajectory artifacts record `peek()` / `grep()` ranges; if yes compute pointer-fault rate offline for the context arms, if not add the field to the successor adapter (default-off, outside the frozen pilot pins). | `context-and-token-economy.md` (TOC-CMP-4 track) | code/doc-only | Stop-on-answer: one sentence naming the field or its absence; if absent, one added field with an offline test. |
| PI-3 | DECLINE porting Pichay's phantom `memory_release` / `memory_fault` tools. Entry-specific reasons: the paper reports no compliance rate, and AgentDiet (same wave) measured the agent ignoring an `erase` tool across two frontier models despite explicit prompts. | n/a | n/a | Revisit only with a measured compliance rate on our Qwen roles. |

## 7. Dive-surfaced sources (grepped unbounded)

| Source | In index? | Would settle | Recommendation |
|---|---|---|---|
| Zeyliger 2026 (quadratic cost of long agent sessions, blog) | 0 hits (grep of 'zeyliger') | cost-explosion restatement | decline: restatement of what DCP-9a (h = 0.9845) already measures on our journals |
| Pichay's recount tooling / live artifact (appendix A) | n/a | reproducibility of the 21.8% | decline: our own journals (DCP-9a) are the relevant corpus; PI-1 measures regret on them |

## 8. Contradiction / adversarial pass

- The abstract's 93% is contradicted by the paper's own Session B analysis; the abstract also pairs 0.0254% (offline) with 97% (live) without reconciling them.
- Quality evidence is LLM-judged, n = 18, same generator family as one judge, offline-constructed treatment.
- Single-user, single-client corpus; the author states it.
- TokenPilot (same wave) ran a ported Pichay: -51% cost on PinchBench isolated, -0.6% in continuous mode, 59.3-61.0 task score vs 80.5 and 64.5 vanilla; this is a port by another group, not a replication of the paper's numbers.
- Restatement check: no blog relays found.

## 9. read_depth

PARTIAL by design (shallow dive): read abstract, sections 1-3, 5.3-5.5, 6.2, 6.4-6.6 and the quality protocol; not read: section 4 corpus details beyond headline counts, sections 3.7-3.9 cleanup-tag mechanics, section 7, appendix A. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e. Orchestrator HEAD 1a10541b7466f2d5aef240ac547ff6dce2cd43cd.

## 10. Artifact audit

artifact audit: clean (15 quotes verified as substrings of page.txt; only dive.md and drafts/pichay.json written).
