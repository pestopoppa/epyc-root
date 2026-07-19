# v6 → v7 production-promotion (production-consolidated-v7)

**Status:** NOT PROMOTED — readiness-gated. Production stays on `production-consolidated-v6` (+iqk, frozen). This handoff tracks promoting the validated experimental **v7** kernel to a NEW production version **production-consolidated-v7**, per the four-step experimental-kernel workflow (fresh-pull → build → validate-no-regression → deploy as new version). Sibling/template: the completed v5→v6 cutover in [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md) (phased procedure + rollback pattern to reuse).

## What v7 is
Experimental tip **`experimental-v7-refresh-20260716` @ `6a8dd5ea6`** (`/mnt/raid0/llm/llama.cpp-experimental`; backed up on `fork/experimental-v7-refresh-20260716`). Verified on disk: iqk present, GPU-opt flags present, `GGML_TYPE_Q2_0`=42 present. Since the `d1e5a20eb` branch-reconcile checkpoint, this tip also includes the Dream arch smoke fix (`04753078f`), GLM-DSA native-MTP scaffold (`d6706a612`), Expected-Attention compact telemetry guard (`8905c3d2c`), K28 GDN boundary test (`231db22c7`), K28/K31 guard prep (`41ae83402`), StreamingLLM KV context controls (`111bff89d`), the `llama-completion` StreamingLLM surface fix (`cf051d3e1`), streaming-KV source prep (`111bff89d`/`cf051d3e1`), the DFlash/quantization forward-port checkpoint (`ed4091266`), and the narrow upstream pre-promotion fixes for Hadamard BLAS default-to-CPU (`11fd0a6fb`) plus TP split metadata for ChatGLM-style tensors (`2e1fd7649`) via local commit `6a8dd5ea6`. Full lever audit + banked-wins detail in [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md) §v7 Promotion Readiness.

**Banked, correctness-verified, runtime-gated-off wins:**
- HIP graphs (per-decode capture) **+25%** worker spec-dec (A4B MoE), +4–14% base decode
- MMVQ→MMQ small-batch verify-dispatch (`de447119f`) **+17.4%** MTP-verify / **+31.7%** gemma-31B
- nwarps 2→4 (`5dc116130`) +4.6%; async prefetch (`7c28056b7`) +3.3%
- bf16 GDN recurrent-state (`496e2f098`) **+21.5% @B32** (frontdoor 35B-A3B +17.7%, architect 122B +16.4%)
- single-stream dense-Q8 **+37%** (29→40.4 t/s)

## Governance — how promotion happens
Production kernels are FROZEN. A production swap to `-v7` is **operator-authorized only** (MEASUREMENT.md trust boundary + `feedback_operator_owns_host_reboots`). The agent drives v7 to a `READY FOR OPERATOR PROMOTION` state and **STOPS** — it must **never** self-push to production. The cutover itself follows the [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md) phased pattern (staging garbage-check → build `-v7` in canonical → `stop/swap/start --hot-only` → assert kernel identity + draft-accept) with its R0–R3 rollback pre-staged. Bench evidence must come from the v7 binary via codified recipes with operator approval.

## Readiness gate — COUPLED (operator-chosen 2026-07-18)
The operator elected to **hold v7 promotion until GLM optimized decode is confirmed**, so GLM spec-dec ships accelerated in the same promotion (GLM-5.2 is *a* **candidate** for the production cross-family reviewer role *if* it passes quality — **the reviewer choice is open and undecided**; Qwable+architect is only one illustrative alternative and other options may prove better, so this should not over-constrain reviewer exploration). When every box is green, flag `v7 READY FOR OPERATOR PROMOTION` and hand to the operator.

