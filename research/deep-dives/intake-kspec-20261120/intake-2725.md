# NarrowSpec: Draft Hidden Width Need Not Match the Target in Speculative Decoding

- **Intake**: intake-2725 (`intake-2725#record`)
- **Source**: https://arxiv.org/html/2611.23835v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: autokernel-loop.md, speculative-decoding.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Narrowing needs a from-scratch drafter retrain; do not treat it as a PTQ step or a CPU lever for DFlash2 (DFlash is NO-GO on CPU). Do not quote the B200/GB10 speedups as a 27B expectation.

## Key claims (anchored)

0. Halving the draft residual width costs at most 3.0% acceptance and quartering costs 2.1-5.4% for DFlash and EAGLE-3 drafters (one seed each, matched data budget).
   - Sec 1, What we find: "halving costs at most 3.0% acceptance, and none in two of the four drafter–target pairs, while quartering costs 2.1–5.4%"
1. Narrow drafts are trained from scratch at their own width with adapters; in the paper on four B200 GPUs, six epochs for DFlash.
   - Sec 1: "The narrow draft is trained from scratch at its own width, with adapters wherever it meets target-width tensors and matching support in the serving engine"
   - Sec 3 Training: "Every variant, including full width, is trained from scratch with SpecForge [ SGLang contributors, 2025 ] on four B200 GPUs, DFlash for six epochs and EAGLE-3 for three"
2. For DFlash the output adapter folds into the borrowed target head with logits unchanged up to floating-point rounding; folding an already-quantized head was not evaluated.
   - Abstract: "the trained output adapter folds into it, giving one narrower projection with logits unchanged up to floating-point rounding"
   - Sec 2.3: "We do not evaluate folding a target head that is already quantized."
3. End-to-end batch-1 gains were 1.06-1.12x (B200) and 1.13-1.44x (GB10); verify stays within 1%, so targets where the draft is a small share of the iteration gain less.
   - Abstract: "narrowing the draft to half or a quarter width speeds up end-to-end decoding by 1.06–1.12"
   - Sec 9 Limitations: "targets where the draft is a small share of the iteration stand to gain less"
   - Sec 5.1: "while verify stays within 1% in every cell"
4. The paper expects narrowing to matter most for MTP drafters that read the full vocabulary head each draft step, but leaves narrow MTP training as future work.
   - App B.1: "MTP layers are usually trained with the target. Training and evaluating narrow MTP drafters is future work."

## Claim corrections

- claim 0: **narrowed** — One seed per variant at a matched data budget; needs a from-scratch retrain.
- claim 2: **narrowed** — Fold done only from BF16 heads; our heads are GGUF-quantized.
- claim 3: **unaffected** — Confirmed; verify within 1% (Table 5).

## Dive record

2026-11-20 Stage-2 dive (opus; full read). OVERTURNS 'direct DFlash2 candidate cutting draft cost on CPU and MI210': (1) narrowing is a from-scratch retrain (paper: ~2.94B tokens at epoch 5 for Qwen3-8B DFlash, GPU-hours not reported); in-house estimate ~60-80 MI210-days of target forwards to match (inferred from 27B prefill 410-574 t/s, speculative-decoding.md:L1725 @1650e3d); (2) DFlash is NO-GO on CPU in-house (speculative-decoding.md:L842 @1650e3d); (3) on the 27B the drafter share of the round is ~10-19% (inferred: verify 43.5 ms at 8 rows L1799, served round ~61 ms AK-GAP-1 autokernel-loop.md:L5746), so half width caps near 1.05-1.10x before acceptance cost; DFlash2 acceptance on agentic traffic is already 0.29-0.39 (L1725). C14 drafter borrows model_other->output (src/models/dflash.cpp L1244-1255 @eee3da838). CPU analogue: Q38FN draft/MUL_MAT:lm_head 6.9 ms of 13.9 ms draft per step at d1k (q38fn-cpu-perop-profile-20261118-r2 RESULT.json; autokernel-akx-program.md:L1659). No published narrow checkpoint found (search). lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)
