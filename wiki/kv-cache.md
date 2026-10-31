# KV Cache Optimization

**Category**: `kv_cache`
**Confidence**: verified
**Last compiled**: 2026-10-31 (operator wiki sweep, workspace-58): KPF-18.x fork-vs-fresh native records, FA4 exact-set R17 outcome, KPF-18.2/18.3 trace builds. Earlier: 2026-10-28 (KPF-62.3 selector port scoped, tiny-model controls; V11-FA-4b scorer diagnostic; KPF-64 EB contrast). Earlier: 2026-10-27 (operator full wrap-up, Codex NI, cutoff 14:56:35Z). Earlier: 2026-10-27 (operator wiki sweep, workspace-58): KVU-16b concurrent residency PASSes on C5, unified KV loses to split at np8 L64k on CPU, and the CME-7S prompt-prefix cache gate passes. Earlier: 2026-10-25 (wrap-up sweep 27, operator /wrap-up workspace-58): KVU-19b P3 B is within 5% on the champion, KVU-16f was already serving, KPF-64.3 F/FB run and EB is re-booked on 48 cores, and the ctx-checkpoints receipt lands. Earlier: 2026-10-24 (wrap-up sweep 26, operator /wrap-up evening): the KPF-18 R4 fork deviation is fork-path-specific, HPR-B INVALID (the simulator omits retained generation), KPF-64.3 EB is infeasible at quarter scale, and HSF-5.P G4 needs a log-capture amendment. Earlier: 2026-10-24 (wrap-up sweep 25, workspace-58 convergence delta): KPF-17.4c finds no reproducible restore defect, 13.1b is a near-tie artifact, KPF-18.0b closes, and the HSF-5.P build gate holds. Earlier: 2026-10-24 (wrap-up sweep 22, 3c4ca599 delta): the DFlash2 restore defect is target-side, the 60k fork deviation is fork-specific, chunk-KV G0 is bit-identical, and the host KV mirror trigger fires. Earlier: 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): the KPF-18 CPU re-runs and graphs-ON step 7 land. Earlier: 2026-10-24 (wrap-up sweep 20, 3c4ca599 delta). Earlier: 2026-10-24 (wrap-up sweep 9: KPF-13.1 rules v3 verdicts, KPF-64 hybrid checkpoint rule, v11 fold decisions). Earlier: 2026-10-23 (wrap-up sweep 19, workspace-f8: KPF-13.1 rules v3 and the DFlash2 arm; on the 27B the SWA cache is the drafter's; idle-slot restore semantics from code reading). Earlier: 2026-10-23 (wrap-up sweep 18, workspace-f8: always-F32 VKQ accumulation costs nothing on architect CPU decode). Earlier: 2026-10-23 (wrap-up sweep 17, workspace-f8: coarse checkpoints REPLACE_DENSE at 32k on a wide spread; KPF-26 outcome clause keeps). Earlier: 2026-10-22 (wrap-up sweep 14, 3c4ca599: upstream #28576 is carried by the pull; the GPU VKQ half-staging question is open (V11-FA-8)). Earlier: 2026-10-22 (wrap-up sweep 10: KVU-12.1 DENSE_STAYS, fork flip is numerics, CME-7 cache miss). Earlier: 2026-10-22 (wrap-up sweep 9: KPF-64 is slow because of decode contention). Earlier: 2026-10-22 (wrap-up sweep 8; wrap-up sweep 7: fork cleared, G1 reference, KVU-12.4). Earlier: 2026-10-21 (wrap-up sweep 6, workspace-f8 delta). Earlier: 2026-10-21 (wrap-up sweep 5: KPF-62 slices filed). Earlier: 2026-10-21 (wrap-up sweep 3 delta). Earlier: 2026-10-20 (wrap-up sweep 2: unified-KV and prefix-fork DeepInfer probes). Earlier: 2026-10-20 (hybrid prefix-cache survey, index entries 2061 through 2115, plus the prefix-fork recut; prior: 2026-10-06 incremental root-wrap synthesis; prior compilation history: 2026-10-03 (wrap-up compile: the 27B's hybrid KV math — 16 of 64 layers hold growing KV, 34,816 B/token q8_0, 42 KiB/token measured marginal; step 1 of the :8083 pool fix is live (token gate, one long prefill per server); step 2 (`-c 393216` unified, per-slot clamp to n_ctx_train 262144) is signed, not yet live); previous: 2026-09-24 (late, main-ak-seat: KVU-11b decided D, no change to the CPU speech layout); earlier: 2026-09-24 (wrap-up #4, main-ak-seat: production is now unified — OP-54 applied np 4 at 196k; the throughput verdict confirmed); earlier: 2026-09-24 (production was never unified: llama-server v10 auto-enables unified KV only when `-np` is absent, the launcher always passes `-np`, so :8083 capped every request at 98,304 tokens; the 27B GPU study (n = 1/cell) finds unified per-request decode equal within 1.1% at np 1 and +0.3..+5.7% at np 2/4, a 124,174-token prompt accepted unified vs HTTP 400 split, two pool-full shapes (unified: one request fails with the MTP sub-batch exception 4/4; split: silent truncation), idle-slot clear under unified against an 8192 MiB RAM tier too small for one full-pool prompt (inferred), and unified-vs-split output divergence at np 2/4 — see the top section); earlier 2026-09-08 note: (the KV-reduction cluster's 09-07 wave — selection-class KV methods hold the FULL cache and buy zero KV memory (1.04 MB vs 8.38 MB on-device at 2K/16K), the streaming-LLM 4-axis sweep gained power and eviction-regime constraints but still has no cells, PS-2 closed as Reset-PE-insignificant, and SWA-window-floor/query-aware-selection coverage pointers filed; earlier 2026-08-23 note: **wave-2 research intake — the KIVI "primary quality gap" recorded for months at `kv-cache-quantization.md:320` never existed**: per-token V is structurally guaranteed once V is quantized (quantized V forces flash attention, which sets `v_trans=false`, making V channel-contiguous), the per-channel-K half is a **2-bit-only** prescription by KIVI's own OB 1, and key outliers are handled instead by the in-tree Hadamard rotation — the only residual is symmetric-vs-asymmetric, which is a flag (`q4_1`/`q5_1`), not a code change; **the granularity reading rule**: with `-fa 1` we quantize K and V per token in 32-element blocks along CHANNELS, finer than the Group-64 *mitigation* published in the alignment-collapse study and on the OPPOSITE axis from KIVI, so third-party KV-quant damage numbers are a pessimistic bound for us and must never be transferred unqualified; **VeriCache's algorithmic core is already expressible in frozen v9 with no code change** (`-ctkd`/`-ctvd` set the draft context's KV type independently of the target's and a model can be its own drafter) while its systems contribution depends on an interconnect we do not have; the dual-cache post-mortem is reframed as **a capacity argument applied to a bandwidth problem**; the PCIe "KV streaming is an anti-pattern" line is scoped to *per token*; R9's spec-decode verdict stands on NIAH+PPL while its throughput warrant is void; and llama.cpp slot-restore reuse loss is **conditional, not blanket** — zero only for a DIVERGENT or EXACT-REPEAT prompt, full for a strict continuation, with upstream PR #25592 (live in-memory checkpoint path) outranking #26004 (dormant disk path) for us — see the end of the page; earlier 2026-08-23 note: evening wave-2 compile: the KIVI "no gap" correction + the REAL instrument gap, the dual-cache reframing (capacity vs bandwidth), the group-32/axis granularity correction, and the KV-quant monitoring gates G2-G5 with the massive-activations deprioritisation — see bottom sections; earlier same-day: the orchestrator prefix-cache path now has an owner and a measurement plan: KV-5 closed in the wiki, the three latent defect fixes KV-0a/b/c landed 2026-08-20 — every KV slot save was failing, roles sharing one server silently clobbered each other's slots, and `radix_cache.py` was dead code — and the KV-1/KV-2/KV-3/KV-4/KV-6 rows filed — see the end of the page; earlier 2026-08-22 note: closure fine-structure of the COMPLETED KV-quant handoff — **V-dequant, not K, is the entire CPU flash-attention prefill cost** (q4_0/f16 −1% vs q8_0/q4_0 +71%; q8_0/q8_0 is the worst prefill config measured at 3.3× slower, reconciling the 2026-08-03 memory-optimal reading as a different axis); Hadamard's isolated contribution priced at 70% gap closure (+0.055 → +0.017); TQ3 abandoned on a *fair* 32B retest after its first gate was flagged as failure-zone-unfair; QJL's SNR≈1.13 arithmetic death; spec-decode +3.3% with q8_0/q4_0; the 4-KV-head q4_0-K hazard; and PR #21089 (TurboQuant CPU KV) verified CLOSED UNMERGED upstream 2026-06-02, retiring the 2026-07-20 monitor row — see the end of the page; earlier 2026-08-12 note: a fork SWA slot-reuse patch previously held for review is **DROPped as a correctness regression, not merely redundant** — it deleted upstream's per-sequence check; KV quantization gets its first decision package with an exact parity result; and lazy KV faulting is re-read as *relocating* provisioning cost rather than removing it; earlier 2026-07-20 note: adds the StreamingLLM floor/admission verdict, the TurboQuant/ChunkKV KV-quant monitor status, and the MI210 KV-split residency facts; earlier 2026-07-17 pass retained))
**Sources**: (+ sweep 2 sources, see its Source References) 51 documents (added 2026-10-03 wrap-up compile: kv-unified-stack-rollout KVU-15/15a/16/17, agentic-serving-harness-fixes UFH14-B2/B3, the prefill-share review, 2026-10-03 workspace-ec progress) (added 2026-09-24 wrap-up #4: see the top section\'s Source References) (44 prior: 3 deep-dives, 8 active handoffs, 2 completed handoffs, 25 intake entries, 3 progress logs, 2 upstream issue threads; +7 added 2026-09-24: the `kv-unified-stack-rollout` handoff, the `2026-09-24-main-ak-seat` progress log, the `-kvu` stack-change package, the stack-wide `-kvu` inventory, the serving-engine technique audit, the research `np_context_kvu_study_20260924` README, and `OPERATING_CONSTRAINTS.md`)

## Compiled Update — 2026-10-25 (wrap-up sweep 27, operator /wrap-up workspace-58): `-kvu` batched decode is within 5% on the champion, `-b 512` on :8083 was already signed and serving, KPF-64.3 is redesigned, and RATIFY-CTXCKPT lands in root

**Confidence: verified** (predeclared verdicts, signed receipts, the live launch record); the P3 B timing is **indicative**.

- **KVU-19b-fold-c1-p3: WITHIN_5PCT.**
  - Setup: 27B Q8_0, `llama-batched-bench` npl 4 / npp 16384 / ntg 64, champion store `dcc853b55-c3`, graphs ON, a fresh process per arm, ABAB.
  - Mean S_TG: `-kvu` 55.93 vs `-no-kvu` 56.47 t/s, so **−0.94%** (pairs +0.39 / −2.27%). The v1 P3 on production v10 measured −15.23%.
  - The `GGML_CUDA_FA_SEQ_ROWS=0` control is −15.9%, so the per-row skip is what closes the gap.
  - This unblocks the kvu part of the v11 stack-change signature.
- **KVU-16f was done, only unticked.**
  - The 10-04 A/B measured `-b 512` at 3.5–4.2× decode while a neighbour prefills, KFD −3.1 GiB, and solo shallow TTFT +35%.
  - STACKCHG-8083BATCH is signed, and :8083 has served `-b 512 -ub 512 --no-cache-idle-slots` since 10-07.
  - The 10-21 triage looked in git rather than at the live launch record. Lesson: check the serving argv before re-running an A/B.
  - Residue: the registry KQ-mask term (KVU-16f-1).
- **KPF-64.3 redesign adopted.**
  - Amendment 4: F/FB run now on q0, and F-FB is evaluated on its own.
  - Amendment 5: EB, the no-cache arm that re-prefills 32k per turn, moves to 48 cores (q2+q3). Its corrected cost is ~18.5 h (17.5–23.8 h), against the ~26 h the 24-core partial projected; the first 90 requests were the short ones. It is booked from 10-26 03:30Z.
  - A 48-core EB stays comparable on the predeclared metric, prefix-hit share from server token counts paired by session. Thread count enters it only through interleaving, and all 90 partial EB requests had `cache_n = 0`. Wall time is not compared.
- **RATIFY-CTXCKPT-HYBRID-20261024 root receipt `b5934d982`.** `--ctx-checkpoints 32` is now declared on every hybrid serving role in all three repos. No reload is needed, because 32 is the default.

Sources: [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) (KVU-16f, KVU-16f-1, KVU-19b-fold-c1-p3) · [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) (KPF-64.3, KPF-64.4) · [calendar plan 2026-10-25](../docs/reference/calendar-plan-2026-10-25.md) · [2026-10-25 workspace-58 progress](../progress/2026-10/2026-10-25-workspace-58.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 26, operator /wrap-up evening): KPF-18 R4 reads FORK_PATH_SPECIFIC, the HPR-B holdout is INVALID_SIM_DISAGREES, KPF-64.3 EB is infeasible at quarter scale, and HSF-5.P G4 was a log filter

**Confidence: verified** (predeclared run verdicts); the HPR-B and G4 mechanisms are **inferred** (accepted static audits, no replay).

- **KPF-18-S1.R4: `FORK_PATH_SPECIFIC`.** The R3 confound (no cold arm at the child's own occupancy) is removed. Teacher-forced mean |dlogprob| over 256 positions: child vs child2 = 0.0 (256/256 exact, so the fork path is deterministic); child vs coldE (child's occupancy matched) 0.0322, vs coldA 0.0293, vs coldB 0.0299; cold-vs-cold 0.0275 (A|B), 0.0259 (A|E), 0.0315 (B|E). The predeclared rule (child-vs-coldE above every cold-vs-cold d) fires on a thin margin (0.0322 vs 0.0315), so the occupancy-only reading of item 3 is rejected. The run was valid (own-pid VRAM 49715 MiB, graphs ON, drained); item 3 stays open and a `do_slot_fork` plus shared-cell FA code read (KPF18-R4-FORK-CODEREAD-1) was delegated to Codex, which must reconcile with KPF-17.4c (layout explains 17.4b).
- **HPR-B 64k holdout: `INVALID_SIM_DISAGREES`.** One cell (q36_35b dense ckpt 64k wave-0 `extend_1`) has simulator prompt_n 2818 vs log 2799 and cache_n 65314 vs 65333: the server reused 19 more tokens. The predeclared outcome is no decision, never re-graded; the box stays open. The accepted diagnosis (HPR-B-SIM-DISAGREE-1): the simulator keeps generated-output counts but not generated token IDs in its simulated slot prefix; 19 = 4 tokens past the selected checkpoint in the old prompt plus 15 retained generated tokens. The 8k wave-0 and 64k wave-1 cells agree, so a count-only extension would over-correct. Proposed fix: persist prompt and generated token IDs, carry the server's actual sequence across simulated requests, and take the LCP against it (retained boundary `n_total + generated - 1`); the regression needs token-ID fixtures from a new predeclared run, since current artifacts cannot supply the 15 IDs.
- **KPF-64.3 EB/F/FB: infeasible at quarter scale.** s5-kpf64-ef was stopped at 16:17Z with arm E done and kept; arm EB (cache-ram 0, atomic, 32k re-prefill per turn) had done 90 of about 388 requests in 6h13m on one 24-core quarter (about 26 h projected against a 22:00Z hard end, and a stop would wipe an atomic arm). F/FB never started. Redesign needs a whole-host window or a reduced session set; KPF-64.3 stays unticked.
- **HSF-5.P microbench: INCONCLUSIVE only on G4, a logging artifact.** G1 decode, G2 graphs-reused and G3 restore PASS; the save (tail_copies=874, replay_steps=6) and restore (device_bytes=298907648) lines are present, but the INFO enable line `HSF-5.P kv host mirror ON` is absent from `server.B.log`: the server ran at verbosity 3 and `common/log.cpp` maps that `LLAMA_LOG_INFO` to verbosity 4. AMENDMENT-G4-log-capture (instrument-only) adds `--log-verbosity 4` to every arm and requires G1 to be evaluated with all arms at verbosity 4, preserving symmetry; extra logging cannot be proven zero-overhead, so the rerun is a separate measurement. The 15:44Z INCONCLUSIVE stands; the GPU rerun is booked after v11-086-cpu.

Sources: [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) (KPF-18-S1.R4, HPR-B, KPF-64.3) · [heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md) (HSF-5.P) · [backlog-audits checkpoint](../docs/reference/backlog-audits-2026-10-24-checkpoint.md) (HPR-B-SIM-DISAGREE-1, HSF-5P-G4-LOG-1) · [2026-10-24 workspace-58 progress](../progress/2026-10/2026-10-24-workspace-58.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 25, workspace-58 convergence delta): KPF-17.4c finds no reproducible restore defect, 13.1b is a near-tie artifact, KPF-18.0b closes, and the HSF-5.P build gate holds

**Confidence: verified** (run verdicts and predeclared rules in the cited sources); the fork-fix reading is **inferred** until KPF-17.4d.

- **KPF-17.4c: `none_reproduced`, `control_layout_numerics` 4/4.** The layout-matched bisect does not reproduce the c1 divergence, so KV cell layout explains KPF-17.4b's apparent `target_restore_defect`. The CPU legs of KPF-17.4 and KPF-19.1a PASS (honest 6/6, flag_on 3/3, `mut_no_transfer` detected 3/3), but both boxes stay open on the GPU FAIL and the CH-18 build.
- **KPF-13.1 reconciliation: the 13.1b failures are near-ties.** All 10 failing runs sit inside the 0.031567 band, repeat exactly, and the controls are token-identical. The rules-v4 spec-off judge has no near-tie clause; that is a rule finding and the recorded verdict stands. The fork-fix-build premise is withdrawn: no fix is built until the new KPF-17.4d (a predeclared near-tie- and layout-aware re-judge) decides.
- **KPF-18.0b closed (`G3_EXACT`).** Group 3 (T = 16384) is bit-identical 4/4 with tokens 4/4; combined groups 0-3 are bit-identical 15/16, tokens 16/16 (grade OBSERVATION). The one g1 / suffix 2 miss has equal tokens and differing top-k probs and goes to KPF-18.0e as CPU input.
- **KPF-18.0d item 3 group 3 v3: `TARGET_SIDE`.** The token-1 flip (2.13 nats, 3/3) survives graphs OFF and the child's drafter request-off, so it is not HIP-graph reuse or the first verify batch. Item 3 stays not closed; a layout-matched control at T = 32000 is filed, with the caveat that 17.4c's drift is 1e-4-scale and may not explain a 2.13-nat flip.
- **HSF-5.P build gate verified from logs and binaries, with a negative control.** B0 (`test-kv-host-mirror`) passes CPU-only; B1 finds the three gate strings in the built libs, while the C3 control image has none of them and does have the control string, so the gate can fail. Linkage verified. The microbench with its G1-G4 gates has not run, so the box stays open.

Sources: [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) (KPF-17.4c, 13.1 reconciliation, 18.0b, 18.0d) · [heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md) (HSF-5.P) · [2026-10-24 workspace-58 progress](../progress/2026-10/2026-10-24-workspace-58.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 22, 3c4ca599 delta): the DFlash2 restore defect is target-side, the 60k fork deviation is fork-specific, chunk-KV G0 is bit-identical, and the host KV mirror trigger fires

**Confidence: verified** (run records and predeclared rules in the cited sources).

- **KPF-13.1b is decision grade: `target_restore_defect`.** The drafter-on resume ended rc 0 at 08:07Z; rules v4 give `kpf13_1b_locus = target_restore_defect`, with failing spec-off arms g0-S2:B, g1-S2:B, g2-S2:B, g3-S1:B, g3-S2:A (spec-off A 5/6, B 2/6 PASS, no drafter loaded). The drafter-on acceptance drop is therefore confounded by the target-side defect and does not fire the upstream #30141 trigger. [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md)
- **KPF-17.4b's `target_restore_defect` reading is confounded by KV cell layout.** Its control C was seeded while the 14336-cell source was resident, so C's cells sit at index 14336+ while the fork X attends cells 0..c-1 written on an empty cache; X differs from C from token 0 (1e-4 to 3e-4) while C1 == C2 == C3 bit for bit. `kpf17-4c-bisect` (rules v1, prepared not run) adds layout-matched arms (Xc~Cmask, Xe~C0, Ks~C0), each judged by exact bit identity; it refuses until KPF-13.1b is decision grade (met 08:06Z).
- **KPF-18-S1.R3: item 3 stays `NOT_SATISFIED` at 60k, fork-specific.** Worst child-vs-cold 0.029879 against a six-pair floor of 0.027456 (ratio 1.088); the six cold pairs held only two distinct values (the cold spread depends on resident-sequence count, not the slot); child-vs-prompt-cache-hit 0.030706 is outside the floor. The follow-up is **KPF-18-S1.R4** (localise the deviation). Item 2 cell g3.s2 reads `G3S2_WITHIN_PLACEMENT_FLOOR` (three Q repeats; the one-sample prefix floor of 24 was unrepresentative), so item 2 is placement numerics at all 6 judged cells. The item-3 group-3 v2 test read `FORK_EFFECT`; a v3 launcher (graphs ON / graphs OFF / child `speculative.n_max 0`, 3 loads each) is prepared.
- **KPF-62 chunk-KV reuse: code landed, G0 bit-identical.** `experimental/kpf62-456-20261024` adds `llama_chunk_kv_decode_at` (sparse recompute that fills a position hole; attention-only, refuses otherwise), a shared `server-chunk-recompute.h`, server `--chunk-store-mib` / `--chunk-max-tokens` and a `kv_chunks` request field (off = champion path), and the G3 harness (`test-chunk-kv-g3`, `g3_gate.py`). ctx_dft, MTP, DFlash and quantized-K are startup refusals in v1. The branch was re-pinned to `786a30078` after a stale-build check grepped the thin `llama-server` launcher instead of `libllama-common`; the build passed and the on-role G0 gate then PASSED bit-identical (G0a / G0a-al / G0a-inj). G3 rows wait on a frozen corpus manifest (KPF-60, P0 thresholds section 8 TBD). Manifest row V11-105. [progress](../progress/2026-10/2026-10-24-3c4ca599.md)
- **KVU-12.3 closes NOT-NEEDED on quiet traffic only.** Only 5 resumed turns fell at >= 3 busy slots, so the predeclared fallback pooled all concurrencies (1,235 resumed turns; 4.52% against the 5% bar). KVU-12.3b re-checks on the busy subset once >= 100 such turns exist on :8083 (stack down since 10-23). [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md)
- **Host-pinned KV mirror (HSF-5): the DI-140 trigger FIRES.** Worst-case KV-tail write-through costs 0.44% of a spec-ON step and 1.01% of a spec-OFF step (128 serialized copies), 0.014% as one staged copy; the 149.6 MiB recurrent state fits the 3% budget only as a checkpoint every 6 (ON) / 13 (OFF) steps. It removes 130 / 218 / 395 ms (tmpfs), 250 / 417 / 753 ms (disk) or 105 / 155 / 184 ms (`--cache-ram`) per handover at 8k / 16k / 32k, using graphs-ON rates (HSF-4.G: the KPF-18-S1.7g rule found 4 of 21 cells graphs-sensitive, so HSF-4/5 re-quote only the graphs-ON run). A copy inside the captured HIP graph breaks reuse; graph-safe is a side-stream copy after the step event. Handover frequency is unknown (HSF-3.1), so value is bounded at 0.1-0.75 s per handover. Prototype HSF-5.P (`experimental/hsf-5p-host-kv-mirror-20261024` @ `14d0f7fa2`, `--kv-host-mirror`, default off) is code-complete but not compiled. Per intake-2126#record and intake-2140#record. [hsf-5](../docs/design/hsf-5-host-kv-mirror-costing-20261024.md), [hsf-4](../docs/design/hsf-4-results-20261023.md), [HSF residency](../handoffs/active/heterogeneous-slot-fabric-residency.md)

Sources: [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md), [heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md), [hsf-5 costing](../docs/design/hsf-5-host-kv-mirror-costing-20261024.md), [hsf-4 results](../docs/design/hsf-4-results-20261023.md), [llama-v11-manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md), [progress 3c4ca599](../progress/2026-10/2026-10-24-3c4ca599.md), [progress workspace-f8](../progress/2026-10/2026-10-24-workspace-f8.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): the KPF-18 CPU re-runs and graphs-ON step 7 land, KVU-12.3 closes NOT NEEDED, and hybrids get a declared checkpoint count

**Confidence: verified** (run records and predeclared rules in the cited handoffs); the CPU re-runs are OBSERVATION grade at 8 pairs and 128 tokens, below the gate's 32 pairs and 256 tokens.

- **KPF-18.0b CPU re-runs (items 1, 2, 5; fixed runner `d4633648…`, 2026-10-20).** Item 5 holds on both cache-idle settings: pool used equals private plus shared 22/22, `pool_used_eq_expected` 14/14 (it was 12/14 on the buggy runner), continuation bit-identical 2/2. Item 1 (MTP on): the fork was taken at n_fork == T in 8 of 8 and top-1, max-abs and greedy prefix match the fresh-vs-fresh control, but KLD max is 0.1045 against 0.0840; that figure is exactly the reverse-direction KL of the control's own pair, and the fork is bit-identical to fresh-B in 8 of 8. The MTP-off arm is a cache restore (`n_fork_tokens` 0), not a trunk fork. Item 2 is bit-identical in 11 of 12 pairs (tokens 12/12) on a partial record; the miss is group 1 / suffix 2 (equal token ids, different top-k probs, 213 vs 210 MTP drafts). "Item 2, rest" is filed as one CPU-quarter inference job.
- **KPF-18.0b.2 answers NO.** `fork_off` polls carry no `kv_cells_*` key in 0 of 73 polls (fork_on 43/43), by construction: the fork tree gates the cell scan and every `llamacpp:kv_cells_*` gauge on the fork being enabled.
- **KPF-18.0d item 3 v2 (same-shape control, GPU 27B): verdict `FORK_EFFECT`, 3/3 valid loads.** The child is a fork-effect candidate 3/3 (first divergence at token 1, nofork top-2 margin 2.13 nats), source arms identical 3/3. This does not settle R3 (18.3 part 4): coldC/coldD, the prompt-cache `sameshape` arm and the item-2 g3 repeats are unrun.
- **KPF-18-S1.7g: step 7 with graphs ON is `graphs-sensitive` in 4 of 21 (L, mode) cells** (cache_baseline at 8000 and 16000; disk_restore_cold and cache_load at 32000). HSF-4/5 must quote the graphs-ON rates (HSF-4.G filed). The difference is attributed jointly to graphs ON, the HSA knob and the fresh-load / step-7-only history, never to HIP graphs alone.
- **KVU-12.3a closes KVU-12.3 NOT NEEDED.** Rule predeclared before reading: re-prefill caused by divergence inside the previously generated span must reach 5 % of processed prompt tokens at >= 3 busy slots (fallback to all concurrencies when fewer than 10 such turns). On the :8083 log, 1083 of 1235 resumed turns extend exactly (87.7 %), 152 diverge in the generated span; with only 5 turns at >= 3 busy the fallback applies and R = 4.52 % < 5 %. Caveat: the cost sits at 1 busy slot (4.9-6.9 %), where A7 step 1 (render-side root cause) is the cheaper lever. KVU-21's trigger also closes on a refresh: median recompute 0.015 (1 busy), 0.014 (2), 0.065 (>= 3, n = 43).
- **Hybrid checkpoint count is now declared in the registry.** RATIFY-CTXCKPT-HYBRID-20261024 puts `ctx_checkpoints: 32` on frontdoor, architect_critic and architect_general; the compiler emits and attests `--ctx-checkpoints 32` for the five hybrid targets, every other argv byte-identical (32 is the default, so no reload).
- **KVU-16g-2 package component drafted, not deployed:** the decode-aware prefill budget flags for :8083 (see [hardware-optimization](hardware-optimization.md)). A KVU-12.1b 64k holdout (dense vs coarse, ~7.3 h, one CPU quarter) is prepared, not run.

Sources: [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md), [qwen38-27b-replace-qwen36](../handoffs/active/qwen38-27b-replace-qwen36.md), [workspace-f8 progress 2026-10-24](../progress/2026-10/2026-10-24-workspace-f8.md), [prefill-budget package](../docs/design/prefill-budget-8083-stack-change-package.md).
## Compiled Update — 2026-10-24 (wrap-up sweep 21, workspace-f8 delta): the slot-fabric source rates must come from the graphs-ON run

- **KPF-18-S1.7g came out `graphs-sensitive`** (4 of 21 length-by-mode cells), so the HSF-4/5 source-rate sub-term must be re-quoted from the graphs-ON step-7 run, all numbers from that run. The difference is attributable to graphs ON, the knob and the fresh-load history jointly, not to HIP graphs alone.
- **Graphs-disabled restore rates stay labelled as such.** tmpfs restore 8.26 / 9.27 / 6.15 GB/s and cold-disk restore 4.12 / 4.10 / 3.06 GB/s at 8k / 16k / 32k, and the earlier judgement that copies sit inside the 3-rep spread is retired (box HSF-4.G).
- **Not yet judgeable:** the session-keyed dispatch probe still has 0 records with a session key (108 ever), so the fabric dispatch claim waits on live traffic from the restarted API.

Sources: [Heterogeneous slot fabric residency](../handoffs/active/heterogeneous-slot-fabric-residency.md), [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 20, 3c4ca599): KPF-64 ran 8/8 arms (checkpoints are load-bearing on hybrids; the RAM tier added nothing at np=4), and INF-42 G1 shows no recall drop to 128K

**Confidence: verified** (run records in the cited handoffs).

- **KPF-64 result.** Frontdoor Qwen3.6-35B-A3B-MTP Q8_0 (hybrid qwen35moe), CPU, np=4, v10 store binary, 19 paired sessions / 388 requests, ideal prefix-hit bound 93.88-93.89% on every arm. Arm A (`--ctx-checkpoints 0 --cache-ram 0`) realised 90.17% / 89.28% (gap 3.71 / 4.61 pp, about 3.6-3.9k uncached tok/req); B, C, D (32 checkpoints, cache-ram 0 / 2048 / 32768) all realised 93.54% (gap 0.35 pp, about 2347 uncached tok/req), replicated across both passes. Predeclared verdict: checkpointing is the whole effect, and the `--cache-ram` tier adds nothing measurable at np=4. ([kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), KPF-64)
- **Follow-ups (KPF-64.2/.4/.5).** Pairwise contrasts among B/C/D are null; the pooled checkpoint effect is about -3.9 pp. The 0.35 pp residual is an ideal-estimate artifact. Policy: `--ctx-checkpoints 0` must never be set on a hybrid role; no frontdoor change (it already runs 32 checkpoints + cache-ram 32768). Whether the RAM tier matters above 4 lineages is untested (KPF-64.3, E/F arms, armed). Fan-out was not exercised (child share 0%). ([progress 2026-10-24](../progress/2026-10/2026-10-24-3c4ca599.md))
- **INF-42 G1 closed.** q8_0 KV on the frontdoor: 100% needle recall (50/50) at 4K, 32K, 64K and 128K at every depth, 9/9 at 256K; f16 control 100% at 4K and 128K, so q8_0 KV costs nothing on this probe. It is a ceiling result: it rules out collapse-scale amnesia but cannot rank configs or bound subtler loss. ([multiscreen-attention-evaluation](../handoffs/active/multiscreen-attention-evaluation.md), G1)

## Compiled Update — 2026-10-23 (wrap-up sweep 19, workspace-f8): acceptance intervals from in-run spread, the 27B's SWA cache is the drafter's, and what an idle-cleared slot restores

**Confidence: verified** for the rules, re-judge counts and the oracle history (handoff records, the queue job 24 record). The idle-slot findings are **inferred** (code reading at `49550eda5`, no run yet).

- **KPF-13.1 rules v3: take the acceptance interval from the control's own spread.** Rules v2 took the interval from a single same-shape control, which gives zero width (for example draft_n in [83,83]). All 7 v2 failures were acceptance-only and off by 1-4 draft tokens. Rules v3 run K=3 same-shape controls per arm and accept within (min - spread, max + spread), with the rules hash recorded.
  - Re-judged offline, the v2 cells pass A 12/12 and B 12/12. They are still not decision-grade, because v2 had only 2 controls per arm.
  - Two runs are armed: a DFlash2 arm on the 27B GPU fork image, and a plain-MTP CPU arm that adds the `skip` launch needed to decide KPF-13.1a ([kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md)).
- **KPF-17.4: the "SWA range fix" blocker was stale, and the real gap was elsewhere.** The 2026-10-20 failures were oracle defects, fixed by `f3a3bb4b1` and verified by queue job 24.
  - On Qwen3.8-27B + DFlash2, the target is hybrid with n_swa 0. The SWA cache is the **drafter's** (`sliding_window` 2048 on all 5 layers, 8704 cells), so neither existing test could see it.
  - A new driver (`kpf174_swa_drafter.py`) forks at junctions 2148, 4096 and 10240 on a 14336-token source, so the drafter window has been overwritten. It judges the drafter behaviourally in four launches: honest, `mut_partial_noop`, `flag_on` and `mut_no_transfer`. Both mutants must be DETECTED.
- **KPF-18-S1 remainder: re-predeclare when the rule's basis abstains.** 18.3 part 4 abstained because the three runs disagreed at token 1, leaving a common greedy prefix of 0. It is re-predeclared as a teacher-forced d() over the S1 cold-A sequence.
  - Item 2 is re-judged against a placement-varied control (the source restored onto another slot through the prompt-cache path), not the zero A/A floor. That floor measures run-to-run determinism, not placement.
- **What an idle-cleared slot restores (code reading at `49550eda5`; check before quoting).**
  1. An explicit `id_slot` on a slot that cache-idle-slots cleared skips the RAM restore: `f_keep` = 0/0 = NaN, so the `< 0.5` test is false, `prompt_load` never runs, and the turn re-prefills from zero. Only `id_slot=-1` LRU selection restores.
  2. "Explicit id_slot reuse overwrites the victim without saving it" is wrong at the default `slot_prompt_similarity 0.1`: the victim is saved first. It holds only with `--slot-prompt-similarity 0`.
  3. With the pool full and idle contexts resident (OFF arm), `try_clear_idle_slots` purges idle slots with no RAM save, so the dropped conversation's next turn is a cold prefill.

  UFH14-LB7 is armed to attribute the 43.5 s pre-prefill stall from `-lv 4` TRACE lines. Its predeclared verdicts are OWNER, SHARED, UNATTRIBUTED, NOT_REPRODUCED and INSTRUMENT_FAIL ([agentic-serving-harness-fixes](../handoffs/active/agentic-serving-harness-fixes.md), UFH14-B4j.1).

- **KPF-LB1.1: the orchestrator's rebuilt-prompt /completion path keeps most of its prefix cache, so no `message_delimiters` flag.** A 12-turn REPL transcript was self-captured on a private 27B server (`coder_escalation`, orch `f3ab78b2`) and replayed on both lanes on a restarted server. /completion turns 2+ had a median hit of **0.818** (token-weighted 0.814), against **0.951** (0.953) for chat with `message_delimiters`; 0 of 11 turns fell below 10% on either lane. The predeclared trigger (/completion re-prefilling below 10% while chat does not) did not fire, so the verdict is NO_CHANGE. The roughly 13-point gap is recorded, not acted on. One transcript and one role, graphs disabled (GPU-LEAK-1 mitigation) ([kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) KPF-LB1.1).

### Source References (2026-10-23 wrap-up sweep 19, workspace-f8)

- [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) (KPF-13.1 rules v3, KPF-13.1a, KPF-17.4, KPF-18-S1 remainder, KPF-LB1.1 verdict)
- [agentic-serving-harness-fixes](../handoffs/active/agentic-serving-harness-fixes.md) (UFH14-LB7, B4j findings, UFH14-B4j.1)
- [speculative-decoding-mtp-refresh](../handoffs/active/speculative-decoding-mtp-refresh.md) (SPEC-GRAM.1 part 2 armed on the MTP lane)
- [workspace-f8 progress, 2026-10-23 afternoon](../progress/2026-10/2026-10-23-workspace-f8.md)

---
## Compiled Update — 2026-10-23 (wrap-up sweep 18, workspace-f8): always-F32 FA accumulation costs nothing on the architect's CPU decode

**Confidence: verified** (predeclared rule plus Amendment 2, 3/3 valid ABBAAB pairs, every row checked not hardened).

- **KVU-LB1.b run 2: NO_COST.** On the champion store image `49550eda5` (build 10411), Q38FN architect recipe, 96 threads, the median decode effect of F32 vs F16 VKQ accumulation was N1@8k +1.38%, N5@8k +0.86%, N1@32k +1.05%, N5@32k +14.1% (one noisy pair); no cell reached the -1% cost threshold.
- **Why prefill is not at stake.** `GGML_FA_VKQ_*` only acts in the per-row chunk kernel that serves N<64 query rows (decode, short verify, split-KV). The tiled path used by every 512-token ubatch always accumulates in FP32. The report-only prefill probe agreed (+1.8% / -0.1%).
- **Consequence.** Always-F32 removes the FP16 V-accumulator overflow risk (KVU-LB1.a) at no measured decode cost. KVU-LB1.d adopts it: choose the carrier (recipe env per CPU role, or a compiled default through the fold ledger), and check the frontdoor and worker CPU shapes with the same guarded harness before flipping a global default ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md)).
- Run 1 of the same A/B was discarded: its F32 arm ran the hardened llama-bench protocol unasked (see benchmark-methodology).

