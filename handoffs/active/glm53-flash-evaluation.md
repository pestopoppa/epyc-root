# GLM-5.3-Flash Evaluation (glm5next)

**Status**: CORE IMPLEMENTED / CANDIDATE NOT ACCEPTED 2026-09-09 — text-only
`glm5next` and native depth-3 MTP pass exact rollback/replay and all 31 full-model
plain/MTP trajectory pairs with real draft rejection. Candidate `c463f601b` is
**not** the canonical champion: `ef81196d5` remains unchanged. The exact
historical-harness CPU check measured 32.152575 tokens/s against the historical
43.280708, so CPU performance admission remains unresolved; the matched GPU
DFlash2 sanity check measured 79.598706 against 79.245255. The earlier GLM
prefill/MTP gains remain historical candidate observations, while the subsequent
expert, batched-Q8 and CPY experiments produced no additional full-model gain and
remain disabled or removed. Four `measured_null` records and the source/evidence
bundle are now in AutoKernel memory for future CPU investigation. DSA semantics
(T2) and role/quality fit (T4) remain open; no inference job remains queued by
this session.
**Created**: 2026-08-31 (spun out of the OP-8 KILL ruling; inherits the GLM-MoE-DSA findings)
**Priority**: MEDIUM — one of the two operator-named novel-under-test models (with qwen3.8-next-flash)
**Categories**: inference_serving, local_inference, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-69)
**Related**:
- [AutoKernel source handoff](../../docs/reference/models/glm53-autokernel-handoff.md) — exact private-fork source, build/launch recipe, rejected experiments and mandatory MTP gates
- [`../completed/glm51-reap-cpu-evaluation.md`](../completed/glm51-reap-cpu-evaluation.md) — the
  GLM-5.2 evaluation (KILLED 2026-08-31, artifact deleted): the evidence record this handoff inherits from
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) — owns the generic DSA
  D2/D3 sparse-attention profiling gates (do not duplicate them here)
- [`tree-draft-forward-port-plan.md`](../completed/tree-draft-forward-port-plan.md) — native GLM MTP head port scoping

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
The proposed expert, batched-Q8, and graph-worker experiments are now complete.
All passed their bounded correctness gates, but none demonstrated a full-model
gain. Their default-off/reverted implementations and final AutoKernel source are
summarized in the [source handoff](../../docs/reference/models/glm53-autokernel-handoff.md).

## Three-lever implementation follow-up — 2026-09-09

Operator authorized all three next kernel experiments at canonical 48 threads.
Starting candidate is `c463f601b`; preserved baseline and instrumented builds
must remain distinct. Final decision table: each lever's bitwise kernel gate,
full-model token/rejection/replay gate, and matched unprofiled performance;
retain only correctness-passing improvements. Use five repeated 512-token
continuations per arm for short and 2,029-token prompts, plus matched prefill.
Do not pool these with the earlier 24-prompt workload's 10.82479 tokens/s.

- [x] T11 — Implement and validate exact multirow Q4_K/Q5_K expert reuse; reject
  retention after the exact one-request short full-model screen showed no gain.
  ✅ 2026-09-09
- [x] T11a — Implement the guarded expert-kernel experiment and pass its compiled
  bitwise operator gate at the real GLM Q4_K/Q5_K dimensions. The test compares
  mapped multirow buckets with the serial Ny=1 path at 48 threads, including
  noncontiguous routes, row tails and chunk offsets; Q4_K 49,152/49,152 and
  Q5_K 98,304/98,304 outputs match exactly, with branch traces. T11c and T14
  record the completed full-model and final regression disposition. ✅ 2026-09-09
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
- [x] T12 — Implement and validate exact batched native Q8 verification; keep
  it default off after the balanced five-request short full-model screen showed
  no gain. ✅ 2026-09-09
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
- [x] T12b — Complete the paired Q8 comparison and reject retention. A balanced
  A3/B3/B2/A2 run produced five measurements per setting: baseline mean/median
  9.2318/9.2866 and Q8 mode-2 mean/median 9.0863/9.0452 tokens/s, ratios
  0.9842/0.9740. Outputs, stable request projections, MTP counters and actual
  rejection events match; comparable contention and a clean second Q8 block
  confirm that the short gate did not clear. ✅ 2026-09-09
