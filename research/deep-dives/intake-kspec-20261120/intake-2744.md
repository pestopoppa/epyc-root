# Attention Drift: What Autoregressive Speculative Decoding Models Learn

- **Intake**: intake-2744 (`intake-2744#record`)
- **Source**: https://arxiv.org/html/2605.09992v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: autokernel-akx-program.md, speculative-decoding.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Do not cite it as an explanation for acceptance loss with context length (it measures chain-depth drift). Its fixes need drafter retraining; cite only the SWA-with-sink long-context data as weak support for a draft window.

## Key claims (anchored)

0. During a speculation chain the drafter's attention moves from the prompt onto its own recently generated tokens, in both EAGLE-3 drafters and MTP heads.
   - Abstract: "attention progressively moves from the prompt onto its own recently-generated tokens"
   - Abstract: "This phenomenon is observed across both EAGLE3 drafters and MTP heads"
1. All architectural fixes explored require retraining the drafter, and inference-time magnitude normalization without matched training hurts accuracy.
   - Sec 4 intro: "All architectural changes explored in this section required re-training of the drafter"
   - Sec 4.4: "normalizing the magnitude without matched training hurts the accuracy in both cases"
2. MTP heads already use post-norm yet drift sharply in the first steps and then plateau; the fix was not evaluated on other drafter designs.
   - Sec 4.5: "This is notable because MTP uses a post-norm architecture, where we expected drift to be largely suppressed"
   - Sec 4.5: "drift onsets sharply within the first few speculation steps and then stabilizes at a new attention baseline"
   - Sec 7 Limitations: "we do not investigate the alternative mechanisms at play there or evaluate our fix across other drafter designs"
3. Drafters trained on short windows fail at long context under full attention, a sliding window rescues them, and performance saturates around a 1024-token window.
   - Sec 5.2: "Under full attention (regular), the pre-norm model fails catastrophically"
   - Sec 5.2: "performance saturates around 1024 tokens, with diminishing returns beyond that"
   - Sec 5.2: "We use SWA as a long-context evaluation tool rather than as a method we propose"

## Dive record

2026-11-20 Stage-2b wave-2 dive (sonnet; full read; surfaced by intake-2739). OVERTURNS the surfacing hypothesis: drift is across draft-chain depth within one round, not across context length, and MTP acceptance versus context length is not measured; so it does not explain the Q38FN acceptance decline with depth (0.79 / 0.73 / 0.66 at 1k/32k/64k; autokernel-akx-program.md L1293 @901b3fe). Weak, indirect support for a draft-only window via the EAGLE-3 long-context SWA data (window 256 recovers ~80%, ~1024 saturates; Llama 3.1 8B at 8k, Qwen3-8B at 32k), with sink/BoS carry mandatory (SWA without BoS collapsed). Whether the Q38FN MTP head drafts more than one token per round was not verified by the dive. Attention Residuals 2603.15031 and the code repo declined. lane_head 901b3fe44a30
