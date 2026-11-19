# intake-2636 — Governance Decay (arXiv 2606.22528v2)

**Dive date**: 2026-11-06 · **Read depth**: FULL (main text; supplementary not on arXiv) · **Revision**: v2 (2026-06-27)

## Results

- Seven models, 1,323 episodes: one compaction step raises pooled violation from **0% under full history to 30%**
  (range 0% GLM-5.1 to 59% DeepSeek-V4/Kimi-K2.5). When the constraint survives the summary, violation is 0%
  (n=90); when dropped, 38% (n=315).
- Decay is **8.3× larger for soft organisational policies than hard safety norms** — exactly the deployment-specific
  rules that live only in context.
- **Constraint Pinning** (quarantine + verbatim re-injection + integrity check) restores 0% across all seven models
  and both attack variants for ~47 pinned tokens; a provenance/spotlighting prompt does not (43%/45%). Residual
  breach under operator impersonation is 17%, 10% hardened.
- Compounding (0%→78% over R=0–4) is stated in one sentence with the table in supplementary material that is not
  on arXiv — directional only.
- Single-author preprint. No independent replication; ARCBench (intake-2631) contradicts the implicit
  deletion-only mechanism: 21.1% of runs that retain the rule still violate.

## EPYC actionables

| Action | Owner | Disposition |
|---|---|---|
| Add a pinned-governance buffer arm to the compaction A/B (extract high-stakes rules, exempt from folding, re-inject verbatim, post-fold entailment check) | context-and-token-economy.md (CF-AB-1) | immediate (design text) |
| Treat the summariser as an untrusted-input sink; test a budget/deprecation-framed injection in tool output | context-and-token-economy.md (TOC-MP-4) | probe |
| Record the defence ranking (system-channel 0% > pinning 0% > provenance prompt 43%) | context-and-token-economy.md | knowledge-only |
| Do not build an in-band "operator policy update" override for pins | agents/shared/OPERATING_CONSTRAINTS.md | decline |

## Surfaced

ARCBench (owned), 2608.11392 guardrail residue (wave 3), 2610.29869 compaction laundering (wave 3).
