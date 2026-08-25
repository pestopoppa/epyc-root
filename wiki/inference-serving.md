# Inference Serving

**Category**: `inference_serving`
**Confidence**: verified
**Last compiled**: 2026-08-25 (extends the 2026-08-24 ROUTE-A1 compile with the seam's never-co-place verification — re-place when possible, refuse when not — and closes the 2026-08-11 NUMA P0-1 IN-PROGRESS item: derived-priors full-instance drop resolved, PROMOTION_GATE_TARGETS 196/0, full suite 16 failed / 12526 passed, no source edits) (inference-serving carries the ROUTE-A1 overlap-queue falsification + SS-BENCH-GATE-c spawn guards); previously 2026-08-23 (evening wave-2/tier-1 compile: Q38-T6 cold-start lineup FIXED (orchestrator `96498c3d` — the launcher never read `ORCHESTRATOR_STACK_NUMA_MODE`, the cold-start fallback was hardcoded `"quarter"`, and a TOTAL cold start was misread as the env=full poison signature); the frontdoor's `-ub 8192` is SILENTLY INERT (no `-b` passed → effective micro-batch is the 2048 default); the slot save/restore path is ARMED-not-dormant and the post-migration request is a STRICT EXTENSION (H20/H21, with the two bounded exceptions: `context_compression` off but one-flag-away, and `request.tools` tail re-prefill); the misnamed `VERIFIED` migration state fixed (`98061c6b` — a restore returning `n_restored: 0` on an HTTP 200 can no longer destroy the source KV); #25592 is the LARGER exposure and a v10 candidate; the in-band `[ERROR: ...]` fail-open under the 2026-08-11 fix is now closed (502 / terminal SSE `error`); and the CT-9 pilot-adoption decision (HOLD all three, no fleet-wide extension — the evidence window carried calibration traffic only); earlier same-day: the Qwen3.8 swap is SERVED — Q38-T5 five-point checklist green on :8083, cold-start NUMA-mode gap filed as Q38-T6; DFlash2 challenger sealed at np1 against the predeclared 55.46 t/s comparator, np2/4/8 grid + greedy parity still mandatory; previously 2026-08-22: KV-restore semantics on the hybrid frontdoor: migration VERIFIED proves transport not reuse, only strict continuations reuse a restored cache, `-ub 8192` is inert; previously 2026-08-21 evening: Q38-T4 mode-artifact closure, Q38 registry swap complete end-to-end)
**Sources**: 79 documents

## Compiled Update — 2026-08-25: the overlap story is complete — re-place when possible, refuse when not — and the NUMA derived-priors regression from 2026-08-11 is closed

**Confidence: verified** — the seam probe ran in an operator-granted clean window (2026-08-24); test
counts are executed-suite results; the P0-1 closure is the owning handoff's recorded state.

### The seam where re-placement cannot help now refuses instead of co-placing (ROUTE-A1 thread, 2026-08-24 clean-window re-run)

The 06:48Z smoke established the first half of the overlap story: forced eval_batch requests are
RE-PLACED onto a disjoint instance whenever one exists (3/3 disjoint admits, 0/5 queue-expected —
the overlap-queue mechanism does not exist in the fleet layer). The 11:46Z clean-window re-run
established the second half. Control: no holds → forced frontdoor probe admits in **1.4s**
(`decision=allow idx=0`). With q0,q1 (ingest anchor) + q2,q3 (frontdoor busy) held, all three forced
probes (frontdoor, worker_general, ingest_long_context) return **504 at exactly the 45s queue
budget** (`error_detail="[ERROR: placement timeout role=frontdoor reason=placement_topology_overlap_timeout holders=[0, 2] after 45.0s]"`).

**The never-co-place invariant holds at the gate level**: the fleet layer avoids overlap by
re-placement when possible and refuses (queues to timeout) when every candidate overlaps a held
region. The standing smoke was restated to judge the observed placement — `--expectation
{replacement|seam}` (default `replacement`; `CO-PLACEMENT` is always a failure), 53 tests green.
Cosmetic residue only: the ingest probe's error_detail echoed `role=worker_general` (stale variable
in the message), worth a one-line fix. The Step-2 flag-on decision remains an operator
re-specification (pin the placement machine vs re-state the expectation).

### NUMA P0-1 CLOSED 2026-08-24 — the derived-priors full-instance drop is resolved

The 2026-08-11 compiled IN-PROGRESS item (the region-lock regression recurring one layer downstream:
`derived/stack_priors.yaml` dropped the `NUMA_FULL` instances for frontdoor 8070 / worker_general
8072 / ingest_long_context 8085) is **closed**: `derived/stack_priors.yaml` now records
8070/8080/8180 with `cpu_shape_class: full`; `PROMOTION_GATE_TARGETS` is **196 passed / 0 failed**;
the full `tests/unit` suite is **16 failed / 12526 passed / 69 skipped / 6 xfailed** after three
fixture-side fixes (gate-fixture `waited_s`/`blocking_roles` fields in `test_dispatch_cross_role_placement.py`
and `test_inference_mixin.py`; the SS-BENCH-GATE-c placement `ps` subprocess counted in
`test_model_server_coverage.py`). The 16 remaining failures are all the E8-era frozen-kernel guard
(documented operator decision, untouched by design) plus same-class derived-priors expectations —
**none are the new-topology breakage this row exists to fix. No source code was modified.** The
2026-08-11 standing falsifiable prediction held: the gate tests went green with zero test edits.

### Source References (2026-08-25)

- [shape-keyed-contention-gating.md](../handoffs/active/shape-keyed-contention-gating.md) — the seam verification (45s budget vs 1.4s control), the OP-21 second-pass pooling note, and the standing-smoke restatement.
- [numa-topology-cutover-resume-20260730.md](../handoffs/active/numa-topology-cutover-resume-20260730.md) — P0-1 CLOSED 2026-08-24 (derived priors record `cpu_shape_class: full`; suite counts; E8-era residual classification).
- [progress 2026-08-25-unattributed.md](../progress/2026-08/2026-08-25-unattributed.md) — the N25/P0-1 closure record (three fixture-side fixes, 19 → 16 failed, no source changes).
- [progress 2026-08-23-unattributed.md](../progress/2026-08/2026-08-23-unattributed.md) — the ROUTE-A1 smoke + bridge record this section extends.

## Compiled Update — 2026-08-24: the overlap-queue premise was falsified by ROUTE-A1 — the live fleet layer has no queue for overlapping placements

Sources: `handoffs/active/shape-keyed-contention-gating.md`,
`progress/2026-08/2026-08-23-unattributed.md` (ROUTE-A1 section).

- **The Step-2 overlap-queue mechanism does not exist in the live fleet layer.** The operator-granted
  ROUTE-A1 step-2 smoke (2026-08-24T06:48Z, quiet host, anchor held via `region-lock run`) ran 8
  probes: 3/3 disjoint admit-expected ADMITTED correctly, **0/5 overlapping queue-expected queued**
  (all admitted). Measured cause: the placement machine RE-PLACES forced eval_batch requests onto the
  disjoint instance (`candidate_topology_idx=2` observed) and the gate allows with reason "all pairs
  + n-way allow" (frontdoor+ingest pair = borderline → gate-allow). The queuing Step 2 was built to
  verify does not exist. Ledger DONE_PASS; RTG-35 re-pointed to the operator re-specification
  decision. [progress/2026-08/2026-08-23-unattributed.md, shape-keyed-contention-gating.md]
- **The same grant's bridge work hardened the spawn layer.** `_verify_anchor_held` (read-only
  `active_region_holders()` scan) + `_verify_probe_signal` (refuses structurally-unobtainable plans)
  landed behind the smoke; SS-BENCH-GATE-c guarded the ONE API-runtime spawn site
  (`worker_pool._start_worker` via `api_enforce_placement`, bench-live → pins to `host_cores −
  claim` or refuses) plus `LlamaCppBackend`/`LlamaOCRWorker` per-request spawns (503 on refusal).
  Quiet paths byte-identical. [progress/2026-08/2026-08-23-unattributed.md]

## Compiled Update — 2026-08-22: four lifecycle defects from one pilot deployment — all the same shape

Sources: `handoffs/active/qwen38-27b-replace-qwen36.md` (Q38-T6),
`handoffs/active/qwen-chat-template-evaluation.md` (CT-DEPLOY),
`progress/2026-08/2026-08-22-research-intake.md`.

Deploying one launcher flag surfaced four independent lifecycle defects, every one a variant of
*"a mode/config surface that silently does something other than asked"*:

1. **The launcher never reads `ORCHESTRATOR_STACK_NUMA_MODE`** — mode is argv-only, and the
   cold-start fallback is hardcoded `"quarter"` (`stack_commands.py:1588`, pre-dating the
   2026-07-30 half-fleet ratification). An unflagged cold start silently drops all three full
   instances. Fix filed as Q38-T6; recovery: `start --only <roles> --numa-mode both`.
2. **The additive-promotion gate deadlocks on itself**: its launch view follows the REALIZED
   fleet mode, so from a sub-full fleet it flags the full ports it is being asked to start —
   mirror image of the clean-shell/mode-full artifact from 2026-08-21. Recovery: the per-server
   `reload` path (gate-free).
3. **`reload server_<port>` matched no dispatch branch, restarted nothing, and returned 0** —
   silent vacuous success; sub-full instances were structurally unreachable by reload and the
   only symptom was config-vs-live drift. Fixed (orchestrator `34ff6fcc`): manifest-table
   addressability + unknown components exit 1 + a full/half serving-flag parity test.
4. **A first mlock failure on the third 80B copy** (`Cannot allocate memory` at 281 GB locked
   fleet-wide) killed the launch silently behind an rc=0 reload; one retry succeeded. The
   both-mode triple-residency of the 80B is a standing capacity edge.

Standing rules these yield: **a lifecycle command that returns 0 must be verified by the live
surface it claims to have changed** (the vacuous reload is the third rc=0-lie in this program's
record); and **runtime attestation of declared-vs-live cmdlines** (added with the plumbing) is the
detector that catches every one of these — the first fully-green check including attestation
landed 2026-08-22 after the fixes.

## Compiled Update — 2026-08-22: four lifecycle defects from one pilot deployment — all the same shape

Sources: `handoffs/active/qwen38-27b-replace-qwen36.md` (Q38-T6),
`handoffs/active/qwen-chat-template-evaluation.md` (CT-DEPLOY),
`progress/2026-08/2026-08-22-research-intake.md`.

Deploying one launcher flag surfaced four independent lifecycle defects, every one a variant of
*"a mode/config surface that silently does something other than asked"*:

1. **The launcher never reads `ORCHESTRATOR_STACK_NUMA_MODE`** — mode is argv-only, and the
   cold-start fallback is hardcoded `"quarter"` (`stack_commands.py:1588`, pre-dating the
   2026-07-30 half-fleet ratification). An unflagged cold start silently drops all three full
   instances. Fix filed as Q38-T6; recovery: `start --only <roles> --numa-mode both`.
2. **The additive-promotion gate deadlocks on itself**: its launch view follows the REALIZED
   fleet mode, so from a sub-full fleet it flags the full ports it is being asked to start —
   mirror image of the clean-shell/mode-full artifact from 2026-08-21. Recovery: the per-server
   `reload` path (gate-free).
3. **`reload server_<port>` matched no dispatch branch, restarted nothing, and returned 0** —
   silent vacuous success; sub-full instances were structurally unreachable by reload and the
   only symptom was config-vs-live drift. Fixed (orchestrator `34ff6fcc`): manifest-table
   addressability + unknown components exit 1 + a full/half serving-flag parity test.
4. **A first mlock failure on the third 80B copy** (`Cannot allocate memory` at 281 GB locked
   fleet-wide) killed the launch silently behind an rc=0 reload; one retry succeeded. The
   both-mode triple-residency of the 80B is a standing capacity edge.

Standing rules these yield: **a lifecycle command that returns 0 must be verified by the live
surface it claims to have changed** (the vacuous reload is the third rc=0-lie in this program's
record); and **runtime attestation of declared-vs-live cmdlines** (added with the plumbing) is the
detector that catches every one of these — the first fully-green check including attestation
landed 2026-08-22 after the fixes.

## Compiled Update — 2026-08-21: the registry has FOUR planes, and a swap is not live until the third one recompiles

Sources: `handoffs/active/qwen38-27b-replace-qwen36.md` (Q38-T2 + same-day correction),
`progress/2026-08/2026-08-21-research-intake.md`, ratification receipt
`artifacts/operator/ratify_qwen38_registry_swap_20260821.json`.

The 2026-08-20 Qwen3.8 swap was executed correctly in the true master and STILL would have served
Qwen3.6 at the next stack start, because the registry is a four-plane compile chain and only the
first plane was current:

1. **Master** — `epyc-inference-research/orchestration/model_registry.yaml` (11k lines, full
   record). The swap landed here (`b376dadd`). This is the only hand-edited plane.
2. **Lean** — `epyc-orchestrator/orchestration/model_registry.yaml`. **AUTO-GENERATED** — the
   banner at line 1 says so (`compile_lean`, `registry_compiler.py`), filtered to active roles,
   recompiled at every stack start on cache-key mismatch. Three separate audits in one day edited
   or audited this file believing it was the master; every one had read it from the middle.
3. **Derived** — `orchestration/derived/stack_priors.yaml`. Compiled FROM the master by
   `stack_change_pipeline.py update` — and **NOT recompiled at stack start**: the launcher reads it
   as-is (`orchestrator_stack.py:252-262`, `-m` from `requirements.model_path` :1062-1071). This is
   the plane that actually launches; it was nine days stale.
4. **Descriptors + operator summary** — compiled artifacts downstream of lean; a hand-edit there is
   discarded on the next recompile.

Operational rules this yields: **a model swap is complete when plane 3 verifies, not when plane 1
commits**; parity validation compares PORTS only (`stack_templates.py:303`) so a model divergence
between planes is silent; and the descriptor compile REMOVES a model when no live role references
it (the master row survives as rollback anchor) — an expected transition that needs
`--allow-descriptor-model-removal` plus an only-this-removal assertion, not a blanket flag. The
2026-08-21 ratification (`scripts/operator/ratify_qwen38_registry_swap_20260821.sh`) encodes all of
this; post-ratification the derived plane verifies Qwen3.8-27B-Q8_0 @ draft_max 8 on
architect_general. Known residue: `guard_all_surfaces` fails on pre-existing quarter-port drift
(frontdoor/worker/ingest `serving.ports` vs launch manifest, unchanged since 2026-03) — tracked as
Q38-T4, does not touch the swap surfaces.

## Compiled Update — 2026-08-20: the Qwen3.8 serving successor has a faster drafter candidate, not a deployment change

**Confidence: verified observation, explicitly nonpromotable.** The DFlash2 result is relevant because
Qwen3.8-27B is the guaranteed successor to the Qwen3.6-27B production variant, but the production
kernel and lineup remain unchanged.

The experimental DFlash2 build reached **70.0 decode t/s** at np1 against **55.2 t/s** for matched
MTP8 and **29.4 t/s** plain, with mean acceptance **0.62804** versus MTP's **0.48246**. This is the
right incumbent comparison: DFlash2's +26.81% over optimized MTP is materially stronger evidence than
its +138.10% over plain. The candidate was built from frozen-v9 ancestry in an isolated branch and
passed real CPU/GPU smoke; frozen production was not edited.

Serving adoption remains gated on the concurrency grid, exact greedy parity, and proof that the
DFlash2 block-verify workload reaches the intended optimized dispatch. The prospective measurement
hook must be integrated before the next grid so throughput and weighted acceptance are written with
the original claim, residency, build, model, protocol, and manifest identities. Historical np1 evidence
is immutable pre-hook evidence and must not be upgraded by a read-side reconstruction.

### Source References (2026-08-20 Qwen3.8 DFlash2 serving candidate)

- [Qwen3.8 replacement handoff](../handoffs/active/qwen38-27b-replace-qwen36.md) — production-successor context and existing registry boundary.
- [DFlash2 experimental build handoff](../handoffs/active/dflash2-block-drafter-experimental-build.md) — matched metrics, build identity, and mandatory residual gates.
- [AutoKernel research loop](../handoffs/active/autokernel-research-loop.md) — governed `experimental_runtime` stage/receipt chain and nonpromotion boundary.
- [Root session progress](../progress/2026-08/2026-08-20-root.md) — exact branch, evidence hashes, cleanup, and carrier integration order.

## Compiled Update — 2026-08-18: the declined coding ladder ran — and the stale axis table got reconciled the right way

**Confidence: verified** — ladder figures are from the completed architect bench on the frozen v9
kernel (seeded temp 0.6, MTP, reasoning off), read from the handoff's populated rows; the SWE cell
is explicitly provisional and is quoted only with that label.

### The ladder: operator-declined, then operator-authorized — the cell's history stays visible

