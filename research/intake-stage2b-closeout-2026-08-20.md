# Stage-2 / Stage-2b close-out ledger — 2026-08-20

Session mandate: 14 operator-submitted sources (10 URLs + 4 pasted write-ups).
Index state at close: **1,207 entries**, validator exit 0.
Stage-1 minted intake-1172..1195 (24). Stage-2b minted **intake-1196..1211 (16)**, persisted
directly as `dive-verified`/`dive-overturned` per the Stage-2b contract.

This file exists because `tmp/*` is gitignored (`.gitignore:33`) — the same durability defect
recorded as D4 and D11. A close-out ledger held only in scratch is not a close-out.

## Why this ledger exists

The Stage-2 gate requires that **every dive-surfaced source is either ingested or explicitly
declined**. Stage-2b was the terminal dive pass and surfaced a further ~40 sources. They are
enumerated below with a disposition each. Nothing is silently dropped.

## Operator steering applied

The operator overruled three Tier-3 declines with a general doctrine:

> "large open-source repos have all sorts of commitment inertia. We can afford to be much mroe nimble"

**Result: the doctrine was vindicated, and it is worth recording how.** Three of the four
highest-value findings in this batch came from artifacts that are unmerged or not public at all:

| Artifact | Status | What it gave us |
|---|---|---|
| SGLang RFC #27574 | open, unmerged | A *hint* vocabulary (Pin/Retain/Prefetch/Demote/Share) that fits our `id_slot` channel better than the merged design does |
| cordis PR #39 | open since 2026-08-06 | The maintainer's own statement of the correct disposal invariants — the cross-check on DeepSeek's patch |
| cordis PR #41 | open, unmerged | The design the vendored fork ports as ledger item 15 |
| deepseek-harness/cordis | **not public at all** (404) | Reached via the vendored copy inside the harness; yielded the real 18-item diff |

## A — Ingested in Stage-2b (16)

