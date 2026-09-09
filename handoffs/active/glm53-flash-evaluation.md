# GLM-5.3-Flash Evaluation (glm5next)

**Status**: IMPLEMENTED / CPU-VALIDATED 2026-09-09 — Q8 prefill and reference-correct parallel MTP pass canonical48 paired checks. Observed +22.6% long prefill, +24.8% repeated512 MTP decode and +41.1% on the24-prompt workload. Qwen reachability audit complete; broader role-fit remains T4.
**Created**: 2026-08-31 (spun out of the OP-8 KILL ruling; inherits the GLM-MoE-DSA findings)
**Priority**: MEDIUM — one of the two operator-named novel-under-test models (with qwen3.8-next-flash)
**Categories**: inference_serving, local_inference, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-69)
**Related**:
- [`../completed/glm51-reap-cpu-evaluation.md`](../completed/glm51-reap-cpu-evaluation.md) — the
  GLM-5.2 evaluation (KILLED 2026-08-31, artifact deleted): the evidence record this handoff inherits from
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) — owns the generic DSA
  D2/D3 sparse-attention profiling gates (do not duplicate them here)
- [`tree-draft-forward-port-plan.md`](tree-draft-forward-port-plan.md) — native GLM MTP head port scoping

## Artifact identity

| Field | Value |
|---|---|
| Local path | `/mnt/raid0/llm/models/unsloth/GLM-5.3-Flash-GGUF/UD-Q4_K_XL/` (6 shards) |
| Architecture | **`glm5next`** — NEW arch, not `glm-dsa`; 288×10B experts (`general.size_label`) |
| DSA surface | `glm5next.attention.indexer.{head_count,key_length,top_k,kpool}` — same Lightning-Indexer family, plus a new `kpool` field |
| MTP surface | `glm5next.nextn_predict_layers` present |

## Inherited findings (from the GLM-5.2 evaluation — verify each against glm5next before relying on it)

**2026-09-08 audit supersession:** GLM5Next is hybrid KDA + MLA/DSA + mHC, not merely
GLM-DSA with another key. Three open upstream PRs implement the architecture; #27917 adds
native MTP to #27773. **Speculative decoding is required by the operator.** The legacy findings
below are historical hypotheses, not established properties of the proposed port. In particular,
do not transfer the old top-k workaround or the old claim of absent GLM-family MTP support.
See [the source/GGUF/upstream audit](../../docs/reference/models/glm53-flash-support-audit-20260908.md)
for pinned identities, metadata/quantization differences and the full validation contract.

1. **DSA-DENSE-MASK**: on this fork the generic DSA path computes the indexer + top-k but final
   attention still runs over FULL KV with a mask (`build_attn` constructs `kq_mask_top_k` over full
   KV length; no sparse gather). Any glm5next support inherits this until the sparse-gather gate in
   `llama-cpp-dsa-contribution.md` lands. Never claim long-context sparse-compute value without it.
2. **`indexer_top_k` is the final-attention KV selection cap, and an under-sized cap CORRUPTS
   output** once prompt length exceeds it (GLM-5.2: exact-output fails beyond the cap; safe policy
   was next-power-of-two ≥ prompt tokens). glm5next adds `kpool` — re-derive the semantics, do not
   assume the 5.2 thresholds.
3. **NextN/MTP**: GLM GGUFs preserve the NextN tail block but the fork's GLM archs skip those
   tensors and never dispatch `LLM_GRAPH_TYPE_DECODER_MTP`; the smallest credible port is Qwen-style
   tail-tensor loading + a `DECODER_MTP` graph (not a flag flip). Applies if glm5next's MTP is wanted.
4. **Wiring precedent**: experimental-v7 `3dee86a5a` is the worked example of wiring a GLM arch into
   `llama_kv_cache_dsa` + the DeepSeek32 DSA graph (incl. forced indexer Hadamard tensors and the
   arch tests that validated it).
5. **Evidence contract** for any long-output/throughput/quality probe: streaming progress, retained
   trace logs, server-log timing extraction, minimum completion-token floor; record every quality
   claim with `(prompt tokens, chosen indexer_top_k)` together.

## Tasks

**2026-09-08 implementation checkpoint:** the operator approved the port with
vision optional. Candidate `experimental/glm53-text-mtp-20260908` lives at
`/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908`, based on champion
`ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`. The six-shard tensor/schema audit and
portable fixture checks pass (5/5 with the local artifact enabled).
The extra compute-approval gate was withdrawn after the operator challenged the
stop; the requested experimental work runs under physical locks, with timings
restricted to observations on this unrebooted host. Candidate `2346de909`
(`llama-server` 10308) builds and passes all four tiny variants: 48 rejection/replay
cases, four used-MTP-context restores, and 24 pool-boundary cases. The full-model
native-MTP smoke passed (10.5371 output tokens/s for 32 tokens; 21/28 drafts
accepted), and trace events witness actual draft rejection. The paired five-by-512
throughput benchmark completed; normal parallel MTP fails parity and existing
serial verification passes. Profiling and bounded configuration experiments
identify the high-value levers in the [profile report](../../docs/reference/models/glm53-cpu-profile-20260908.md). Details:
[session progress](../../progress/2026-09/2026-09-08-glm53-support-audit.md).

