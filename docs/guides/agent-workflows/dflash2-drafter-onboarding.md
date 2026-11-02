# DFlash2 drafter onboarding for a serving target

Prepared 2026-11-01 for the open **DF2-DRAFTER-CAPABILITY** task. This is an implementation and evidence checklist; it does not establish a working reusable training pipeline or close that task. No capture, training, conversion, inference or deployment was performed to prepare this guide.

The controlling task and pilot are in the [DFlash2 handoff](../../../handoffs/active/dflash2-block-drafter-experimental-build.md), under DF2-DRAFTER-CAPABILITY and DF2-FT-1. That handoff owns their status and decision rules. The references below were checked against local root `origin/main` at `2689038d77c5220f78f1061ba237e0b459fd275c`. This guide introduces no measurement grading rule or replacement gate.

## Evidence and remaining implementation

| Item | Evidence available in the handoff | Work still required |
|---|---|---|
| Existing serving path | DFlash2 for Qwen3.8-27B was structurally selected and operator-ratified on 2026-10-03; DRAFT-SEL-1 compiles selections | Target-specific acceptance and a signed stack change for every replacement |
| Training implementation | Historical scoping identifies public NeMo Automodel `train_dflash2`; DF2-FT-1 names revision `1667095` | A new ROCm environment, offline-feature dataset adaptation and CPU smoke; MI210 training is not established by the CUDA reference |
| Feature capture | Existing target-feature path exposes five taps | The reusable dumper, manifest, token alignment and KL final-hidden contract remain implementation work |
| Conversion | Audit read `DFlash2DraftModel` registration at champion `c72ec82f` | Prove intended checkpoint keys, dimensions, tensor mapping and conversion round-trip; registration alone is insufficient |
| Training objective | DF2-FT-1 explicitly compares hard CE and forward KL | Measure the pilot and record its objective verdict; the default is not already decided |

The Qwopus work and K1 registration were cancelled on 2026-10-27. Historical Qwopus tables and engineering estimates do not provide a current target, a live booking or a drafter-transfer result. The older [scoping memo](../../design/df2-qwopus-scoping-20260915.md) is useful for implementation decomposition only, with the cancellation and later audit controlling its applicability. Reported production-shape acceptance of 0.29–0.39 and benchmark acceptance of 0.62–0.73 have different shapes and do not by themselves identify a training-objective defect.

## 1. Bind one target and one intended serving recipe

Prepare a target manifest before dataset capture. Include:

- Exact target checkpoint revision, GGUF path and SHA-256, quantization, architecture, vocabulary and hidden dimensions; hash the tokenizer files, configuration, chat template and special-token mapping. Pin target-provided embedding/output weights used by the headless drafter.
- Starting drafter checkpoint revision and hashes, incumbent serving drafter hash, block size, tapped layers, selector layout and intended output quantization. A common architecture or tokenizer name is not a compatibility proof.
- Kernel source commit, converter and quantizer commits, binary/build manifest and loaded library identity. A directory name or mtime is not content proof.
- Exact server argv and sampler, context and sliding-window limits, draft cap, slot count, intended in-flight workload and role. Hash the prompt/request manifests and untouched holdout split.
- Dataset provenance, generated token IDs and their alignment with target features/labels, seed, objective, optimizer/configuration and training environment lock or version record. Preserve resumable checkpoints and inference-only weights separately.

For the FT-1 pilot the serving target is the 27B Q8_0 recipe at :8083. The converter's planned `--target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw` supplies configuration and tokenizer; that path does not change the teacher into an EXL3 target. Validate its configuration/tokenizer binding against the pinned serving target before use. For another model, resolve that model's own pins and tensor contract rather than copying the 27B dimensions.

## 2. Prepare capture and training without touching production

Follow the existing four-step experimental-kernel workflow in [AGENTS.md](../../../AGENTS.md): start from fresh current production in `llama.cpp-experimental`, build there, validate GPU and CPU regressions, then promote a complete candidate as a new production version. FT-1 specifically requests a branch from the current experimental champion tip; bind that tip and verify its production ancestry under the existing workflow. Do not edit, build or patch the frozen production tree to add a dumper. Production v10 remains frozen at `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`; serving uses the kernel store, not the frozen tree's in-tree build directories.

Implement the feature-dump and dataset adapter, then perform the pilot's CPU-only smoke before GPU work. Use a **new ROCm venv**, preserving the two verified environments. The referenced upstream inference model is not a local training pipeline. Missing plumbing is implementation scope, not a reason to reject a target.