| ID | Source | Verification |
|---|---|---|
| intake-1196 | KVFlow, arXiv:2507.07400 | **dive-overturned** |
| intake-1197 | AIDev dataset, arXiv:2602.09185 | dive-verified |
| intake-1198 | AI Teammates companion, arXiv:2507.15003 | dive-verified |
| intake-1199 | Context Engineering in OSS, arXiv:2510.21413 | dive-verified |
| intake-1200 | HOBBIT, arXiv:2411.01433 | dive-verified |
| intake-1201 | Nygard, Documenting Architecture Decisions | dive-verified |
| intake-1202 | Deep JIT Inconsistency Detection, arXiv:2010.01625 | dive-verified |
| intake-1203 | Learning to Update NL Comments, arXiv:2004.12169 | dive-verified |
| intake-1204 | @earendil-works/pi-ai (npm) | dive-verified |
| intake-1205 | Agent-Context-File-Analysis replication package | dive-verified |
| intake-1206 | llm-verifier 0.2.0 (PyPI) | dive-verified |
| intake-1207 | SGLang Rust tree-core cluster (PR #32710 et al.) | dive-verified |
| intake-1208 | cordiverse/cordis | dive-verified |
| intake-1209 | @deepseek-ai/cordis (vendored) | dive-verified |
| intake-1210 | flash-attention `hopper/` (FA3) | dive-verified |
| intake-1211 | PyTorch ROCm wheel index | dive-verified |

## B — Surfaced by Stage-2b, DEFERRED to a next-session expansion queue

Ranked. These are **not declines** — they are named, ranked and carried, because the expansion
cap (10) was already exhausted in Stage 1 and Stage-2b is terminal. Each names what it would settle.

| # | Source | Would settle | Bearing entry |
|---|---|---|---|
| 1 | arXiv:2606.24429 (Khosravani & Mockus) | Measures a **~79% PR-census miss rate** for commit-deployed agents and a 30× bot-lookup recall gap — the independent evidence that our AIDev absence is a *class*, not an exception | intake-1197 |
| 2 | arXiv:2601.21473 ScaleSim | Same group's follow-up; the title ("Invocation Distance-Based") suggests **the authors replaced steps-to-execution**. If so, that is a stronger argument against porting KVFlow than anything in KVFlow | intake-1196 |
| 3 | arXiv:2604.27333 (ADR template comparison) | Whether a **richer rationale schema measurably hurts**. Headline says the leaner Nygard template beat MADR; N and effect size are not in the abstract | intake-1201 |
| 4 | SGLang issue #27574 (RFC, open) | Whether upstream is converging on a **hint vocabulary** rather than a step graph — a materially better fit for our `id_slot` channel | intake-1196, intake-1207 |
| 5 | github.com/PanZaifeng/KVFlow | The eviction comparator **in code** (the paper describes it in prose only) — heap key vs full re-sort, tie-breaking, incremental min-propagation | intake-1196 |
| 6 | arXiv:2602.07609 (LLMs detecting ADR violations) | 980 ADRs / 109 repos — the nearest existing analogue to "can a ledger be auto-checked against what it describes" | intake-1201, intake-1202 |
| 7 | ROCm/composable_kernel @ c56c6750 | The **only gfx90a-named** FlashAttention route in the whole FA dependency chain | intake-1210 |
| 8 | github.com/earendil-works/pi | MIT, 94k stars, never rowed as an HS-4 candidate; the one consumer where `samplingParams` is already zero-code config | intake-1204 |
| 9 | dshbox/cordis-rs | Whether the disposal-invariant pattern survives leaving TypeScript (it appears to, with a stronger check-under-the-drain-lock discipline) | intake-1209 |
| 10 | arXiv:2507.08671 LLMCup | Current ceiling on LLM-based comment updating — whether the 18.4% figure is a 2020 artifact or a task property | intake-1203 |
| 11 | lmsys HiCache redesign blog (2025-09-10) | Whether the failure mode KVFlow measured at v0.4.4 was structurally removed or merely moved | intake-1196 |
| 12 | hao-li/AgentREADMEs (HF dataset) | Blob-pinned file **content** (`content_commit_sha`) the GitHub CSVs lack; also confirms the licence absence a second way | intake-1205 |
| 13 | arXiv:2512.19883 / arXiv:2306.06347 | Successor operating points for just-in-time inconsistency detection | intake-1202 |
| 14 | arXiv:2604.03826 (ADR context strategies) | How much falsification lineage to carry forward — their answer is 3–5 prior records, not all of it | intake-1201 |
| 15 | ROCm 7.x supported-GPU matrix | **Whether gfx90a survives into ROCm 7.x.** Gates every escape from the torch 2.5.1 ceiling | intake-1211 |

## C — DECLINED, with reasons

| Source | Reason |
|---|---|
| IEEE Access DOI 10.1109/ACCESS.2023.3287654 | Wanted, but **HTTP 418** on the PDF; abstract-level only. Two search-engine figures ("6.03 ADRs/repo", "<2% exceed 25") are recorded **UNVERIFIED and must not be cited**. Re-attempt only via an open-access route |
| joelparkerhenderson/architecture-decision-record | Low priority — the MADR changelog already supplies the field-survival signal from a *maintained* spec |
| `raw_datasets/` inside intake-1205 | A **sub-artifact** of an entry we hold, not a separate source. Named because it is the only place the pre-attrition frame exists |
| llm-verifier 0.1.0 sdist | Only dates the defect; no decision turns on it |
| llm-as-a-verifier issues #5/#10/#14 | **Cite, do not ingest** — they are the corroboration for intake-1206's degradation claims, not a source in their own right |
| PyPI `triton-rocm` (3.0.0rc1) | A stale name-collision hazard, fully documented inside intake-1211. No entry needed |
| `@mariozechner/pi-ai`, pi-agent-core, openai npm | Corroborating reads already folded into intake-1204's fork-topology finding |
| PR #7568, models.md, cordis THIRD_PARTY_NOTICES | Sub-artifacts of entries we hold; quoted and anchored in place |
| davetha/mi210-llm-stack | Surfaced from a **search-result title only**; not fetched, credibility unassessed. A lead, not a source |
| AMD wheel-variant article | Would tell us whether `+rocmX.Y` is being superseded by PEP-771 wheel variants. Low urgency — our reading method works today |
| `flash_attn/cute/` (FA4) | CuTeDSL, NVIDIA-only; **further** from us than FA3, not closer |
| InferCept / Autellix / RAGCache / CachedAttention / Pensieve | Five at once from one related-work section. RAGCache + CachedAttention now carry KVFlow's transfer-beats-recompute claim in the version of record, so they are the place that measurement actually lives — worth one combined entry later, not five now |
| Live HTTP request confirming the pi-ai / llm-verifier wire behaviour | **Not a reading task.** Belongs to whichever integration task is authorised; this session holds no inference mandate. Recorded so the gap stays visible: **nobody in either chain has observed an HTTP body** |

## D — Gate status

- [x] Every Stage-1 preliminary actionable carried
- [x] Every dive-ledger row dispositioned
- [x] Every steering-ledger row (7) planned or declined
- [x] No unverified quote promoted (`stage1-unverified` entries remain unquotable)
- [x] Every dive-surfaced source ingested (A), deferred-and-ranked (B), or declined with reason (C)
- [x] Index validator exit 0 at 1,207 entries

**Stage 2 is closed. Stage 3 (plan mode) may begin.**

## E — What Stage 3 must re-examine

Per the operator's nimbleness doctrine, **every posture built on "unmerged upstream" reasoning is
re-openable**, and three are named explicitly: intake-1191, intake-1185, and the SGLang cluster now
filed as intake-1207. The doctrine's own evidence is in the table at the top of this file.

14 defects are carried as D1–D14 in `.research-session.json`. **D13 is a recurrence** — intake-1186's
HS-4 row has now gone un-applied across two consecutive passes with an unchanged blocker, which by
the CLAUDE.md recurrence check is proof it was never blocked. It goes first.
