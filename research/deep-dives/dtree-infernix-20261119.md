# Tree-verified speculative decoding: Infernix and lineage (intake-2705..intake-2717)

**Date**: 2026-11-19 · **Requester**: autokernel (AK-DTREE program, operator pre-approved intake) · **Consumer**: `handoffs/active/speculative-decoding.md` → *AK-DTREE program plan* → *Intake refinements 2026-11-19*, DTREE-A, DTREE-B

## Sources

| Intake | Source | Verification | Disposition |
|---|---|---|---|
| intake-2705 | Infernix @ `397f8cd` (`docs/maintainer/tree-verification.md` + kernels) | dive-verified | integrated |
| intake-2706 | Infernix issue #30 | dive-verified | integrated |
| intake-2707 | STree 2505.14969 | dive-verified | knowledge_only |
| intake-2708 | TreeWY 2608.20961 | dive-verified | integrated |
| intake-2709 | SpecLA 2607.16673 | dive-verified | knowledge_only |
| intake-2710 | Bastion 2605.29727 | dive-verified | integrated |
| intake-2711 | CAST 2610.00321 | dive-verified | integrated |
| intake-2712 | Cost-aware dynamic tree 2510.26577 | dive-verified | knowledge_only (superseded by 2711) |
| intake-2713 | Trees from Marginals 2607.06763 | stage1-unverified (PDF only) | integrated (design alternative, no numbers) |
| intake-2714 | Recursive Speculative Decoding 2402.14160 | dive-verified | integrated |
| intake-2715 | UniVer 2605.04543 | dive-verified | monitor |
| intake-2716 | LumoTree 2609.23900 (same Qwen3.8-27B target) | dive-verified | integrated |
| intake-2717 | Traversal Verification 2505.12398 | dive-verified | knowledge_only |
| intake-2667 (existing) | DDTree 2604.12989, re-encountered | dive-verified (2026-11-09) | re-encounter note only |

Three literature sweeps were run (operator cap: six). Each sweep did every deep dive it recommended. A fourth sweep was not run: every remaining surfaced source is either already indexed (DART, Block Verification, Bole, OPT-Tree, Sequoia, SpecInfer) or has no arXiv id (Wang & Zhou 2026, Hu et al. 2026b, ReplaySSM blog).

## Findings that change the AK-DTREE plan

0. **The MI210 breakeven comes first.** Our own DF2-VERIFY-SLOPE (2026-11-09) measured 2.39 ms per extra verify row on a 52.5 ms 27B round, about 4.6 %/column, against about 1.2 % on Infernix's 5090. At that slope, Infernix-sized acceptance gains lose. The new box DTREE-0 attributes the slope and cuts it before tree width can pay. LumoTree (intake-2716) found that tree verify on Qwen3.8-27B only matches the chain rate on GB10.
1. **"+12-17 %" measures accepted drafts per round, not speed.** On RTX 5090 the tok/s gain is +6.9 % at 12 columns and +8.6 % at 16, with one request. It falls to about 0 at four requests and turns negative at 128K context (intake-2705#03). The P5 row must cover context buckets.
2. **A greedy token-identity gate against linear spec will fail for a correct tree build.** A wider verify block selects different GEMM tiles (intake-2705#02). Replace it with a one-token-prefill oracle, where the disagreement rate must be no worse than the chain's.
3. **Our DFlash2 already produces the predecessor-conditional lattice that Infernix's best-first builder consumes.** So P1 should build the tree from it, not from independent top-k.
4. **Path rows cost about path count x chain** (intake-2705#05). They need three or more paths to pay. Infernix uses them only where attention has no tree form. So P1 is a scaffold; the real design is the ancestor mask plus compaction.
5. **Device-side builder and acceptance (DTREE-A).** Host accept is already 9.8 % of 27B-dflash2 time, and it grows with W.
6. **`auto` should be a measured controller (DTREE-B).** Measure same-text gain from nested widths, and time per (batch, context bucket, width). A CAST/Bastion latency curve is the prior. gfx90a GEMM-tile cliffs make a fixed table risky.
7. **Kernel alternatives for GDN tree records on gfx90a:**
   - The depth-first walk: exact, and needs a wave64 remap.
   - TreeWY closed form: within BF16 rounding, rows of 16 columns or fewer.
   - Commit-time replay with an ancestor-masked solve (TfM).
   - Time all three at W = 8/12/16 before choosing.
8. **Sampled acceptance.** RSD needs siblings drawn without replacement. UniVer adds acceptance only above T≈0.

Raw dive material: `/mnt/raid0/llm/tmp/dive-dtree-20261119/` (Infernix clone, issue JSON, paper HTML/PDF text).