- [x] **K5 quality** — v6 vs v7 MMLU-Pro/GPQA `+0.0%` (PASS) ✅ 2026-07-16
- [ ] **OP-2 CPU-regression canonical bench** PASS — clean post-reboot canonical decode bench + live v6+iqk verify per MEASUREMENT.md (shares [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md) Phase J; package `docs/reference/op-2-canonical-bench-window-package-2026-07-18.md`). **Timeline note (2026-07-18):** the last host reboot was ~2 weeks ago (not "a month" as an earlier note said); but "post-reboot" here is a MEASUREMENT.md cold-cache/clean-NUMA/no-throttle requirement, and ~2 weeks of uptime is *not* that fresh-boot state — so this still needs either a verified bench-clean host or the next operator reboot/quiet window. Not indefinitely blocked, but not trivially runnable either.
- [ ] **`P-GPU-1` ratified** — MEASUREMENT amendment signed so Gate-R + all GPU numbers are decision-grade (package `docs/reference/p-gpu-1-ratification-package-2026-07-18.md`)
- [ ] **Final cutover coherence + garbage smoke**, separate from the already-closed K35/A1 release matrix: after the last promotion-candidate source state is fixed, run the production-role smoke/garbage check for gemma worker / qwen frontdoor / 122B architect / ingest / vision and confirm no across-the-board regression.
- [x] **Upstream-ahead narrow audit applied ✅ 2026-07-19** — read-only audit found official `origin/master` at `571d0d540`, 23 commits ahead of `ed4091266`. DFlash KV rotation (`571d0d540`), DFlash/EAGLE3 sidecar runtime (`0af063a88` local), routing-table quant skip (`4937ca83f` local), and recurrent rollback coverage were already covered or docs-only. The two scoped code fixes were applied in experimental-v7 commit `6a8dd5ea6`: `11fd0a6fb` (Hadamard BLAS default-to-CPU) and `2e1fd7649` (TP split metadata for ChatGLM-style tensors). Validation passed: `cmake --build build-hip --target llama-bench test-llama-archs -j16` and `ctest --test-dir build-hip -R '^test-llama-archs$' --output-on-failure`. DeepSeek4 fused-HC (`0dc74e332` + `5d5306bf3`) remains out of current v7 scope.
- [ ] **GLM reviewer quality cleared** — `GC-shadow-repair4b → P-REV-1` ([`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md)) ← *research gate; also admits GLM to the reviewer role*
- [ ] **Native GLM-MTP α + throughput confirmed** — end-to-end spec-dec win measured (scaffold feasibility already ✅ B6/K23.1, [`tree-draft-forward-port-plan.md`](tree-draft-forward-port-plan.md))
- [ ] → **flag `v7 READY FOR OPERATOR PROMOTION` and STOP** (operator authorizes the cutover; no self-push)

> **Tradeoff on record (revisitable).** COUPLING defers the banked *production-model* wins (gemma +25%, qwen/architect +17–32% / +16–21%) behind the last two boxes — an open GLM reviewer-quality research gate. This is coherent with GLM-5.2 as *a* **candidate** production reviewer (**undecided; the reviewer choice is open** — Qwable+architect is just one example, other options may be better): *if* chosen, quality (P-REV-1) admits the role and native-GLM-MTP makes it practical (~238GB/~2.5 t/s otherwise), so coupling ships both with v7. The 2026-07-18 audit's alternative was to **decouple** (promote on production validation now; ship native GLM-MTP inert; enable it when GLM passes P-REV-1). Flip to decoupled by striking the last two boxes if the GLM gate proves slow.

## Cross-links
- Kernel audit + banked wins: [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md)
- Promotion template + shared canonical-bench gate (Phase J): [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md)
- GLM role/quality gate: [`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md); native GLM-MTP: [`tree-draft-forward-port-plan.md`](tree-draft-forward-port-plan.md)
- Domain index: [`inference-acceleration-index.md`](inference-acceleration-index.md)

## Reporting
Tick the gate boxes here as each precondition passes; when all green, flag READY and STOP. On promotion, follow the v6-iqk-promotion phased cutover and record the era-registry row + attestation (operator/human steps).
