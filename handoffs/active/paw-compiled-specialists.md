# PAW Compiled Specialists — compile-once fuzzy functions on the local stack

**Status**: stub
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: training_distillation, local_inference, inference_serving, tool_implementation
**Parent index**: [inference-research-index.md](inference-research-index.md)
**Evidence**: intake-811#record (parent paper + 2026-07-11 blocker), intake-1466/1467 (docs + SDK), intake-1477 (Compile by Training), intake-1478/1483 (Standard/Compact compiler weights), intake-1479 (FuzzyBench eval data), intake-1481 (self-hosted compile server, scope-overturned), intake-1482 (independent eval), intake-1484 (.paw corpus)
**Operator steering (2026-09-17)**: PAW links are "relevant for constructing agent loops and making our current agent loops more robust"; the operator likes a GUI separating deterministic flow from fuzzy LLM work (separate stub, UFH-09).

## Objective

Turn the re-opened Program-as-Weights line into a bounded, licensed-aware decision: can we compile recurring
fuzzy subtasks (tool-output classification, log filtering, JSON repair, routing predicates) into tiny local
specialists that run on the frozen llama.cpp stack, and does the compile-once economics survive on CPU/MI210?
The intake-811 re-open trigger is literally met on artifact availability (weights + FuzzyBench eval data, both
predating the 2026-07-11 blocker); licenses and a self-hosted compile path are the remaining gates.

## Research Context

| Intake ID | What it settles |
|-----------|-----------------|
| intake-1478/1483 | Standard (Qwen3-0.6B) / Compact (GPT-2 124M) compiler weights public and ungated; NO artifact license |
| intake-1479 | `fuzzy_bench_verified` downloadable (43,128 + 7,550 rows, spec/input/output); no train split; no license |
| intake-1481 | Unofficial MIT self-hosted compile server exists and works for the default Qwen3 compiler; Compact GPT-2 SDK-compat claim overturned; no ROCm proof |
| intake-1482 | Independent eval: standard 94 / finetuned 97 / compact 85 on 100 adversarial cases (one task, n=100, author labels); semantic abstention 98.9% on decided cases; logit-confidence thresholding fails |
| intake-1484 | 7,226 public .paw programs (heterogeneous bundle hygiene, no license) |
| intake-1477 | Self-hosted training-based recipe (teacher synthesis → LoRA on Qwen3-0.6B); no paper memory numbers |

## Tasks

- [x] **PAW-1 — Artifact-license scope RESOLVED 2026-09-17** (OP-43 closed by operator ruling: "everything we do is internal research"). **Scope ruling: internal research use only** — no redistribution, no deployed-service use, no shipping of compiled programs or adapter outputs. Under this ruling the unlicensed artifacts (intake-1478/1483 weights, intake-1479 dataset, intake-1484 corpus) are usable for all internal work; the license question re-opens only if a distribution/productization path is ever scoped. ✅ 2026-09-17
- [ ] **PAW-2 — Self-hosted compile spike on the target host.** Run the MIT self-hosted compile server (intake-1481#00) with pinned weights (intake-1478#00), mapper and SDK; prove one end-to-end compile producing a modern GGUF-ZIP .paw, then one local call. Measure compile wall time, peak RAM, disk. Document the Compact GPT-2 canonicalization caveat (intake-1481#05) and whether CPU-only execution is workable before MI210.
- [ ] **PAW-3 — Evaluate compiled programs on FuzzyBench (internal, unlicensed).** Build the eval manifest for `fuzzy_bench_verified` (1479) and record standard-vs-compact capability on our own task slices; replicate the abstention experiment (semantic 3-class vs thresholding) per intake-1482. WIRE THE VIDYA ADAPTER BEFORE THE FIRST RUN (VB-TDP-1).
- [ ] **PAW-4 — Amend the intake-811 blocker record.** Replace the stale 2026-07-11 "compiler is CLOSED / no concrete download" text with the verified availability + license + no-official-self-hosted-compile status (index correction; see §7 of the Stage-3 plan file).
- [ ] **PAW-5 — Agent-loop candidates list.** Identify ≤3 recurring fuzzy subtasks in the current agent loops (candidates: tool-output classification, transcript/log filtering, JSON repair, routing predicates) and file each as a compile-once candidate with a direct-model baseline. Do not start compiling until PAW-1 and PAW-2 land.

## Open Questions

- Does the compile-once economics survive on this host without an accelerator (compile time vs adapter lifetime)?
- Does intake-1482's abstention finding transfer to our task slices, or is it task-specific?
- Is the Qwen3-0.6B interpreter (594 MB Q6_K) fast enough per call for always-on loops versus our current cheap-first models?

## Notes

Re-open trigger status: MET on availability, NOT met on capability (no official self-hosted compile). License scope resolved
2026-09-17 (OP-43): internal research only — all current work is in scope; distribution would require a grant. The 10M-example
FuzzyBench training set remains unavailable; 1477's recipe is the closest self-hosted path. The 10M-example FuzzyBench training set remains unavailable; 1477's recipe is the closest self-hosted path.
