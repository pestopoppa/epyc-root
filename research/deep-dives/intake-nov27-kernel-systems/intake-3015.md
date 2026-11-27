# HoMe: Toward Practical Harness Optimization of Memory Systems for AI Assistants

[Primary source](https://arxiv.org/abs/2611.34624v1) · intake-3015 · 2026-11-27

HoMe varies versioned ReMe harness plugins in a Git DAG under a fixed runtime, with isolated evaluation and memory files committed at every conversation boundary. Diagnosis asks whether needed evidence is in retrieved output, final memory, or source sessions and their mutation diffs, and aggregates supporting case traces across failures. Smoke on deterministically truncated cases precedes formal evaluation; early half of six-candidate budget requires meaningful structural edits. Adaptive sampling mixes loss, staleness, uncertainty, unresolved failures and uniform exploration; compare shared cases or use final independent test, because changing sample aggregates cannot rank candidates directly. Reuse is stochastic (0.6) and permitted from the nearest evaluated ancestor with construction-equivalent code/prompts/config, rerunning query and scoring. Table 1 vs tuned ReMe: held-out LME score 0.888→0.916, raw query tokens 43.9K→17.9K; BEAM-1M 0.650→0.704 with token counts 101.8K→60.4K (BEAM search trained on independent BEAM-100K). Counts do not deduct KV-cache hits; BEAM calls rise 4.5→6.7. Some categories regress. Second BEAM optimization reaches 0.720 at 68.3K; cross-transfer LME→BEAM goes 0.650→0.639 with 62% fewer tokens. Six formal evaluations followed a full baseline, and timing for spot trials excludes baseline and agent overhead. Search cost BEAM 185.2M vs 331.2M raw tokens for MemPro; in these matched runtime experiments MemPro changed only prompts/parameters, although its original design can edit structure. No independent replication found in bounded search. Case winners include date-grouped topic directory, per-file diversity cap, user-action postings, and keyword-based selected lines with recoverable citations and backing text.

Read §§3–5, all main table passages and Figure 1–3 captions, Appendix A.4/A.6.3 and trace conclusion. The full trace, per-category tables, sampler details, system prompts and references not read.

## Evidence

- Capture construction history per session to localize omission, maintenance damage, retrieval miss and answer misuse from trajectory evidence. [§3.2, session-level versioning (#S3.SS2)](https://arxiv.org/html/2611.34624v1)
- On held-out LongMemEval-S, HoMe raised score from 0.888 to 0.916 while cutting query-stage token counts from 43.9K to 17.9K. [§4.2.1, main results (#S4.SS2.SSS1)](https://arxiv.org/html/2611.34624v1)

## Scope and local transfer



Trajectory attribution and construction-equivalent snapshot reuse are closest to the orchestration harness loop and active context/token-economy work. A defensible first transfer uses fixed case IDs, compare-on-common-cases, stable construction dependency fingerprints, and small held-out evaluation, then checks evidence coverage and source diversity without launching a complete self-optimizer. CPU supports provenance/diff replay and cold memory construction cost may dominate; MI210 batch/diversify retrieval comparisons with actual warm-prefix tokens, decode work and wall time, because uncached raw token count is not device cost.

M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases. Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons.

## Sources surfaced

- https://github.com/agentscope-ai/ReMe — Author-linked implementation companion and separate artifact; inspect whether reproducibility plugins, trial DAG, per-session checkpointing and targeted retrieval are exposed. URL absent from lane index.
- https://arxiv.org/abs/2606.00619 — MemPro primary source checks if and when its nominal structural editing produced gains; exact ID absent from lane index.