The 2026-08-14 decline ("quality will improve certainly") was later reversed by the operator ("both
rungs, proceed"), and the full ladder ran on the same recipe the candidates artifact already uses,
so the results slot directly into the row: **LCB-hard 52.8% (28/53) — tops the 27B class**;
**BCB-hard 31.1% (28/90) — ties stock 27B**; humaneval 96.3%; aime25 76.7 / gpqa-cot 81.3 /
mmlu_pro 56.7 / olympiad_hard 47.1. The handoff records the supersession explicitly rather than
overwriting the decline — an `operator-declined` cell is a state with a history, not a permanent
verdict, and the record shows authorization preceded the run (the bench was never silently re-run
past a standing decline).

### SWE-40 = 15/40 is provisional and understated, and the reason is the harness

19 of 40 agentic instances came back empty because the harness's `ACTION:` grammar parser did not
recognise the model's native `<tool_call><function=…>` tool-call grammar — a scoring artifact, not
model failure (the full mechanism is compiled on
[Benchmark Methodology](benchmark-methodology.md)). The parser fix is written and staged; the re-run
is parked on one named container-local blocker (the devcontainer's Docker socket is an orphaned
bind-mount whose inode was pinned across a host dockerd upgrade — the host and all 40 eval
containers are healthy). Until the merged re-run lands, 37.5% is a floor to be finalized, not a
result to rank with.

### The axis-table conflict below is resolved — and the resolution direction is the lesson

The 2026-08-16 update below flagged a standing source conflict: the candidate-surface handoff's axis
table still showed the retracted synthetic cells (`37.15 → 13.61`, "MTP HURTS at depth") as ✅
measured beneath a completion note retracting them. That is now reconciled: the table itself carries
the corrected flat-curve rows (~45 t/s single-stream 2k–32k, peak aggregate 157.3 t/s @ np8/2k) with
an explicit **RETRACTED — do not cite** block for the synthetic values. The reconciliation merge
deliberately took the rewritten-rows form over a union — a union would have preserved the retracted
✅ cells *beside* their retraction, and a ✅ cell gets quoted downstream without the paragraph that
withdraws it. Corrections must land in the cell being quoted, not in prose beneath it.

### Source References (2026-08-18 coding ladder)

- [`gpu-candidates-surface-qwen38-update.md`](../handoffs/active/gpu-candidates-surface-qwen38-update.md)
  — the "Coding ladder — WAS RUN" section with all rungs, the corrected axis table with its
  RETRACTED block, the 21-patches/19-empty split, and the parked re-run's exact next steps.
- [`qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — the arm's
  verified identity and throughput evidence the ladder rows sit beside.
- [`loop-owned-fleet-implementation.md`](../handoffs/active/loop-owned-fleet-implementation.md) —
  the reconciliation-merge "instructive case" naming this exact table as why union is the worst
  outcome for a retraction.

## Compiled Update — 2026-08-16: a decode-vs-depth curve and an MTP workload gate, both manufactured by the prompt

**Confidence: verified** — every number below was measured on this host against the frozen v9 kernel
(`/mnt/raid0/llm/llama.cpp` @ `0db32c06e`, `llama-server --version` `10125`) on the single MI210, and
the retraction was made by the same workstream that produced the retracted numbers.

### The arm

`Qwen3.8-27B` was staged on release day (2026-08-14) as the successor to `Qwen3.6-27B-MTP-Q8_0`,
which is the primary model for **`architect_general` + `coder_escalation`** — both served from one
`:8083` MI210 process (ROCm0). Load smoke PASSes on the v9 HIP build
(`-ngl 999 -c 4096 --spec-type draft-mtp --spec-draft-n-max 4`): the model loads at **31.98 GB VRAM**,
generates coherently, and raises no op-fallback warnings.

**The MTP-sidecar assumption was wrong, and only header inspection caught it.** The plan assumed a
separate draft sidecar. `llama-gguf r` on the unsloth `Qwen3.8-27B-Q8_0.gguf` (29.05 GB) shows
`blk.64.nextn.*` tensors (`eh_proj` / `enorm` / `hnorm` / `shared_head_norm`) and
`qwen35.nextn_predict_layers` metadata — the same **embedded** self-draft layout as
Qwen3.6-27B-MTP-Q8_0. So `--spec-type draft-mtp` stays same-file self-draft and the registry's
`draft_model` is unchanged: a genuine like-for-like wiring swap. The ggml-org `mtp-*.gguf` (3.16 GB)
is a full layer-64 draft model (`attn` + `ffn` + `nextn`) built for the ggml-org base, which *strips*
MTP — redundant here, and downloaded only as a fallback. A "drop-in" claim is only as good as the
artifact inspection behind it; the assumed topology and the shipped topology differed.

### The retraction

The first throughput sweep (2026-08-14) used a **synthetic random-word prompt** and produced a clean,
plausible story that was entirely an artifact of the prompt:

| depth | synthetic sweep (RETRACTED) | real-prompt sweep (2026-08-15) |
|---|---|---|
| 512 | 37.15 t/s | — |
| 2k | 37.95 t/s | ~45 t/s |
| 8k | 22.22 t/s (plain 29.11, "MTP −23.7%") | ~45 t/s |
| 32k | 13.61 t/s (plain 21.65, "MTP −37.1%") | ~45 t/s |

The re-run on **real olympiadbench prompts** shows single-stream decode **flat at ~45 t/s across
2k–32k**, and MTP holding. Both artefacts died together: the monotone "KV-read-cost" decay curve
*and* the "MTP is net-negative on deep-RAG" workload gate it appeared to reproduce. Random-word
prompts destroy MTP draft acceptance, so a speculative arm benched on synthetic text measures the
prompt distribution, not the workload. This is the same failure mode as the retracted n-gram-drafter
`2.8×` (a warm-context self-copy artifact): **never characterise a speculative-decoding arm on
generated filler text.** The natural-prompt interactive single-shot figure, `47.57 t/s`, was never
affected and still stands.

*Standing source conflict, resolved here*: the candidate-surface handoff's axis table still lists the
synthetic `37.15 → 13.61` row and the MTP-hurts-at-depth cell as ✅ measured, while its own
2026-08-15 completion note retracts them. The real-prompt sweep supersedes; treat the axis table's
throughput/RAG/MTP cells as stale until that handoff is reconciled.

### Batched serving on the arm

- Prefill **pp512 = 727.29 ± 28.00 t/s** (`llama-bench -ngl 999 -nkvo 1 -p 512 -r 3`).
- 24-cell `np × depth` sweep on real prompts: single-stream flat ~45 t/s, **peak aggregate 157 t/s at
  `np=8`**.
- From the (otherwise retracted) synthetic sweep, the `np=4` @512 cell read ~20–23 t/s per request,
  ~80 t/s aggregate. Do **not** splice that against the 157 t/s figure to build a scaling curve —
  different prompt regimes, and the per-request half of the synthetic cell inherits the same
  acceptance defect.

**The accounting rule that makes any of this readable** (standing campaign policy, unchanged and
still binding): under concurrency the individual request t/s normally *drops* while aggregate batch
throughput *rises*, so every concurrent eval must record `speed_metric_mode`, `eval_concurrency`,
median per-request t/s, aggregate batch t/s, and eval wall time. For concurrent eval batches the
SafetyGate/Pareto `speed` objective is **aggregate batch t/s**, with raw median request t/s retained
as audit metadata — precisely so the planner does not read safe same-trial fan-out as a regression
while the per-instance slowdown stays visible for diagnostics. A run missing that metadata is
diagnostic-only quarantine, never a baseline mutation.

**`np` is a per-arm constant, not a stack default.** The campaign's remaining batched-decode item
(E1 / P-BENCH-3) is deliberately a *per-model* ladder `-np 1,2,4,8,16`, and the 2026-07-06 checkpoint
completed the `qwen36_q8_0` MoE ladder but interrupted the `qwen36_27b_q8` **dense-control** tail
after `np=1` to restore the stack cleanly — so the MoE-vs-dense concurrency comparison that sweep
exists to produce **does not exist yet**, and no cross-arm np optimum can be quoted from it. Read this
alongside the call-shape rule compiled in
[Benchmark Methodology](benchmark-methodology.md) (*"Tuning constants are CALL-SHAPE specific"* — the
`-fa 1` optimum already inverts between two models on this same GPU). Cross-role parallelism is
stricter still: allow-verdicts are closed-world only for the exact `topology_hash` measured, and any
stack, role, model, CPU-binding or launch-topology change invalidates the matrix before concurrency
may be used again.

### What is still open

The **registry swap** is the one unchecked step: `architect_general` + `coder_escalation`
`model_path` → `Qwen3.8-27B-Q8_0.gguf` (with `draft_model` pointing at the same file), then
`stack_change_pipeline.py` regenerate plus the standard model-stack-change checklist. The optional
vision projector (`mmproj-Qwen3.8-27B-Q8_0.gguf`, 0.63 GB) is not downloaded and the multimodal
question — whether to also stage this arm for `worker_vision`/`vision_escalation` — is explicitly out
of scope for the coder/architect swap.

### Source References (2026-08-16 Qwen3.8 serving arm)

- [`qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — GGUF-header
  verification and the embedded-MTP correction, load smoke (31.98 GB VRAM), the real-prompt
  flat-decode result and its explicit CORRECTION of the synthetic decline, prefill pp512, and the
  remaining registry-swap step.
- [`gpu-candidates-surface-qwen38-update.md`](../handoffs/active/gpu-candidates-surface-qwen38-update.md)
  — the synthetic sweep's per-depth and MTP-workload-gate cells (the retracted values, still present
  in its axis table), the `np=4` @512 batched cell, and the 2026-08-15 24-cell re-run that supersedes
  them.
- [`bulk-inference-campaign.md`](../handoffs/active/bulk-inference-campaign.md) — the concurrent-run
  metric policy (aggregate batch t/s as the Pareto speed objective), the baseline-mutation hard rule,
  the topology-scoped closed-world guarantee, and the E1 `-np 1,2,4,8,16` per-model ladder with its
  interrupted dense-control tail.

## Compiled Update — 2026-08-13: a region-lock grant is not a model-server inference window

**Confidence: verified** — current handoff, redesign protocol, artifact absence, and dispatch-resource
scope were checked together; no inference was authorized or run.

The K-LCM-1 LongCoT-Mini full-run dispatch was not runnable merely because it carried a q2 benchmark
grant. Its v1 protocol floor-saturated (frontdoor `0/402`, worker-general `0/307`), and the v2 redesign
requires RE-4.2 first: a frontdoor-only, 30-row, two-phase non-saturation probe whose admissible band is
overall accuracy strictly between 10% and 90% with approximately complete marker presence. No RE-4.2
artifact exists. The probe itself requires an operator-granted quiet window, current v8/v9 topology
re-attestation, and stopped autopilot; the design note explicitly authorizes no inference. In addition,
the LongCoT runner needs live model-server role ports, which a region-lock-only benchmark grant does not
provide. The durable disposition is therefore `BLOCKED_PRECONDITION`, not a failed or completed run:
execute RE-4.2 in its governed window, and attempt/close K-LCM-1 only if that probe is in band.

### Source References (2026-08-13 K-LCM-1 precondition)

- [Bulk inference campaign](../handoffs/active/bulk-inference-campaign.md) — exact K-LCM-1 dependency,
  prior floor-saturated evidence, resource mismatch, and next action.
- [mainB progress](../progress/2026-08/2026-08-13-mainB.md) — dispatch-premise audit and no-run
  disposition.
- [RE-4 protocol redesign](../handoffs/active/re4-protocol-redesign.md) — governing probe order,
  acceptance band, quiet-window prerequisites, and inference-authorization boundary.

## Compiled Update — 2026-08-12 (second pass): a gate that fails open by agreeing with itself, and two "missing" things that already existed

**Confidence: verified** — each item was measured through the real consumer rather than inferred from the declaration; the registry-coverage figures are executed-statement counts.

### RETRACTED premise: "25 inference-batch entries are failing closed on a dead topology pin"

The premise inverts under measurement. Of the 25 entries pinned to a dead topology hash and kernel era, only **4 genuinely failed closed**. The other **21 were FALSE-PASSING** — because the topology gate compares the entry's pin against a **stale attestation from 2026-07-20** rather than against the live host. A stale pin and a stale attestation **agreed with each other**, and the gate reported success while both disagreed with reality.

This is the most reusable failure shape on the page: **a check between two artifacts that rot together is not a check.** Re-pinning is necessary and insufficient — 36 entries across 7 files were re-pinned to the live hash and the v9 era, and the residual blocker is a **fresh attestation**, without which the repaired pins would simply agree with a new stale reference later.

The same tree contains the contrast case, which is why the defect was diagnosable at all: two consumers implement the nominally same check, and one is fail-closed on exact match while the other is the attestation-based one above. **Same name, opposite polarity.** When two implementations of one invariant exist, the weaker one is the one that will be in the path that matters.

A sibling premise fell the same day: a host-prep task assumed `numa_balancing=0` did not persist across reboot. It already did, via two independent host mechanisms — the confusion was that the container's `/etc/sysctl.d` is a **different overlayfs layer** from the host's, so the setting was invisible from where it was checked. What genuinely did not persist were `perf_event_paranoid`, the CPU governor and the transparent-hugepage settings, now covered by a boot unit spanning eight settings with 39 fake-root mutation tests plus 7 live assertions.

### Two "missing" capabilities that were already built

- **The role-restart applicator was not missing.** A backlog row framed `restart_role()` as the one absent piece blocking capability promotion; it has existed since late June. What was actually missing was **test coverage of one branch**: the orchestrator-role health-gate path had **zero executed statements across 44 existing tests**. Five induced-failure tests closed it — **49 passing, zero missing statements, 5 of 5 mutations caught**. The applicator has a real production caller chain but stays fail-closed behind a flag with zero promoted registry rows, so nothing changed operationally. Live shadowed restart remains **blocked on a reload window owned by the inference-owning session**, per the reload-ownership rule.
- **A duplicate port registration was not a collision.** Port 8083 appearing twice in the registry had been filed as a blocker; it is **intentional** — one role is an alias of another and they share the server, which is the same-GGUF-roles-share-one-server rule working as designed. Fleet construction resolves cleanly to 6 fleets and 11 bindings with no phantom. The slot count in the original filing was also wrong (2, not 8).

Both are the same lesson from opposite directions: **before building the missing thing, measure whether it is missing.** Two of this week's largest "gaps" cost their sessions a re-derivation and zero implementation.

### A role-attribution correction that changes who owns a banked number

The Probe B result recorded below and on [MoE Optimization](moe-optimization.md) — 12.19 t/s single-instance canonical against 4.3 t/s per instance cross-NUMA, +184% per-request — was **attributed to the wrong role after the 2026-07-31 cutover**. The 122B moved to the critic role at that cutover and the GPU-resident 27B now holds `architect_general`. The numbers are unchanged and correct; **the role label on them was not**. The fix was applied as an append-only correction note rather than by editing the original figures, which is the right handling: a banked measurement's *identity* can be corrected without rewriting the measurement.

The general rule for reading any role-keyed throughput on this page: **a role name is a binding, not a model**, and bindings move at cutovers. Index by model and quant; treat the role as of-its-era.

### Duty cycle: the instrument, not just the number

A compute duty-cycle figure circulated at ~19–20% and is **~8–9% receipted**. Two independent errors produced it: the 19% window was scoped to a couple of hours and quoted as covering a whole night, and a 3h47m stretch with **zero compute receipts** was treated as measured rather than **unwitnessed**. The instrument was also wrong in kind — instantaneous samples used as a utilisation *rate*, where the load average (which peaked at 38.84) is the rate. Any serving-utilisation claim needs its window, its instrument, and an explicit unwitnessed category.

### Source References (2026-08-12, second pass)

- [`reboot-gated-inventory-and-staging.md`](../handoffs/active/reboot-gated-inventory-and-staging.md) — the 21-of-25 false-passing gate, the two-consumer polarity split, and the host-persistence premise correction.
- [`capability-registry-and-promotion.md`](../handoffs/active/capability-registry-and-promotion.md) — the applicator premise correction and the zero-coverage branch closed to 49 tests.
- [`autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md) — the port-8083 alias resolution and the fleet/binding recount.
- [`gpu-serving-tie-in-program.md`](../handoffs/active/gpu-serving-tie-in-program.md) — the Probe B role-attribution correction, applied append-only.
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the duty-cycle scope and instrument corrections.

## Compiled Update — 2026-08-12: fixing only the cited line would have left every streaming client corrupted

**Confidence: verified** — read from committed code and its guard tests, plus direct execution of the validation path against the live template. Items marked committed-not-live are explicitly not in effect until the owning session reloads at its own boundary.

### The fail-open 200 was four sites, not one — and a stream cannot retract its 200

The 2026-08-11 finding (backend failures returned as HTTP 200, so retry logic, error metrics and every eval scorer read an outage as a model answer) cited a single non-streaming line. **The identical fail-open sat at three further streaming sites plus the uninitialised-primitives case** — and streaming is the SDK default for most harnesses, so fixing only the cited line would have ticked the box and left the majority path corrupted.

Two consequences the original finding did not name, both from the same blanket handler:

- It swallowed the **503 raised twelve lines above it** for uninitialised primitives.
- It swallowed the **contention-denied exception**, which has a dedicated `503 + Retry-After + failure_provenance` handler — so documented back-pressure arrived at the caller as prose and nothing retried.

Now typed exceptions propagate and everything else is a **502**. The streaming sites emit a **terminal SSE error event** rather than streaming the error as content and closing with `finish_reason: "stop"`, because **a stream cannot retract its 200** — once the status line is out, the only honest channel left is the event stream itself.

> **When a fail-open is found on one path, the finding is the class, not the line.** Enumerate every path that reaches the same handler before closing the row.

A companion cleanup on the same principle: two dashboard-facing fallbacks silently substituted a *plausible* value on failure — an unfiltered manifest rendering other-mode ports as "expected", and an empty list rendering as a **healthy empty stack** rather than a read failure. The **fail-open was deliberately kept** (for a status panel, over-reporting beats dropping the panel); what was fixed is the **silence** — each now warns, naming what was substituted and why, with a negative-control test asserting the healthy path does *not* warn.

### A dry-run flag that is not wired is worse than no dry-run flag

`orchestrator_stack.py start --validate-only` was **declared and never read**: the argparse entry existed with help text *"Validate stack template and exit"*, and a grep for its destination across the whole file returned only the declaration. `main()` dispatched `start` straight to the launcher with no branch — so **the documented dry run launched the production stack.**

> **A missing implementation made a safety affordance do the opposite of what it advertised, and it manufactures exactly the confidence needed to run the command.** Note the test that would not have caught it: *a test asserting the flag EXISTS passes today.*

Now wired, with two design choices worth keeping: the branch sits **before dispatch**, so no code path between the check and the launcher can start a server; and it exits 0 on valid, **1 on invalid *or unloadable***, so an unloadable template fails closed rather than falling through to a launch. Its guard test drives `main()` through argv with the launcher booby-trapped **plus a control proving the trap can fire** — the positive alone would also pass if `main()` never reached dispatch for an unrelated reason. Executed directly against the live template it returns `validate-only: stack template 'default' — PASS` / `nothing was launched`, exit 0.

**Guard scope must match what the action mutates.** The new validation path initially sat *below* the running-bench guard — which covers start/stop/reload because those **mutate the host**, and exists because a lifecycle action once destroyed 1 h 09 m of decision-gating measurement. Validation mutates nothing, so `--validate-only` returned a refusal whenever a bench was detectable: **pure config validation was unavailable exactly when the host is busy, i.e. when you most want it.** Fail-closed, never dangerous, just useless at the moment of need. Hoisted above the guard, with a test asserting a **real** `start` is still refused under identical conditions — or the hoist could have been implemented by weakening the guard for every start.

### The stack-change gate's catch-22 now names its own escape

The gate refuses a launch while live ≠ config; the only cure for that drift is a restart; the restart requires the launch it just refused. **The obvious operator reaction — retry `start` — cannot work**, and the fatal message said only that it refused. It now names the escape: `stop --all` first, after which there is no live process to drift against. Message-only, no behaviour change, and the escape was **verified to exist before the message was written** — a fix that ships an unverified command is the same defect wearing the new name.

A sibling correctness note on the launcher: **keying on a structural property survives a topology change that breaks name-keyed code.** The NUMA-mode resolver (arg → runtime-facts manifest → shell env, then probe the realized fleet and *override* a disagreeing resolution, logging the correction) still returns the right answer after the lineup changed, because its probe universe is defined as *the non-full instances* rather than by shape name. Verified by classification with no live probing: full ports and non-full ports together classify as `both`, and the empty set classifies as unknown — deliberately fail-safe, so a cold start falls back to manifest/env rather than fabricating a mode. **The label went stale and the behaviour did not.**

### `-c` provisioning re-decided: lazy faulting relocates the cost, it does not remove it

The standing rationing of context length rested on launch-time cost, which was later measured at ~zero. The decision package that followed corrects the inference rather than the measurement: **lazy KV faulting relocates the cost from launch to load.** Resident-set size grows toward the full reservation exactly when requests genuinely use deep context, so max-provisioning converts a **launch-time guarantee** (KV bounded by construction) into a **runtime exposure** — worst case being the sum of full-window KV over all resident roles, hit silently under concurrent deep-context load. *"~Zero" was measured at reservation and short context — true, and not the number the decision needs.*

Options as filed: **(A)** max-provision fleet-wide plus a compaction/eviction policy above the server — full trained window everywhere, but that policy machinery does not exist and the worst-case sum is uncomputed; **(B, recommended)** a **staged raise** — raise context only where the lineup's summed full-window KV fits RAM with stated margin, computed **mechanically at priors/stack compile time so the gate is a check, not a judgement** — and keep rationing elsewhere until (A) exists; **(C)** status quo, the worst option, because it is a rationing decision standing on a premise now measured false. Sequencing note that costs nothing to honour: fold the change into the next recompile so the rebuild is paid once. **Ruling belongs to the lineup owner plus operator; the row stays open.**

### Registry hygiene for status surfaces: a liveness probe is not a freshness probe

Every entry in the dashboard registry declared the **transport** health path, while the server's own source states plainly that it means only *this process is serving*. **A registry entry buys liveness of the SERVER, not freshness of the DATA** — an automated consumer reading that field as "the page is fine" reads a much narrower claim than it thinks, and the probe stays green over a dead producer. One entry has been repointed to its three-valued fold; the pattern generalises to every surface added under the plane rule.

Filed alongside and still **OPEN**: drift in the production-kernel attestation renders loudly as a failure class, but a **missing** attestation renders as a single muted line with no reason and no alarm class — on the one surface whose job is to assert which kernel is production. The neighbouring reader already synthesises an explanatory sentence when the file is merely absent; the summary passes the error straight through.

### Source References (2026-08-12)

- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the streaming-site enumeration, the `--validate-only` wiring and guard hoist, and the registry/attestation findings
- [`progress/2026-08/2026-08-11.md`](../progress/2026-08/2026-08-11.md) — the stack-gate catch-22 message fix and the fail-open fallback warnings
- [`handoffs/active/numa-placement-defect-20260730.md`](../handoffs/active/numa-placement-defect-20260730.md) §T12 — the `-c` provisioning decision package and its three options
- [`handoffs/active/autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md) — the rows these closures were pulled from
- `epyc-orchestrator/scripts/server/orchestrator_stack.py`, `scripts/server/realized_fleet.py` — read directly for the validation branch and the mode classifier

## Compiled Update — 2026-08-11: a fail-open 200 masked backend outages as model answers; a region-lock regression recurs in derived priors

**Confidence: verified** — both findings read directly from committed code and tests. The region-lock fix is **IN-PROGRESS** (owner: `inference`, gated on a stack relaunch) and must not be read as resolved.

### Every eval fan-out through `:8000` had been scoring backend outages as low-quality generations

`/v1/chat/completions` caught *every* exception into a generic `[ERROR] Backend failed: {e}` string and returned it as a normal 200 completion — so retry logic, error metrics, and every eval scorer reading through this route read an infrastructure outage as a model answer. The fix (`a4e398fc`, `f8479a72`) lets `HTTPException` and `ContentionDenied` propagate and maps everything else to 502 (this route is a gateway; the fault is the upstream's). The finding as filed cited one non-streaming call site; the same fail-open pattern was independently found at three further streaming sites plus an uninitialized-primitives case — a stream cannot retract an already-sent 200, so those now emit a terminal SSE `error` event instead of streaming the error as generated content with `finish_reason: "stop"`. Guards assert both directions (three failure-path tests verified to FAIL against pre-fix HEAD in a detached worktree; two success-path tests pass on both sides), closing the false-negative "the guard would pass just as happily if the route errored on everything" shape. 292 tests passed.

### A NUMA-topology region-lock regression recurred, this time in the derived priors rather than the launch config

`derived/stack_priors.yaml` drops the `NUMA_FULL` instance for every quarterable-fleet role (frontdoor `8070`, worker_general `8072`, ingest_long_context `8085`) — the exact triplet the operator ruled "accidental and clearly a mistake" on 2026-07-23, now recurring one layer downstream in the derived priors rather than the launch config that caused the first instance. A HALF instance is advertised as the FULL instance via `ServerURLsConfig().frontdoor`, and this is the confirmed root cause of 7 of 9 red promotion-gate unit tests — the tests assert the topology-declared lineup and are correct; editing them to expect halves-only would encode the regression into the gate itself, the same "guard that asserts the defect" shape already retired elsewhere in this stack. **IN-PROGRESS**: the fix requires a `--numa-mode both` stack relaunch plus a priors recompile (owner: `inference`); a standing, falsifiable prediction is on record that all seven tests go green with zero test edits once that lands.

### Source References (2026-08-11)

- [`progress/2026-08/2026-08-11.md`](../progress/2026-08/2026-08-11.md) — mainB's HS-OD-2 fix narrative and the A4/P0-1 region-lock root-cause derivation
- [`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) — HS-OD-2 closure
- [`numa-topology-cutover-resume-20260730.md`](../handoffs/active/numa-topology-cutover-resume-20260730.md) — P0-0, the derived-priors `NUMA_FULL` drop
- [`gpu-serving-tie-in-program.md`](../handoffs/active/gpu-serving-tie-in-program.md) — P2-5l closure (`NUMA_NODE0`/`NUMA_NODE1` constant deletion, quarter-name attribution repair)
## Compiled Update — 2026-07-29 GPU shadow lane: built, inert, NOT activated

The MI210 acquired a *designed and largely implemented* serving lane during the
2026-07-28/29 window. **Nothing about it is live.** The GPU serves no production
traffic, the master registry is frozen, no registry proposal has been applied, and
the activation choreography (Steps 0-7) has not been run. Read every item below as
"code and data that exist and are tested", never as "a serving capability the stack
has".

Confidence: `verified` for the landed code, test counts, on-disk artifact hashes and
region-lock/sysfs observations — all of which were re-checked rather than restated;
**no throughput or quality claim about the lane exists yet**, because the lane has
never served a request. The Phase-3 bake-off that would produce one has not started.

### Key Findings (2026-07-29)

- **The shadow-only invariant (D3) is the governing constraint, and it is enforced
  structurally rather than by policy memory.** "The GPU lane serves no production
  traffic until Phase-3 bake-off evidence + operator three-gates sign-off." The
  tenancy module has **no apply path at all** — D3 by absence of the function, not a
  flag over one — and `render_registry_proposal` emits diffs only. The np_ceiling
  loader sits behind a default-off `ORCHESTRATOR_FEATURE_GPU_SHADOW_LANE`; the
  preflight probe is plan-only and was never run. 170 lane tests pass across the
  four suites at integrated HEAD.
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **The inertness guarantee got *weaker* as the lane got more complete, and the
  handoff says so rather than letting it pass.** The original P0-7 witness was
  lexical ("`gpu_shadow_lane` does not appear in `orchestrator_stack.py`"). P2-6
  legitimately added gated lane plumbing, so that assertion could not survive and was
  reworked into a structural witness (no manifest/NUMA/port/server row exists, so no
  gated branch can fire; every compile output byte-identical to the pre-lane state).
  The safety property therefore changed from **two independent barriers (no code AND
  no data) to one (no data)**: a single data edit adding a `PORT_MAP`/`ROLE_LAUNCH_META`
  row now suffices to make live code fire. That is a deliberate tradeoff, named
  explicitly so a later reader does not assume the old, stronger property.
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **An idle MI210 does not imply a startable lane — measured, not inferred.** The
  lane's host threads pin to SMT siblings 184-191 → physical cores 88-95 → atomic
  region `q3`, so starting it requires holding `q3`'s flock, the same lock production
  CPU roles take. Observed 2026-07-28: `q0`/`q1` held by frontdoor, `q2` free, `q3`
  held by a `bench-e8-quality` run — while `rocm-smi` simultaneously reported VRAM 0%
  and no KFD PIDs. The GPU was entirely idle and the lane was still not startable.
  Activation waits for the `q3` holder to quiesce-and-drain at its own boundary and is
  never forced (fabric axiom 4).
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **Tenant landing (P2-2) closed on two of three tenants, and P2-2 itself is NOT
  closed.** All three D2 tenants were already on disk, so the pass required zero
  downloads and the `curl -C -` resume-corruption hazard was off the critical path.
  Dense-27B stock is **verified landed** by an independent local re-hash
  (28,665,067,072 B, sha256 `5927dc06…43897b2a`) rather than a restatement of the
  existing attestation. MiniCPM-o's artifacts verified against both runbook P4 hashes
  (plus a newly-recorded audio-F16 hash, out of runbook scope). But the MiniCPM-o
  *promotion* (P2-2c, Steps 1-6) is **not executable**: runbook precondition P7 FAILS
  because no fleet port is listening, and Step 2 forbids a manual mode override in
  exactly that case. That is a genuine constraint, not a preference — the executable
  deliverable was the proposal, and no file in either repo was edited.
  [p2-2-tenant-landing-readiness](../docs/reference/p2-2-tenant-landing-readiness-20260729.md)

- **The third tenant is blocked by a capability gap D2 did not anticipate, and the
  operator deferred rather than fixed it.** Measured on the actual runtime: the
  deployed whisper is faster-whisper large-v3-turbo on **CTranslate2 4.7.2, which has
  no ROCm/HIP backend** (`cuda_devices 0`); `whisper_server.py:61-62` hard-codes
  `device="cpu"`. whisper.cpp is not on this host. Critically, **D2's "~1.6 GB" was
  the CTranslate2 directory's disk footprint — the size of a model that cannot execute
  on the device — never a measured MI210 VRAM figure.** Blast radius is fail-safe: the
  np_ceiling `phase2_resident_set` rows bake that 1.6 GB in, so if whisper never lands
  those budgets are *conservative*, under-stating available VRAM; no ceiling
  over-authorises and no cell needs withdrawing. The operator chose **W3 (defer)**;
  whisper is refiled as P2-9 downstream of the bake-off, with W1 (stays on CPU) the
  standing recommendation and W2 (port to whisper.cpp on HIP) explicitly ruled out for
  now. A comment-only banner was added at the head of
  `gpu_shadow_lane_np_ceiling.yaml` specifically to block the obvious wrong reaction —
  "whisper isn't landing, so free up its 1.6 GiB."
  [p2-2-tenant-landing-readiness](../docs/reference/p2-2-tenant-landing-readiness-20260729.md),
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **"One artifact = one tenant = one policy row; identity is (path, bytes, sha256),
  never a flag on a shared row."** The rule was adopted after a near-miss whose failure
  mode is silent-wrong-answer: FF-MTP is a *separate GGUF* (30,239,022,560 B, 866
  tensors = 851+15) from its non-MTP sibling (29,787,701,792 B, 851 tensors). Modelling
  MTP as a flag on one shared row would have sized the tenant at 27.74 instead of 28.16
  GiB — a wrong number with no error anywhere.
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **Lane admission priority orders admission, never eviction — and the shed-batch class
  is partially self-defeating.** §3.2 states explicitly that a higher class may be
  admitted ahead of queued work and may stop new lower-priority admissions, but may NOT
  interrupt a request already decoding, at any priority; reclaim stays quiesce-and-drain.
  This is spelled out because "priority queue" ordinarily implies preemption and here it
  must not. Separately, the shed-batch class's premise ("CPU is stressed, move batch work
  to the GPU") is undercut by the lane not being a pure GPU resource: its host threads sit
  on `q3`'s physical cores, so shedding consumes CPU in the region most likely contended
  under CPU stress. Net benefit is `(GPU gained − q3 CPU lost)` and is **never measured**.
  Classes 3-4 flags are reserved but deliberately *not registered* in `src/features.py`,
  on the reasoning that a flag for an unbuilt feature reads as "someone can turn this on".
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **The slot fabric is being amended by the program, not replaced — and it has a named
  hole.** The tie-in program is the ACTIVE execution vehicle; the heterogeneous-slot-fabric
  handoff remains DESIGN-GATED and is the axiom source the program cites by name (the GPU
  gets its own non-blocking flock rather than a CPU pseudo-region per axiom 1; `force_release()`
  raises by construction per axiom 4). The amendment recorded 2026-07-29: **GPU host threads
  are an implicit consumer the fabric does not model** — no slot, no lease, no epoch, so
  quiesce-drain cannot cover them — and the fabric must not be finalised without closing it.
  The fabric's own contract was separately generalized (2026-07-27) into a resource-admission
  blueprint spanning the orchestrator CPU placement layer and the session bus, with the
  axiom-1 consequence stated sharply: **observing holders is not exclusion (TOCTOU); only
  acquiring is.**
  [heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md)

- **Activation sequencing is decided (D11, hybrid "sign-off last") but not executed.**
  Order: P2-2 tenant landing → Steps 0-7 choreography → the P3-1/P3-2 bake-off starting on
  the **incumbent 184-191 placement** (with a placement-pending caveat on absolute latency
  and token economics) → the P2-5j placement sweep folding into the P2-5c campaign →
  placement + carve + residency decided *together* at the verdict → **P3-3 production
  sign-off last**. Both irreversible acts (minting a carve, production sign-off) sit after
  the sweep. [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

### Open Questions (2026-07-29)

- Nothing in Phase 3 has run, so the lane's serving characteristics are entirely unknown:
  the bake-off's own published MDEs (~0.20 SWE / ~0.19 LCB / ~0.13 critic) say the critic
  duty is the discriminating signal and the coder case will likely turn on token economics
  — but that is a design expectation, not a result.
- P2-2c (MiniCPM-o Steps 1-6) needs the fleet up *and* a runbook P1 operator grant; until
  then P2-2 stays open.
- The P2-5 decision rule has an explicit unbuilt dependency chain: E8 signature → AutoPilot
  resume → stress duty cycle becomes measurable → complexity threshold settable → rule
  executable. AutoPilot is currently down. The stress duty cycle is measured nowhere, and
  measuring it under present conditions would wrongly close the shed-batch class on a
  measurement artifact.
- Does whisper belong on the MI210 at all (W1 vs W2)? Deliberately unanswered until the
  bake-off numbers exist.

### Source References (2026-07-29)

- [gpu-serving-tie-in-program.md](../handoffs/active/gpu-serving-tie-in-program.md) — ratified
  decisions D1-D11, the shadow-only invariant and its structural enforcement, the P0-7→P2-1c
  witness degradation, the `q3` coupling, tenant/policy identity rule, admission-not-eviction
  contract, and the Phase-3 gates.
- [p2-2-tenant-landing-readiness-20260729.md](../docs/reference/p2-2-tenant-landing-readiness-20260729.md)
  — independent re-hash of all three tenants, runbook P1-P7 verdicts (P7 FAIL, no fleet port
  listening), and the whisper capability blocker with its fail-safe blast-radius analysis.
- [heterogeneous-slot-fabric-residency.md](../handoffs/active/heterogeneous-slot-fabric-residency.md)
  — the target architecture and axiom source; the 2026-07-29 GPU-host-threads gap; the
  resource-admission-blueprint generalization.
- [progress 2026-07-29](../progress/2026-07/2026-07-29.md) — the D11 decision, the W3
  execution and P2-2 rescope, and the pre-reboot state in which none of this is activated.
## Compiled Update — 2026-07-26 E8 rebaseline hold

Production remains frozen on `production-consolidated-v8`; the post-freeze E8
quality boundary is a fail-closed rebaseline, not a stack change. The quality
fence and empty-frontier bootstrap receipts are complete and AutoPilot was
re-armed on the unchanged frozen-v8 both-mode lineup with only
`kv_compaction` suppressed. At this checkpoint the numeric frontier remains
in progress (`7/16`); its exact-stop `16/16/0` boundary precedes the human-only
quality-baseline evidence/apply path and the Laguna Q4 CPU lane. No registry,
lineup, or serving-kernel conclusion is implied.

### Source References (2026-07-26 E8 rebaseline hold)

- [AutoPilot decision-plane audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md) — ratified receipts, re-arm state, and remaining numeric/quality gates.
- [Post-v8 master handoff index](../handoffs/active/master-handoff-index.md) — CPU/GPU campaign ordering and frozen-kernel constraints.
- [Progress 2026-07-26](../progress/2026-07/2026-07-26.md) — checkpoint count and human-only apply boundary.
- [AutoPilot digest 2026-07-26](../progress/2026-07/2026-07-26-autopilot.md) — current numeric-trial activity; it does not override the checkpoint's exact-stop gate.
- [Bulk inference campaign](../handoffs/active/bulk-inference-campaign.md) — related post-v8 campaign context; no additional serving conclusion was promoted from this source.
## Compiled Update — 2026-07-24

The operator ruled the v7-cutover's quarters-only launch an **accidental regression**, not a ratified design, and the CPU lineage restored the big+quarters lineup same-day behind a new additive, no-outage promotion path. In parallel, the WP-12 server-fleet layer (one `ConcurrencyAwareBackend` per physical fleet, replacing N per-role URL/CAB copies) flipped live, and its case-10 acceptance gate surfaced a load-bearing finding about how within-role concurrency actually works in production. Confidence: `verified` for the landed/flipped code and the measured live gates; `observation` for the E5 scout numbers referenced below (pre-cert, direction-only — see [Hardware Optimization](hardware-optimization.md)).

### Key Findings (2026-07-24)

- **The "quarters-only" v7 lineup was a mistake, not the design — restored same day via a new additive promotion primitive.** Operator ruling (verbatim intent): every role runs a full-performance instance *plus* quarter instances for concurrent aggregate boost; exclusivity is a **dispatch-time thread-overlap property** (region locks), not a launch-time mode choice. `orchestrator_stack.py` gained `start --only <role> --numa-mode both` (`_only_mode_transition_allowed`): over an already-quarters-live fleet it launches **only the missing big instance**, skip-healthy, zero outage to running quarters. Executed for all three quarterable fleets — worker_general 8072 (full, interleave), frontdoor 8070 (NODE0 half), ingest_long_context 8085 (NODE0 half) — sequentially, three-gates green (pipeline + 183-test promotion suite + live affinity + solo-dispatch-lands-on-big verified per fleet). J2/J3 KV-migration replay then PASSED on the restored lineup: forward=6, reverse=1, committed=7, aborted=0. [stack-lineup-dossier-2026-07-23](../handoffs/active/stack-lineup-dossier-2026-07-23.md), [within-role-placement-state-machine](../handoffs/active/within-role-placement-state-machine.md)

- **A 5-agent read-only archaeology settled a genuine operator-recall vs. git-history conflict — both sides were partly right.** The operator recalled "2 halves + 4 quarters" per role and a 192-thread architect; git history showed the fulls were deliberately dropped at v7 cutover (mode-exclusivity contract 2026-07-21, `full_disabled`). Resolution: **the launch-time drop was real and deliberate** (accurate history) **but was never operator-ratified intent** — hence "accidental." Separately, **"2 halves per role" was never a committed config** — the one live 2-half event (2026-05-26, certified affinity) was an ad-hoc experiment that measured **negative** (co-run ratios 0.455–0.541: two 48-core halves contend on the memory channels serving the shared mmap'd weight pages) and was reverted same day. The architect has always been -t 96 physical-only, never 192 threads; `worker_vision` ran 4 quarters for ~90 minutes once (2026-05-24) and was deliberately reverted with a regression-test pin (flat scaling, 11.39 vs 11.30 t/s — model too small to benefit). [stack-lineup-dossier-2026-07-23](../handoffs/active/stack-lineup-dossier-2026-07-23.md)

- **WP-12 fleet layer flipped live; its case-10 acceptance gate found that production within-role concurrency comes from OS process fan-out, not the role-concurrency semaphore.** `ServerFleet`/`RoleBinding` (one CAB per physical fleet, one breaker/lock identity per endpoint, same-fleet fallback compiled to a no-op) merged and flagged live (`ORCHESTRATOR_FLEET_LAYER=1`) after 33/33 acceptance + 53/53 regression. The live case-10 burst probe (worker_math, 4-wide) passed cleanly — 4 disjoint busy quarters, fleet identity on every dispatch, zero same-fleet fallback — but surfaced **C10-F1**: `live_warm_worker_slots()` filters `tier=="warm"`, and every live production role is `hot`, so `get_role_max_concurrency()` resolves to **1 for every role**; the in-process `Semaphore(1)` therefore serializes each role fully **per API worker**. The real within-role concurrency mechanism in production is **6-uvicorn-process spread × cross-process region flocks**, not a role-level concurrency cap of N — a single-worker API test artifact (staircase completion times) had been silently misread as semaphore behavior. A follow-up flag (`ORCHESTRATOR_FLEET_ROLE_CONCURRENCY=1`) derives `get_role_max_concurrency` from the realized fleet's disjoint-quarter capacity instead — built and tested, but **default OFF** (raises real in-process concurrency; deploy decision), timed to enable **after E5** so every E5 comparison and the R3 eval-lane baseline describe one consistent lane. [wp12-fleet-layer-design](../handoffs/active/wp12-fleet-layer-design.md), [batched-decode-measurement](../handoffs/active/batched-decode-measurement.md)

- **The inference-batch `/loop`'s runnable island stays empty; ownership of the CPU-gated residuals formally transferred.** All remaining manifest entries are operator/build/model-download gated. A **parked-island decision menu** was written for one-word operator approvals: ROUTE-A1 (shape-keyed step-2 smoke) recommended parked until post-E5 (its design may be reshaped by E5's R4 capability rows); ROUTE-A2 (edit-transaction A/B) recommended folded into the architect-bench Phase-2 SWE-bench corpus effort (same multifile-edit task family, one corpus for two consumers); RE-4 (LongCoT-Mini calibration, floor-saturated 0/402+0/307 under answer-only grammar) recommended a suffix-extraction redesign (free reasoning + a terminal `solution = X` line + a new `structural_exact_match` scorer) over LLM-judge extraction or dropping the entry. Ownership of A2/RP-5 (fenced CPU 122B-Q4 architect arm — see [Quantization](quantization.md)) and RE-4 transferred to the CPU lineage as the operator moved GPU-only. [inference-batch-loop](../handoffs/active/inference-batch-loop.md)

### Open Questions (2026-07-24)

- `ORCHESTRATOR_FLEET_ROLE_CONCURRENCY` stays off pending the post-E5 window — will enabling it change the R3 eval-lane baseline enough to require a second re-measure, or does one combined re-baseline suffice?
- The dual-half 2026-05-26 negative result is pre-v7-era (kernel + model era both changed since) — does E5's C1b cell (2×half) confirm or overturn the contention physics under the current kernel? (The E5 W0 scout, see [Hardware Optimization](hardware-optimization.md), suggests confirm-but-model-dependent.)
- Registry `server_mode` primaries still point at ports the fleet layer no longer needs verbatim (8070/8072/8085 vs realized quarters-plus-big) — reconciliation deferred to WP-13/14 cleanup.

### Source References (2026-07-24)

- [stack-lineup-dossier-2026-07-23.md](../handoffs/active/stack-lineup-dossier-2026-07-23.md) — 5-agent archaeology + operator override + same-day restoration; per-role intended/configured/realized table; reader-contradiction resolution.
- [wp12-fleet-layer-design.md](../handoffs/active/wp12-fleet-layer-design.md) — fleet-layer design, flip-boundary execution, case-10 live gate, C10-F1/F2 findings.
- [within-role-placement-state-machine.md](../handoffs/active/within-role-placement-state-machine.md) — DESIGN CONTRACT (full/quarters mutual exclusivity is dispatch-time), WP-12 checkbox closure, J2/J3 restored-lineup pass.
- [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md) — parked-island decision menu, ownership transfer.
- [progress 2026-07-23](../progress/2026-07/2026-07-23.md) — restoration execution log, WP-12 flip-boundary sequence, case-10 evidence.
## Compiled Update — 2026-07-21

### Addendum (same day, evening): within-role placement fixed end-to-end (DISPATCH-A/A2/A3)

Operator-driven investigation ("four healthy NUMA-pinned quarters should decode concurrently")
uncovered a three-layer serialization stack, fixed in orchestrator `99dd6c92`+`570200ff`+`5408109f`:
(1) the dispatcher emitted the all-region full candidate first while the live 4-quarter stack had a
quarter **impersonating the full slot** — each worker_general decode held all 4 per-role + all 4
GLOBAL cross-role mutexes, blocking **every role machine-wide** ~26s/request (invisible production
head-of-line); (2) the placement filter consumed an attribution holder view that phantom-reported
the full → all disjoint quarters queued; (3) the misaligned full stranded one quarter and shifted
region-locks off their physical cores (cross-role collision hazard). Fixes: policy-aware candidate
construction + alignment guard, exact held-regions filter, and misaligned-full **demotion** to its
true topology index. Result: first-ever 4-wide same-role decode (EV-11c live on all four quarters),
mode-exclusivity design contract recorded (full/half XOR quarters; burst abandons the big
instance). Operational lessons: eval client needs reconnect backoff (a mid-run API reload burned
~680 questions as connect-errors); SIGSTOP-the-runner is the correct mid-run deploy procedure;
`real_mode:true` is required on manual /chat probes (request-level mock default).

**Source References (addendum):** `handoffs/active/within-role-placement-state-machine.md`
(contract + WP-8..11), `coordination/inference-batch/op-bundle.md` (DISPATCH-A row),
`progress/2026-07/2026-07-21.md` (DISPATCH arc), orchestrator commits `99dd6c92`/`570200ff`/`5408109f`.

The inference-batch `/loop` — the single-writer execution vehicle over a 52-entry manifest — completed a clean overnight burn-down and a takeover session that **exhausted the live runnable island**, while a companion **loop-robustness audit** corrected the root cause of the EV-4 stall and hardened the loop against a whole class of topology-change regressions. The load-bearing correction: the EV-4 failure was **not** the v7 kernel cutover — it was the **2026-07-17 `vision_escalation` NUMA rebind (5 instances → 1)** shipping without a contention-matrix recert, which had been silently degrading production cross-role concurrency ever since. Confidence: `verified` for the landed loop/runner/preflight fixes (each with coordination-suite tests) and the terminal ledger outcomes; `observation` for the EV-4 baseline still in flight.

### Key Findings (2026-07-21)

- **Overnight burn-down terminalized 5 entries, then the live island went empty.** DONE_PASS: `BULK-K-EMB-1` (Granite-97M-r2 Phase-B embedder bench — Granite Q8_0 recall@10 0.9333 vs BGE-M3 0.9000, e5-base 0.8444), `ROUTE-A3` (single-worker within-role KV-migration probe), `BULK-hermes-smokes` (13/13 including 2/2 parallel subagents on one :8099 slot), plus `BULK-langgraph-tm7-parity` after **four** attempts. DONE_MARGINAL_OBS: `BULK-kbrag-autowiki-k11` (lexical-weight sweep 0.1-0.3 matched ColBERT-only recall@10 0.5048 exactly → keep `lexical_weight=0`). The takeover session then parked the last two "runnable" entries as mislabeled: **ROUTE-A1** build-gated (`_drive_admit_overlap_probes` is a `NotImplementedError` stub) and **ROUTE-A2** data-gated (no `multifile_edit` corpus on disk) — both first-attempt invalid-passes caught by the `b216fe0f` artifact-validation hardening. Every remaining entry is now operator/build/model-download gated. ([inference-batch-loop](../handoffs/active/inference-batch-loop.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md))

- **The runner-robustness audit found the EV-4 failure was three stacked defects, root-caused to a NUMA rebind, not the kernel.** `topology_fingerprint` hashes only `(cpu_list, port, threads)`, so a pure kernel swap cannot move it — a *measured-role NUMA change* did (old shape `df373c79…` → live `8c8cfcbb…`). The stale matrix had, since 2026-07-17, been **silently degrading production cross-role concurrency**: `contention_gate` fail-closes background decode to `QUEUE` and foreground to `DEGRADED_ALLOW` whenever `matrix_health() != OK`, visible only in a counter. On top of that the runner silently degraded fanout→concurrency=1, then a killed partial serial run left a dirty stack plus a decision-grade-*looking* empty result. ([eval-tower-loop-robustness-audit-2026-07-20](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md))

- **The loop is now hardened against the whole topology-change class, not just kernel promotions.** Landed + verified: the live v7 contention matrix was **re-measured** (15 cross-role pairs on `8c8cfcbb…`, never rehashed — a hash-only bump would certify wrong geometry); the `INFRA_BLOCKED` permanent wedge was broken (`pending()` now re-picks `INFRA_BLOCKED`/stale-`RUNNING` under `retry_policy`); the runner got try/finally + SIGINT/SIGTERM rollback (a killed run always rolls back `eval_batch_serving=1` + `:18070` and writes `summary.json{status:interrupted}`); `decision_grade` is gated on `n_questions>=expected` + `n_scored>0`/`reliability>0` (a degenerate/empty eval no longer returns `decision_grade=True, rc=0`); matrix-freshness + topology-cert became a first-class precondition for *every* `*_eval_fanout` entry regardless of reload; `host_health.py --remediate` was pointed at `flush_cache_with_pause` (not bare `drop_caches`, which pins one NUMA node); and CI + stack-start now bind the committed matrix hash to live `NUMA_CONFIG`. The change-hardening rule (§H) is general: recertify topology-dependent artifacts (matrix, placement caps, entry `required_topology_hash` pins) on any measured-NUMA-role change — a kernel promotion is just one caller. ([eval-tower-loop-robustness-audit-2026-07-20](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md), [inference-batch-loop](../handoffs/active/inference-batch-loop.md))

- **ROUTE-A3 closed the live within-role KV-migration probe** — ratifying the placement state machine's session-handover path under real traffic. Final single-worker frontdoor probe: forward=6 / reverse=4 live KV-migrations, `n_aborted=0`, `sessions_over_cap=[]`, one cooldown-guard skip; matrix fresh; focused migration suite 74 passed; API restored to `--workers 6`. This is the under-traffic evidence the 2026-07-20 placement-SM update flagged as still-needed (it had only been verified in-process). WP-3/WP-4 flipped; WP-6/WP-7 full ratification stays open. ([inference-batch-loop](../handoffs/active/inference-batch-loop.md), [within-role-placement-state-machine](../handoffs/active/within-role-placement-state-machine.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md))

- **EV-4 launched two-phase after an honest concurrency refusal.** Post-B7 a READY row was appended; the first execute was refused by the B2/B5 guard because worker_general's true topology cap is 1 (J5-measured min_ratio 1.005) and the entry still carried the pre-truthful `--min-eval-concurrency 3`. It was rewritten as two sequential per-role phases — frontdoor@3 then worker_general `--allow-serial` (intentional, recorded) — and is now RUNNING as the first decision-grade-capable calibration baseline on the E7 instrument. The refusal is the design working: the runner's forced-role concurrency resolver takes the min safe cap across the roles a fanout will actually hit. ([inference-batch-loop](../handoffs/active/inference-batch-loop.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md))

### Open Questions (2026-07-21)

- WP-6/WP-7 full ratification of the placement SM still needs sustained under-traffic forward/reverse migration observation beyond the single ROUTE-A3 probe.
- The remaining manifest backlog is entirely operator/build/model-download gated (RCP prologue OP-6a/6b + stack-restart, PaddleOCR-VL download, multifile-edit corpus, ThinkPRM/GLM downloads) — no agent-runnable serving entries remain in the current quiet window.
- Does the §H topology-recert discipline need a standing pre-commit/stack-start check for *placement caps* and *batch-entry pins* too, or only the contention matrix (matrix leg landed; the other two artifacts are checklist-only)?

### Source References (2026-07-21)

- [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md) — single-writer `/loop`, 52-entry manifest, overnight terminal rows, live-island-exhausted takeover, EV-4 two-phase relaunch, quiet-window discipline.
- [eval-tower-loop-robustness-audit-2026-07-20.md](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md) — EV-4 three-defect root cause (stale matrix ← vision NUMA rebind), production cross-role concurrency degradation, and the Cluster A-D + §H change-hardening fixes.
- [within-role-placement-state-machine.md](../handoffs/active/within-role-placement-state-machine.md) — placement SM whose session-handover KV-migration path ROUTE-A3 ratified under traffic.
- [progress 2026-07-21](../progress/2026-07/2026-07-21.md) — ROUTE-A3 evidence row, the takeover reconciliation, and the EV-4 launch log.
- [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md) — the E1/E2/E5 batched-decode serving-class context the loop's eval-fanout entries exercise.
## Compiled Update — 2026-07-20

The serving layer gained a **live within-role placement state machine**, decision-grade **single-instance batched-decode** economics, and a **heterogeneous CPU×GPU slot-fabric design** that generalizes (not replaces) the placement machinery. The load-bearing constraint across all three: `_migrate_kv` **cannot preempt an in-flight llama-server decode** — every migration/teleport is session-handover / turn-boundary.

### Key Findings (2026-07-20)

- **Within-role full↔quarter placement state machine is LIVE** (WP-0..WP-5 merged behind flags). `max_safe_concurrency` per role from cpuset-disjointness: frontdoor/ingest/vision = 3, worker_general/architect = 1. It queues-instead-of-overlaps, and migrates sessions transactionally on handover (forward WP-3 + reverse WP-4) with anti-thrash (cooldown + recency window + per-session cap). J1 gate (verified): 3-way frontdoor **1.68×**, 4-way **1.91×** aggregate, no overlap collapse. Per-role policy ratified: frontdoor/worker_general/vision = `burst_prefer_quarters` (worker_general -t48 re-bench 0.77–0.95 after a launcher over-threading fix `da1aed6`; vision quarter-pairs super-linear 1.14–1.27×, full+quarter blocks → full-disabled-under-burst). ([within-role-placement-state-machine](../handoffs/active/within-role-placement-state-machine.md))
- **Single-instance batched decode (E1/E2, P-BENCH-3, decision-grade CPU window):** the A3B eval primitive **saturates early** — aggregate `-np 2 ≈ -np 8 ≈ -np 16` (~29 t/s) while tail p95 rises sharply after `-np 2`; the dense control scales more strongly through `-np 8`. E2: a single `-np 8` batch server is **4.86× faster by wall-minutes/eval** than the current 3-concurrent EvalTower fan-out → keep-candidate for a dedicated eval-batch serving class (default-off `eval_batch_frontdoor` on :18070 + feature flag landed; activation smoke passed then rolled back cleanly). Caveat: MoE batching is weaker than dense (distinct tokens hit distinct experts → expert-weight traffic grows with batch). E3 8x8 GEMM batch>1 body = NO-GO (decode BW-killed). ([batched-decode-measurement](../handoffs/active/batched-decode-measurement.md))
- **E5 NUMA×batch is the never-measured 2D cross** (specced, post-promotion, runs LAST in `inference-batch-loop → architect-bench → E5`): directly tests whether one big high-`-np` server beats quarter-batched servers, and whether workload-class lanes (low-K latency vs high-K throughput) are real. It sets the slot-fabric grid shape. ([batched-decode-measurement](../handoffs/active/batched-decode-measurement.md))
- **Heterogeneous CPU×GPU slot fabric is a DESIGN, not greenfield** (gated post-v7-promotion + post-E5 + operator). It models the whole machine as one slot fabric — CPU = `N×K` (NUMA instances × `-np`), GPU = `1×K_gpu` — so teleport, residency-swap, and spillover are all slot operations. It **reuses** the live `ConcurrencyAwareBackend`/`ContentionGate`/`NUMA_CONFIG`/KV-migration/anti-thrash machinery and its **no-mid-decode-preemption / session-handover** constraint; new work is only the GPU-as-placement-target, a Layer-2 residency actuator (the ONLY VRAM-touching op, allowlist + hysteresis + kill-switch), and an N-dwell swap hysteresis `N ≥ C·(1−X)/X` (~6.3 min at C=20s/X=5%). Governing principle: **the GPU accelerates; the CPU guarantees** (every GPU model has a designated CPU fallback). ([heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md))
- **Inference-batch loop** is the single-writer `/loop` execution vehicle over a 52-entry manifest; the current lead island is eval-tower EV-4, while OP-2/GLM-reviewer entries were superseded by the 2026-07-19 readiness work. Quiet-window-gated; never competes with the parallel inference session. ([inference-batch-loop](../handoffs/active/inference-batch-loop.md))

### Open Questions (2026-07-20)

- Live under-traffic forward/reverse migration observation still needs a single-worker API (`--workers 6` confounds per-worker session affinity; the state machine is verified in-process).
- Slot-fabric provisioning `(N,K)` per model, the CPU "N quarters vs 1 full pool" question, and whether workload-class lanes exist all wait on E5.

### Source References (2026-07-20)

- [within-role-placement-state-machine.md](../handoffs/active/within-role-placement-state-machine.md) — live placement SM, per-role policy ratification, no-mid-decode-preemption constraint.
- [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md) — E1/E2 batched-decode economics, eval-batch serving class, E5 spec.
- [heterogeneous-slot-fabric-residency.md](../handoffs/active/heterogeneous-slot-fabric-residency.md) — CPU×GPU slot-fabric design extending the live fabric.
- [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md) — single-writer campaign loop + quiet-window discipline.
- [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md) — MI210 fleet-placement sequencing (residency → eval-engine → embedder → prefill offload → drafter farm).
## Summary

The production inference serving stack runs 9+ llama-server instances plus 2-4 auxiliary services, organized into HOT/WARM/COLD memory tiers on a single AMD EPYC 9655 machine with 1.13 TB RAM. The architecture follows a hierarchical local-agent workflow: one model thinks (architect), many models work (workers), and tools decide who is right. This is speculative decoding applied at the system level -- a strong model sets the trajectory, cheap models propose artifacts in parallel, and correctness is enforced by gates rather than agreement.

The server topology maps models to agent tiers. Tier A (frontdoor, Qwen3.6-35B-A3B) handles interactive chat, intent classification, and task routing through the shared frontdoor/coder server. Tier B specialists handle code escalation through `coder_escalation`, long-context synthesis through `ingest_long_context`, and terminal architecture through `architect_general`; the former distinct `architect_coding` live role is retired and now normalizes to `architect_general` only for compatibility. Tier C workers provide parallel burst capacity with auto-scaling. The entire stack is managed by orchestrator_stack.py, which handles sequential startup, health monitoring, NUMA-pinned launching, and granular component reload.

The orchestrator uses a hierarchical configuration system with 15 independent feature flags backed by pydantic-settings. Production mode enables all flags; test mode defaults to all-off for isolation. Critical environment variables redirect all caches, temp files, and data to the RAID array -- the 120 GB OS drive must never receive large writes. Request routing uses round-robin distribution for multi-instance models (frontdoor 4x, coder 4x), with escalation driven by gate failures (lint, typecheck, unit tests), repetition detection, context overflow, or explicit TaskIR directives.

Recent architectural improvements include REAP MoE expert-pruning evidence for the now-retired coding-architect path, attention-matching KV compaction (L1-L4 merged to production-consolidated-v3), and concurrent inference sweeps that determined optimal -np settings per role (frontdoor gets np=2, dense models stay at np=1 due to p95 latency degradation).
## Key Findings

### New Findings (2026-07-16) — refreshed v7 readiness checkpoint and server-launch guard

- **Refreshed experimental v7 `53f6e30a1` is the current serving-side checkpoint, and its N5 semantic dry preflight blocks only on a live `llama-server` process.** The current artifact is `/mnt/raid0/llm/epyc-inference-research/data/specdec_frontdoor_alpha/n5_retest_v7_semantic_preflight_20260716T181836Z/preflight.json`; it no longer reflects the earlier `8e5c555ab` / `180801Z` precommit snapshot. Sources: [GPU-Drafter on MI200 investigation](../handoffs/active/gpu-drafter-mi200-investigation.md), [Progress 2026-07-16](../progress/2026-07/2026-07-16.md).

- **Launcher hygiene for stack-launched CPU roles now explicitly hides ROCm devices when the launcher is HIP-capable.** The orchestrator guard appends `--device none` for normal launches and `--device-draft none` for speculative launches so fresh server state does not inherit accidental GPU visibility. Source: [Gemma challenge kernel techniques v7](../handoffs/active/gemma-challenge-kernel-techniques-v7.md).
- **The serving-side N5 readiness checkpoint was superseded by the final execute artifact once the patched v7 candidate landed.** The earlier `53f6e30a1` semantic preflight only proved the stack was blocked on a live `llama-server`; after `da1bf5e2f` fixed `draft-tree` output capacity, the rebuilt `llama-server --version` reports `10077 (da1bf5e2f)` and the execute summary at `/mnt/raid0/llm/epyc-inference-research/data/specdec_frontdoor_alpha/n5_retest_v7_execute_20260716T190836Z/summary.json` is `decision_grade=true`. Sources: [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md), [Progress 2026-07-16](../progress/2026-07/2026-07-16.md).
- **Qwable's first bounded task-quality slice is now closed on both MI210 and CPU, and it does not separate IQ4_XS from Q8_0 on this tiny deterministic set.** The server/chat runner compared the two quants on six tasks and both arms passed `6/6` on MI210; the measured decode rates were `112.15 t/s` for IQ4_XS and `113.62 t/s` for Q8_0. The CPU repeat also passed `6/6` for both, with IQ4_XS decoding faster than Q8_0. This is bounded task-quality evidence only, not a production role-quality claim; the next gate is routing codification plus a broader representative quality suite. Sources: [model-admission-2026-07-16.md](../repos/epyc-inference-research/docs/reference/models/model-admission-2026-07-16.md), [model-smoke-queue-2026-07-16.md](../repos/epyc-inference-research/docs/reference/models/model-smoke-queue-2026-07-16.md), [Progress 2026-07-17](../progress/2026-07/2026-07-17.md).
- **K35.3a registry drift is now closed in the live serving registry path.** Research `ingest_long_context` now uses default-expert Qwen3-Next with `acceleration.type: none`, the stale server-mode model string was corrected, and the orchestrator lean registry/model descriptors/stack priors/current-stack summary were regenerated from the master registry. Validation evidence: the research registry validator reports `0 error(s)` with only pre-existing off-disk catalogue warnings, `stack_change_pipeline.py check --allow-known-gaps --allow-production-blocker-waivers` passes, the focused no-inference promotion suite passes (`181 passed`), and the serving path no longer carries `qwen3next.expert_used_count`. Sources: [Gemma challenge kernel techniques v7](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [Progress 2026-07-17](../progress/2026-07/2026-07-17.md)

### New (2026-07-07 — E1 dense-control sweep completed; eval-batch serving activation window smoked and rolled back cleanly)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. Sweep numbers below are observations without decision-gating protocol citations.

- **E1 dense-control sweep now has useful-but-not-pristine evidence for the 27B dense model.** The `qwen36_27b_q8` P-BENCH-3 `-np 1,2,4,8,16` sweep with `GGML_IQK=1` completed all `43/43` cells with `0` errors. Tasks/hour scaled `20.11 → 124.62` (≈6.2×), aggregate predicted t/s `1.07 → 6.81`, and p95 latency rose `240.9s → 674.0s`. Because the MI210 server remained live, the run used `--skip-clean-check --allow-host-health-warning` and is classified as useful evidence, not pristine decision-grade. The earlier attempt without `GGML_IQK=1` was aborted and recorded as `ABORTED_UNACCELERATED_ENV.json`. Sources: [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

- **Eval-batch serving activation window smoked through and rolled back cleanly — mechanism is working, awaiting quality/eval telemetry.** The 2026-07-05 activation window of `eval_batch_frontdoor` (port `18070`) completed as `status=smoke_passed_rolled_back`: API workers attested `eval_batch_serving=true`, smoke answer was `ok`, tap hit expected port `18070`, and rollback disabled the feature + stopped the frontdoor. Activation evidence is decision-grade; representative quality/eval telemetry remains the next gate before any default EvalTower path change. The eval-tower window runner (`eval_batch_serving_evaltower_window.py`) is plan-only by default and requires `--apply --confirm-clean-window` for live evaluation. Sources: [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md).

### New (2026-07-04, DS-7 profile decision + dashboard transport hardening)

- **Userspace OOM protection must distinguish control plane from killable workload processes (2026-06-05).** The host earlyoom deployment protects long-lived orchestrator and AutoPilot processes by setting `oom_score_adj=-1000` after stack start, while leaving transient planner/eval subprocesses killable. Because uvicorn and AutoPilot appear as `comm=python`, process-name ignore rules are insufficient; the durable protection belongs in launcher code (`stack_processes.set_oom_score_adj` and the AutoPilot start path) plus a host-level earlyoom rule that ignores llama-server/sd-server and prefers disposable benchmark processes. Sources: [progress 2026-06-04](../progress/2026-06/2026-06-04.md), [earlyoom-oom-protection.md](../handoffs/completed/earlyoom-oom-protection.md).
- **Three RAM-reclaim mechanisms are distinct and must not be conflated; the stack deliberately pre-warms rather than lazy-loads (2026-06-21).** The serving stack proactively pre-warms ~22 instances at ~653 GB resident with `mlock`, accepting the memory cost to eliminate cold-start latency for a single-user interactive workload. That makes wholesale on-demand lazy-loading (the drove model) an anti-pattern here, not an improvement. RAM is reclaimed by three orthogonal levers that operate at different scopes: (1) **earlyoom** is the reactive last-resort ceiling that kills disposable processes under pressure; (2) **DS-6 quarter-eviction** reassigns quarter cpusets on an idle timeout but does NOT free model weights (the process and its `mlock`'d pages stay resident); (3) the proposed **DS-7 idle-teardown profile** is the only mechanism that frees whole-process RAM, by tearing down COLD/RARE roles (e.g. `sd_server`, `document_formalizer`) after idle, and is explicitly never applied to hot pre-warmed roles. DS-7 idle-teardown is an optional, evidence-gated profile, not a default. Sources: [dynamic-stack-concurrency.md § Research Intake 2026-06-20](../handoffs/active/dynamic-stack-concurrency.md), [intake-701 (drove)](https://github.com/cleanunicorn/drove).
- **A GPU serving tier is now live: the MI210 (gfx90a) is installed and the fork's HIP build leg is verified, opening a latency tier above the CPU stack (2026-07-02).** The MI210 (CDNA2, 64 GB HBM2e, ROCm 6.2 bind-mount) passed into the devcontainer and llama.cpp's HIP build works on gfx90a from an isolated `production-consolidated-v6` worktree (`-DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a`); one fp8-guard fix was required because ROCm 6.2 ships only `_fnuz` fp8 types (OCP landed in 6.3). The design intent is explicitly additive — the GPU lifts the hot frontdoor + drafter path into the 100+ t/s regime while architect and workers stay CPU-resident at their already-competitive 20-50 t/s baseline; the MI210 does not replace the NUMA CPU serving tiers. All first-pass GPU numbers are OBSERVATIONS (contended host), not decision-gating per MEASUREMENT.md. Sources: [gpu-drafter-mi200-investigation.md § 2026-07-02 Advancement](../handoffs/active/gpu-drafter-mi200-investigation.md), [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md).
- **The GPU story mirrors the CPU one-kernel discipline: llama.cpp-HIP is the production GPU binary; vLLM is a measurement instrument, not a second deployment engine (2026-07-02).** Just as the 2026-06-26 v6 cutover consolidated CPU inference onto one kernel, the GPU path is a single production binary (llama.cpp-HIP, native ggml-cuda + rocWMMA + MFMA, loads GGUF). vLLM is stood up only to answer one question — do its gfx90a kernels beat llama.cpp's roofline ceiling — because vLLM (0.10.1 and even current v0.22.0) does not support the 2026 `gemma4`/`qwen35` architectures and can never be the frontdoor/worker engine for current models. Matched-precision Qwen3-8B fp16 head-to-head: per-stream decode llama.cpp-HIP 62.45 t/s vs vLLM ~69 t/s (+11%); batched 32-way llama.cpp-HIP 909.8 gen tok/s vs vLLM 1129 out tok/s (+24%); both scale ~15-16x from single stream. vLLM's decisive edge is batched serving, not per-stream. Sources: [2026-07-02 ROCm MI210 vLLM deep-dive](../research/deep-dives/2026-07-02-rocm-mi210-vllm-gfx90a.md), [gpu-drafter-mi200-investigation.md § vLLM comparison](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **GPU-side MTP speculative decoding is demonstrated end-to-end and qwen35 decodes clean on the HIP path, localizing the CPU spec-dec failures to the CPU codepath (2026-07-02).** gemma-4-31B-it-Q4_K_M plus its 514 MB NEXTN head both offloaded to ROCm0 via llama-server (`--spec-type draft-mtp -ngl 99 --spec-draft-ngl 99`) decoded at 43.25 t/s = 1.44x over plain (30.01 t/s) at 59.7% draft acceptance (mean accept length 2.79 of n_max=3) — direct Stage-4/head-on-GPU evidence. Separately, Qwen3.6-27B (arch `qwen35`, gated-delta-net + full attention) decoded clean at 28.69 t/s with `-ngl 99` and no M-RoPE/GDN failures, in sharp contrast to the CPU external-draft/tree-spec qwen35 crashes: the v6 fork's GPU delta-net kernels prove the qwen35 forward pass is fine and the failures live in the CPU speculative codepath. This does not by itself supply the frontdoor drafter α number (N5 gate). Sources: [gpu-drafter-mi200-investigation.md § 2026-07-02 Advancement](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **On gfx90a, the enabling kernel stack covers the card but the accelerator libraries do not — a gfx90a vLLM is a reference-kernel build, and Vulkan is impossible (2026-07-02).** Triton (`pytorch-triton-rocm`, first-class gfx90a), FlashAttention-2 (CK default + Triton opt-in, ROCm 6.0+), and vLLM's `PYTORCH_ROCM_ARCH` all include gfx90a; but AITER, MORI, and DeepEP are `gfx942;gfx950` only, so an MI210 vLLM falls back to reference Triton/CK kernels rather than AITER's hand-tuned CDNA3 paths — which is exactly the fair comparison against llama.cpp's own reference-maturity gfx90a kernels. Vulkan is definitively impossible on CDNA2 (RADV enumerates zero devices; no ICD targets the compute-only Instinct family), complementing the earlier GT 1030 falsification: HIP/ROCm is the only GPU path. Sources: [2026-07-02 ROCm MI210 vLLM deep-dive § gfx90a support matrix](../research/deep-dives/2026-07-02-rocm-mi210-vllm-gfx90a.md), [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **MoE-Spec (budgeted-expert verification) is a proven CPU serving mechanism with no live consumer, because the frontdoor runs zero spec-dec today (2026-06-12 portfolio pass).** The training-free technique aggregates routing scores across a spec-dec verification batch, top-B selects experts, and masks the rest before `argsort_top_k` — measured +15.2% forward-pass / +3% end-to-end on REAP-246B at B=40 (robust across builds) and +7.3% on Coder-30B at B=64 (not robust across builds/cache states). But the REAP role was removed from the production stack, the Coder result did not survive PGO, and the frontdoor launches with no `-md`/`--spec-type` flag at all — so there is nowhere to deploy `moe_spec_budget`. Reopen is chained to first enabling frontdoor spec-dec and measuring α on its actual verification batches; do not schedule registry integration on the released gate alone. Sources: [moe-spec-cpu-spec-dec-integration.md § Current State](../handoffs/active/moe-spec-cpu-spec-dec-integration.md), [gpu-drafter-mi200-investigation.md § Gating Measurement](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **The OpenAI `/v1/audio/transcriptions` ASR facade is a shipped first-class managed service (2026-06-21).** `whisper_server.py` exposes an OpenAI-compatible transcription endpoint and `start_whisper` is a managed member of `orchestrator_stack`, alongside the existing detached `whisper` launch path. This means the drove-style "OpenAI-compatible proxy fronting a local ASR worker" pattern is already realized in production rather than a gap to close; only drove's process-lifecycle idea (the DS-7 idle-teardown profile above) survives as a candidate. Sources: [dynamic-stack-concurrency.md § Research Intake 2026-06-20](../handoffs/active/dynamic-stack-concurrency.md), [intake-701 (drove)](https://github.com/cleanunicorn/drove).
- **The DS-7 profile decision retains static pre-warm and parks DS-6 QuarterScheduler (2026-07-04).** `scripts/server/dynamic_stack_evidence_packet.py` now reports `ready_for_profile_decision=true` in `ds_e1_evidence_packet_20260704T192333Z.{json,md}`: stack roster, DS-5 manifest freshness, RI-10 canary evidence, contention matrix, and direct production KV-size measurements all pass. The DS-7 decision artifact `ds7_profile_decision_20260704T194020Z.{json,md}` records `stack_templates/default.yaml` as `steady_state_static_prewarm`, validates it with `python3 scripts/server/orchestrator_stack.py start --stack-profile default --validate-only` (`17` roles, `28` instances, `657` GB), and parks DS-6 until future evidence shows static pre-warm leaves material throughput or latency on the table. The drove findings carry no benchmarks — they are observations from a tiny single-maintainer project, not decision-gating numbers. Sources: [dynamic-stack-concurrency.md § Start Here / Outstanding Tasks](../handoffs/active/dynamic-stack-concurrency.md), [intake-701 (drove)](https://github.com/cleanunicorn/drove).
- **Stack lifecycle helpers should be direct imports once circularity is removed.** The `stack_commands.py` cleanup moved away from lazy wrapper duplication for checkpoint and MemRL/tool initialization paths, keeping `orchestrator_stack.py` as the CLI shell while reusable process/checkpoint helpers live in focused modules. This preserves the operator-facing command surface while reducing import-shape drift for registry/compiler fallback tests. Sources: [progress 2026-06-04](../progress/2026-06/2026-06-04.md), [routing-and-optimization-index.md](../handoffs/active/routing-and-optimization-index.md).

- **Dashboard activity counts must use exact holder-instance accounting, not region-overlap attribution (2026-05-31).** The scheduler-facing `active_region_holders()` projection intentionally marks every configured instance whose region set overlaps a held lock; that is useful for admission/placement overlap checks, but it over-reports display activity. On a single-slot MTP worker holding all four quarter locks, the attribution view can surface `worker_general: [0,1,2,3,4]`, making the topology/contention panel show "×5 active" for one request. The dashboard-facing contention metrics now use `active_region_holder_instances()`, which groups held region locks by `(role, PID)` and resolves the exact region set to one configured topology instance, so the same worker reports `worker_general: [0]` while admission behavior remains unchanged. [progress 2026-05-31](../progress/2026-05/2026-05-31.md)
- **Cross-role contention must be keyed to physical CPU regions, not just role pairs (2026-05-31).** A live dashboard/tap discrepancy showed `frontdoor.half0` streaming on q0/q1 while `worker_general.full` held q0-q3: same-role/full waits were serialized, but cross-role admission remained placement-blind and allowed a physically overlapping decode. The rollout now has two default-off/staged layers: Step 1 stages `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` in `orchestrator_stack.py` so the next reload arms a role-agnostic `cpu_region.GLOBAL.{qN}.lock`; Step 2 wires dispatch to evaluate the shape-aware gate against each real `candidate_topology_idx` when `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` is explicitly enabled. No live reload was performed during the active autopilot run, so production traffic was unchanged. [shape-keyed contention handoff](../handoffs/active/shape-keyed-contention-gating.md), [progress 2026-05-31](../progress/2026-05/2026-05-31.md)
- **Live-panel staleness is a delivery-path property; a health check that only stats producer files is structurally blind to it (2026-07-05).** The recurring "tap/locks/topology stale AGAIN" reports all had healthy producers and a green `/dashboard/api/health` — the failures lived in one shared serve path (an unbounded 29-port `/slots` fan-out + per-tick region-locks/ps recomputation coupling exactly those three panels) and in client transport wedges (a poll with no fetch timeout behind a jam-forever in-flight flag; a monotonic frame watermark with a client-clock fallback and no reset; SSE-only tap content), all repeatedly re-rolled by AutoPilot restarting the API at every trial boundary. The durable design rule adopted: every failure must be self-healing or loudly visible — bounded fan-out deadlines with degradation counted in the payload (`slots_poll_meta`), TTL caches that fail open to last-good marked `stale_cache`, a 15s client watchdog that rebuilds the stream and fires a poll, per-worker serve-path vitals + an on-demand `?probe=snapshot` real-build check in health, self-clearing in-panel error chips, and a SIGKILL-mid-SSE chaos test as the regression guard. Sources: [progress 2026-07-05 dashboard transport hardening](../progress/2026-07/2026-07-05-dashboard-transport-hardening.md), [loops-and-dashboards audit § P1 dashboard sweep](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), `epyc-orchestrator/src/api/routes/dashboard.py`, `epyc-orchestrator/tests/integration/test_dashboard_restart_recovery.py`.
- **Freshness verdicts must compare like-for-like scopes: a full-topology hash checked against a measured-subset artifact produces false STALE (2026-07-05).** The contention gate reported `matrix_status: stale` and the operator queued a quiet-window re-bench — but the measured-role hash (`df373c79cc4af06f`) still matched; the live check hashed the full `NUMA_CONFIG` including the auxiliary `eval_batch_frontdoor` role the matrix intentionally excludes. The fix (codex session, orch `3d1706c6`+`120498c9`) centralizes a measured-role-subset topology helper in `src/scheduling/contention.py` and aligns the gate, validator, SafetyGate/EvalTower consumers, and the re-bench tool's validate path to it — saving a quiet window that would only have restated existing evidence. Pattern: before spending measurement time on a "stale instrument" verdict, verify the staleness detector compares the same scope the instrument actually measured. Sources: [contention-matrix-v6-quarter-refresh.md](../handoffs/completed/contention-matrix-v6-quarter-refresh.md), [progress 2026-07-05 dashboard transport hardening § second wave](../progress/2026-07/2026-07-05-dashboard-transport-hardening.md), `epyc-orchestrator/src/scheduling/contention.py`.
- **Completed-task output recovery must not depend on a fixed tail of the structured inference tap (2026-05-31).** Under eval load, `inference_tap_events.jsonl` reached 2.3 GB, so a 1 MB tail covered only seconds of history and older completed tasks rendered as "no output collected" even though their answers were fully present. The dashboard now reverse-scans the tap in bounded chunks for the task's own lines, exits once it has passed the task block, and falls through to rotated siblings. The structured tap now size-rotates under the existing flock, defaulting to a 512 MB cap and three retained files. [progress 2026-05-31](../progress/2026-05/2026-05-31.md)
- **Frontdoor streaming requests must preserve registry chat-template options (2026-05-28).** The frontdoor/coder_escalation shared `8070` instance was healthy under direct probes only when `chat_template_kwargs.enable_thinking=false` was present. The streaming `/v1/chat/completions` adapter had not forwarded the registry `chat_template_kwargs`, unlike the non-streaming path, so Qwen thinking mode could consume the request budget, produce empty streams/timeouts, trigger slot erases, and trip circuit breakers. Fixing the streaming adapter dropped the same bounded `/chat` smoke from about 85.5s to about 10.8s, with llama-server reporting 22.78 t/s raw decode. [progress 2026-05-28](../progress/2026-05/2026-05-28.md)
- **Stack-managed long-lived children must be detached and preserved durably (2026-05-28).** `orchestrator_stack.py` now launches llama-server branches and document_formalizer with detached stdio/session handles, matching the already-hardened uvicorn/sd/whisper paths. Healthy pre-existing listeners are recorded as `ProcessInfo` instead of transient dicts that state persistence drops, stale-port cleanup uses listener-only PID discovery, and state-empty scans now include warm, NUMA replica, Docker, and native auxiliary ports. This prevents "started OK, died when launcher exited" and "healthy service invisible to later stop/status" failure modes. [progress 2026-05-28](../progress/2026-05/2026-05-28.md)
- **Server-URL defaults now follow live worker truth.** `src/config/models.py` no longer carries a separate hardcoded worker URL fallback; the config helper now resolves the canonical worker-general path before falling back, so the compatibility default stays tied to the live worker server rather than a duplicated literal. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [Model Stack Single-Source Update Pipeline](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/config/models.py`, `tests/unit/test_config_consolidation.py`.
- **Dashboard service hints now read `worker_fast` from the live manifest.** `src/api/routes/dashboard_topology.py` stopped hardcoding the `8102` service hint and now derives the `worker_fast` port from `scripts.server.stack_manifest.PORT_MAP` when present. That keeps dashboard fallback labels aligned with current service truth instead of a stale literal and removes the standalone service-port fallback from the helper. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [Model Stack Single-Source Update Pipeline](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/api/routes/dashboard_topology.py`, `tests/unit/test_dashboard_helpers.py`.
- **Hierarchical routing dramatically reduces average latency**: Most tokens are generated by simple expansion (frontdoor/workers at 19-50 t/s), not complex reasoning (architects at 4-7 t/s). Only gate failures or explicitly hard tasks escalate to expensive models. [02-orchestration-architecture.md]
- **Sequential model loading is mandatory**: Concurrent mlock crashes the system. Servers start with 5-second cooldown between large models. Vision servers need 90-120s timeout for mmproj + main model loading. [04-production-server-stack.md]
- **Concurrent inference sweep results**: Frontdoor (30B MoE) benefits from np=2 (+121% aggregate TPS, p95 multiplier 1.33). Dense 32B coder rejected at np=2 (p95 multiplier 1.98). Worker 7B rejected at np=2 (p95 multiplier >= 1.505). [04-production-server-stack.md]
- **ORCHESTRATOR_CASCADING_TOOL_POLICY must be set**: Without this env var, the legacy tool permission path denies ALL roles ALL tools because no role has tool_permissions defined in model_registry.yaml. This caused seeding stalls before being fixed on 2026-03-03. [01-runtime-environment.md]
- **REAP MoE expert-pruning evidence is historical, not current serving truth**: A 246B REAP-pruned model replaced the full 480B coding-architect experiment, but the distinct live `architect_coding` role was later retired. Current serving/routing docs should treat REAP rows as historical evidence unless projected into generated descriptors/stack priors. [completed/reap-moe-expert-pruning.md]
- **KV compaction active**: Attention-matching L1-L4 merged to production, enabling passive KV cache compression without orchestrator changes. AM compact is passive-by-default. [active/attention-matching-kv-compaction.md]
- **Qwen3.5 serving requires special care**: lookup causes segfault on hybrid SSM models after 1-3 prompts. No speculation of any kind should be used on hybrid models -- all draft configs are net-negative. moe6-only is stable. [numa-orchestrator-deployment.md]
- **Worker pool architecture evolved significantly**: The 7B f16 worker was replaced by Qwen3-Coder-30B-A3B Q4KM after benchmarks proved it was both 2x faster (39.1 vs 19.2 t/s) and higher quality at similar RAM. [progress/2026-03-21]
- **Round-robin routing implemented**: RoundRobinBackend wraps multi-instance backends using comma-separated URLs. Frontdoor (4 instances) and coder_escalation (4 instances) distribute requests round-robin. Least-loaded routing is a future optimization. [numa-orchestrator-deployment.md]
- **Infrastructure failures produce no reward**: Timeouts, connection errors, and backend-down events are classified separately and excluded from Q-value updates. This prevents slow or flaky backends from biasing routing probabilities. [08-cost-aware-rewards.md]
- **Auxiliary services**: NextPLAID (multi-vector code/doc retrieval, ONNX INT8), LightOnOCR (PDF OCR, 19x PDF speedup), BGE embedder pool (6 instances, probe-first). [04-production-server-stack.md]
- **Qwen3.6-35B-A3B is now the completed production frontdoor upgrade path.** Byte-for-byte identical architecture to Qwen3.5-35B-A3B (same `qwen3_5_moe` model type, same 10x(3xGDN->MoE -> 1xAttn->MoE) pattern). All improvements are post-training only -- no llama.cpp patches needed beyond existing Qwen3.5 support. Performance: 25.6 tps baseline, 27.4 with ngram dm=64 (+10.1%), 57.4 quad-instance, 76.8 eight-instance. Q8 is faster than Q4 (25.6 vs 24.4). Key benchmarks: SWE-bench +3.4pp (73.4), Terminal-Bench +11pp (51.5), NL2Repo +8.9pp (29.4). `preserve_thinking` feature works via `--jinja` flag. The handoff has since been archived after rollout completion. [qwen36-production-upgrade.md](../handoffs/completed/qwen36-production-upgrade.md)
- **llama.cpp v3 production swap delivered large per-role gains (2026-04-10, Package F).** The v3 binary (upstream-merged PRs including #21038 Hadamard auto-rotation and paged-attention registry-driven config) replaced production v2 after a 5-task smoke test. Per-role throughput vs v2 baseline:

| Role | Model | v2 t/s | v3 t/s | Δ | Notes |
|------|-------|--------|--------|---|-------|
| worker_general | Qwen3-Coder-30B-A3B Q4KM | 39.0 | 38.6 | −1% | Noise-level regression |
| frontdoor | Qwen3.5-35B-A3B Q4KM moe6 | 12.7 | 14.3 | **+13%** | Single-instance baseline; 4× NUMA aggregate scales accordingly |
| coder | Qwen2.5-Coder-32B + 0.75B draft | 10.8 | 21.7 | **+101%** | Spec-dec path received largest benefit |
| architect_coding | REAP-246B + draft | 8.0 | 12.0 | **+50%** | Pruned MoE + draft stack |

  Hadamard rotation auto-enables in v3 when KV types are quantized (PR #21038 landed upstream as `744c0c731`); the orchestrator's prior custom `--kv-hadamard` flag is redundant and was removed. Paged attention is registry-driven via `paged_attention.enabled_threshold_gb` — no `--paged-attention` CLI flag needed. The swap was binary-only; no config or model changes. [bulk-inference-campaign.md § Package F](../handoffs/active/bulk-inference-campaign.md), [completed/llama-cpp-v3-upstream-rebuild.md](../handoffs/completed/llama-cpp-v3-upstream-rebuild.md)

- **Model-specific serving configurations are critical for correct behavior (2026-04-19).** Five new models each required unique configurations not documented in the codebase. Universal findings: (1) Gemma4 models need `use_chat_api + repeat_penalty 1.05 + reasoning off + KV q8_0` to avoid degenerate repetition (70-83% of responses without fix) and thought leakage; (2) Qwen3.6 needs `use_chat_api + reasoning off` to avoid `<think>` loops; (3) M2.7 needs `--jinja` for correct template (37% training data leakage without it) and must NOT use repeat_penalty (caused 52%->27% regression); (4) SG4-26b Q4KM proved irrecoverable (16.2%) due to fundamental MoE expert routing degradation at Q4 -- model deprecated and GGUF deleted. The benchmark infrastructure now supports per-model `disable_thinking`, `repeat_penalty`, and `reasoning` flags. [progress/2026-04-19](../progress/2026-04/2026-04-19.md)
## 2026-06-13 Update — Serving Gaps After Fable 5

Fable 5 confirmed the batch=1 CPU decode closure at the kernel level but found a serving-level evidence gap. The system has mature multi-instance concurrency: NUMA quartering, placement state machine, per-region locks, cross-role disjoint placement, measured contention matrix, session affinity, and reverse migration. What remains unmeasured is the eval/harness serving class: single-instance continuous batching and CPU14 `-np` sweeps were never run despite the dominant workload now being independent eval questions.

The decisive next measurements are E1/E2 from the kernel/concurrency handoff: run `-np {1,2,4,8,16}` on frontdoor and a dense control, then A/B a T1 eval against a single full instance with continuous batching versus the current cross-quarter fanout. If that shows intermediate-batch decode is not per-thread bandwidth saturated, only then write the missing 8x8 GEMM SIMD body. This separates "batch=1 closed" from "batch/eval serving untested."

Frontdoor speculative decoding is another unharvested config path. It is not a general GPU-drafter endorsement; it is the first cheap measurement that unlocks or kills several downstream hypotheses, including MoE-Spec reuse on frontdoor verification batches.

Sources: [Fable 5 kernel and concurrency](../handoffs/completed/fable5-findings-06-kernel-and-concurrency.md), [routing truth restoration](../handoffs/completed/routing-truth-restoration.md).
## 2026-06-13 Update — Stack-Prior Serving Truth

The stack-update audit established `stack_priors.yaml` as the generated serving contract for model-specific consumers. The live truth hierarchy is: orchestrator `server_mode` plus descriptors first, generated priors as the consumer contract, and research-registry/history only as provenance until explicitly projected. This matters because raw compatibility surfaces can still mention retired roles and dead ports while live serving has moved on.

Concrete current examples: frontdoor and `coder_escalation` share the Qwen3.6 server and memory owner on port `8070`, while older maps and config compatibility fields can still mention retired `8084` surfaces. Consumers that need endpoint, slots, tier, shared mmap, context, launch binary, or memory accounting should read the generated serving record or a typed helper over it; direct role/port tables are acceptable only as documented degraded fallback or legacy fixtures.

Follow-through on 2026-06-13 moved this from policy to working guardrails in active serving consumers. Vision ReAct routing now reads `worker_vision` and `vision_escalation` endpoints from stack priors, shared `server_mode` alias-port drift is caught by `validate_against_registry()`, and AutoPilot preflight health probes are generated from live stack-prior serving URLs instead of a static health-port table. The stack-prior contract now also projects launch ports, effective launch context, launch requirements, runtime/binary/KV/flag witnesses, GGUF-derived model context, architect/REAP quality, and structured thinking-control evidence. Shared-runtime alias mismatches are preserved as `role_bindings.alias_overrides` in descriptors and `evidence.alias_overrides` in stack priors rather than as `known_gaps`, so generated descriptors and stack priors now compile cleanly. A 2026-06-15 N11 cleanup refreshed active escalation docs and diagrams so current topology terminates at `architect_general`; the all-surface stack-change warning count dropped from `36` to `29` unique, with historical-doc warnings `25 -> 18`. Remaining serving-truth work is residual historical-doc/waived-fixture cleanup, descriptor-native projector/measurement refinements, high-risk consumer migrations, and swap-CI before stack changes can be fully data-only.

The 2026-06-19 wrap-up re-audited AutoPilot `health_preflight_probes` after the consumer migrations. The live preflight path already derives model-server targets from stack-prior serving URLs, while its degraded fallback intentionally consumes stack-manifest HOT/WARM auxiliary metadata and launch-mode filtering. That fallback is compatibility plumbing, not a duplicate role/port table to migrate. The same pass recorded that full stack-change checks with runtime attestation can legitimately stop while the isolated K-MEM Tulving benchmark owns stack port `8080`; generated-contract and guard checks remain the correct no-inference validation during that measurement window. A follow-up simulated worker swap witness now also proves seeding reward degraded fallback consumes swapped model descriptor throughput before the legacy static table.

Sources: [model-stack-update-pipeline-audit.md](../handoffs/active/model-stack-update-pipeline-audit.md), [standardized-stack-update-pipeline-finalization.md](../handoffs/active/standardized-stack-update-pipeline-finalization.md), [progress 2026-06-13](../progress/2026-06/2026-06-13.md).
## Actionable for EPYC

- **Current deployed stack** has evolved beyond the 2026-04-13 snapshot: the later Qwen3.6 consolidation moved frontdoor, coder_escalation, and worker_summarize onto shared Qwen3.6-35B-A3B Q8 mmap, and Probe B rewired architect_general to a 1x96t canonical full-machine layout. Keep the older list below as historical context only.
- **Total RAM footprint**: ~515 GB with multi-instance copies (reduced from ~701 GB after coder f16-to-Q4KM decision). Leaves ~429 GB for KV caches and OS.
- **Dynamic NUMA-aware concurrent routing** is planned but not yet implemented -- event-driven allocation based on conversation lifecycle, queue depth, escalation events, and idle timeouts.
- **Autopilot should dynamically assemble the orchestrator stack** based on workload rather than static configuration. Single-user constraints noted.
- **Monitoring**: All servers expose /health endpoint. orchestrator_stack.py status shows component health, model, port, and PID. State persists to orchestrator_state.json for graceful recovery.
## 2026-06-15 Update — Generated Serving Truth

- **Serving truth now comes from generated stack priors.** The live contract for ports, launch shape, and role aliases is projected into the generated stack-prior view, and the major consumers now read that generated truth instead of stale handwritten role/port tables. Sources: [model-stack-update-pipeline-audit.md](../handoffs/active/model-stack-update-pipeline-audit.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md).
- **OpenAI `/v1/models` degraded fallback now follows the live manifest, not a frozen role tuple.** When no live stack-prior role IDs are available, `src/api/routes/openai_compat.py` now derives the fallback `/models` list from current `HOT_ROLES` / `PORT_MAP` membership at call time, keeping the compatibility surface aligned with stack truth. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md).
- **OpenAI `/v1/models` degraded fallback now tracks computed server lists.** The fallback path in `src/api/routes/openai_compat.py` now reads `HOT_SERVERS` / `WARM_SERVERS` for its compatibility role list, so the degraded surface follows the same computed launcher topology used by the CLI/status and AutoPilot preflight fallbacks while still preferring live stack-prior records when available. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/api/routes/openai_compat.py`.
- **OpenAI `/v1/models` generated-prior ordering now reuses the shared primary-port helper.** `src/api/routes/openai_compat.py` no longer keeps a route-local stack-prior port resolver; it calls the shared serving helper used by other stack-prior consumers, while preserving explicit endpoint precedence and the compatibility alias order. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/api/routes/openai_compat.py`.
- **Chat-completions degraded fallback now uses launch classes instead of a static role set.** `src/chat_completions_roles.py` still prefers generated stack priors (`jinja=true` and `enable_thinking=false`), but when priors are unavailable it walks computed `HOT_SERVERS` / `WARM_SERVERS` order and admits only manifest launch classes known to use server-side chat templates in the current stack: the frontdoor shared process and the `worker_pool` explore process. Architect, ingest, vision, embedding, and warm fast-worker launch modes are excluded. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/chat_completions_roles.py`.
- **CLI status and AutoPilot preflight now fall back through computed server lists instead of a role→port table.** `src.cli_orch.cmd_status()` and `scripts.autopilot.preflight_audit` now derive degraded probe/health targets from `HOT_SERVERS` / `WARM_SERVERS` while still preferring live stack-prior records when they exist. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/cli_orch.py`, `scripts/autopilot/preflight_audit.py`.
- **AutoPilot KV-compression fallback ports are manifest-derived and dynamic.** `scripts/autopilot/kv_compress.py` still prefers generated stack-prior serving records for KV-compaction targets, but its degraded fallback now derives from the live stack manifest and the legacy `PRODUCTION_PORTS` compatibility surface resolves through a dynamic helper rather than an import-time snapshot. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `scripts/autopilot/kv_compress.py`.
- **Inference-tap safe-mode streaming policy is no longer an import-time snapshot.** `src/runtime/inference_tap.py` still prefers generated stack-prior memory facts and keeps the explicit manifest fallback, but `should_stream_role()` now resolves the safe non-stream role set at decision time so stack-prior or threshold changes are not frozen when the module imports. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/runtime/inference_tap.py`.
- **Inference-lock exclusive/shared role policy is no longer an import-time snapshot.** `src/runtime/inference_lock.py` still prefers generated stack-prior launch facts and keeps the explicit manifest fallback, but `_is_heavy_role()` now resolves the lock role sets at decision time so stack-prior or manifest changes are not frozen when the module imports. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/runtime/inference_lock.py`.
- **Chat-routing heuristic priors now degrade through the computed stack manifest.** `src/api/routes/chat_routing.py` still prefers generated stack-prior live role records, but when those records are unavailable it builds the heuristic-prior candidate universe from `HOT_SERVERS` / `WARM_SERVERS`, excludes embedding launch entries, and canonicalizes aliases instead of falling back to a fixed role tuple. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/api/routes/chat_routing.py`.
- **Admission degraded fallback now derives URL/slot limits from the computed stack manifest.** `src/api.admission` still prefers generated stack-prior serving slot limits, but empty or malformed priors now recompute fallback limits from `HOT_SERVERS` / `WARM_SERVERS` at controller construction time instead of using an import-time static URL table. Embedding services are skipped so they do not participate in request admission. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/api/admission.py`, `tests/unit/test_admission.py`.
- **Benchmark seeding topology fallback now degrades through the lean registry.** `scripts/benchmark/seeding_types.py` still prefers generated stack priors for default roles, role ports, model ports, and heavy-port classification, but if priors are unavailable it derives degraded topology from `orchestration/model_registry.yaml` `server_mode` records instead of a static current-stack role/port table. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `scripts/benchmark/seeding_types.py`, `tests/unit/test_seeding_types_state.py`.
- **Bilinear cold-start routing model specs now degrade through model descriptors.** `orchestration/repl_memory/bilinear_scorer.py` still prefers generated stack-prior model facts, but when priors are unavailable it derives `params_b`, MoE status, and quant bits from compiled model descriptors instead of a fixed role/model feature table. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `orchestration/repl_memory/bilinear_scorer.py`.
- **GraphRouter training fleet fallback now degrades through model descriptors.** `scripts/graph_router/train_graph_router.py` still prefers generated stack-prior live role records, but when priors are unavailable it builds offline training fleet nodes from compiled model descriptors instead of a static model-fleet table. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `scripts/graph_router/train_graph_router.py`.
- **Generated stack summaries now canonicalize last-resort degraded role rows.** `scripts/registry/render_stack_summary.py` still prefers generated stack priors and then compiled descriptors, but if it must fall back to the raw registry it now emits only canonical current roles or generic chain aliases resolved to canonical roles. Retired serialized aliases and arbitrary auxiliary server-mode names no longer become operator/system-card live-role rows. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `scripts/registry/render_stack_summary.py`.
- **Architect prewarm targets now come from stack priors.** `src/services/escalation_prewarmer.py` derives the live architect endpoint and chat-template model hint from generated stack-prior serving/model records instead of static `ARCHITECT_PORTS` and `ARCHITECT_PORT_MODEL_HINT` tables. The legacy constants remain compatibility/degraded fallback exports only; live graph escalation prewarm should follow generated serving truth. Sources: [progress 2026-06-20](../progress/2026-06/2026-06-20.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/services/escalation_prewarmer.py`.
- **Vision serving role membership now comes from stack-prior launch metadata.** `src.api.routes.vision_serving` derives the live VL role set from generated `serving.launch.modes` / `vision_type` metadata, and the chat vision routes use that helper when resolving VL endpoints and multimodal eligibility. The legacy `VISION_ROLES` export and static VL ports remain degraded fallback compatibility only; a valid generated stack-prior artifact with zero vision launch roles yields no live vision roles instead of silently restoring the legacy pair. Sources: [progress 2026-06-20](../progress/2026-06/2026-06-20.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `src/api/routes/vision_serving.py`, `src/api/routes/chat_vision.py`, `src/api/routes/chat_pipeline/vision_stage.py`.
- **AutoPilot system-card generation fails closed when live stack facts cannot be rendered.** `_render_system_card()` no longer falls back to checked-in `system_card.md` after generator failure. The degraded card says live role, port, tier, throughput, baseline, and trust-boundary facts are unavailable and forbids using historical docs, memories, or old logs as authoritative stack truth until `gen_system_card.py --check` passes again. Sources: [progress 2026-06-19](../progress/2026-06/2026-06-19.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), `scripts/autopilot/autopilot.py`, `tests/unit/test_autopilot_system_card.py`.
- **Stack-template validation now uses live stack-prior role records for retired-role checks.** `src/config/stack_templates.py` no longer keeps a local retired-role denylist; it validates deployable template roles against the generated live-role set, so the last active-code retired-role warning is derived from serving truth instead of a hand-maintained literal list. Sources: [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), [progress 2026-06-15](../progress/2026-06/2026-06-15.md), `src/config/stack_templates.py`.
- **Dashboard contention accounting is now exact per PID, not overlap-attribution by region.** The active-count view groups held locks by `(role, PID)` so one worker no longer renders as a multiplied set of holders just because its region spans multiple quarters. Source: [progress/2026-05/2026-05-31.md](../progress/2026-05/2026-05-31.md).
- **The remaining serving question is still batch/eval serving, not batch=1 decode.** Fable 5 treats the current kernel closure as insufficient to infer continuous-batching behavior, so the next measurements are `-np` sweeps and single-instance-vs-fanout eval A/Bs rather than more same-shape kernel extrapolation. Sources: [canonical-cpu-benchmarking-methodology-draft.md](../docs/publication/canonical-cpu-benchmarking-methodology-draft.md), [public-results-draft.md](../docs/publication/public-results-draft.md).
## Open Questions

- Least-loaded routing (route to instance with shortest queue) would improve latency under uneven load but adds complexity over round-robin. Worth implementing when concurrent user count exceeds 1.
- The 122B architect could run 2 instances (2x96t) for ~2x aggregate throughput if architect becomes a bottleneck. Currently single-instance.
- WARM tier idle timeout of 300 seconds (5 minutes) may be too aggressive for bursty workloads. No telemetry on warm-tier spin-up frequency yet.
- The Qwen3.5 serving recipe (intake-152) from upstream has not been fully evaluated against our NUMA-optimized configuration.
- Tool output compression and context folding handoffs are active but not yet production-deployed, which would reduce token consumption in multi-turn serving.
- Does a future DS-7 whole-process idle-teardown profile for COLD/RARE roles (`sd_server`, `document_formalizer`) recover enough RAM to justify its cold-start re-launch cost on a single-user stack, or does earlyoom's reactive ceiling already cover every realistic pressure scenario? The 2026-07-04 DS-7 decision retained the default static-prewarm profile, so reopening this needs fresh DS-E1-equivalent evidence of material memory pressure or throughput/latency loss.
- What idle-timeout threshold separates "RARE" (idle-teardown candidate) from "WARM" (spin-down to quarter-eviction only) roles? The WARM tier's existing 300s timeout was flagged as possibly too aggressive; an idle-teardown tier would need a longer, separately telemetered threshold.
- Is llama.cpp-HIP's gfx90a decode ceiling (~62% of the 1.64 TB/s HBM roofline at fp16, but only ~33-47% at Q4_K/Q8_0) a genuine CDNA2 reference-kernel limit or a llama.cpp quantized-MMQ-dequant artifact? The fp16 result argues the quantized ceiling is a dequant artifact, but a matched quantized-vs-quantized vLLM comparison (vLLM AWQ/fp8 vs llama.cpp Q4/Q8) has not been run.
- Which GPU roles migrate first once the drafter α is measured — frontdoor residency, eval-engine acceleration, embedder/classifier host, prefill offload, or the drafter farm? Fable 5 re-ranked residency and eval-engine ahead of the drafter farm, but all placements remain gated on the N5 acceptance-rate number that GPU-side qwen35 decode does not by itself supply.
- Does GPU-side MTP head-split for `worker_general` (Gemma4-26B/31B) pay off, given the CPU MTP baseline is already ~77% acceptance-saturated (Stage-0 low-headroom, revised ceiling +10-15%)? The 2026-07-02 gemma4-31B + NEXTN GPU demo (1.44x) shows the mechanism is structurally sound but does not yet isolate the CPU-BW-released component.
- Where can MoE-Spec's budgeted-verification gain actually be deployed now that REAP is off the stack and the frontdoor runs no spec-dec? The mechanism is proven but consumer-less until frontdoor spec-dec is enabled and re-benched on its real verification batches.
## Related Categories

- [Hardware Optimization](hardware-optimization.md) -- NUMA topology and thread allocation determine serving performance
- [Local Inference](local-inference.md) -- llama-server configuration details and GGUF model management
- [Routing Intelligence](routing-intelligence.md) -- MemRL-driven routing decisions between serving endpoints
- [Speculative Decoding](speculative-decoding.md) -- acceleration methods vary per serving endpoint
- [KV Cache](kv-cache.md) -- cache management directly impacts serving memory footprint and latency
- [MoE Optimization](moe-optimization.md) -- expert reduction applied per serving role
## Source References

- [Chapter 04: Production Server Stack](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/04-production-server-stack.md) -- Server topology, memory architecture, CLI operations, concurrent inference sweep
- [Chapter 02: Orchestration Architecture](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/02-orchestration-architecture.md) -- Agent tiers, escalation flows, worker pool design
- [Chapter 01: Runtime Environment](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/01-runtime-environment.md) -- Feature flags, hierarchical config, environment variables, NUMA tuning
- [NUMA Orchestrator Deployment](/workspace/handoffs/completed/numa-orchestrator-deployment.md) -- Deployed configuration, round-robin routing, mlock setup
- [REAP MoE Expert Pruning](/workspace/handoffs/completed/reap-moe-expert-pruning.md) -- historical 246B REAP coding-architect experiment, superseded by live `architect_general` topology
- [Chapter 08: Cost-Aware Rewards](/mnt/raid0/llm/epyc-inference-research/docs/chapters/08-cost-aware-rewards.md) -- Infrastructure error handling, cost normalization per serving role
- [Attention Matching KV Compaction](/workspace/handoffs/active/attention-matching-kv-compaction.md) -- L1-L4 merged, passive KV compression
- [Progress 2026-03-21](/workspace/progress/2026-03/2026-03-21.md) -- Worker swap to 30B-A3B, registry updates
- [Qwen3.6 Production Upgrade](/workspace/handoffs/completed/qwen36-production-upgrade.md) -- intake-387/391, drop-in architecture, throughput benchmarks (25.6-76.8 tps), preserve_thinking feature, quality benchmark in progress
- [Progress 2026-04-19](/workspace/progress/2026-04/2026-04-19.md) -- Five-model quality benchmark campaign, per-model serving config discovery (Gemma4/Qwen3.6/M2.7/SG4), SG4-26b Q4KM deprecation, benchmark infrastructure upgrades
- [Progress 2026-05-31](../progress/2026-05/2026-05-31.md) -- Dashboard active-count over-report fix; exact per-PID holder-instance accounting for contention metrics
- Intake entries: 22 results across intake index and handoffs including Qwen3.5 serving recipe (intake-152), DFlash speculation (intake-158), REAP models (intake-181/184/186), and 7 active/completed handoffs
- [intake-424](https://github.com/m0at/rvllm) rvllm -- Rust/CUDA+JAX/XLA engine, H100 +24% over vLLM at B=128, EAGLE-3 (450M draft K=5), validates no-framework philosophy. GPU-only, reference bookmark for hardware acquisition.
- [rvllm deep-dive](../research/deep-dives/rvllm-gpu-inference-reference.md) -- Benchmark reference data (Gemma 4 31B: 8786 tok/s H100 FP8), CUDA graph capture strategy, draft/target ratio 1.5%
- [Model Stack Update Pipeline Audit](../handoffs/active/model-stack-update-pipeline-audit.md) -- generated stack-prior contract for serving endpoints, ports, slots, hot/warm status, shared mmap ownership, context limits, and launch requirements.
- [Model Stack Single-Source Update Pipeline](../handoffs/active/model-stack-single-source-update-pipeline.md) -- current stack-change warning baseline and active escalation-topology doc cleanup through `8221971`.
- [Progress 2026-06-15](../progress/2026-06/2026-06-15.md) -- N11 doc-only validation that reduced all-surface warnings from 36 to 29 unique.
- [Dynamic Stack Concurrency](../handoffs/active/dynamic-stack-concurrency.md) -- prewarm footprint (~22 instances / ~653 GB / mlock), DS-6 quarter-eviction vs DS-7 whole-process idle-teardown profile distinction, earlyoom complementarity, DS-E1 evidence-packet gate (`dynamic_stack_evidence_packet.py`), and the clean-window KV harness.
- [intake-701 — drove](https://github.com/cleanunicorn/drove) -- local model server manager (lazy-load OpenAI-compatible proxy for llama.cpp + ONNX ASR). External, tiny single-maintainer repo, observations only. Its `/v1/audio/transcriptions` ASR facade is already shipped here (`whisper_server.py` + `start_whisper`); surviving idea = optional DS-7 proactive idle-teardown of COLD/RARE roles. `verdict: adopt_patterns`.
- [GPU-Drafter on MI200 investigation](../handoffs/active/gpu-drafter-mi200-investigation.md) -- the 2026-07-02 MI210 advancement (HIP build verified on gfx90a, GPU-side gemma4-31B + NEXTN MTP at 43.25 t/s/1.44x/59.7% accept, clean qwen35 GPU decode, Qwen3-8B vLLM-vs-llama.cpp fp16 head-to-head), the additive latency-tier thesis (GPU lifts hot frontdoor/drafter path, CPU tiers stay), and the N5 frontdoor-drafter α gate that all GPU placements depend on.
- [GPU Acceleration Path](../handoffs/active/gpu-acceleration-path.md) -- CPU+GPU hybrid MoE serving survey and the MI210-install status header; establishes the GPU serving tier as additive to (not a replacement for) NUMA CPU serving, and the Fable-5 residency→eval-engine→drafter placement re-ranking.
- [2026-07-02 ROCm MI210 vLLM / gfx90a deep-dive](../research/deep-dives/2026-07-02-rocm-mi210-vllm-gfx90a.md) -- the two-binary GPU discipline (llama.cpp-HIP production engine vs vLLM measurement instrument), the confirmed gfx90a support matrix (Triton/FA-2/vLLM-core cover the card; AITER/MORI/DeepEP do not → reference-kernel vLLM), and the ROCm-6.2 fp8/ABI build risks. Cites [intake-759 — ROCm/aiter](https://github.com/ROCm/aiter) (gfx90a absent from matrix; vendor ceiling ref only), [intake-760 — ROCm/triton](https://github.com/ROCm/triton) (first-class gfx90a), intake-761 (ROCm/flash-attention), intake-762 (vLLM Dockerfile.rocm), intake-763 (vLLM v0.6.5 ROCm docs).
- [MoE-Spec CPU spec-dec integration](../handoffs/active/moe-spec-cpu-spec-dec-integration.md) -- [intake-491 (Mamba drafters)], the budgeted-expert verification mechanism (REAP-246B +15.2%/B=40, Coder-30B +7.3%/B=64), and the 2026-06-12 finding that the mechanism now has no live serving consumer (REAP removed, frontdoor spec-dec off). Cites [MoE-Spec arXiv:2602.16052](https://arxiv.org/html/2602.16052v1) and [REAP arXiv:2510.13999](https://arxiv.org/abs/2510.13999).
- [Launcher NUMA-mode gating](../handoffs/completed/launcher-numa-mode-gating.md) -- `--numa-mode {full,quarter,both}` flag (COMPLETE 2026-07-05); default flipped to `quarter` (`01d14301`) so `start --only worker_general` no longer silently launches overlapping full+quarter instances (~1.5× oversubscription, measured 76.5→9 t/s collapse @ load-420 on 2026-05-08).
- [Capability Registry & Promotion](../handoffs/active/capability-registry-and-promotion.md) -- W0 workload-class tagging closed (live `ChatRequest.workload_class`), W2 generated Action-Availability + A-by table adopted, W3 safe role-restart applicator strict-scope hardening (explicit-affected-roles + smoke-check gates, batched-restart trial protocol); W3/W4 gated on `evidence-plane-ledger.md` Phase 1, no capability promoted.
- [Standardized Stack-Update Pipeline Finalization](../handoffs/active/standardized-stack-update-pipeline-finalization.md) -- canonical `stack_change_pipeline.py check --run-promotion-gate` caught stale generated stack-prior `source_artifacts` after launcher/registry source changes (2026-07-04 → 181 tests; 2026-07-05 `a0377110` metadata-only regen → 181 tests); guard inventory `consumer_surface_count=13`, `rule_count=27`, `exceptions: []`.
- [MoE-on-GPU aggregate deployment wins brief](../handoffs/completed/moe-aggregate-deployment-wins-brief.md) -- OBSERVATION-grade (no P-GPU-1, operator production-hold) MI210 gemma-26B-A4B config wins: `-fa 1` for aggregate B≥8 (peak bf16-fa1 @B128 = 1548 t/s, ~2.75× prior anchor), bf16-for-aggregate / Q8-for-single-stream crossover B≈16–24; L1-MoE mmid dispatch and MoE-decode MTP falsified as levers.
- [Progress 2026-07-04](../progress/2026-07/2026-07-04.md) -- DS-7 static-prewarm profile decision, capability-registry W3 strict restart contract, MI210 aggregate campaign summary, v6 `/slots` dashboard-stream regression fix + SSE multiplex.
- [Progress 2026-07-05](../progress/2026-07/2026-07-05.md) -- launcher NUMA default checkpoint (`01d14301`), stack-prior source-fingerprint repair (`a0377110`), AutoPilot current-code-guard restarts.
## 2026-04-23 Additions — Single-instance throughput backlog

Deployment has leaned hard on NUMA 4-way multi-instance aggregate throughput (6.7× frontdoor). This makes concurrent-session aggregate great but leaves single-session interactive use at 14.2 t/s on 30B-A3B — the user-visible slow path. Three new handoffs target single-session decode specifically, under a new backlog index:

- **[CPU Inference Optimization Index](../handoffs/archived/cpu-inference-optimization-index-history-through-2026-06-19.md)** — forward-looking backlog umbrella listing all 14 unimplemented CPU throughput techniques (CPU1–CPU14), with dependency graph, composition matrix, and the 460 GB/s BW ceiling as physical cap. Start gate: CPU3 Phase 0 baseline (uncore counters + barrier profiling on 30B-A3B 192t).
- **[Intra-Process Tensor-Parallel Decode](../handoffs/active/intra-process-tensor-parallel-decode.md)** — the largest single lever: shard each matmul across 12 CCDs with shared-L3 reduction and next-layer prefetch comm-hiding. Closes the 1×instance vs N×instance gap for single-session. Projected 2–5× single-instance depending on NPS mode. Would take 30B-A3B from 14 t/s → 28–70 t/s single-session. No known CPU prior art; GPU TP pattern ported to CPU.
- **[Single-Instance System Tuning](../handoffs/completed/single-instance-system-tuning.md)** — NPS mode audit (NPS2 current, NPS4/L3aaN candidates), THP (`madvise`→`always`), 1 GB hugepages, IRQ affinity, per-CCD sync primitive (replaces GGML global barrier), SMT, weight replication. Projected 15–40% alone. Some items (NPS, SMT) require reboot windows; others are zero-cost sysctls.

Composition: TP × GEMV ukernel × system tuning multiply up to the 460 GB/s BW ceiling. Realistic 2.5× TP × 1.75× ukernel × 1.25× tuning = 5.5× single-instance; stretch 5× × 2.5× × 1.4× = 17.5× but clipped by ceiling on most production models. Beyond the ceiling requires reducing weights-read-per-token (KV work, speculation, sparsity).

What this does NOT replace: the NUMA 4-way multi-instance deployment for concurrent sessions stays. TP sharding changes what "full-speed instance" means; the ConcurrencyAwareBackend routing architecture is unchanged.
## 2026-04-23 late-session update — CPU2 falsified, 96t whole-machine opportunity found

> **Label correction 2026-07-30** (annotation; no measurement changed): this section originally
> called the 96-thread arm "96t pinned to NUMA node 0". `taskset -c 0-95` is **all 96 physical
> cores of the whole machine**, not one node — a node on this NPS4 host is 24 physical cores
> (`node0 = 0-23,96-119` … `node3 = 72-95,168-191`), and even under the NPS2 BIOS live in April a
> node was `0-47,96-143`. The `stack_numa.py` names `NUMA_NODE0` / `NUMA_NODE1` carry the same
> NPS2-era misnomer and each span two NPS4 nodes. The 49.11 t/s result is therefore a
> **full-machine** number, consistent with the 2026-07-30 finding that canonical placement is
> `taskset -c 0-95` + `numactl --interleave=all`. See
> [`numa-placement-defect-20260730`](../handoffs/active/numa-placement-defect-20260730.md).

Phase 0 of the CPU optimization pickup (see `hardware-optimization.md` §2026-04-23 late-session) changes the serving story in two ways:

1. **The 1.75× ukernel factor in the composition above is falsified by measurement**. AVX-512VNNI port of the hottest Q8_0 decode function (`ggml_vec_dot_q8_0_q8_0`) delivered +1.7% end-to-end at 96t (not 1.46×), because quantized decode is BW-bound on this hardware — perf samples inside the dot loop are DRAM-wait, not ALU-bound. Revised composition is 2.5× TP × **1.0× ukernel** × 1.25× tuning = 3.1× single-instance. Still valuable; just smaller.

2. **A new single-instance operating point emerged: 96t on the whole machine** *(originally written "96t pinned to NUMA node 0" — see the correction above).* On Qwen3-Coder-30B-A3B Q4_K_M (canonical baseline), 96t taskset = **49.11 t/s** (quiet host, stddev 0.08) vs production worker_general 1×24t = 39.1 t/s. **+26% single-session decode with zero code change.** Worth a production sweep before the CPU1 TP-sharding Phase 1 prototype (because: simpler to deploy, 0-cost validation, independent of CPU1 outcome).

| Config | Qwen3-Coder-30B-A3B Q4_K_M t/s | Notes |
|---|---|---|
| 1×24t (worker_general current) | 39.1 | Production |
| 1×48t | 39.6 | Barrier-bound, no gain over 24t |
| **1×96t taskset 0–95 (whole machine, all physical cores)** | **49.11** | **+26% vs current production; unmeasured before today** |
| 4×48t NUMA-pinned (frontdoor style) | 95.8 aggregate | Aggregate throughput across 4 sessions |
| 1×192t `--numa distribute --mlock` | 18.7 | Cross-NUMA penalty dominates |

CPU1 TP-sharding (gate passed) would close the 49→95 single-session gap via CCD-local weight sharding + per-CCD pools + reduction-during-barrier-window prefetch. CPU4 per-CCD sync primitive (promoted to HIGH on the 32–45% barrier-cost measurement) is an independent lever that could recover barrier idle time.

Action for `dynamic-stack-concurrency.md` / routing owner: benchmark 1×96t whole-machine (`0-95` + `interleave=all`) under realistic concurrent load; verify KV scaling; verify multi-instance aggregate doesn't regress if adopted as a single-session fast path. Task #10 tracks.
## 2026-04-24 — Concurrent-split sweep dominates: +110% production throughput available

**Bigger finding**: going the OPPOSITE direction from "1×96t single" — splitting the socket into MORE smaller concurrent instances — delivers the largest production gain in this work stream. SMT-paired splits measured:

| Model | 4×48t (current) | Peak split | Aggregate gain |
|---|---|---|---|
| Qwen3.6-35B-A3B Q8 (frontdoor class) | 64.3 | **48×4t = 135.1 t/s** | **+110%** |
| Qwen3.6-27B Q8 (dense hybrid) | 6.6 | **48×4t = 15.4 t/s** | **+133%** |
| Qwen2.5-Coder-32B Q4 (dense) | 13.6 | **32×6t = 20.0 t/s** | **+47%** |

35B-A3B Q8 at 48×4t hits **~100% of the 460 GB/s BW socket roofline**. Dense Q4 peaks earlier (32×6t) because at 48×4t per-instance compute is too small to saturate that instance's BW share. Optimal split is model-specific.

**This is a config-only change to `orchestrator_stack.py`** — replace 4×48t quarters with N×N-phys-SMT-paired instances. Orchestration overhead grows (48 llama-server processes per role × 3 roles = 144 processes); health checks, rolling restarts, log aggregation need updates. Per-session throughput at 48×4t is ~2.8 t/s on 35B-A3B (135/48), so this is strictly for **concurrent workloads** — single-user interactive routes stay on 1×48t or 1×96t.

**Autopilot implications**: `project_autopilot_stack_assembly.md` memory predicted dynamic mode switching would matter. Today validated with hard numbers: the stack should switch between single-session modes (1×48t / 1×96t for ~27 t/s/user interactive) and concurrent-split modes (48×4t for 135 t/s aggregate across N users) based on real-time load.

Deep-dive: `research/deep-dives/cpu-96t-production-sweep-2026-04-24.md`. Auto-memory: `project_concurrent_split_throughput.md`.
## Disaggregated prefill/decode literature audit (2026-04-26)

Research-intake batch indexed the disaggregation lineage: DistServe (intake-459, arXiv:2401.09670, OSDI'24, 4.48× throughput), Splitwise (intake-460, arXiv:2311.18677, ISCA'24, 1.4× at 20% lower cost), Mooncake (intake-472, arXiv:2407.00079, FAST'25, 525% throughput on long-context Kimi production traces). All three split prefill (compute-intensive, latency-tolerant) onto one machine pool and decode (memory-bandwidth-bound, latency-critical) onto another, with KV migration over high-bandwidth back-plane (NVLink / InfiniBand). Foundational scheduler literature also indexed: ORCA (intake-468, OSDI'22, iteration-level scheduling + selective batching — the abstraction underpinning vLLM/SGLang/TRT-LLM continuous batching).

**Tier 2b critique mattered.** Disaggregation can REGRESS 20-30% on small/short workloads (BentoML handbook; vLLM disagg_prefill docs explicitly state "does not improve throughput" — it trades throughput for TTFT/SLO interference reduction). NVIDIA's "Beyond the Buzz" (arXiv:2506.05508, Jun 2025, first systematic study) shows disagg only wins on prefill-heavy traffic + larger models with dynamic rate matching + elastic scaling; static splits lose. EPYC's xGMI inter-socket bandwidth (~64 GB/s/dir) is ~14× lower than NVLink, making the KV-transfer tax proportionally worse on CPU. Single-user CPU regime is the opposite of the multi-tenant GPU regime where DistServe/Splitwise were validated.

**The CPU-appropriate alternative is chunked prefill, not disagg.** Sarathi-Serve (intake-048, OSDI'24, **already_integrated** upstream) achieves the same prefill/decode interference elimination via chunked-prefill + decode-piggybacking hybrid batches — no KV migration, no high-bandwidth interconnect requirement. Sarathi authors explicitly note disagg "could be challenging in the absence of high-bandwidth interconnects." Two CPU backlog tracks now reflect this finding: CPU16 (`numa-prefill-decode-disaggregation.md` — feasibility-gated stub with Tier 2b counter-evidence pre-recorded; Phase 0 = empirical xGMI BW falsification) and CPU17 (`sarathi-serve-cpu-evaluation.md` — chunked-prefill eval, the cheaper path likely to obsolete CPU16). See [`cpu-inference-optimization-index.md`](../handoffs/archived/cpu-inference-optimization-index-history-through-2026-06-19.md) ⚑ START HERE block.
## 2026-04-26 critique-integration addendum

Serving-side CPU optimization now follows a strict wave pipeline:

1. CPU20 protocol gate (benchmark rigor/revalidation)
2. CPU21 + CPU24 attribution (runtime matrix + uncore/fabric counters)
3. CPU22 mechanism work (dynamic MoE load balancing)
4. CPU23 regime matrix (2K/8K/32K + interference), including this Sarathi-serving path

Implication for serving decisions: treat any decode-only or single-regime conclusion as provisional until CPU23 coverage completes.
## Updates — 2026-04-28

This update consolidates dynamic stack concurrency Phases B–D status, revisits the 2026-04-24 concurrent-split throughput finding through the lens of dynamic stack assembly, and indexes SGLang's slot-promotion serving primitives (intake-490) as architectural lessons for hybrid SSM serving on CPU.

### Dynamic stack concurrency Phases B–D done (2026-04-26)

Per [`dynamic-stack-concurrency.md`](../handoffs/active/dynamic-stack-concurrency.md):

- **Phase B (orchestrator pre-warm) — done.** Orchestrator detects upcoming role demand and spawns instances ahead of first request, hiding cold-start (~30-90s for large models).
- **Phase C (KV migration) — done.** Validated the path for migrating KV state across instance boundaries when concurrent split mode is reconfigured. Used by Phase D under load to avoid full prompt re-prefill.
- **Phase D (load-aware mode switching) — done.** Pre-warm + KV migration validated together; the orchestrator can switch between single-session (1×48t / 1×96t) and concurrent-split (48×4t) modes based on real-time queue depth without dropping in-flight sessions.
- **Phase E (autoresearch exploration) — ready.** Exploration of the mode-switching policy space (which thresholds, which quality gates) is queued. Folds into AR-3 Package D as a NumericSwarm parameter sweep.
- **Phase F1 (cross-NUMA anchor pool) — blocked on AM compaction P2 → KVCOMM dependency.** F1 requires KV-compaction-aware migration across NUMA boundaries; AM compaction P2 must land first.

### Concurrent-split throughput +110% gain (2026-04-24 finding)

Recorded earlier in this wiki at the 2026-04-24 section; reframed here through the dynamic-stack lens:

- Qwen3.6-35B-A3B Q8 at 48×4t = **135.1 t/s aggregate** (+110% vs 4×48t baseline 64.3 t/s), saturating ~100% of the 460 GB/s BW socket roofline.
- **Configuration-only change** to `orchestrator_stack.py`; no kernel work, no model change. Routes to concurrent workloads only.
- Single-session interactive routes stay on 1×48t or 1×96t (single-user latency floor). Mode switching is per-role.
- **Implication**: dynamic stack assembly should switch modes based on real-time load, validated empirically by Phase D pre-warm + KV migration. The autopilot's `project_autopilot_stack_assembly.md` predicted dynamic mode switching would matter; today validated with hard numbers and production-deployed via Phases B–D.

### SGLang slot-promotion serving framework (intake-490)

Per intake-490, SGLang ships hybrid Mamba+Attention slot-promotion serving primitives. Indexed as **architectural-lessons reference**, NOT a target adoption:

- **Primitives**: MambaRadixCache (radix-tree cache for Mamba state), layer-ID remap to skip KV for linear layers, CUDA-VMM-backed elastic Mamba/KV pool, PD-disaggregation State Transfer Channel (cross-instance state migration).
- **CUDA / H200 targeted.** TP=2, FP8 weights, CUDA VMM. **None of the kernel-level wins port directly to llama.cpp CPU.**
- **Architectural lessons that translate**: host-RAM accounting on EPYC for hybrid SSM serving (Mamba state has different lifecycle than attention KV; conflating the two in `mlock` accounting causes either over-allocation or false-positive OOM under load). Cross-link to `wiki/ssm-hybrid.md` for hybrid-model serving notes.
- **EPYC verdict**: `adopt_patterns` (extract HybridReqToTokenPool, HybridLinearKVPool, MambaRadixCache, Elastic Memory Pool as **reference design** for host-RAM accounting); NOT `adopt_component`. The CUDA-VMM-backed pool has no CPU equivalent (mmap + numactl is the closest analogue, but the elasticity story is different).
- **Closure-inflation guard**: SGLang validates that hybrid-model serving needs explicit per-state-class accounting. We are extracting the design pattern, not claiming we have a SGLang-class serving framework.

### Sources

- [`handoffs/active/dynamic-stack-concurrency.md`](../handoffs/active/dynamic-stack-concurrency.md) — Phases B–D done, Phase E ready, Phase F1 blocked on AM compaction P2 → KVCOMM
- 2026-04-24 concurrent-split sweep deep-dive: `research/deep-dives/cpu-96t-production-sweep-2026-04-24.md`
- Auto-memory: `project_concurrent_split_throughput.md`
- intake-490 (SGLang slot-promotion serving) — architectural-lessons reference, NOT adopt_component; cross-link to `wiki/ssm-hybrid.md`
## 2026-05-04 Update — architect_general 1× canonical wiring + orchestrator host_prereqs

### architect_general wiring change LANDED

Probe B (2026-05-04) found Qwen3.5-122B-A10B Q4_K_M production wiring (`numa_instances: 2 / numa_ports: [8083, 8183] / --numa distribute -t 96 / 4.3 t/s/instance / 8.6 t/s aggregate`, set 2026-03-29) is suboptimal in BOTH dimensions vs canonical-recipe alternatives:

| Wiring | per-instance t/s | Aggregate | Best for |
|---|---|---|---|
| 1× canonical 96t + c2 env | 12.19 ± 0.05 | **12.19** | single-user, slots=1 (+184% per-request) |
| 2× per-NUMA-node 24t + c2 | 4.19, 4.27 | 8.47 | matches old 2× cross-NUMA |
| 4× per-NUMA-node 24t + c2 | 4.15-4.25 | **16.86** | 4+ concurrent batch (+96% aggregate) |
| Production prior (2× --numa distribute) | 4.30 | 8.60 | suboptimal in BOTH dimensions |

Wiring change LANDED in `epyc-orchestrator` commit `64101fd`:

- `NUMA_CONFIG["architect_general"]`: collapsed from 2 instances to 1 instance using new `NUMA_FULL = ("0-95", 96)` constant (96 physical cores, no SMT, all 4 NPS4 nodes).
- Added `numactl_policy: "interleave=all"` field — `_numa_prefix()` now wraps launch with `numactl --interleave=all --` ahead of taskset for canonical-recipe roles.
- `HOT_SERVERS` port 8183 entry removed.
- `model_registry.yaml`: `numa_instances: 2 → 1`, `numa_ports: [8083, 8183] → [8083]`, `throughput: 4.3 → 12.19`.

Restart-verified 2026-05-04: `/proc/PID/numa_maps` shows `interleave:0-3` evenly across N0/N1/N2/N3, env block correctly applied (OMP stack + GGML_NUMA_REPACK_INTERLEAVE=0), VmLck = 73.36 GB.

### Orchestrator host_prereqs enforcement (NEW)

`apply_host_prerequisites()` wired into `cmd_start` audits and (with sudo -n) auto-fixes:

- sysctls: `kernel.numa_balancing=0`, `kernel.perf_event_paranoid=1`
- THP: `enabled` and `defrag` both `always`
- CPU governor: `performance`

Refuses to launch on prereq failure unless `--skip-host-prereqs` flag is set. Drift report + fix attempt + re-audit.

`build_launch_env(role, base_env)` merges canonical OMP env stack (`OMP_PROC_BIND=spread`, `OMP_PLACES=cores`, `OMP_WAIT_POLICY=active`) into every llama-server launch — without these, post-reboot Coder-30B drops 17 → 48.8 t/s per `feedback_omp_env_stack_required`. Per-role GGML_* env block from `_ROLE_ENV_BLOCKS` dict (sourced from `model-registry-v5-deployment-draft.yaml`):

| Role | env block | Source |
|---|---|---|
| worker | CPU1 3-flag stable | CPU21 P3 isolation |
| frontdoor | EP stack (5 GGML_EP_* vars) | EP +17% honest baseline |
| **architect_general** | **GGML_NUMA_REPACK_INTERLEAVE=0** | Probe B 2026-05-04 |
| architect_coding | (default v5) | Probe B 2026-05-04 confirmed |
| hybrid_ssm_dense | CPU1 + mbind-off (c3) | Nemotron-9B-v2 +8.9% pp512 |
| hybrid_ssm_moe / dense_q8 / dense_q4 | (default v5) | per arch class probes |

Production aliases routed automatically: `coder_escalation/worker_summarize/thinking_reasoning/toolrunner` → `worker`; `ingest_long_context/formalizer` → `architect_general`; `general_gemma_3_27b_it_qat` → `dense_q4`.

### `--draft-p-split` flag stripped from v5 binary (orthogonal fix)

`production-consolidated-v5` binary no longer accepts `--draft-p-split` (tree speculation removed during the v5 kernel push). `build_server_command` was emitting it unconditionally for spec-decode roles, blocking architect_general startup. Fixed in commit `9b8143e` by gating both emission sites behind `if False` with comments preserving the historical context (Coder Q4KM tree was +2.7% at 48t; hybrids tree harmful -25% to -40%). Default behavior with the flag stripped is linear-only spec-decode, which matches the registry's intent (all 4 spec-decode roles configured with `p_split=0` = linear).

### Spec-decode crash on Qwen3.5 hybrids (still open)

After fixing `--draft-p-split`, architect_general comes up healthy but live decode crashes via `common_speculative_state_tree::draft` → `GGML_ASSERT(logits != nullptr)`. This is a **pre-existing** spec-decode bug on Qwen3.5/3.6 hybrid architectures — memory entry `feedback_qwen35_27b_architecture` already documented "CPU spec-dec architecturally foreclosed by GDN verification wall". The v5 binary appears to have introduced an assertion crash on top.

Workaround: clear `draft_model:` field for `architect_general` in registry. Loses spec-decode advantage but makes the role serviceable. The 12.19 t/s Probe B number (no spec-decode) is what the role would deliver under the workaround. Actual investigation of the bug is open.

### Sources (2026-05-04)

- `epyc-orchestrator` commits `64101fd` (wiring), `4155d1c` (host_prereqs + per-role env), `9b8143e` (--draft-p-split fix)
- [`handoffs/active/model-registry-v5-deployment-draft.yaml`](../handoffs/active/model-registry-v5-deployment-draft.yaml) — `host_prerequisites` + per-role env blocks; status PARTIAL APPLIED 2026-05-04
- [`progress/2026-05/2026-05-04.md`](../progress/2026-05/2026-05-04.md) — full session including restart verification
- [`data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings_phase2.md`](../repos/epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings_phase2.md) — wiring revalidation
## 2026-05-24 — Test-time-compute techniques (OptiLLM intake): DeepConf built + validated NEGATIVE on CPU

`/research-intake` of OptiLLM (intake-601) + expansion (CoT-Decoding intake-602, DeepConf intake-603, Sharma theory intake-604). Full analysis + autopilot-scope determination in [`research/deep-dives/optillm-test-time-techniques.md`](../research/deep-dives/optillm-test-time-techniques.md).

**OptiLLM is a pattern reference, not a usable dependency.** Its high-value local techniques (DeepConf, CoT-decoding, entropy-decoding, AutoThink, ThinkDeeper) are HuggingFace-transformers-only (in-process model + activation hooks) and do NOT run over llama-server endpoints. AutoThink steering needs layer-19 activation injection (infeasible without our own fork-level steering); only its complexity-classifier idea is portable. API-level techniques (MCTS, self_consistency, PlanSearch, RTO, MARS) do work over llama-server; BoN/MoA/CEPO degrade because llama.cpp lacks the `n` multi-sample param. Apache-2.0 but has unfixed RCE issues (z3/code-exec plugins) — never import those.

**DeepConf (arXiv:2508.15260) — built, validated, NOT adopted.** Reimplemented the offline variant (confidence-weighted self-consistency from per-token top-k logprobs) on `epyc-orchestrator` branch `feat/p21a-deepconf` (default-OFF `Features.deepconf`, 41 tests). Sanity-checked against live Qwen3.6-35B-A3B (thinking ON, 4 hard multiplications × 6 traces):

| Metric | Result |
|---|---|
| Plain majority | 3/4 |
| DeepConf confidence-weighted vote (top-50%) | 3/4 — identical to majority |
| Top-1 confidence (DeepConf's filtering signal) | **1/4** |
| Correct-vs-wrong confidence gap | **−0.158 (anti-correlated)** |

The model is systematically **overconfident on wrong short answers** (e.g. `529`@13.7 outscored correct traces), so on our CPU/Qwen3 stack confidence-filtering *hurts* and confidence-weighted voting *degenerates to plain majority* — zero accuracy gain for N× generation + `n_probs` overhead (~58 s/trace). **Verdict: do not wire into the orchestrator or autopilot** (autopilot `program.md` gate updated to permanent do-not-wire). The branch is preserved as a default-OFF reference, not merged. Confirms the candidate-bounded / "confidently wrong" / verification-overhead criticisms logged at intake. CoT-decoding (intake-602) + DeepConf-online remain unbuilt fork-level work, gated on a BW roofline; the OptiLLM-style method-selection axis (intake-601, P21.B) is a separate future track.

### Sources (2026-05-24)

- [`research/deep-dives/optillm-test-time-techniques.md`](../research/deep-dives/optillm-test-time-techniques.md) — full deep-dive + autopilot-scope + P21.A outcome
- `research/intake_index.yaml` intake-601..604 (committed `27e86f0`)
- `epyc-orchestrator` branch `feat/p21a-deepconf` (`d894fd5` module+flag, `3f4eaee` runner+adapter+tests) — default-OFF, not merged
- [`handoffs/active/routing-and-optimization-index.md`](../handoffs/active/routing-and-optimization-index.md) P21 (A1 done / A2 negative / A3 do-not-proceed)
- [`handoffs/active/per-request-reasoning-budget.md`](../handoffs/active/per-request-reasoning-budget.md), [`handoffs/active/routing-intelligence.md`](../handoffs/active/routing-intelligence.md) — research-intake updates
## 2026-05-25 — Within-role full↔quarter placement is unmodeled (architectural gap)

`ConcurrencyAwareBackend` (`epyc-orchestrator/src/backends/concurrency_aware.py`) and `ContentionGate` (`src/scheduling/contention_gate.py`) admit and place requests by lock availability + NUMA disjointness, but they do NOT model the within-role full↔quarter cpuset overlap relation. For each role with `full + N quarters` deployed, the dispatcher tries full first (via non-blocking try-acquire), then falls through to NUMA-disjoint quarters first, overlapping quarters last. The `same_role` matrix verdict in `orchestration/contention_matrix.yaml` is a single `allow / block / n/a` value with no instance-pair granularity — it was measured for quarters-only co-placement, not full+quarter.

Concrete failure modes per role (cpu_list source: `scripts/server/stack_numa.py:NUMA_CONFIG`):

> *2026-07-30: `NUMA_NODE0` (`0-47,96-143`) and `NUMA_NODE1` (`48-95,144-191`) are NPS2-era names
> and are **not** single NUMA nodes — each spans two of this host's four NPS4 nodes
> (`node0 = 0-23,96-119` … `node3 = 72-95,168-191`). The overlap arithmetic in the table below is
> unaffected (it is core-id disjointness, not node identity), but read the labels as cpusets.*

| Role | Full cpu_list | Disjoint quarters | Safe-without-migration N |
|---|---|---|---|
| frontdoor | NUMA_NODE0 (0-47) | q2(48-71), q3(72-95) | 3 (full+q3+q2); N=4 forces q1 onto NUMA_NODE0, overlap |
| ingest_long_context | NUMA_NODE0 (0-47) | q2, q3 | 3 |
| vision_escalation | NUMA_NODE1 (48-95) | q0(0-23), q1(24-47) | 3 |
| worker_general | NUMA_FULL (0-95) | (none) | 1 — full covers every quarter |
| architect_general | NUMA_FULL (0-95) | n/a (single instance) | 1 |
| worker_vision | NUMA_Q0B (24-47) | n/a (single instance) | 1 |

The KV save/restore HTTP plumbing IS in place: `_slot_save()` (`concurrency_aware.py:69-88`), `_slot_restore()` (90-108), `_slot_erase()` (111-120), `_migrate_kv()` (436+). It is wired into both legacy `_select` (trigger at 314-319) and per-region-locks `_dispatch` (trigger at 636-682). The trigger is "different session takes over full while old session has no quarter affinity yet" — session-handover-based, NOT load-transition-based. The right trigger for contention avoidance is "load grew past the safe-with-full threshold → evict in-flight full session to a disjoint quarter before admitting the new request."

The 2026-05-25 `AUTOPILOT_EVAL_CONCURRENCY=4` regression made this concrete: autopilot's eval tower previously dispatched sentinels serially (`eval_tower.py:421-498` plain for-loop with shared httpx.Client), so the dispatcher never saw concurrent traffic and quarters sat idle. Adding a `ThreadPoolExecutor` fan-out to 4 surfaced the gap — 4-way frontdoor lands on full + q3 + q2 + q1, and q1 CPU-overlaps full → contention.

Closure plan: 7-phase handoff [`within-role-placement-state-machine.md`](../handoffs/active/within-role-placement-state-machine.md). WP-0 reverts the 4 → 1 default. WP-1 adds `max_safe_concurrency(role)` topology-derived cap. WP-2 builds a placement state machine (queue-instead-of-overlap, no migration). WP-3 wires the load-transition forward migration trigger using the existing `_migrate_kv` primitives. WP-4 adds reverse migration (quarter→full when load drops, with cooldown + thrash guard). WP-5 handles full-machine roles. WP-6 re-benches `same_role` with instance-pair granularity. WP-7 production rollout. Each phase ships behind an env flag with a metric gate.

### Sources (2026-05-25)

- [`handoffs/active/within-role-placement-state-machine.md`](../handoffs/active/within-role-placement-state-machine.md) — NEW 2026-05-25 — 7-phase handoff
- [`handoffs/completed/cross-role-bw-aware-routing.md`](../handoffs/completed/cross-role-bw-aware-routing.md) — direct predecessor; Phases A-F shipped the matrix, gate, per-region-locks dispatcher; Phase E KV migration under PER_REGION_LOCKS was deferred as design-only follow-up (this gap)
- [`handoffs/active/dynamic-stack-concurrency.md`](../handoffs/active/dynamic-stack-concurrency.md) — owns the KV save/restore mechanics + DS-6/DS-7 quarter scheduler; reused by new handoff
- `epyc-orchestrator/orchestration/contention_matrix.yaml` — same_role schema gap is documented in the new handoff
- `epyc-orchestrator/src/backends/concurrency_aware.py:228-269` (`_compute_quarter_preference`) — already orders quarters by NUMA-disjointness; only the candidate priority is overlap-blind
- `progress/2026-05/2026-05-25.md` Session 10 — full session log with concrete cpu_list table

### 2026-05-26 update — WP-0..WP-4 + WP-5 scaffold IMPLEMENTED

The architectural gap documented above (within-role full↔quarter overlap unmodeled by the dispatcher; KV save/restore plumbing without load-aware trigger) is now closed on the code side. Six stacked commits MERGED to `epyc-orchestrator` main 2026-05-26 (merge tip `15350fe`; source branch `feat/wp-0-eval-concurrency-default` consumed + deleted post-merge; 155/155 dispatcher-adjacent tests at merge):

| Commit | WP | Status |
|---|---|---|
| `33bfe20` | WP-0 | Live — `AUTOPILOT_EVAL_CONCURRENCY` default reverted 4→1 |
| `cab27ac` | WP-1 | Live — `max_safe_concurrency(role)` topology helper; autopilot default = `max_safe_concurrency('frontdoor')` = 3 |
| `29e95b4` | WP-5 scaffold | Live — `RolePlacementPolicy` enum + accessor, conservative `solo_prefer_full` for all roles (no live behavior change) |
| `3d94a03` | WP-2 | Behind `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1` (default off) — `src/scheduling/placement.py` + dispatcher refactor with poll-on-queue |
| `b4d5161` | WP-3 | Always-on transactional `MigrationTransaction` + policy gate + `migration_budget_ms` honoring on the existing session-handover trigger. The speculative load-transition trigger was explored and removed (`_migrate_kv` cannot preempt mid-decode — rationale documented in `_dispatch` comment) |
| `66a8bfc` | WP-4 | Behind `ORCHESTRATOR_REVERSE_MIGRATION=1` (default off) — quarter→full migration with 4 guards (cooldown 2s / window 30s / per-session cap 5 / in-flight de-dup) |

Inference-gated verifications (WP-2/WP-3/WP-4 gates, WP-5 ratification, WP-6 matrix re-bench, WP-7 production rollout) are bundled in `bulk-inference-campaign.md` § Package J alongside DCP-6 and BEP-2 from the same audit batch and HLE-4 from the harness-metrics track. Priority-zero sequencing: J1 → J2 → J3 (the WP-2/WP-3/WP-4 verifications) must run BEFORE any other downstream inference Package so flag-enablement raises every subsequent Package's effective concurrency.

### Sources (2026-05-26)

- `epyc-orchestrator` branch `feat/wp-0-eval-concurrency-default` — 6 stacked WP commits, 155/155 tests green
- [`handoffs/active/bulk-inference-campaign.md`](../handoffs/active/bulk-inference-campaign.md) § Package J — wires the inference gates with priority-zero sequencing
- [`handoffs/active/within-role-placement-state-machine.md`](../handoffs/active/within-role-placement-state-machine.md) — handoff frontmatter `implementation_status` block tracks per-WP status
- [`progress/2026-05/2026-05-25.md`](../progress/2026-05/2026-05-25.md) Session 14 + [`progress/2026-05/2026-05-26.md`](../progress/2026-05/2026-05-26.md) Session 15
## 2026-05-27 — Handoff hygiene now separates live serving work from stale narration

Second-pass handoff hygiene corrected an index-tracking failure: some active CPU/serving handoffs were still visible as broad work streams even though only narrow residual decisions remained. The durable serving rule is that domain indices should carry unresolved action only; completed chronology belongs in progress logs or the handoff body.

Current examples:

- `numa-prefill-decode-disaggregation.md` remains active only for the Phase 0 xGMI KV-transfer falsification gate and multi-tenant reopen condition. `inference-acceleration-index.md` and `cpu-inference-optimization-index.md` now carry explicit hygiene notes so direct readers see the pending trim.
- `wdata-aware-mul-mat-coalescing-design.md` is a completed Phase 0 negative/low-ROI analysis; keep only the decision statement and re-evaluation triggers active. Its sibling `cpu22-hybrid-spillover-design.md` should retain only a lightweight comparison pointer after trim.
- `qwen36-benchmark-fixes.md` should close or trim after one post-reboot confirmation. Qwen3.6 output and benchmark wiring are fixed; the separate bimodal-throughput regression belongs in progress/future tracking.
- `launcher-numa-mode-gating.md` is PARTIAL, not complete: the `--numa-mode {full,quarter,both}` flag landed, but the original acceptance criterion that `start --only worker_general` default to `quarter` is still unmet because default remains `both`. That default is an operator decision, not a hygiene cleanup.

### Sources (2026-05-27)

- [`handoffs/completed/handoff-backlog-hygiene-audit.md`](../handoffs/completed/handoff-backlog-hygiene-audit.md) — second-pass audit correction and outstanding domain-scoped dereferences
- [`handoffs/active/numa-prefill-decode-disaggregation.md`](../handoffs/active/numa-prefill-decode-disaggregation.md), [`handoffs/completed/wdata-aware-mul-mat-coalescing-design.md`](../handoffs/completed/wdata-aware-mul-mat-coalescing-design.md), [`handoffs/completed/qwen36-benchmark-fixes.md`](../handoffs/completed/qwen36-benchmark-fixes.md) — handoff notes
- [`handoffs/completed/launcher-numa-mode-gating.md`](../handoffs/completed/launcher-numa-mode-gating.md) — partial status and default-decision gate
- [`progress/2026-05/2026-05-27.md`](../progress/2026-05/2026-05-27.md) — owner-refresh and dereference queue
## 2026-05-28 — Dynamic-stack active gate clarified

The active/completed split for `dynamic-stack-concurrency.md` separates already-landed serving mechanics from still-open scheduler decisions. DS-B through DS-D remain completed evidence in the sibling ledger. The active handoff now owns DS-6/DS-7 and explicitly gates scheduler rollout on Phase E evidence; KVCOMM is optional after Attention Matching / q4_0 feasibility rather than a deployment queue item.

Operational implication: do not implement the quarter scheduler from old completed sections alone. Start from the active twin, confirm the current Phase E/autoresearch evidence, and only then decide whether DS-6 is code-ready. Sources: [`dynamic-stack-concurrency.md`](../handoffs/active/dynamic-stack-concurrency.md), [`dynamic-stack-concurrency-completed-through-2026-05-28.md`](../handoffs/completed/dynamic-stack-concurrency-completed-through-2026-05-28.md), [`progress/2026-05/2026-05-28.md`](../progress/2026-05/2026-05-28.md).
## 2026-06-26 — Prompt-construction & sampling determinism audit

A determinism audit of the live orchestrator prompt/sampling path (post-v6-iqk-cutover) established that **prompt *construction* is deterministic, but generation *sampling* was not** — and the non-determinism was masked by an accidental fallback.

**Deterministic (verified):** routing artifact `derived/stack_priors.yaml` is the source of truth (consumed via `chat_completions_roles()`, gate = `jinja ∧ enable_thinking==False`); freshness is hash-checked; no env override; template-family selection is correct per role; system prompts are static; `--jinja` is **inert on `/completion`** (the OpenAI `/v1/chat/completions` endpoint is the only one that applies the GGUF jinja template), so a role launched with `--jinja` but called on `/completion` is orchestrator-templated only — not double-templated.

**Three sampling gaps (fixed 2026-06-26):**
1. **Temperature-source split** — roles declare `generation_defaults.temperature` (0.1–0.3) but the payload builders read only `acceleration.temperature` (unset), falling back to `request.temperature=0.0`. Net effect: the whole stack ran **accidental greedy**, and the declared temps were dead config. Honoring `generation_defaults` makes sampling intentional but then requires a pinned seed.
2. **No seed** — text-gen payloads set no `seed`; reproducibility is impossible once temp>0. Fixed seed (override via `request.seed`) added.
3. **Endpoint sampler divergence** — `/completion` hard-coded `top_k/top_p/repeat_penalty`; the chat path sent none (server defaults). Two regimes for the same logical request. Unified via one `_apply_deterministic_sampling()` helper across all three payload sites (`/completion`, non-stream + stream chat).

**architect_general `enable_thinking` was inert:** its registry `enable_thinking=false` only applies on the `/v1/chat/completions`+jinja path, but the 2026-04-15 `0879ed56` `--jinja` exclusion (which guarded a confirmed Qwen3.5-122B hybrid `<think>`-loop — zero-content/4096-tok "Wait, I found a reference" cycles) routed it to `/completion`, so the kwarg never reached the server. Removing the exclusion enrolls architect into the cc-set where nothink fires (frontdoor, same family, is the working reference). **This is a revert-gate**, not a free flip — the think-loop suppression must be confirmed by the J12 probe before trusting; if it loops, revert. This updates the still-open "Spec-decode crash on Qwen3.5 hybrids" topic above: the think-loop is now mitigated via server-side nothink rather than template avoidance.

Operational implication: the stack was reproducible only by accident (temp=0 fallback). Wiring declared temps + a seed makes it deterministic *by design*, but it is a behavior change (greedy→sampled) that requires canonical-bench certification and an `autopilot_quality` instrument-era boundary.

Sources: [`prompt-construction-determinism.md`](../handoffs/active/prompt-construction-determinism.md) (master N14), [`bulk-inference-campaign.md`](../handoffs/active/bulk-inference-campaign.md) (J12 revert-gate), [`progress/2026-06/2026-06-26.md`](../progress/2026-06/2026-06-26.md).
## 2026-07-02 Update — GPU Serving Tier Arrives (MI210 installed, HIP verified)

The long-dormant GPU-acceleration workstream activated: an AMD Instinct **MI210 (gfx90a, CDNA2, 64 GB HBM2e)** is physically installed, passed into the devcontainer, and the fork's HIP build leg is verified. This turns the entire GPU-drafter design corpus from hardware-gated speculation into a live serving surface. Framing that matters for serving decisions:

**The GPU is an additive latency tier, not a replacement.** The CPU NUMA stack already runs cloud-competitive (20-50 t/s per role). The MI210's job is to lift the *hot* frontdoor + drafter path into the 100+ t/s regime while architect (Qwen3.5-122B, does not fit in 64 GB) and workers (throughput-amortized) stay CPU-resident. This is the same hierarchical "one model thinks, many work" philosophy applied across a heterogeneous CPU/GPU substrate.

**GPU discipline mirrors the CPU v6 one-kernel cutover.** llama.cpp-HIP is the single production GPU binary (native ggml-cuda + rocWMMA + MFMA, loads GGUF); vLLM is a *measurement instrument only* — it cannot serve current models because vLLM 0.10.1 and even v0.22.0 lack the `gemma4`/`qwen35` architectures, so a shared Qwen3-8B is used for any head-to-head. First-pass observations (contended host, not decision-gating): fp16 per-stream llama.cpp-HIP 62.45 t/s vs vLLM ~69 t/s (+11%); batched 32-way 909.8 vs 1129 gen tok/s (+24%). vLLM's edge is batched serving; llama.cpp already reaches 62% of the HBM roofline at fp16, so the earlier ~33-47% ceiling at Q4_K/Q8_0 is a quantized-dequant artifact, not general kernel immaturity.

**Two serving-relevant unblocks.** (1) GPU-side MTP spec-dec works: gemma-4-31B + its NEXTN head both on ROCm0 → 43.25 t/s (1.44x, 59.7% accept), the first live evidence for the head-on-GPU / trunk split. (2) qwen35 (gated-delta-net) decodes clean on the GPU HIP path, localizing the persistent CPU spec-dec crashes (M-RoPE/GDN `GGML_ASSERT(logits != nullptr)`) to the CPU speculative codepath rather than the qwen35 forward pass. Neither supplies the N5 frontdoor-drafter acceptance-rate (α) number, which remains the single gating measurement for all GPU placements. The gfx90a support matrix is settled on paper: Triton/FlashAttention-2/vLLM-core cover the card; AITER/MORI/DeepEP are CDNA3-only; Vulkan is impossible on CDNA2 — HIP/ROCm is the only path.

Sources: [gpu-drafter-mi200-investigation.md § 2026-07-02 Advancement](../handoffs/active/gpu-drafter-mi200-investigation.md), [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md), [2026-07-02 ROCm MI210 vLLM / gfx90a deep-dive](../research/deep-dives/2026-07-02-rocm-mi210-vllm-gfx90a.md), [moe-spec-cpu-spec-dec-integration.md](../handoffs/active/moe-spec-cpu-spec-dec-integration.md).
## 2026-07-05 Update — Launcher NUMA Default Flip, DS-7 Profile Codified, Restart-Applicator Hardening, MoE-on-GPU Deployment Wins

Five serving-plane threads advanced this window: the launcher now defaults to a single NUMA mode (no more silent full+quarter oversubscription), the dynamic-stack effort resolved its Phase E profile decision without touching the live stack, the capability-registry restart applicator gained strict-scope gates, the standardized stack-change pipeline caught and repaired source-fingerprint drift twice, and the MI210 campaign produced measured (observation-grade) config wins for MoE-on-GPU aggregate serving.

### Launcher `--numa-mode` default flipped to `quarter` (full XOR quarters, resolved)

The long-standing launcher hazard — `orchestrator_stack.py start --only worker_general` silently bringing up **all 5 instances** (1 full-NUMA 96-thread + 4 NUMA-quarter 48-thread), whose CPU sets overlap → ~1.5× oversubscription — is now closed. Orchestrator `01d14301` makes both the CLI parser and the programmatic `cmd_start()` fallback default `--numa-mode` to `quarter` instead of `both`. The overlap was not cosmetic: the 2026-05-08 discovery measured load average jumping to 420 and the full instance collapsing from 76.5 t/s solo → 9 t/s once the quarters ran alongside it. gemma4's `-t 96` per-instance made the collapse visible where the pre-2026-05-08 Qwen3-Coder worker's lighter `-t 24` had masked it.

- `--numa-mode full` starts only the full-NUMA instance (max single-request throughput); `quarter` starts the 4 quarters (max aggregate throughput under multi-request load); `both` remains available as compatibility mode and still emits the oversubscription advisory.
- Filtering lives in `stack_manifest.py:_filter_by_numa_mode`, wired at `stack_commands.py:393`; the flag is declared at `orchestrator_stack.py:1324`.
- The default flip is a launcher-source change, so it also rippled through the stack-change pipeline as a source-fingerprint repair (below). Handoff `launcher-numa-mode-gating.md` is now COMPLETE.

### DS-7 static-prewarm profile decision (DS-6 QuarterScheduler parked)

Dynamic-Stack Phase E closed its interpretation step **without a live stack change**. The DS-E1 evidence packet (`dynamic_stack_evidence_packet.py`, output `orchestration/reports/ds_e1_evidence_packet_20260705T094913Z.{json,md}`) reports `ready_for_profile_decision=true`: generated stack-prior roster ready (10 live roles, compiled 2026-07-05), DS-5 research-manifest freshness ready, contention matrix ready, RI-10 canary evidence ready, and production KV-size measurements ready. Two freshness subtleties were codified so auxiliary topology no longer creates false DS-E1 blockers:

- **Content-aware manifest freshness** (`c98c9e14`): same-version stack-prior recompile timestamp drift is accepted as long as every live role is still covered (`stack_priors_version=4` matches).
- **Measured-subset contention validation** (`a62f9d14`): the contention matrix is validated against its measured contention-role topology (`df373c79cc4af06f`), excluding launcher-only auxiliary `eval_batch_frontdoor`; the full live topology hash `5d19b3e4edf6fc27` differs only because it includes that auxiliary.

Decision (`ds7_profile_decision_20260704T194020Z.{json,md}`): retain `stack_templates/default.yaml` as `steady_state_static_prewarm` (`metadata.ds7_profile`, `metadata.ds7_decision.status=retain_default`); `load_template()` now preserves template metadata so the decision is machine-readable. `orchestrator_stack.py start --stack-profile default --validate-only` passed with **17 roles, 28 instances, 657 GB RAM estimate**. DS-6 QuarterScheduler stays parked — implement dynamic quarter reassignment only if future DS-E1-equivalent evidence shows static pre-warm leaves material throughput/latency on the table. Note the `data/kv_cache_quant/kv_quant_*.csv` artifacts are explicitly **not** DS-E1 evidence (different schema/contexts, no production role rows) and must not be converted into the gate. Phase F KVCOMM remains a separate research fork that must not block DS-6/DS-7.

### Capability-registry W3 safe role-restart applicator — strict-scope hardening

The dormant `config_applicator.restart_role()` primitive (never wired into live AutoPilot) gained strict opt-in gates for future promoted callers (`7b47671e` lineage, hardened 2026-07-04):

- `require_explicit_affected_roles=True` fails **before** dispatch pause, registry edits, or reload unless the caller supplies the exact affected-role surface — a "role restart" can bounce sibling roles because same-GGUF roles share one server process (`feedback_same_model_roles_share_server`), so restart scope must be declared, not inferred from stack-prior topology.
- `require_smoke_check=True` fails **before** reload unless a role smoke hook (canned completion) is present.
- The registry validator now rejects any `role_restart` / `stack_restart` row missing `smoke_check: canned_completion` and `require_explicit_affected_roles: true`, on top of the earlier structured `trial_protocol` contract (`class: batched_restart`, `min_trials >= 1`, `restore_after_batch: true`, non-empty `boundary_event`). First restart-class rows (`moe_spec_budget`, `ea_compaction_profiles`, `draft_max_p_split`) carry the shared 5-trial-restore / `role_restart_boundary` contract.

W3 remains open only for a **shadowed live restart attestation**, itself gated on `evidence-plane-ledger.md` Phase 1 (the instrument must certify effects before the optimizer gets restart-class levers). No capability row was promoted; no live restart was enabled. W0 workload-class tagging is fully closed (live `ChatRequest.workload_class` constrained to `interactive|eval_batch|campaign`; unset requests infer `eval_batch` for background/batched calls without changing admission priority). W2 compilation (generated Action-Availability + master-index A-by table) is adopted with drift guards.

### Standardized stack-change pipeline — twice caught source-fingerprint drift

The canonical gate (`stack_change_pipeline.py check --run-promotion-gate`) continues to work as designed: it catches stale generated metadata after any launcher/registry source change and forces regeneration through the canonical `update` path.

- **2026-07-04**: `stack_change_guard.py --all-hardcoded-surfaces` caught stale generated stack-prior `source_artifacts` metadata for `orchestrator_stack.py`; regeneration refreshed descriptors, stack priors, procedure enums, and the operator summary with **no semantic role diffs**; promotion gate passed 181 tests.
- **2026-07-05**: after `01d14301` changed the launcher NUMA default, the guard again caught stale `source_artifacts` for `orchestrator_stack.py`; Orchestrator `a0377110` regenerated through the canonical pipeline. GitNexus impact was HIGH for `compile_stack_priors` (60 upstream), MEDIUM for `write_stack_priors` (49), LOW for `run_stack_change_pipeline` (2), but the diff was **metadata-only**: compiled timestamps, source commits, source hashes, and summary fingerprints — no role rows, ports, tiers, launch requirements, or procedure enums changed. `check --run-promotion-gate` returned `summary: ok` with `guard_all_surfaces/guard_strict/runtime_attestation: ok` and 181 tests passing.

Guard inventory holds at `consumer_surface_count=13`, `rule_count=27`, `exceptions: []`. Remaining pipeline work is opportunistic high-risk consumer migration and W4 swap-CI expansion, both on-new-finding rather than an already-identified open gap.

### MoE-on-GPU aggregate deployment wins (measured, production-hold)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. All MI210 numbers below are OBSERVATION (no P-GPU-1 protocol); they gate nothing until certified through MEASUREMENT.md, and the operator placed an explicit **production hold** (2026-07-04) — nothing deploys, all changes stay experimental, and any prod push additionally requires CPU-numerical-correctness verification (untestable while the CPU stack serves production).

From the 2026-07-04 MI210 campaign on gemma-4-26B-A4B (the clean MoE-no-GDN test vehicle), two zero-code role→config wins for a MoE role hosted on the GPU (the findings-02 residency bet — **not** a change to the current CPU stack):

- **Win 1 — `-fa 1` for aggregate decode (B≥8).** Flash-attention is a WIN at batch for MoE-on-GPU — the *opposite* of the dense-hybrid Qwen3.6-27B, where gfx90a FA is prefill-only and `-fa 1` hurt everywhere. Measured S_TG t/s: at B=1 `-fa 1` costs 7–12% (Q8 96.2→85.0, bf16 72.6→67.4), but crosses over near B=8 and dominates at scale — B=128 Q8 851→1107 (+30%), bf16 1083→**1548** (+43%). FA fuses the KV mat-vec and avoids the V-cache padding that `-fa 0` forces on gemma's uneven-V-size layers. **Rule: `-fa 1` for aggregate serving (B≥8); `-fa 0` for single-stream latency.**
- **Win 2 — bf16-for-aggregate / Q8-for-single-stream.** Crossover ≈ B=16–24: Q8 wins low-batch (+27–37% at ≤B8), bf16 wins high-concurrency (+27–43% at ≥B32) because high-batch GEMM is compute-bound and bf16 runs native on CDNA2 matrix cores with no dequant tax (B1→B128 scaling: Q8 8.85× vs bf16 14.9×). HBM-fit-gated: bf16-26B @B128 / 32k-ctx = 56.6 GB of 65.5 (fits, ~9 GB headroom); a larger MoE would not fit at B128 on the 64 GB card.
- **Combined peak: bf16 + `-fa 1` @ B=128 = 1548 t/s** aggregate — ~2.75× the prior Q8 `-fa0` @B32 anchor (563), entirely config, zero kernel work.
- **Not levers (measured, do not attempt):** the L1-MoE `mmid` dispatch threshold (forcing experts to MMQ at low batch is net-negative — B2 −30%, B4 −21%; MMVQ is the correct low-batch kernel and the default threshold 8 is already optimal); and **MTP for MoE-on-GPU decode** (−12%, head-quant-independent — verify overhead on already-fast plain MoE decode; the MTP verdict itself is owned by the speculative-decoding page).
- **Still open (our-side kernel bet):** the real aggregate ceiling is Q8-MMQ GEMM efficiency (61% of B=32 decode; 2.61 vs bf16 3.22 waves/CU occupancy) — a fused-dequant Q8-MMQ kernel could make Q8 aggregate-competitive at half the HBM, but that is a research bet (L3-MoE), not low-hanging. Until then bf16 is the aggregate precision.

Meta-finding reinforced across the campaign: every lever's sign is a function of arch × substrate × batch — never carry a verdict across dense↔MoE or GPU↔CPU.

Sources: [launcher-numa-mode-gating.md](../handoffs/completed/launcher-numa-mode-gating.md), [dynamic-stack-concurrency.md](../handoffs/active/dynamic-stack-concurrency.md), [capability-registry-and-promotion.md](../handoffs/active/capability-registry-and-promotion.md), [standardized-stack-update-pipeline-finalization.md](../handoffs/active/standardized-stack-update-pipeline-finalization.md), [moe-aggregate-deployment-wins-brief.md](../handoffs/completed/moe-aggregate-deployment-wins-brief.md), [progress/2026-07/2026-07-04.md](../progress/2026-07/2026-07-04.md), [progress/2026-07/2026-07-05.md](../progress/2026-07/2026-07-05.md).
## Realized-fleet truth (ESC-8, compiled 2026-07-22)

Production routed correctly only by accident for two days: a poisoned `STACK_NUMA_MODE=full`
env + a valid full-mode runtime-facts manifest were held off by a silently-swallowed circular
import (`handoffs/completed/esc8-stack-restart-landmine-audit-2026-07-22.md`). The durable rule
extracted into code: **no layer may trust launch-time intent over the realized fleet**.
`scripts/server/realized_fleet.py` (TCP-probe mode classification, injectable) now backs the
facts writer (realized-state serialization, unknown≠"full"), launch-time env alignment, config
lineup liveness validation, the priors compiler (refuses ambient default-full), the stack-change
guard, and the dashboard. The manifest is honest for the first time (realized mode + 21 live
servers), verified end-to-end. Deploy discipline: SIGSTOP the eval runner before any API reload
(no client reconnect backoff — two burned-arm incidents), and implementation subagents carry
zero process-management authority (a prose ban failed; 532 questions paid for the lesson).
## Cold-fleet mode inference in the stack-change gate (2026-07-25)

**Why a cold start cannot be gate-green, and why that is correct.**

The stack-change guard builds its launch view by resolving NUMA mode as
*realized-fleet → `ORCHESTRATOR_STACK_NUMA_MODE` → default `full`*. On a fully-cold host
there is no realized signal and a clean shell has no env, so the view is built for `full`
while the registry documents the live lineup — producing wholesale mismatch errors (37 in the
2026-07-25 instance; the same family as an earlier 105-error class for live fleets). A CLI
`--numa-mode` flag existed but was **never consulted by the guard**; it is now threaded into
the gate subprocess env (precedence unchanged: realized > CLI > env > default), which took
that instance from 37 errors to 1.

**The residual 1 is by design, and the distinction is subtle enough to be worth recording.**
`_check_stack_priors` sets `require_realized_mode=True` **not** for write-safety but for
*comparison validity* — so a clean-shell check computes the same lineup an update would write
and cannot report quarters-only priors as "stale" against a full expected. Kill-chain-A4
write protection lives only on the *update* path. The refusal is the fail-closed alternative
to a comparison the tool cannot trust.

**Do not "fix" this by trusting an explicit mode on a dead fleet.** That carve-out is
explicitly encoded as prohibited in `tests/unit/test_stack_priors_compiler.py`:
*"An explicit env does NOT rescue a no-signal probe (unverifiable fleet)."* Changing it means
changing a test that is the specification, with the owning surface's sign-off.

**Consequence**: the documented cold-start recipe (dry-run to verify the priors refusal is the
*only* residual, bring up with the gate skipped, then run the pipeline update immediately once
the fleet is realized and the mode is derivable) is the **sanctioned** path, not a workaround.

_Sources: `handoffs/completed/esc8-stack-restart-landmine-audit-2026-07-22.md` § 2026-07-25;
`epyc-orchestrator ed6288ea`._
## Compiling the stack: the derived layer is the only thing production reads (2026-07-31)

Confidence: `verified` — every claim below was checked against the live process table
(`/proc/<pid>/cmdline`), the compiled artifacts on disk, or an executed pipeline run, not
against config or intent.

**The load-bearing fact: the master registry is not what launches anything.** Production
serves from `orchestration/derived/stack_priors.yaml`, which is compiled. Three separate
correct edits to master — a spec-recipe reversal made on falsification evidence, four
throughput-prior corrections, and the NUMA topology cutover — all landed in master and **none
reached the launcher**, because the step that would carry them was silently skipped for days.

### The fail-quiet that caused it

`scripts/registry/stack_change_pipeline.py update` regenerated descriptors and priors **from
the lean registry**, and nothing in it recompiled lean from master. Run alone it printed
`descriptors: updated / stack_priors: updated / guard: ok` while re-emitting the stale values
verbatim: a green result computed over the wrong input. The blast radius was not academic —
production was one `start` away from launching a composed `ngram-mod,draft-mtp` recipe that had
already been falsified and reversed in master, where `ngram-mod` alone costs 23–31%.

**Generalization worth carrying**: a pipeline that verifies *the artifact it wrote* rather than
*the artifact its consumer reads* cannot detect a stale input. This is the same class as the
seven fail-open guards catalogued in [`formal-verification`](formal-verification.md); this one
just had production reach.

### Compile is now a pure function of its declared inputs

`compile(master, role assignments, topology) -> lean -> derived`. Three deviations were closed:

1. **`registry_compiler --force` is now the pipeline's first step**, in both `check` and
   `update` — the missing hop, no longer something a human must remember.
2. **Topology is declared, not probed.** It previously came from a probe of the *running*
   fleet, so identical inputs produced different artifacts depending on machine state. It now
   lives in `orchestration/stack_topology.yaml` and the live probe is a **backstop**, not the
   decision-maker. This directly retires the cold-start pathology recorded in the 2026-07-25
   section above: the compile no longer needs a realized fleet to know what to build.
3. **One mode resolver.** `check` and `update` resolved NUMA mode separately and could
   disagree; there is now a single resolver that reports its source.

Verified both directions: clean shell → `acceptance: no-inference checks passed` (the first
fully-green clean-shell run; it was **39 errors** the same morning), and master mutated by one
comment → `lean_registry: stale`, exit 1. A false positive was caught before shipping — the
pipeline's active-role set carries `eval_batch_frontdoor`, which the lean projection does not,
so the cache key never matched and the step reported stale on every run.

### Binaries resolve by backend, so a role's kernel follows its declared device

Four kernels, three ggml generations (llama.cpp 0.16.0, whisper.cpp 0.18.0, qwentts.cpp
0.17.0). A stable layer at `/mnt/raid0/llm/kernels/production/{cpu,gpu,stt,tts}` plus
`src/registry/kernel_paths.py` resolves them and **raises** on an unresolvable backend rather
than falling back. `_backend_for_role()` maps device `ROCm*`/`cuda*`/`gpu*` → gpu, else cpu;
`stack_priors` emits a per-role `binary_path` and the launcher verifies live matches declared.

**Why this was urgent rather than tidy**: `llama.cpp/build/bin` has **no `libggml-hip.so`** —
it is a CPU-only build. Before this change no registry field named a binary path and the
launcher used `build/bin` unconditionally, so a registry edit moving a role to the GPU would
have launched it on the CPU binary **silently**, because a missing HIP backend does not error.
Four roles were queued for exactly that move.

A near-miss inside the same change is instructive: `env_policy`/`kmp_blocktime` key off
`binary_dir` being *truthy*, so always-populating it would have flipped every role from
`canonical` to `binary_override_strip_ggml` with `KMP_BLOCKTIME=10`. **Deriving a value that
was previously a sentinel changes the meaning of every check that tested it for presence.**
Explicit override and derived default are now distinguished and the env policy is asserted
unchanged.

### Kernel freeze scope is a projection, not a list

The question a freeze must answer is narrow: *which models must show no regression before this
kernel may serve?* A curated list goes stale the moment a role is repointed, and a stale gate
is worse than none because it passes while testing the wrong thing. The correct set is derived:
**the models that matter for backend B are exactly the models whose roles resolve to B in the
compiled priors** (`scripts/validate/kernel_freeze_scope.py`).

**This is what makes the four kernels independently upgradable.** A whisper.cpp upgrade cannot
regress a role that never calls whisper.cpp, so it is not gated on one. At the 2026-07-31
snapshot: `cpu` serves 10 roles across **5 distinct models** (bench the *models*, not the roles
— several roles share one server); `gpu`, `stt` and `tts` serve none, so a freeze for those
gates on nothing from the stack and needs only its own functional evidence.

Promotion is a symlink move and rollback is repointing to the archived target — **neither
registry changes, and no launcher changes**. The binary name is deliberately unchanged, which
is what lets the orchestration apparatus keep working untouched. Changing *which* backend a
role uses is a topology change, not a kernel freeze, and gates on the stack-change pipeline
instead.

### Two operational residues

- **Byte-hash pins on source files do their job and must be refreshed as part of the edit.**
  The priors pin `orchestrator_stack.py`'s SHA-256; adding one function staled the artifact
  immediately. That is correct behaviour, not friction.
- **The stack-change gate cannot distinguish "aux service unmanaged" from "unsafe to launch".**
  It refused a launch on `runtime_attestation: live process drift` for two long-running
  services (`:8000` orchestrator API, `:9000` faster-whisper) while every config gate was
  green, and the only available response was `ORCHESTRATOR_SKIP_STACK_CHANGE_GATE=1`. A gate
  whose sole failure response is a blanket bypass trains the bypass. Bringing those services
  under management is tracked as W4/W5.

_Sources: `handoffs/active/numa-topology-cutover-resume-20260730.md` § SESSION APPEND
2026-07-31 (20:00–21:00Z), ADDENDUM, ADDENDUM 2, ADDENDUM 3;
`docs/reference/kernel-freeze-runbook.md`;
`artifacts/audit/orchestration-wiring-audit-20260731.md` (epyc-root `5d4d05a6`);
`progress/2026-07/2026-07-31.md` § Session 20:00–23:00Z;
`epyc-orchestrator` `ed891211`, `596e2189`, `c1a004bf`, `b060dd56`, `4e8bf1f0`, `ca5f3e81`._
## Compiled Update — 2026-08-11 production v9 stack restoration

The complete serving stack is resident again on frozen production v9. Runtime attestation matches
`production-consolidated-v9` at `0db32c06e3e550065b78311a6031ef3dd2c4f27c` (binary 10125), all
six backend groups and probes report healthy, the embedders warmed, speech launchers proved their
tree-local ggml linkage, and a live TTS synthesis smoke passed. This is a stack-health result, not a
new model-quality or throughput claim.

The first cold start failed closed because `stack_paths` imported the full config graph before
publishing the binary/path constants that the config graph itself imports. Runtime-facts NUMA
inference then failed and selected an inactive manifest. Orchestrator `74c68a2a` breaks that cycle
without removing `PathsConfig` environment overrides; `969244d8` regenerates the stack derivatives
from the repaired loader. Focused config/manifest tests passed 142/142 and the complete launch gate
passed 191/191. The reusable lesson is that launcher leaf modules must publish path constants before
importing configuration consumers: generated topology selection is only as reliable as the import
graph that feeds it.

### Source References (2026-08-11)

- [`progress/2026-08/2026-08-11.md`](../progress/2026-08/2026-08-11.md) — live restoration, health probes, root cause and verification counts.
- [`ratify_v9_final_freeze_20260811.json`](../artifacts/operator/ratify_v9_final_freeze_20260811.json) — ratified kernel identity and rollback boundary.
- [`v9-kernel-promotion-attestation.json`](../handoffs/active/v9-kernel-promotion-attestation.json) — frozen CPU/HIP and production certification evidence map.
- [orchestrator `74c68a2a`](https://github.com/pestopoppa/epyc-orchestrator/commit/74c68a2a8e01a0f4a8c93a49fa32c0b85494f501) and [`969244d8`](https://github.com/pestopoppa/epyc-orchestrator/commit/969244d8015155c0193ad2780313a858df3f0ba1) — circular-import repair and regenerated derivatives.

## Three ggml generations in one fleet: why `prepend` is right for llama and wrong for speech (2026-08-12)

The production kernel set runs **three different ggml generations** — llama.cpp (v9), whisper.cpp
(0.18.0, STT) and qwentts.cpp (0.17.0, TTS). A binary that inherits another tree's ggml runs silently
wrong, so `scripts/server/stack_env.py` composes `LD_LIBRARY_PATH` in **two modes**, and the choice
between them is not stylistic:

- **`prepend`** — declared paths lead, the ambient value is kept behind them. Correct for **every
  llama-server role**, because the ambient path *is* the CPU llama tree and is a legitimate fallback.
  The loader takes the first directory containing a matching soname, so the GPU tree wins for every
  library it actually ships — and `build-hip/bin` ships all four, including `libggml-hip.so.0`.
- **`replace`** — declared paths are the *whole* value. Required for any binary from a tree with its
  own ggml generation. `stack_manifest.py:318` defaults to `replace` whenever a service declares
  `backend:`, and speech paths are **backend-derived** (`backend_ld_library_path`), not read from the
  manifest's `ld_library_path` (which is empty for both speech services).

**Why prepending cannot rescue a speech kernel.** Prepending llama's tree in front of whisper's does
not produce a clean failure — it produces a **mixed load**: `libggml`, `libggml-cpu` and `libggml-base`
resolve from llama's 0.16.0 while `libggml-hip` resolves from whisper's 0.18.0, because llama's tree
ships the first three and not the fourth. Two ABI generations in one process. The mixed outcome is worse
than a clean failure precisely because it starts and produces numbers.

**Verifying this is itself a trap — measure the launcher's environment, not your shell.** Two distinct
false findings came from getting this wrong on 2026-08-12:

1. Running `ldd` in an **agent shell** shows llama's GPU binary resolving CPU ggml, which reads as a P1
   "production runs on CPU". It is an artifact: the shell has only the ambient path; the launcher
   prepends `build-hip/bin`. The falsifier was throughput — ~50 t/s on a 27B is impossible on CPU.
2. Calling `build_service_env()` on the **raw manifest spec** reports `paths=[]` for whisper and tts,
   which reads as "replace mode declared but never applied". Also an artifact: it skips the
   backend-resolution step the launcher runs first.

`verify_speech_kernels.sh` encodes the distinction properly — it runs **two** checks, a *launch-recipe*
check (is the frozen tree self-sufficient?) and an *ambient* check (is this shell poisoned?). Both are
RC=1, and they answer different questions. A launch-recipe pass with an ambient fail means production is
fine and hand-run measurement is not.

**Committed is not deployed.** The ambient poisoning had a correct fix committed on 2026-07-31
(`136894e8`, dropping CPU-only llama dirs from the global `LD_LIBRARY_PATH`; both `/etc/environment` and
`.devcontainer/devcontainer.json` carry the clean value). It was still not live on 2026-08-12: container
PID 1 started 2026-07-29, two days *before* the fix, and a `containerEnv` change only takes effect on
rebuild. Reading a committed file and concluding a running process has the fix is the general trap —
check the process, not the repo.

**Source references**
- `scripts/server/stack_env.py` — `compose_ld_library_path`, `build_service_env`, and the mode contract
- `scripts/server/stack_manifest.py:318` — `replace` default when `backend:` is declared
- `scripts/server/orchestrator_stack.py:2337-2344,2479` — backend resolution and `verify_ggml_linkage`
- `scripts/session/verify_speech_kernels.sh` — the two-check design and INC-20260731 rationale
- `progress/2026-08/2026-08-12.md` — the two false findings and their retraction

## Compiled Update — 2026-08-21: a registry swap is not served until the DERIVED layer recompiles

The Qwen3.6→Qwen3.8 rollout produced a three-layer lesson that extends the standing
"pipeline-green ≠ starts ≠ live==config" rule with a fourth inequality: **master-swapped ≠
lean-compiled ≠ derived-compiled ≠ served.** The master registry was swapped and validated on
2026-08-20 (`b376dadd`), and the lean runtime view auto-recompiles at `orchestrator_stack.py start`
— but the DERIVED artifacts (descriptors, stack_priors) had been compiled 2026-08-11, nine days
pre-swap, and the launcher reads them AS-IS with no recompile at start (`orchestrator_stack.py:252-262`).
A stack start in that state would have served the OLD model at the OLD draft depth while every
config a reader would check said otherwise. The ratification that closed it
(`ratify_qwen38_registry_swap_20260821.sh`, executed; orchestrator `7483d7fb`) recompiled the chain
and verified the derived layer names `Qwen3.8-27B-Q8_0` @ `draft_max 8`.

Two adjacent facts worth keeping with it:
- **A `NOT_SELECTABLE` challenger compiles into the lean but not the launch layer** — decision
  context carries through (`challenger_under_evaluation` at lean line ~2511), launch requirements
  do not speculate. That asymmetry is correct and deliberate; a recompile that strips the
  challenger from the lean, or promotes it into launch, is a defect.
- **`guard_all_surfaces` carries pre-existing quarter-port drift** (frontdoor/worker/ingest
  `serving.ports` vs launch manifest, unchanged since 2026-03, 13 errors) — filed as Q38-T4 in
  [`qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md). It blocks a
  fully-green check without blocking swap surfaces, i.e. a red guard is not necessarily YOUR red.

### Source References

- [`qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — the swap, ratification v2 rationale, Q38-T4
- `scripts/operator/ratify_qwen38_registry_swap_20260821.sh` — the phased recompile + its header's corrected audit trail
- epyc-inference-research `b376dadd` (master swap), orchestrator `7483d7fb` (executed ratification) — direct commit reads
- [`progress/2026-08/2026-08-21-operator.md`](../progress/2026-08/2026-08-21-operator.md) — the coordination record

## Compiled Update — 2026-08-21 (evening): a stack-change guard must be checked under the PRODUCTION fleet mode

Q38-T4 closed with neither proposed fix being right: the 13 registry-vs-stack "drift" errors were a
**check-time mode artifact**. The guard builds its launch view against the *realized* fleet mode and
defaults to `full` in a clean shell (`stack_change_guard.py:1183-1191`), which filters the half
instances out of its view while the master unconditionally projects them into `serving.ports`. Under
the production mode (`ORCHESTRATOR_STACK_NUMA_MODE=both`) all 13 errors vanish with **zero data
edits**, and after a mode-correct `update` the campaign's first fully green stack-change check landed
(`guard: ok`, `guard_strict: ok`, acceptance passed). Master, topology, template and manifest were
correct all along. **Rule: run every stack-change check under the exported production fleet mode —
a guard evaluated in a default shell is checking a fleet that does not exist** (the same
near-miss class as the 08-21 numa_ports/stack-template lesson). The ratify script now exports the
mode. Same day: the Qwen3.8-27B registry swap completed end-to-end (master registry `b376dadd`,
compile chain via `ratify_qwen38_registry_swap_20260821.sh` v2, derived `stack_priors.yaml` verified
serving Q38 @ draft_max 8), and the CT-1 chat-template A/B launched with its belief-kernel write-side
hook filed before the first result (SC46). Remaining on operator sequence: Q38-T5 stack start +
`live == config` checklist.

### Source References

- [`handoffs/active/qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — Q38-T4 ✅ closure with the mode-artifact diagnosis
- [`handoffs/active/qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) — CT-1 A/B launch + SC46 wiring
- [`progress/2026-08/2026-08-21-operator.md`](../progress/2026-08/2026-08-21-operator.md), [`progress/2026-08/2026-08-21-research-intake.md`](../progress/2026-08/2026-08-21-research-intake.md)
## Compiled Update — 2026-08-22: the KV-migration path is live, but its "VERIFIED" state proves transport, not reuse — and on the hybrid frontdoor only strict continuations reuse a restored cache

Sources: `handoffs/active/dynamic-stack-concurrency.md` (Stage-2b research-intake riders
intake-1274/intake-1279, dived 2026-08-22; earlyoom residual audit 2026-07-29; DS-7-guard row).
The three-arm reuse measurement and the multi-turn replay these findings gate are OPEN — what is
compiled here is the code-verified failure surface, the live-path evidence, and the corrected
scope, not their results.

- **The frontdoor slot save/restore path is LIVE, not dormant — its dormancy escape clause is
  void.** `--slot-save-path /mnt/raid0/llm/cache/kv_slots/frontdoor` is set on all three frontdoor
  instances (8070/8080/8180, read from `/proc/<pid>/cmdline`); 75 `kv_migrate_*` artifacts sit on
  disk; live probes recorded forward=6 / reverse=4 with `n_aborted=0`. Qualification: the newest
  artifact is 2026-08-09 and all carry synthetic `old-sess_*` ids, so the path is proven wired,
  enabled and executed — exercise by *production traffic* in the last two weeks is unproven.
- **`MigrationState.VERIFIED` verifies transport, not reuse.** `concurrency_aware.py:679` advances
  to VERIFIED with `detail="restore_confirmed"` on an HTTP 200, and `:682` then erases the source
  slot. `n_restored` proves the file loaded, not that a single token will be reused: a zero-reuse
  migration would advance to VERIFIED, destroy the source, and record success. The true reuse
  instrument already exists — `n_prompt_tokens_cache` via `GET /slots`, or `timings.cache_n` on
  the first post-restore completion ([benchmark-methodology.md](benchmark-methodology.md) already
  names it as the correct KV-reuse counter). **Reconciliation with the 2026-07-21 ROUTE-A3 closure
  above**: the forward=6 / reverse=4, `n_aborted=0` probe ratified the migration *transport* under
  traffic; by this state-machine reading it did not — and structurally could not — assert any
  reused token. The fix (gate the source erase on a reuse assertion, or rename the state) is filed
  but not landed.
- **Hybrid restore reuse is all-or-nothing on prompt shape: strict continuation reuses fully;
  divergence or exact repeat reuses zero.** Upstream #25913's "restore silently delivers zero
  prompt reuse on hybrid/recurrent models" was scope-corrected by the 2026-08-22 dive against our
  own frozen v9 source: `server-context.cpp:3320,3322` compute
  `pos_min_thold = max(0, pos_next - n_swa - (has_new_tokens ? 0 : 1))` and the reset block at
  `:3374` runs only when `pos_min >= pos_min_thold`, while `llama-memory-hybrid.cpp:172-175`
  returns the *recurrent cell's* position as `seq_pos_min` — stated outright by the PR author and
  matched by four independent upstream measurements. The frontdoor model (`qwen35moe`, 30 Gated
  DeltaNet + 10 full-attention layers) is squarely hybrid-recurrent, but our full↔quarter
  migration is a turn-boundary session handover — the *continuation* shape. So "every migration
  costs a full re-prefill" is NOT the default expectation; it is the failure mode that occurs when
  something rewrites the restored prefix (a rendered chat-template byte change, reasoning-block
  stripping — mitigated today by `--reasoning off` — or any injected timestamp/preamble). The open
  gate is correspondingly cheaper: determine whether our request stream stays a byte-exact strict
  continuation across a migration boundary, not confirm a known loss.
- **Restore-measurement methodology hazard: leftover in-RAM checkpoints fake restore success.**
  The fixture for any restore-reuse measurement must restart the target server (or set
  `--cache-ram 0`) between arms — an upstream reporter lost a day to resident checkpoints making a
  broken restore look like a 340× success, and the frontdoor runs the 8 GiB `--cache-ram` default
  with no override.
- **#25592 is the wider hybrid exposure, and it is absent from v9.** It fixes the *live in-memory*
  checkpoint path for hybrid/recurrent models — exercised on **every request**, not only on
  migrations. Our frozen tree still carries the unfixed `[TAG_CHECKPOINTS_FIX_POS_MIN]` TODO
  verbatim (`server-context.cpp:2332-2337`), and its four independent upstream verifications
  include Qwen3.6-35B-A3B — the exact frontdoor model. The whole adjacent checkpoint cluster
  (#24055, #25472 merged, #25592 open, #26004) is **performance-only** — lost reuse and forced
  full re-prefill, never wrong output. If the open multi-turn replay shows a non-trivial forced
  re-prefill rate, #25592 is a v10 candidate ahead of #26004.
- **The frontdoor's `-ub 8192` is silently inert.** `cparams.n_ubatch = std::min(cparams.n_batch,
  n_ubatch)` and `-b` is never passed, so the effective micro-batch is the **2048 default**. The
  launch config misrepresents itself, and any reasoning that assumed an 8192 ubatch on the
  frontdoor is wrong. Fix (pass `-b 8192` or drop the flag) is filed, not landed — independent of
  everything above.
- **earlyoom residual, re-verified 2026-07-29 (auditor): the tweak is host-side operator-only, and
  the measured risk is a futile kill, not "agents are victims".** Premise confirmed — the live
  process (`-M 41943040,20971520 -s 100,100 -r 60 --sort-by-rss --ignore
  '^(llama-server|sd-server)$' --prefer '^llama-bench$'`) does not ignore `claude|codex`. But the
  original prescription cannot be followed from any agent session and **both of its steps point at
  things that do not exist**: `/etc/default/earlyoom` is absent and the container is not
  systemd-booted — earlyoom is PPID 1, started at host boot, outside the container entirely. This
  refines the 2026-06-05 earlyoom entry above: the durable in-container protection remains
  launcher-side `oom_score_adj`; the ignore-regex edit is a HOST action. Measured sharpening of
  the rationale: thresholds are ~40 GB warn / ~20 GB kill against 1133 GB total with the memory
  held by *ignored* llama-servers, so if earlyoom ever fires, `--sort-by-rss` selects a ~0.7 GB
  agent session against a ~20 GB deficit — destroying a main without relieving pressure.
- **The DS-7 default template is now self-policing against generated live priors** (orchestrator
  `464aca54`, 2026-07-06 — completes the DS-7 record in the 2026-07-05 update above):
  `validate_template()` fails the production `default` profile if deployable role ports drift from
  generated live stack-prior serving ports, and alias roles pass only when their generated serving
  ports are covered by the alias target. Experimental templates stay flexible and embedding-only
  helper roles remain outside the parity surface.

### Source References

- [dynamic-stack-concurrency.md](../handoffs/active/dynamic-stack-concurrency.md) — sole compiled
  source: Stage-2b intake-1274/1279 riders (restore semantics, VERIFIED misnomer, `-ub` inertness,
  #25592 exposure, fixture hazard), the 2026-07-29 earlyoom audit, the DS-7-guard row.
- [benchmark-methodology.md](benchmark-methodology.md) — already documents `timings.cache_n` /
  `n_prompt_tokens_cache` as the true KV-reuse counter; the instrument the VERIFIED state should
  consume (cited by the source at its line 257).
- [earlyoom-oom-protection.md](../handoffs/completed/earlyoom-oom-protection.md) — the deployment
  closure whose optional `--ignore` residual the 2026-07-29 audit re-verified and corrected.
- [attention-matching-kv-compaction.md](../handoffs/active/attention-matching-kv-compaction.md) —
  Phase-F KVCOMM gate the source keeps as a separate fork from the restore-semantics work.
- epyc-orchestrator `464aca54` — DS-7 default-template prior-drift guard commit (tests:
  `test_dynamic_stack.py`, `test_stack_templates_v2.py`).
- Upstream llama.cpp #25913 / #26004 / #25592 (open) and #25472 (merged) — the hybrid
  checkpoint/save-restore cluster; performance-only, produces no wrong output.

## Compiled Update — 2026-08-23: the Qwen3.8 swap is LIVE — and the DFlash2 challenger stays on its experimental-runtime contract

**Confidence: verified** — Q38-T5's five-point checklist was executed against the live :8083
process (pid 896239), and the campaign posture is read from the handoff's receipt chain.

Sources: `handoffs/active/qwen38-27b-replace-qwen36.md` (Q38-T5/T6),
`handoffs/active/dflash2-block-drafter-experimental-build.md`,
`progress/2026-08/2026-08-21-operator.md`, `progress/2026-08/2026-08-21-research-intake.md`,
`progress/2026-08/2026-08-21.md`.

### The swap is served: Q38-T5 stack start, `live == config` verified

The 2026-08-21 22:00Z start closed the swap campaign. Built-in stack-change gate PASSED at launch
(`promotion_gate: ok`, launch roles match registry); 15 servers healthy; five-point checklist all
green on :8083 (pid 896239): (1) serves `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf` with the
documented Unsloth template; (2) flags `--device ROCm0 --jinja --spec-draft-n-max 8` — the measured
optimum, live; (3) all four ggml libs from frozen v9 `build-hip` on the LIVE process maps; (4) KFD
count 4 (designed GPU co-tenancy: architect+vision+sd+embedder); (5) real generation correct
(17×23→391), `enable_thinking=false` live-confirmed (empty reasoning_content), VRAM 93% sampled
DURING the request. The **master-swapped ≠ lean-compiled ≠ derived-compiled ≠ served** chain from
the 2026-08-21 section is now closed at the last inequality: the derived plane's
Qwen3.8-27B-Q8_0 @ draft_max 8 (ratification `7483d7fb` executed and pushed; master swap
`b376dadd`, on origin since `bb405297`) is what :8083 actually serves.

**Operator flag, one observation:** the cold-start launcher rejected the `both` lineup (no fleet to
adopt) and fell through to priors at `--numa-mode=quarter` — HALF instances launched
(:8080/:8180/:8082/:8182/:8185/:8285), FULL instances (:8070/:8072) did NOT. Single-stream
frontdoor throughput therefore ran on halves; whether to restart into `both` (full+halves) is a
lineup-policy call left to the operator, not churned at 22:00. Root cause filed as **Q38-T6**: the
launcher NEVER reads `ORCHESTRATOR_STACK_NUMA_MODE` — mode is argv-only, and the cold-start
fallback at `stack_commands.py:1588` is hardcoded `"quarter"` (pre-dating the 2026-07-30 half-fleet
ratification) — so an unflagged cold start silently drops all three full instances
(frontdoor :8070, worker_general :8072, ingest_long_context :8085). Verified-safe recovery path:
`start --only frontdoor worker_general ingest_long_context --numa-mode both` + scoped
`reload orchestrator` (the `--only` clobber fix `f2ffd298`).

### The DFlash2 challenger: np1 sealed; grid + parity mandatory; the kernel-source frontier is closed by contract

Campaign state: **build / no-regression (GPU+CPU) / matched np1 complete** — manual PR #27342
forward-port on `ak/dflash2-qwen38-20260820` @ `2046c64e` (frozen v9 untouched; `a6b4b5263` remains
an ancestor, but DF2-2 stays open until the DFlash2 block-verify dispatch itself is proven rather
than inferred from source presence), full Release/gfx90a HIP build, CPU + real-model GPU smoke
passed, 36/36 np1 requests error-free, receipts SHA-256-pinned, GPU claims released, VRAM back to
the 13,094,912-byte idle baseline. The matched np1 numbers are compiled above (2026-08-20 section);
what the 2026-08-23 state adds is posture: **55.46 t/s at MTP n-max 8 is the PREDECLARED
single-stream comparator** — the decision rule was written into the campaign before np1 ran ("if
dFlash2 does not beat 55.46 t/s single-stream *and* hold up at np=8, it does not displace MTP"), so
the np1 result (+26.81% over the matched MTP arm) clears only the single-stream half.
**Remaining and mandatory: the np2/4/8 concurrency grid (DF2-5) and exact greedy parity (DF2-6)** —
DF2-5 runs three arms (none/MTP/DFlash2) at every point because the upstream concurrency report
(#27117) is DFlash-1, predates PR #27342, and carries a `--kv-unified` confound nobody has
controlled for; DF2-6 additionally needs the route-log proof that the block-verify workload
(`ne11≈8`) reaches the intended optimized dispatch, not the less-tuned path `a6b4b5263`'s
MTP-verify shape was tuned for. The registry carries the challenger as
`challenger_under_evaluation` / `np1_only_NOT_SELECTABLE` (`bd40ca94`) — decision context, not a
selection; `spec_type: draft-mtp` / `n_max: 8` untouched.

**Campaign contract (governs any future DFlash2 number):** this is the replacement campaign's
`experimental_runtime` sibling under the AutoKernel loop — a fixed, resumable receipt chain
(`experimental_build` → `cpu_gpu_regression` → `matched_np1` → `concurrency_grid` → `greedy_parity`
→ `decision`) binding candidate/build/model/protocol identities and, for GPU stages, the claim
window; **no DFlash2 result may enter the kernel-source champion frontier**; a stopped campaign
resumes at the first missing or invalid receipt and never reruns a sealed cell. The AMD negative
datapoint to hold in view: upstream #25117 reports DFlash at 0.48× baseline on an AMD APU
(gfx1151, Q4_K MoE target) — not our discrete MI210 dense Q8_0, but exactly the failure class
DF2-2/DF2-5 are designed to catch.

### Source References (2026-08-23 Qwen3.8-27B stack + DFlash2 posture)

- [`qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — Q38-T5 ✅ five-point live evidence + operator flag; Q38-T6 root cause and recovery path
- [`dflash2-block-drafter-experimental-build.md`](../handoffs/active/dflash2-block-drafter-experimental-build.md) — campaign state, predeclared comparator + decision rule, receipt chain, DF2-2/5/6 gates, #25117 negative
- [`progress/2026-08/2026-08-21-operator.md`](../progress/2026-08/2026-08-21-operator.md) — executed ratification `7483d7fb`, derived-layer verification, coordination sequence
- [`progress/2026-08/2026-08-21-research-intake.md`](../progress/2026-08/2026-08-21-research-intake.md) — fourth-pass ratification execution + validation, dFlash2 `challenger_under_evaluation` carried through the recompile
- [`progress/2026-08/2026-08-21.md`](../progress/2026-08/2026-08-21.md) — AutoKernel lifecycle (v20–v25) and the CPU-TP proposal; the governed loop the experimental_runtime contract routes through

---

## Compiled Update — 2026-08-23 (evening): the cold-start lineup fix, the slot save/restore path read live, and the CT-9 pilot decision

**Confidence: verified** — Q38-T6 is a landed fix with 290 tests; the H20/H21 findings are live-process reads from `/proc` with timestamps and a zero-compute code trace of `/v1/chat/completions`; the migration-state fix landed in `epyc-orchestrator` `98061c6b` with 75 disk artifacts inspected.

### Q38-T6 closed: the cold-start lineup defect is FIXED (orchestrator `96498c3d`)

The launcher NEVER read `ORCHESTRATOR_STACK_NUMA_MODE` — mode came from argv `--numa-mode` only, and the cold-start fallback was hardcoded `"quarter"` (`stack_commands.py:1588`, pre-dating the 2026-07-30 half-fleet ratification), so an unflagged cold start silently dropped the THREE full instances (frontdoor :8070, worker_general :8072, ingest_long_context :8085). Fixed three ways: (a) `cmd_start` fallback is now realized-fleet inference first, else the env var, else ratified `"both"`; (b) stale argparse help ("QUARTERS-ONLY…FULL_DISABLED") and the `_filter_by_numa_mode` docstring rewritten for the half-fleet reality (quarters retired 2026-07-30; `quarter` token = halves 2×48t; `both` is ratified production); (c) API-side producer-2 liveness veto corrected — a TOTAL cold start (nothing listening anywhere) is not the env=full poison signature; the veto now requires ≥1 live port anywhere, so a cold start accepts the lineup instead of logging a spurious "lineup rejected" and falling through to stale priors. Recovery path re-verified intact: explicit `--numa-mode both` still wins. 290 targeted tests pass.

### The slot save/restore path: ARMED, not dormant — and the post-migration request is a STRICT EXTENSION

The dormancy escape clause on the KV-migration row is **VOID**: `--slot-save-path /mnt/raid0/llm/cache/kv_slots/frontdoor` is set on all three frontdoor instances (8070/8080/8180, read from `/proc/<pid>/cmdline`), 75 `kv_migrate_*` artifacts sit on disk, live probes recorded forward=6 / reverse=4 with `n_aborted=0` (synthetic `old-sess_*` ids; newest artifact 2026-08-09 — exercise by production traffic in the last two weeks is unproven, but the path is wired, enabled and demonstrably run). Two live-process samples one day apart (2026-08-22T~14:43Z and 2026-08-23T07:52:51Z): same PID 2052930 on :8070, elapsed 18h35m, argv unchanged — `--slot-save-path`, `-ctk q8_0 -ctv q8_0`, `--reasoning off`, `--spec-type draft-mtp --spec-draft-n-max 4`, `-ub 8192` with **no `-b`** (independently confirming K4). The flag is emitted **unconditionally** for every role built by `orchestrator_stack.py:1471-1480`; `ORCHESTRATOR_REVERSE_MIGRATION` defaults to `"1"`. **Methodological lesson recorded to the minute:** two dive blocks appeared to contradict each other on whether :8070 had a listener — block 1 read `/proc` before the 13:17:35Z restart and was already stale when block 2 ran. Every `/proc`/`ss`/`ps` result quoted in a handoff must carry its timestamp, and a second sample if load-bearing.

**H21 (Z, answered in-session — a finding, not a task):** traced through `/v1/chat/completions` (`openai_compat.py`), `_context_parts_from_history` renders each history message as exactly one `"{Role}: {content}"` line — append-only, no summarisation/truncation/reordering/windowing — joined with `"\n\n"`, and `_combined_prompt_with_context` returns `f"{context}\n\nUser: {prompt}"`. So **turn N+1 begins with turn N's prompt byte for byte: a STRICT EXTENSION** — full prompt reuse across a migration boundary. Two bounded exceptions: **(a)** `context_compression` rewrites history above 8 messages but is OFF (default and fallback both `False`, string absent from the repo, absent from the live environment) — but it is a **one-flag divergence**: enabling it silently destroys strict-extension for every conversation past 8 messages; **(b)** `request.tools` — the native-tools block is appended *after* history, so the shared prefix ends at the previous turn's history and the tail re-prefills: **bounded and independent of conversation length, not a full re-prefill** — but a tools-carrying session never reuses its own last turn (this is arm E3 of G4). Scope: OpenAI-compat chat route only; says nothing about vision, completions, or non-OpenAI ingress. `--reasoning off` on the live process removes the thinking-block divergence separately.

**The misnamed `VERIFIED` migration state is fixed** (`98061c6b`): `_slot_save` now *returns* `n_saved` and `_slot_restore` returns `n_restored` instead of discarding the count into a log string; the forward path aborts on `n_restored != n_saved` **before** `advance(MigrationState.VERIFIED)` and before erasing the source slot; the reverse path carries the identical guard; `llama_server.py:1268/1284/1302` was fixed in the same commit (previously did not parse the body at all). The triggering input is on disk: of 75 slot files, exactly 9 are 752-byte header-only saves (next smallest 66,148,192 B — strictly bimodal), 4 of the 9 `old-sess_*`. Residual, deliberately not re-opened: the state now means *"the KV came back complete"* — strictly stronger than HTTP 200, still weaker than *"a token was reused"*; the reuse instrument (`timings.cache_n`) is what G4 reads. **#25592 is the LARGER exposure** and a v10 candidate: it fixes the live in-memory checkpoint path that runs on **every request** (not only migrations), is open upstream, absent from our tree (`server-context.cpp:2332-2337` still carries the unfixed `[TAG_CHECKPOINTS_FIX_POS_MIN]` TODO), and has four independent verifications including one on Qwen3.6-35B-A3B, our exact frontdoor model. Measurement: multi-turn agentic replay at 16K/64K counting forced full re-processing; a non-trivial rate makes #25592 a v10 candidate ahead of #26004. Do not conflate with the adjacent checkpoint cluster (#24055, #25472, #25592, #26004) — that cluster is entirely *performance* (lost reuse), no wrong output.

### The in-band error fail-open under the 2026-08-11 fix is now closed

The 2026-08-11 fix stopped *raised* exceptions becoming 200s, but the layer beneath still failed open: `LLMPrimitives.llm_call` does not raise — it returns `[ERROR: ...]` strings at start-of-answer, and those in-band failures reached clients as HTTP 200 assistant content (streaming closed `finish_reason: "stop"`). Now detected at the route via the canonical `inband_error_text()` rule: non-streaming → 502 `HTTPException`; streaming → terminal SSE `error` event + `finish_reason: "error"`; REPL path checks the raw result before the auto-wrap into `FINAL(...)`. A model answer *beginning* with `[ERROR:` is classified as a backend failure (codebase-wide convention); mid-answer occurrences stay 200 (guarded). 4 new tests failed against the unfixed code, 10/10 green after; 121 passed across the openai_compat surface.

### CT-9 — the pilot-adoption decision: HOLD all three roles, no fleet-wide extension, nothing reverted

Decision basis = production behavior over ~18 h (2026-08-22 13:55Z → 2026-08-23 08:00Z), NOT new benchmarks. **The window carried CALIBRATION traffic only — zero real user/autopilot traffic after 15:36:49Z** (autopilot stopped since 08-09; the 186 API completions and 4,943 server-side slot lines are E-7 recalibration runs). Operational signal: 0 server errors, 0 truncations, 0 slot-restore failures, 0 KV-migration events on :8070/:8080/:8180/:8083; one gateway-side 504 whose server-side completion returned 200; halves :8080/:8180 received zero requests ever. Decision lines: **frontdoor → HOLD** (E-7 stamps 82.5/37.5/55.0/32.5 reproduce CT-1b arm-2 live; revert is one line); **architect_general → HOLD** (first-ever stamps 85.0/27.5/47.5/22.5, cot 75.0 @4096; 282 clean slot releases, 0 errors); **coder_escalation → HOLD** (alias on :8083; no production signal exists — the cruxeval watch-item has NO basis in this window); **fleet-wide → NOT EXTENDED** (the adoption precondition "serves real traffic for a while" is unmet; extending unmeasured roles would void their CT-2 calibration slices on an unmeasured basis). What would flip a role to REVERT: any error/truncation/slot-restore signature or real-traffic quality drift — none observed. Follow-ups filed: **CT-10** (cruxeval watch-item re-check under real coder traffic) and **CT-11** (re-decide after the first non-calibration traffic signal). The KV-migration bug `98061c6b` is independent of the pilot (all 9 header-only slot files predate it by 3–4 weeks).

### Source References (2026-08-23 evening)

- [`qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — Q38-T6 closure (`96498c3d`): fallback chain, help/docstring corrections, liveness-veto fix, recovery path
- [`dynamic-stack-concurrency.md`](../handoffs/active/dynamic-stack-concurrency.md) — K4 (`-ub 8192` inert), the G4 scope correction + H20/H21 live reads (with timestamps), the `98061c6b` migration-state fix, the #25592 v10-candidate row, the strict-extension trace
- [`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) — the in-band `[ERROR: ...]` fail-open closure (502 / terminal SSE `error` / REPL pre-check)
- [`qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) — CT-9 decision lines with the calibration-only window evidence, CT-10/CT-11 follow-ups (template decision compiled in [Chat Templates](chat-templates.md))
- [`progress/2026-08/2026-08-23.md`](../progress/2026-08/2026-08-23.md) — the full CT-9 evidence bundle and the tier-1 backlog-pass context