### Source References (2026-10-23 wrap-up sweep 18, workspace-f8)

- [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) (KVU-LB1.b run 1 and run 2, KVU-LB1.d)
- [autokernel-rebuild-program](../handoffs/active/autokernel-rebuild-program.md) (the llama-bench defect behind run 1)
- [workspace-f8 progress, 2026-10-23 midday](../progress/2026-10/2026-10-23-workspace-f8.md)


## Compiled Update — 2026-10-23 (wrap-up sweep 17, workspace-f8): coarse checkpoints replace dense at 32k (on a wide spread), and the KPF-26 outcome clause keeps

**Confidence: verified** for the verdicts (VERDICT.json / summary files named in the handoffs). **Observation grade** for what the verdicts imply about production: each one rests on a single predeclared run.

- **KVU-12.1b: coarse REPLACES_DENSE at 32k, against the predicted DENSE_STAYS.** Coarse checkpointing (`--checkpoint-min-step 16384`) keeps 534.05 vs 735.05 MiB per sequence (-27.34%). Its prompt_n stays within the dense wave spread on all four probes. This supersedes, for the coarse grid only, sweep 10's "KVU-12.1 reads DENSE_STAYS" below ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md)).
  - **Do not oversell it.** On edit_back_8192 coarse re-prefills +5,908 tokens more than dense (~52% more). It passes only because the dense wave-to-wave spread on that probe is itself 6,644 tokens, and the rule is spread-relative. More waves could flip it. Coarse also gains 3,970 tokens on edit_back_16384.
  - **Scope.** The verdict covers the 32k holdout only. At 8k coarse ties dense, because the conversation is shorter than the 16k step. 64k and 128k are unmeasured.
  - **Next.** HYBRID-PREFIX-REUSE (b) is re-opened: a 64k holdout of dense vs coarse with more waves, so the dense spread is measured rather than assumed. Production keeps `--ctx-checkpoints 32 --checkpoint-min-step 8192` until then.
