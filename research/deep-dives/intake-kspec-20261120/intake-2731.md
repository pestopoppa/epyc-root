# On-Policy Morphing into Hybrid Attention Models

- **Intake**: intake-2731 (`intake-2731#record`)
- **Source**: https://arxiv.org/html/2611.24809v1
- **Verification**: dive-verified · read depth PARTIAL
- **Disposition**: knowledge_only; handoffs: none
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Conversion method for pure Transformers only; no result applies to the already-hybrid 27B. Do not cite it as evidence about EA/L4 KV compression.

## Key claims (anchored)

0. FlashMorph2 replaces FlashMorph frozen-weight, teacher-forced layer scoring with on-policy discrete sampling plus joint weight adaptation, raising average RULER from 63.26 to 65.68 over six Qwen3-0.6B/1.7B configurations.
   - Abstract: "improving average scores over FlashMorph by + 2.42"
   - Sec 5.2: "it raises the RULER score from 63.26 to 65.68"
   - Sec 5.1: "We use Qwen3-0.6B and Qwen3-1.7B"
1. Layer selection takes 0.72-3.57 GPU-hours and is a small part of a multi-stage conversion pipeline whose post-training recovery is the real cost.
   - Abstract: "while completing layer selection in only 0.72"
   - Appendix A.2 Table 5: "training tokens 320M 20M 1B 1B"
   - Sec 5.3: "This overhead is confined to a one-time selection stage"
2. Removing both on-policy components reverts to FlashMorph; larger-scale results cover Qwen3-8B and Qwen3-30B-A3B with Lightning attention only.
   - Sec 5.3 Ablation: "Removing both components reverts to FlashMorph"
   - Appendix: "we further scale our evaluation to larger dense and MoE backbones, including Qwen3-8B and Qwen3-30B-A3B with Lightning Attention"

## Claim corrections

- claim 0: **narrowed** — Average of six small-model configs at a 3:1 ratio, single runs; some configs regress.
- claim 1: **narrowed** — Conversion is ~2.34B tokens at the 1.7B config (320M+20M+1B+1B).

## Dive record

2026-11-20 Stage-2 dive (sonnet; PARTIAL: Appendix B/C per-task tables skimmed). Method converts a pure Transformer into a hybrid; Qwen3.8-27B is already a trained GDN+attention hybrid, and the paper has no result for re-selecting an existing hybrid. Orthogonal to AM-PORT-2B (no safe EA/L4 KV ratio on the hybrid 27B, long-context-program.md:L952 @e9ee76c): FlashMorph2 changes architecture, EA evicts KV. Adjacent observation only: full linearisation collapses RULER (Qwen3-1.7B 87.66 -> 9.57 GLA / 21.89 GDN), so the few full-attention layers carry retrieval; consistent with, not proof of, why compressing their KV hurts. Adversarial pass not run. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)
