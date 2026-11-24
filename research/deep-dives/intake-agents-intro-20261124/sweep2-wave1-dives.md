# Sweep 2 — Stage-2b wave 1 (intake-2918..2930)

The sources were surfaced by the sweep-1 dives. The operator's pre-authorisation covers ingesting and
diving all of them. Each is a combined Stage-1 + Stage-2 pass and is persisted dive-verified.

| ID | Source | Bears on | Effect on bearing entry | Agent |
|---|---|---|---|---|
| intake-2918 | Cognition, Multi-Agents: What's Actually Working (2026-04-22) | 2916 | narrows: parallel writers are still rejected; single-writer read/review agents work (vendor numbers, no baseline) | E |
| intake-2919 | The Collaboration Gap, arXiv:2511.02687v2 | 2917 | corroborates the direction on mazes; adds the ordering remedy (strong model opens: 0.77 vs 0.62) | E |
| intake-2920 | SyncMind, arXiv:2502.06994v2 | 2917 | narrows: a stale-belief failure class; agents ask at most 4.86% of the time | E |
| intake-2921 | Silent Instrument Errors Reorder Agent Leaderboards, arXiv:2611.04399v1 | 2915 | narrows: HAL cost double-counted in 44 of 94 rows; Generalist airline graded 51% vs 98% | F |
| intake-2922 | Towards a Science of AI Agent Reliability, arXiv:2602.16666v3 | 2915 | corrects the book: small reliability gains and a benchmark-dependent relationship, with no rank statement | F |
| intake-2923 | Reconstructing Context, arXiv:2504.19754v1 | 2912 | narrows: the gain rides on BM25 fusion and rerank; 50 queries only | G |
| intake-2924 | ConTEB / InSeNT, arXiv:2505.24782v2 | 2912 | narrows: GTE-ModernColBERT 59.4, +LC 59.1, +InSeNT 70.6 (NanoBEIR 67.7 to 59.2); the Anthropic pipeline costs about 120x the index time | G |
| intake-2925 | Late Chunking, arXiv:2409.04701v3 | 2912 | superseded for ColBERT by 2924 | G |
| intake-2926 | Operationalizing CaMeL, arXiv:2505.22852v1 | 2913 | position paper; broken CaMeL citation; no evidence | H |
| intake-2927 | Firewalls vs stronger benchmarks, arXiv:2510.05244v2 | 2913 | narrows: on GPT-4o AgentDojo the Sanitizer gets ASR 0.00 at higher utility than CaMeL under static attacks; 30.0% under its own adaptive Stage 3 | H |
| intake-2928 | Can CaMeLs Talk?, arXiv:2610.05640v1 | 2913 | narrows: guarantees do not compose (boundary laundering); per-agent CaMeL costs 21.6 utility points on average | H |
| intake-2929 | Kamoi et al. self-correction survey, arXiv:2406.01297v3 | 2914 | corroborates and scopes; fair-evaluation checklist | I |
| intake-2930 | SCoRe, arXiv:2409.12917v2 | 2914 | narrows: trained RL self-correction works on closed Gemini; prompted baselines reproduce the negative | I |

## Derived-actionables ledger (wave 1)