- [x] T12d — Run the first full-model mode0/mode2 reachability and correctness
  screen inside the same UD-Q4_K_XL model. Both arms match the prior 512-token
  trajectory and MTP counters, with real draft rejection; mode2 reaches its
  rows=2 branch. The apparent 1.0497x ratio is rejected for attribution because
  median unrelated load was 8.41 versus 1.82 CPU-equivalents. A clean mode0
  bracket reaches 9.3046 versus mode2's 9.4659 tokens/s (1.0173x); this single
  bracket was superseded by the balanced rejection result in T12b. ✅ 2026-09-09
- [x] T13 — Measure node-level worker waits and validate a bounded scheduling
  change. Measurement completed; route validation rejected the candidate before
  retention. ✅ 2026-09-09
- [x] T13a — Complete the node-level worker audit. The mixed MTP target topology
  records 34 recurrent-state copies totaling 11.132 ms (4.36% of sampled wall),
  but their source and destination are contiguous. They already use the
  48-worker block-partitioned path, so the initial `ne01=1` single-worker claim
  is retracted. The measured copy cost remains valid; it is not an opportunity
  bound for the rejected outer-row patch.
  [Audit](../../docs/reference/models/glm53-cpu-worker-audit-20260909.md). ✅ 2026-09-09
- [x] T13b — Implement and correctness-test the default-off outer-row CPY
  experiment at `068db793f`, then audit actual model reachability. The inventory
  contains 408 qualifying small F32 `[3,8192,1,1]` copies already parallel over
  8192 rows; the first ACTIVE witness verifies this route class, while
  contiguity proves the branch cannot reach the 34 large state copies. The experiment was rejected
  and removed in private commit `f8e2668b6`; its overlap/fallback tests remain
  a valid record of the discarded implementation. ✅ 2026-09-09
- [x] T13c — Run the bounded canonical-48 copy microbenchmark and model screen.
  The synthetic padded, noncontiguous `[1048576,1,4]` case was byte-exact and
  measured 0.464135/0.183828 ms off/on means (2.524827x; median ratio 2.430912x),
  but that layout is absent from the profiled state copies. The five-arm model
  selector was exact but its opening/closing controls drifted 4.08%; it supports
  no CPY or Q8 throughput claim. Benchmark-only commit `a4ec393a9` preserves the
  rejected micro evidence. ✅ 2026-09-09
- [x] T14 — Complete integrated selection and mandatory speculative regression
  gates. The five-arm selector was exact but drifted; the balanced Q8-only repeat
  rejected the last candidate lever. Final `f8e2668b6` regression executables
  pass both aliases, rollback, used-MTP restore, pooled state, long export and
  six real-model row-exact comparisons. No new lever was retained, and the long
  performance phase was not run after the short gate failed. ✅ 2026-09-09

Final evidence and the exact branch intended for future discovery are collected
in the [AutoKernel source handoff](../../docs/reference/models/glm53-autokernel-handoff.md).

## Champion integration — operator-authorized 2026-09-09

- [ ] T15 — Fold the GLM core through `c463f601b` into the existing AutoKernel champion lineage, build CPU/HIP with the champion recipe, validate GLM native-MTP and existing-model regressions, and refresh the admitted champion identity/standing. Validation worktree: `/mnt/raid0/llm/llama.cpp-experimental-glm53-champion-20260909`, branch `ak/champion-glm53-candidate-20260909`; created from current champion `ef81196d5` by fast-forward. The rejected experiments remain at `f8e2668b6`. **Disposition:** do not admit `c463f601b`; the matched CPU result remains below the historical champion observation. `ef81196d5` stays canonical. Any causal investigation or revised candidate is future AutoKernel work, not a pending inference task in this session. Frozen production is unchanged.

