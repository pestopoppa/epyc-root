# intake-2630 — Benchmarks Are Surprisingly Compaction-Friendly (arXiv 2610.31778v1)

**Dive date**: 2026-11-06 · **Read depth**: FULL · **Source revision**: 2610.31778v1 (2026-10-22)
**Verdict**: dive-verified; claims 0 and 1 narrowed.

## Method

Fixed scaffold **OpenCode**, five compaction strategies implemented inside it, three long-horizon benchmarks
(PaperBench, ProgramBench, PostTrainBench). Threshold grid 160K–380K; strategies compared at a fixed 160K.
Four models appear in §3.1 (Opus 4.6, GPT-5.3-Codex, GPT-5.4, Gemini 3.1 Pro Preview); Gemini drops out of the
headline because it rarely compacted, so the abstract's "three frontier models" is a presentation choice.

## Results

- For the two 1M-context models, accuracy is similar across thresholds — **but the sweep covers only 16–38% of
  the window**, so it does not test the scaffold-default regime. GPT-5.3-Codex (smallest window) goes 0.38→~0.60
  on PaperBench between 160K and 260K; PostTrainBench is inconclusive by the authors' wording.
- **No compaction method beats default self-summarisation.** Discarding more content costs some models up to 20
  points; lossless filesystem offloading *lowered* GPT-5.3-Codex from 0.38 to 0.24.
- Rule loss: on ProgramBench the first summary drops ~one third of the three anti-cheating rules on average
  (0.92 categories), 1.93 by the 10th compaction, 2.65 by the 30th. The mean is Codex-dominated (2.73 vs 1.76 vs
  0.51).
- Real sessions (SWE-chat, 44 sessions, 269 constraints): 81% preserved overall, but **process instructions lost
  35.9%** and **scope exclusions 36.8%** vs feature requirements 6.2% — "how to work" and "don't touch X" are
  exactly what our governance depends on.
- Thesis confirmed: these benchmarks are compaction-friendly because the objective is fixed and progress lives
  on disk; what cannot be recovered is the constraint that exists nowhere else.

## EPYC relevance

The scaffold is the one we run, but our OpenCode is configured `compaction: {"auto": false, "prune": false}`
(`harness/opencode-plugin/config/opencode.jsonc.template:73`), so these threshold findings apply to the
orchestrator summary path, not to the CLI session.

## Actionables (ledger)

| Action | Owner | Disposition |
|---|---|---|
| Add a rule-retention probe over our own folding summaries, using the paper's judge shape | context-and-token-economy.md | probe |
| Add a compaction-damage arm to agentic acceptance (forced low budget vs control) | benchmark-suites.md (CJ-4) | trigger |
| Record the harness-identity fact so nobody reads "thresholds don't matter" as our safety | harness-program.md | knowledge-only |
| Decline porting the five strategies / retuning thresholds | context-and-token-economy.md | decline |

## Dive-surfaced sources

Zahn & Chana (2026) compounding loss; Wang et al. (2026) constraint-loss baseline; Baumann et al. 2026 SWE-chat
(ingested wave 2 as intake-2637); Goldman et al. (2024) information-scope framing.