- [x] T0 — **Arch-support audit**: does any tree on this host load `glm5next` (production v9: no —
  frozen pre-arch; experimental/champion: check; upstream llama.cpp: check for a landed PR)? Output:
  the backport-or-wait decision, same shape as the qwen4exp bringup. ✅ 2026-09-08
  Evidence: [audit](../../docs/reference/models/glm53-flash-support-audit-20260908.md).
  Recommend adapting pinned #27773 + #27917 into a champion-descended experimental candidate;
  this is a source-audit recommendation, not a built or validated port.
- [x] T0-SPEC — Adapt the architecture and native-MTP stack with local GGUF compatibility;
  validate target/draft hidden-state semantics, index sharing and convolution/KDA/cache rollback
  at every rejection position before declaring speculative decoding supported. Trunk-only load
  is an intermediate gate, not completion. Completed for CPU with existing serial
  verification: five exact 512-token trajectories, actual accepted/rejected drafts,
  and independent rollback/MTP-state fixture tests. The initial parallel verifier failed greedy parity; candidate `04ffb8ad0` now
  passes the paired CPU gates in the [optimization report](../../docs/reference/models/glm53-cpu-optimization-20260908.md).
- [x] T1 — Load + short-context coherence smoke on the chosen tree (abort on repetition loops),
  CPU-only, canonical env; record `(arch, indexer defaults, kpool)` from the load log.
- [ ] T2 — DSA-path disposition for glm5next: DENSE-MASK vs sparse (expect DENSE-MASK per finding 1);
  `indexer_top_k`/`kpool` semantics probe BEFORE any quality run (finding 2).
- [x] T3 — Throughput baseline at the canonical recipe (interleave + no-mmap, t48/t64, r5) —
  observation-grade first; codified attestation only if it becomes a serving candidate.
- [ ] T4 — Quality/role fit per the standard suites; GO / WAIT / KILL disposition with the disk-retention
  decision (artifact is in the novel-under-test keep bucket until this verdict).

## Authorized optimization work — 2026-09-08

- [x] T5 — Implement Q8 prefill acceleration with phase-aware dispatch and validate
  numerical/task quality against the preserved GLM reference.
- [x] T6 — Implement measured decode projection/synchronization improvements;
  first audit Qwen4Next/INF-70 development for immediately reusable wins.
  Achieved through parallel verification amortization; useful champion paths
  already reach GLM. No new standalone Q8 dot-kernel gain is claimed.
- [x] T7 — Implement reference-correct parallel MTP; preserve the selected plain
  reference and validate accepted/rejected drafts, rollback and multiple prompts.
- [x] T8 — Retest the integrated candidate with the canonical CPU recipe at
  48 target/draft/batch threads, source-pinned workload and retained raw evidence.

The prior throughput confirmation was stopped as requested. The new runs are
separately authorized by the operator's implementation request. Baseline binary
`2346de909` is preserved under `glm53-validation-20260908/baseline-2346de909`;
source-only helper HEAD `f25c89d52` is the implementation starting point.

Completion evidence: candidate `04ffb8ad0`, [implementation and results](../../docs/reference/models/glm53-cpu-optimization-20260908.md).
Final plain/MTP agree on all24 workload, five quality, five repeated512 and two
additional512 responses; repeated512 also preserves the original reference.
Q8 prefill changes22/24 trajectories versus the old kernel; the bounded quality
screen is3/5 versus2/5, not broad quality certification. Production is unchanged.

## Reprofile follow-up — 2026-09-09

- [x] T9 — Reprofile the integrated candidate at canonical48, separating prefill
  and decode, and rank the next high-value levers. Completed with matched2029-token
  prefill and512-token plain/MTP profiles, corroborating short-context pair and
  independent period/output audit. [Report](../../docs/reference/models/glm53-cpu-next-levers-20260909.md).
- [x] T10 — Repair the discovered multi-ubatch MTP selection-width assertion,
  reproduce on the old binary, validate both aliases and retry the real long
  input. Fix `7c78663de`, full/chunk regression `c463f601b`; original experimental
  tree and canonical build updated. CPU library arithmetic is unchanged.

Current tested recipe remains native-MTP depth3. The depth2 diagnostic is
rejected: exact output diverges at index58 and its single observed rate is
lower. Do not generalize the passing depth3 evidence to arbitrary draft widths.
The next proposed kernel work is reference-exact multirow expert reuse, then
exact batched Q8, then measured graph/worker scheduling. Profiling shares are
not prospective speedups; no performance kernel was developed in this follow-up.

## Three-lever implementation follow-up — 2026-09-09

Operator authorized all three next kernel experiments at canonical 48 threads.
Starting candidate is `c463f601b`; preserved baseline and instrumented builds
must remain distinct. Final decision table: each lever's bitwise kernel gate,
full-model token/rejection/replay gate, and matched unprofiled performance;
retain only correctness-passing improvements. Use five repeated 512-token
continuations per arm for short and 2,029-token prompts, plus matched prefill.
Do not pool these with the earlier 24-prompt workload's 10.82479 tokens/s.