- **KPF-26.1d/e (another session's runs): both v2 windows are WITHIN_SPREAD, so the outcome clause reads KEEP_ON_ELIGIBLE.** Each window ran 144 cases with all gates passing. Window 1: pass A 0.951 / B 0.979, drop -0.028. Window 2: A 0.951 / B 0.958, drop -0.007. Enabling still waits on KPF-26.1g (the terse-share check) and the KPF-26 timing clause ([kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md)).

### Source References (2026-10-23 wrap-up sweep 17)

- [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) (KVU-12.1b, HYBRID-PREFIX-REUSE (b))
- [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) (KPF-26.1d, KPF-26.1e)
- [workspace-f8 progress, 2026-10-23 morning](../progress/2026-10/2026-10-23-workspace-f8.md)


## Compiled Update — 2026-10-22 (wrap-up sweep 14, 3c4ca599): upstream #28576 is carried by the pull; the GPU VKQ half-staging question is open (V11-FA-8)

- V11-FA-7 decided: upstream #28576 (fp32 VKQ accumulation on MFMA, V11-050) is carried by the v11 pull because `bfdc32183` is an ancestor of upstream master `11fe02151`; presence gate G-ANC. It is perf-only on MMA-routed MFMA shapes and overflow-neutral: opnan arms with and without it fail the same 6/228 cases, and it does not touch the ROCWMMA-ON champion route ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md)).
- CPU-FA-VKQ-4 closed with a corrected premise: upstream has not fixed the GPU analog (the unnormalized VKQ partial is still staged as half before the row-sum division); the CPU defect is upstream issue 29774 / PR 29810, where KVU-LB1.a posted the reduced repro and accumulator peaks.
- V11-FA-8 (open): measure per-layer peak abs(V) and unnormalized row sums on the 27B (8k repetitive and 57k contexts) and file upstream only if a value is non-finite or exceeds FP16 range. Candidate FA gates compare the non-finite case set against the incumbent rather than demanding 0/228 on the bias1024 stress.

## Compiled Update — 2026-10-22 (wrap-up sweep 10): KVU-12.1 reads DENSE_STAYS, the fork flip is numerics not a defect, and CME-7 missed its cache gate on client layout

**Confidence: verified** for the recorded KVU-12.1, KPF-18-S1 and CME-7 numbers (run artifacts and server logs, read offline) and for the driver fixes (tests, no server); **inferred** for the CME-7 checkpoint mechanism (INFO-level log, read from cached-token arithmetic plus source) and for every prediction not yet re-run.

- **KVU-12.1 checkpoint-policy arms: DENSE_STAYS for every alternate arm.** Qwen3.6-35B-A3B-MTP Q8_0, one CPU quarter, fork binary, `decide` selection null. Keep `--ctx-checkpoints 32 --checkpoint-min-step 8192`. The 8k conversation (~8.2k tokens) is shorter than every min-step of 8k or more, so dense, coarse, fixed_s8k_c8 and fixed_s16k_c8 place identical checkpoints (296 / 231 MiB for w0 / w1) and fail the bytes rule by tying; fixed_s4k_c8 costs +27.8% bytes and halves edit_back_4096 `prompt_n` (5,176 vs 10,331). 8k therefore does not discriminate.
- **tail_junction fails on substance at 32k.** On the clean w0 pair it saves 40% bytes (460 vs 763 MiB, 4 vs 7 states) but edit_back_8192 / edit_back_16384 fully re-prefill: `prompt_n` 37,976 / 37,989 vs dense 9,200 / 18,766, TTFT 620 / 651 s vs 291 / 520 s (indicative). Junction-only placement loses every resume deeper than the last user message. Only the coarse grid is unmeasured at 32k (KVU-12.1b, 2.2 h, ~45 GiB, launcher armed, not run); the prediction stated before the run is that coarse restores near ~17k, `prompt_n` about 21k vs 9.2k, so it fails and DENSE_STAYS holds.
- **The simulator was NOT validated, and the launcher did not check.** `sim_matches_log=false` in 16/16 cells (12/12 at 8k); phase 2 started on phase-1 rc 0 alone. Causes were in the driver: estimated rather than rendered user-start offsets (sim 31,064 vs log 28,930 at 32k), the first user start dropped (the server's empty-set checkpoint sits at 154), an n_ubatch checkpoint 4 tokens off, and a wave-1 artifact (w1 inherits the w0 checkpoint at 154 on the warm server, so every w1 row under-reports count by 1 and bytes by ~63 MiB). The two 32k w1 ERRORS were a driver bug, not a server fault: `fit_conversation` overshot its target (38,868 vs 32,688 tokens) and `extend_1` overflowed `-c 40960` (HTTP 400), which also explains tail_junction's 3,233 s wall.
- **KVU-12.1a driver fixes landed (research `f7b647705`, not pushed).** Fit refuses loudly (`REFUSED_FIT`), `-c` is sized per cell with a pre-request `REFUSED_CTX`, an exact `ServerSim` runs on rendered token ids, each ckpt cell gets a fresh server, and `run` refuses (rc 8, `REFUSED_SIM_GATE`) while an earlier cell lacks exact agreement. Offline re-check of the recorded run: wave 0 went from 0/8 cells to 8/8 cells and 34/34 requests exact (prompt_n, cache_n, positions, count, bytes); wave 1 still differs only by the inherited checkpoint. 86 tests pass.
- **KPF-18-S1: the fork flip at token 161 is read as batch-shape/placement numerics (OBSERVATION grade, not a verdict).** Predeclared item-3 rule NOT satisfied, `aa_diverges_earlier`: the no-fork A/A pair itself diverges at token 114 (margins 1.10 / 0.87) while the fork-vs-nofork flip at 161 sits at a 0.167-nat near-tie, 0.010 nats above the 0.157 A/A noise. The fork arm differs from nofork in exactly the dimension the A/A does not vary (shared vs private trunk cells, child resuming at a different time: child TTFT 12.0 s fork vs 14.6 s nofork), so the nofork arms are not a same-shape control; on deterministic CPU, KPF-17.2(3) is byte-identical. A v2 same-shape control (three arms, n >= 3 fresh loads) is filed and armed, not run.
- **KPF-18-S1 per-item counts.** Item 2 (A/A-floor oracle) 0/12 OK: the zero floor is run-to-run determinism with placement fixed, not the placement floor, so it needs a placement-varied control. 18.1 rules met (A 3/3 n_fork == T; A_tailonly recorded 3/3 at 8000, probably an arm-order confound); 18.2 cold and policy controls met (junction-only = dense = 8508); 18.3 part 1 chunk-split cost -0.25% / -0.08%, inside noise; 18.3 part 4 ABSTAINED (common greedy prefix 0 < 16). Steps 6 (KPF-19.1a) and 7 (HSF-4/5) did not run.
- **KPF-26.1 outcome runner exists now.** The "runner not located" blocker was wrong: nothing existed, so it was written (orchestrator `c6f58498`, pushed, not merged; 18 fake-endpoint tests). It renders every delegate-wave step with the real `_build_step_prompt`, flags off (arm A) vs shared-first (arm B) plus a flag-off rerun (A2) as the spread; verdict UNCHANGED / WITHIN_SPREAD / CHANGED / INVALID. KEEP_ON_ELIGIBLE needs both windows (seeds 261, 262) UNCHANGED or WITHIN_SPREAD; no window has run. Trunk-prefilled-once timings, child TTFT and admission waits stay in KPF-26.
- **KPF-LB1: on the 27B chat path one turn in five to four re-prefills from near zero at turns 2-3.** From opencode step records (token-weighted hit): qwen-gpu (Qwen3.8-27B) turn 1 0.032 (n=162, 85% cold), turn 2 0.696 with 19.8% of steps below 10% cache, turn 3 0.784 (24.7% cold), turns 4-5 0.878, 6-10 0.934, 11-20 0.948; qwen-local (Flash-Next) turn 2 0.976, 0% cold from turn 2. The /completion x turn cell is NOT measurable from retained logs (`serving_calls` has no session or turn key; 8 `/completion` rows), so the `message_delimiters` flag is not added. KPF-LB1.1 (replay one captured 12-turn REPL transcript through /completion and chat, ~25 min on :8083) is armed; its capture fixes landed (orchestrator `cdbca26b`).
- **CME-7 poker smoke missed the prefix-cache gate: 0.7948 vs 0.95 (103,933 cached / 130,762 reusable), mostly client layout.** Of 26,829 re-prefilled reusable tokens: 52.4% (14,058) the schema instruction was attached only to the OUTGOING last user message, so the previous user message changed at its tail; 41.1% (11,028) previous-call generated tokens that the CME-5 rule counts as reusable but a hybrid server never reuses (accounting); 6.5% (1,743) parse-retry history rewind; slot misrouting 0, so pinning slots would gain nothing here. For every one of 38 steady-state calls `cached = previous_input - (380..460)`, i.e. exactly one user message re-prefilled.
- **Mechanism and gate amendment.** For a recurrent model the slot resumes only from a context checkpoint (last user-message start and prompt end - 4); the LCP ended inside the previous user message, so the end-4 checkpoint was rejected and the user-message-start one used (inferred; CME-7S reruns at `-lv 4`). The 0.95 bar stands but the CME-5 denominator is unreachable (about 0.91 even with perfect layout), so the gate basis was amended before any rerun to `prompt_prefix`: recorded smoke 0.868, projected about 0.99 after the layout fix (research `08ace05fd`, instruction stored once in the user message). Confirmation needs CME-7S.
- **CPU-FA-VKQ-3 moved to the top of its queue.** Production v10 has no fix for the dense F16 MTP head's overflow-prone accumulation and the architect declares 262144 context, so the > 64k MTP acceptance check (`GGML_FA_VKQ_F16=1` vs default) is now first. Evidence was also posted upstream (llama.cpp PR #29810): non-finite only for n_q < 64 once n_kv*bias > 65504, F16-accumulator sub-overflow error 0.297 vs 4.1e-5 in F32, fused-F32 op-time parity on Zen 5, real-model peak 237.6 with a 2048-cell window.

### Source References (2026-10-22 wrap-up sweep 10)

- [handoffs/active/kv-unified-stack-rollout.md](../handoffs/active/kv-unified-stack-rollout.md) — KVU-12.1 verdict, KVU-12.1a driver fixes, CPU-FA-VKQ-3, KVU-LB1.a upstream post
- [handoffs/active/kv-prefix-fork-and-paged-attention.md](../handoffs/active/kv-prefix-fork-and-paged-attention.md) — KPF-18-S1 counts and item-3 reading, KPF-26.1 runner, KPF-LB1 turn table, KPF-LB1.1 spec
- [progress/2026-10/2026-10-22-cme7-cache-miss.md](../progress/2026-10/2026-10-22-cme7-cache-miss.md) — CME-7 miss decomposition, checkpoint mechanism, gate amendment
- [progress/2026-10/2026-10-22-kpf261-runner.md](../progress/2026-10/2026-10-22-kpf261-runner.md) — KPF-26.1 runner design and rule
- [handoffs/active/conversational-memory-eval-instrument.md](../handoffs/completed/conversational-memory-eval-instrument.md) — CME-7R/7S/7T task text and the cache finding
- [progress/2026-10/2026-10-22-workspace-f8.md](../progress/2026-10/2026-10-22-workspace-f8.md) — KVU-12.1 / KPF-18-S1 verdict analysis

## Compiled Update — 2026-10-22 (wrap-up sweep 9): KPF-64 is slow because of decode contention, not thinking, and it keeps the live design

**Confidence: verified** for the decode rates and the per-arm times (server logs and harness tests); **inferred** for the 4-night total, which depends on windows.

- **Mis-diagnosis corrected.** The first explanation for the slow replay was thinking-on. The logs say otherwise: on raw `/completion` (no chat template) `predicted_n` averaged 119 against a 128 cap, and decode ran at 0.80 tok/s per slot because it competes with the other three slots' prefill, while prefill alone ran about 200 tok/s aggregate.
- **Outputs are not skippable.** In `--history live` the model's reply is stored, re-sent in later prompts and defines the ideal bound, so an `n_predict 1` shortcut would change what is measured. Research `b93017dc9` caps live generation at the recorded reply length (-17% decode tokens), fixes the `--history reference` bound (`slot_holds_output=False`) and keeps the endpoint on raw `/completion` on purpose (a chat template tail would force a rollback per request).
- **Time per full arm (24 threads).** Live about 20.7 ks (A) and 14.7 ks (D); the jobs' per-arm minimum windows are 23,800 s (A, B, C) and 16,900 s (D); the reference variant would take 11,500 and 8,100 s. A 2 h 50 min window cannot finish a live arm.
- **Operator decision (2026-10-22).** Keep the LIVE design with night windows: one atomic arm per quarter-night of at least 6.6 h, 8 arms, about 4 nights. The reference-history variant stays a declined alternative on record. Partial arms pass1-A (196/400) and pass2-D (260/400) are voided (PREDECLARED Amendment 2).

### Source References (2026-10-22 wrap-up sweep 9)

- [progress/2026-10/2026-10-22-kpf64-decode-fix.md](../progress/2026-10/2026-10-22-kpf64-decode-fix.md)
- [handoffs/active/kv-prefix-fork-and-paged-attention.md](../handoffs/active/kv-prefix-fork-and-paged-attention.md)
- [docs/guides/agent-workflows/compute-fillers.md](../docs/guides/agent-workflows/compute-fillers.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 7): the fork is cleared of the 1-token divergence, the G1 reference was the defect, and unified-vs-split np4 reads NO_DIFFERENCE (weakly)

**Confidence: verified** for the named run records and logs; **inferred** for the filed Locals+Beacon tasks; the KVU-12.4 verdict is PROPOSED-until-ratified and weak, and the np8 pair is CONFOUNDED (no verdict).

- **KPF-13.1 closed in the fork's favour.** The 1-token-suffix divergence is CPU batch-shape numerics (a 1-token ubatch takes vec_dot, not GEMM), not a fork defect; kpf13-v2 shows the fork token-identical to a cache hit 24/24. The same batch-shape drift explains SPEC-RNG.1.1: np1==np4 identity failed 7/8 and 6/8 with a stateful control drifting identically, so the RNG is not the cause.
- **kvu12-2: an MTP drafter-state bank fixes a roughly 20% decode loss on restore** (f8, ran inside f8-day-q0).
- **KPF-18 item 3 (fork vs no-fork, G1 repeats, six records).** Token-identical 17/21 vs A/A 20/21, minimum greedy prefix 43 for both. Fork divergences: group 0 at token 43 (once) and group 3 at token 161 in 3 of 3 passes, while group 3 A/A pairs were identical 3 of 3. Observation grade; KPF-18.0d item 3 group 3 is filed to read the top-2 margin at 161 (a near-tie means not a fork effect).
- **KPF-62.8 chunk-KV real-role G1 (Qwen3-VL-30B-A3B Q4_K_M, f32 K/V): the pre-registered reference was the defect.** First run failed 9 checks (K NMSE 1.4e-3 to 1.8e-3, V 6.4e-3 to 7.8e-3, logits 5.4e-3 to 8.7e-3 at deltas 1/17/300) although injected V was bit-identical to source; the drift is ulp-level RoPE rounding amplified by q8 re-quantization and router top-k flips across 48 layers. Fix @ `357f3117f` adds G1a (inject vs in-tree `seq_add`, bit-identical K, V, logits); re-run PASS at all three deltas, and the in-tree shift shows identical drift against the in-place reference. Operator-visible caveat: the criterion was changed after data existed and is recorded as an amendment (KPF-62.9 ruled option A); in-place drift is now an ungated translation-drift figure under the G3 budget.
- **KVU-12.4 np4 L64k ABA: NO_DIFFERENCE, weak.** Unified vs split: decode sum -22.78%, per stream -24.33%, TTFT +0.79%, against anchor floors of 12.48%/11.93%/0.51% (threshold 2x floor); a 12% floor means "about 23% slower but within noise", not equal. The np8 L64k pair is confounded (unified `gpu_busy_frac` 0.4654 plus a foreign KFD process vs split 0.0). The s4 128k cell hit its 12,000 s cap on the wrong estimator and the re-runs were declined (frontdoor is moving to GPU).
- **PB-HOL-1 budget-on arms: the prefill budget is not a head-of-line fix.** Short prompt above the long slot waited 83,352 ms vs 70,932 ms off (below it 3,593 vs 3,217.5 ms); confounded by `-b`/`-ub` 512 to 2048. Frozen PB-QCOST-1 failed held-out (MAPE 12.84% n=1, 26.32% n=4).
- **Filed, unrun:** KPF-LB1 (cache_n/prompt_n by role x endpoint x turn; message_delimiters on /completion), KPF-LB2 (replay harness amendments before first live arm), DS-LB1 prefix-property tests, KVU-LB1 FP16 V-accumulator upstream follow-through, KVU-12.3a zero-compute log pass (open P-A patch only if generated-span divergence reaches 5% of processed prompt tokens at 3+ busy slots).

### Source References (2026-10-22 sweep 7)
- [handoffs/active/kv-prefix-fork-and-paged-attention.md](../handoffs/active/kv-prefix-fork-and-paged-attention.md)
- [handoffs/active/kv-unified-stack-rollout.md](../handoffs/active/kv-unified-stack-rollout.md)
- [handoffs/active/dynamic-stack-concurrency.md](../handoffs/active/dynamic-stack-concurrency.md)
- [progress/2026-10/2026-10-22-kpf62-fix.md](../progress/2026-10/2026-10-22-kpf62-fix.md)
- [progress/2026-10/2026-10-22-workspace-f8.md](../progress/2026-10/2026-10-22-workspace-f8.md)
- [progress/2026-10/2026-10-22-workspace-58.md](../progress/2026-10/2026-10-22-workspace-58.md)

## Compiled Update — 2026-10-21 (wrap-up sweep 6, workspace-f8 delta): KPF-18 item 7 fan-out speed on the MI210, and PB-HOL-1 confirms head-of-line blocking

**Confidence: verified** for the recorded run numbers (records and summaries named); **inferred** for the KPF-62 slices, which are filed and not run.

- **KPF-18.0d item 7 (T4, done 14:55Z 2026-10-21, rc 0, CANDIDATE grade, A/B/A/B; fork build `gpu-20261020-a1f0c8cf9`).** Four-way fan-out total TTFT: fork_off 1312.9 s and 1404.0 s, fork_on 169.3 s and 140.0 s (about 8.5x). Prefill tokens 254,512 -> 74,512, exactly the shared expectation (unique cells 75,532); aggregate decode 3.40/3.32 -> 26.5/32.1 tok/s; all checks OK. Records `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run-c/records/` and `item7_summary.json`. Equivalence is not measured in item 7 (items 1 and 3 carry it).
- **PB-HOL-1 off arms (16:00-16:12Z): predeclared verdict CONFIRMED.** Rule B_median >= 2x A_median holds: A-off (short slot below long) TTFT median 3217.5 ms, B-off (short slot above long) median 70932 ms, B/A = 22.05; C solo about 280 ms; solo 64K prefill 119.9 s. Slot-order head-of-line blocking is real on this server, so the ordering-fix trigger (M4, shortest-remaining-prompt-first plus a prefill-vs-prefill cap) is OPEN, and the DI-126 monitor changes from "nothing to fix until measured" to "component (ii) is measured". Summaries `/mnt/raid0/llm/tmp/pb-hol-1/runs/*/summary.md`.
- **Budget-on arms did not run**: a harness bug (`end_phase` did not clear `self.srv`, so `check()` read the stopped phase-1 server as dead) and a preflight refusal (`plan_estimate` ignored `--phases`); both fixed. Re-armed for 2026-10-22 (`/mnt/raid0/llm/tmp/pb-hol-1/overnight-on-launch.sh`, latest start 06:03Z, hard stop 06:25Z).
- **KPF-62.3 to KPF-62.8 filed (not run)**: selector (head window W=64 plus check-layer K deviation), sparse recompute by explicit-position batches (G0 at r=100% bit-identical), server wiring (`--chunk-store-mib`, `kv_chunks`), G3 harness on the frozen corpus, speed report vs tuned prefill, and the real-role G1 (Qwen3-VL-30B-A3B Q4_K_M f32 K/V).

### Source References (2026-10-21 sweep 6)
- [handoffs/active/kv-prefix-fork-and-paged-attention.md](../handoffs/active/kv-prefix-fork-and-paged-attention.md)
- [handoffs/active/gpu-serving-tie-in-program.md](../handoffs/active/gpu-serving-tie-in-program.md)
- [handoffs/active/kv-unified-stack-rollout.md](../handoffs/active/kv-unified-stack-rollout.md)
- [progress/2026-10/2026-10-21-workspace-f8.md](../progress/2026-10/2026-10-21-workspace-f8.md)

## Compiled Update — 2026-10-20 (wrap-up sweep 2): the unified-KV and prefix-fork programs gain DeepInfer probes, and two decisions close

**Confidence: verified** for the recorded P1 gate results, the champion-manifest rows and the operator decision; **inferred** for every DeepInfer-derived probe below (each is a filed, unrun task whose rule is a hypothesis).

- **KVU-21: agent-resume recompute probe on :8083 (filed, not run).** From existing request logs, compute per resumed agent turn the recompute fraction (prompt tokens processed over prompt tokens) against pool usage from `/slots`, at 1 to 4 concurrent agents. Rule: median fraction at or above 0.25 at 3 or more agents while usage is at or above 0.5 opens a CONCUR-style AIMD admission trigger; below closes it. The point is that the unified pool's fit limit is not the only failure mode; a pool-fit-only cap misses queue wait that rises while occupancy is low (dormant trigger).
- **KVU-12.3: decode-boundary checkpoint arm.** A fifth hybrid-checkpoint arm in the KVU-12.1 matrix snapshots recurrent (and drafter) state every 128 generated tokens, measured on the frontdoor Qwen3.6-35B-A3B and the 27B by turn-2 resume `prompt_n` after 1k-4k generated tokens, checkpoint bytes and TTFT. Counts are correctness class; TTFT needs a window. Rationale: GDN layers cannot be "replayed instead of checkpointed" (the DeepInfer reading is retained as the boundary for any future replay proposal; only drafter SWA windows qualify).
- **KPF-28: DS41 checkpoint and fork characterisation.** DeepSeek-V4.1 uses a dsv4 memory with a raw SWA window, compressed planes with compressor state, an indexer and engram state. Before any fork policy is chosen, record bytes per checkpoint per component, whether `create_checkpoint`/restore and the KPF-11 fork rule work on `llama_kv_cache_dsv4`, hit length against the checkpoint grid (128-aligned versus dense) and resume `prompt_n`. It decides whether a 128-grid policy or a window-state-free checkpoint (needs DS41-CED.1) is worth building.
- **P1 prefix fork was re-cut onto the live champion tip.** Canonical branch `experimental/kv-prefix-fork-p1r2-20261020` @ `14d603f3a` on champion `dd3d9721c`: the six fork commits applied cleanly; `test-kv-seq-share`, save-load/state-restore, `test_slot_fork.py` 12/12 and `test_slot_save.py` 15/15 pass; fork-off equals champion 7/7 on two models. P1 ownership moved from workspace-ec (no bus heartbeat since at least 2026-10-08, code ungated for 16 days) to the operator session; P2-P5 stay with workspace-ec.
- **The 10-04 "open divergence" finding is benign (KPF-18.0c).** A hybrid fork child departing from a fresh run at token 55-57 is bit-identical to the same slot continuing a trunk it prefilled itself, and a fresh run on a deliberately fragmented pool diverges at the same token. The cause is prefill chunk boundaries and KV cell layout, not fork state. This closes the order-preserving-placement worry for now (P3 stays a measure-first item). KPF-18.0b (re-run items 1, 2, 5 on the fixed runner, plus the 16k fan-out item 7) is still open; the inherited runner had three bugs (late-bound trunk length, child sent after controls, missing log dir).
- **KPF-17a shared-trunk FlashAttention cases pass:** CPU `FLASH_ATTN_EXT` 5207/5207 including 25 shared-trunk cases; ROCm0 2978/2978. The KVU-19a 64-case exactness harness on ROCm0 and CPU remains open.
- **Decision OP-KPF19-2: accept upstream's slot-file layout.** A pinned junction restored from a slot file (SCKP block, upstream #26004) comes back unpinned: never wrong output, at worst extra prefill if eviction drops it first. No slot-format divergence. Dormant re-pin trigger: migrated fan-outs losing fork hits after a full-to-half KV migration, handled by re-sending the trunk's `checkpoint_at` request (KPF-21).
- **Orchestrator scout path (KPF-21/25)** is on `feat/rtg58-kpf21-25-20261020`, pushed and NOT merged: one `max_tokens: 0` trunk request with `checkpoint_at` before siblings are released, behind `ORCHESTRATOR_PREFIX_INDEX` + `_FORK` and `/props.slot_fork`. `llm_call` delegate waves are not wired.
- **v11 champion manifest ties the KV rows together.** KVU-19a (FA masked-KV-block skip, GPU and CPU), KVU-19b commit 1 (`n_seq` hint to the vec kernel), the HIP-graph MMVQ q8_1 private arena (VRAM growth +0.057 versus +5.83 GiB), the fp16-VKQ overflow fix, FA-INT64-OFFSET (past about 524k cells at ub 2048) and the decode-aware prefill budget (decode-under-prefill x2.92 at solo prefill -4%, versus `-b 512` x3.22 at -14%) are all IN the champion `dd3d9721c`; the `:8083` prefill-budget switch lands with v11. Per-keep percentages are 5-pair screening numbers, not additive (CH-16: 36 claims compounding to +171.7% against a measured +8.524% block effect). The manifest also flags dangling ids: V11-FA-1..6 and `KVU-19b-rework-c2-cal` are referenced by the index but absent from `kv-unified-stack-rollout.md`.
- **Dormant triggers worth remembering (no tasks):** MTP state-hook port if fork restore drops draft acceptance; iSWA `seq_pos_max` assertion (upstream #29480) on a Gemma-class gate; intra-batch state capture if the forced chunk-end split costs more than the noise floor; a host-pinned KV tier prototype (MORI UMBP gather pattern, MIT) only if an analytic write-through mirror fits the decode budget; MORI itself does not support gfx90a or ROCm 6.2, so any use is a port. Gemma-3n/4 style KV-shared prefill skipping has no consumer since Gemma-4 left the lineup.

Open questions: does the fork-attributable divergence stay under the fragmented-layout control at production length (KPF-18.0b)? Do hybrid agent resumes recompute enough to justify admission control (KVU-21)? See [Inference Serving](inference-serving.md) for the slot-fabric side and [MoE Optimization](moe-optimization.md) for the routing-tap instrument.

### Source References (2026-10-20 sweep 2)

- [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md) — KVU-21, KVU-12.3, dormant triggers.
- [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) — P1 recut, KPF-18.0c, KPF-19.2, KPF-28.
- [llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md) — KV rows IN the champion and the at-risk list.

## Compiled Update — 2026-09-24 (wrap-up #4): production is now unified, and the "unified costs aggregate" reading was answer length

**Confidence: verified** for the live shape (launch log, `/proc/<pid>/cmdline`) and the load-only table; the
throughput confirmation rests on n ≤ 2 per cell and one named substitution (below).

- **Live since ~18:50Z (OP-54, orch `0a564a1f`, research `75ee1b8e`):** :8083 runs `-np 4 -c 196608
  --kv-unified --spec-draft-n-max 4 -ub 2048 --cache-ram 65536`. The log reads `n_slots = 4, n_ctx_slot =
  196608, kv_unified = 'true'`, and a 124k-token request served. O-2 (q8_0 draft KV) was **dropped**: the q8_0
  draft cache adds a 768 MiB FA conversion buffer, which cancels its saving. np 4 at 196k fits only because
  whisper STT left the GPU (projected free ≈ 1.88 GiB with VL resident).
- **Load-only (server MiB above a 2,139 MiB base, 27B, n = 1):** split d8 np2/196k 39,018 · unified d4 O-2
  np2/196k 39,026 · np4/196k 40,522 · np2/262k 42,362 · np4/262k 43,858. Each extra slot pair ≈ +1.5 GiB
  (per-slot recurrent GDN state, not KV); 196k → 262k ≈ +3.3 GiB.
- **Throughput verdict confirmed (RTG-57 KVU-8).** 35B-A3B fixed-length L 2048 cells: unified within 2% of split
  in all 4. 27B cells where every request ran to the cap: unified aggregate +5.1% at np 4. Live np4 at fixed
  length (M-4, 2 waves): 40.2/39.9, 71.4/67.8, 95.3/93.1 tok/s aggregate at concurrency 1/2/4 — in line with the
  split study cells. The single-wave −8%/−16% was the answer-length artifact. Substitution: no fixed-length
  **split** arm was re-run on the 27B.
- **35B-A3B diverges even at np 1** under the two modes (0 matching fingerprints), so at 8k/32k its −5.3..+5.6%
  per-request spread compares different sequences. np 8 fits on the 35B (44–45 GiB at 32k).
- **Context checkpoints fire on the unified hybrid:** 26 `created context checkpoint` lines (150 MiB each, up to
  32 per slot) since the np4 launch — the only partial-prefix reuse the hybrids get.
- **None of these numbers can gate a decision yet:** the study drivers, M-4's live driver and M-3's log read have
  no write-side hook, so they produce zero belief-kernel tuples and are not backfilled (VB-KVU-1, VB-KVU-1a). M-3's
  depth-4 figure is a projection and must be recorded as one if a script ever emits it.
- Voice/STT/TTS planners: the GPU constraints above, with the CPU speech contention numbers, are collected in
  [`cpu-speech-contention-20260924.md`](../docs/reference/speech/cpu-speech-contention-20260924.md).
- **CPU speech contention decided 2026-09-24 (KVU-11b): the operator chose D, no change to the CPU speech layout,**
  pending their own STT/TTS integration plan. So TTS stays off the GPU and the np 4 / 196k :8083 VRAM budget above
  stands; returning TTS to the GPU (0.92 GB of weights) is a question for that plan, not open work here.

### Source References (2026-09-24, wrap-up #4)

- [`kv-unified-stack-rollout.md`](../handoffs/active/kv-unified-stack-rollout.md) — KVU-1, KVU-1c, KVU-1e, KVU-8, KVU-9, KVU-11b (decision D).
- [`2026-09-24-main-ak-seat.md`](../progress/2026-09/2026-09-24-main-ak-seat.md) — *Stack window, part 2*.
- [`cpu-speech-contention-20260924.md`](../docs/reference/speech/cpu-speech-contention-20260924.md) — §6, GPU-side facts.
- research `artifacts/np_context_kvu_study_20260924/README.md` §7–§9 (`07060eaa`).
- [`vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) — VB-KVU-1, VB-KVU-1a, VB-SPEECH-CPU-1a.

## Compiled Update — 2026-09-24: production was never unified — `-np` disables llama-server's auto-unified KV; the 27B GPU split-vs-unified verdict

**Confidence: verified** for the root cause (frozen-tree `file:line` reads plus every live launch log) and for the 27B GPU numbers (research study README, recomputed from `summary.tsv` / `pq.jsonl` / `server.stderr`; **n = 1 per cell, no noise floor measured**). Figures marked **modelled** come from the stack-change package's buffer model, not from a run; the RAM-tier size is marked **inferred** where its source marks it so. The Qwen3.6-35B-A3B matrix was still running and uncommitted at compile time and is **not** used here (KVU-9).

### Root cause: the auto-unified default exists only when `-np` is absent

The registry said "KV IS UNIFIED ON THIS SERVER" for :8083 (Qwen3.8-27B Q8_0, MI210), but **no production launch ever ran unified KV**. The frozen v10 server's `n_parallel` defaults to `-1` (auto) (`common/arg.cpp:1216`); auto becomes 4 slots **and** `kv_unified = true` (`tools/server/server.cpp:145-150`) — the only place the server enables unified by itself. Any explicit `-np`, including `-np 4`, leaves the library default `kv_unified = false` (`common/common.h:580`; help text "default: enabled if number of slots is auto", `common/arg.cpp:1548`). The orchestrator launcher **always** passes `-np <slots>` (`orchestrator_stack.py` `_build_role_command`) and no orchestrator file mentions kv-unified, so every live llama-server logs `kv_unified = 'false'`. The "unified" registry evidence came from **bench** launches with no `-np` (2026-07-31, 2026-09-17) or with `--kv-unified` passed by hand (2026-08-20). The rule for every agent is now canonical: [`OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks* → "The llama-server KV mode is an argv fact, not a default"](../agents/shared/OPERATING_CONSTRAINTS.md).

**Semantics.** Split: `n_ctx_seq = n_ctx / n_seq_max`, so each slot is a hard `-c / -np` partition; unified: `n_ctx_seq = n_ctx`, one shared pool (`src/llama-context.cpp:289-302`). Total attention-KV bytes are identical in both modes — only the partition changes. :8083 runs `-np 2 -c 196608`, so every request has been capped at **98,304 tokens** — the ceiling that emptied DS41 run 8's first planner reply (`finish=length`, 1235.7 s). The MTP draft context inherits the flag (both contexts get `n_ctx_seq = 196608` under `-kvu`).

### The 27B GPU study (v10 GPU binary, MTP draft depth 8, olympiad-style prompts, n = 1 per cell)

| Finding | Measured / modelled | Value |
|---|---|---|
| Per-request decode, np 1 | measured | unified vs split +0.2% / −1.1% / −0.4% at L 2k / 8k / 32k — **equal within 1.1%**, byte-identical outputs |
| Per-request decode, np 2 and np 4 | measured | unified **+0.3% to +5.7%** in all 6 cells (outputs differ, so different sequences are compared) |
| Aggregate, np 4 | measured, **confounded** | unified −8% at 8k (94.0 vs 102.0 tok/s), −16% at 32k (85.0 vs 100.8); completion tokens differ (8k: 21,894 vs 24,663), so not attributed to KV mode. Where every request hit the same cap (L 2048) unified aggregate was +5.1% (97.6 vs 92.9) |
| Long prompt at production shape `-np 2 -c 196608` | measured | **124,174-token prompt accepted under unified** (prefill 399.9 tok/s, 310.5 s); split returns HTTP 400 `exceed_context_size_error` at 98,304 after 0.2 s |
| np 8 | measured | does not fit in either arm: L 2048 skipped at 63 GiB whole-device (above the 62 GiB guard); L 8k/32k OOM at load (32k on a 10,773 MiB `rs cache` allocation). The per-slot GDN recurrent state, not the KV mode, limits the slot count |
| O-2 (`-ctkd/-ctvd q8_0`) per-request | measured | 39.4 vs 37.1 tok/s (2k), 41.0 vs 41.3 (8k) — **no per-request cost** |
| O-2 saving 0.35 GiB (draft KV 768 → 408 MiB) | **modelled** | package buffer model at `-c 196608`; the integer-GiB device column shows no difference at the tested shapes |
| Unified KQ-mask growth +0.75 GiB | **modelled** | mask is 768 MiB at any `-np` under unified vs `196608/np × 2048` elements split; +384 MiB per context × 2 contexts at np 2 — fixed at load, not a runtime ratchet |
| MTP draft depth 4 vs 8 (unified) | measured | acceptance 0.632 / 0.648 / 0.661 vs 0.403 / 0.448 / 0.443 in the same cells (all v2 depth-8 cells: 0.368–0.460); per-request +7.8% (np2 2k), −2.4% (np2 8k), +2.4% (np4 8k); load-only at `-np 2 -c 196608 --kv-unified`: 63,568 vs 64,582 MiB whole-device = **1014 MiB less** at depth 4 |

Verdict (progress log): **unified KV does not cost throughput** on this model; a fixed-length (`ignore_eos` + `n_predict`) or ≥3-wave confirmation is still owed (KVU-8). Depth 4 is neutral on speed and must be confirmed on production traffic before the recipe changes (KVU-1b). Capacity at production shape (**modelled**, package §4.3): np2 + `-kvu` leaves 0.18 GiB card free; np2 + `-kvu` + O-2 leaves 0.53 GiB (the recommended funding); each extra slot costs +1.315 GiB of GDN state at draft 8, independent of `-kvu`, which is why a higher `-np` is not cheap on the hybrids.

### Two pool-full failure shapes — and the server's general abort-all

At `-np 2 -c 4096` with two concurrent 2048-token generations (measured, v1 + 3 repeats):

- **Unified: exactly one request fails** (HTTP 500) with `speculative batch index 8 is not inside the current sub-batch [0, 8)` in **4 of 4** runs — not the clean "Context size has been exceeded." path; the survivor runs to 2048 tokens, deterministically. Filed as a guarded v11 experimental-kernel candidate (KVU-7).
- **Split: never errors, silently truncates** at the slot in 4 of 4 runs — both slots stop at `n_tokens = 2047, truncated = 1` (`finish_reason: length`) after 1777 and 1632 generated tokens.

The general v10 behaviour on unified exhaustion (package §4.4, **source-read, not a measured run**): admission checks the prompt against `slot.n_ctx` only (`server-context.cpp:3303-3310`), never pool occupancy, so two long requests (e.g. 120k + 90k on 196,608) are both admitted. When `llama_decode` finds no free cells the server purges idle slots (`try_clear_idle_slots`, `:1716-1735`, unified only), halves `n_batch` down to 1 (`:3797-3801`), then throws "Context size has been exceeded." (`:3759-3763`) and `abort_all_slots` **fails every in-flight request** (`:2949-2951`). Not a crash, but both callers lose their request. How the orchestrator defends against this is in [inference-serving.md](inference-serving.md) (2026-09-24 section).

### Idle slots are cleared under unified, and the RAM tier is too small to catch them

With the default `--cache-idle-slots`, starting any task already saves idle slots to the RAM prompt cache; under unified KV it **also clears them** (`server-context.cpp:2468-2482`, `TAG_IDLE_SLOT_CLEAR`). A returning conversation then restores its prefix from RAM — a warm-prefix latency cost on a shared server, not a correctness cost. But every server runs the **8192 MiB** `--cache-ram` default, and one full-pool 27B prompt is **~9.2 GiB (inferred** from the :8083 buffer lines: 6528 MiB attention KV + 2693 MiB recurrent state; whether RS is stored per entry is not verified), so the idle-slot save is likely a no-op for long prompts until `cache_ram` is sized. Proposed sizes (KVU-2, OP-55): 65536 MiB on :8083 (floor 24576), 32768 on :8070, 16384–32768 on :8074, 0 on :8086. **Decided by the operator 2026-09-24 (~17:50–18:10Z, OP-55):** all of it as recommended. Reroute only `ingest_long_context`; route by the live per-request limit rather than a ~5k threshold; apply these `cache_ram` sizes via the package; the opencode bypass uses live `/slots` plus retry. OP-56 moves whisper STT back to CPU, which is what lets :8083 `-np 4` fit ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) *Start here*).

### Unified changes outputs at the same seed

At seed 42, T 0.6, unified and split produced **different completions at np 2 and np 4 in every cell**; at np 1 they were byte-identical. The expected cause is that the KV layout changes float summation order. Unified np 4 even differed between its 8k and 32k cells, so **the pool size itself perturbs outputs**. Any deterministic replay or output-comparing A/B must pin the KV mode per arm (OAB-4a).

### Rollout candidates (inventory ranking)

1. **:8083** — the only role whose alias (`ingest_long_context`) is defined by long context; package awaiting signature (OP-54; KVU-1).
2. **Embedders :8090–8095** — `-np 4 -c 512` gives 256 tokens per slot, below bge-large's 512 window, with a WARN on every launch; `-kvu` or simply `-c 2048 -np 4` fixes it; pure attention, no GDN cost.
3. **:8070** — only if long jobs are routed there (today they go to :8083 at a 20,000-char threshold).
4. **:8086** — only if its `-np` rises (pure attention, so unified `-np` is cheap there).
5. **Never** :8080, :8180, :8074 — `-np 1`, per-slot already equals `-c`.

### Source References (2026-09-24, unified KV)

- [`kv-unified-stack-rollout.md`](../handoffs/active/kv-unified-stack-rollout.md) — RTG-57: root cause, the verified "Measured" block, KVU-1..13b.
- [`progress/2026-09/2026-09-24-main-ak-seat.md`](../progress/2026-09/2026-09-24-main-ak-seat.md) — *Stack-configuration window*: DS41 run 8's 98,304 ceiling, GPU sweep timeline, the throughput verdict.
- [`stack-change-kvu-20260924/PACKAGE.md`](../artifacts/operator/stack-change-kvu-20260924/PACKAGE.md) — §1 root cause with `file:line`, §4.2–4.3 buffer model and capacity table (modelled), §4.4 shared-pool failure mode and idle-slot behaviour.
- [`kvu-stack-inventory-20260924.md`](../artifacts/operator/kvu-stack-inventory-20260924.md) — every live server's `kv_unified = 'false'`, declared-vs-live mismatches, ranked candidates.
- [`serving-engine-technique-audit-20260924.md`](../artifacts/operator/serving-engine-technique-audit-20260924.md) — §2.3 the ~9.2 GiB (inferred) prompt-cache arithmetic and FIFO prompt-cache eviction.
- epyc-inference-research `artifacts/np_context_kvu_study_20260924/README.md` @ research main `21cf444c` — the 27B matrix, long-prompt, pool-full, O-2, divergence and MTP-depth results (the files win over the working page).
- [`OPERATING_CONSTRAINTS.md`](../agents/shared/OPERATING_CONSTRAINTS.md) — *Inference and Benchmarks*: the KV-mode-is-an-argv-fact rule and the output-divergence caveat.

## Compiled Update — 2026-08-12: a "keep or port?" review that resolves to *neither*, and the first KV-quant decision package

**Confidence: verified** — the fork verdicts are read-only git archaeology with commit SHAs and ancestry checks; the KV-quant numbers are a measured retrieval-parity run.

### The SWA slot-reuse fork commits: DROP, because they subtract a safety check

Two fork commits (`d1c72d7fc`, `603702769`) sat under review as ambiguous keep-or-port candidates. The verdict is **DROP**, and the reason is stronger than redundancy: the fork **deletes** upstream's `cells.seq_get(idx)` lookup and substitutes the incoming batch's position, replacing a per-sequence-aware sliding-window reuse check with a **per-sequence-blind** one. Under multi-slot serving a cell can be judged reusable against the wrong slot's window. Production v6 through v9 correctly retain upstream's original form and were never exposed.

The reusable lesson for fork-reconciliation reviews: **a commit that reads as "our version of upstream's check" may be upstream's check with a lookup removed.** The discriminating question is not *does the fork do the same thing* but *what does the fork's diff delete*.

### KV quantization has a decision package, and q8 is dominated

The first exact-parity KV-quant measurement gives a clean shape: across f16 / q8_0 / q4_0 KV, retrieval parity holds at **51 of 52 on every arm**. `q4_0` buys **10.54 GiB** of KV headroom at **−7.4% decode**; **q8 is dominated** — it neither preserves the f16 operating point nor buys q4_0's memory. One arm (C) aborted invalid. The recommendation is Option A. This is the first result that lets the KV-quant monitor status recorded in the 2026-07-20 pass below be acted on rather than watched.

### Lazy faulting relocates the `-c` provisioning cost, it does not remove it

The old premise for capping context provisioning — that a large `-c` costs at *launch* — is dead: KV pages fault lazily. But the re-read is not "provision maximally and stop worrying". The cost moves from launch to **load**, and the worst case is the sum of full-window KV across all resident roles under concurrent deep-context load, **which is currently uncomputed**. The recommendation is the staged option: raise `-c` only where the lineup's Σ full-window-KV fits RAM with margin, computed mechanically at priors-compile rather than chosen per role. The ruling belongs to the lineup owner plus the operator and is **not settled**.

### Source References (2026-08-12)

- [`llamacpp-v6-consolidation.md`](../handoffs/archived/llamacpp-v6-consolidation.md) — the SWA slot-reuse DROP verdict and the deleted per-sequence check.
- [`numa-placement-defect-20260730.md`](../handoffs/active/numa-placement-defect-20260730.md) — the T12 lazy-KV decision package and the uncomputed concurrent-load worst case.
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the KVQuant parity/headroom numbers and the dominated-q8 finding.

## Compiled Update — 2026-07-20

The StreamingLLM baseline — the cluster-wide gate that must precede prioritizing the whole May-2026 KV-reduction cluster (SP-KV / KVP / LU-KV / ForesightKV / PBKV) — reached a pre-v7 verdict, and the MI210 sharpened where KV should physically live. Confidence: `verified` for the CPU floor sweep result; `external` for the KV-quant PRs; `inferred` for the MI210 KV-placement economics.

### Key Findings (2026-07-20)

- **StreamingLLM (attention-sink + sliding-window) is the easy-floor gate, and no simple KV cluster is admitted yet.** The scaffold landed in the fork (`632ce0f92`, default-off, via server context-shift `llama_memory_seq_rm`/`seq_add` + `--kv-streaming-sink/-window` + per-request fields) and was reconciled onto current v7 (`111bff89d`/`cf051d3e1`). The pre-v7 floor/admission sweep (Qwen3-1.7B Q8 CPU, 2026-07-20) ran a context-shift baseline + sink/window clusters `8:128`/`16:192`/`32:256`: all arms exited cleanly but **all failed the prompt-quality/final-marker floor**, and no streaming arm beat baseline speed (0.990–1.011×) → `admit_cluster=false`. This closes the "admit a simple KV cluster *now*?" question negatively; the full 4-axis research sweep (retrieval/reasoning/dialogue × 25/50/75% budget × 2 models) stays open. ([streaming-llm-baseline](../handoffs/active/streaming-llm-baseline.md))
- **KV-quant monitor status:** Hadamard rotation (upstream PR #21038) landed and auto-enables when KV types are quantized — a free KV-quality improvement (custom `--kv-hadamard` removed as redundant). TurboQuant CPU KV kernels (PR #21089, TBQ3_0/TBQ4_0, ~5.2× compression) remain open/monitor; ChunkKV (arXiv:2502.00299, 12% retention, +26.5% throughput) is worth-investigating. TQ3_1S rejection stands (immature, VRAM-savings we don't need, MoE ghost-activation risk). ([tq3-quantization-evaluation](../handoffs/active/tq3-quantization-evaluation.md))
- **Where KV physically lives (MI210):** keeping KV in HBM alongside attention weights is ideal but VRAM-limited; PCIe4 (~64 GB/s) is 7–14× slower than EPYC DDR5, so per-token KV *streaming* is an anti-pattern. GDN-hybrid residents have **O(1) KV**, so long-context ingest is comfortably GPU-served (better than a dense model) and makes teleport KV-copy near-moot — the teleport v1 instead *re-prefills from transcript* to regenerate correct KV at the target quant (a copied KV is wrong under quant-asymmetric transport). **Correction 2026-09-24:** the orchestrator does *not* store that transcript today. On `/v1`, `x_session_id` is recorded only, and the session store has no messages table. So v1 teleport depends on client-resent history until the session-keyed conversation store (conversation-stack CS-15) lands. ([gpu-acceleration-path](../handoffs/active/gpu-acceleration-path.md), [heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md), [conversation-stack](../handoffs/active/conversation-stack.md))

### Open Questions (2026-07-20)

- Does StreamingLLM at 50% budget preserve ≥95% accuracy on our representative workloads (the 4-axis sweep is still pending)? The answer sets whether LU-KV/KVP/ForesightKV get demoted or LU-KV promoted.
- Does uniform sink+window hide per-head heterogeneity (LU-KV's whole pitch)? Track per-head attention entropy in the sweep.
- Does PR #21089 (TurboQuant CPU KV) merge and beat Hadamard+q4_0 on context extension?

### Source References (2026-07-20)

- [streaming-llm-baseline.md](../handoffs/active/streaming-llm-baseline.md) — cluster-wide floor gate, scaffold, negative pre-v7 admission sweep.
- [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md) — TurboQuant/ChunkKV/Hadamard KV-quant monitor list.
- [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md) — MI210 KV CPU/GPU-split economics + PCIe anti-pattern.
- [heterogeneous-slot-fabric-residency.md](../handoffs/active/heterogeneous-slot-fabric-residency.md) — O(1)-KV GDN residents + re-prefill teleport (KV-copy near-moot).

## Summary

KV cache is the dominant memory bottleneck for CPU inference on our EPYC 9655 stack. At 256K context, Qwen2.5-Coder-32B's KV cache at f16 consumes approximately 64 GB -- more than the model weights themselves. Since CPU inference is memory-bandwidth-bound during decode, reducing KV cache size directly improves both capacity (more concurrent slots, longer contexts) and throughput (less memory traffic per token). At very long sequences (S >> d_model), attention rises above 50% of total per-token compute time, making KV cache compression a throughput lever, not just a memory lever. Our research has identified four orthogonal compression layers that operate on different dimensions of the KV cache problem, and we have validated or deployed work across all four.

The four layers form a compression stack. **Quantization** (how each KV entry is stored) reduces precision: Hadamard+q4_0 delivers 2-4x compression quality-neutral and is deployed in production since commit `b51c905`, now auto-enabled in v3 upstream. **Compaction** (constructing fewer but more informative KV entries in latent space) uses mathematical optimization: Attention Matching achieves 5x zero-degradation with native ggml NNLS+OLS solvers merged to `production-consolidated-v3` across 3 commits, validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, and Qwen3.5-35B-SSM-hybrid. **Selection** (keeping only important tokens) uses importance scoring: Expected Attention achieves 94.7% RULER at 50% compression on Qwen3-8B and is Flash Attention compatible; TriAttention is the strongest decode-phase scorer with trigonometric Q/K concentration. **Block masking** (removing entire reasoning blocks) leverages model structure: Memento provides 2-3x peak KV reduction by training models to segment reasoning into blocks and retaining only summary KV states; the key finding is that KV states carry implicit information beyond summary text (15pp accuracy penalty when KV states are recomputed without original block context).

Each layer operates on a different dimension -- precision, count, and semantic structure -- making them composable. The theoretical combined ceiling is staggering: quantization 4x times compaction 5x times masking 3x equals 60x. Even the conservative two-layer stack (quantization 4x times compaction 2x) would transform the deployment landscape from "one 256K context slot barely fits" to "eight concurrent slots." The critical unknown is quality interaction under multi-layer compression: each layer claims minimal individual loss, but combined degradation may be multiplicative. Pairwise testing is in progress; three-way testing is a separate gate.

The field is evolving rapidly around closed-form approaches that replace heuristic token eviction with principled optimization. Attention Matching (MIT, 2602.16284) introduced the first closed-form KV compaction decomposition via NNLS for attention mass and OLS for attention output -- no gradient descent, no training, just linear algebra on small matrices that fit in L2 cache. Expected Attention (NVIDIA, KVPress library) uses Gaussian MGF closed-form scoring with Flash Attention compatibility and explicit quantization orthogonality. TriAttention (Song Han lab, MIT/NVIDIA) exploits the intrinsic trigonometric concentration of pre-RoPE Q/K vectors (Mean Resultant Length R approximately 0.98) for scoring. Memento (Microsoft Research) revealed the dual information stream: KV cache states computed while a block is visible carry implicit information recoverable by probing at 23-27% from downstream memento states (vs 10% chance), establishing a fundamental ceiling for all text-level compression approaches.

## Key Findings

### Quantization (Deployed)

- **Hadamard+q4_0 is quality-neutral at production scale**: PPL increase of +0.017 on Qwen2.5-7B at 512 tokens. Needle-in-haystack: 9/9 at 1K/4K/16K on Coder-32B. Walsh-Hadamard rotation smooths outlier distributions before quantization via orthogonal transform that preserves norms while redistributing magnitude across dimensions. Production config: `-ctk q4_0 -ctv f16` for pure-attention models, `-ctk q4_0 -ctv q4_0` for hybrid SSM (validated at PPL 1.2466 vs f16 1.2510 on Q35 frontdoor). [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **q4_0 Key cache degrades at extended context on pure-attention models**: At 32K context, q4_0/q4_0 (both K and V quantized) produces garbage output on Qwen2.5-7B; q8_0/q4_0 remains correct. The safe production config uses q4_0 for Keys with Hadamard rotation and f16 for Values on pure-attention models. Hybrid SSM models with 75% recurrent layers absorb the quantization error (validated: PPL identical at 4K context). [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **Upstream auto-enables Hadamard rotation**: llama.cpp v3 upstream PR #21038 (`744c0c731`) auto-enables identical Walsh-Hadamard rotation when KV types are quantized. The `--kv-hadamard` flag from our production branch is superseded. The upstream implementation may be more optimized, potentially reducing the +9% wall time overhead observed at 32K context with dequant during prefill. [v3 rebuild handoff](../handoffs/completed/llama-cpp-v3-upstream-rebuild.md)

- **TurboQuant (TQ3) loses to Hadamard+q4_0 on CPU**: ikawrakow's full implementation on EPYC 9975 shows Hadamard+q4_0 at 1279 tok/s vs TQ3 at 573 tok/s -- 2.2x faster. Even with all four ecosystem fixes (norm correction, S=512 initial layers, fused dequant, 32-block format), TQ3 is slower on CPU due to codebook lookup overhead vs simple q4_0 dequant on AVX-512. TQ3 is on monitor-only status; revisit only if upstream merges natively with fused FA kernel. [TQ3 handoff](../handoffs/active/tq3-quantization-evaluation.md)

- **Hybrid buffer architecture is memory-negative**: The dual-cache design (kv_recent f16 + kv_old q4_0) allocates both at full context size, using MORE memory than a single f16 cache. The standard single-cache with quantized KV types is strictly better. Split attention (separate scoring for old and recent, concat, single softmax) works correctly at 5.2 t/s on 14.5K context but is unnecessary with the single-cache approach. Archived as research. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

### Compaction (Active -- L1-L4 Merged to Production)

- **Attention Matching achieves 5x zero-degradation validated on 3 models**: HighestAttnKeys-fast compaction uses three closed-form steps: RMS key selection, NNLS for per-token scalar biases (beta) that reproduce attention mass, and OLS for fitted values that reproduce attention output. Validated at 2x (cosine 1.000, universally lossless), 5x (0.906 average across layers), 10x (0.807). Layer-adaptive compression is the right strategy: 10x for early layers (1.000 cosine at layer 0), 5x for middle (0.878 at layer 14), 2x for deep (1.000 at layer 27). Combined effective ratio approximately 5x with near-lossless quality. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md), [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **Full native ggml implementation merged to production**: Three production commits: `81c9ad1ec` (L1-L4: beta injection via kq_mask, public API `llama_memory_set_beta()`, NNLS+OLS solvers, server endpoints), `80c72c0c6` (state format versioning for backward compat), `7784b3d9c` (L4b K-norm importance scoring for compact endpoint). Validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, and Qwen3.5-35B-SSM-hybrid at 5x compression with zero degradation. SSM-hybrid support preserves recurrent state tail bytes. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **AM's decode-side change is minimal**: `score[j] += beta[j]` in the attention inner loop -- one `_mm512_add_ps` per 16 positions, negligible vs memory-bandwidth-bound attention. Plus KV metadata for logical vs physical length. Flash attention path required disabling for compacted slots (Phase 1); CPU flash kernel modification deferred to Phase 2. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **CPU timing is well within budget**: NNLS approximately 10ms, OLS approximately 13ms at T=4096 on EPYC. Small dense matrices fit in L2 cache. The 2.2s H200 GPU timing is likely dominated by CUDA kernel launch overhead. CPU may actually be faster for these small linear algebra subproblems. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **Online compaction enables effective context extension**: 2048 physical KV + 6 repeated 50% compactions = 8192 effective context = 13/30 on AIME, matching uncompacted 8192. Reasoning state preserved across consecutive compactions. This pattern (compact-in-place during generation) composes with all other layers: if live KV is quantized + block-masked, AM compaction dequantizes for scoring, fits compact (K,beta,V), re-quantizes. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **Latent Briefing is broken -- do NOT use as reference**: Code audit revealed PGD beta optimization is a no-op (optimizes against kept-only attention pattern, not full-cache pattern -- the target variable is created but never referenced in the loss). Ridge C2 correction ignores V_full. "Cross-model KV transfer" is standard text-passing via Anthropic API. The AM paper is the correct formalization. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **Still introduces the missing third compaction category -- amortized synthesis**: Compaction methods now split three ways: token *selection* (keep/evict originals), *per-context synthesis* (optimize a compact cache per input, e.g. Cartridges), and *amortized synthesis* (Still). Still trains a small per-layer Perceiver -- learned latent queries cross-attending the live KV cache -- **once** against a frozen base model via forward-KL distillation from a full-context teacher, then synthesizes compact K/V in a **single forward pass** (not gradient descent per context). This combines selection-method lightness with synthesis-method expressiveness. The trained compactor transfers across model scales (4B-32B) and attention architectures unmodified, and runs iteratively/chunked for streaming. Position-free placement via inverse-RoPE -> latent positioning -> re-rotation. Reported: beats KV-Distill by 8-22 points in 16/18 RULER cells across 8x-200x compression and 8k-128k context; 256k @100x = 40.7% QuALITY. No public code or released compactor weights as of 2026-06-05 -- gated on a one-time GPU distillation pass per base model. [intake-708] Still

- **Our deployed default compactor is Expected-Attention (TriAttention), NOT Attention-Matching**: Despite the AM native ggml work being merged, the production default compactor on the live stack is Expected-Attention (the TriAttention selection scorer); AM K-norm is the *legacy fallback*. Crucially, even AM is selection+beta (keep a key subset, add fitted bias/values), **not synthesis** -- so there is no deployed amortized-synthesis path against which Still could be benchmarked today. The AM handoff/experiment notes still cite the `production-consolidated-v3` branch label, but production has since rebased to v5 (functionality carried forward across rebases). [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

### Selection (Active -- Scaffold Ready)

- **TriAttention's trigonometric scoring is the strongest decode-phase method**: On AIME25 at 2048 KV budget: TriAttention 32.9%, SnapKV 20.0%, R-KV 17.5% (full attention: 40.8%). Q/K concentration is a real intrinsic model property: Mean Resultant Length R = 0.977-0.980 across 5 architectures including MLA with 940 heads. Calibration is robust -- works with 50K-960K tokens of any data, even "Google homepage HTML." Ablation validates the trig series: removing S_trig collapses AIME24 from 42.1% to 18.8% (-23.3pp). [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

- **Expected Attention is more practically deployable**: Flash Attention compatible (SnapKV and H2O require materializing the full attention matrix -- incompatible with Flash Attention). Explicitly orthogonal to quantization (validated claim: "quantization methods orthogonal to Expected Attention... making it possible to integrate them"). GQA/MQA supported with per-head adaptive compression. KVPress library includes 20+ methods with standardized benchmarking and public HuggingFace leaderboard. RULER 4K accuracy: 94.7% at 50% compression vs SnapKV 55.7% (+39pp). [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

- **Selection vs compaction: AM subsumes selection at high ratios**: At 20x+, Attention Matching (latent-space construction with fitted biases and values) outperforms all token-selection baselines (H2O, SnapKV, PyramidKV, KVzip). At 5-10x, the gap narrows and selection may be sufficient and simpler (no attention biases needed). Selection and compaction are redundant to stack -- AM constructs better compact representations than keeping original tokens. The crossover point depends on model architecture. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **LongFlow's 11.8x headline is misleading**: Measures system-level throughput vs vanilla (no compression), not accuracy-matched like TriAttention's 2.5x. Scoring degrades under "abrupt distribution shifts (topic switches, tool-use interleaving, highly stochastic decoding)" -- exactly our orchestrator's workload pattern. Downgraded to LOW priority. [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

- **Quantization interaction is the critical unknown for selection**: Neither TriAttention nor Expected Attention tested on Hadamard-rotated q4_0-quantized K vectors. Hadamard preserves norms (orthogonal transform) but q4_0 introduces norm error. TriAttention scoring uses pre-RoPE centers (offline) and current K norms (online) -- the norm signal degrades under quantization. Expected Attention's Gaussian approximation may be more robust to quantization noise but has not been tested. [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

### Block Masking (Active -- Feasibility Confirmed)

- **Memento's dual information stream is the most important theoretical finding**: KV cache states computed while a reasoning block is visible carry implicit information beyond what the summary text captures. Recomputing memento KVs without block context: AIME24 drops from 66.1% to 50.8% (-15.3pp). Probing with injected 5-digit passcode: direct memento recovers at 60-70%, masked memento at 23-27% (vs 10% chance), signal concentrates in deeper layers (26.5% at layer 36 vs 10.8% at layer 4 for Qwen3-8B). Confirmed on toy transformer at 24.9% masked accuracy. This is **architectural, not learned**. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Text-level compression has a fundamental approximately 15pp ceiling vs KV-retaining approaches**: Any method that discards KV and keeps only text summaries (InftyThink, Accordion-Thinking, our context-folding) loses the implicit KV channel. This establishes Memento's KV-retaining block masking as strictly superior to text-level compression for reasoning tasks. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Accuracy gap is consistency, not capability**: Pass@64 Jaccard similarity between Base and Memento solved sets is 96.4%. The model can solve the same problems, just less reliably. Majority voting at k=3 recovers base accuracy without RL. Combining Memento KV savings with our short-m@k voting infrastructure yields 2-3x KV reduction at zero accuracy cost. Scale helps: gap narrows from -6.3pp at 8B to -3.5pp at 32B. MATH-500 is near-lossless (<1pp) across all scales. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Accordion-Thinking provides runtime fold/unfold toggle**: Same model, same weights, user chooses at request time between compressed (Fold, 3-4x throughput) and full (Unfold, max accuracy). After RL training, accuracy gap vanishes (Fold 52.7 macro vs Unfold 52.2). Maps directly to our difficulty routing: easy problems to Fold, hard to Unfold. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **InftyThink+ demonstrates RL-learned adaptive compression**: +21pp on AIME24 vs SFT baseline (largest single improvement in the cluster). Task+efficiency RL trades 3.4pp accuracy for 60-70% latency reduction. Key finding: after RL, internal summaries outperform external (GPT-4) summaries -- the model learns summary strategy coupled to its own reasoning. Implies our context-folding Phase 2 (external 7B summarizer) should eventually move summarization into the reasoning model itself. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **llama.cpp block masking uses existing API**: `llama_memory_seq_rm()` at `include/llama.h:733` provides the eviction primitive. Block boundaries tracked via special tokens (`<|block_start|>`, `<|block_end|>`, `<|summary_start|>`, `<|summary_end|>`). Freed cells are immediately reusable. Position gaps must NOT be closed with `seq_add` -- the dual information stream requires preserving original RoPE phases. Feasibility confirmed 2026-04-13. Test skeleton written. [Memento handoff](../handoffs/active/memento-block-reasoning-compression.md)

- **OpenMementos dataset available for fine-tuning**: 228K examples, 4.7 GB, MIT licensed. Approximately 9 blocks/response median, approximately 12K tokens/response. Two-stage LoRA training design: Stage 1 (format learning, full attention, 2 epochs), Stage 2 (compression learning, custom memento attention mask removing approximately 59% of causal positions, 1 epoch). CPU-feasible validation path: Qwen3-1.7B in approximately 54h. Production 32B requires GPU QLoRA. [Memento handoff](../handoffs/active/memento-block-reasoning-compression.md)

### Cross-Instance Sharing

- **KVCOMM eliminates redundant prefill across homogeneous worker pools**: When 3+ coder-32B instances share the same codebase context (10K-50K tokens), KVCOMM reduces 3 independent 50K-token prefills to approximately 1.3x one prefill. Anchor-based offset estimation works within same-model same-quant boundaries. Compounds with AM compaction: AM compresses shared context, KVCOMM shares the compressed result. Triple hard blocker for heterogeneous stack (Claude+Qwen3 at mixed quants), but valid for homogeneous NUMA pools. Open questions: q4_0 offset estimation untested, cross-NUMA IPC for anchor pool, AIME 8-11pp drop on hard reasoning. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

## Actionable for EPYC

- **Deployed**: Hadamard+q4_0 KV quantization (2-4x, production since `b51c905`, auto-enabled in v3 upstream via PR #21038)

- **Merged to production branch**: Attention Matching L1-L4+L4b -- native ggml NNLS+OLS, K-norm importance scoring, server endpoints (`set-beta`, `seq-rm`, `compact`), SSM-hybrid support. Three production commits on `production-consolidated-v3`

- **Autopilot integration complete (2026-04-14)**: `slot_compact` action dispatch wired into autopilot controller (`autopilot.py:812-849`). Controller can issue compaction commands to production slots, logs pre/post token counts, measures quality via `hybrid_eval()`. Slot memory visibility added: `_query_slot_memory()` queries `/slots` on primary production ports (8070-8084) each trial, showing per-slot context size in the controller prompt. Guideline: compact when any slot exceeds 4000 cached tokens. Validated parameters: keep_ratio=0.3, beta=0.5. Long-context validation (8K-32K production contexts) deferred to AR-3 -- current tests validated up to 2.7K tokens. [bulk-inference-campaign.md Package D]

- **Next validation steps**: P2 Coder-32B coding benchmarks (validates production deployment at scale), P3 comparison vs Expected Attention at 5x/10x/20x (determines whether selection or compaction is primary path at each ratio), P4 AM + Hadamard q4_0 stacking quality test (validates dual compression)

- **KVPress HF path infeasible on CPU; replanned as llama.cpp-first (2026-04-14)**: KVPress runs through HuggingFace transformers, not llama.cpp. On EPYC CPU, even 0.5B at 4K-16K context took >5 min/sample with no results; 7B consumed 65GB and projected hours/sample (~100x slower than llama.cpp on identical hardware). S4 (Expected Attention C++ port to ggml) promoted to critical path. The scorer is a per-layer function (mean/cov of pre-RoPE queries + Gaussian future prediction + V-norm weighting), not an architecture change. Eviction uses `llama_memory_seq_rm()` validated by Memento S1 (5/5 tests, 2026-04-14). Once the scorer runs in llama.cpp, S1's RULER benchmark can execute at production speed. S2 (TriAttention Q/K concentration) and S3 (selection+quantization stacking) depend on S4 completion

- **Memento S1 runtime validation PASSED (2026-04-14)**: Block masking primitive validated end-to-end on Qwen3-1.7B-Q8_0. 5/5 tests passed: basic block eviction, position gap semantics, generation after eviction (no attention corruption), multi-block iterative eviction (4x compression, 200->50 KV entries), and memory reuse. S2 LoRA training now unblocked. OpenMementos dataset downloaded, training design complete. CPU-feasible validation on 1.7B; production 32B requires GPU QLoRA

- **Priority ranking**:
  1. HIGH: Complete AM P2 benchmarks on Coder-32B (validates production deployment for highest-value model)
  2. HIGH: Implement Expected Attention scorer in llama.cpp (S4 — critical path; HF CPU path infeasible, enables S1/S2/S3 eval at production speed)
  3. MEDIUM: AM P4 dual compression test (AM + Hadamard q4_0 stacking -- validates the 8-40x combined promise)
  4. MEDIUM: Prototype llama.cpp block masking for Memento (builds on ISWA work and existing `llama_memory_seq_rm()`)
  5. LOW: KVCOMM for parallel worker pools (Phase F in dynamic-stack-concurrency, only relevant when running 3+ same-model instances)

## Open Questions

- Does Attention Matching maintain 5x quality on coding benchmarks (Coder-32B at production-length contexts)? Information-dense content degrades faster than narrative in the paper. Short-prompt P2 results (0.807 at 10x) may improve significantly at 32K+ context where AM has more attention structure to exploit
- Can Expected Attention and quantization stack without quality cliff? The paper's explicit orthogonality claim needs validation on our specific models with Hadamard rotation
- Does TriAttention's trigonometric scoring work on Hadamard-rotated q4_0 K vectors? Hadamard preserves norms but q4_0 introduces error -- the net effect on the Q/K concentration property is untested
- What is the real-world quality under triple-stack compression (quant + compaction + masking)? Each pair tested independently but three-way interaction is unknown and may be multiplicative in degradation
- Can Memento-style models be created via LoRA fine-tuning on OpenMementos with GGUF-quantized base models, or does quantization degrade the implicit KV information channel?
- At what compression ratio does AM compaction subsume selection? The handoff estimates 20x+ but the crossover depends on model architecture and context length
- Does the L4c true NNLS attention scoring (deferred -- requires graph modification to retain attention weights during inference) offer meaningful quality improvement over L4b K-norm approximation?
- Does Still's amortized-synthesis quality (RULER wins over KV-Distill) survive the CPU compute-overhead-vs-quality trade vs the deployed Expected-Attention compactor, and can the per-layer Perceiver run cheaply enough on EPYC during decode? Untestable until code/weights release for a served family (Qwen/Gemma) -- tracked as a GPU-CPT-gated watch item in [`summary-token-attention-readiness.md`](../handoffs/active/summary-token-attention-readiness.md)

## Updates — 2026-04-29 (PM)

Three architectural sub-quadratic-attention papers ingested in same-day batch (intake-502 + intake-506 + intake-507) sharing the same first-principle: **sequence-level compression through a tunable ratio**, complexity O(n/k) or O(L·k) instead of O(n²) — preserving linear KV growth but compressing semantic content per position.

- **Kwai Summary Attention (KSA, intake-502)** — Kuaishou OneRec, arxiv:2604.24432. Learnable summary tokens injected at chunk boundaries (default chunk size k=8). 3:1 KSA-to-Full layer ratio. **Persistent summary visibility** — all summary tokens always visible to text. Reports +5.81 RULER-128K vs Full (CPT setting), +16.60 (from-scratch); 2.5× KV cache reduction at 128K (7.5 GB vs Full 18.6 GB); decode 1.06× Full (only sub-quadratic baseline that does NOT lose decode speed in their comparison set). Composable with GQA/MLA: `1/k` × `g/h` ≈ 128× compression at h=128 d=128 g=8 k=8. Three-stage CPT distillation recipe (summary-token adaptation with MSE+KL + parameter annealing via λ schedule + sequence-length extension) makes Qwen3-4B-base retrofittable in 85B tokens. Open-source training scripts at github.com/Kuaishou-OneRec/KSA; no checkpoints yet.

- **DeepSeek Sparse Attention (DSA, intake-506)** — DeepSeek-V3.2, arxiv:2512.02556. Two-stage: **Lightning Indexer** (FP8 head-weighted scorer with block-64 quantized key cache) → top-k=2048 token selection → MLA forward pass on selected subset. Composition is orthogonal: MLA compresses per-token KV dim, DSA selects which tokens to attend. Reports V3.2-Exp ≈ V3.1-Terminus on GSM8K/GPQA-Diamond. **PR #21149 by fairydreaming is an active draft on llama.cpp upstream** (opened 2026-03-29, last commit 2026-04-28; CPU + CUDA + Vulkan backends working); author caveat that long-context speedup not yet realized (sparse path applies to token generation only, not prompt processing — separate follow-on PR flagged). 2-models-for-1 leverage: same DSA infrastructure unlocks GLM-5.1-555B-A14B simultaneously.

- **Gist Sparse Attention (GSA + H-GSA, intake-507)** — Stanford / Emily Fox, arxiv:2604.20920. Same gist-token primitive as KSA but distinct mechanism: hard top-k chunk selection at decode + **selective unfolding** restoring raw KV pairs for selected chunks (unselected chunks fully invisible). Bounded context size at decode = k·(1+L)+M. **Hierarchical H-GSA** (gist-of-gist) achieves log-linear decode complexity — only mechanism in this cluster scaling naturally to 1M+ context on 1.1 TB RAM headroom. Reports LongBench at 32× → 44.07 vs ActivationBeacon 38.30 (+5.77). Stage 1 CPT REQUIRED; tested on Qwen2-7B + Llama3.2-1B (no 30B+, no MoE, no RULER beyond passkey). Code at github.com/yuzhenmao/gist-sparse-attention.

**Mechanism comparison axis**: KSA = persistent summaries, soft compression, larger active context per query. GSA = hard top-k + unfolding, sharp compression, smaller active context. DSA = learned indexer for top-k, integrated rather than retrofit. KSA / GSA / DSA all REQUIRE pretraining or CPT — no retrofit path for our existing Qwen production stack. Compares against our deployed retrofit methods (Attention Matching compaction intake-351, Expected Attention selection intake-288) — the retrofit-vs-integrated trade-off becomes a research question worth testing once any of the architectural mechanisms ships in llama.cpp.

**Tracked at**: [`summary-token-attention-readiness.md`](../handoffs/active/summary-token-attention-readiness.md) (joint KSA + GSA readiness stub) and [`llama-cpp-dsa-contribution.md`](../handoffs/active/llama-cpp-dsa-contribution.md) (active PR #21149 tracker with three contribution sub-tracks).

**DSA fork-side status update (historical 2026-06-20; superseded by the 2026-07-17 closeout)**: pre-fix source had `LLM_ARCH_GLM_DSA` loading tensors and falling back to **dense MLA** (no Lightning Indexer, no sparse flash-attention path), so the blocker really was the DSA path, not storage. Experimental-v7 `3dee86a5a` now routes GLM through `llama_kv_cache_dsa` and the DeepSeek32 DSA graph. The remaining open work is sparse-compute profiling and quality, not cache/runtime wiring. [DSA handoff](../handoffs/active/llama-cpp-dsa-contribution.md)

- **GLM-5.2 current-source DSA cache/runtime wiring is closed (2026-07-17)**: experimental-v7 `3dee86a5a` routes `LLM_ARCH_GLM_DSA` through `llama_kv_cache_dsa`, aliases GLM to the DeepSeek32 DSA graph, and the current-source exact smoke returned `READY` with `Lightning Indexer enabled`. That closes the wiring prerequisite only; sparse-vs-dense attention classification, current-source long-context needle/coherence, and quality remain open. [llama-cpp-dsa-contribution.md](../handoffs/active/llama-cpp-dsa-contribution.md), [glm51-reap-cpu-evaluation.md](../handoffs/completed/glm51-reap-cpu-evaluation.md), [Progress 2026-07-17](../progress/2026-07/2026-07-17.md)

## Related Categories

- [Speculative Decoding](speculative-decoding.md) -- Speculative decoding increases KV pressure; KV compression enables larger speculation budgets. The verification wall on hybrid models makes KV optimization even more critical (speculation cannot help, so other levers matter more)
- [Quantization](quantization.md) -- Weight quantization (Q4_K_M) and KV quantization (Hadamard+q4_0) are orthogonal. KV quantization is the first deployed layer of the compression stack
- [MoE Optimization](moe-optimization.md) -- MoE models have different KV patterns than dense; MLA (Leanstral's DeepSeek V3 architecture) reduces KV cache independently of expert pruning via low-rank latent attention
- [Context Management](context-management.md) -- Context folding and session compaction are text-level compression; Memento's dual information stream shows KV-level approaches are strictly superior for reasoning

## Source References

- [KV Compaction Attention Matching Deep-Dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md) -- AM closed-form decomposition (NNLS+OLS), 50x compression on narrative QA, Latent Briefing code audit (broken corrections), KVCOMM analysis (valid for homogeneous pools), LRAgent rejection (LoRA-specific)
- [TriAttention KV Selection Deep-Dive](../research/deep-dives/triattention-kv-selection-cluster.md) -- Trigonometric scoring validated on 5 architectures, Expected Attention upgraded (Flash compatible, quantization orthogonal), LongFlow downgraded (topic-switch failure), In-Place TTT rejected (incompatible with GGUF)
- [Memento Iterative Reasoning Deep-Dive](../research/deep-dives/memento-iterative-reasoning-cluster.md) -- Dual information stream (15pp ceiling for text compression), Accordion fold/unfold toggle, InftyThink+ efficiency reward (+21pp AIME24), OpenMementos pipeline (228K MIT dataset), quad-stack analysis
- [AM Handoff](../handoffs/active/attention-matching-kv-compaction.md) -- L1-L4+L4b merged to production, P2 layer-adaptive results, server endpoints, SSM-hybrid support
- [TriAttention Handoff](../handoffs/active/triattention-kv-selection.md) -- KVPress scaffold, evaluation gates S1-S4, composability analysis with AM and Memento
- [Memento Handoff](../handoffs/active/memento-block-reasoning-compression.md) -- Block masking feasibility confirmed, llama.cpp API mapping, LoRA training design, OpenMementos downloaded
- [KV Cache Quantization Handoff](../handoffs/completed/kv-cache-quantization.md) -- Hadamard Phase 1 deployed, hybrid buffer archived, TurboQuant/PolarQuant/QJL abandoned, split attention working but unnecessary
- [TQ3 Monitor Handoff](../handoffs/active/tq3-quantization-evaluation.md) -- TQ3_1S on monitor-only, PR #21038 Hadamard auto-rotation, PR #21089 CPU TurboQuant KV cache
- [intake-191](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/) TurboQuant -- Extreme KV cache compression (3-4 bit with Hadamard)
- [intake-192](https://arxiv.org/abs/2502.02617) PolarQuant -- Polar transformation for KV quantization
- [intake-193](https://arxiv.org/abs/2406.03482) QJL -- 1-bit quantized JL transform for KV cache, zero overhead claim
- [intake-256](https://arxiv.org/abs/2604.01178) Multiscreen Attention -- Screening architecture replacing softmax attention
- [intake-284](https://arxiv.org/abs/2604.04921) TriAttention paper -- Trigonometric KV scoring, Song Han lab
- [intake-287](https://arxiv.org/abs/2603.11504) LongFlow -- Attention-weighted value norm scoring (downgraded)
- [intake-288](https://arxiv.org/abs/2510.00636) Expected Attention paper -- Gaussian MGF scoring, KVPress library
- [intake-289](https://github.com/microsoft/memento) Memento paper -- Dual KV stream, block masking, Microsoft Research
- [intake-292](https://arxiv.org/abs/2503.06692) InftyThink (ICLR 2026) -- Iterative reasoning compression
- [intake-293](https://arxiv.org/abs/2602.06960) InftyThink+ -- RL-learned adaptive compression
- [intake-294](https://arxiv.org/abs/2602.03249) Accordion-Thinking -- Fold/unfold runtime toggle
- [intake-350](https://github.com/CuriousCaliBoi/latent-briefing) Latent Briefing -- Broken (PGD no-op, Ridge no-op, do NOT use)
- [intake-351](https://arxiv.org/abs/2602.16284) Attention Matching paper (2602.16284) -- Closed-form KV compaction, MIT
- [intake-352](https://arxiv.org/abs/2510.12872) KVCOMM (NeurIPS'25) -- Cross-context KV sharing for homogeneous pools
- [intake-708](https://www.arxiv.org/html/2606.07878v1) Still: Amortized KV Cache Compaction in a Single Forward Pass (arXiv 2606.07878) -- per-layer Perceiver, forward-KL distillation, amortized synthesis (the third compaction category), position-free via inverse-RoPE; no public code as of 2026-06-05

## KV admission / eviction cluster + cluster-wide gate (2026-05-19)

Five May 2026 papers spanning write-time admission, read-time eviction, per-head budget allocation, workflow-aware residency, and reasoning-domain oracle distillation. Deep-dive verdict: **PBKV is the strongest near-term EPYC fit; SP-KV is empirically refuted; landing a StreamingLLM baseline first is a cluster-wide gate for prioritization**.

**SP-KV** (intake-538, arxiv:2605.14037, FAIR — Jégou/Douze/Yih) — jointly trained lightweight utility predictor decides at write time whether each KV pair is admitted to the long-term cache; recent-window keeps short-range pairs locally available. 3-10× KV cache reduction with little/no validation-loss degradation. **Tier-2b refutation**: arxiv:2601.14279 (Steele) shows a 1.7M-param learned scorer (SIP) fails to beat trivial position-based heuristics (keep first 4 + last N) across 5 seeds × 4 retention levels × 3 tasks. SP-KV is exactly the KV-only, query-agnostic write-time scorer Steele targets. Independent corroboration from ForesightKV (below): pure learned predictor degrades LM loss on low-entropy tokens, hence the two-stage Supervised+GRPO recipe.

**KVP** (intake-551, arxiv:2602.10238, Moschella/Manduchi/Sener) — per-head RL agents trained offline on pre-computed generation traces using only K/V vectors. No LLM weight modification. Generalizes zero-shot to longer contexts and unseen tasks. The ONLY cluster paper that explicitly compares to StreamingLLM (per-head specialization is the axis SP-KV doesn't exploit).

**LU-KV** (intake-552, arxiv:2602.08585, Tang et al.) — global combinatorial optimization for per-head budget allocation via convex-hull relaxation + marginal-utility greedy solver. 80% KV reduction at minimal performance degradation on LongBench/RULER. **Static profile after offline training** — fits our frozen-weights constraint. Strongest frozen-weights attention-kernel candidate.

**ForesightKV** (intake-553, arxiv:2602.03203, Dong et al.) — distills a "Golden Eviction" oracle (future-attention scores) via supervised Pairwise-Ranking, then GRPO RL on LM loss. Outperforms prior eviction methods at half the cache budget on reasoning benchmarks (AIME 2024/2025). Requires LLM fine-tuning — collides with frozen-quant constraint until DGX Spark lands.

**PBKV** (intake-554, arxiv:2605.06472, Zheng et al., CC-BY 4.0) — **standout for EPYC orchestrator**. Operates at the **workflow/orchestrator residency layer**, not the attention kernel. History-conditioned next-agent-invocation predictor drives KV residency decisions. 1.85× over LRU on dynamic workflows, 1.26× over KVFlow on static. Maps directly onto frontdoor → coder/worker hand-off pattern where shared long prompts pay BW-bound re-prefill cost. **No fine-tuning needed.** Requires tiny next-agent predictor + llama.cpp prefix-cache hooks (soft-depends on RadixAttention prefix-tree work in `llama-cpp-fork-rebase.md`).

**KVFlow** (intake-1196#01, arXiv:2507.07400, Pan et al., UCSD + AWS) — **the ORIGIN of workflow-aware KV
residency, and the paper PBKV's 1.26× is measured against.** Recorded here in its own right because our
index previously carried it only as PBKV's denominator, which inverted the reading for our own use case.
Peer-reviewed at **NeurIPS 2025**, with an Apache-2.0 implementation released. An Agent Step Graph yields a
per-agent *steps-to-execution* value propagated into the KV radix tree: the value lands on the last node of
each agent's fixed prompt, internal nodes take the **minimum** across children, dynamic suffixes always get
highest eviction priority, and conflicts at nodes shared between concurrent workflows resolve to the most
conservative priority.

Three things to carry, all from a source-level dive:

- **The camera-ready prices the portable half at 1.11×.** Its optimization breakdown — present only in the
  NeurIPS version — gives workflow-aware eviction *alone* an average **1.11×**; the jump to 1.29× comes from
  overlapped prefetching, which does **not** port to our stack (llama-server slot save/restore runs on the
  shared task loop and a failed restore is destructive). **1.11× is the honest ceiling for us.**
- **An arXiv version check is not a version check.** arXiv has exactly one version of this paper, so a
  freshness check passes while the version of record diverges underneath it. The NeurIPS camera-ready
  deleted a testbed, added a baseline and a limitations section, and changed the body's headline numbers.
  For any paper with a venue, fetch the proceedings separately.
- **PBKV's 1.26× is on STATIC workflows — KVFlow's design centre.** A 1.26× increment there means KVFlow
  retains most of the available gain on *declared* topologies, which is exactly what our delegation path is
  (`compute_waves()` already computes a cycle-checked wave index that **is** a steps-to-execution value).
  Filing KVFlow as "beaten" inverts the reading for the one workload where we would actually use it. Note
  also the asymmetry in what our index recorded: PBKV is an undived preprint, KVFlow is peer-reviewed.

**Do not quote 1.83× or 2.19×** as the value of workflow-aware eviction: 1.83× is the full system on
hardware we do not have and its stated configuration was removed from the version of record, and 2.19× is
an arithmetic ratio (1.25/0.57) against a HiCache version that no longer exists.

**Cluster-wide gate** — [`streaming-llm-baseline.md`](../handoffs/active/streaming-llm-baseline.md) (master P#45 MED): land a clean sink + sliding-window baseline in `epyc-llama` to measure the **easy-floor** any KV reduction method must beat. Of the 5 papers above, only KVP explicitly compares to StreamingLLM. Without an internal floor, LU-KV / KVP / ForesightKV gain rankings are unanchored against the simplest competing technique. Gate criteria flip cluster prioritization: if StreamingLLM at 50% budget preserves ≥95% accuracy on representative workloads, **demote** attention-kernel methods (LU-KV/KVP/ForesightKV) — their incremental gain over the floor is too small to justify kernel work. PBKV stays prioritized because it operates at the orchestrator layer and **composes with** sink+window rather than replacing it.

**Sources**: [intake-538](https://arxiv.org/abs/2605.14037) SP-KV · [intake-551](https://arxiv.org/abs/2602.10238) KVP · [intake-552](https://arxiv.org/abs/2602.08585) LU-KV · [intake-553](https://arxiv.org/abs/2602.03203) ForesightKV · [intake-554](https://arxiv.org/abs/2605.06472) PBKV · [Steele falsification](https://arxiv.org/abs/2601.14279) · [Deep-dive](../research/deep-dives/2026-05-19-kv-admission-cluster.md) · [StreamingLLM baseline gate](../handoffs/active/streaming-llm-baseline.md) · [intake-1196#record](https://arxiv.org/abs/2507.07400) KVFlow (NeurIPS 2025; cite the proceedings, not the preprint) · [prefix-cache ownership + KV rows](../handoffs/active/attention-matching-kv-compaction.md)

## Per-slot context is a hard split, and "safer KV quant" can cost more memory (2026-08-03)

Two measured corrections that change how KV budgets are reasoned about on this fleet.

**`-c` is not what a request gets.** llama.cpp carves the KV cache into `-np` fixed slots at launch,
so the effective per-request limit is `-c / -np`. A single stream does **not** grow into unused slots
on this build (no unified KV cache), and overflow is a hard `HTTP 400
exceed_context_size_error`, never a queue and never a reroute. Verified on three live shapes, with
the server reporting its own limit:

| `-np` | `-c` | c/np | prompt sent | result |
|---:|---:|---:|---:|---|
| 16 | 262144 | 16,384 | 29,121 | 400, `n_ctx=16384` |
| 4 | 262144 | 65,536 | 116,501 | 400, `n_ctx=65536` |
| 8 | 65536 | 8,192 | 14,561 | 400, `n_ctx=8192` |

> **Correction (2026-09-24):** "no unified KV cache" is wrong about the build. The binary supports unified KV
> (`--kv-unified`; it is even the server's own default when `-np` is absent). The fleet ran split because the
> launcher always passes an explicit `-np`, which leaves `kv_unified = false`. The per-slot `-c / -np` limits in
> the table above are correct for how the fleet was launched. See the 2026-09-24 update at the top of this page.

Consequence: a role with heterogeneous instances has heterogeneous *capability*. The same request
succeeded or failed depending only on which frontdoor instance took it, because `:8070` (`-np 16`)
offered 16,384 tokens while `:8080` (`-np 4`) offered 65,536.

**The safe pure-attention KV config can be a memory REGRESSION.** For a model at 260 KiB/token f16
(split evenly K/V):

| config | K | V | KiB/token |
|---|---:|---:|---:|
| f16 / f16 | 130 | 130 | 260 |
| q8_0 / q8_0 | 65 | 65 | **130** |
| q4_0 / f16 | 32.5 | 130 | **162.5** |
| q4_0 / q4_0 | 32.5 | 32.5 | 65 |

`-ctk q4_0 -ctv f16` is the documented safe production config for pure-attention models, and it uses
**more** memory than `q8_0/q8_0` — quantising K hard while leaving V at f16 costs more than
quantising both moderately. On a VRAM-constrained card the memory-optimal *safe* point is
`q8_0/q8_0`, not the "more aggressive" asymmetric config. Only `q4_0/q4_0` saves further, and that is
the config that produces garbage at 32K on pure-attention models — so the saving is gated on
architecture, not on willingness to trade quality.

_Sources: `progress/2026-08/2026-08-03.md`; `handoffs/active/autopilot-continuous-optimization.md`;
`handoffs/completed/kv-cache-quantization.md`; live probes of `:8070`/`:8080`/`:8083` on
production-consolidated-v8._

## Compiled Update — 2026-08-22: the KV-quant program closed because V-dequant, not K, is the CPU cost — and every exotic lost a fair rematch

**Confidence: verified** — everything below is landed, measured and decided inside the COMPLETED
[`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) handoff (closed 2026-03-28: Hadamard Phase 1
cherry-picked to production as `b51c905` on `production-consolidated-v2`, 10 files / +141 lines, later superseded by upstream
PR #21038 auto-rotation; TurboQuant / PolarQuant / QJL / hybrid buffer ABANDONED, each on a measured gate, not by fiat). This
pass compiles the closure fine-structure the page never carried: the headline results (Hadamard+q4_0 quality-neutral, hybrid
buffer memory-negative, the 2.2× ikawrakow speed confirmation) were compiled long ago and are not repeated here.

### V dequantization is the ENTIRE CPU flash-attention prefill cost; K dequantization is free

The page has so far motivated the asymmetric production config (`-ctk q4_0 -ctv f16` on pure-attention models) purely as a
*quality* margin. The handoff's 2026-03-28 root-cause section establishes it is equally a **speed** decision, with a clean
4-config isolation on Coder-32B Q4_K_M at 4K context:

| config | time/chunk | vs f16/f16 | reading |
|---|---:|---:|---|
| f16 / f16 | 37.91 s | baseline | — |
| **q4_0 / f16** | **37.42 s** | **−1%** | K dequant is FREE — bandwidth saving offsets cost |
| q8_0 / f16 | 40.57 s | +7% | q8_0 K simply reads more bytes than q4_0 |
| q8_0 / q4_0 | 64.87 s | **+71%** | **V dequant is the entire bottleneck** |

Mechanism: the K path runs a fused `kq_vec_dot` (dequant+dot in one pass) while the V path runs `v_to_float` → materialized
f32 buffer → `vec_mad_f32`; f16 V instead uses the native single-pass `ggml_vec_mad_f16`. The Phase-0 sweep shows the same
thing at scale — Coder-32B 16K prefill: f16/f16 **111.1** t/s, q4_0/q4_0 46.6, q8_0/q4_0 48.9, **q8_0/q8_0 34.0 t/s
(3.3× slower)** — while *decode* is unaffected in every config (~8.5–9.5 t/s across all cells; at batch-1 the KV read is
tiny next to ~18 GB of weight reads). On the hybrid 35B-A3B (25% attention layers) KV quantization is entirely free at
4K–65K, all configs within noise: the SSM layers amortize the dequant away.

**Reconciliation with the 2026-08-03 section above**: that section is correct that `q8_0/q8_0` is the *memory*-optimal safe
point (130 vs 162.5 KiB/token) — but on the CPU flash-attention path it is also the **worst prefill config measured**,
because it pays V-dequant on every tile, while the "memory-regressive" `q4_0/f16` is prefill-free (−1%). The two sections
answer different objectives (VRAM ceiling vs CPU prefill throughput); neither dominates, and a config choice must name which
axis it is optimizing. The 2026-08-14 GPU falsification on the [Quantization](quantization.md) page (KV-quant −16.7%/−6.9%
at 64k) is the same cast-cost mechanism showing up on the other substrate.

### Hadamard's isolated contribution, quantified — and the exotics' exact causes of death

**Hadamard rotation closes 70% of the bare-q4_0 quality gap.** The page carries the +0.017 endpoint but never the
comparison that prices the rotation itself (Coder-32B, 50 chunks, n_ctx=512): q4_0/q4_0 *plain* is **+0.055** PPL vs f16;
q4_0/q4_0 **+ Hadamard is +0.017** (3.56× K compression); q8_0/q4_0 + Hadamard is **−0.010 — quality-neutral** at 2.46×;
throughput overhead at 4K is zero (11.58 vs 11.45 t/s, within noise).

**TurboQuant was abandoned on a fair test, after the handoff itself flagged its first gate as unfair.** The original
decision gate tested one of four ecosystem fixes (norm correction only) on Qwen2.5-7B — squarely inside TQ3's measured
failure zone, since TQ3 quality is **model-size dependent** (Qwen3-0.6B: PPL **1216** vs f16 13.51, catastrophic; 8B: worse
than Hadamard+q4_0; 35B+: approaches f16 — head_dim=128 only gaussianizes with enough coordinates). The handoff recorded
"why we stopped too early", then re-ran fairly: **Coder-32B with norm correction still lost — TQ3 +5.9% PPL (1.4676) vs
q4_0's +0.001% (1.3875)** — and only then declared ABANDONED. Norm correction itself is real (77% gap reduction on 7B, PPL
9.017 → 2.13; beats q8_0 by 1.17% in spiritbuun's CUDA fork) but insufficient. This is the closure discipline worth copying:
the verdict survives because the gate's own weakness was found and removed before the decision was made final.

**QJL died on arithmetic, not implementation.** The custom XNOR+popcount attention kernel worked mechanically, but the
sign-bit estimator at S=256, d=128 has **SNR ≈ 1.13** — noise ≈ signal for the small Q·K scores that dominate a PPL
aggregate (PPL ~15–16K, unusable). Adding the paper's top-8 outlier correction lifts effective storage to ~6 bits/element,
**at which point plain q8_0 (8 bits, trivial) wins on quality-per-complexity** — the compression advantage evaporates
exactly when the method starts working. The paper's remaining viability path is a full-precision recency buffer for the
most-attended recent tokens — i.e. the hybrid-precision buffer this handoff independently built and measured as
memory-negative. PolarQuant's +0.229 PPL at 3.1 effective bits completes the set.

### Residual validated facts worth keeping on the record

- **Spec-decode composes with quantized KV**: speculative decoding + q8_0/q4_0 measured **19.15 t/s (+3.3% vs f16)** on
  Coder-32B — the R9 interaction risk closed positive, not merely neutral.
- **A standing small-GQA hazard**: q4_0 K on Qwen2.5-7B-f16 (4 KV heads, `n_embd_k_gqa=512`) produces PPL 2642 (garbage) on
  BOTH experimental and production binaries while q8_0 K is fine; all production models (8+ KV heads) are unaffected; root
  cause never found. Any future ≤4-KV-head model must re-run the q4_0-K gate before inheriting the production config.
- **Ecosystem bug watch-list for anyone touching WHT/KV code**: WHT normalization must be `1/sqrt(block)` not `1/block`
  (garbage PPL otherwise); store V non-transposed and transpose in-graph (block-quant crash otherwise); apply WHT during
  quantization (`set_rows`), never graph-side (PPL 23.5 vs 6.2); CPU dequant targets F32 only.
- **Reconciliation — the 2026-07-20 monitor row above is retired**: upstream PR #21089 (TBQ3_0/TBQ4_0 CPU TurboQuant KV),
  listed above as "remain open/monitor" and as an Open Question, was **CLOSED UNMERGED upstream on 2026-06-02** (GitHub API:
  `state closed`, `merged false`, verified 2026-07-29, re-verified 2026-08-21). No TBQ code entered the local tree. The
  question "does #21089 merge and beat Hadamard+q4_0?" is answered: no, and there is nothing left to monitor on that PR.

### Source References

- [`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) — the closed handoff: V-dequant root-cause table, Phase-0/1/3b/3c results, TQ3 model-size dependence and fair 32B retest, QJL SNR post-mortem, spec-decode validation, the 4-KV-head q4_0-K bug.
- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — the verified PR #21089 closed-unmerged state (2026-08-21 re-check) that retires this page's 2026-07-20 monitor row.
- [llama.cpp issue #20977](https://github.com/ggml-org/llama.cpp/issues/20977) — the upstream TurboQuant feature request the revisit criteria were pinned to (cited by the handoff).
- [ik_llama.cpp issue #1509](https://github.com/ikawrakow/ik_llama.cpp/issues/1509) — ikawrakow's independent EPYC 9975 confirmation runs (Hadamard+q4_0 better quality AND 2.2× faster than TQ3), the external anchor for the abandonment.
- [intake-193](https://arxiv.org/abs/2406.03482) QJL — the paper whose S=512 / recency-buffer requirements the SNR post-mortem quantifies against our S=256 implementation.

## Compiled Update — 2026-08-23: the orchestrator prefix-cache path is owned, its three latent defects fixed, and its measurement plan filed

**Confidence: verified** — committed orchestrator fixes with regression tests, read-only artifact archaeology on the slot-save path, and the closed KV-5 row whose wiki correction was already compiled in this page's 2026-05-19 section (not restated below, only pointed to).

### KV-5 closed 2026-08-20 — the KVFlow correction is already on this page

The KV-5 row ("correct `wiki/kv-cache.md`") was closed in the 2026-08-20 wrap-up wiki sweep: KVFlow is recorded above in the 2026-05-19 section as the **ORIGIN of workflow-aware KV residency** — NeurIPS 2025 venue, its own 1.11× eviction-only ablation as the honest portable ceiling, the arXiv-version-check trap, and the PBKV-1.26×-is-on-static-workflows reading. Nothing new to add; the pointer is kept so the row's closure is traceable. [attention-matching-kv-compaction.md](../handoffs/active/attention-matching-kv-compaction.md) §KV-5, commit `508eaeb0`.

### The ownership gap is closed: the prefix-cache path now has an owner

No ACTIVE handoff owned the orchestrator prefix-cache path. The original owner, [`radix-attention.md`](../handoffs/archived/radix-attention.md), is **archived "VERIFIED 2026-01-09"** with its Next Steps stopping at *"Integration testing with live llama-server"* — the integration was never done. `repl-turn-efficiency.md` touched `PrefixRouter` only incidentally. The attention-matching handoff adopted the rows (filed there because nothing else owned them); re-home if a better owner appears.

### Three latent defect fixes (KV-0a/b/c, committed 2026-08-20) — all three were silently wrong in production

- **KV-0a — every KV slot save was failing.** `prefix_cache.py` built the filename with `os.path.join(...)`, producing a `/`-containing string that llama-server rejects via `fs_validate_filename(allow_subdirs=false)` before it concatenates `--slot-save-path`. Proof it never worked: the 75 retained slot artifacts on disk are **all** `kv_migrate_*` from the sibling `concurrency_aware.py` path, with **zero** `slot_<id>_<hash>.bin` files anywhere. Two compounding defects fixed alongside: the restore path did a **client-side** `os.path.exists()` on a **server-side** filename, and both backend methods caught `httpx.RequestError`, which does **not** cover `HTTPStatusError` — so a 4xx propagated instead of returning `False` as documented. Fixed by emitting a bare filename (`_slot_state_filename`, mirroring `concurrency_aware._slot_filename`).
- **KV-0b — roles sharing one llama-server were evicting each other, unobservably.** Under `shared_with`, several roles resolve to one physical server, but the legacy loop built a **separate `PrefixRouter` per role**, each allocating `id_slot` in `[0, num_slots)` from its own private LRU — so two roles both emitted `id_slot=0` and silently clobbered each other. Now one router per physical URL (`_router_for`), matching the shape the fleet layer already had. 3 regression tests added.
- **KV-0c — `radix_cache.py` deleted** (480 lines + shim). Verified dead: its only two importers were the file importing itself. It also carried an unexercised stale-slot bug and a docstring claiming path compression it did not implement. The 20 tests that exercised the unwired module went with it — green tests over dead code manufacture exactly the false confidence this work exists to avoid.

### The measurement plan (KV-1..KV-4, KV-6) — mostly zero-inference, all from existing logs or one-line changes

- **KV-1 (gates everything below): count DISTINCT hot prefixes per window against resolved slot count, per role and per shared server, from existing logs. ZERO INFERENCE.** Production `num_slots` is **2**; `coder_primary` and `coder_escalation` both declare `slots: 1` — **at slots=1 there is no eviction order to improve**, and at 2 it is a coin flip. The row was named in two consecutive passes with an unchanged blocker — by the recurrence rule that is proof it was never blocked. Do it before anything else here.
- **KV-2: pass `role` and `session_id` into `PrefixRouter.get_slot_for_prompt`.** Both are already present at the call site (`model_server.py:91` requires `role`; `inference.py:755-767` attaches the session id) and the router receives **only prompt text** — the router is discarding for free the identity signal KVFlow had to invent a client-ID scheme to recover.
- **KV-3: evaluate llama.cpp's NATIVE token-level LCP slot selection.** It is strictly better than a 256-char SHA-256 exact match, already shipped, and currently **overridden** rather than off: `slot_prompt_similarity` defaults to `0.1f`, but our explicit `id_slot` takes tier-one priority ahead of it (`server-context.cpp:1541` before `:1549`). Config + call-site change, no kernel work. **Gated on KV-1 and on the shared-router fix having landed.** Note our Python hit-rate counter is a proxy for a quantity it does not measure — `n_past` is decided in C++.
- **KV-4: IF KV-1 shows working set > slot count, THEN consider workflow-aware eviction** — replace the LRU victim choice with an argmax over steps-to-execution, sourced from the delegation DAG that already exists (`parallel_step_executor.py:75` `compute_waves()` — the wave index **is** a steps-to-execution value, already cycle-checked; `routes/delegate.py:86-98` enumerates the whole plan at `dry_run=True` for zero LLM calls). **Ceiling recorded on the row: 1.11×** — KVFlow's own eviction-only ablation; the other 1.18× comes from prefetching we cannot port (llama-server slot restore is on the shared task loop and a failed restore is destructive). **NOT the RLM tree and NOT the autopilot loop** — neither materialises children in advance.
- **KV-6 (filed 2026-08-20): measure `canonicalize_prompt` before optimising anything downstream of it.** It makes **SEVEN full-length passes** (3 string scans + 4 `re.sub`) over prompts of tens of KB and then **discards everything past char 256**. It has NEVER been measured: grepping both prefix-cache files for timing primitives returns 3 hits, all docstring prose, zero code. Cheap to instrument, and it may dominate the routing cost the rest of the rows are trying to improve.

### Source References (2026-08-23)

- [attention-matching-kv-compaction.md](../handoffs/active/attention-matching-kv-compaction.md) — the ownership filing, the KV-0a/b/c fixes with their commit record, the KV-1..KV-6 rows, and the KV-5 closure
- [progress/2026-08/2026-08-20-research-intake.md](../progress/2026-08/2026-08-20-research-intake.md) — the intake round that surfaced the prefix-cache findings (KVFlow dive, SGLang Rust tree-core cluster)
- [radix-attention.md](../handoffs/archived/radix-attention.md) — the archived original owner of the prefix-cache path, whose integration step was never done
- Commits `508eaeb0` (KV-5 wiki close) and `c75a2f68` (KV-0a/b/c checkbox record + KV-6 filing) on this repo

---

## Compiled Update — 2026-08-23 (evening): KIVI's "primary quality gap" was never a gap; the real gap is an instrument gap

**Confidence: verified** — the KIVI correction is a read of `llama-kv-cache.cpp` / `llama-context.cpp` at frozen v9 against arXiv:2402.02750 v2 in full; the granularity correction reads the alignment-collapse study (arXiv 2606.09864) against our own layout; the monitoring gates G2-G5 are filed, not run.

### The KIVI "per-channel K / per-token V" gap is closed as a misread — all three load-bearing parts are wrong

The completed KV-quant handoff had claimed llama.cpp's symmetric block quantization leaves KIVI's per-channel-K / per-token-V unimplemented ("the primary quality gap"). The Stage-2b dive (arXiv:2402.02750 v2, read in full) shows that claim wrong on all three parts:

1. **Per-token V is already implemented, and structurally unavoidable.** `llama-kv-cache.cpp:231-232` allocates K and V with dim0 = channels, dim1 = tokens, so a 32-element q4_0/q8_0 block spans 32 contiguous channels *within one token* — exactly KIVI's per-token grouping at G=32. And quantized V forces flash-attention (`llama-context.cpp:3557` refuses to start otherwise), which sets `v_trans = false` — **our quantized V can never be on KIVI's bad axis.**
2. **Per-channel K is outside KIVI's demonstrated scope.** KIVI's own OB 1 says per-token quantization of *both* caches maintains accuracy at INT4; the axis asymmetry is established **only at 2 bits**, and we never run 2-bit KV.
3. **We solve the key-outlier problem a different way.** The orthonormal self-inverse Walsh-Hadamard rotation (`llama-kv-cache.cpp:319-336`) mixes across head channels — the exact dimension KIVI's outliers live on. RotateKV (arXiv 2501.16383, no author overlap) uses per-token keys plus rotation at 2 bits and states verbatim it "offers superior outlier management compared to per-channel approaches".

The one residual difference is real and cheap to test: KIVI's quantizer is **asymmetric** (zero-point + scale) where q4_0/q8_0 are symmetric — but q4_1/q5_1 are supported asymmetric KV types, so it is a flag, not a code change; a rotated distribution is near zero-mean, which predicts the asymmetric quantizer buys nothing (falsifiable in one short A/B).

**THE REAL GAP IS AN INSTRUMENT GAP, NOT AN IMPLEMENTATION ONE.** KIVI reports no perplexity at all and rejects single-decode-step metrics; its own data show why — on Llama-2-7B the same 2-bit damage costs CoQA 7% but collapses GSM8K by 57% (13.50 → 5.76). **Our entire first-party quality case for quantized KV is perplexity plus needle-in-a-haystack — precisely the instrument class that survives multi-step damage. No GSM8K-class generation eval has ever been run against quantized KV in this repo** (gate G3 in `tq3-quantization-evaluation.md`).

### The dual-cache conclusion is REFRAMED: a capacity argument applied to a bandwidth problem

The completed handoff's "dual cache = more bytes resident = wrong" conclusion does not generalise the way it has been read. It is sound only when both copies sit in the **same** memory tier and the cheap copy is **dequantized on the read path** — ours did both, which is why it lost (the ~30% gen-speed gap is the `q4_0 → f16` cast on every decode token: a *dequantization* cost, not a *capacity* cost). **A dual-cache design whose second copy lives in a cheaper tier (host DDR5, slower NUMA node) and is never dequantized into the attention hot path is a different design, not refuted by anything measured here.** Same-tier plus dequantize-on-read is memory-negative AND bandwidth-negative; that is the narrow, citable claim. Do not cite the paragraph to close a tiering proposal.

### Granularity correction — we are FINER than the published mitigation, on the OPPOSITE axis from KIVI

Two facts keep being conflated because both are called "grouping": (1) **granularity** — ours is group-**32** per token (with `-fa 1`, blocks run along the channel dimension, dim0 = channels / dim1 = tokens), while the alignment-collapse study (arXiv 2606.09864) *recommends* Group-**64** as a mitigation; we are already finer than its remedy, by default, everywhere, so **its headline damage figures are a pessimistic bound for us, not a matched estimate**; (2) **axis** — KIVI's prescription is per-channel for K; ours is per-token for both, and quantized V is *structurally incapable* of landing on KIVI's bad axis. Same word "group", orthogonal dimension. Any transfer of a third-party grouping-damage number to this stack must state which axis the grouping runs along (gates G4/G5 in `tq3-quantization-evaluation.md` replace transfers with our own numbers).

### The 2026-08-23 KV-quant monitoring gates (filed, not run — both compute planes were held elsewhere)

- **G2 — measure our actual KV outlier ratio** on the 10 full-attention layers only (a quarter of the frontdoor's 40 layers by construction; report as such): capture K after QK-norm and after RoPE, V at cache-write, ~200 prompts; report per layer and per head, K and V separately, max/median and max/p99.9. A pooled max÷median is NOT the measurement. **Gate:** if V's max/median materially exceeds K's, `-ctv` is the risk surface; if both are < ~50×, close the massive-activations line for this stack as measured-and-negative.
- **G3 — close the instrument gap**: GSM8K-class multi-step generation eval at f16 vs q8_0/q8_0 vs q4_0/q4_0 KV, rotation ON, one pure-attention + one GDN hybrid model, per-question persisted. Gate: reasoning delta outside noise with PPL/NIAH flat = KIVI's instrument finding replicated first-party.
- **G4 — paired behavioural drift (IFEval, FP16-anchored CondFlip)**, N≥250, one model, sweeping `-ctk`/`-ctv` over five configs. CondFlip > 5% while PPL drift < 2% ⇒ a behavioural gate becomes mandatory before any future KV-default change. All configs < 2% ⇒ group-32 granularity is doing the work and PPL+NIAH was retrospectively adequate.
- **G5 — reproduce KIVI's Figure 2/Table 2 on our architecture** (per-channel key magnitudes, with/without `LLAMA_ATTN_ROT_DISABLE=1`, per-group max/RMS at G=32). Gate: near-flat rotated ratio ⇒ redundancy conclusion first-party; surviving outliers make rotation placement (pre- vs post-RoPE, B1) live. Nobody has measured whether key-channel outliers even exist under per-head QK-RMSNorm — KIVI's ablated models all predate QK-norm.
- **H11 (Z, recorded)** — the frozen tree carries **none** of the three mitigations the massive-activations literature assumes: no per-channel scaling (`cpy_k`/`cpy_v` are pure `ggml_set_rows`), no clipping (zero `clip`/`clamp` in `llama-kv-cache.cpp`), no attention-sink special-casing (sinks exist only as a softmax bias in the graph — "llama.cpp has sinks" ≠ "llama.cpp protects sink tokens from quantization"). The one mitigation we carry is the Walsh-Hadamard rotation — exactly the lever G5 probes.
- **Massive-activations deprioritisation (record, not task):** our ρ = 4 hybrid (10 of 40 layers full attention) shows the **smallest** massive activations of every hybrid the paper (arXiv 2608.12149) measured — peak first-token magnitude 30 vs Kimi-Linear 180–240 and Nemotron-H 750–1800, and ratio does not explain the gap: output gating on the full-attention layers is the dominant attenuator, and our family ships it natively (`src/models/qwen35moe.cpp:349-354`). The paper contains no quantization experiment and no median anywhere, so no dynamic-range ratio can be computed from it — that is exactly why G2 exists. Deprioritise, do not close; never re-open this line from an abstract.

### Source References (2026-08-23 evening)

- [`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) — the KIVI correction (all three load-bearing parts), the dual-cache capacity-vs-bandwidth reframing, the R9 warrant repair, the group-32/axis granularity correction
- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — gates G2/G3/G4/G5 and B1/B2 with their named open/close criteria, H11 static read, the massive-activations deprioritisation record, the PR #21089 closed-unmerged re-verification
- [`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) — G3: quantized-KV spec-decode bandwidth-positive only at `draft_max = 1` on MI210 (see [Speculative Decoding](speculative-decoding.md))
- [KIVI arXiv:2402.02750](https://arxiv.org/abs/2402.02750) / [RotateKV arXiv 2501.16383](https://arxiv.org/abs/2501.16383) / [arXiv 2606.09864](https://arxiv.org/abs/2606.09864) / [arXiv 2608.12149](https://arxiv.org/abs/2608.12149) — the corrected external evidence base

## Compiled Update — 2026-08-23 (wave-2 research intake): the KIVI "primary quality gap" never existed, our KV blocks are finer than the published mitigation, and slot-restore loss is conditional

**Confidence: verified** — every statement below about our own tree is a read-only inspection of frozen
`production-consolidated-v9` (`0db32c06e3e550065b78311a6031ef3dd2c4f27c`) with file:line loci, reproduced
independently by three separate Stage-2b dives. Every third-party figure is dive-verified against its
primary source and is labelled as third-party. Under [MEASUREMENT.md](../MEASUREMENT.md) **no external
number here gates a stack change**; each is a hypothesis, and the tests are filed on
[`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) and
[`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md).

### The "primary quality gap" at `kv-cache-quantization.md:320` never existed — and it was wrong in three independent ways

The standing first-party claim was: *"llama.cpp's current q4_0/q8_0 KV does symmetric block quantization
— KIVI's per-channel K / per-token V is NOT implemented. This is the primary quality gap."* A Stage-2b
dive read KIVI (arXiv:2402.02750v2, ICML 2024) in full against the frozen tree and **retired it**
(`intake-1286#record`, dive-verified 2026-08-22, credibility 4/HIGH).

- **Per-token V is already implemented, and is structurally unavoidable once V is quantized.**
  `src/llama-kv-cache.cpp:231-232` allocates K and V with **dim0 = channels, dim1 = tokens**, so a
  32-element `q4_0`/`q8_0` block spans 32 contiguous *channels within one token* — precisely KIVI's
  per-token grouping at G=32. `v_trans = !cparams.flash_attn`, and `src/llama-context.cpp:3557` refuses
  to start with *"quantized V cache requires flash_attn to be enabled"*. **So whenever V is quantized,
  `v_trans` is false and V is channel-contiguous: our quantized V can never land on KIVI's bad axis.**
  The only configuration that would transpose V is the one where V is f16 and unquantized. This half of
  the old claim was simply false.
- **The K half is outside KIVI's demonstrated scope.** KIVI's own **OB 1** states that at INT4,
  per-token quantization of *both* caches maintains accuracy; the axis asymmetry is established **only
  at 2 bits**, and the paper runs **no 4-bit and no 8-bit axis ablation** — so it licenses no conclusion
  in either direction at the bit widths we serve. Production runs q8_0/q8_0, q4_0/f16 and q4_0/q4_0,
  never 2-bit. KIVI's own Table 3 4-bit per-token/per-token rows match or exceed FP16 CoQA on three of
  four models (Llama-2-7B 64.82 vs 63.88; Llama-2-13B 66.73 vs 66.37; Mistral-7B 67.80 vs 67.40).
- **We solve the key-outlier problem a different way, and an independent source says that way works.**
  The orthonormal self-inverse Walsh-Hadamard rotation gated at `src/llama-kv-cache.cpp:319-336`
  (`ggml_is_quantized(type)` && `n_embd_head % 64 == 0`, defeatable by `LLAMA_ATTN_ROT_DISABLE`) and
  applied at `src/llama-graph.cpp:2713-2720` mixes across **head channels** — the exact dimension KIVI's
  outliers live on — redistributing a magnitude-*m* outlier as *m*/√n so every 32-channel group ends up
  with comparable dynamic range. RotateKV (arXiv:2501.16383v2, Su et al., **no author or institutional
  overlap with KIVI**) uses **per-token keys plus rotation** at 2 bits and states verbatim that it
  "offers superior outlier management compared to per-channel approaches", reaching <0.3 PPL degradation
  on Llama-2-13B and <1.7% GSM8K degradation. **Per-channel keys are one remedy for channel outliers,
  not a requirement.**

**The one residual difference is real, small and cheap to test.** KIVI's quantizer is **asymmetric**
(zero-point *z* = min X, scale *s* = (max X − min X)/(2^B − 1)) where `q4_0`/`q8_0` are **symmetric**
(scale only). That half of the old sentence was accurate — but `q4_1` and `q5_1` are supported
**asymmetric** KV cache types, so this is a **flag, not a code change**. A Hadamard-rotated distribution
is near zero-mean and near-symmetric, which predicts the asymmetric quantizer buys nothing here; that
prediction is directly falsifiable in one short A/B, filed on the TQ3 handoff.

Two honest limits, neither of which reinstates the gap. First, this is a **mechanism argument plus one
third-party paper**, so it retires a *claim* and licenses no config change. Second, RotateKV's own Table 7
builds its 2-bit result on plain QuaRot rotation **plus** outlier-aware channel reordering **plus**
pre-RoPE rotation, implying a plain rotation is not sufficient *at 2 bits*; our fork applies a plain
**post-RoPE** Hadamard (the K-shift path at `src/llama-kv-cache.cpp:1874-1888` confirms the cache holds
rotated post-RoPE keys: dequantize → rotate back → RoPE → rotate forward → requantize). At 4/8 bits this
is very likely immaterial. Recorded as a caveat, not a defect, because we do not run 2-bit KV.

One correction to how KIVI itself is cited anywhere in this lineage: **the per-token-V prescription is
not an outlier argument.** KIVI's Figure 2 finds *no* value-channel outlier pattern; the per-token V
choice is derived from **84.3% attention sparsity** — the output is a weighted sum over few tokens, so
per-token grouping confines error to unimportant tokens. Anyone citing KIVI for "V is per-token because V
has outliers" is citing it wrongly.

### The granularity finding: the reading rule for every future KV-quant paper against this stack

**With `-fa 1`, llama.cpp quantizes K and V per token in 32-element blocks running along the CHANNEL
dimension.** Two consequences that keep being conflated because both mechanisms are called "grouping":

1. **We are finer than the published *mitigation*, by default, everywhere.** The alignment-collapse study
   (arXiv:2606.09864v2, `intake-1291#record`) lists **Group-64 quantization** among the mitigations it
   recommends and measures. Our group-32 is finer than its remedy. **Its headline damage figures are
   therefore a pessimistic bound for us, not a matched estimate** — any transfer of its numbers to this
   stack must say so, and G4 on the TQ3 handoff exists to replace the transfer with our own number.
2. **This is the OPPOSITE axis from KIVI, not the same one.** KIVI prescribes *per-channel for K*; ours is
   *per-token for both*, and quantized V is structurally locked onto the per-token axis by the
   flash-attention gate above. Same word "group", orthogonal dimension. **Do not read a Group-64 result
   as an upper bound on our group-32 damage without first checking which axis the grouping runs along.**

The behavioural half of the alignment-collapse result — the decoupling from perplexity, the K/V damage
asymmetry, and what our KV write path does *not* protect against — is compiled on the
[Quantization](quantization.md) page, which owns the KV-quant quality-instrument thread.

### Spec-decode over quantized KV: R9's verdict stands, its warrant did not — and VeriCache's algorithm is already expressible in frozen v9

**R9's warrant is repaired, not its verdict.** This page's 2026-08-22 section records "spec-decode
composes with quantized KV: 19.15 t/s (+3.3% vs f16) on Coder-32B — the R9 interaction risk closed
positive". The COMPLETED handoff has since corrected the *reasoning*: **that figure is a speed
observation and cannot evidence "no degradation"** — it logged no acceptance rate and named no
correctness instrument. The clearing evidence is **R11's needle-in-a-haystack result (q8_0/q4_0 = 9/9 at
1K/4K/16K, 10/50/90% depth) together with the R4 perplexity pair**; the throughput number is supportive,
never probative. R9 stays **CLEARED** because its config sits on the protected axis (K = q8_0) at the
safe bit width, but it is right by evidence only after the substitution. Re-measurement with both an
acceptance rate and a named correctness instrument is filed as `speculative-decoding-mtp-refresh.md`
**B5** (itself blocked on that file's G3, so the re-run does not measure a full-cache dequant and report
it as a KV-quant result).

**VeriCache's algorithmic core needs no code from us** (arXiv:2605.17613v1, `intake-1282#record`,
credibility 1/Low — the low tier grades *the paper's own performance claims*, not the tree reads below,
which carry no credibility discount). VeriCache drafts on a compressed KV cache and then **verifies
against the FULL KV cache**, so the target distribution is the real FP16 model rather than a quantized
surrogate. Frozen v9 already ships `--spec-draft-type-k`/`-ctkd` and `--spec-draft-type-v`/`-ctvd`
(`common/arg.cpp:3806-3830`), which set the **draft context's** KV type independently of the target's,
and `common_speculative_are_compatible` (`common/speculative.cpp:70`) checks only vocab type / BOS / EOS
/ token text — **so a model can be its own drafter**. `-ctkd q4_0 -ctvd q4_0` against `-ctk f16 -ctv f16`
with `--model-draft <same GGUF>` *is* draft-on-lossy-KV / verify-on-exact-KV, with no code change.
Nothing in either repo configures those flags **asymmetrically**: no registry entry and no launcher sets
them at all, and the only recorded use is a 2026-07-14 experimental-tree argv that set
`-ctkd q8_0 -ctvd q8_0` mirroring the target, which exercises none of the premise.

Three bounds on that, all load-bearing:

- **It gives us the ALGORITHM, not the SYSTEM.** llama.cpp's draft context prefills its own second
  full-length cache **in the same memory tier**. There is no host-resident full-KV tier, no
  PCIe-overlapped swap-in and no staggering scheduler — which is the entire systems contribution.
- **The headline decomposes, and the arm matching our lever is the weak one.** VeriCache *alone* measures
  **1.92–2.73×** on long-context decoding and 1.33–2.11× on remote prefix caching; the 4.26× is
  **composed with an EAGLE3 drafter**, the 4.35× is a **modelled ideal** from its own Appendix-B analytic
  model, and the **quantization-compressor arm** (KVQuant, RotateKV, ExpectedAttention, SnapKV on
  Mistral-24B) is **1.4–1.9×**. Losslessness is scoped by footnote 1 to *greedy* decoding "except for
  randomness caused by hardware"; the measured residual is KL < 0.01 nats, not zero; sampling is asserted
  in footnote 2 and never evaluated. And "first" is contradicted by TriForce (arXiv:2404.11912, 2024-04)
  and Vegas (arXiv:2602.07223, 2026-02), whose own abstract already describes the mechanism as
  established prior work.
- **Total memory goes UP, and our card sits at the worst end of its own hardware sweep.** VeriCache keeps
  the full KV on CPU *in addition to* the compressed cache on GPU; GPU-resident footprint is
  KV_full·(xc+1)/(x+1), i.e. 0.231·KV_full at its own x=25, c=0.2 — **a tier relocation, not a size
  reduction**. Its sweep runs 1.92× at HBM-to-interconnect ratio 60 up to 3.01× at ratio 10; **our MI210
  ratio is 35.5–56.7** (derived by the dive from MI210 HBM2e 1638 GB/s spec / ~1025 GB/s attained against
  the first-party PCIe4 x16 measurement of **28.89 GB/s H2D, 28.20 D2H, 2026-08-03**), predicting
  **~1.9–2.4×**, not 4×. Note the denominator spread: the [Quantization](quantization.md) page's roofline
  work records **1433.3 GB/s** as MI210 achievable bandwidth, giving ratio 49.6 — inside the same band, so
  the conclusion is insensitive to which attained figure is used. VeriCache's resource model also
  **excludes GPU compute** by its own §5.1, so any CPU-side estimate built on it is optimistic by the
  prefill term.

A first-party correction rode along and matters more than the paper: **the whole-cache dequant "cliff" is
a CUDA/HIP-backend property and must NOT be generalised to our primary CPU serving path.** The CPU
backend takes `kq_vec_dot = ggml_get_type_traits_cpu(k->type)->vec_dot` (`ggml-cpu/ops.cpp:8635`), so K
is consumed **in its quantized form at any q_len**, and V is dequantized **one DV-length row at a time**
into a stack temp (`:8739`). There is no whole-tensor conversion anywhere on the CPU path. On the GPU
path, without `GGML_CUDA_FA_ALL_QUANTS` only Q4_0/Q8_0/F16/BF16/F32 are FA-eligible KV types
(`fattn.cu:340-358`) — exactly our production `-ctk q4_0`/`q8_0`.

**Filed, not run:** measure α for KV-asymmetric self-speculation on our own models — same GGUF as target
and drafter, target `-ctk f16 -ctv f16`, draft `-ctkd q4_0`/`q8_0`, sweeping `--draft-max` ∈ {4, 8, 16},
reporting mean accept length and per-token agreement. Gate opens if q8_0-draft agreement ≥ ~95% at
draft-max 8; closes if q4_0-draft agreement < 90%. The drafter is the full model, so **this measures α,
not speedup**. Rider on `speculative-decoding-mtp-refresh.md`.

### The dual-cache post-mortem was a capacity argument applied to a bandwidth problem

This page's *"Hybrid buffer architecture is memory-negative"* finding — the `kv_recent` f16 + `kv_old`
q4_0 design that allocated both at full context size — is **reframed, not overturned**
(`kv-cache-quantization.md:71`, reframed 2026-08-23). "Dual cache = more bytes resident = wrong" is sound
**only when both copies sit in the same memory tier and the cheap copy is dequantized on the read path.**
Ours did both, which is why it lost: the **~30% gen-speed gap at 14.5K filled context is the cost of the
`q4_0 → f16` cast on every decode token** (~400 MB cast per decode token at 14K positions × 512 elements
× 28 layers × 2), a *dequantization* cost, not a *capacity* cost.

**A dual-cache design in which the second copy lives in a cheaper tier — host DDR5 behind a GPU, or a
slower NUMA node — and is never dequantized into the attention hot path is a different design and is not
refuted by anything measured here.** Cite that post-mortem narrowly: *same-tier plus dequantize-on-read is
memory-negative AND bandwidth-negative.* It establishes nothing about tiered KV, and must not be used to
close a tiering proposal.

### "Per-token KV streaming over PCIe is an anti-pattern" — scope it to *per token*

The 2026-07-20 section above states that PCIe4 is 7–14× slower than EPYC DDR5, "so per-token KV
*streaming* is an anti-pattern". That remains true **per token**, and is now scoped: **amortised over an
x-token draft/verify horizon the effective bandwidth is 28.89·x GB/s**, reaching **EPYC DDR5 parity
(~300 GB/s) at x ≈ 11** and **MI210 HBM parity (1638 GB/s spec) at x ≈ 57**. Those crossovers are
*derived* by the VeriCache dive from the first-party 28.89 GB/s H2D measurement, not measured end-to-end.
The transfer is only an anti-pattern when it is *not* amortised, and the horizons this literature
actually uses (x = 20–50) straddle the DDR5 crossover. The minimum draft length needed to hide a full-KV
reload at c = 0.25, B = 1 is x ≥ 24.8 (spec) / 15.3 (attained) at KV/M = 0.5, rising to 74.3 / 46.0 at
KV/M = 2.0 — i.e. above the 20–50 range once KV exceeds ~0.5× model bytes.

### Slot save/restore: the reuse loss is CONDITIONAL, it is detectable today, and the wrong PR is being watched

Upstream issue **#25913** ("`/slots` save/restore silently loses all prompt reuse on hybrid/recurrent
models") is real, open, unfixed on upstream master as of 2026-08-22, and **present byte-identically in
frozen v9** — the 87-line SLOT_SAVE/SLOT_RESTORE handler block matches upstream b10045 and the 33-line
checkpoint/reset block matches b10045 *and* upstream master `e85caa81`; no EPYC-local commit touches
either locus, so there is neither local mitigation nor local aggravation (`intake-1292#record`,
credibility 3/Medium, five independent reproducers on five backend/model combinations).

**The issue title is too broad in the direction that matters most to us.** Reuse is zero only for a
**DIVERGENT or EXACT-REPEAT** post-restore prompt; **a prompt that strictly extends the restored prefix
reuses fully, with no patch.** This follows from
`pos_min_thold = std::max(0, pos_next - n_swa - (has_new_tokens ? 0 : 1))`
(`tools/server/server-context.cpp:3322`) given that a hybrid's `llama_memory_hybrid::seq_pos_min` returns
the **recurrent cell's position** rather than 0 (`src/llama-memory-hybrid.cpp:172-175`): a strict
continuation leaves `pos_min` below the threshold and skips the reset block entirely, while an exact
repeat or a mid-prefix divergence opens it and forces `n_past = 0`. The PR author states the same thing
in prose, and four independent measurements fit the corrected table. **Our full-to-quarter migration is a
turn-boundary session handover — i.e. exactly the continuation shape — so "every migration costs a full
re-prefill" is NOT the default expectation; it is the failure mode that occurs when something rewrites
the prefix.**

Mechanism, for the record: the save writes **tokens only** (`:2539-2541`); restore calls
`slot->prompt.clear()` (`:2586`), and `server_prompt::clear()` destroys checkpoints
(`tools/server/server-task.h:615-618`); with the checkpoint list empty `do_reset` is always true
(`:3388`) and `pos_next`/`n_past` are forced to 0 (`:3404-3409`), logged only at `SLT_TRC` (level 4).
Scale of the effect where it does fire, third-party: one controlled A/B on a 58,202-token prefix measured
`prompt_n = 58,202 / cache_n = 0 / 181.9 s` on master versus `prompt_n = 516 / cache_n = 57,686 / 4.7 s`
with the candidate patch.

**"Silent" is true of the log and of the restore response, and FALSE of the next completion.**
`slot.n_prompt_tokens_cache = n_past` (`:3434`) reaches the client as `timings.cache_n`, OpenAI
`cached_tokens`, Anthropic `cache_read_input_tokens`, and the `/slots` payload — the instrument already
exists and this repo already documents it. **The operative silence is ours**:
`concurrency_aware.py:148-161` returns `True` on an HTTP 200, `:679` advances to
`MigrationState.VERIFIED` with `detail="restore_confirmed"`, and `:682` then **erases the source KV**.
That is a misnamed state; gating the source erase on measured reuse (compare returned `n_restored`
against `n_saved`, then read `cache_n`) is zero-compute and independent of any benchmark. The same gap
exists in `llama_server.py:1256-1279`, which never parses the body at all.

Three operational facts to carry:

- **The migration path is NOT dormant.** `--slot-save-path` is set on all three frontdoor instances
  (`:8070` at `-np 4`, `:8080`/`:8180` at `-np 1`, all `Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, `--device none`),
  emitted unconditionally by `orchestrator_stack.py:1454-1462`; 75 `kv_migrate_*` artifacts sit on disk
  and live probes recorded forward=6 / reverse=4 with zero aborts. Honest qualification: those artifacts
  carry synthetic `old-sess_*` ids and the newest is 2026-08-09, so **exercise by production traffic in
  the last two weeks is unproven** — "wired, enabled, exercised under probe", not "dormant".
- **Any measurement must defeat the RAM cache first.** Leftover in-process checkpoints produced a
  **340× false negative** for one reporter (a 5K restore appeared to reuse until the server was
  restarted, then reprocessed 5,428 tokens). Our frontdoor runs the default `cache_ram_mib = 8192` with
  no override, so `--cache-ram 0` or a full server restart between arms is **mandatory**.
- **This is a performance defect with a documented adjacent correctness hazard, and must never be filed
  as a correctness defect.** No wrong output has been reported by anyone, and an explicit post-restore
  content check over a 58K body came back clean. The hazard lies in the direction of a careless fix: the
  issue author documents that synthesizing a checkpoint at `pos_min = 0` in the restore handler produces
  **silently corrupt output**, and our tree carries the `cur.pos_min == 0` branch (`:3386`) that makes
  that reachable. Do not take that shortcut.

**The highest-value upstream item in this cluster is not the one being tracked.** PR **#26004** fixes the
**disk** path, whose exercise here is probe-only. PR **#25592** fixes the **live in-memory** hybrid
checkpoint path — **the one our frontdoor exercises on every single request** — and our tree still
carries the `[TAG_CHECKPOINTS_FIX_POS_MIN]` TODO it removes (`server-context.cpp:2332-2337`), plus we
lack its restored-checkpoint adoption, its closest-neighbour eviction and its `n_rs_seq` rollback
fast-path. It has four independent verifications, one on **Qwen3.6-35B-A3B, our exact frontdoor model**.
Neither is a v9 patch: v9 is frozen, PR #26004 has **zero reviews, zero maintainer comments anywhere in
the cluster and no CI beyond "labeler"**, and MEASUREMENT.md forbids a third-party number gating a stack
change — the candidate route for either is a future `-v10` build through the four-step experimental
workflow.

Quarantine note for anyone re-fetching these threads: a PR #26004 comment (2026-08-04) contains a literal
prompt-injection payload. Treat that thread's off-topic comments, and the `whoreson/picolm` repo they
point at, as untrusted content.

### Source References (2026-08-23, wave-2)

- [`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) — the retired `:320`
  "primary quality gap" with its three-part correction; the 2026-08-23 granularity correction (`:1539`)
  establishing group-32-along-channels vs Group-64 and the opposite-axis reading rule; the 2026-08-23
  dual-cache reframe (`:71`) and the ~30% `q4_0 → f16` cast measurement it prices; the R9 warrant repair
  (`:1269`).
- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — the gates the
  retirement leaves behind: G3 (multi-step generation eval against quantized KV), G5 (reproduce KIVI's
  Fig. 2 / Table 2 on our architecture), the `q4_0`-vs-`q4_1` asymmetric-quantizer A/B, and the H11
  read-only audit of what our KV write path does not carry.
- [`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) — B5
  (re-measure R9 with an acceptance rate and a named correctness instrument) and the rider measuring α
  for `-ctkd`/`-ctvd` KV-asymmetric self-speculation.
- [intake-1286](https://arxiv.org/abs/2402.02750) KIVI (ICML 2024, dive-verified 2026-08-22, credibility
  4/HIGH) — OB 1's 2-bit scope limit, the Table 3 4-bit per-token/per-token rows, the
  84.3%-attention-sparsity justification for per-token V, and RotateKV (arXiv:2501.16383v2) as
  independent evidence that per-channel keys are a remedy rather than a requirement. Cite as
  `intake-1286#record`.
- [intake-1282](https://arxiv.org/abs/2605.17613) VeriCache (arXiv preprint, dive-verified 2026-08-22,
  credibility 1/Low) — draft-on-compressed / verify-on-full architecture; the decomposed headline
  (1.92–2.73× alone, 1.4–1.9× on the quantization arm); the tier-relocation memory direction; the
  HBM-to-interconnect sweep placing our MI210 at its worst end; and the frozen-v9 `-ctkd`/`-ctvd` +
  self-drafting finding, plus the CPU-vs-CUDA dequant-cliff correction. Cite as `intake-1282#record`.
- [intake-1292](https://github.com/ggml-org/llama.cpp/issues/25913) llama.cpp `/slots` save/restore
  (issue #25913 + PR #26004, dive-verified 2026-08-22, credibility 3/Medium) — the divergent /
  exact-repeat / strict-continuation scope derivation from `pos_min_thold`, the byte-identity audit
  against frozen v9, the `cache_n` detectability finding and our `VERIFIED`-on-HTTP-200 gap, the
  `--cache-ram` masking hazard, and PR #25592 as the larger live exposure. Cite as `intake-1292#record`.
- [intake-1291](https://arxiv.org/abs/2606.09864) Alignment Collapse Under KV Cache Quantization (arXiv
  preprint, dive-verified 2026-08-22, credibility 3/Medium) — the Group-64 mitigation our group-32 is
  finer than; behavioural detail compiled on [Quantization](quantization.md). Cite as
  `intake-1291#record`.

(append to the page-level `## Source References` list)

- [intake-1286](https://arxiv.org/abs/2402.02750) KIVI (ICML 2024) -- the warrant behind every "per-channel K / per-token V" citation in this corpus. Dive-verified 2026-08-22: the prescription is measured, not asserted, but OB 1 establishes it **at 2 bits only** and the paper runs no 4-bit or 8-bit axis ablation; it reports **no perplexity anywhere**; and the full-precision residual window, not the axis, does most of the accuracy recovery (Llama-2-7B GSM8K 5.76 -> 12.74 at a fixed axis). Retires the `kv-cache-quantization.md:320` "primary quality gap". Cite as `intake-1286#record`
- [intake-1291](https://arxiv.org/abs/2606.09864) Alignment Collapse Under KV Cache Quantization -- ConditionalFlip as a paired behavioural gate; K carries 76-102% of the damage at 4-bit; **Group-64 is its mitigation, which our group-32 blocks are already finer than**. Unreviewed preprint, NVIDIA-only hardware, no independent replication located. Cite as `intake-1291#record`
- [intake-1282](https://arxiv.org/abs/2605.17613) VeriCache -- draft on the compressed KV cache, verify against the FULL KV cache; the algorithmic core is expressible in frozen v9 via `-ctkd`/`-ctvd` with the model as its own drafter, while the systems contribution needs an interconnect we do not have. Cite as `intake-1282#record`
- [intake-1292](https://github.com/ggml-org/llama.cpp/issues/25913) llama.cpp `/slots` save/restore (issue #25913 + PR #26004) -- post-restore reuse is zero only for a DIVERGENT or EXACT-REPEAT prompt and full for a strict continuation; detectable today via `timings.cache_n`; PR #25592 (live in-memory checkpoint path) is the larger exposure for us. Cite as `intake-1292#record`


## Compiled Update — 2026-08-31 (incremental): GLM-5.2 KILLED; the DSA findings transfer to glm5next

**Confidence: verified** (operator ruling + artifact deletion ledgered; GGUF header read for the successor arch).

The GLM-MoE-DSA evaluation closed with a KILL (OP-8, operator ruling 2026-08-31: GLM-5.3-flash
supersedes any reason to run GLM-5.2); the 223 G UD-IQ2_M artifact is deleted and ledgered. What
survives the model is the DSA layer knowledge, now seeded into the GLM-5.3-Flash handoff (INF-69):

- **GLM-5.3-Flash is arch `glm5next`** (288×10B), NOT `glm-dsa` — but it carries the same
  DSA-family metadata surface (`indexer.{head_count,key_length,top_k}`, a NEW `kpool` field, and
  `nextn_predict_layers`). Arch-support audit is the INF-69 gate; the `3dee86a5a` GLM→DSA-cache
  wiring is the worked precedent, not reusable code.
- **DSA-DENSE-MASK stands as a fork-level finding**: the generic DSA path computes the indexer +
  top-k but final attention masks over FULL KV (no sparse gather) — any glm5next bringup inherits
  it, and the sparse-gather/profiling gate stays owned by `llama-cpp-dsa-contribution.md` (D2/D3).
- **`indexer_top_k` is a correctness cliff, not a tuning knob**: an under-sized cap corrupts exact
  output once prompt length exceeds it (GLM-5.2's safe policy was next-power-of-two ≥ prompt
  tokens). glm5next's `kpool` may change the semantics — re-derive before any quality run.
- **NextN/MTP**: GLM GGUFs preserve the NextN tail, the fork's GLM archs skip it and never
  dispatch `LLM_GRAPH_TYPE_DECODER_MTP`; the smallest credible port is Qwen-style tail-tensor
  loading + a DECODER_MTP graph.
- The GLM-5.2 reviewer-capability program (REV-02) is mooted by the KILL; its retarget-or-close
  disposition is flagged to the reviewer control plane.

### Source References (2026-08-31)

- [`glm51-reap-cpu-evaluation.md`](../handoffs/completed/glm51-reap-cpu-evaluation.md) — the
  completed evaluation: KILL verdict, DSA-DENSE-MASK evidence, top-k schedule records.
- [`glm53-flash-evaluation.md`](../handoffs/completed/glm53-flash-evaluation.md) — INF-69: the
  inherited-findings contract and the glm5next arch facts (GGUF header read).
- [`2026-08-31-disk-reclaim-menu.md`](../progress/2026-08/2026-08-31-disk-reclaim-menu.md) —
  OP-31 execution record incl. the GLM-5.2 deletion and disk state (87 G → 480 G).

## Compiled Update — 2026-09-08: the KV-reduction cluster's 09-07 wave — selection-class methods cannot serve a memory objective, and the streaming floor's design gained power and an eviction regime

**Confidence: verified** (source-derived arithmetic on the intake's Table 4; the design-constraint rewrite is the owning handoff's recorded state); the two intake pointers are stage-1 — pointer only, no claims.

### Selection-class KV methods hold the FULL cache — they buy zero KV memory

At a 2K budget / 16K context, sink+window matches the best selection method on FLOPs (1.05M), global-to-shared transfer (1.04 MB) and kernel latency (20.1 µs) at **1/8th the on-device memory (1.04 MB vs 8.38 MB)** — because every selection-class method (Expected-Attention/TriAttention, SnapKV, H2O, …) keeps the full cache and selects at read time. `intake-1334#05`. Two consequences:

1. **Selection-class methods leave the candidate set of the 10× KV-MEMORY objective.** The earlier selection-vs-compaction framing on this page was about quality per ratio; this is the memory-axis verdict — [Attention Matching](../handoffs/active/attention-matching-kv-compaction.md)'s KV-7 rider records them as buying zero KV memory (8.38 MB on-device, identical to full attention).
2. **The streaming floor question (PS-1) reduces to a single axis: accuracy.** Sink+window already matches selection-class methods on every cost axis at a fraction of the memory — so the floor gate decides on accuracy alone.

Also on that sweep design: **PS-2 closed, no task filed** — our context-shift path is Reset-PE (`seq_rm` + `seq_add -n_discard`), the source reports the difference insignificant, and its recovered Figure 14 puts Reset-PE ahead at 4 of 5 budgets within one standard error (`intake-1315#record`). Three numeric corrections carried against the source so a future sweep session does not re-quote them: Table 1's 128K cell is the **vanilla-SWA** value (11.26×, not 11.7×); W=16384 does **not** match full attention (28.74 vs 31.14; first match at W=32768); the "seconds" axis is **derived** — nothing was timed.

### The streaming-LLM 4-axis sweep: design rewritten with power and an eviction regime — still zero cells

The binding design constraints were rewritten 2026-09-07 (full text in [streaming-llm-baseline.md](../handoffs/active/streaming-llm-baseline.md)):

- **Generation length is the independent variable** — every arm must generate ≥ 4×W or it does not test the mask; each cell's eviction regime must be stated. Priced at the measured ~31 t/s (Qwen3-1.7B Q8 CPU): one 4×W generation ≈ 9 min @W=4096, ≈ 18 min @W=8192; **W ∈ {2048, 4096, 8192}, W=16384 is GPU-only or dropped**.
- **Context sizing**: v9's `n_discard = n_left − window` collapses when `-c = prefix + W`, so run `-c = prefix + W + chunk` and sweep `chunk`.
- **Benchmark × power tension resolved**: MATH500 is power-adequate (stderr ~1.0) but its traces (~5K generated tokens) barely evict at W=4096; AIME stresses the mask but has only 30 problems (stderr 6.7–7.8 pp). Resolution: **pool AIME-24 + AIME-25 with avg@k and a stated detectable effect size, and RETAIN W=2048** — the only power-adequate arm actually in the eviction regime — reversing the earlier "DROP W=2048".
- **A workload-split result IS the finding**: short-context/dialogue arms pass the ≤10% floor at every K_win, long-retrieval arms fail it; add a training-free sink+window control arm.
- **Instrument-mismatch rule**: the literature masks at every position including prefill; frozen v9 evicts only inside the context-shift branch and rejects a prompt of `n_ctx` or more outright — the long-INPUT arm measures full-attention prefill + streaming decode, a strictly stronger method, and must never be set against a published S-NIAH table.

Execution state: **zero cells completed** — the 72-cell daemon (3 workloads × 3 budgets × 3 K_win × 2 models + 6 full-KV baselines + 12 gemma4 F16 controls) was reconciled 2026-08-27 after the lease/region was held by another lane; relaunch is gated on q0–q3 release. SWA finding to carry into it: **gemma4 needs `--swa-full` on v9 or context-shift silently disables**.

### Coverage pointers (stage-1, no claims)

Two structural gaps now have pointer entries in the cluster: the **SWA window floor** (SWAA, arXiv:2512.10411; Cabannes et al., ICLR 2026, *Short window attention enables long-term memorization* — both bear on the PS-1 window floor; `intake-1340#record`) and **query-aware SELECTION-based sparse attention** (TidalDecode arXiv:2410.05076, Quest arXiv:2406.10774, SeerAttention-r arXiv:2506.08889; `intake-1334#record`). Independent external corroboration of the cross-head/cross-layer unification that landed under S4/S7 (TriAttention row S8-d) is recorded in [triattention-kv-selection.md](../handoffs/active/triattention-kv-selection.md) (`intake-1334#01`, `intake-1334#04`).

### Source References (2026-09-08, KV-reduction cluster)

- [`streaming-llm-baseline.md`](../handoffs/active/streaming-llm-baseline.md) — the binding constraints, the intake-1334/1340 pointer rows, PS-1/PS-2, and the sweep execution state.
- [`attention-matching-kv-compaction.md`](../handoffs/active/attention-matching-kv-compaction.md) — the KV-7 selection-class rider and the 10× memory objective.
- [`triattention-kv-selection.md`](../handoffs/active/triattention-kv-selection.md) — the S8-d corroboration record.


## Compiled Update — 2026-10-03: sizing the 27B's unified pool, and admitting one long prefill at a time

**Confidence: verified** for step 1: it is deployed (orch `2586a7bb`) and was proven by a live gated call. Step 2 is
signed and applied in git, but **not live**: the :8083 relaunch and its serving proof are pending. The per-token
figures come from the :8083 KV-sizing decision package.

- **The 27B is a hybrid.** Only 16 of its 64 layers hold growing KV, at 34,816 B/token in q8_0. The measured marginal
  cost is 42 KiB/token, which includes the KQ mask and the flash-attention scratch.
- **The pool ran out because traffic bypassed the gate.**
  - All 17 pool-exhaustion episodes in the :8083 log were four ~45–55k contexts filling the 196,608-token pool.
  - `logs/orchestrator.log` held zero `SharedKVPoolAdmission` queue lines.
  - Scouts reserved slots, not tokens, and direct harness clients went straight to :8083.
  - Between 09-24 and 10-01 the :8083 log shows 929 prompt-cache evictions, 456 "failed to find a memory slot"
    warnings and 39 "Context size has been exceeded" errors.
- **Step 1 (KVU-15 / UFH14-B2), live after an API-only reload.**
  - Scouts reserve prompt + max_tokens on the token gate.
  - Each server admits one long prefill at a time: at least 16384 estimated tokens, set by
    `ORCHESTRATOR_KV_POOL_LONG_PREFILL_TOKENS` (0 turns it off). The lease ends at the first streamed chunk, or after
    prompt/250 tok/s.
  - A `/slots` observation holds long requests behind any slot that is prefilling ≥4096 tokens. This covers the other
    uvicorn workers and direct clients.
  - The per-request cap is min(slot ctx, model ctx_max).
  - 32 new tests. The target is the measured collapse of neighbour decode under concurrent prefill, from 28.6 to
    7.8 tok/s.
- **Step 1's known limits (KVU-15a).**
  - **The lease is per uvicorn worker.** Across the 6 workers it relies on `/slots`, which sees a long prefill only
    after about 4096 processed tokens plus a 1.5 s cache. Two workers can therefore start long prefills seconds
    apart. Fix: move the lease to a cross-process primitive.
  - **Size is judged on the whole prompt,** so a mostly-cached long prompt still waits. Fix: subtract the matching
    slot's `cache_n`.
  - Done when a 2-worker replay peaks at one long prefill and a cached-prefix request is not held.
- **Step 2 (KVU-16 / UFH14-B3), signed 2026-10-03T11:50:52Z, not live.**
  - `-c` goes from 196608 to 393216, unified at np 4: +4.86 GiB, to about 51.4 GiB, leaving about 12.5 GiB free.
  - The v10 server clamps each slot to n_ctx_train 262144 itself. The orchestrator's per-request cap is 262144:
    `per_request_n_ctx` must take min(n_ctx, n_ctx_train) once `-c` exceeds n_ctx_train.
  - Draft n-max drops to 7.
- **What 393216 holds.** It holds one 262k request plus 131k, or 4 × 98k. It does **not** hold two full 262k
  requests. The session had told the operator it did, and corrected the claim before the signature.
- **Step 2 bring-up proof (pending).**
  - Read the `-lv 4` memory lines and KFD at load (about 51.4 GiB expected).
  - Run one synthetic 4 × 90k concurrent replay: zero "failed to find a memory slot", and a KFD peak ≤ 62 GiB.
- **The alternative the package weighed.** Before packaging, a zero-compute check regressed per-slot decode against
  pool high-water on the existing log. If decode with neighbours had been more than 15% slower at 300k+ fill than at
  100k, the alternative was a 4 × 163840 split. The signed package kept 393216 unified.
- **Defects caught while packaging step 2:**
  - step 1's code would have misread the new pool as split, which disables admission;
  - a single `update` wrote stale priors;
  - a stale template `draft_max: 4` override.
- **Hold.** The API must not reload before the :8083 relaunch, because the new code expects the 393k pool.

### Source References

- [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [multiscreen-attention-evaluation](../handoffs/active/multiscreen-attention-evaluation.md), [progress 2026-10-24 3c4ca599](../progress/2026-10/2026-10-24-3c4ca599.md) — sweep 20: KPF-64 8/8 arms, G1 closed.

- [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md) — KVU-15 (live), KVU-15a (limits), KVU-16 (signed, not live), KVU-17.
- [Agentic serving harness fixes](../handoffs/active/agentic-serving-harness-fixes.md) — UFH14-B2/B3; defects D6 (pool overflow) and D7 (prefill stalls decode).
- [Prefill/decode share review](../docs/reviews/prefill-share-20261003.md) — evictions, memory-slot warnings and the neighbour-prefill decode collapse.
- [2026-10-03 workspace-ec progress](../progress/2026-10/2026-10-03-workspace-ec.md) — the hybrid KV figures, the "two full 262k requests" correction, and the hold.

## Incremental synthesis — 2026-10-06 root wrap

**Confidence: experimental evidence with unresolved calibration.** The post-manifest masked-block-skip GPU run passed five bit-identity criteria at 132/132 each and `test-backend-ops` at 118/118 twice. Its measured kernel time versus KVU-19a was 0.708× for 4×9 rows, 0.88–0.90× for uneven layouts, 0.98× for aligned 4×8, and 0.99–1.01× for streams. Two calibration failures remain, including one shared with KVU-19a, and the draft=1 p3batch result still trails the no-KV baseline. Treat this as an experimental path with open calibration and end-to-end questions, not a promoted serving result.

The prefix-fork update reports branch B landed with its flag off; the API was not reloaded, and the live shadow window remains the next proof. The `/props.slot_fork` capability gates automatic fork use. First-prompt TTFT attribution is also still a proposed GPU measurement. The updated campaign record says the operator kept the shared 393K pool after the P3 decode loss (−59.5% with three resident ~99K neighbours) and routed the response to masked-block skip. The champion ledger records P3 v2 on candidate X matching the KVU-19 champion at L3. These are the documented decision and a bounded parity check, not a claim that the cache tax is eliminated for all shapes.

Sources: [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md), [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [GPU serving tie-in program](../handoffs/active/gpu-serving-tie-in-program.md), [Current campaign](../handoffs/active/CURRENT-CAMPAIGN.md), [AutoKernel champion aggregate](../handoffs/active/autokernel-champion-aggregate.md).

### Supplemental KV findings — Oct 3–6 changed files

The prefix-fork P1 experimental branch passed CPU exactness checks across generated Qwen3.5 GDN, Qwen3.5-0.8B hybrid, Qwen2.5-0.5B attention and Gemma-3-1B SWA: fork-versus-fresh/state-copy and source continuation were bit-identical in the tested cases, with exact cell accounting. For three trunk-first 1,575-token children, each forked 1,560 tokens and prefetched 9–15 tokens; with idle caching disabled, the pool held 1,772 unique versus 6,452 logical cells. A fork-attributable hybrid divergence appeared after source purge at thread count 8 (55/64 tokens matched fresh); the handoff attributes it to cell order and requires comparison with fresh/fragmented-layout controls at production scale. This remains CPU-only experimental evidence, not GPU serving proof.

The durable masked-block-skip fold record supplies the implementation and early validation boundary behind KVU-19: its 64-case HIP harness was bit-identical skip-on/off, while six cases differed from unpatched champion codegen only at NMSE ≤3.1e-7; its shared-GPU microbench was explicitly indicative. CPU decode stayed within noise (2.85 ms to 2.87–3.01 ms over 0–112K foreign cells), so no CPU speedup is claimed. Full model P3 remeasurement remained a separate exclusive-window gate. The post-manifest workspace science record also finds that a masked tile uses the union of sequence live sets, so per-sequence routing can help batched decode where block skipping alone cannot.

Sources: [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [FlashAttention masked-block-skip fold](../docs/design/fa-masked-block-skip-20261003-fold.md), [Oct 4 workspace-ec progress](../progress/2026-10/2026-10-04-workspace-ec.md), [Oct 3 AK progress](../progress/2026-10/2026-10-03-ak-ds41-main.md).

## Incremental synthesis — 2026-10-06: K-shift defects at v10

**Confidence: unit-verified on CPU fixtures; no model-level run.** The K-shift path (`build_rope_shift`, `build_graph_shift`) has three confirmed defects at `ffc1bac82`: it re-applies YaRN mscale on every shift, `pos_div` records shift deltas with the wrong sign, and under quantized K it applies the Hadamard to an n_rot-wide view of a full-head transform (large error; aborts on CPU with a non-contiguous q8_0 destination). Context-shift under YaRN and any quantized-K shift should be treated as unsafe until the probe-branch fixes pass a model-level test. Details: [context-extension](context-extension.md#incremental-synthesis--2026-10-06-workspace-ec-wrap-native-window-inertness-k-shift-jet-long).

Sources: [YaRN context-extension research](../handoffs/active/yarn-context-extension-research.md) (CTX-KSHIFT), [Oct 6 workspace-ec progress](../progress/2026-10/2026-10-06-workspace-ec.md), [Oct 5 workspace-ec progress](../progress/2026-10/2026-10-05-workspace-ec.md).

## Compiled Update — 2026-10-20: hybrid prefix-cache survey (vLLM and llama.cpp) and the prefix-fork recut

**Confidence: external for every vLLM and upstream-llama.cpp mechanism and number below (author-reported, one setup each, none reproduced on our hardware); verified only for the recorded session facts.** The intake packet is `intake-hybrid-prefix-cache-20261020`: Stage 1 `intake-2061#record`..`intake-2071#record`, then six Stage-2 dive waves (entries 2072 through 2115 of the index) with an independent second reader per wave and a Stage-3 plan that filed 16 tasks (KPF-13.1, KPF-17.1..17.4, KPF-18.1..18.3, KPF-19.1, KPF-26.1, DOC-1, KVU-12.1/12.2, VB-KVU-PF.1, CH-18) and ticked KPF-25. Entries whose verification is still `stage1-unverified` (`intake-2064#record`, `intake-2065#record`, `intake-2067#record`, `intake-2069#record`, `intake-2070#record`) are provenance only; no number from them is used here.

- **Granularity is the central design variable.** vLLM's partial-hit work decouples prefix-match granularity from the physical block size so a hybrid attention + Mamba model can hit a prefix ending inside a block; the recurrent state must come from exactly the hit boundary, so only one state is registered at the final match-unit boundary rather than every intermediate one (`intake-2061#record`, `intake-2062#record`, design alternatives in `intake-2071#record`). Our analogue is that a fork can start only at a checkpointed position, which is why checkpoint placement (KPF-15 junction checkpoint, KPF-13) decides the achievable hit length.
- **Two derivations of one position is the recurring bug class.** The position where the scheduler ends a prefill chunk and the position where the cache publishes recurrent state must come from one flag; a mismatch with MTP made a sibling reuse 0 of 1536 shareable tokens and, author-reported, cost roughly 4-6 points of hit rate and 20-30% of per-GPU throughput until fixed (`intake-2073#record`; related shift handling in `intake-2072#record`, `intake-2076#record`). This is the model for KPF-17.1 (n_tokens binding) and KPF-18.1/18.2 (trunk-then-suffix and MTP parity).
- **Publish-before-write is a corruption hazard, not only a miss.** vLLM published state hashes at schedule time while the writing step ran later or never (client abort); a retry could load never-written state and poison later requests that share the prefix, fixed by a step-commit fence (`intake-2088#record`, open PR at read time). The MTP-plus-prefix-caching accuracy thread shows the field magnitudes disagree between reporters (about -2 to -4 points in some harnesses, larger in one tool-calling suite, unreproducible in others) and was closed without naming one fix (`intake-2090#record`). Our fork must therefore gate restores on a bit-identity check, which is what KPF-17/18 specify.
- **Admission and retention policy.** Marconi admits at most two recurrent states per sequence (a radix branch point found by speculative insertion, and the post-decode state) and evicts by recency plus a FLOP-efficiency term; its token-hit-rate gains over a dense every-32-token-block baseline are paper-reported at 4.5x/7.3x/34.4x across three traces (`intake-2102#record`). vLLM's merged shared-prefix admission is reactive: the first occurrence of a prefix still pays full prefill (`intake-2091#record`), and selective retention keeps a pinned junction (`intake-2109#record`). Dense per-boundary snapshots saturated the pool in one report, motivating a retention interval (`intake-2063#record`; the vLLM default was later set to 0 by a merged 2026-08-17 PR). Our per-slot checkpoints are large, so the lesson is snapshots at branch points, not a dense grid.
- **Prefill checkpoints inside one forward.** One PR exports the intermediate recurrent state from the kernel mid-chunk instead of splitting the forward in two, author-reported 9-25% TTFT gain; it excludes speculative decoding as shipped (`intake-2087#record`, `intake-2086#record`).
- **llama.cpp slot save/restore now carries checkpoints and draft state upstream.** Context checkpoints are appended to the slot file (`intake-2096#record`) and the draft context plus speculative state follow (upstream llama.cpp PR #30574 and its linked issue); author-reported draft acceptance after restore 49% versus 37% on master for a Qwen3.8-27B MTP draft. `PARTIAL_ONLY` handling in the plain KV cache (upstream llama.cpp PR #30514) and a one-hunk SWA reuse-threshold fix (upstream llama.cpp PR #30580) are candidates for the next experimental rebase on fresh production, never a cherry-pick into v10.
- **Session record (verified from the progress log).** The P1 prefix fork was reassigned to workspace-f8 and re-cut on the champion twice, ending at `experimental/kv-prefix-fork-p1r2-20261020` @ `14d603f3a` with tests green and CPU gate evidence kept outside git. The champion fold "slotdraft" (`e33229348` to `dd3d9721c`, ports of upstream #26004 and #30574) measured MTP acceptance after slot restore at 0.98-1.02x live versus 0.53-0.71x before. KVU-12 (CPU np x ctx study) was reopened with a Tier-0 window armed; the KPF-18 runner needs a fix to create its log directory before writing (`kpf18_gate.py`). These are session-reported operational results, not a promotion decision.

**Open questions.** Whether the vLLM junction-checkpoint rule transfers to a fork with no hashed prefix blocks (restore-time check only); async scheduling and speculative-decoding interaction (named open in `intake-2071#record`); whether a production-scale fork reproduces the cell-order divergence seen after source purge (see the 2026-10-06 section above).

Sources: [Progress 2026-10-20](../progress/2026-10/2026-10-20.md) (workspace-f8 section), [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md), [research intake index](../research/intake_index.yaml) (entries for the vLLM and llama.cpp hybrid prefix-cache packet).

## Compiled Update — 2026-10-21: KPF line references are tree-tagged, vacuous fork tests found, and the first KPF-18 and KVU Tier-0 readings

**Confidence: verified for the code facts (each checked with `git show <rev>:<path>` on 2026-10-20) and the recorded runs; OBSERVATION grade (n = 1 per cell) for every timing or divergence number. The KPF-18 item 4 and the later KPF-17.1b parked jobs have not reported.**

- **Cite a kernel line only with its tree tag.** Four trees disagree on line numbers: v10 `ffc1bac82`, champion `dd3d9721c` (`e33229348` was the tip before the #26004/#30574 ports, so refs against it are about +229 lines off from `server-context.cpp` L2450 on), p1r `a1f0c8cf9`, p1r2 `14d603f3a`. Example: `create_checkpoint` is L2365 in v10 and L2802 on the KPF branches. The handoff now carries `[v10 · champ · p1r · p1r2]` tags (KPF-DOC-1; [kv-prefix-fork handoff](../handoffs/active/kv-prefix-fork-and-paged-attention.md)).
- **Structural facts of the tree a fork builds on.** `llama_memory_recurrent::seq_cp` ignores p0/p1 and makes the destination share the source's current tail cell (same in all four trees); `--cache-reuse` is not force-disabled for hybrids at the champion: `llama_memory_hybrid::get_can_shift()` returns true; no production role sets the flag, and the engine defect is tracked as CH-21 (KPF-63 correction); `get_available_slot` computes LCP similarity only over slots that are not processing; the hybrid ubatch split is `split_equal`, the pure-KV path `split_simple`.
- **The last-user checkpoint spacing exemption (`is_last_user_message || near_prompt_end`) is NOT a KPF change**; it is in v10 and the champion. The KPF departures are the `pinned` checkpoint field (`common.h`, absent in v10 and champ), the `checkpoint_at` request parameter, the `ckpt_pinned ||` term in that condition, the cross-slot fork path, the attention-only zero-copy seq share, fork telemetry, the `/props` fork capability, the prefix-hash ladder and content epoch. A promotion carries them inside the FULL candidate build, never as a cherry-pick.
- **A fork test that never forks passes vacuously.** KPF-17.1a's gate failed in job 21 because the case's wait loop read a stale `/slots` `next_token.n_decoded`, returned while the source was still prefilling, and the child prefilled from scratch (`n_fork_tokens 0`); job 20's honest pass of the same case was vacuous. With a real fork the `fork_clobber_src` mutant aborts a hybrid server (`common_context_seq_rm` GGML_ABORT) and drops source cells on SWA/attention. The audit (`a7af56dff`) added an `assert_forked` guard (fails on `n_fork_tokens` 0, below the case minimum, or wrong source slot) and found vacuous: the busy-source test, 172 current-step and same-iteration-as-erase (`assert any(...) or True`), 171 abort-then-retry and key-check control, 174 SWA pinned-junction, and the P2 epoch ladder. Rule: every fork-purpose case must fail when `n_fork_tokens == 0`. The earlier queue failures (jobs 22/23) were oracle and setup bugs, not fork defects: CPU logits move 0.32-0.47 under any evaluation-order change with top-1 unchanged.
- **SWA correctness and a speed loss.** SWA checkpoint data always covers its own resume window and the recorded pos_min is never above the real one, so a pinned-junction fork on an SWA cache cannot produce wrong output. Once context exceeds the SWA cache (about n_swa x n_seq + n_ubatch) the upstream `pos_min < pos_next - n_swa` gate rejects junction checkpoints and the fork falls back to full reprocessing (correct, slower); found by code reading and unmeasured (KPF-17.4a; fix is upstream TAG_CHECKPOINTS_FIX_POS_MIN via CH-18).
- **KPF-18 MI210 readings (window f8-w1/f8-w1c, fork build `gpu-20261020-a1f0c8cf9`).** Item 6 off is bit-identical to the champion 8/8; item 5 seq-bit invariants 44/44 and forks 8/8. Item 1: fork taken at `n_fork_tokens == T` 16/16, first-token top-1 matches fresh 16/16 vs control 15/16, greedy-prefix median 174 vs control 53 (DFlash2 on), logit max-abs 0.17 inside the fresh-vs-fresh spread 0.09-0.17. Item 2 is INCONCLUSIVE: on the MI210 two fresh runs match all 256 tokens only 2/16 (non-batch-invariant GPU kernels; CPU gave 16/16) and the runner has no same-slot A/A control. Item 3 (groups 0-4): first-token distributions identical 5/5, full 256-token greedy match 3/5 with min prefix 43, and the A/A control matches 4/5, min prefix also 43: no sign the fork perturbs its source, but n = 5 cannot separate that from GPU batch non-invariance. Gate item 2 at the measured A/A floor rather than bit-identity (Gemma fork vs own continuation differs 0.04 nats at token 1 when KV cell placement differs).
- **CPU fan-out (KPF-18.0b item 7, Qwen3.6-35B-A3B-MTP Q8_0, one quarter, 16k trunk + 4 children).** Fork off: 51,712 fan-out prefill tokens, child TTFT 183–512 s, aggregate decode 1.5 tok/s. Fork on (min-tokens 1024): 2,560 prefill tokens, 3 checkpoint forks × 16,384 tokens per window, child TTFT 38–47 s, aggregate decode 23–24 tok/s; logical KV cells 68,604 vs unique 19,452. n=1 per cell on a shared host; equivalence was not measured, so these are bounded OBSERVATION readings rather than a KPF-18 pass. Follow-up KPF-18.0b.1 corrected metadata by deriving speculative mode from launched argv and applying `llamacpp:kv_cells_used` to both arms; this corrects record provenance/metric consistency and does not alter the recorded observation or close the remaining KPF-18 gate.
- **KVU Tier-0 window W2 (v10 `4483bcfc`, Qwen3.6-35B-A3B MTP on): the decision rule is undecidable.** Split np4 L64k decode sum 18.67 / 18.50 tok/s (ABA spread 0.9%, n = 2 launches; higher is better), unified np4 L64k 18.22 (-2.0%), prefill -3.0%, TTFT +1.0%. Not like-for-like: the split arm lost its 4th stream to HTTP 400 context-exceeded (a 65.5k-token turn exceeds the 65,536 slot) in every decode wave, and cache-idle-slots was on for split, off for unified. Unified np8 L32k 26.71 vs L64k 10.18 tok/s sum (about 99% pool occupancy; the 2.6x drop is unexplained, so no np8 decode figure should be quoted). Redo needs equal streams, `--no-cache-idle-slots` on both arms, a 32k anchor at start, middle and end with its unit, and the threshold predeclared (KVU-12.4 to 12.6; evidence research `artifacts/np_context_kvu_cpu_study_20261020/w2_20261021/`).
- **KVU-21 usage arm not judgeable; fraction arm leans toward closing CONCUR.** /slots pool usage is in no :8083 log; on agent-length resumes (prompt >= 2000) median recompute fraction is 0.065 at >= 3 busy slots (n = 43) and 0.014-0.015 at 1-2, all below 0.25; not conclusive (`/mnt/raid0/llm/tmp/analytics-20261020/KVU-21/REPORT.md`).

Sources: [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md), [heterogeneous slot fabric residency](../handoffs/active/heterogeneous-slot-fabric-residency.md), [Progress 2026-10-20](../progress/2026-10/2026-10-20.md).

Sources: [KPF-18 owner handoff](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [2026-10-21 workspace-f8 progress](../progress/2026-10/2026-10-21-workspace-f8.md), [KPF-18 staging record](../docs/reference/kv-prefix-fork-radix-lesson-and-vllm-copy-vs-share.md).


### 2026-10-21 hybrid cache reuse guard — pending integration

The [experimental kernel manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md) and [owner progress record](../progress/2026-10/2026-10-21-hybrid-cache-reuse-fix.md) describe experimental `8b08c9f25`: recurrent memory reports `can_shift=false`, and hybrid memory requires both component capabilities. The owner reports `can_shift=0` for two real models and six generated recurrent/hybrid cases, with a dense control reporting `1`. This remains pending integration and does not establish a production fold. Server pytest and Nemotron ctest are unrun; the reported controls do not substitute for those checks.


### Peer placement and prefill design refinements — 2026-10-21

[HSF-4 and WP-15](../handoffs/active/within-role-placement-state-machine.md) now require worker-merged dispatch/serving joins, role-specific uncached-length histograms, cached-token recovery costs and load-regime stratification before comparing placement rules. [PB-QCOST-1](../handoffs/active/gpu-serving-tie-in-program.md) requires held-out residuals and validation at the target decode concurrency before enabling the fitted prefill budget. These are prerequisites and proposed comparisons; deployment commentary and armed future GPU probes do not establish a local performance gain.

## Compiled Update — 2026-10-21 (sweep 4): the prefix-cache ceiling on real agent traffic, the hybrid shift guard, the radix lesson, and the KPF-17 conformance close

**Confidence: verified for the code facts and recorded runs named in the sources; the trace figures are measured on our own transcript stores (1,519 Claude Code transcripts plus sampled Codex and opencode sessions) and are OBSERVATION grade for what they imply about the planned REPL, memory and RAG paths, which have no real traffic yet.**

- **A prefix cache already captures about 99 percent of append-ordered agent traffic.** An ideal never-evicted prefix cache would capture roughly 98.7-99.2 percent of prompt tokens on those traces, and chunk reordering adds well under 1 percent (reorder-case repeats are 0.003-0.004 percent of prompt tokens). So non-prefix chunk reuse is not justified by coding-agent traffic. The operator framing (2026-10-21) is that chunk reuse is infrastructure for the planned REPL retrieval, episodic memory, SkillBank and document-QA paths, whose real reuse RTE-LOG-1 measures; the parallel lever on current traffic is making the prefix cache hit reliably on hybrid models (KPF-64: checkpoints at block boundaries, `--cache-ram`, eviction). Design of record: `/mnt/raid0/llm/tmp/cacheclip-port-20261021/DESIGN.md`; phase 1a (the exact, hybrid-safe reorder planner, KPF-61) stands at `a62f64d5` on an experimental tree, its manifest row V11-099 pending push.
- **`--cache-reuse` is not force-disabled on hybrids; the engine was wrong the other way.** At the champion `llama_memory_hybrid::get_can_shift()` returned true, and the recurrent memory also reported true while `seq_add` only rewrites `cell.pos`, so a KV shift left the recurrent state stale (silently wrong output). The fix (V11-098, `experimental/hybrid-cache-reuse-guard-20261021` @ `8b08c9f25`, pending fold, not in production) reports false for recurrent and ANDs both parts for hybrid and hybrid-iswa; `can_shift` is 0 on Qwen3.5-0.8B, LFM2.5-1.2B and six generated recurrent or hybrid architectures and 1 on a dense model. Behaviour change: `--context-shift` is now disabled on hybrid and recurrent models. No production role sets `--cache-reuse`, context shift defaults off and an overflow without it is loud, so nothing in production relied on it; the StreamingLLM sweep (dense Qwen3-1.7B) is unaffected.
- **The radix lesson.** The orchestrator's client-side radix router (about 480 lines, 20 green tests) never served a request and was deleted as dead code on 2026-08-20: a client-side prefix structure cannot share KV the server does not share. The revival as an index of where prefixes are (KPF-27) keeps three rules: the server is the source of truth, a key is the wire text, and it sits on a path every request crosses with a flag-off identity test. Done-when for any phase is a measurement on the live server.
- **vLLM copy versus share, by path (external, read from source; PR #46384).** A block-aligned hit shares both attention and recurrent state by reference; a partial hit copies the whole block page; a running owner of an aligned Mamba block moves the cache entry to a copy. The PR's single benchmark (0.0955 s versus 0.1337 s) is one self-reported run and is not citable as a performance claim. PR #53945's junction checkpoint ends the prompt chunk at the junction a sibling stopped at and publishes state there; it is reactive (the first occurrence pays full prefill) and prompt-bounded, whereas the fork's `checkpoint_at` names the junction up front. Full page: `docs/reference/kv-prefix-fork-radix-lesson-and-vllm-copy-vs-share.md`.
- **KPF-17 conformance closed (KPF-17.1a/b/c ticked).** All six failures of the morning re-check were test defects, two of them the author's own, not fork defects. The oracle `same_as_fresh` is now two-sided on top-2 logprobs with drift below 0.45 and flip distance below 0.6 (floors measured with the gates off); honest runs land at drift <= 0.157 and flip <= 0.050; the 35B+MTP suite passes 7/7 and the 192-thread run 18/18; 10 mutant arms fail as they should. Two new upstream notes: CH-18.b (SWA `pre_decode` re-decodes from a checkpoint whenever pos_next <= n_swa) and KPF-13.1a (skip the private drafter copy at the fork for plain drafters).

Sources: [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [Streaming LLM baseline](../handoffs/active/streaming-llm-baseline.md), [llama.cpp v11 manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md), [KV prefix fork radix lesson](../docs/reference/kv-prefix-fork-radix-lesson-and-vllm-copy-vs-share.md), [Progress hybrid-cache-reuse-fix](../progress/2026-10/2026-10-21-hybrid-cache-reuse-fix.md), [Progress workspace-f8](../progress/2026-10/2026-10-21-workspace-f8.md)


### Chunk-KV slice1 remains experimental — 2026-10-21

The [KPF-62 source record](../progress/2026-10/2026-10-21-dpf-kpf62.md) reports attention-only export/inject and tiny-model CPU checks at experimental `2b7e1c98d`; hybrids refuse this path. The owner also identified repeated application of the YaRN magnitude factor during K-shift and filed KPF-62.1. KPF-62 remains open: selection, sparse recompute, server wiring, continuation harness and speed slices remain. Neither the tiny-model checks nor the earlier P1a planner establish real-role equivalence, a timing gain or a production fold.

## Compiled Update — 2026-10-21 (sweep 5): the KPF-62 chunk-KV build is sliced for fresh agents

**Confidence: inferred.** These are filed task definitions; no slice below has run.

- **The slices after KPF-62.2 (the `chunk_kv.py` grading extension).**
  - **KPF-62.3, the selector.** A head window of W=64, a check-layer K deviation and group-contiguous runs, followed by auxiliary-model scoring that needs a K tap at a check layer.
  - **KPF-62.4, sparse recompute.** It runs by explicit-position batches beside the cache-reuse block, and G0 must be bit-identical at r=100%.
  - **KPF-62.5, server wiring.** It adds `--chunk-store-mib` (0 = off), a `kv_chunks` request field, isolated encode on a miss, a logged startup self-check and `prompt.approx=true`, with ctx_dft/MTP/DFlash2 coverage.
  - **KPF-62.6, the G3 harness.** It runs on the frozen corpus and needs the corpus manifest hash.
  - **KPF-62.7, the speed report.** It compares against tuned prefill including load, in a timing window.
  - **KPF-62.8, the real-role G1.** It runs on Qwen3-VL-30B-A3B Q4_K_M with f32 K/V in a CPU bench quarter, and it is in the inference queue.
- **The layout contract that would let chunk reuse hit on REPL retrieval** (REPL-EMB-6.1, filed earlier) sets the rules that inlined retrieval must follow:
  - chunks are fixed at 256 tokens;
  - small chunks are grouped into blocks of at least 256 tokens;
  - serialisation is byte-identical in any retrieval order;
  - reusable blocks sit after the stable prefix and before the volatile tail.

  No inlining path exists yet, so real reuse is still unmeasurable.

Sources: [KV prefix fork and paged attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [Current campaign](../handoffs/active/CURRENT-CAMPAIGN.md), [Progress 3c4ca599](../progress/2026-10/2026-10-21-3c4ca599.md), [REPL embedding retrieval](../handoffs/active/repl-embedding-retrieval.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 8, workspace-f8 delta over sweep 7)

- **KVU-12.2 MTP-on bank cells PASSED.** Candidate `dd3d9721c` (champion + #26004 + #30574) 4/4 cells: restored/live acceptance 0.98-1.02, decode 0.98-1.01, tokens identical. The unported control `4348de400` failed 4/4 (acceptance 0.53-0.71, decode 0.77-0.82), so the gate discriminates. ([kv-unified-stack-rollout.md](../handoffs/active/kv-unified-stack-rollout.md), [progress](../progress/2026-10/2026-10-22-workspace-f8.md))

## Compiled Update — 2026-10-24 (wrap-up sweep 9, delta over 2026-10-23)

- **KPF-13.1 plain-MTP CPU leg PASSED under rules v3.** K=3 same-shape controls per arm, `decision_grade` true: default A 12/12, B 12/12, skip-A 12/12 PASS. `restore_faithful` true, `fork_equals_cache_hit` true, `investigate` false, `trigger_port_30141` false; `kpf19_1_choice` = keep the full drafter KV through the fork, no re-prefill. The cold-twin `info_vs_twin` column (A 7/12, 6/12, skip-A 8/12) is informational only and gates nothing.
- **KPF-13.1a decided NO: keep `load_dft` for plain drafters.** Skip-A runs are not equal to default-A runs cell by cell on tokens / draft_n / draft_n_accepted (all three required), so skipping the drafter-KV copy at the fork is not shown output-equivalent.
- **KPF-13.1 DFlash2 GPU leg FAILS the rule (A 9/12, B 11/12 PASS) but only by near-ties.** `restore_faithful` false, `investigate` true, `kpf13_1a` NOT_MEASURED (SWA drafter). All 4 failing cells (g0-S2, g1-S2, g3-S2 on A; g2-S1 on B) diverge on tokens only, at first-divergence tokens 2/24/38/48 with top-2 gaps 0.0075/0.0059/0.0034/0.0167, all inside the near-tie band; acceptance is inside the interval in all four, controls agree 64/64. Deterministic, not run-to-run noise; the rule has no GPU near-tie pass, so the item stays open. An earlier launch aborted (rc 3, zero cells) because the read-back rejected the ROCm helper thread that resets its own affinity; the driver now exempts up to 2 full-mask threads on GPU runs (85/85 tests).
- **Hybrid serving rule (KPF-64): never set `--ctx-checkpoints 0` on a hybrid role.** On frontdoor (Qwen3.6-35B-A3B-MTP Q8_0, np=4, CPU, v10; 19 paired sessions / 388 requests), checkpoints off lose 3.9 pp of prefix-hit share (95% CI [-6.42, -1.99]) and about 1,400 extra uncached tokens per request versus 32 checkpoints. A `--cache-ram` tier (2 or 32 GiB) added nothing measurable at np=4; untested above 4 lineages (KPF-64.3 pending). Frontdoor already runs 32 checkpoints plus `cache_ram` 32768; no registry or manifest declares `ctx_checkpoints`, so the llama-server default of 32 is load-bearing and a kernel default change would silently alter production.
- **Unified-stack fold decisions.** KVU-19b-rework commit 2 (WMMA exact/straddle tiles) is DROPPED from v11 by operator decision: about 14% slower on aligned verify, skip on/off exactness breaks 6/119. CPU-FA-VKQ-1 (`2ad8bff36`) is closed as superseded: the champion carries the hybrid FP16 + overflow-recheck port (V11-086), with the register-resident arm as live successor (gate HOLD). V11-FA-6 (#27870 for DF2-9): code is in the champion; the owed gate is `test-backend-ops -o FLASH_ATTN_EXT` 640/640 plus the df29 10-run probe.

Sources: [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md), [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md), [ufh14-b4-prefix-cache-policy](../docs/design/ufh14-b4-prefix-cache-policy-20261003.md)


## Compiled Update — 2026-10-24 (wrap-up sweep 23, workspace-f8): the GPU fork divergence splits by device, and a layout confound

- **The GPU and CPU fork legs point at different loci.** On the MI210, KPF-13.1b became decision-grade `target_restore_defect`: with no drafter loaded, the fork child still differs from its token-identical controls. On CPU, the KPF-19.1a leg reads `c1_locus = drafter_on_only`: honest and flag-on pass, and both mutants are detected. So the GPU c1 divergence is not a property of the fork protocol itself. (Sources: `handoffs/active/kv-prefix-fork-and-paged-attention.md` KPF-13.1b and KPF-19.1a notes; `progress/2026-10/2026-10-24-workspace-f8.md` Afternoon section.)
- **KPF-17.4b's GPU reading was confounded by KV cell layout.** Its control was seeded with the source resident, so its cell layout differed from the fork's. The layout-matched KPF-17.4c bisect then did not reproduce the c1 divergence (`locus = none_reproduced`, decision-grade; read-out by rule pending). Lesson: a fork-vs-control comparison must match cell layout and occupancy, not only tokens. (Sources: KPF-17.4c task and finding in the KPF handoff; the 10-24 progress shard; `/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf17-4c-bisect/PREDECLARATION.md`.)
- **The KPF-18 item 3 cold floor was degenerate.** R3's six cold pairs gave only two distinct values (A≡C, B≡D), and no cold arm ran at the child's slot occupancy. R4 therefore adds a cold arm at the child's occupancy and a child A/A before calling the 60k fork deviation fork-intrinsic. (Sources: KPF-18-S1.R3 / R4 in the KPF handoff; the R4 PREDECLARATION; the 10-24 progress shard.)
- **KVU-12.3 is closed only for quiet traffic.** The predeclared fallback pooled all concurrencies when only 5 turns had ≥3 busy slots, so the 4.52% generated-span re-prefill (bar 5%) says nothing about load. KVU-12.3b re-checks on the busy subset once traffic exists. (Sources: `handoffs/active/kv-unified-stack-rollout.md` KVU-12.3a/b; `/mnt/raid0/llm/tmp/analytics-20261024/KVU-12.3a/PREDECLARED.md`; the 10-24 progress shard.)

## Compiled Update — 2026-10-26 (wrap-up, workspace-58)

- **Unified-KV rollout live front**: OP-54 GPU residency is applied and serving-proven (:8083 `-np 4 -c 196608 --kv-unified`, speech on CPU). Remaining: kernel candidate v11 (guarded), measurement follow-ups (HPR-b 64k holdout, KVU-12.3b busy-subset re-check), speech residency. ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md), [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md))
- **HPR prefix-capture reader enrolled in the existing `np-ctx-kvu-measurement` family** (no new grading rule): 110 model-free cases and a 6/6 synthetic preflight pass, synthetic scope only; historical HPR-B `INVALID_SIM_DISAGREES` is not regradable, and the native contract stays UNVERIFIED until a golden control. HPR golden v3 later PASSed for instrument equivalence only. ([HPR enrollment](../progress/2026-10/2026-10-25-hpr-prefix-enrollment.md), [workspace-58 log](../progress/2026-10/2026-10-26-workspace-58.md))
- **KPF-64 serving rule stands**: do not set `--ctx-checkpoints 0` on hybrid roles; fan-out TTFT about 8.5x is candidate-grade. ([week outcomes](../docs/reference/inference-outcomes-week-2026-10-18-to-25.md))

Sources: [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md), [HPR enrollment](../progress/2026-10/2026-10-25-hpr-prefix-enrollment.md), [week outcomes](../docs/reference/inference-outcomes-week-2026-10-18-to-25.md)

## Compiled Update — 2026-10-27 (operator wiki sweep, workspace-58)

**Confidence: verified** (each bullet is a recorded verdict against a predeclared gate unless marked).

- **KVU-16b is closed: the 393216 pool holds four long contexts while all four decode.** The corrected runner (KVU-16b-1) uses the `request-task-prompt-end-v1` predicate on champion c72ec82f5/10419, `-np 4 -c 393216`: 324,673 resident cells with 4/4 requests decoding (gate >= 300,000), KFD peak 48.57 GiB (gate <= 62), 0 failed requests, slot errors or faults, 898 residency samples. One replay, so it is a capability proof, not a throughput claim. This matters because production runs `cache_idle_slots` ON, so parked slots never prove residency; only decoding slots do. ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) KVU-16b / KVU-16b-1; [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); [2026-10-26 log](../progress/2026-10/2026-10-26-workspace-58.md))
- **Unified KV at np8 L64k on one CPU quarter: SPLIT_BETTER (PROPOSED until the KVU-12 owner ratifies).** Decode sum 10.49 vs 20.63 tok/s (-49.2%, threshold 25%), per stream 1.41 vs 2.54 (-44.5%), TTFT +2.2% (threshold 3%), GPU idle in both arms. It ran at q3, `-t 24`, so it is not comparable to the 10-21 redo. ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) KVU-12.5; [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); artifact `/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/VERDICT.json`)
- **KVU-16g-1 prefill-budget read-out: no arm meets the done-when (>= 4x decode-during-neighbour at <= 30% TTFT cost).** b512 x3.22 / +21.5%, pb512 x2.92 / +26.7%, t1000 x3.87 / +44.8%; one sample per arm against an OFF arm that is not the served optimum. Descriptive only; no flag is enabled and prospective g-2 measurements are owed. ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) KVU-16g-1; [2026-10-26 log](../progress/2026-10/2026-10-26-workspace-58.md); `/mnt/raid0/llm/tmp/cal-1026/kvu16g1-fa4-audit/OWNER-READOUT.md`)
- **CME-7S: the prompt-prefix cache gate passes on the poker smoke.** `hit_ratio_prompt_prefix` 0.9977 against 0.95; `hit_ratio_reusable` 0.951 is printed but no longer gates, because generated tokens are never reusable and cap it near 0.91 on this model. The misses split into 13,475 unreusable generated tokens, 0 history rewinds and 633 lost prompt-prefix tokens (about 13 per call). Correctness-only. ([conversational-memory-eval-instrument](../handoffs/completed/conversational-memory-eval-instrument.md) CME-7S; [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); `/mnt/raid0/llm/tmp/cme7-poker-out-s2/run-20261023T003634Z/`)
- **A client-side stagger does not land sibling requests on a cached prefix (RTE-PFX-2, negative).** On the hybrid frontdoor (Qwen3.6-35B-A3B MTP, `-np 4`): simultaneous 0/20 hits; `hold_first_tok` 0/15, with siblings landing on empty slots; `hold_first_end` reuses 1 of 3 siblings per trial at about 69% cache (gate 90%). The fix belongs in slot selection or the checkpoint-fork path (KPF), not the client. ([repl-turn-efficiency](../handoffs/active/repl-turn-efficiency.md); [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); `/mnt/raid0/llm/tmp/qb2-rtepfx2/run-20261023T094104Z/probe.json`)
- **CH-26a M12 long-context reader recipe on C5: PASS 9/9.** Warm cache share is 0.980-0.99996 (gate >= 0.95) and warm processed tokens are <= 2052 (gate <= 4100) on 35B-MTP np4 and 27B-DFlash2. One sample per leg, no speed claim; the research recipe doc still has to be re-anchored on c72ec82f5 (CH-26a.1). ([autokernel-champion-aggregate](../handoffs/active/autokernel-champion-aggregate.md) CH-26a; [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); [2026-10-26 log](../progress/2026-10/2026-10-26-workspace-58.md))

Sources: [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md), [conversational-memory-eval-instrument](../handoffs/completed/conversational-memory-eval-instrument.md), [repl-turn-efficiency](../handoffs/active/repl-turn-efficiency.md), [autokernel-champion-aggregate](../handoffs/active/autokernel-champion-aggregate.md), [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md), [2026-10-26 log](../progress/2026-10/2026-10-26-workspace-58.md)

## Compiled Update — 2026-10-27 (operator full wrap-up, Codex NI, cutoff 14:56:35Z)

**Confidence: verified** (accepted task receipts and source records listed below).

KPF R15’s native attempt is scientifically invalid: the required `gate.pid_owns_port` check was absent before seeding HTTP, so rc 0 is not a geometry result. The listener-repair successor passed entry-path controls and enrolled, but PF refused the run because the declared 64 GiB output would leave 144.28 GiB free, below the 150 GiB floor. No threshold was lowered and no normal-run claim is made.

Sources: [KPF handoff](../handoffs/active/kv-prefix-fork-and-paged-attention.md) · [GPU serving](../handoffs/active/gpu-serving-tie-in-program.md) · [2026-10-27 Codex full wrap](../progress/2026-10/2026-10-27-codex-ni-full-wrap-1456.md)

## Compiled Update — 2026-10-28 (operator wiki sweep, workspace-58)

**Confidence: verified** (accepted receipts; diagnostic/tiny-model results marked as such).

- **KPF-62.3 selector port is scoped, not measured.** NI owns the port on an isolated branch from C5 `c72ec82f5`: mandatory head W=64, check-layer K-deviation scores over chunk-relative 64-token groups, group-contiguous recompute runs, all paths off by default. Stage A is offline selector quality (no speed claim; `llama_decode()` computes the full graph); Stage B (partial-layer online path) only if Stage A wins. C5 lacks the earlier chunk-KV infrastructure, which must be ported first. No inference, quality or performance claim. ([KPF handoff](../handoffs/active/kv-prefix-fork-and-paged-attention.md))
- **Tiny generated-model CPU controls pass (diagnostic only).** `KPF623_CONTEXT_V_CVEC`, `KPF623_LAYER_TAP`, `KPF623_R100_IDENTITY` PASS on qwen3, `KPF623_HYBRID_REFUSAL` PASS on qwen35; four pre-existing G0 controls also pass. The attention-callback smoke emitted four finite chunk-token scores, and flash-enabled decode hit the expected refusal. Independent full-attention-oracle validation, real cross-vocabulary alignment and G3/role quality remain owed. ([KPF handoff](../handoffs/active/kv-prefix-fork-and-paged-attention.md))
- **KPF-64.3 EB contrast: the 48-core arm loses badly.** EB realised 23.07% vs ideal 93.89%; E(D)-EB -71.61 pp [-91.44, -49.88] is real, E-D +0.20 pp [-0.0015, 0.67] is not (paired-by-session bootstrap, B=2000; 19 sessions / 388 requests). F is done; FB is NOT done (10 consecutive 4 h grants hard-ended rc=124), so there is no F-FB contrast. Arm E itself realised 93.35% vs 93.89% ideal. ([KPF handoff](../handoffs/active/kv-prefix-fork-and-paged-attention.md))
- **KPF-18 R14 and KPF-17.4d c1 are ticked.** The r3 CPU replay of the R6 X1 bridge completed rc0 (1,128 grids / 8 events, all payload hashes verified; recorded framing only, historical R6 stays INVALID). The c1 raw oracle passed honest 2/2 and flag-on 1/1 with exact top-2 over 64 tokens. ([KPF handoff](../handoffs/active/kv-prefix-fork-and-paged-attention.md); [KPF-62 native G1](../progress/2026-10/2026-10-27-kpf62-native-g1-result.md))
- **V11-FA-4b recorded-scorer diagnostic: not a quality-equivalence pass.** `agreement_all_configs=false`; 200 scored / 100 greedy pairs per config. C5 ON-OFF paired deltas: q8/off -0.5 pp [-2.5,+1.0], q8/on +1.0 [0,+2.5], f16/off +1.5 [0,+3.5], f16/on 0 [-2,+2]; only f16/on met the +/-2 pp rule. 98-105 outputs per arm were length-truncated. No timing or promotion claim; the parent box stays open. ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md))
- **KVU-LB1.d frontdoor F16-V quarter diagnostic: NO_COST.** Per-cell median effects vs F32: n1/8192 +0.60%, n1/32768 +5.92%, n5/8192 -0.40%, n5/32768 +8.88% (sign per the verdict file); single attempt. ([kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md))

Sources: [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) · [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) · [KPF-62 native G1](../progress/2026-10/2026-10-27-kpf62-native-g1-result.md) · [2026-10-28 workspace-58](../progress/2026-10/2026-10-28-workspace-58.md)

## Compiled Update — 2026-10-31 (operator wiki sweep, workspace-58)

**Confidence: verified** for filed native records (KPF-18.1 CPU subset, KPF-18.3 attribution, FA4 R17 collection); GPU KPF-18.1 and component-custody are unmeasured; no placement floor, parity, quality or performance verdict yet.

- **KPF-18.1 CPU subset (35B Q8): fork predictions hold, outer run failed on harness.** Native job rc0 with 42/42 record hashes verified: A checkpoint 3/3 at 4096, B 4/4 predicted and within the fresh floor, D (MTP and no-drafter) 9/9 predicted with held-out drop 0, C 16/16 fork-at-L with MTP on and off within the pooled fresh floor. The outer run is a FAILED-RUN (final launcher omitted --complete-cmd) and `task_gate_complete=false`; slot-versus-response fork-count observations still differ across records, which the offline collector audit attributes to capture phase (response timings precede slot release; /slots is read after completion), not to a native fork failure. ([source](../handoffs/active/kv-prefix-fork-and-paged-attention.md))
- **KPF-18.3: fork-on vs fork-off is mostly but not fully token-identical.** In the disjoint 35B Q8 two-case successor (12 HTTP 200), fork-on matched fork-off on 10/12 sequences and the e332 champion on 8/12; on matching sequences the max selected-token logprob difference was 0.0622 (vs fork-off) and 0.1393 (vs champion). Compilers/builds differ between champion and experimental, so this is not a parity gate. Delimiter/role-span and checkpoint events were joined by task ID (28/28 match raw traces); of 20 candidate checkpoint decisions, 8 were user-start (4 with checkpoint at start 32). Raw reply coverage had one-token gaps (siblings forked at 40/41 and 45/46). ([source](../progress/2026-10/2026-10-31-codex3-kpf-td29-results.md))
- **e332 HIP and GPU KPF-18.1 are built/started but unresolved.** The exact-e332 gfx90a build finished (455/455 steps, own-image linkage, version e332293486) with no model load or GPU comparison. The GPU 27B R3 run's first segment ended rc75 on STOP; of 170 recorded cells, active-slot evidence is observed for 156 and unknown for 14, with one interrupted exposed baseline unit that must not be replayed. No full-grid verdict. ([source](../progress/2026-10/2026-10-31-kpf181-gpu-first-segment.md))
- **KPF-18.2 component-custody observer and raw-trace builds exist; no component hit measured.** A default-off native observer reported sequence-owned attention intervals and recurrent boundary metadata on a public 0.8B control (forks at 302 and 310, all three paired token arrays matched), and CPU plus HIP raw-trace servers were built with same-build linkage. Component hits, the minimum and restore success remain null. ([source](../progress/2026-10/2026-10-31-kpf182-v3-runtime.md))
- **FA4 exact-set R17: inputs match, outcomes differ on six keys.** After R14-R16 harness races (16 MiB smoke cap, transient /proc/exe loss) were separately diagnosed, R17 completed rc0: 228 unique cases per arm with arm checks OK; outcomes differ on six keys (ON-only two, OFF-only four) across three pairs, 22 bands, two KV types (132 band-pair records). Earlier ON arms showed 224 OK / 4 NONFINITE (bias1024/diffuse tail, f16 and q8_0); this is an outcome, not equivalence, mechanism or performance evidence. ([source](../progress/2026-10/2026-10-31-codex-ni-fa4-r17-qualified-ready.md))
- **UFH14-LB5.1 prefix stability confirmed for four templates.** 35b-terse, 27b-embedded, vl-embedded and fn-embedded each passed four original fixtures plus shared trunk under the predeclared all-four rule (CPU template rendering and tokenization only, with loaded-model residency samples); no GPU compute or throughput claim. ([source](../progress/2026-10/2026-10-30-codex3-fa4-lb51-filing.md))

Sources: [kv-prefix-fork-and-paged-attention](../handoffs/active/kv-prefix-fork-and-paged-attention.md) · [kv-unified-stack-rollout](../handoffs/active/kv-unified-stack-rollout.md) · [KPF-18.1 CPU/FU03](../progress/2026-10/2026-10-31-codex3-kpf181-fu03-results.md) · [KPF TD29](../progress/2026-10/2026-10-31-codex3-kpf-td29-results.md) · [KPF GPU first segment](../progress/2026-10/2026-10-31-kpf181-gpu-first-segment.md) · [FA4 R17](../progress/2026-10/2026-10-31-codex-ni-fa4-r17-qualified-ready.md)
