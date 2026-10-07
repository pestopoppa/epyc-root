# Stage-3 PLAN rev2.1 (APPROVED 2026-10-07) — Q38FN 2x DGX Spark physics intake

Status: rev2.1. Operator approved rev2 with the +5.0% go/no-go ("approved. Proceed to stage 4"). rev2.1 = rev2 with (a) packet IDs relabelled to the v2 convention (P = immediate task-bearing, K = knowledge/gated closure; old -> new: M1->P1, P1->K1, P2->P4, P3->K3, V1->P2, I1->K4 with I1b->P3, I1a/I1c->K4a/K4c), (b) the host-driver fact the operator relayed on 2026-10-07 added to P2, (c) the machine-checkable v2 payload added. No scope change. Task IDs Q38P-1..Q38P-4 are allocated against origin/main (no collision).

## 0. What the evidence settled (quotable; all from dive-verified entries)

- Two-Spark aggregate bandwidth (2 x 273 = 546 GB/s, intake-1943) is within 2% of our theoretical 537.6 and above our measured 446.8 read-sum, but it is not pooled for one stream. Like-for-like (official 10-expert NVFP4, TP2, thinking off) the independent median is 53.7 tok/s (intake-1948/1949); ours is 52.66 (champion MTP). The 93/177 headline is a 5-of-512-expert healed INT4 model with MTP up to K=7 and a best-window peak (intake-1937/1939). No physics violation and no like-for-like gap.
- The real gap is streaming efficiency: Sparks run kernels at 80-87% of 273 (intake-1951, 1958); we stream ~137-174 GB/s = 31-39% of 446.8 (derived, INTAKE_STAGE2.md physics table).
- Correction to my own earlier Stage-2 text: the draft-head vocab trim is NOT a lever on our CPU (our B10, cpu-decode-roofline-program.md ~L3634: head ~4-5% of the token, L3-resident; ceiling +3.0-3.9%; break-even on alpha). Retracted in INTAKE_STAGE2.md and in the dive_corrections of intake-1950/1955/1956.
- The 9.1-11.6 GB step estimate used independent expert routing. The only measured union (author-measured, intake-1951 wave 4) is 0.69/0.63/0.60 of independent at 4/8/16 rows, so the estimate is an upper bound and the 80-100 tok/s headroom figure is a rough derived estimate that the P1 measurement must replace.

## 1. Packets

Postures per skill: primitive-now / cheap-screen-now / full-reproduction-now (fired trigger) / monitor / knowledge-only / decline. Model tier = cheapest capable per the operator rule; main (opus) reviews every packet; no Fable.

### P1 — MEASUREMENT: our Q38FN MTP step bytes, expert union, streaming GB/s (posture: cheap-screen-now; ENABLES K1/K3, replaces derived numbers)
- Decision it can change: whether lever K1 is worth an AK campaign slot (headroom 2x vs ~1.2x), what K/R to sweep in K3, and whether the INF-70 roofline ledger row for Q38FN MTP step bytes can be filled with a measured value.
- Owner: `handoffs/active/cpu-decode-roofline-program.md` (it already carries C0/C1/C2/C4 instrument rules: report achieved GB/s vs C0, sanity assertion per instrument, control arm per claim). Consumers: `moe-routing-tap-and-locality-measurement.md` (RT-1 tap supplies the router ids; RT-5 is the Qwen3.6 skew report, distinct), `autokernel-research-loop.md`/AK campaign `ak-q38fn-cpu-decode-20261003` (recipe `q38fn-cpu-t48-mtp-d4`, K=4 draft) for the lever table, `speculative-decoding-mtp-refresh.md` (CAFE-2 consumes the curve). No duplicate tasks for consumers.
- Smallest deliverable: one table for the served Q38FN recipe (UD-IQ4_XS, `-t 48`, MTP d4; plain and MTP arms) with (a) bytes/step static from the GGUF tensor table incl. K+1 GDN state writes, (b) measured distinct experts per layer vs verify rows R=1..6 and drafter rows from the router-id tap, (c) tokens/step (alpha) per prompt class, (d) step ms, per-op-class achieved GB/s from the existing node/PATHROW profiler against C0 (446.8), and (e) implied total GB/s and fraction of read-sum.
- Which parts need a timing window: (a) static arithmetic from the tensor table and the GDN state-write arithmetic: NO window (clerk). (b) expert-union and (c) tokens/step are COUNT measurements: correctness/accounting only, insensitive to contention, but they run the server so they take the CPU region lock (`region-lock run --cpu-list 0-95`) and must not overlap a timed arm; use a diagnostic/ID-tap build or the existing tap, never the production binary. (d)/(e) step ms and GB/s ARE timing: need an AK CPU window (flock is truth), a warm run, node-profile build as a non-measured sibling, build/knob proven compiled in (`strings`), residency proven. Nothing here is a headline; label research-instrument.
- Six controls: frozen input manifest = the AK prompt manifests already in the campaign inputs (`q38fn-decode.prompt-manifest.json` and held-out one) plus digest of the GGUF and binary; baseline = frozen production v10 `ffc1bac82` with the champion recipe; per-item raw outputs retained (router ids per call, per-step timings); holdout = the held-out prompt manifest for tokens/step; complete denominator = all calls counted incl. catch-up evals with logits=0 (B10 lesson); predeclared decision rule: accept the measurement only if the instrument passes its sanity assertion (reproduces the 4.16 GB plain per-token table and the known 53 tok/s within the stated between-launch noise) and the node timings reconcile to the step wall within 2%.
- Stop rule: if effective streaming is already >= 60% of read-sum (>=268 GB/s) the lever K1 is closed as 'no headroom'; otherwise K1 proceeds.
- Model tier: static table and union analysis = sonnet clerk; timing arm = sonnet runner under main supervision; interpretation/review = main (opus).

### K1 — streaming efficiency toward >=270 GB/s via the dispatch/barrier floor (posture: AK-seed + REBUILD-candidate; gated on P1)
- Decision: whether the CPU decode floor can move from ~140 toward 270 GB/s effective (about 2x on the plain path; spec-aware gain smaller).
- Merge, do not duplicate: INF-70 axes in `cpu-decode-roofline-program.md` (dispatch floor ~7.9k graph nodes/token, DS41-C57 libgomp barrier-sleep, C5 re-anchor), the cafe-llama seeds already filed there (CAFE-5 REBUILD GDN raw gates/rows for qwen35moe, CAFE-6 seeds AK-A/AK-B) and the AKX-ALL-25 injection of AK-A/B/C/G in `autokernel-all-devices-all-dimensions.md`. The new external contribution is only an acceptance criterion and two measured Spark reference points: kernels at 80-87% of peak with a fixed ~8-11 ms/cycle overhead independent of K (intake-1951 wave 4), small mid-size reads carry a per-kernel overhead, and GDN verify kernel at 145-148 GB/s is latency-bound. These become a comparison column in P1, not new AK seeds.
- Proposed single row (an addendum line to the roofline program, not a new task unless P1 says go): 'Q38FN streaming efficiency target: per-op-class achieved GB/s vs C0; interim target weight-path nodes >= 60% of read-sum (>=268 GB/s) in aggregate'.
- Predeclared acceptance (for any lever under it): keep only at >= +1.0% above the window floor (same rule as CAFE-1), greedy identity 100%, matched-process A/B with >= 5 interleaved pairs, held-out prompts, per-op-class GB/s reported for every row (C1). REBUILD items follow the production-kernel immutability rule: experimental branch from a fresh production pull, full-candidate promotion, no cherry-picks.
- Model tier: AK loop actors as configured; opus for the kernel-lane review; no new model class introduced.