- [ ] T11 — Implement and validate exact multirow Q4_K/Q5_K expert reuse.
- [x] T11a — Implement the guarded expert-kernel experiment and pass its compiled
  bitwise operator gate at the real GLM Q4_K/Q5_K dimensions. The test compares
  mapped multirow buckets with the serial Ny=1 path at 48 threads, including
  noncontiguous routes, row tails and chunk offsets; Q4_K 49,152/49,152 and
  Q5_K 98,304/98,304 outputs match exactly, with branch traces. Full-model and
  performance gates remain T11/T14. ✅ 2026-09-09
- [x] T11b — Run the five-pair operator microdiagnostic for expert reuse at the
  GLM dimensions. All 80 type/width/arm/round cells have exact paired output
  hashes. Median serial/optimized ratios for widths 2/3/4 are
  1.075/1.120/1.149 for Q4_K and 1.108/1.156/1.227 for Q5_K; width 1 controls
  are 1.017/1.013. This is noisy, noncanonical kernel-level evidence only;
  full-model performance and replay gates remain open. ✅ 2026-09-09
- [x] T11c — Run the matched one-request full-model expert screen with Q8 row
  batching disabled. Off/on produce the same 512-token trajectory as the prior
  plain/MTP reference, the same 561/323 drafted/accepted counters, and 122
  verification events with rejection. Expert reuse reaches its rows=2 branch
  but measures 9.8985 versus 9.7305 output tokens/s (0.9830x). Keep the lever
  off; this screen does not justify a five-repeat expert-only run. ✅ 2026-09-09
- [ ] T12 — Implement and validate exact batched native Q8 verification.
- [x] T12a — Rebuild and repeat the Q8 operator gate for the specialized mode-1
  source/test corrections. That binary passes 4/4 cases and CTest with
  an active rows=4 branch witness, covering Ny2/3/4, native and converted Q8,
  noncontiguous input, broadcast stride, multiple heads and worker tails.
  ✅ 2026-09-09
- [x] T12c — Validate Q8 mode 2 (two weight rows across up to four activation
  rows): all five operator cases pass for each of modes 0/1/2, with branch
  witnesses and CTest. Tail-focused correctness uses three workers; the paired
  microbenchmark uses canonical 48 workers and exact outputs. AB/BA means
  improve 1.073x for MLA and 1.023x for output projection. These bounded
  operator observations warrant the full-model screen, not enablement.
  CPU library SHA256 begins `e8c93f6c`; both modes remain default off. ✅ 2026-09-09
- [ ] T12b — Complete paired Q8 mode comparison and retain or reject the lever.
  The first exact microdiagnostic is negative (0.960x MLA, 0.943x projection);
  treat it as directional. Mode 2 has cleared its separate compiled and
  paired micro gates (T12c); its first full-model pair is correctness-only
  because the off arm overlapped substantially higher unrelated CPU work.
- [x] T12d — Run the first full-model mode0/mode2 reachability and correctness
  screen inside the same UD-Q4_K_XL model. Both arms match the prior 512-token
  trajectory and MTP counters, with real draft rejection; mode2 reaches its
  rows=2 branch. The apparent 1.0497x ratio is rejected for attribution because
  median unrelated load was 8.41 versus 1.82 CPU-equivalents. A clean mode0
  bracket reaches 9.3046 versus mode2's 9.4659 tokens/s (1.0173x); this remains
  a single bracket, so the interleaved decision gate stays open. ✅ 2026-09-09
- [ ] T13 — Measure node-level worker waits and validate a bounded scheduling change.
- [x] T13a — Complete the node-level worker audit. The mixed MTP target topology
  exposes 34 recurrent-state copies totaling 11.132 ms (4.36% of sampled wall
  time); their `ne01=1` partition assigns four snapshots to one worker. This is
  an opportunity bound, not a speedup. A guarded outer-row partition fix now
  owns T13's remaining correctness and timing gates.
  [Audit](../../docs/reference/models/glm53-cpu-worker-audit-20260909.md). ✅ 2026-09-09
- [x] T13b — Implement guarded outer-row CPY scheduling with conservative
  overlap fallbacks and pass separate/fallback copy tests on committed source
  `068db793f`. Expert, Q8 projection, and both CPY CTests pass in the final
  build; serving snapshot is pinned to version 10315 and CPU library
  `f820fe5a`. Model rejection/replay and performance retention remain T13/T14.
  ✅ 2026-09-09
- [ ] T14 — Retest the integrated retained candidate against the preserved baseline.

## Constraints

- Authorized experimental inference runs under held physical CPU-region claims; observations on the unrebooted host do not authorize production promotion.
- Do NOT add a `model_registry.yaml` role without operator approval.
- Any DSA correctness finding also updates `llama-cpp-dsa-contribution.md` (single owner of the
  generic gates).
