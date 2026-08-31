# 2026-08-31 — ad-hoc audit session: INF-67 external audit + INF-68 baseline control

## Task 1 — INF-67 external audit (operator-commissioned)

Four-subagent audit of the fused-decoder session's work (code safety, allocator/weight claims,
measurement premises, debugging narrative). Verdict delivered to the operator and relayed:
direction + GDN/MoE/PLE core SOUND (kernel-mirror method proven bit-exact where wired right);
three headline root-cause findings MISDIAGNOSED (gallocr "inp_tokens corruption" — real aliasing,
no consumer after the overwrite, graph greedy was 13 all along; ple_norm_query "weight diff" —
harness eval-callback matched layer-0's hc_ffn_norm, weight 0.826172 correct on both paths;
flash_attn_ext "NaN" — the repro's own F16-Q staging bug); full-attn layer wrong ~6 independent
ways; fallback contract unsafe (state commits before bail-outs); premise constants (65 µs/9.4 ms/
180 GB/s) unmatched by committed records. Uptake by the owning session same-day: retractions +
ATTN defect list (`c43f888d`, `962c23f1`), ATTN rewrite landed (`73bf7e34` — layers 0-6
bit-exact, logit O(10)→0.684). Production v9 verified untouched throughout.

## Task 2 — INF-68: qwen4exp uniform-IQ4_XS baseline control

Spun out of the operator-commissioned INF-67 audit; executed same-day on operator go.
Evidence: `epyc-inference-research/data/inf68-uniform-iq4xs-ab-20260831/` (SHA256SUMS) @ `0dbc9992`.

## Method

- Artifact: `llama-quantize --allow-requantize` UD-IQ4_XS → uniform IQ4_XS, 98.4 GB (4.45 BPW vs
  the UD's 4.24 — uniform is *larger*; the UD's IQ3_S experts are smaller), 7.3 min at t48 under a
  region claim. 195/1224 tensors took standard fallback quantization. **Speed control only** —
  quant-from-quant; not quality-representative (the destroyed 08-28 original came from FP8→Q8_0).
  Location: `models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/`.
- Binary: fresh pinned clone of the fusion repo at the PRE-fusion anchor `7cdd7c97b` (build 10151),
  Release + native, CPU-only; `verify_ggml_linkage.sh` PASS; `[iqk] ACTIVE` confirmed in-run.
- Recipe: `taskset -c 0-95 numactl --interleave=all`, OMP spread/cores/active/dynamic-false,
  `GGML_IQK=1`, `-mmp 0`, r5, tg128+pp512, t48+t64. Region-locked (q0-q3). Per-arm load-gates
  (start only when 1-min load <10) + an in-window sampler (top frame-2, any non-bench process
  >300% CPU, 20 s cadence) so window cleanliness is evidenced DURING, not inferred after.

## Results (clean, verified windows)

| file | t48 tg128 | t64 tg128 | t48 pp512 | t64 pp512 |
|---|---|---|---|---|
| UD-IQ4_XS (87.24 GiB) | 9.13 ±0.04 | 8.86 ±0.08 | 130.7 ±9.0 | 128.4 ±1.2 |
| uniform IQ4_XS (91.63 GiB) | **10.52 ±0.05** | 9.79 ±0.08 | 161.2 ±0.5 | 169.4 ±1.5 |

- **Finding 1 — uniform beats UD: decode +15.2% (t48) / +10.5% (t64); prefill +23-32%.**
  Direction reproduced in three independent measurements (first A/B, clean A/B, fa=1 probe);
  the pre-NUMA +22% (progress 08-28) shrank but holds. Mechanism unchanged: the UD experts are
  IQ3_S×94/IQ4_NL×43/Q8_0×5, dequant-heavy on the IQK decode path; uniform IQ4_XS is the fast path.
- **Finding 2 — the documented UD baseline (tg128 13.46 t48, progress 08-28 Round 3) does NOT
  reproduce**: same code lineage, same recipe, clean verified windows → 9.13-9.18 (−32%), pp 130.7
  vs 164.4 (−21%). `-fa 1` refuted as the cause (UD 9.18, uniform 10.18 — neutral/slightly worse).
  Not chased further (box-state class: 18-day uptime, memory placement/fragmentation candidates).
  **INF-67 impact**: its fused-vs-graph A/Bs are same-window so its ratios survive, but the
  74 ms/token budget arithmetic and the eventual headline denominator must be re-anchored by the
  INF-67 session on its own build at its own boundary.
- First A/B run DISCARDED as contaminated (UD t64 ±2.86 tg / ±30 pp variance; 5-min load 49 during
  the window) — kept in evidence as `ab-run1-CONTAMINATED.log`.
- Correctness pairing: greedy "The capital of France is **Paris**." on the uniform file, iqk
  engaged, 11.3 t/s in-cli. Ratifies the speed control only, not serving quality.
- **Status per MEASUREMENT_POLICY: observations** (no codified protocol id / attestation).
  Sufficient to re-anchor a design premise and open the adoption decision; a `bench_canonical`
  attestation run is the ratification gate if adoption is chosen.

## Operator decision opened (in the INF-68 handoff)

Adopt uniform IQ4_XS for qwen4exp CPU work? Options + tradeoffs + recommendation in
`handoffs/active/qwen4exp-uniform-iq4xs-baseline-control.md` → Results.

## Hygiene notes

- **Disk at 98% (90 G free) after the 98.4 GB artifact** — the FP8 re-download branch of the
  outcome contract is blocked until cleanup; a read-only reclaim investigation was dispatched
  same-day on operator request (three-bucket keep test: production-registry / novel-under-test
  (glm-5.3-flash, qwen3.8-next-flash) / small kernel-test models; everything else purgeable in
  principle, purge list to operator before any deletion).
- llama-cli REPL footgun reproduced even with `-no-cnv` + stdin from /dev/null: 1.9 GB of "> "
  spam after a correct generation (evidence log trimmed to head). The known guidance stands:
  prefer llama-bench, or expect to trim.
- Ad-hoc session: bus outbox is roster-only, so routing to INF-67 is via this repo record (that
  session demonstrably syncs from the repo at its boundaries) — noted in the handoff T5.
- Pinned build tree `/mnt/raid0/llm/tmp/inf68-baseline-tree` retained for the ratification run;
  delete freely once the decision closes.

## Addendum — same-day disk executions (Tasks 3-4 of this session)

OP-31 minimal set executed (~212 G) and OP-8 resolved KILL with the GLM-5.2 deletion (223 G):
full record in [`2026-08-31-disk-reclaim-menu.md`](2026-08-31-disk-reclaim-menu.md) §EXECUTED.
Day-end disk: **87 G → 480 G free (87%)**. Notable: pre-deletion re-verification caught 4
misclassifications in the approved set (held with registry evidence); the GLM handoff audit split
its content into dead (model-quality) vs transferable (DSA-layer), seeding INF-69.
