# Dive: Bridging the Gap: Position-Independent Cache Reuse for Hybrid SSM-Attention Architectures (intake-2785, Stage-2b wave 3)

- Source version read: NeurIPS 2026 poster page abstract (Poster Wed Dec 9 2026, Hall 1-4 #S1508); OpenReview id SZ24HRIAMK
- read_depth: PARTIAL. Only the abstract (about 2.9 kB of page text) was readable. The OpenReview PDF returns HTTP 403 (challenge) to curl; no arXiv version found by title. Not read: method, models, datasets, baselines, accuracy numbers, ablations, code.
- lane_head: 4b428f15153d0a32b37e6302849691b2212a49ab
- Entry: novelty medium, relevance high, verdict worth_investigating, credibility null (abstract only), bears_on intake-2774

## Namesake or same work?
Namesake, from the text available. Evidence:
| | arXiv 2607.01299v3 (intake-2774) | NeurIPS poster 152513 (this) |
|---|---|---|
| Authors | Yifei Liu, Juntong Wu, Yang Liu, Junhao Hu, Minghao Li, ... (Xiaohongshu, PKU, SJTU) | Weikang Wang, Xin Zhou, Haiyang Liu, Lei Wang, Jun Liu, Weifeng Zhang |
| Venue | SIGOPS ATC 2026 | NeurIPS 2026 poster |
| LA-layer mechanism | cache the segment-cumulative transition operator per segment, constant-time state composition | "residual state propagation and online decay correction", recompute minimal boundary tokens |
| Attention-layer mechanism | small seam window propagates hidden states, recompute cross-segment attention | not stated in abstract |
| Parallelism | segment parallelism across instances | parallel recomputation pipeline using linear superposition of SSM |
| Headline | TTFT 3.25x average, QPS 1.66x vs Prefix Cache, 1.71-point quality gap | 2x TTFT, "highly competitive accuracy" |
The arXiv text contains zero occurrences of "superposition", "residual state", "decay correction" or "Weikang". Both claim to be "the first" PIC framework for hybrids, which cannot both hold. The shared name and problem make concurrent independent work (or a different lineage) the likeliest explanation; a revision of one into the other is not supported by any text we have.

## Claim verification (abstract-level only)
| # | claim | verdict | passage |
|---|---|---|---|
| 0 | SSM coarse-grained caching invalidates adjacent attention hits | NOT CHECKABLE beyond abstract; located | "SSMs are always restricted to coarse-grained block- or request-level reuse" |
| 1 | residual state propagation + online decay correction + minimal boundary recompute | located, no detail | "We introduce residual state propagation and online decay correction" |
| 2 | 2x TTFT, competitive accuracy | located, no models/datasets/baselines/numbers | "HyPIC achieves a 2$\times$ speedup in time-to-first-token (TTFT) ..." |
| 3 | different work from 2774 | CONFIRMED by authors/mechanism/numbers | see table |

## Principles (abstract-level; cannot assess beyond)
| principle | MI210 | Zen5 | port | consumer |
|---|---|---|---|---|
| residual state propagation plus online decay correction with boundary-token recompute | unknown; Gated DeltaNet is a delta-rule affine state, not pure decay, so a decay correction may not carry (need the paper) | unknown | L | KPF-62-P3-SKELETON, already covered by the (T_C,S) compose from intake-2774/2783 |
| linear superposition to parallelise recompute | holds for GDN chunks given the segment transition; same property as the compose already planned | chunk-parallel prefill across quarters = KPF-60-LPT-MODEL | M | KPF-60-LPT-MODEL |

## Grounding
kv-cache-program.md:L583 @ 4b428f1 (KPF-62-P3-SKELETON) already builds the hybrid affine-state phase and carries the drift-curve gate to phase 0; P4 boxes KPF-62-DRIFT-PRIORS and KPF-60-LPT-MODEL already take intake-2773/2774/2783 priors. The poster adds nothing measurable.

## Adversarial pass
Not run (no text to attack; one title search by the intake step found no arXiv version). Note that "online decay correction" suggests an SSM with scalar decay (Mamba-2 style); applicability to Gated DeltaNet is unestablished.

## Derived-actionables ledger
| id | action | owner | bears on | disposition | reason |
|---|---|---|---|---|---|
| neurips-152513-A1 | M2 monitor clause: re-fetch SZ24HRIAMK or an arXiv version; ingest-and-dive only if it reports a GDN result or code | kv-cache-program.md | KPF-62-P3-SKELETON | task | zero compute; abstract-only today |
| neurips-152513-A2 | poster-derived experiment box | kv-cache-program.md | KPF-62-DRIFT-PRIORS | decline | nothing measurable readable; drift priors already carried |

## Stage-3 plan effect
**Monitor change (M2), no new box.** Proposed exact addition to the M2 text in `handoffs/active/kv-cache-program.md` (end of the existing paragraph, before the final period): "; re-fetch the NeurIPS 2026 poster 'Bridging the Gap' (OpenReview SZ24HRIAMK, intake-2785#record) when the PDF or an arXiv version is retrievable, and ingest-and-dive it only if it reports a Gated-DeltaNet model result, a drift or KLD number, or code". P3/P4 box texts unchanged.

## Dive-surfaced sources
- https://openreview.net/forum?id=SZ24HRIAMK: ingest-and-dive when retrievable (challenge-gated today).
- arXiv:2607.01299 (intake-2774): already indexed; the comparison target.

artifact audit: clean