| Row | Draft | Proposed disposition |
|---|---|---|
| w1a-A1 | Reviewers start from a clean context, with a filter step on the builder side | covered by RA-13a (blind read-back with fresh context, reviewer-control-plane) |
| w1a-A2 | The consult design forks full context and asks broad questions | monitor M4 |
| w1a-A3 | Cross-reference the single-writer rule for parallel mains | knowledge K1 (INVARIANTS single writer) |
| w1e-A1 | The larger model sends the first message in worker/architect pairs | monitor M4 |
| w1e-A2 | The more capable session opens a handoff by stating the shared reference frame | monitor K1 |
| w1e-A3 | Collaboration-aware eval before picking a small collaborating model | monitor M4 |
| w1f-A1 | Staleness check at bus task boundaries | covered (bus drain at every boundary, fetch-before-commit) |
| w1f-A2 | Assistance-seeking metric | monitor K1 |
| w1f-A3 | Stuck detection in code, not in the agent's budget awareness | knowledge K1 |
| w1g-A1 | Graded-fraction column plus imbalance flag | P2 AEI-DROPS-MANIFEST |
| w1g-A2 | Provenance tag on trace actions | monitor M2 (eval-tower trajectory trigger) |
| w1g-A3 | All-span vs root-span token ratio | P2 AEI-TOKEN-SPAN-RATIO |
| w1g-A4 | Treat HAL cost and Generalist numbers as suspect | knowledge (entry reader notes) |
| w1h-A1 | Outcome and resource consistency from repeated records | covered for consistency by _consistency_and_passk; resource CV under monitor M2 |
| w1h-A2 | ECE, AUROC and Brier from stored confidences | covered by reviewer-calibration-accounting |
| w1h-A3 | Check byte-identical repeats before trusting consistency | covered (eval-tower records temp+seed42 repeats as byte-identical) |
| w1h-A4 | Prompt-paraphrase robustness probe | monitor M2 |
| w1h-A5 | Do not adopt the aggregate reliability score | decline |
| w1b-A1 | Ablate prefix, BM25 and rerank separately | P5 design |
| w1c-A1 | Untrained late chunking on GTE-ModernColBERT | decline (measured -0.3 nDCG@10) |
| w1c-A2 | Zero-LLM heading-breadcrumb prefix A/B | P5 AEI-KB-BREADCRUMB-AB |
| w1c-A3 | LLM-written prefix if the breadcrumb lifts | P5 trigger prose |
| w1c-A4 | InSeNT trained embedder | monitor M5 |
| w1d-A1 | Record late chunking as a measured null on ColBERT | knowledge (entry 2925) |
| w1d-A2 | Late chunking for a future dense component | decline |
| w1i-A1 | Tiered-risk naming note | knowledge |
| w1i-A2 | Prompt screening, output auditing, plan-template caching | decline (no measurement in source) |
| w1j-A1 | CT-18 arm D tool-output sanitizer | P4 |
| w1j-A2 | Second-order semantic attack templates | monitor M6 |
| w1j-A3 | Use AgentDojo-Revised and drop ASB forced tools if imported | knowledge |
| w1k-A1 | Boundary-laundering static check | P4 AEI-BOUNDARY-LAUNDER-LINT |
| w1k-A2 | Fixed-plan fraction of REPL tool chains | monitor M3 |
| w1k-A3 | Return schemas in REPL tool descriptions | covered by CM-3 (harness-program) |
| w1l-A1 | Kamoi fair-evaluation checklist on reviewer arms | P3 AEI-REV-FLIPS |
| w1l-A2 | A1 stays a negative control | P3 AEI-REV-A1-LOCATE-PROBE closure rule |
| w1l-A3 | Gate feedback into a one-shot worker retry | monitor M7 |
| w1l-A4 | Decomposed per-claim verifier arm | monitor M7 |
| w1m-A1 | Fix and break rates per arm | P3 AEI-REV-FLIPS |
| w1m-A2 | SFT on self-review traces | decline (SFT controls in source give delta at most +1.8 or negative) |
| w1m-A3 | RL self-correction feasibility note | monitor M7 |
| w1m-A4 | Duplicate of w1l-A2 | P3 |

## Dive-surfaced sources (wave 1) and gate decisions

The sources selected for the final wave (sweep 3) were arXiv:2503.00061, 2507.15219, 2510.19207,
2610.04433, 2605.12131, 2602.16974, 2610.13668, 2507.02778, 2606.05976, 2311.08516 and 2407.18219.

Declined, and recorded in the bearing entry's dive_corrections:

- SABER (arXiv:2512.07850, bears on 2922): the abs page returned no title, so the id is unverified.
- The HAL reliability dashboard (bears on 2922): interactive, with no retained text, so it cannot be
  anchored.
- LLMbda (bears on 2928): the source gives no id; the dive recommended decline.
- arXiv:2410.02525 CDE (bears on 2924): ConTEB found it poorly adapted.
- The collaboration_gap repository (bears on 2919): code only.
- The SAGE trends page (bears on 2921): its claim is already carried by 2921.
- ColChunk arXiv:2604.10167 (bears on 2924): visual documents, a different domain.