- [x] T15a — Create the champion-descended GLM core candidate, build matching CPU control/candidate and the house-flag HIP candidate, and pass the freshly built GLM alias/rollback/restore/pool/long-export and six exact real-model phase comparisons. Evidence: `final-spec-regressions-champion-candidate-c463f601b-20260909T104706Z`. Full-model trajectories subsequently passed T15b; existing-model sanity is recorded in T15c/d, with CPU admission held. ✅ 2026-09-09

- [x] T15b — Validate full-model GLM plain/native-MTP parity on the fresh core candidate at canonical 48 threads. All 31 trajectory pairs match exactly; plain has zero verification events, while MTP records 2,804 verification events, 5,419 accepted and 2,949 rejected draft tokens. Evidence: `/mnt/raid0/llm/tmp/glm53-validation-20260908/champion-core-pair-c463f601b-20260909T105800Z/comparison-audit.json`. Both owned servers exited with rc0 and are absent. The post-hoc audit preserves null plain counters and accepts them only with zero plain verification events; no serving data was rewritten. Existing-model functional sanity is recorded in T15c/d; CPU throughput still blocks official champion admission under T15. ✅ 2026-09-09

- [x] T15c — Complete the operator-narrowed single-stream sanity checks: Qwen3.8-Flash-Next (`qwen4exp`) CPU native-MTP, and the distinct Qwen3.8-27B (`qwen35`) GPU DFlash2 target. Flash-Next MTP matches all 24 historical text/count/finish/draft trajectories at 31.0587 tok/s; 27B DFlash2 passes the preliminary, differently configured smoke at 65.0559 tok/s (superseded for performance comparison by T15d), acceptance 0.6427, and 1.963× its same-build no-spec control. GPU residency and owned-process cleanup pass. Evidence: `/mnt/raid0/llm/tmp/qwen-glm-core-fold-20260909/candidate-c463-serving-20260909T115700Z/FAILFAST-RESULT.md` and `/mnt/raid0/llm/tmp/glm53-validation-20260908/champion-gpu-c463f601b/dflash-smoke-run.json`. CPU performance is unresolved: the new plain/MTP observations are lower than historical instrumented results, whose own report flags an unexplained high regime. These sanity passes do not certify unchanged CPU throughput. No additional repeats or standing campaign were run after the operator narrowed scope; official canonical admission remains T15 and has not occurred. ✅ 2026-09-09

- [x] T15d — Repeat the two candidate-only sanity tests through last night's original instruments, as requested. GPU27B DFlash2:79.5987 vs79.2453 tok/s, matched recipe/prompt/warmup, residency proven. CPUFlash-Next MTP:32.1526 vs43.2807 tok/s (-25.71%), all24 historical output/draft trajectories exact and original host screens CLEAN. The mismatched GPU65.06 smoke is superseded for performance comparison; CPU performance still prevents official admission under T15. Evidence and complete paths are in the dated progress entry's “Matched historical-harness retest” section. All owned inference exited; no additional repeats. ✅ 2026-09-09

- [x] T15e — Seed the completed GLM work into the live AutoKernel memory without changing the champion. Four `measured_null` records were inserted and independently retrieved under campaign `ak-external-glm53-core-20260909`; the normal loop reads inbox `24-glm53-core-c463-external.md`. The self-contained source/evidence bundle and receipt are `/mnt/raid0/llm/autokernel/loop-memory/external/glm53-core-c463-20260909/ingestion-receipt.json`. Idempotence passed: four initial inserts and zero duplicate inserts. These cross-epoch records cannot advance the champion. ✅ 2026-09-09

## Constraints

- Authorized experimental inference runs under held physical CPU-region claims; observations on the unrebooted host do not authorize production promotion.
- Do NOT add a `model_registry.yaml` role without operator approval.
- Any DSA correctness finding also updates `llama-cpp-dsa-contribution.md` (single owner of the
  generic gates).
