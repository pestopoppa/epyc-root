# RSIBench-Infra: Can Agents Optimize Their Own Training and Inference Infrastructure at Production Scale?

- **Intake**: intake-2723 (`intake-2723#record`)
- **Source**: https://arxiv.org/abs/2611.24395
- **Verification**: stage1-unverified · read depth PARTIAL
- **Disposition**: monitor; handoffs: autokernel-akx-program.md, rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Unverified PDF-only entry: do not cite its figures in plans. Its protocol description may inform design discussion; the 66.2% is 86 of 130 single runs and is not an expected success rate.

## Key claims (anchored)

0. Submission is one OCI filesystem layer; the Serve/Train job rebuilds from the baseline image, verifies engine-baseline and layer digests and applies the same layer on every rank.
   - p5 s3.3: "The agent is required to explicitly package its changes as an OCI filesystem layer, submit_oci.tar.gz,"
   - p5 s3.3: "baseline and layer digests before applying the layer, using the same layer on every rank. This reconstructs the"
1. A separate Benchmark Job never loads the submitted layer and runs fixed quality and performance scripts through service interfaces; an LLM judge reviews trajectories for benchmark hacking.
   - p5 s3.3: "Benchmark Job never loads the submitted layer"
   - p5-6 s3.3: "judge additionally reviews agent trajectories and submitted changes to identify potential benchmark hacking,"
2. A speedup counts only after the quality gate; the Faster threshold is strictly above 1.10x; 86 of 130 formally scored results (66.2%) exceed it.
   - p6 s3.3: "strictly above 10% to reduce sensitivity to small performance fluctuations."
   - p8: "Table 2 reports 130 formally scored results, of which 86 (66.2%) exceed"
3. There are no repeated-run confidence intervals; results are one run per model-task pair.
   - p10: "repeated-run confidence intervals or a controlled comparison of agent budgets, so the rankings should be"

## Claim corrections

- claim 2: **narrowed** — 66.2% is 86 of 130 single-run results (Claude scored on 10 tasks only), not a rate over 140 pairs.
- claim 3: **narrowed** — Independence is job isolation plus an LLM reviewer; no repeated re-evaluation of a submission and no variance protocol.

## Dive record

2026-11-20 Stage-2 read (sonnet) of the PDF text extracted with PyMuPDF (22 pages, FULL read; quotes hand-checked against the extract, not machine-anchorable, so the entry stays stage1-unverified per the PDF rule). Only one compliance rejection of 130 (Seed TTS removed the repetition penalty and passed the WER gate); 9 zeros = 4 failed deployments, 4 quality-gate fails, 1 compliance rejection. Baselines are median of 3 or 5 cold starts (OPD single sample). Behavior categories (Table 7): graph/compilation 31/35 Faster, spec decoding/MTP 22/23, specialized GEMM/GEMV 15/15, batch/microbatch 1/7. Hardware H20 and Ascend 910B2 only. Protocol elements we lack vs have: see the dive README. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d) Stage-2 close-out (2026-11-20): arXiv 2603.19173 (SOL-ExecBench) ingested as intake-2732; arXiv 2601.00227 (FlashInfer-Bench) declined (NVIDIA kernel focus; protocol part captured by RSIBench).
