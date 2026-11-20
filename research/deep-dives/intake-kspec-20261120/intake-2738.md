# Is Grep All You Need? How Agent Harnesses Reshape Agentic Search

- **Intake**: intake-2738 (`intake-2738#record`)
- **Source**: https://arxiv.org/html/2605.15184v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: context-and-token-economy.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Directional only (single runs, 116 questions, commercial authors). Cite the delivery-path and harness-sensitivity findings, not a general grep-beats-vector claim.

## Key claims (anchored)

0. With inline delivery, grep exceeds vector retrieval for every harness-model pair on a 116-question LongMemEval-S subset.
   - 4.1.3: "inline grep exceeds inline vector for every harness–model pair"
1. The harness effect is as large as the retriever effect: the same Opus backbone scores 93.1% under one harness and 76.7% under Claude Code.
   - 4.1.3: "The same Claude Opus 4.6 backbone reaches 93.1% under Chronos but 76.7% under Claude Code"
2. File-based (programmatic) delivery erases or reverses the lexical advantage; one pair falls from 93.1% to 55.2%.
   - 4.1.3: "which falls from 93.1% under inline grep to 55.2% under programmatic grep"
3. Under growing distractor load degradation is small, and vector is often stronger at low session counts.
   - Fig 1 caption: "Both methods face minimal degradation, but GREP outperforms vector on average"
   - 4.2.4: "vector retrieval is often stronger at low session counts"
4. The authors do not claim grep beats vector in general; the corpus includes an extracted structured-events layer and the harness opens with a vector block.
   - 5 Limitations: "We do not claim that grep"
   - 3.3.1: "followed by an initial broad context block (top-15 vector results)"

## Dive record

2026-11-20 Stage-2b dive (sonnet; full read). Single run per cell, no CIs, 116 questions; an Exp-2 cell differs from its Exp-1 twin by 3.4 points (run noise as large as several reported gaps). Commercial authors (PwC); corpus layer is their own Chronos pipeline. Count mode, pagination and line clipping: NOT-FOUND-IN-SOURCE. Transferable lessons are delivery path and harness: our ms.search returns rows inline (the favourable condition); pointer/file-based designs (A7 peek/grep surface, context-and-token-economy.md:L255; dispatch_pointer_results track, harness-program.md:L161 @b5c5fe7, frozen) need a closed-loop success probe before any claim. Chronos and MemTool 2507.21428 declined (confound / tangential). lane_head b5c5fe7b4e63