The 27B pilot's five bf16 taps are layers `[6,20,34,48,62]`, width 5120: **51,200 B/token**. KL additionally needs the final-hidden tap, adding 10,240 B/token for **61,440 B/token** total. The handoff calls this final post-norm hidden and also describes reconstruction through `output_norm + W`: resolve the exact capture/reconstruction placement against source during implementation so normalization is applied once. Keep that resolution in the feature manifest; do not silently infer a different tensor contract. Capture only each completion and its 2,048-token window prefix, with token positions and request/split identity preserved.

**Final-hidden implementation anchor (C5 source audit).** In experimental champion commit `c72ec82f5417bb2937310326120f149b665e8400`, `src/models/qwen35.cpp:204–222` applies `output_norm` before naming `h_nextn` and `result_norm`, and then calls `build_lora_mm(model.output, cur, model.output_s)` for logits. Therefore a captured post-norm `h_nextn` or `result_norm` must enter the equivalent output projection **without applying output_norm again**; a pre-norm final-layer capture must apply it once. The source also conditionally selects output rows before `result_norm`, and can select them in the last layer when `embeddings_nextn_masked` is set (`:174–176, 211–215`); neither callback name alone proves every completion token was captured. Bind positions, output-row selection, projection weights, scaling and any adapters, and compare reconstructed logits against target outputs on aligned tokens before using the data for KL. This is a source-level contract for the pinned architecture and commit, not evidence that a dump or numerical reconstruction has run.

Any compute follows the existing backlog-scheduling calendar and granted windows, with :8083 preempted by drain and reloads owned by the inference session. Prove per-launcher ggml isolation using research `scripts/utils/verify_ggml_linkage.sh`; prove HIP residency during the run through VRAM/KFD evidence. This guide grants no resource window.

## 3. Execute the explicit DF2-FT-1 pilot

These are the existing pilot controls, not a generic recipe that has already passed:

1. **Data:** use the DS41-C95 wire contexts at `/mnt/raid0/llm/tmp/ds41-c95/results` (historical inventory: 36 captures, 320 turns, 630k generated tokens). Hold out every C4 run untouched. Regenerate two completions per held-in request at the production sampler and pinned `X0_ARGV_8083.txt`, capped at 2048 tokens, within 3 MI210-hours. Capture C4 features separately for the held-out offline proxy; never train on C4.
2. **Capture:** implement the preceding tap contract; plan approximately 0.8–1.2M tokens / 50–75 GB in at most two rolling shards, within 3 MI210-hours. These are planning quantities, not measured capture throughput or storage availability; remeasure headroom before issuance.
3. **Train:** warm-start `z-lab/Qwen3.8-27B-DFlash2` bf16 with NeMo Automodel `train_dflash2 @1667095`, `sdpa`, and the offline-feature adaptation. Freeze the target; train the whole drafter. Arm H is hard block CE on sampled tokens. Arm K is forward KL at T=1 through the frozen target projection with Automodel KDLoss, chunked, plus renormalized KL over the selector's top-16 candidates. Share data order, seed, steps and LR; add a second seed for K. Training budget is at most 4 MI210-hours. The approximately 31 GB optimizer/weight state plus 5.1 GB frozen embedding/output footprint is a planning estimate, not a fit result.
4. **Convert:** export inference-only weights, convert through `DFlash2DraftModel`, then quantize to Q8_0, preserving all pins and logs. Validate the intended 81-tensor 27B checkpoint: names, dimensions, mapping, missing/unexpected keys, borrowed target weights and GGUF metadata. The served header describes five non-causal blocks, window 2048, `fc` 25600→5120, and codebooks `2 × 256 × 248320`; these are target-specific facts to verify, not universal DFlash2 constants.
5. **Baselines and receipts:** include the incumbent and an **untrained round-trip** of the z-lab bf16 checkpoint through the same converter/quantizer. The round-trip must be tensor-equal after dequantization or within the A/A band on DF2-4. Preserve the tensor comparison independently; an A/A behavioral result is not a claim of tensor equality. Log raw per-request `draft_n`, `draft_n_accepted`, `predicted_n`, timings and failures in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. The proxy is not measured serving acceptance.
6. **Held-out evaluation:** replay all C4 requests twice ABAB on a fresh server per arm at the production argv; also run the DF2-4 12-prompt benchmark per arm. Count every held-out request, including failures. Preserve the frozen target/incumbent/warm-start hashes, champion binary identity, holdout list, sampler and seeds.

The pilot plan budgets about **13 MI210-hours** plus **4–6 desk days**. This guide does not authorize bypassing scheduling, resource controls or the existing measurement process.

Apply the rule in the handoff without changing gates:

| Decision | Existing DF2-FT-1 requirement |
|---|---|
| PROMOTE to follow-on work | Best arm has held-out weighted acceptance `sum(accepted)/sum(drafted)` at least incumbent +0.05 on both reps; held-out decode tok/s improves at least 8%; DF2-4 acceptance is at least incumbent −0.02; coherence gate is clean and DF2-6 greedy pass count is not below incumbent |
| Choose KL default | K − H ≥0.02 on both reps and the second K seed has the same sign |
| Cost-neutral objective | `abs(K − H) <0.01`: choose hard labels, which need no final-hidden tap |
| One bounded extension | Acceptance gain +0.02..+0.05 earns one further shard of at most 1M fresh resamples, retraining and one reapplication of the rule |
| KILL | Acceptance gain below +0.02; record the result |

Higher acceptance and decode throughput are better. Where the handoff's clauses leave a boundary or objective case unresolved, preserve the raw result and obtain the existing protocol's adjudication; this guide supplies no new cutoff. FT-1 PROMOTE opens **DF2-FT-2**, not a production deployment. On every verdict, the owning session records the objective verdict and the requested onboarding rule in DF2-DRAFTER-CAPABILITY. Re-alignment on the exact model's served traffic is a rule to record from that pilot outcome, not a measured benefit already established here. The named next instances are the frontdoor 35B-A3B MTP head, then Flash-Next.

## 4. Accept each target, then package adoption

For a new target, establish its own held-out acceptance, decode throughput, quality/coherence and relevant concurrency/cache-reuse correctness under the pinned recipe. Use matched incumbent/no-speculation and applicable MTP comparisons from the DFlash2 protocols; do not substitute a vendor speedup, a different target's acceptance or a teacher-forced proxy. Keep raw denominators and distinguish per-request acceptance, per-position behavior, target verify cost and end-to-end serving throughput. The DF2-4 benchmark shape does not by itself certify production agentic traffic or concurrent serving. Use the existing measurement constitution and target protocol for acceptance decisions.

The existing FT-2 trigger, contingent on FT-1 PROMOTE, scales to 3–5M on-policy tokens with C4 and a new role holdout untouched. Its serving keep gate includes SL-2 verify steps/s and aggregate tok/s at np 1/4/8, fresh servers, ABAB with at least five pairs, coherence and greedy checks, DF2-4 acceptance ≥ incumbent −0.02, held-out acceptance ≥ incumbent +0.05 and np4 throughput above the calibrated floor. Keep this separate from the smaller FT-1 pilot.

After the applicable keep verdict, prepare adoption through the existing [stack-change skill](../../../.claude/skills/stack-change/SKILL.md) and [derivation graph](../../../.claude/skills/stack-change/DERIVATION.md). Draft the complete multi-repo change and preflight in scratch; one operator signature precedes applying the serving change. The source master is research `orchestration/model_registry.yaml`; DRAFT-SEL-1 lists acceptable `roles.<model_role>.drafters`, while orchestrator `orchestration/stack_topology.yaml` selects the drafter for each server. Repoint the appropriate `drafters.dflash2.draft_model` only through that package; retain the incumbent file as rollback. Do not hand-edit the generated lean registry, priors, launch projection or production argv.

The [stack-change handoff](../../../handoffs/active/stack-change-governance-pipeline.md) owns compile/projection, capacity, runtime attestation and promotion checks. Complete its serving proof after signed apply; use actual kernel-store binary and loaded-library identity plus a real completion. Documentation or a green process-health response cannot substitute for serving proof.

## Review and delivery packet

For owning-session review, deliver the target manifest, dataset/split manifest, versioned dump/trainer code and environment, resumable checkpoint, inference weights, converted GGUF and tensor-parity report, raw evaluation receipts, objective verdict, and the applicable stack-change package with rollback. Keep prepared artifacts, executed measurements and deployed state explicit. DF2-DRAFTER-CAPABILITY remains open until its owning session has evidence of the reusable implemented path; this guide supplies its onboarding instructions only.

Source baseline: root local `origin/main` at `2689038d77c5220f78f1061ba237e0b459fd275c`. Source sections used: DFlash2 handoff opening production-selection ruling, cancellation notice, INF-62 audit, DF2-DRAFTER-CAPABILITY, DF2-4/5, DF2-FT-1 and FT-2 trigger; historical scoping memo training/capture/conversion analysis; stack-change handoff DRAFT-SEL-1; stack-change skill phases 0–8 and DERIVATION source/generated tables; root AGENTS.md production freeze and experimental workflow. Future executions must re-resolve source revisions and actual artifacts.
