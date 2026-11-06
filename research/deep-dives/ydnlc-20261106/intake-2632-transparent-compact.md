# intake-2632 — transparent-compact (arXiv 2610.20116v1)

**Dive date**: 2026-11-06 · **Read depth**: FULL · **Source revision**: 2610.20116v1 (2026-10-14)
**Verdict**: dive-verified; the commitment claim is OVERTURNED as stated.

## Method

Deterministic compaction for the Pi coding agent. Every user message and all assistant prose are kept word for
word across earlier compacted spans; tool outputs and reasoning are removed entirely; each tool call becomes a
one-line signature; read/modified files are listed and marked "not in context"; a header declares what was
removed and that retained prose is a record of what was said, not verification. Conversation section capped at
25% of the window (~10 verbatim rounds). Compaction makes **no model call**; recovery is an optional subagent
over the raw session or deterministic list/grep/show. 27 commitment probes in 18 real sessions at a 48k window;
18 synthetic sessions with 17 planted facts.

## Results

- **Planted facts**: 97.8% vs 75.3% (Qwen3.8-27B), 95.1% vs 55.0% (Luna), 93.3% vs 51.5% (Gemma); F(1,17)=860.2,
  p<0.001. Fewer confident wrong answers on all three.
- **Commitments**: vs Pi default summary the difference is +10/+16/+4 points on the lightweight models but
  **−5 on the frontier model and not significant overall** (F(1,26)=2.25, p=0.15). The significant win is against
  pi-vcc (F=9.98, p=0.004). So "beats model-written summaries on commitment" is not supported.
- **Latency**: 0.43 s per compaction vs 167.8 s for a model-written alternative, at 2.7× uncached prompt tokens.
- Public implementation and replication package exist; no independent replication or critique found, and the
  author discloses building the method.

## Limits

Synthetic sessions are ~85% tool output, which this method externalises rather than compresses; testing stops
at ~20 rounds; the 25% cap must be re-expressed against our C=16,384, not the served window.

## Actionables (ledger)

| Action | Owner | Disposition |
|---|---|---|
| Add a `verbatim_manifest` arm to TOC-MP-2: arm-4 pruning plus a declaration header (file manifest marked not-in-context, one-line tool signatures, re-orient block, 25% cap) | context-and-token-economy.md (TOC-MP-2) | immediate (design text) |
| Add a declaration-effect cell to TOC-MP-4: same cleared output, arms 4 vs 6, score whether the agent calls `peek` before answering | context-and-token-economy.md (TOC-MP-4) | probe |
| Do not port the `context_lookup` subagent as the default recovery path | context-and-token-economy.md | decline (subagent only) |
| Record the 0.43 s vs 167.8 s datapoint in the A/B-CTRL rationale | context-and-token-economy.md | knowledge-only |

## Dive-surfaced sources

ARCBench (intake-2631), source-judged compaction (intake-2633), Governance Decay 2606.22528 (wave 2).