### P4 — draft-head byte reduction (posture: decline for vocab trim; cheap-screen for head requant only; knowledge for Spark evidence)
- Decision: whether any draft-head change is worth CPU effort. Evidence: our B10 closed the vocab trim as NO-GO (head L3-resident, break-even alpha, +3% ceiling, upstream #25187 +1.4%). Spark gains (+9.6% mean, code x1 +21.5%) are GPU/DRAM-resident-head effects (intake-1950, 1956).
- Retained single item: B10's already-recorded 'cheapest remaining probe, no code': requantise the head to IQ4_XS into the MTP GGUF slot `blk.48.nextn.shared_head_head` (521 -> 338 MB, expected +1.4-1.8%). It already belongs to the roofline program (B10 record); this plan only asks the owner to either schedule or decline it after P1, by the predeclared gates: greedy output identity 100% (target verifies), alpha change <= 0.01 absolute (measured on the held-out manifest), aggregate >= +1.0% above the window floor with >= 5 interleaved pairs, complete denominator. Quality is unaffected by construction because the target model verifies every drafted token; the gate is acceptance and speed.
- Declined: reduced-vocab slice / frequency-ranked top-64k builder (B10 NO-GO; FR-Spec paper numbers, intake-1955, are for 128k-vocab dense models with a one-layer EAGLE-2 draft and must not be carried).
- Model tier: sonnet (GGUF requant + A/B under supervision).

### K3 — adaptive MTP depth (posture: merge into existing CAFE-1/CAFE-2/CAFE-3; no new task)
- Decision: whether an online depth controller beats best static K (currently d4) on the CPU MTP chain.
- Owner: `handoffs/active/speculative-decoding-mtp-refresh.md` (CAFE-1 flag-only p-min sweep, CAFE-2 verify cost curve, CAFE-3 REBUILD re-probing controller; acceptance P9 >= +1.0% over best static, identity 100%, absorbing-state test).
- What this intake adds, as proposed edits to those existing rows' notes (not new rows): (i) the myllmbox/jschmied/MiaAI controllers all use per-position acceptance thresholds with promote/demote bands (kit config: promote [60,45]% / demote [25,15]%, min depth 3, window 48; intake-1937) as a prior for CAFE-3's controller parameters; (ii) measured Spark cycle cost is near-linear, about +4.8 ms per added draft and flat 1.2x floor ratio (intake-1951), so CAFE-2's decision rule (T(5)/T(1) <= 1.25 declines the cost model) should be evaluated using the P1 measured expert-union curve rather than an independence model (measured union 0.60-0.69 of independent); (iii) include d in {3,4,5,6,7} in the CAFE-1 sweep because our AK recipe is d4 and external stacks gain up to K=5-7 on code only (prose acceptance collapses: code 3.15 vs English 1.23 accepted per step, intake-1958).
- Acceptance: unchanged from CAFE-1/3 (predeclared there). No duplicate gate.
- Dependency note: CAFE-2 and the P1 union capture share instrumentation; run P1(b) first so CAFE-2 does not re-derive it.
- Model tier: sonnet runners, opus review (as the owning rows already specify).

### D1 — OPERATOR DECISION: the 5-of-10 routed-expert cut — CLOSED: "Decline for now" (operator, steering row S6)
- Disposition: declined for now. No task, no eval, no checkpoint work. Fact base retained in intake-1939 (config `num_experts_per_tok=5`; shared-expert-only KL healing; card's own capability numbers disagree, 49.3 vs ~47 vs 51.8 original).
- Reopen trigger (durable prose, no checkbox): P1 shows routed-expert bytes dominate our step AND K1 headroom is closed. Until then it stays declined.

### P2 — VALUE ASSESSMENT: does ROCm 10.1 improve OUR MI210 llama.cpp HIP build? (posture: cheap-screen-now, staged so the reboot is the LAST thing that happens; operator steering S4)
Operator position (S4, verbatim in section 3): willing to reboot as part of v11 kernel promotion IF ROCm 10.1 has value. This item defines how to find out cheaply and predeclares the go/no-go.

What the 10.1.0 notes actually say, claim by claim (source: https://rocm.docs.amd.com/en/docs-10.1.0/about/release-notes.html, retrieved 2026-10-06, saved dive-1944/r101_release-notes.txt; intake-1944 anchors):
| Candidate improvement | What the notes say | Verdict |
|---|---|---|
| LLVM 24 codegen for MMQ_MFMA / rocWMMA FA | Only the component row: LLVM 24.0.0, ROCr 1.21.0 (release-notes L1353-1360, "10.0.0 => 10.1.0"); the blog adds "LLVM 24 ... new features and optimizations from the LLVM community" and faster rebuilds via LTO partition caching. NO statement about MFMA, gfx90a codegen, spills or occupancy. Our own record: MMQ on gfx90a sits at the 256-VGPR cap (J=64 Q8_0: 256 VGPR, 37 spilled; wiki/hardware-optimization.md L5922) and "no toolchain reduces vector-ALU VGPR; newer ones carry hazards" (L545-556). | UNCITED upside; testable only by compiling. AK-HYPOTHESIS. |
| hipBLASLt / rocBLAS | hipBLASLt 1.4.1 unchanged (L1270); rocBLAS 5.7.0: gfx950 GEMM defaults to hipBLASLt (L1683, not gfx90a), gfx90a syrk/herk OOB fix (L1689); our hot paths are ggml MMQ/MMVQ/rocWMMA, not rocBLAS GEMM. | No lever. |
| rocWMMA | 2.2.1 unchanged (L1318); no 10.1 changelog section. | No lever. |
| HIP graph capture | 10.0 added rocprofv3 per-graph-node attribution (r100 L420) and 10.1 graph-safe table (rocWMMA/CK flagged not graph-safe, a library-API label that contradicts our working rocWMMA FA + graphs). Nothing that speeds capture/replay. | Tooling only (profiling of captured decode graph); no speed claim. |
| Runtime / driver overheads | The only gfx90a runtime item is a PENALTY: with ROCm >=7.14, per-launch scratch-memory reclaim degrades RCCL; workaround `HSA_NO_SCRATCH_RECLAIM=1` (L1677). Scratch is exactly what our spilling MMQ kernels use, so this is a risk and a knob to test, not a gain. No decode-latency or launch-overhead improvement is claimed for gfx90a. | RISK + knob. |
| FP8/FP4 | CDNA2 crossed out for all fp8/fp6/fp4 rows (precision-support); no new CDNA2 dtype. | None. |
| Frameworks | vLLM 0.29 / SGLang 0.5.18 in the 10.1 matrix do not list gfx90a, but vLLM's own current docs do (see K4). | See K4. |
Bottom line: the 10.1.0 release notes contain no cited gfx90a performance improvement. Any value would come from compiler codegen on our register-bound kernels and is an UNMEASURED hypothesis that the existing runbook (docs/runbooks/rocm-upgrade-checklist.md) already says to expect to regress ("expect a plain upgrade to regress"; LLVM 23+/TheRock 10.1 default offload-LTO, runtime-unroll hazards, MFMA VGPR-vs-AGPR form change).

Compatibility with the CURRENT driver (needed before any reboot decision):
- 10.1.0 compatibility matrix lists amdgpu (kernel) driver versions 31.60.0 ... 30.10.2 for Instinct (r101_compatibility-matrix L298-312) and lists MI210 (gfx90a). The docs state a coordinated firmware/driver/userspace stack (L240-244) but give no statement that 10.1 userspace runs on an older driver.
- Our driver (host fact, reported by the operator 2026-10-07): on the host, `modinfo amdgpu | grep -E '^version'` and `dkms status | grep -i amdgpu` both print NOTHING, so amdgpu is the in-kernel upstream driver of host kernel 6.14.0-37 (no DKMS or amdgpu-install package). Userspace is ROCm 6.2.0-66 (AMD clang 18.0.0git); KFD node gfx_target_version 90010 = gfx90a. What the 10.1.0 docs say about that: the Instinct driver column lists only packaged amdgpu versions 31.60.0 ... 30.10.2 (compatibility matrix L298-312); the prerequisites page says "For Instinct and Radeon devices, install the AMD GPU Driver (amdgpu)" and reserves the "inbox kernel driver" for supported Ryzen APUs (Ubuntu 26.04 / 24.04.4; r101_prereq L843-853, compatibility matrix L404-405); the Ubuntu 24.04 kernel columns I read list GA 6.8 / HWE 7.0 and no 6.14 line. So the docs do NOT establish that 10.1 userspace supports the upstream in-kernel driver for MI210; that is the open question stage 1 must settle by test, not by assumption.

Cheapest staged test (each stage has a predeclared stop; the reboot only happens at stage 3):
- Stage 0 (no GPU, no reboot, no timing window, CPU region lock for the compile): non-root tarball install of 10.1 Core SDK (family `gfx90a`, side-by-side; transition-guide) into /mnt/raid0/llm; build the gfx90a MMQ/MMVQ/MMA-FA/rocWMMA-FA TUs of the experimental tree, compile-only, and run the runbook's zero-GPU static audit (VGPR, spill, scratch bytes/ops, agpr_count/accum_offset, drains) across {offload-LTO default, `-fno-offload-lto`} x {default unroll, `--amdgpu-unroll-threshold-local=600`} vs the 6.2 build; method `artifacts/gpu-aux-baselines/a10_iq2_vgpr_compiler_ab_20260915.md`. Stop (NO-GO, no reboot) unless some cell shows fewer spills / no worse VGPR on the hot kernels than 6.2. Because the host runs the in-kernel driver, stage 2 would ALSO have to decide whether to install the packaged 30.x/31.x amdgpu driver (a change to the serving host's driver, not only a reboot) or whether 10.1 userspace works on the in-kernel driver; that choice is part of the v11 window's go/no-go and is the operator's.
- Stage 1 (GPU claim; timing window only for the A/B): establish whether 10.1 userspace supports the in-kernel upstream amdgpu driver (the docs are silent for Instinct, see above). The natural test is P3's container with bundled userspace (a ROCm >=6.3/7.x image; ideally a 10.x image if one exists) on the live driver: a trivial HIP kernel, then a small-model correctness run, load/coherence only; if that passes, run the same check with the side-by-side 10.1 tarball userspace, then a side-by-side champion build and an MI210 same-window ABA vs the 6.2 champion, with `HSA_NO_SCRATCH_RECLAIM` arms. No reboot, no production change. Gate G1 below.
- Stage 2 (inside the v11 promotion window; needs the operator reboot): only if Stage 0 passes and the driver must change. The reboot is combined with the v11 promotion window (kernel-promotion skill) so it is paid once; the candidate is built on 10.1 and gated against the incumbent with the standard speed + quality gates plus G1/G2; failure rolls back to 6.2 (rollback anchor = v10 kernel store, ROCm 6.2 tree untouched).
Predeclared go/no-go (G1 speed, G2 quality; X may be edited by the operator before approval):
- G1: keep 10.1 only if the paired MI210 serving-gate decode tok/s on the production GPU roles is >= +5.0% (median of >= 5 interleaved launch pairs per arm; this is above the paired-median noise implied by the recorded v10 serving floor, p95_dev 7.249%, CI [6.024, 9.371], n=24, promotion_gates.yaml L130-134, which is ~3.2% at n=5 under 1/sqrt(n) scaling [derived]) AND prefill not worse than -2.0% AND zero new VGPR spills on the hot kernels in the static audit.
- G2: coherence gate at production prompt length passes and the promotion_gates.yaml quality suites show no worse than the v10 recorded cells (pass_ratio floor 0.95 etc.); greedy-parity per P-PARITY-1 where applicable.
- Otherwise: stay on 6.2 (no unpin), record the verdict; the v11 promotion proceeds on 6.2.
Owner: `handoffs/active/mi210-big-model-and-acceleration-roadmap.md` (MI210 acceleration) with the rocm-upgrade-checklist as the method; the v11 window is owned by the kernel-promotion run. Consumers: `autokernel-all-devices-all-dimensions.md` (AK-MMQ spill/J-cap lane reuses the static audit), wiki hardware-optimization (compile). Compile-time work follows the production-freeze rule: experimental branch from a fresh production pull; never touch the frozen tree.
Six controls: frozen manifest = the promotion_gates.yaml suites + pinned 200-item manifests; baseline = frozen v10 on ROCm 6.2 same window; raw per-item outputs retained; holdout = the gate's held-out manifests; complete denominator incl. truncations; predeclared rule = G1/G2 above.
Model tier: tarball install and static audit = sonnet runner (clerk-grade, scripted); A/B and promotion-window interpretation = main (opus); driver read = operator.

### K4 — Sources promoted out of "declined" because they cite MI210/gfx90a (operator steering S5; waves exhausted 4/4, so these are Stage-4 investigation items)
Per-source grep result for MI210 / gfx90a / CDNA2 / MI200 / MI250 on saved copies (see section 2 table). Three sources cite it and are NOT declined:
1. vLLM ROCm install docs (https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html, retrieved 2026-10-06, sha256 8633a3adef6e, saved dive-s3/vllm_rocm_doc.txt): L504 "GPU: MI200s (gfx90a), MI300 (gfx942), MI350 (gfx950), Radeon RX 7900 series ..." and "ROCm 6.3 or above" (so vLLM would NOT run on our ROCm 6.2 userspace, but IS documented-supported on gfx90a); L923-924 "To build vLLM for multiple arch MI210/MI250/MI300 ... PYTORCH_ROCM_ARCH="gfx90a;gfx942""; L1203/1219 "To build vllm on ROCm 7.0 for MI200 and MI300 series, you can use the default". Pre-built wheels are for ROCm 7.0 and 7.2.1 (page header text). Conclusion: my earlier "vLLM/SGLang exclude gfx90a" was true ONLY of AMD's 10.1 framework-validation list (intake-1944); it is OVERTURNED for vLLM upstream: gfx90a is officially supported there. Whether Qwen3.8-Flash-Next (qwen4_exp) runs on it is NOT established (the 125B model does not fit 64 GiB anyway).
2. SGLang AMD page (https://docs.sglang.ai/platforms/amd_gpu.html, retrieved 2026-10-06, sha256 29f4414275c5, saved dive-s3/sglang_amd.txt): the only mention is L130 "petit_nvfp4 enables NVFP4 models ... on MI250/MI300X via Petit"; the tuning guides cite MI300X only. gfx90a is therefore NOT established as supported by SGLang (neither listed nor excluded beyond MI250 for one kernel package). Unofficial/community status for gfx90a: not found in these pages; to be investigated, not asserted.
3. TheRock SUPPORTED_GPUS.md (raw github ROCm/TheRock main, retrieved 2026-10-06, sha256 fd0211338eaa, saved dive-s3/therock_gpus.html): L50 "| CDNA2 | gfx90a | check | check | check |" for Build Passing / Sanity Tested / Release Ready on Linux; L119 gfx90a Windows build-passing only. Contradicts the runbook sentence that TheRock lists gfx90a as "Build Passing" only (docs/runbooks/rocm-upgrade-checklist.md): on today's page Linux gfx90a is Release Ready. (The runbook text predates this read; correction proposed, not applied.)
Stage-4 tasks proposed (index writes only for the first; no kernel changes):
- K4a: ingest-and-dive these three pages as new intake entries (full read, anchors; the raw copies already exist on disk; the Stage-4 step records read_depth FULL for TheRock page and PARTIAL for the two long docs pages, then a per-claim second reader). Tier: sonnet (clerk) + main review.
- P3: vLLM-on-MI210 PROBE (cheap-screen): determine whether an upstream vLLM ROCm wheel/container with its own bundled userspace (ROCm >=6.3) loads on the live gfx90a driver and serves a small model that fits (e.g. the 27B at a quant vLLM supports), correctness-only first (greedy parity vs llama.cpp, exclusive GPU claim, residency proven by VRAM sampling DURING the run), timing only afterwards in an MI210 window. Doubles as the cheapest evidence for P2 stage 1 (newer userspace on the current driver) and as an engine comparator against the production llama.cpp numbers (27B Q8 DFlash2: 80.87 tok/s at np1, ctx 65,536; v10 record). Host precondition: container runtime available on the host (not verified from here). Owner: mi210-big-model-and-acceleration-roadmap.md. Tier: sonnet runner, main review. No production change; no ROCm install under /opt/rocm.
- K4c: SGLang gfx90a status: read SGLang's ROCm install page and release notes for gfx90a (and community forks) with anchors; decline if no support evidence after the read. Tier: haiku clerk.

### K2 — Knowledge-only retentions (no task)
- Physics-normalised comparison convention for external Q38FN numbers (model variant, checkpoint experts, K, concurrency, median vs peak, bytes/step): rides into the next wiki compile of hardware-optimization/inference-serving at the operator-invoked wrap-up, and into the roofline program's C1 wording as one clause (proposed edit text only). Origin: INTAKE_STAGE2.md physics table.
- Measurement discipline from intake-1957/1951: back-calculate bytes per token from measured decode and reject hypotheses that exceed spec bandwidth; compare tokens per weight read, not tok/s. Folded into P1's sanity assertion.
- RecoverSSM (intake-1942): our llama.cpp already rolls back GDN state in O(1) via `rs_idx`; cost class is K+1 state writes. Monitor: trigger = PR merges with a K>=5 measurement showing >5% step gain, or P1(a) arithmetic shows the K+1 state-write term >3% of step bytes.
- Interconnect results (b12x RoCE all-reduce 23.6 us vs NCCL 65.5 us at 48 KB, ib_write_lat 1.47 us, 185 Gb/s link; intake-1946/1947/1958): not applicable to a single host; knowledge only.
- 1953 (PP=2 review, no Q38FN, no 1-node baseline) and 1954 (vLLM Spark blog, no bandwidth number): monitor-grade knowledge; surfaced for operator review, not dismissed; trigger = a decision to consider multi-host pipeline parallelism.

## 2. Declines (named, with reason) and the MI210/gfx90a citation check (operator steering S5)
Method: `grep -i -E 'MI210|gfx90a|CDNA ?2|MI200|MI250'` over every saved copy (clones, HTML-to-text, JSON), with case-insensitive "Instinct" false positives (the word "instincts" in test prose) excluded; sources that had never been fetched were fetched now (curl, one at a time) into dive-s3/ and grepped. No benchmark or compute was run.
| Source / decline item | Cites MI210/gfx90a/CDNA2/MI200/MI250? | Anchor / note | Status |
|---|---|---|---|
| Vocab trim: FR-Spec paper (1955), MiaAI single/dual (1950, 1956) | No | grep clean on all saved copies; the Spark gains are CUDA GB10 results | Declined (B10 NO-GO on our CPU) |
| 2-node TP/EP kit sources: myllmbox (1937), azampatti (1939/1940), Saren (1941), b12x (1946), eugr (1947), jschmied (1951), tonyd2wild (1949), ai-muninn (1952/1957/1958), MiaAI TensorFold (1959), StorageReview (1953), vLLM Spark blog (1954), NVIDIA specs (1943) | No | grep clean. Only AMD hit: jschmied notes cite gfx1151 (Strix Halo), e.g. notes/upstream/comment-54521-davidcanar-2.md:9 "The gfx1151 rows are a genuinely different picture ..." (determinism tooling, not gfx90a, not MI210) | Declined for our purposes |
| The two vLLM-specific items (prefix-cache chunk alignment, draft-vocab coverage; from intake-1958) | No (intake-1958 and ai-muninn Part 46 grep clean) | Part 46 (https://ai-muninn.com/en/blog/qwen38-flash-next-tp2-two-dgx-sparks) fetched now, 0 hits | Declined |
| vLLM / SGLang on MI210 | YES (vLLM docs), partial (SGLang) | see K4 items 1-2 with line anchors | NOT declined: K4 |
| TheRock supported-GPUs page | YES | K4 item 3 | NOT declined: K4 |
| ai-muninn Part 46; MiaAI PR #45 (API JSON); TensorFold upstream README; llama-benchy README; hibrid48 card; Intel W4A16-AutoRound card; NVIDIA forum 382522 (topic JSON); jschmied entire repo clone (all ~45 unread notes included) | No (0 hits each; sha256 of fetched copies in dive-s3/) | grep over whole clone: only gfx1151 hits | Declined |
| ROCm 10.1 docs/blog themselves | Yes by nature (they are the gfx90a support source) | intake-1944 anchors | Already dived; feeds P2 |
Remaining declines unchanged: 2-node TP/EP on our hardware (no second host; interconnect irrelevant), the reduced-vocab slice/ranked-64k builder (P4), adopting Spark-only stack pieces (b12x/CuTe kernels are SM120/121 only).

## 3. Ledger coverage (every row has a terminal mapping) and the plan-carried steering reconciliation
Per the lane skill, Stage 3 carries new steering rows in the plan only (the session file is not edited before approval); Stage 4 would write them into `steering_ledger`.
Retained rows (already in `.research-session.json`):
- S1 (dive policy; context-only; executed).  S2 (physics requirement; planned -> section 0, P1, K1).  S3 (ROCm 10.1 addition; planned -> P2, K4).
New Stage-3 rows, verbatim:
- S4 (stage 3, planned, plan_ref P2): "I'd be happy to perform a reboot as part of v11 kernel promotion. *IF* there's value to ROCm 10.1, we should do it."  Reason: replaces "knowledge plus deferred" with a staged value-assessment item.
- S5 (stage 3, planned, plan_ref K4): "are these sources explicitly citing the MI210? If so, shouldnt they be investigated?"  Reason: per-source grep done (section 2); three sources cite gfx90a and become investigation items K4a-c; the rest remain declined with the grep evidence.
- S6 (stage 3, declined, plan_ref null): "Decline for now"  Reason: operator closes D1 (5-of-10 expert cut) for now; reopen trigger recorded in D1.
- Stage-1 preliminary actionables: (1937/1948 physics-normalised row) -> K2; (1937/1942 MTP depth K>4 with cheap rollback) -> K3 + K2 RecoverSSM monitor; (1944/1938 migration screen) -> P2.
- Dive ledger A1 -> K2; A2 -> P1; A3 -> P4; A4 -> K3 + P1(a); A5 -> D1 (declined for now); A6 -> P2 (replaces deferred-only); A7 -> K2/P1; A8 -> section 2 (declined; grep clean).
- Dive-surfaced sources: dived (waves 1-4), declined with grep evidence (section 2), or promoted to K4.
- Unverified-contract: no plan text quotes a `stage1-unverified` figure; numbers are from dive-verified entries or labelled derived. New K4 anchors (vLLM/SGLang/TheRock lines) are from pages read this session but NOT yet index entries; they are quoted here as "retrieved 2026-10-06" observations, and K4a exists to make them dive-verified before any handoff text relies on them.

## 4. Proposed entry updates at Stage 4 (not applied)
integration_disposition values already set at dive time (knowledge_only/monitor/declined); intake-1944 would move monitor -> integrated (P2 owner: mi210-big-model-and-acceleration-roadmap.md) and the three K4 pages become new entries at Stage 4. Entries routed into an owner by this plan would be set to `integrated` with `handoffs_updated` filled (cpu-decode-roofline-program.md, speculative-decoding-mtp-refresh.md) at Stage 4: 1951, 1945, 1950, 1956, 1937. Task text edits proposed above are descriptions only; exact checkbox lines and the v2 proposed-payload JSON (`format_version: 2`, `opportunity_scan`, `outcome_reviews`, `proposed_tasks`, `steering_reconciliation`) are NOT generated in this draft; they are produced when the operator approves scope, because the draft deliberately proposes at most one new addendum row (K1) and one measurement row (P1) and every other item is an edit to an existing row or an operator decision.

## 5. Safe concurrency and ordering
P2 stage 0 and K4a/K4c are non-GPU and can run in parallel with P1(a)(b). P1(a)(b) first (no timing window; (b) needs CPU lock). P1(d)(e) in an AK CPU window. K1, P4, K3 depend on P1 only for their go/no-go and parameters; P4 requant and K3 CAFE-1 sweeps are timed experiments and serialise on the CPU window; CAFE-5/6 (existing) are unaffected. No safe parallel TIMED lane exists (P1(d)(e), P2 stage 1/2, P3 timing, P4, K3 serialise on their device windows; CPU vs MI210 windows are separate devices but each follows its own lock). K2 and K4a/K4c are non-compute and parallel.

## 6. Plan-completeness self-check
Context/opportunity review done per packet (objective -> gap -> changed behaviour -> deciding evidence); six controls named for P1 and P4/K3 (via owning rows); no packet defaults to paper reproduction; no full reproduction planned (no trigger fired); no handoff/stub/index write made; gitnexus impact analysis not run because no code is edited.

Operator approved rev2 on 2026-10-07 ("approved. Proceed to stage 4").

## Work packets

| Packet | Action | Owner |
|---|---|---|
| P1 | Measure our Q38FN MTP step bytes, expert union, tokens/step and streaming GB/s (replaces derived 9.1-11.6 GB and the 80-100 tok/s estimate) | handoffs/active/cpu-decode-roofline-program.md |
| P2 | ROCm 10.1 value assessment for the MI210 llama.cpp HIP build, staged, with the +5.0% go/no-go and the reboot only inside the v11 window | handoffs/active/mi210-big-model-and-acceleration-roadmap.md |
| P3 | vLLM-on-MI210 probe with bundled userspace (engine comparator and in-kernel-driver compatibility test) | handoffs/active/mi210-big-model-and-acceleration-roadmap.md |
| P4 | Schedule-or-decline decision for B10's no-code IQ4_XS draft-head requant probe, after P1 | handoffs/active/cpu-decode-roofline-program.md |
| K1 | Streaming-efficiency lever toward >=270 GB/s, gated on P1; AK-seed/REBUILD candidate merged into existing INF-70, CAFE-5/6 and AKX-ALL-25 work | handoffs/active/cpu-decode-roofline-program.md |
| K2 | Knowledge-only retentions and monitors (comparison convention, measurement discipline, RecoverSSM, interconnect, PP review, vLLM Spark blog) | handoffs/active/cpu-decode-roofline-program.md |
| K3 | Adaptive MTP depth merged into existing CAFE-1/CAFE-2/CAFE-3 by note amendments, no new task | handoffs/active/speculative-decoding-mtp-refresh.md |
| K4 | Ingest the three gfx90a-citing pages as intake entries and read SGLang for gfx90a at the approved Stage-4 boundary (index writes, no handoff task) | handoffs/active/mi210-big-model-and-acceleration-roadmap.md |

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-Q38P-1 | intake-1951#record | Adopt a physics-normalised comparison convention for external Q38FN numbers (model variant, checkpoint experts, K, concurrency, median vs peak, bytes per step) | K2 |
| RI-Q38P-2 | intake-1951#record | Measure our actual Q38FN MTP step bytes, verify-window expert union, tokens per step and streaming GB/s | P1 / Q38P-1 |
| RI-Q38P-3 | intake-1948#record | Raise effective CPU streaming from about 140 toward 270 GB/s via the dispatch and barrier floor, gated on the measurement | K1 |
| RI-Q38P-4 | intake-1955#record | Reduced-vocabulary draft-head slice and frequency-ranked builder for the MTP head | decline: our B10 measured no-go on the CPU (head 4-5 percent of the token, L3-resident, ceiling +3-4 percent, break-even acceptance, upstream +1.4 percent) |
| RI-Q38P-5 | intake-1956#record | Decide whether to schedule or decline B10's no-code IQ4_XS draft-head requant probe after the measurement | P4 / Q38P-2 |
| RI-Q38P-6 | intake-1937#record | Adaptive MTP depth with per-position acceptance bands, merged into the existing adaptive-width rows, plus a RecoverSSM monitor | K3 |
| RI-Q38P-7 | intake-1939#record | Evaluate the 5-of-10 routed-expert cut | decline: operator ruled decline for now; reopen only if the measurement shows expert bytes dominate and the streaming lever is closed |
| RI-Q38P-8 | intake-1944#record | Assess whether ROCm 10.1 improves our MI210 llama.cpp HIP build, staged, with the reboot only inside the v11 promotion window and a predeclared +5.0 percent go/no-go | P2 / Q38P-3 |
| RI-Q38P-9 | intake-1944#record | Probe vLLM on the MI210 with bundled userspace, as engine comparator and as the in-kernel-driver compatibility test | P3 / Q38P-4 |
| RI-Q38P-10 | intake-1944#record | Ingest the vLLM, SGLang and TheRock pages that cite gfx90a and read SGLang for gfx90a support | K4 |
| RI-Q38P-11 | intake-1946#record | Retain interconnect, pipeline-parallel and vLLM-on-Spark findings as knowledge with named triggers | K2 |
| RI-Q38P-12 | intake-1958#record | Check Q38FN draft-vocab traffic coverage and hybrid-GDN prefix-cache chunk alignment | decline: moot after the vocab-trim decline; prefix-cache alignment is a vLLM-specific finding with no llama.cpp analogue identified |

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-1951",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md",
    "speculative-decoding-mtp-refresh.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Q38P-1 and the CAFE-3 amendment consume the byte ledger and measured expert-union curve (applied 2026-10-07)"
   ]
  },
  {
   "id": "intake-1945",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Computed bytes-per-step basis (reproduces our 1.296 GB experts) is the Q38P-1 static part (a)"
   ]
  },
  {
   "id": "intake-1950",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Draft-head and accepted-tokens evidence feeds Q38P-2; vocab slice declined by B10"
   ]
  },
  {
   "id": "intake-1956",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Q38P-2 keeps the head requant probe schedule-or-decline"
   ]
  },
  {
   "id": "intake-1937",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md",
    "speculative-decoding-mtp-refresh.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Dynamic-depth bands recorded as CAFE-3 priors; headline numbers carried only with variant/K/aggregation labels"
   ]
  },
  {
   "id": "intake-1944",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "mi210-big-model-and-acceleration-roadmap.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Q38P-3 and Q38P-4 own the ROCm 10.1 value assessment and driver-compatibility test"
   ]
  },
  {
   "id": "intake-1942",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "speculative-decoding-mtp-refresh.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "RecoverSSM monitor trigger recorded in the CAFE-3 amendment: upstream merge with K>=5 gain >5% or Q38P-1 shows K+1 state-write term >3% of step bytes"
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Replace derived Q38FN step-bytes and headroom estimates with measured values before any lever is scheduled",
   "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md C1/C2/C4 instrument rules and B10 record (L3634-3690) @ origin/main 3d497622e; dive-1951w4/byte_ledger.md section 6",
   "gap": "No measured expert union, tokens per step or per-op GB/s exists for our Q38FN MTP recipe; the 9.1-11.6 GB and 80-100 tok/s numbers are derived under an independence assumption the only measured union (0.60-0.69 of independent) contradicts",
   "operational_change": "One measurement table for the served recipe",
   "benefit_direction": "Correctness and accounting only: decides whether the streaming lever has headroom and what K and R to sweep",
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "execution_conditions": "Parts (a) static: no window. Part (b) count measurement: CPU region lock, diagnostic build, never overlaps a timed arm. Part (c) timing: AK CPU window, warm, node-profile sibling build",
   "closure_basis": "Immediate; stop rule closes the streaming lever if streaming is already >= 60% of read-sum"
  },
  "P2": {
   "project_objective": "Decide whether ROCm 10.1 is worth a host driver/userspace change inside the v11 promotion",
   "implementation_ref": "docs/runbooks/rocm-upgrade-checklist.md; wiki/hardware-optimization.md L519-556 and L5922; 10.1.0 release notes saved dive-1944/r101_release-notes.txt @ origin/main 3d497622e",
   "gap": "The 10.1.0 notes cite no gfx90a performance gain; any upside is an unmeasured compiler-codegen hypothesis on register-bound MMQ kernels, and host driver compatibility with the in-kernel amdgpu is untested",
   "operational_change": "Staged value assessment with a predeclared go/no-go",
   "benefit_direction": "MI210 decode and prefill throughput must improve >= 5.0% paired with no new spills; otherwise stay on 6.2",
   "owner": "handoffs/active/mi210-big-model-and-acceleration-roadmap.md",
   "execution_conditions": "Stage 0 no GPU no reboot; stage 1 GPU claim and a timing window for the ABA; stage 2 only inside the operator-scheduled v11 window with reboot",
   "closure_basis": "Immediate stage 0; later stages gated by the stop rules in the task"
  },
  "P3": {
   "project_objective": "Establish whether newer ROCm userspace and vLLM run on the MI210 under the in-kernel amdgpu driver",
   "implementation_ref": "docs.vllm.ai ROCm install page L504, L923-924 (retrieved 2026-10-06, dive-s3/vllm_rocm_doc.txt) @ origin/main 3d497622e",
   "gap": "vLLM documents gfx90a support at ROCm >= 6.3 but we have never run it; the 10.1 docs are silent on in-kernel driver support for Instinct",
   "operational_change": "Container-based probe, correctness first",
   "benefit_direction": "Cheapest evidence for Q38P-3 stage 1 and an engine comparator for the MI210 serving numbers",
   "owner": "handoffs/active/mi210-big-model-and-acceleration-roadmap.md",
   "execution_conditions": "Needs a host container runtime (unverified) and an exclusive MI210 claim; correctness-only needs no timing window; timing only in an MI210 window",
   "closure_basis": "Immediate; declined if the container does not load, which still answers the driver question"
  },
  "P4": {
   "project_objective": "Decide whether the only surviving draft-head byte lever on our CPU is worth a run",
   "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md B10 record L3634-3690 @ origin/main 3d497622e",
   "gap": "B10 listed a no-code IQ4_XS head requant as the cheapest remaining probe but left it unscheduled",
   "operational_change": "A schedule-or-decline decision after P1",
   "benefit_direction": "Draft-head bytes only; target verification keeps output lossless",
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "execution_conditions": "Decision needs P1's head share; if scheduled it is a timed A/B in an AK CPU window",
   "closure_basis": "Immediate decision; probe itself conditional on the 5% rule"
  },
  "K1": {
   "project_objective": "Move CPU decode streaming toward 270 GB/s",
   "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md INF-70 axes, CAFE-5/CAFE-6; autokernel-all-devices-all-dimensions.md AKX-ALL-25 @ origin/main 3d497622e",
   "gap": "Effective streaming is ~137-174 GB/s (derived) vs Spark kernels at 80-87% of peak",
   "operational_change": "No new task: comparison column in P1 and an interim 60%-of-read-sum target recorded in P1",
   "benefit_direction": "Throughput, matched-process A/B with identity 100% and per-op GB/s per row",
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "execution_conditions": "Gated on P1; any lever follows CAFE-1 keep rule (>= +1.0% above window floor)",
   "closure_basis": "Closed-with-basis: owned by existing INF-70/CAFE/AKX rows; trigger = P1 shows streaming < 60% of read-sum"
  },
  "K2": {
   "project_objective": "Keep external-number comparison discipline and monitors without new tasks",
   "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md C1 wording; intake-1942/1946/1953/1954 records @ origin/main 3d497622e",
   "gap": "External Q38FN numbers were repeatedly compared across model variants, K and aggregation",
   "operational_change": "Knowledge retention; clause text proposed for the next wiki compile at the operator-invoked wrap-up",
   "benefit_direction": "Prevents mis-comparison; no throughput claim",
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "execution_conditions": "RecoverSSM monitor trigger: upstream merge with K>=5 gain > 5% or P1 shows the K+1 state-write term > 3% of step bytes; PP/vLLM-blog trigger: a multi-host pipeline-parallel decision",
   "closure_basis": "Knowledge-only; no immediate operational step remains: our rollback is already O(1) via rs_idx and the others do not apply to a single host"
  },
  "K3": {
   "project_objective": "Choose draft depth adaptively on the CPU MTP chain",
   "implementation_ref": "handoffs/active/speculative-decoding-mtp-refresh.md CAFE-1/2/3 (L384-386) @ origin/main 3d497622e; intake-1937 recipe mtp_depth bands; intake-1951 byte ledger",
   "gap": "CAFE rows lack Spark-measured priors for controller bands and an expert-union-based cost model",
   "operational_change": "Note amendments under CAFE-3 only",
   "benefit_direction": "Aggregate tok/s above best static K with identity 100%",
   "owner": "handoffs/active/speculative-decoding-mtp-refresh.md",
   "execution_conditions": "Unchanged CAFE-1/2/3 gates; run P1(b) before CAFE-2 so the cost curve is not re-derived under independence",
   "closure_basis": "Closed-with-basis: CAFE-1/2/3 already own the work and gates; no duplicate task"
  },
  "K4": {
   "project_objective": "Make the gfx90a-citing vLLM, SGLang and TheRock pages citable and settle SGLang gfx90a support",
   "implementation_ref": "dive-s3 saved pages (vLLM sha 8633a3adef6e, SGLang 29f4414275c5, TheRock fd0211338eaa) @ origin/main 3d497622e",
   "gap": "The three pages were read at Stage 3 but are not index entries, so no handoff text may rely on them",
   "operational_change": "Append three intake entries at Stage 4 with anchors; record the SGLang no-evidence result",
   "benefit_direction": "Provenance only",
   "owner": "handoffs/active/mi210-big-model-and-acceleration-roadmap.md",
   "execution_conditions": "Index writes at the approved Stage-4 boundary; no compute",
   "closure_basis": "Closed-with-basis: executed in Stage 4 itself, no standing task"
  }
 },
 "opportunity_scan": [
  {
   "scan_id": "S1",
   "source_ref": "intake-1951#record (byte_ledger section 6)",
   "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md C1 @ origin/main 3d497622e",
   "mechanism": "measured sub-linear verify-window expert union (0.69/0.63/0.60 of independent at 4/8/16 rows)",
   "consumer": "INF-70 roofline ledger",
   "application": "Measure our own union and step bytes",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-Q38P-2",
    "RI-Q38P-1"
   ],
   "basis": "Read the ledger and the current roofline rows; our 9.1-11.6 GB is derived under independence"
  },
  {
   "scan_id": "S2",
   "source_ref": "intake-1948#record",
   "implementation_ref": "cpu-decode-roofline-program.md INF-70 axes",
   "mechanism": "Spark kernels at 80-87% of peak vs our 31-39% derived",
   "consumer": "INF-70/CAFE/AKX rows",
   "application": "Streaming-efficiency lever",
   "disposition": "covered",
   "ledger_ids": [
    "RI-Q38P-3"
   ],
   "basis": "Existing rows own it; gated on the measurement"
  },
  {
   "scan_id": "S3",
   "source_ref": "intake-1955#record",
   "implementation_ref": "cpu-decode-roofline-program.md B10 L3634-3690",
   "mechanism": "reduced-vocab draft head",
   "consumer": "MTP draft head",
   "application": "Vocab trim",
   "disposition": "declined",
   "ledger_ids": [
    "RI-Q38P-4"
   ],
   "basis": "B10 NO-GO measured on our CPU"
  },
  {
   "scan_id": "S4",
   "source_ref": "intake-1956#record",
   "implementation_ref": "cpu-decode-roofline-program.md B10",
   "mechanism": "head requant as residual probe",
   "consumer": "MTP GGUF head slot",
   "application": "Schedule-or-decline requant probe",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-Q38P-5"
   ],
   "basis": "B10 left it unscheduled; decision needs P1 head share"
  },
  {
   "scan_id": "S5",
   "source_ref": "intake-1937#record",
   "implementation_ref": "speculative-decoding-mtp-refresh.md CAFE-1/2/3",
   "mechanism": "dynamic MTP depth bands and RecoverSSM",
   "consumer": "CPU MTP chain",
   "application": "Adaptive depth priors",
   "disposition": "covered",
   "ledger_ids": [
    "RI-Q38P-6"
   ],
   "basis": "CAFE rows own the work"
  },
  {
   "scan_id": "S6",
   "source_ref": "intake-1939#record",
   "implementation_ref": "MEASUREMENT/ model lineup",
   "mechanism": "5-of-512 expert cut",
   "consumer": "Q38FN serving",
   "application": "Expert cut",
   "disposition": "declined",
   "ledger_ids": [
    "RI-Q38P-7"
   ],
   "basis": "Operator: decline for now"
  },
  {
   "scan_id": "S7",
   "source_ref": "intake-1944#record",
   "implementation_ref": "docs/runbooks/rocm-upgrade-checklist.md; promotion_gates.yaml",
   "mechanism": "ROCm 10.1 toolchain",
   "consumer": "MI210 HIP build and v11 promotion",
   "application": "Staged value assessment",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-Q38P-8"
   ],
   "basis": "Read the notes and runbook; no cited gain, test is cheap"
  },
  {
   "scan_id": "S8",
   "source_ref": "intake-1944#record",
   "implementation_ref": "dive-s3/vllm_rocm_doc.txt L504",
   "mechanism": "vLLM gfx90a support at ROCm>=6.3",
   "consumer": "MI210 serving",
   "application": "Bundled-userspace probe",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-Q38P-9"
   ],
   "basis": "Docs cite gfx90a; untested here"
  },
  {
   "scan_id": "S9",
   "source_ref": "intake-1944#record",
   "implementation_ref": "dive-s3 pages",
   "mechanism": "gfx90a-citing pages",
   "consumer": "intake index",
   "application": "Ingest and settle SGLang",
   "disposition": "covered",
   "ledger_ids": [
    "RI-Q38P-10"
   ],
   "basis": "Executed at Stage 4"
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-1946#record",
   "implementation_ref": "intake-1953/1954 dive records",
   "mechanism": "interconnect, PP, vLLM Spark blog",
   "consumer": "single-host stack",
   "application": "Knowledge",
   "disposition": "context-only",
   "ledger_ids": [
    "RI-Q38P-11"
   ],
   "basis": "Not applicable to a single host; triggers named"
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-1958#record",
   "implementation_ref": "intake-1958 anchors",
   "mechanism": "draft-vocab coverage; prefix-cache alignment",
   "consumer": "vLLM-specific",
   "application": "Checks",
   "disposition": "declined",
   "ledger_ids": [
    "RI-Q38P-12"
   ],
   "basis": "Moot after the vocab-trim decline"
  },
  {
   "scan_id": "S12",
   "source_ref": "intake-1951#record",
   "implementation_ref": "wiki/hardware-optimization.md compile",
   "mechanism": "comparison convention",
   "consumer": "wiki",
   "application": "Convention",
   "disposition": "covered",
   "ledger_ids": [
    "RI-Q38P-1"
   ],
   "basis": "Knowledge retention"
  }
 ],
 "actionable_additions": [
  {
   "ledger_id": "RI-Q38P-1",
   "source": "intake-1951#record",
   "action": "Adopt a physics-normalised comparison convention for external Q38FN numbers (model variant, checkpoint experts, K, concurrency, median vs peak, bytes per step)",
   "terminal_mapping": "K2"
  },
  {
   "ledger_id": "RI-Q38P-2",
   "source": "intake-1951#record",
   "action": "Measure our actual Q38FN MTP step bytes, verify-window expert union, tokens per step and streaming GB/s",
   "terminal_mapping": "P1 / Q38P-1"
  },
  {
   "ledger_id": "RI-Q38P-3",
   "source": "intake-1948#record",
   "action": "Raise effective CPU streaming from about 140 toward 270 GB/s via the dispatch and barrier floor, gated on the measurement",
   "terminal_mapping": "K1"
  },
  {
   "ledger_id": "RI-Q38P-4",
   "source": "intake-1955#record",
   "action": "Reduced-vocabulary draft-head slice and frequency-ranked builder for the MTP head",
   "terminal_mapping": "decline: our B10 measured no-go on the CPU (head 4-5 percent of the token, L3-resident, ceiling +3-4 percent, break-even acceptance, upstream +1.4 percent)"
  },
  {
   "ledger_id": "RI-Q38P-5",
   "source": "intake-1956#record",
   "action": "Decide whether to schedule or decline B10's no-code IQ4_XS draft-head requant probe after the measurement",
   "terminal_mapping": "P4 / Q38P-2"
  },
  {
   "ledger_id": "RI-Q38P-6",
   "source": "intake-1937#record",
   "action": "Adaptive MTP depth with per-position acceptance bands, merged into the existing adaptive-width rows, plus a RecoverSSM monitor",
   "terminal_mapping": "K3"
  },
  {
   "ledger_id": "RI-Q38P-7",
   "source": "intake-1939#record",
   "action": "Evaluate the 5-of-10 routed-expert cut",
   "terminal_mapping": "decline: operator ruled decline for now; reopen only if the measurement shows expert bytes dominate and the streaming lever is closed"
  },
  {
   "ledger_id": "RI-Q38P-8",
   "source": "intake-1944#record",
   "action": "Assess whether ROCm 10.1 improves our MI210 llama.cpp HIP build, staged, with the reboot only inside the v11 promotion window and a predeclared +5.0 percent go/no-go",
   "terminal_mapping": "P2 / Q38P-3"
  },
  {
   "ledger_id": "RI-Q38P-9",
   "source": "intake-1944#record",
   "action": "Probe vLLM on the MI210 with bundled userspace, as engine comparator and as the in-kernel-driver compatibility test",
   "terminal_mapping": "P3 / Q38P-4"
  },
  {
   "ledger_id": "RI-Q38P-10",
   "source": "intake-1944#record",
   "action": "Ingest the vLLM, SGLang and TheRock pages that cite gfx90a and read SGLang for gfx90a support",
   "terminal_mapping": "K4"
  },
  {
   "ledger_id": "RI-Q38P-11",
   "source": "intake-1946#record",
   "action": "Retain interconnect, pipeline-parallel and vLLM-on-Spark findings as knowledge with named triggers",
   "terminal_mapping": "K2"
  },
  {
   "ledger_id": "RI-Q38P-12",
   "source": "intake-1958#record",
   "action": "Check Q38FN draft-vocab traffic coverage and hybrid-GDN prefix-cache chunk alignment",
   "terminal_mapping": "decline: moot after the vocab-trim decline; prefix-cache alignment is a vLLM-specific finding with no llama.cpp analogue identified"
  }
 ],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "ts": "2026-10-06T19:00:00Z",
   "verbatim": "In the meantime, dispatch a subagent to perform a research-intake of this (usual 'all recommended' 10 cap peer stage 2 wave, and a cap of four maximum stage 2 waves) repo where 2x dgx spark achieve insane performance numbers with q38fn",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Operator dive policy: Stage 2 on all recommended dives (<=10 per wave), at most 4 waves total including Stage 2; stop at Stage-2 close-out; Stage 3 needs operator approval."
  },
  {
   "seq": 2,
   "stage": 1,
   "ts": "2026-10-06T19:00:00Z",
   "verbatim": "2x dgx spark should have an effective aggregate memory bandwidth in line with our CPU+ram hardware. As such, there either must be a physics reason for why we can't hit similar performance numbers, or we MUST got much much higher performance numbers",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "Core question of the intake: physics comparison section in INTAKE_STAGE1.md / INTAKE_STAGE2.md; carried into Stage 3 as a decision input (plan_ref assigned at Stage 3). Plan: section 0, P1 (measurement), K1 (gated lever)."
  },
  {
   "seq": 3,
   "stage": 1,
   "ts": "2026-10-06T19:00:00Z",
   "verbatim": "Add this to the same research intake also please: https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-10.1-blog/README.html?term=10-6-rocmrelease&utm_campaign=thallosocial&utm_source=twitter&utm_medium=social&utm_content=1791306421",
   "disposition": "planned",
   "plan_ref": "P2",
   "reason": "Operator added the AMD ROCm 10.1 blog to the same intake: ingested as intake-1938 (tracking params stripped) with the MI210/gfx90a migration angle (REBUILD / AK-HYPOTHESIS / KNOWLEDGE / ALREADY-HAVE tags); carried into Stage 3. Plan: P2 (staged value assessment), K4."
  },
  {
   "seq": 4,
   "stage": 3,
   "ts": "2026-10-07T00:00:00Z",
   "verbatim": "I'd be happy to perform a reboot as part of v11 kernel promotion. *IF* there's value to ROCm 10.1, we should do it.",
   "disposition": "planned",
   "plan_ref": "P2",
   "reason": "Replaces knowledge-plus-deferred with the staged value assessment P2 (Q38P-3); reboot only inside the v11 window; +5.0% go/no-go."
  },
  {
   "seq": 5,
   "stage": 3,
   "ts": "2026-10-07T00:00:00Z",
   "verbatim": "are these sources explicitly citing the MI210? If so, shouldnt they be investigated?",
   "disposition": "planned",
   "plan_ref": "K4",
   "reason": "Per-source grep done; the vLLM, SGLang and TheRock pages cite gfx90a and are ingested at Stage 4 (K4) and probed (P3, Q38P-4); the rest stay declined with grep evidence."
  },
  {
   "seq": 6,
   "stage": 3,
   "ts": "2026-10-07T00:00:00Z",
   "verbatim": "Decline for now",
   "disposition": "declined",
   "plan_ref": null,
   "reason": "Operator closed the 5-of-10 expert cut for now (RI-Q38P-7); reopen trigger recorded in the plan."
  },
  {
   "seq": 7,
   "stage": 3,
   "ts": "2026-10-07T00:00:00Z",
   "verbatim": "approved. Proceed to stage 4",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Operator approval of Stage-3 rev2 including the +5.0% go/no-go; recorded as context: approval of scope is not a waiver of the review gates, and Stage 4 applies exactly the approved plan."
  }
 ],
 "outcome_reviews": {
  "RI-Q38P-1": {
   "required_outcome": "External Q38FN numbers are compared on model variant, experts, K, concurrency and median-vs-peak",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge retention is the right terminal: it changes how future intake reads numbers, needs no code or run; clause text is carried to the next wiki compile",
   "task_refs": []
  },
  "RI-Q38P-2": {
   "required_outcome": "A measured step-bytes, expert-union, tokens/step and GB/s table for the served recipe replaces the derived estimates",
   "review_status": "preserved",
   "review_basis": "Q38P-1 binds the measurement with parts (a)(b)(c) separated by timing need and carries the six controls and a reconciliation rule; reviewed against the byte ledger caveats",
   "task_refs": [
    {
     "owner": "handoffs/active/cpu-decode-roofline-program.md",
     "task_id": "Q38P-1",
     "task_text": "- [ ] **Q38P-1 — MEASURE our Q38FN MTP step: bytes, expert union, tokens/step and streaming GB/s (replaces the derived 9.1-11.6 GB and the 80-100 tok/s estimate).** For the served recipe (UD-IQ4_XS, `-t 48`, MTP d4; plain and MTP arms): (a) static bytes/step from the GGUF tensor table incl. the K+1 GDN state writes (no timing window); (b) distinct experts per layer vs verify rows R=1..6 and drafter rows from the router-id tap on a diagnostic/ID-tap build, plus tokens/step per prompt class on the held-out manifest (count measurement: CPU region lock, never overlaps a timed arm); (c) step ms and per-op-class achieved GB/s against C0 (446.8) from the node/PATHROW profiler in an AK CPU window, node-profile as a non-measured sibling build, knob proven compiled in (`strings`), residency proven (C1/C2/C4 apply). Controls: AK prompt manifests and GGUF/binary digests frozen; baseline = frozen v10 `ffc1bac82` champion recipe; per-call raw ids and per-step timings retained; held-out manifest; every call counted incl. logits=0 catch-up evals; accept only if the instrument reproduces the 4.16 GB plain table and ~53 tok/s within between-launch noise and node timings reconcile to step wall within 2%. Stop: if weight-path streaming is already >= 60% of read-sum (>=268 GB/s), close the streaming lever as no-headroom. (intake-1951#record) — Owner: workspace-ec (2026-10-07).",
     "acceptance": "Table exists with static, count and timing parts, instrument sanity assertion passed"
    }
   ]
  },
  "RI-Q38P-3": {
   "required_outcome": "Streaming efficiency is raised only if the measurement shows headroom",
   "review_status": "closed-with-basis",
   "review_basis": "Owned by existing INF-70/CAFE-5/CAFE-6/AKX-ALL-25 rows; the new input is the P1 measurement and an interim 60% target; opening a duplicate lever task would shadow them",
   "task_refs": []
  },
  "RI-Q38P-4": {
   "required_outcome": "Vocab-trim is not pursued on the CPU",
   "review_status": "closed-with-basis",
   "review_basis": "B10 measured it: head 4-5% of the token, L3-resident, +3.0-3.9% ceiling, id-prefix slice break-even on alpha, upstream +1.4%; Spark gains are GPU DRAM-resident effects (no MI210/gfx90a mention in those sources)",
   "task_refs": []
  },
  "RI-Q38P-5": {
   "required_outcome": "The surviving draft-head byte lever is explicitly scheduled or declined on measured head share",
   "review_status": "preserved",
   "review_basis": "Q38P-2 keeps the one B10 candidate probe alive with a predeclared 5% schedule rule and gates, and keeps the slice declined",
   "task_refs": [
    {
     "owner": "handoffs/active/cpu-decode-roofline-program.md",
     "task_id": "Q38P-2",
     "task_text": "- [ ] **Q38P-2 — After Q38P-1 lands, schedule or decline B10's no-code IQ4_XS draft-head requant probe.** Requantise the MTP head to IQ4_XS into `blk.48.nextn.shared_head_head` (521 -> 338 MB; B10 expected +1.4-1.8%). Schedule only if Q38P-1 measures the draft head at >= 5% of step time, otherwise decline and record it; gates if scheduled: greedy identity 100%, alpha change <= 0.01 absolute on the held-out manifest, aggregate >= +1.0% above the window floor over >= 5 interleaved pairs, complete denominator. The reduced-vocabulary slice stays declined (B10 NO-GO). (intake-1956#record) — Owner: workspace-ec (2026-10-07).",
     "acceptance": "Decision recorded after Q38P-1; if scheduled, the four gates are applied"
    }
   ]
  },
  "RI-Q38P-6": {
   "required_outcome": "Adaptive depth gains are tested only inside the existing CAFE gates",
   "review_status": "closed-with-basis",
   "review_basis": "CAFE-1/2/3 already specify sweep, cost curve and controller with identity and +1.0% gates; amendments add priors and ordering, so a new task would duplicate",
   "task_refs": []
  },
  "RI-Q38P-7": {
   "required_outcome": "The 5-of-10 expert cut is not pursued",
   "review_status": "closed-with-basis",
   "review_basis": "Operator ruled decline for now; reopen trigger recorded in the plan",
   "task_refs": []
  },
  "RI-Q38P-8": {
   "required_outcome": "ROCm 10.1 is adopted only if it passes a predeclared paired +5.0% gate with no spills, else 6.2 stays",
   "review_status": "preserved",
   "review_basis": "Q38P-3 states the host fact, the three stages, the stop at stage 0, and the go/no-go; reviewed against the runbook which expects a plain upgrade to regress",
   "task_refs": [
    {
     "owner": "handoffs/active/mi210-big-model-and-acceleration-roadmap.md",
     "task_id": "Q38P-3",
     "task_text": "- [ ] **Q38P-3 — ROCm 10.1 value assessment for the MI210 llama.cpp HIP build (staged; the reboot happens only inside the v11 promotion window).** Host fact (operator, 2026-10-07): amdgpu is the in-kernel upstream driver of host kernel 6.14.0-37 (no DKMS or amdgpu-install package); the 10.1.0 compatibility matrix lists only packaged drivers 30.10.2-31.60.0 and reserves inbox drivers for Ryzen APUs, so 10.1 userspace support on this driver is untested. Stage 0 (no GPU, no reboot; CPU lock for compiles): non-root side-by-side 10.1 tarball (family gfx90a) under /mnt/raid0/llm, compile-only gfx90a MMQ/MMVQ/MMA-FA/rocWMMA-FA from an experimental worktree, run the `docs/runbooks/rocm-upgrade-checklist.md` static audit (VGPR, spill, scratch, agpr_count; {offload-LTO default, `-fno-offload-lto`} x {default unroll, `--amdgpu-unroll-threshold-local=600`}) vs 6.2; NO-GO (stay on 6.2) unless a cell shows fewer spills or no worse VGPR on the hot kernels. Stage 1: settle whether 10.1 userspace works on the in-kernel driver (Q38P-4's container first, then the tarball userspace), then a side-by-side champion build and an MI210 same-window ABA with `HSA_NO_SCRATCH_RECLAIM` arms. Stage 2 (operator reboot, inside the v11 promotion window; may also need the packaged amdgpu driver, the operator's call): keep 10.1 only if paired serving-gate decode >= +5.0% (median of >= 5 interleaved launch pairs), prefill no worse than -2.0%, zero new hot-kernel spills, and the coherence and quality gates pass (promotion_gates.yaml); otherwise roll back to 6.2 and record the verdict. No production or frozen-tree change before the v11 window. (intake-1944#record) — Owner: workspace-ec (2026-10-07).",
     "acceptance": "Static audit verdict, driver-compatibility result and (if reached) the v11-window A/B verdict recorded against the +5.0% rule"
    }
   ]
  },
  "RI-Q38P-9": {
   "required_outcome": "Whether bundled-userspace vLLM runs on the MI210 and on the in-kernel driver is known",
   "review_status": "preserved",
   "review_basis": "Q38P-4 is correctness-first with exclusive claim and during-run VRAM sampling, and feeds Q38P-3 stage 1",
   "task_refs": [
    {
     "owner": "handoffs/active/mi210-big-model-and-acceleration-roadmap.md",
     "task_id": "Q38P-4",
     "task_text": "- [ ] **Q38P-4 — vLLM-on-MI210 probe with bundled userspace (engine comparator and in-kernel-driver compatibility test).** vLLM's install docs list MI200s (gfx90a) with ROCm >= 6.3 (docs.vllm.ai, retrieved 2026-10-06), which our ROCm 6.2 userspace does not meet. Run an upstream vLLM ROCm container (bundled userspace, no /opt/rocm change; the host needs a container runtime, unverified) on the live in-kernel amdgpu driver: a trivial HIP kernel, then a small model that fits (e.g. the 27B at a vLLM-supported quant), correctness-only first (greedy parity vs llama.cpp, exclusive GPU claim, VRAM sampled DURING the run, KFD process count); timing only afterwards in an MI210 window against the v10 27B Q8 DFlash2 record (80.87 tok/s at np1, ctx 65,536). Decline the engine comparison if the container does not load; the load result still answers Q38P-3 stage 1. (intake-1944#record) — Owner: workspace-ec (2026-10-07).",
     "acceptance": "Load/correctness result recorded; timing only if correctness passes"
    }
   ]
  },
  "RI-Q38P-10": {
   "required_outcome": "The three gfx90a-citing pages are citable index entries and SGLang gfx90a support is settled",
   "review_status": "closed-with-basis",
   "review_basis": "Done at the Stage-4 boundary by intake-index writes (no standing task); the SGLang install page and README show no gfx90a text, the AMD page cites MI250 only for a Petit package",
   "task_refs": []
  },
  "RI-Q38P-11": {
   "required_outcome": "Interconnect, PP and vLLM-blog findings are retained with named triggers",
   "review_status": "closed-with-basis",
   "review_basis": "None applies to a single host; triggers recorded in K2",
   "task_refs": []
  },
  "RI-Q38P-12": {
   "required_outcome": "Draft-vocab coverage and prefix-cache alignment checks are not pursued",
   "review_status": "closed-with-basis",
   "review_basis": "Moot after the vocab-trim decline; no llama.cpp analogue identified for the vLLM prefix-cache alignment finding",
   "task_refs": []
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "task_text": "- [ ] **Q38P-1 — MEASURE our Q38FN MTP step: bytes, expert union, tokens/step and streaming GB/s (replaces the derived 9.1-11.6 GB and the 80-100 tok/s estimate).** For the served recipe (UD-IQ4_XS, `-t 48`, MTP d4; plain and MTP arms): (a) static bytes/step from the GGUF tensor table incl. the K+1 GDN state writes (no timing window); (b) distinct experts per layer vs verify rows R=1..6 and drafter rows from the router-id tap on a diagnostic/ID-tap build, plus tokens/step per prompt class on the held-out manifest (count measurement: CPU region lock, never overlaps a timed arm); (c) step ms and per-op-class achieved GB/s against C0 (446.8) from the node/PATHROW profiler in an AK CPU window, node-profile as a non-measured sibling build, knob proven compiled in (`strings`), residency proven (C1/C2/C4 apply). Controls: AK prompt manifests and GGUF/binary digests frozen; baseline = frozen v10 `ffc1bac82` champion recipe; per-call raw ids and per-step timings retained; held-out manifest; every call counted incl. logits=0 catch-up evals; accept only if the instrument reproduces the 4.16 GB plain table and ~53 tok/s within between-launch noise and node timings reconcile to step wall within 2%. Stop: if weight-path streaming is already >= 60% of read-sum (>=268 GB/s), close the streaming lever as no-headroom. (intake-1951#record) — Owner: workspace-ec (2026-10-07)."
  },
  {
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "task_text": "- [ ] **Q38P-2 — After Q38P-1 lands, schedule or decline B10's no-code IQ4_XS draft-head requant probe.** Requantise the MTP head to IQ4_XS into `blk.48.nextn.shared_head_head` (521 -> 338 MB; B10 expected +1.4-1.8%). Schedule only if Q38P-1 measures the draft head at >= 5% of step time, otherwise decline and record it; gates if scheduled: greedy identity 100%, alpha change <= 0.01 absolute on the held-out manifest, aggregate >= +1.0% above the window floor over >= 5 interleaved pairs, complete denominator. The reduced-vocabulary slice stays declined (B10 NO-GO). (intake-1956#record) — Owner: workspace-ec (2026-10-07)."
  },
  {
   "owner": "handoffs/active/mi210-big-model-and-acceleration-roadmap.md",
   "task_text": "- [ ] **Q38P-3 — ROCm 10.1 value assessment for the MI210 llama.cpp HIP build (staged; the reboot happens only inside the v11 promotion window).** Host fact (operator, 2026-10-07): amdgpu is the in-kernel upstream driver of host kernel 6.14.0-37 (no DKMS or amdgpu-install package); the 10.1.0 compatibility matrix lists only packaged drivers 30.10.2-31.60.0 and reserves inbox drivers for Ryzen APUs, so 10.1 userspace support on this driver is untested. Stage 0 (no GPU, no reboot; CPU lock for compiles): non-root side-by-side 10.1 tarball (family gfx90a) under /mnt/raid0/llm, compile-only gfx90a MMQ/MMVQ/MMA-FA/rocWMMA-FA from an experimental worktree, run the `docs/runbooks/rocm-upgrade-checklist.md` static audit (VGPR, spill, scratch, agpr_count; {offload-LTO default, `-fno-offload-lto`} x {default unroll, `--amdgpu-unroll-threshold-local=600`}) vs 6.2; NO-GO (stay on 6.2) unless a cell shows fewer spills or no worse VGPR on the hot kernels. Stage 1: settle whether 10.1 userspace works on the in-kernel driver (Q38P-4's container first, then the tarball userspace), then a side-by-side champion build and an MI210 same-window ABA with `HSA_NO_SCRATCH_RECLAIM` arms. Stage 2 (operator reboot, inside the v11 promotion window; may also need the packaged amdgpu driver, the operator's call): keep 10.1 only if paired serving-gate decode >= +5.0% (median of >= 5 interleaved launch pairs), prefill no worse than -2.0%, zero new hot-kernel spills, and the coherence and quality gates pass (promotion_gates.yaml); otherwise roll back to 6.2 and record the verdict. No production or frozen-tree change before the v11 window. (intake-1944#record) — Owner: workspace-ec (2026-10-07)."
  },
  {
   "owner": "handoffs/active/mi210-big-model-and-acceleration-roadmap.md",
   "task_text": "- [ ] **Q38P-4 — vLLM-on-MI210 probe with bundled userspace (engine comparator and in-kernel-driver compatibility test).** vLLM's install docs list MI200s (gfx90a) with ROCm >= 6.3 (docs.vllm.ai, retrieved 2026-10-06), which our ROCm 6.2 userspace does not meet. Run an upstream vLLM ROCm container (bundled userspace, no /opt/rocm change; the host needs a container runtime, unverified) on the live in-kernel amdgpu driver: a trivial HIP kernel, then a small model that fits (e.g. the 27B at a vLLM-supported quant), correctness-only first (greedy parity vs llama.cpp, exclusive GPU claim, VRAM sampled DURING the run, KFD process count); timing only afterwards in an MI210 window against the v10 27B Q8 DFlash2 record (80.87 tok/s at np1, ctx 65,536). Decline the engine comparison if the container does not load; the load result still answers Q38P-3 stage 1. (intake-1944#record) — Owner: workspace-ec (2026-10-07)."
  }
 ]
}
```
