# Qwen3.8-27B — replace Qwen3.6-27B in production

**Status**: ACTIVE — download/smoke/MTP/throughput/architect-bench done; **stack-template swap DONE 2026-08-20** — `1cff5162` ("stack template: architect_general -> Qwen3.8-27B; draft_max 24 -> 8 (measured)", 2026-08-20 21:52:11Z), whose *only* changed file is `repos/epyc-orchestrator/stack_templates/default.yaml` (`git show --stat`: 1 file, +7/-2). **CORRECTED 2026-08-21 (second pass): the MASTER registry swap IS done** — `b376dadd` ("registry: swap architect_general + coder_escalation to Qwen3.8-27B; draft_max 4 -> 8", 2026-08-20 12:19) is a LOCAL, UNPUSHED commit in **epyc-inference-research**, whose `orchestration/model_registry.yaml` is the TRUE master; the orchestrator's same-named file is the AUTO-GENERATED lean view (banner at its head) and was audited by mistake. What is NOT done is the **compile chain**: `orchestration/model_registry.yaml` contains **zero** occurrences of the fixed string `Qwen3.8` (`grep -F -c` → `0`, re-verified 2026-08-21), and `architect_general` / `coder_escalation` there still carry `model_role: qwen36_27b_mtp_q8_local` (`model_registry.yaml:1501`, `:1398`) — so a registry-vs-stack-template divergence stands until the registry is updated **and** the derived layer regenerated. **THIRD PASS 2026-08-21: the compile chain is now DONE too** — ratification executed (`ratify_qwen38_registry_swap_20260821.sh` v2; orchestrator `7483d7fb`): derived `stack_priors.yaml` verified serving Qwen3.8-27B-Q8_0 @ draft_max 8 on architect_general. (The earlier "`b376dadd` resolves in no repo" was an artifact of the research repo's `safe.directory` config defeating the check; it resolves fine and is on origin since `bb405297`.) Remaining: Q38-T5 stack start + `live == config` checklist (operator-sequenced), Q38-T4 third edit + recompile. Full evidence: *Research Intake — 2026-08-21*.
**Created**: 2026-08-14
**Priority**: P2 (model refresh; no production pain forcing it, but a same-day release refresh is cheap to stage)
**Effort**: Low-Medium — download/smoke/MTP/throughput/architect-bench done; the registry swap is the last step (the 2026-08-14 quality-gate decline was later reversed and the coding ladder ran)

## Objective

Stage `Qwen3.8-27B` as the replacement for `Qwen3.6-27B-MTP-Q8_0`, which is the **primary model for
`architect_general` + `coder_escalation`** (both served from the :8083 MI210 process, ROCm0; the 122B
vacated to `architect_critic` 2026-07-31). Qwen3.8 was released 2026-08-14.

## What is known (verified against HF on release day)

- Upstream: `Qwen/Qwen3.8-27B` (public, not gated), plus `Qwen/Qwen3.8-2.4T-A95B` (the large sibling).
- **Qwen3.8-27B is MULTIMODAL** — a vision projector (`mmproj`) ships alongside it. This is a new
  capability vs the text/code-only Qwen3.6-27B; treat it as optional, not a migration requirement.
- **MTP/NextN head is EMBEDDED in the unsloth base — NOT a separate sidecar (CORRECTION).** GGUF-header
  verification (`llama-gguf r`) shows the unsloth `Qwen3.8-27B-Q8_0.gguf` carries `blk.64.nextn.*`
  tensors (`eh_proj`/`enorm`/`hnorm`/`shared_head_norm`) and `qwen35.nextn_predict_layers` metadata —
  the same embedded self-draft layout as `Qwen3.6-27B-MTP-Q8_0`. So the wiring is **same-file
  `--spec-type draft-mtp` self-draft, unchanged from Qwen3.6**. The ggml-org `mtp-*.gguf` (3.16 GB) is a
  *full layer-64* draft model (`attn` + `ffn` + `nextn`) for the ggml-org base (which strips MTP) — it is
  **redundant** for the unsloth base and was downloaded only as a fallback.

## Artifacts

| Artifact | Source | Size | Status |
|---|---|---|---|
| `Qwen3.8-27B-Q8_0.gguf` | `unsloth/Qwen3.8-27B-GGUF` | 29.05 GB | ✅ downloaded + header-verified (embeds nextn/MTP) |
| `mtp-Qwen3.8-27B-Q8_0.gguf` | `ggml-org/Qwen3.8-27B-GGUF` | 3.16 GB | ✅ downloaded (redundant fallback; unsloth base embeds MTP) |
| `mmproj-Qwen3.8-27B-Q8_0.gguf` (optional, vision) | `ggml-org/Qwen3.8-27B-GGUF` | 0.63 GB | not downloaded |

Destination: `/mnt/raid0/llm/models/`. Download log: `/tmp/opencode/dl_qwen38.outerr`.

## Inherited findings — from INF-32's predecessor `qwen36-27b-cpu-feasibility.md`, archived 2026-09-14

The predecessor model's handoff was archived 2026-09-14 (premise gone: Qwen3.8-27B *is* the 27B role
candidate now). Three of its findings are about the **architecture class**, not the specific weights,
so they survive the model swap — Qwen3.8-27B reports the same `qwen35` arch identifier:

- [x] **MI210 dense-Q8 +37% is the inherited GPU baseline for this class** — Qwen3.6-27B went
      **29.5 → 40.4 t/s** on the MI210 via the embedded-NEXTN MTP head plus the MMVQ→MMQ
      verify-dispatch fix (`de447119f`). That is the banked "dense-Q8 +37%" v7 win, and it is the
      lineage of this handoff's own `draft-mtp` numbers. EAGLE-3 was tested → no-go; GDN-MFMA was
      profiled → killed. Record: [`mi210-speed-campaign-summary.md`](../completed/mi210-speed-campaign-summary.md).
- [x] **CPU speculative decoding stays architecturally foreclosed for this family** — Gated-DeltaNet +
      Gated-Attention (3:1) makes draft verification non-equivalent under CPU serial decode; the GDN
      verification wall costs more than acceptance gains. Do not re-run CPU spec-dec probes on
      Qwen3.8-27B either. (This is a CPU-only foreclosure; the GPU numbers above are the proof it is
      not a statement about the model.)
- [x] **Cross-version DFlash drafter portability is real but lossy** — a Qwen3.5-27B-DFlash drafter
      loads unchanged on a 3.6-class target (identical `Qwen35` identifier, layer/head dims) at
      acceptance length 5.05 vs 9.18 same-version (intake-501#record). Relevant to the open **DFlash2
      selection decision** below: expect a same-family-but-not-same-version drafter to lose roughly
      half its acceptance length.

Full ledger: [`qwen36-27b-cpu-feasibility.md`](../archived/qwen36-27b-cpu-feasibility.md).

## Steps

- [x] **Verify the download** ✅ 2026-08-14 — both files at full declared size (29,047,086,048 B /
  3,164,006,688 B); GGUF header shows arch `qwen35`, `block_count`, `context_length`, and the embedded
  `nextn`/MTP tensors in the base (see "What is known" — the MTP-sidecar assumption was wrong).
- [x] **Load smoke** ✅ 2026-08-14 — PASS on v9 HIP (`-ngl 999 -c 4096 --spec-type draft-mtp --spec-draft-n-max 4`): model loads (31.98 GB VRAM), generates coherently ("Quicksort is a highly efficient sorting algorithm…"), no op-fallback warnings.
- [x] **MTP wiring** ✅ 2026-08-14 — RESOLVED: the unsloth base embeds the nextn/MTP head, so
  `--spec-type draft-mtp` self-draft is same-file, exactly like Qwen3.6-27B-MTP. `draft_model` in the
  registry stays the same file. The separate `mtp-*.gguf` sidecar is NOT needed.
- [x] **Quality gate — DECLINED by operator (2026-08-14):** *"quality will improve certainly."* The
  Qwen3.8→Qwen3.6 quality uplift is taken as a given (same-day release refresh); no coder/architect
  quality comparison will be run. The load-smoke below is the only remaining correctness check, and it
  confirms the model loads + generates — a technical check, not a quality gate.
- [x] **Throughput (optimized mode, GPU `draft-mtp`)** ✅ 2026-08-14/15 — prefill pp512 **727.29 t/s**; single-stream decode **flat ~45 t/s across 2k–32k depth** on real olympiadbench prompts (peak aggregate **157 t/s @np8**). **CORRECTION:** an earlier synthetic random-word probe showed a spurious 37→13.6 t/s decline + "MTP reversal at depth" — that was a prompt artifact (random words kill MTP acceptance), NOT real behaviour. On real prompts decode is flat and MTP holds. (natural-prompt single-shot 47.57 t/s still stands as the interactive figure.)
- [x] **Registry swap** ✅ 2026-08-20 — master registry commit `b376dadd`. `architect_general` +
  `coder_escalation`: `model` / `model_path` / `draft_model` / descriptor `name`+`path` →
  `Qwen3.8-27B-Q8_0.gguf` (self-draft, same file). `epyc-orchestrator/stack_templates/default.yaml`
  also repointed, and its `spec_overrides.draft_max: 24` corrected — that override was **silently
  beating** the registry's measured value at stack-assembly time.
  - **`model_role` was the trap.** It is load-bearing, not documentation: `model_descriptors.py:1233-1244`
    substitutes the `model_role` role's config when an alias's model id differs from its `server_mode`
    entry (recording `ignored_model_id`). Swapping `model_path` alone would have **served Qwen3.6 while
    the registry read as swapped**. Both refs now point at a new `qwen38_27b_q8_local` role;
    `qwen36_27b_mtp_q8_local` is RETAINED unmodified as the rollback anchor.
  - **`draft_max` 4 → 8, re-measured not inherited.** 4 was the measured optimum for *Qwen3.6*; depth is
    per-model. Qwen3.8 sweep (np=1, 12 real olympiadbench prompts, v9 `0db32c06e`/10125): plain 27.78 /
    n2 39.77 / n3 46.61 / n4 51.03 / n6 55.22 / **n8 55.46** / n12 51.14 t/s; acceptance 0.842 → 0.482
    across depth 2→8. Curve turns over past 8. MTP is worth **2.00× over plain** at n-max 8.
  - Every figure in the new role is measured on THIS artifact: `baseline_tps 27.78`, `optimized_tps 55.46`,
    `vram_gib 37.22` (n_slots=4, n_ctx 262144, q8_0 KV, kv_unified=true, sampled DURING residency).
    `optimized_tps_long_context` and `contended_tps` are explicitly `null` — not measured, and copying
    Qwen3.6's across would be a false attestation.
  - Validator: **0 problems** (this required fixing a pre-existing duplicate-key defect that had been
    failing the validator closed for the whole file — commit `a94e0e01`).
  - **2026-08-21 CORRECTION (Q38-T2, this box's claim does not hold).** Everything in this bullet
    describes the MASTER registry, and the master registry does not contain it. `grep -F -c 'Qwen3.8'
    orchestration/model_registry.yaml` → `0`; `git log -S 'Qwen3.8' -- orchestration/model_registry.yaml`
    → **empty** (no commit has ever added that string); there is no `qwen38_27b_q8_local` key anywhere in
    `orchestration/`; and the working tree is clean for that file (`git status --short` → no output). Only
    `stack_templates/default.yaml` was repointed (`1cff5162`). Because the launched `-m` path is read from
    `orchestration/derived/stack_priors.yaml`, **not** from the stack template, a start today would serve
    **Qwen3.6**, not Qwen3.8. Box left ticked as another session's record; the corrected state is in
    *Research Intake — 2026-08-21 → Q38-T2*.
- [x] **dFlash2 np1 folded in as decision context, selection UNCHANGED** ✅ 2026-08-20 — cross-session
  campaign measured **70.0 decode t/s** at matched np=1 vs a same-campaign MTP n-max-8 arm at 55.2
  (+26.81%), acceptance 0.628 vs 0.482. Independently verified here: `campaign-summary.json` SHA-256
  matches `e4f9e21f…` and the figures re-read correctly. Their matched MTP arm reproduces our 55.46 to
  within 0.5%. Recorded in the registry (`bd40ca94`) as `challenger_under_evaluation`, status
  `np1_only_NOT_SELECTABLE`; `spec_type: draft-mtp` / `n_max: 8` untouched. **No selection published.**
- [x] **DFlash2 selection decision** — BLOCKED on three named gates before it may displace MTP: np2/4/8
  scaling, exact greedy parity at temp 0, and the block-verify dispatch proof. Owned by the autokernel
  session under INF-62; this row exists so the registry side has a visible decision point.
  ✅ 2026-10-03 — **decided by the operator, applied and serving.** Operator rulings 2026-08-27 (ruling 3,
  `autokernel-champion-aggregate.md`) and 2026-10-01 ("ALWAYS use dflash2"); signed as
  `RATIFY-STACKCHG-DFLASH2-20261003` (terminal, 2026-10-03T04:39:55Z). Package:
  [`artifacts/operator/stack-change-dflash2-20261003/PACKAGE.md`](../../artifacts/operator/stack-change-dflash2-20261003/PACKAGE.md).
  Research `be2cc414` (master `drafters` list, VRAM 37.92 measured), orch `d3233170` + `5265e09d` (DRAFT-SEL-1
  compiler + derived). `reload architect_critic` gave :8083 PID 3793153 with `-md Qwen3.8-27B-DFlash2-Q8_0.gguf
  -ngld 99 --spec-type draft-dflash --spec-draft-n-max 8` (clamped to 7), np4 / 196608 / q8_0 / kv-unified; load
  log shows `draft-dflash`; `check --run-promotion-gate` green. Of the three gates: np2/4/8 scaling was measured
  (DF2-5, v10 qualification np4 ratio 1.239); greedy parity was attributed away from DFlash2 (DF2-6/DF2-8). The
  production-shape measurement is still owed: Q38-T7.
  **Greedy-parity contract (Q38-T10, operator ruling 2026-10-20: per-role).** Speculative serving (DFlash2 n-max 7
  and MTP) is NOT bit-identical to non-speculative greedy on this stack. DF2-6/DF2-8 (12 prompts, 256 tokens): 6 prompts
  differ for dflash, all six first divergences at top1-top2 margins of 0.005-0.079; draft-simple fails too (recorded 5/12).
  DF2-17 (horizon 1600, widths 2 to 8): every speculative arm differs on 12 of 12 stage-1 prompts, and at the production
  mix (q8_0 KV, 24 prompts) 11 of 24 differ with 2 graded flips (`ifeval_1481` PASS to FAIL, `gpqa_diamond_cot_8116937b0ca6`
  FAIL-at-cap to PASS); evidence [`artifacts/gpu-queue-20261020/df2-17/`](../../artifacts/gpu-queue-20261020/df2-17/), first
  divergence located by DF2-18 at a layer-0 Q8_0 `MUL_MAT` with no runtime knob. Exact only under `LLAMA_SPEC_EXACT=serial`
  (no speedup). So "parity was attributed away from DFlash2" does NOT mean "parity holds". Contract: roles that are
  eval, judge, replay, parity-gated or machine-parsed evidence are bitwise-required (spec off or serial-exact); serving roles
  are distributional (graded no-loss gate, Q38-T10.1). Role table and gaps: under Q38-T10 below.
- [x] **Q38-T7 — DFlash2 at the PRODUCTION shape: speed paired with correctness, plus the coherence gate**
  ✅ 2026-10-04 (workspace-ec; the organic-traffic acceptance clause is split out as Q38-T7a, below)
  (STACKCHG-DFLASH2 PACKAGE §7.4 M-1; filed 2026-10-03). DFlash2 was never measured at np 4 / `-c 196608` / q8_0
  KV / kv-unified (recipe runs were ctx 16384 f16, 65536 f16, DF2-5 4096×np). The operator fast path (PID 3737649)
  gave 91.7 tok/s single-stream decode, acceptance 450/490, vs workspace-76's MTP probe of ~37-41 tok/s at the same
  shape (`/mnt/raid0/llm/tmp/ds41-c95/probe-decode-vs-context.md`) — one request, not a measurement. Owed, in the
  owner's :8083 window: the coherence gate at production prompt length; MTP vs DFlash2 decode paired with a
  correctness check at production context; acceptance rate on organic traffic; n-max 7 vs 8 (7 saves ~0.58 GiB of
  GDN state with identical drafting — rides KVU-16). Wire the result as a belief-kernel source (VB-SERVING-DF2).
  - 2026-10-03 ~17:15Z (workspace-ec): runner prepared, dry-run OK, not yet run: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/q38_t7.py` (RUNBOOK step 3,
    :8083 serving at the current KVU-16 shape, 393216 unified / n-max 7, with its roles parked; ~23 min).
    - Phase A: the codified 24-prompt production mix (`inf70/agents/e3-alpha/prompts.json`, recipe WORKLOAD: greedy,
      max_tokens 200, thinking off), DFlash2 arm vs a `speculative.n_max: 0` arm, classified with the INF-70 classifier.
    - Phase B: decode vs context at ~2k/16k/50k/80k with a greedy needle question per length as the paired
      correctness check. It compares 1:1 with the 2026-10-01 MTP table, which was on the pre-KVU-16 196608 pool, so the
      comparison crosses server shapes.
    - Phase C: 4 concurrent ~16k streams. Draft acceptance is recorded for every call.
    - PASS needs every needle answered and no SALAD / EARLY-EOS / EMPTY / HTTP-ERROR on the DFlash2 arm; a
      correctness FAIL marks the speed numbers INVALID. Output: `results/q38_t7/<ts>/{calls.jsonl,report.json,report.md}`,
      schema `epyc.gpublock.q38_t7.v1`. Runs in the coordinated GPU block after ~18:15Z. The adapter row text for
      VB-SERVING-DF2 is prepared in `/mnt/raid0/llm/tmp/wrapup-ec-maskskip/INDEX_ROWS.md`.
  - 2026-10-04 (workspace-ec, note only): **RUNNING** since 02:52:47Z in the GPU block (which started 01:59Z, not
    18:15Z), output `results/q38_t7/20261004T025247Z/`; preflight `slots_debug_env: null`, `argv_nmax7: true`, :8083
    parked. Not complete; the queue after it is KVU-16b, B4g, B4i, then workspace-89's P3 v2 on the mask-skip build.
  - **2026-10-04 (workspace-ec): PASS — speed paired with correctness at the production shape.** Durable copy of all
    evidence: [`artifacts/gpu-block-27b-20261004/`](../../artifacts/gpu-block-27b-20261004/) (`results/q38_t7/`,
    `analysis/q38t7-rescore/`).
    - Run #1 `results/q38_t7/20261004T025247Z/` reported **FAIL**, but the FAIL was a classifier artifact. The v1
      `uniq < 0.35` rule is length-biased: every coherent 1000–1500-token reasoning trace in the repo's corpus scores
      SALAD under it. Chat "stop" on 1–8-token answers was also read as EARLY-EOS. The offline paired re-score
      (`analysis/q38t7-rescore/RESCORE.md`, no inference) gives **PASS**: phase A has 0 drafting regressions out of
      24 (class-equal 24/24, byte-identical 19/24); ground truth is 4/5 in both arms with the same answers; phase B/C
      are 12/12 OK under `inf70-degeneracy.v2`.
    - Run #2 `results/q38_t7/20261004T040110Z/` is a paired long-context re-run (2k and 16k, 1500 tokens, drafted and
      no-draft, full text stored) under the patched runner (schema `epyc.gpublock.q38_t7.v2`): **PASS**. The caller
      read a saved 1500-token output: coherent technical reasoning.
    - **Production mix** (24 prompts, recipe WORKLOAD): DFlash2 **60.02** vs no-draft **31.07** tok/s token-weighted
      (**1.93×**), acceptance **0.53**, 0 drafting regressions.
    - **Long context**, DFlash2 vs the 2026-10-01 MTP probe: 1.04 / 0.99 / 0.95 / 1.06× at ~2k / 16k / 50k / 80k
      (run #1). DFlash2 ≈ MTP at depth. The MTP probe was on the pre-KVU-16 196608 pool, so the ratio crosses shapes.
    - **4 concurrent ~16k streams:** 20.84 tok/s aggregate. The per-stream TTFT of 40–164 s is the prefill/decode
      interleave root-caused under KVU-16b in `kv-unified-stack-rollout.md`.
    - **80k needle:** the model abstained and called the planted vault code "injected instructions" in an AutoKernel
      haystack. That is model behaviour plus a needle-design confound, not a drafting fault; see Q38-T7b.
    - n-max 7 vs 8 is settled by KVU-16, which runs n-max 7. The belief-kernel write side is VB-SERVING-DF2, which
      stays open in `vidya-belief-substrate-program.md`.
  - [ ] **Q38-T7a — DFlash2 draft acceptance on ORGANIC :8083 traffic.** (filed 2026-10-04, workspace-ec, split out of
    Q38-T7.) Q38-T7 ran with :8083's roles parked, so its 0.53 acceptance comes from the codified mix, not from
    organic traffic. Read `draft_n` / `draft_n_accepted` from the KVU-17 serving records (`logs/serving_calls/`) for
    `architect_general` / `coder_escalation` on :8083 since the 2026-10-04 restore. This is a passive read with no
    inference. Done when acceptance over ≥ 200 organic drafted calls is recorded here with its window, and is compared
    against the codified-mix 0.53.
  - [x] **Q38-T7b — the needle test must use a neutral haystack and be asked in both arms.** (filed 2026-10-04,
    workspace-ec.) The 80k miss in run #1 was a refusal to repeat an "injected" fact planted in an AutoKernel
    planner context. Before the next production-shape correctness gate, use a neutral filler (RULER noise, or essays
    with sentence ids). Ask every needle in the no-draft arm too, and give phase C a no-draft pair. The INF-59 E0
    runner (`yarn-context-extension-research.md`) builds this harness, so reuse it rather than writing a second one.
    Done when `q38_t7.py` (or its `coherence_gate` successor, TD-30d) uses the neutral haystack with paired needles.
  - [x] **Q38-T7b source and private-admission preparation — freeze the neutral E0 paired N/C runner and pass the corrected T1 gate.** ✅ 2026-10-27 — source `codex/ni-q38-t7b-20261027` at `7a73805c13d6db1e3dda47341090b8789a257908`; SOURCES.sha256 content SHA-256 `7f65bb4a9368fef0a5d3ad9c788d88d0227c2f842ded0316518c7f24eb6dd33a`; neutral E0 manifest `2eb07287faba49ed5e368700b273aa8345e927cf53d0aeb34371aca2888b1b04`. The 10:54:24Z T1 refusal (rc=6) was a packet defect (missing `dryrun_pass`); corrected full row passed private validation, normal `dryrun_check.py admit --require-proof`, and private `grant_ok`. OWNER later accepted corrected same-entry q3 PF `46218b17e9100c919828696317b0a94c7893fe39a453b11d`, normal 2700-second admission (150-GiB floor), and grant_ok for the live owner PID. Preparation only; the separate correctness result is recorded below. [no-belief: source, PF and admission only]
  - *(2026-10-28, ws58 results filing.)* Q38-T7b C-cachepair: rc0 complete 23:38:11Z. Superseded by the closeout entry below.
  - **2026-10-28 (Q38-T7b closeout, workspace-58): N 16/16 PASS; cache-free C pair PASS, valid speed result.** N arm `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/q38_t7/20261027T120457Z/report.json` (16/16). Cache-free C repair `/mnt/raid0/llm/tmp/codex-ni-20261027-q38-t7b/c-repair/out/result-20261027T233116Z-2059430/report.json`: `cache_prompt=false`, cache_n 0 on all rows, build 10303, correctness PASS, aggregate decode 24.14 tok/s, draft acceptance 0.36, drafted arm faster on every stream. Replaces the confounded 14.13 tok/s phase C figure. Source `codex/ni-q38-t7b-20261027` @ `736992fa656c474fc9d8301f2e733601b9c743ed`. [belief: cc]
  - **2026-10-27 (Q38-T7b run, workspace-58, 12:04Z): needle correctness PASS 16/16; phase C speed comparison CONFOUNDED, no speed verdict.** [belief: cc]
    Report `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/q38_t7/20261027T120457Z/report.md` (+ `report.json`, `calls.jsonl`); b10303-ffc1bac82, :8083 production shape, roles parked (`parked_8083` true), inf70-degeneracy.v2 OK on all 8 C streams.
    N: both neutral E0 needles (manifest sha256 `2eb07287...`) found, drafted and no-draft, at ~2k/16k/50k/80k = 16/16 (no drafting regression; the 2026-10-04 80k miss was the planner-context confound, as hypothesised).
    C (4 concurrent ~16k streams), dflash2: aggregate decode 14.13 tok/s over the overlap span (sum of per-stream 33.94); per-stream decode 3.85-16.4 tok/s; TTFT 86-308 s; draft acceptance 0.32-0.40 (mean 0.3575). Nodraft: 9.12 tok/s per stream with an identical TTFT of 3.566 s on all 4 streams.
    **Confound:** the identical TTFT strongly suggests prefix-cache reuse, because nodraft ran after dflash2 on the same four prompts. The speed comparison is therefore invalid; no speed claim is made either way. Acceptance 0.3575 is descriptive only.
    Reporting oddity: preflight/report shows speculative `['None']` from `/props` although argv had n-max 7 and draft acceptance was measured.
    VRAM: own-PID KFD peak 50.795 GiB (min 47.813), card peak 50.821 GiB, 809 samples taken during the run.
    Calendar wrapper ended rc1 ("expected one actual N+C report, found 0"): FALSE FAIL; runner rc was 0 and wrote the report to the default results dir, not the wrapper `out/`.
    - [x] **Q38-T7b-C2 — rerun phase C with a valid speed comparison:** clear the prefix cache between arms (or alternate ABAB with distinct/cache-busted prompts) and assert nodraft TTFT is not identical across streams. Done when a paired C table with non-degenerate nodraft TTFT is filed here.
    - [ ] **Q38-T7b-W — wrapper report-path fix:** bind the wrapper's "actual N+C report" check to the runner's results dir (or pass the runner an output dir) so rc0 runs are not marked failed. Also investigate why `/props` reports spec_types `['None']` under a dflash n-max-7 argv.
  - **2026-10-20 (Q38-T9, per-class replay, no inference): no class loses; the 24-prompt mix cannot refute a prose/chat sign flip.**
    Frozen input `artifacts/gpu-block-27b-20261004/results/q38_t7/20261004T025247Z/calls.jsonl`, sha256
    `56315a4b7adf11f759efab5f9a9616eb600b382e0a81f8b9c5d1c41326855bf2` (68 lines; phase A = 48 records = 24 prompts x 2 arms;
    on-disk copy equals the origin/main blob). Script and raw output (sha256 `fb4ad45f...` / `311b52f5...`):
    `artifacts/gpu-block-27b-20261004/analysis/q38t9-perclass/`. Token-weighted ratio = sum(predicted_n)/sum(predicted_n/decode_tps)
    per arm; draft_acc = sum(draft_n_accepted)/sum(draft_n). Classes by suite: code = coder, bigcodebench, debugbench,
    livecodebench; reasoning/math/science = math, gpqa_diamond_cot, physics, mmlu_pro, thinking; instruction/prose/chat/other =
    instruction_precision, real_suite_v1, simpleqa, mode_advantage. Six prompts with `predicted_n` < 50 are EXCLUDED from ratios
    (listed in the table).
    | class | qualifying prompts | DFlash2 tok/s | no-draft tok/s | token-weighted ratio | draft_acc |
    |---|---:|---:|---:|---:|---:|
    | code | 6 | 83.38 | 31.27 | 2.667 | 0.803 |
    | reasoning/math/science | 6 | 63.35 | 31.34 | 2.021 | 0.583 |
    | instruction/prose/chat/other | 6 | 45.10 | 30.55 | 1.476 | 0.366 |

    All 18 qualifying prompts: 60.01 vs 31.06 tok/s (matches the reported 60.02 / 31.07). Predeclared rule: no class has a
    token-weighted ratio < 1.0, so no A/B task is filed. Per-prompt sub-1.0 ratios exist but do not move a class: ifeval_1481
    0.925 (qualifying, acc 0.175) and the excluded short answers ifeval_322 0.686, mmlu_pro x2 ~0.45, hellaswag 0.449 (n 2-9,
    acc 0.114-0.143). The prose class is the weakest (ratio 1.476, acc 0.366) and holds only 6 prompts, one of them a loser;
    this mix cannot refute a prose/chat sign flip. Next evidence: Q38-T7a (organic :8083 acceptance, >= 200 drafted calls).
    Per-prompt table:

      | prompt | suite | class | predicted_n | DFlash2 tok/s | no-draft tok/s | ratio | draft_acc | status |
      |---|---|---|---:|---:|---:|---:|---:|---|---|
      | mbpp_0391 | coder | code | 41 | 60.85 | 31.45 | 1.935 | 0.5893 | EXCLUDED (<50) |
      | mbpp_0303 | coder | code | 200 | 78.06 | 31.55 | 2.474 | 0.7217 | in |
      | mbpp_0508 | coder | code | 57 | 88.08 | 31.14 | 2.829 | 0.875 | in |
      | bcb_BigCodeBench/547 | bigcodebench | code | 88 | 93.11 | 31.47 | 2.959 | 0.9048 | in |
      | bcb_BigCodeBench/512 | bigcodebench | code | 200 | 83.17 | 31.55 | 2.636 | 0.7925 | in |
      | debugbench_flood-fill_cpp | debugbench | code | 200 | 96.58 | 30.43 | 3.174 | 0.9886 | in |
      | leetcode_the-number-of-the-smallest-unoccupied-chair | livecodebench | code | 200 | 73.96 | 31.51 | 2.347 | 0.6992 | in |
      | ma_multi_015 | mode_advantage | prose | 200 | 64.85 | 27.38 | 2.369 | 0.7112 | in |
      | gsm8k_00739 | math | reason | 200 | 73.16 | 31.46 | 2.325 | 0.8204 | in |
      | gsm8k_00115 | math | reason | 200 | 74.56 | 31.37 | 2.377 | 0.7205 | in |
      | gsm8k_00041 | math | reason | 200 | 56.38 | 31.37 | 1.797 | 0.4842 | in |
      | gpqa_diamond_cot_5fd3fe9084c9 | gpqa_diamond_cot | reason | 200 | 63.86 | 31.1 | 2.053 | 0.5824 | in |
      | gpqa_diamond_cot_8116937b0ca6 | gpqa_diamond_cot | reason | 200 | 57.95 | 31.3 | 1.851 | 0.5016 | in |
      | phybench_electricity_25 | physics | reason | 200 | 58.92 | 31.46 | 1.873 | 0.5065 | in |
      | mmlu_pro_law_01532 | mmlu_pro | reason | 2 | 25.03 | 54.98 | 0.455 | 0.1429 | EXCLUDED (<50) |
      | mmlu_pro_health_05883 | mmlu_pro | reason | 2 | 25.05 | 55.31 | 0.453 | 0.1429 | EXCLUDED (<50) |
      | ifeval_3456 | instruction_precision | prose | 200 | 47.92 | 31.36 | 1.528 | 0.393 | in |
      | ifeval_322 | instruction_precision | prose | 9 | 22.11 | 32.25 | 0.686 | 0.1143 | EXCLUDED (<50) |
      | ifeval_1481 | instruction_precision | prose | 200 | 29.24 | 31.62 | 0.925 | 0.175 | in |
      | ifeval_1129 | instruction_precision | prose | 139 | 51.56 | 31.61 | 1.631 | 0.4245 | in |
      | real_suite_v1_0003 | real_suite_v1 | prose | 200 | 45.29 | 31.48 | 1.439 | 0.3579 | in |
      | real_suite_v1_0032 | real_suite_v1 | prose | 53 | 67.32 | 30.84 | 2.183 | 0.6 | in |
      | simpleqa_general_01814 | simpleqa | prose | 8 | 36.92 | 32.15 | 1.148 | 0.4286 | EXCLUDED (<50) |
      | hellaswag_06230 | thinking | reason | 2 | 24.89 | 55.41 | 0.449 | 0.1429 | EXCLUDED (<50) |
- [x] **Q38-T8 — DFlash2 load-time VRAM peak sampled DURING the load** (PACKAGE M-2). ✅ 2026-10-03 — the sampler
  armed before `reload architect_critic` (`/mnt/raid0/llm/tmp/stack-change-dflash2-20261003/apply/vram_during_reload.log`,
  0.5 s cadence) reads 44.31 GiB card-total on the OLD process (04:44:36Z), 0.01 GiB at unload (04:44:39Z), and a
  NEW-process load-time peak of **43.49 GiB at 04:44:57Z**. Load peak ≤ the 44.30 GiB runtime reading, so the
  declared `vram_non_kv_gib: 37.92` (runtime-derived) stays the conservative figure; no registry change.
- [x] **Q38-T4 ✅ 2026-08-21 — CLOSED, and neither proposed fix was the right one: the "drift" was a CHECK-TIME MODE ARTIFACT.** The guard builds its launch view against the realized fleet mode, defaulting to `full` in a clean shell (`stack_change_guard.py:1183-1191`, `stack_numa_mode.py:10`), which filters the half instances out of the view while the master unconditionally projects them into `serving.ports`. Under the PRODUCTION mode (`ORCHESTRATOR_STACK_NUMA_MODE=both`) all 13 errors vanish with ZERO data edits; after a mode-correct `update` (re-pinning the launcher hash the jinja fix had legitimately broken) the check is **FULLY GREEN — `guard: ok`, `guard_strict: ok`, `acceptance: no-inference checks passed`** — the first fully green stack-change check of the campaign. Master, topology, stack template and launch manifest were all correct all along; the ratify script now exports the mode. (Earlier annotation about launch-manifest-vs-accepted_gaps options is superseded. CORRECTED FRAMING 2026-08-21 (after a reverted over-read): the flagged ports are
      the HALF instances, which are LIVE production config** — `stack_templates/default.yaml:93-94`
      and `:121-122` launch them (`{port: 8080, numa: HALF_A, threads: 48}` …). The operator's
      "no quarter instances anymore" covers quarters only (retired 2026-07-30); an over-broad
      reading briefly removed 2 of 3 half-port sites from the master working tree — caught by the
      operator, reverted verbatim, and the recompile never ran, so no artifact or serving state was
      affected. THE REAL FIX therefore runs the other way: represent half mode in
      `orchestration/launch_manifest.yaml` (whose comments already name the half ports) so
      `guard_all_surfaces` sees them as launchable — or file exact `(role, gap)` accepted_gaps
      declarations. Operator to pick the direction; the master is not the defect. Original finding
      follows. — quarter-port surface drift (pre-existing, surfaced 2026-08-21 by the ratification's
      post-check).** `guard_all_surfaces` fails on frontdoor / ingest_long_context / toolrunner /
      worker_* because their `serving.ports` declare quarter-instance ports (8080/8180/8082/8182/…)
      that `orchestration/launch_manifest.yaml` carries only as comments. Unchanged since 2026-03;
      failed identically before this ratification's writes. Either represent quarter mode in the
      launch manifest or file exact `(role, gap)` `accepted_gaps.yaml` declarations (expiry
      required). Blocks a fully-green `check`; does NOT block the swap surfaces, which verify clean.
- [x] **Q38-T5 ✅ 2026-08-21 22:00Z — STACK STARTED, `live == config` VERIFIED, THE SWAP IS LIVE.**
      Started under `ORCHESTRATOR_STACK_NUMA_MODE=both`; built-in stack-change gate PASSED at launch
      (`promotion_gate: ok`, launch roles match registry); 15 servers healthy. Checklist, all five
      green on :8083 (pid 896239): (1) serves `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf` with the
      documented Unsloth template; (2) flags `--device ROCm0 --jinja --spec-draft-n-max 8` — the
      measured optimum, live; (3) all four ggml libs from frozen v9 `build-hip` on LIVE process maps;
      (4) KFD count 4 (designed GPU co-tenancy: architect+vision+sd+embedder); (5) real generation
      correct (17×23→391), `enable_thinking=false` live-confirmed (empty reasoning_content), VRAM 93%
      sampled DURING the request. **OPERATOR FLAG, one observation:** the cold-start launcher rejected
      the `both` lineup (no fleet to adopt) and fell through to priors at `--numa-mode=quarter` —
      HALF instances launched (:8080/:8180/:8082/:8182/:8185/:8285), FULL instances (:8070/:8072)
      did NOT. Single-stream frontdoor throughput therefore runs on halves tonight; whether to
      restart into `both` (full+halves) is a lineup-policy call left to the operator, not churned
      at 22:00. Original task follows.** post-CT-1 stack start + checklist (operator-directed 2026-08-21).** As soon as
      CT-1's arms complete: (a) verify no autokernel GPU work is running (none is as of 14:05Z —
      no codex session listed, no claims, no KFD processes expected); if one appeared, negotiate a
      quiet window with that codex agent (via workspace-c0 if not directly reachable) before
      touching the GPU; (b) start the stack via `orchestrator_stack.py` (the lean auto-recompiles
      at start; derived is already regenerated and verified); (c) run the stack-change checklist:
      `live == config` — confirm architect_general serves Qwen3.8-27B-Q8_0 at draft_max 8 on
      :8083, `verify_ggml_linkage.sh`, non-zero VRAM sampled DURING a request, KFD process count;
      (d) close the ticked-but-stale 2026-08-20 checklist item against this evidence.
- [x] **Q38-T6 ✅ 2026-08-23 — cold-start lineup defect FIXED (orchestrator `96498c3d`).**
      (a) `stack_commands.py` cmd_start fallback: hardcoded `"quarter"` → realized-fleet
      inference first, else `ORCHESTRATOR_STACK_NUMA_MODE` env, else ratified `"both"`
      — an unflagged cold start now produces the production lineup (fulls included);
      (b) stale argparse help `orchestrator_stack.py` (was "QUARTERS-ONLY…FULL_DISABLED…
      defaults to 'quarter'") + `_filter_by_numa_mode` docstring (`stack_manifest.py`)
      rewritten for the half-fleet reality (quarters retired 2026-07-30; `quarter` token
      now means halves 2x48t; `both` is ratified production); (c) API-side producer-2
      liveness veto (`src/config/models.py`): a TOTAL cold start (nothing listening
      anywhere) is not the env=full poison signature — the veto now requires ≥1 live
      port anywhere, so a cold start accepts the lineup instead of logging a spurious
      "lineup rejected" and falling through to stale priors. Recovery path re-verified
      intact: explicit `--numa-mode both` still wins. 290 targeted tests pass (incl.
      new cold-start + veto tests); py_compile + ruff clean. Original task follows.** cold-start lineup defect (root-caused 2026-08-22 after it fired on the Q38-T5
      start).** The launcher NEVER reads `ORCHESTRATOR_STACK_NUMA_MODE` — mode comes from argv
      `--numa-mode` only, and the cold-start fallback is hardcoded `"quarter"`
      (`stack_commands.py:1588`, pre-dating the 2026-07-30 half-fleet ratification), so an
      unflagged cold start can never produce the production `both` lineup and silently drops the
      THREE full instances (frontdoor :8070, worker_general :8072, ingest_long_context :8085). Fix: (a) change
      the :1588 fallback to the ratified production mode (or read the env there); (b) update the
      stale argparse help ("production is QUARTERS-ONLY… FULL_DISABLED",
      `orchestrator_stack.py:2773-2786`) and the `_filter_by_numa_mode` docstring
      (`stack_manifest.py:833-850`); (c) cosmetic: the API-side producer-2 liveness veto
      (`models.py:664-676`) logs a spurious "lineup rejected" on every cold start and would poison
      the API lineup if the API ever started before the fulls finish loading. Recovery path used
      tonight (verified safe: `--only` clobber fixed in `f2ffd298`):
      `start --only frontdoor worker_general ingest_long_context --numa-mode both` + scoped
      `reload orchestrator`.
- [x] **Stack-change checklist / `stack_change_pipeline.py` regenerate** ✅ 2026-08-21 — regenerated (mode-correct, fully green check) and the start-time gate re-ran it PASSING; checklist closed under Q38-T5's five-point evidence above. Nothing is serving
  (`:8083` unbound), so config and runtime agree only by both being absent. `live == config` is
  UNVERIFIED until someone actually starts the stack; that is a separate lifecycle action with its
  own gates and was deliberately not taken here.
- [x] **Architect bench (reasoning + coding ladders)** ✅ 2026-08-15 — L0–L4: mmlu_pro 56.7%, gpqa_diamond 42.4% (letter) / 81.3% (CoT), aime25 **76.7%**, olympiadbench_hard 47.1%; P2a–P2d: humaneval 96.3%, BCB-hard 31.1%, LCB-hard **52.8%** (tops stock 45.3%), SWE-oracle 39/40 single-shot (2 hard tool-using instances deferred to the agentic rung). Full tables in `gpu-candidates-surface-qwen38-update.md` + the artifact dir. The quality uplift the operator banked is now measured — it is real on LCB (52.8 vs 45.3) and aime25 (76.7), near-parity elsewhere, with SWE + agentic still landing.
- [x] ✅ 2026-10-20 **Q38-T9 — Per-class replay of the banked Q38-T7 phase A: where does DFlash2 n-max 7 lose to no-draft? (intake-2004; filed 2026-10-20).** No inference. Frozen input: `artifacts/gpu-block-27b-20261004/results/q38_t7/20261004T025247Z/calls.jsonl` phase A (24 prompts x 2 arms; record its sha256). Group suites into code, reasoning/math/science, and instruction/prose/chat/other; compute per-prompt and token-weighted DFlash2/no-draft decode ratios from the stored `decode_tps`, `predicted_n` and `draft_acc`; prompts with `predicted_n` < 50 are listed and excluded from ratios, never silently dropped. Predeclared: a class with >= 3 qualifying prompts and a token-weighted ratio < 1.0 files a paired live class-stratified A/B (per-request `speculative.n_max` 7 vs 4 vs 0) as a new task here; otherwise the note records that the 24-prompt mix cannot refute a prose/chat sign flip and names the organic-traffic read (Q38-T7a) as the next evidence. Done when the table is filed under Q38-T7 with the file digest.
- [x] ✅ 2026-10-20 **Q38-T10 — State the greedy-parity contract of the DFlash2 serving path where the selection decision is recorded (intake-2004/2021; filed 2026-10-20).** Add to the "DFlash2 selection decision" row: speculative serving (DFlash2 n-max 7 and MTP) is NOT bit-identical to non-speculative greedy on this stack (DF2-6/DF2-8, 12 prompts at 256 tokens: 6 prompts differ for dflash, all six first divergences at top1-top2 margins of 0.005-0.079, and draft-simple fails too, recorded 5/12; exact only under `LLAMA_SPEC_EXACT=serial`, which gives no speedup); parity-gated work and eval-reproducibility runs must use spec off or serial-exact; the DF2-17 horizon/width result and any exact-argument-role decision (monitor M6) are appended when they report. Done when the statement is in the row with the DF2-17 pointer, so "parity was attributed away from DFlash2" can no longer be read as "parity holds".
  - **2026-10-20 OPERATOR DECISION PACKAGE (Q38-T10; prepared by q38-t10, no decision taken, checkbox NOT ticked).** Sources: DF2-17 and DF2-18 result notes in `dflash2-block-drafter-experimental-build.md` (evidence `artifacts/gpu-queue-20261020/df2-17/`, `.../df2-18/`), AKX-ALL-26 CPU and HIP notes in `autokernel-all-devices-all-dimensions.md`, the M6 monitor record (same DF2 handoff), the Q38-T9 note above. Every number is quoted from those notes except the interval and sample-size arithmetic under Option 1, computed here and marked.
    - **Context.** Speculative serving (MTP, DFlash2) is not bit-identical to spec-off greedy. DF2-17 stage 1 (f16 KV, 12 prompts, cap 1600): every speculative arm (verify widths 2 to 8) differs on 12 of 12 prompts; 65 of 72 forks are near-ties under the frozen rule, the other 7 are three-way ties (arm token is the baseline's rank 3, 0.007 and 0.021 nats below rank 2). Stage 2 (q8_0 KV, 24-prompt mix, DFlash2 n-max 7): 11 of 24 differ, all near-tie (baseline margin 0.005-0.032 nats), 10 graded, 2 graded flips: `ifeval_1481` baseline PASS to arm FAIL (2 bullets required, arm wrote 4); `gpqa_diamond_cot_8116937b0ca6` baseline FAIL (truncated at the cap) to arm PASS. Spec-off A/A and `LLAMA_SPEC_EXACT=serial` are bit-identical at every width and both KV types. DF2-18: the first differing node is `node_13`, a layer-0 Q8_0 `MUL_MAT`, at every width, prefix and row; knob-off re-runs (`GGML_CUDA_DISABLE_FUSION`, `GGML_CUDA_DISABLE_GRAPHS`, `GGML_CUDA_FA_MASK_SKIP=0`) remove zero differing nodes; the route flips (MMVQ geometry 1|2, MMVQ to MMQ 4|5, flash-attn VEC 1|2 and VEC to rocWMMA 2|3) have no runtime knob. Rowexact argmax flips: 0 of 62 rows, with the batch-vs-reference margin moving by at most 0.058 nats (median 0.024), so only a near-tie below about 0.06 nats flips at those prefixes. AKX-ALL-26 HIP first-fail k on the 27B dense shapes: 2 for Q8_0 and Q4_K, 4 for Q3_K, 5 for Q6_K and IQ2_XXS/XS, IQ3_XXS, IQ3_S, IQ4_XS; flash-attn fails at k=2 in all 12 cells (F16, Q8_0, Q4_0 KV); GATED_DELTA_NET passes with F32 state and fails with BF16 state at k=2. AKX-ALL-26 CPU: `GGML_ROWEXACT_N=9` makes all nine MUL_MAT types pass k=1..9; CPU flash-attn with F16 KV fails at k=2 at 24 threads and passes at 1 thread. The choice is the operator's because the options trade reproducibility against throughput and kernel engineering that only the operator budgets. M6 trigger (b), a graded flip in DF2-17, has fired; trigger (a) is partly met: the route is located but has no runtime knob, so pinning it means a kernel change on an experimental branch.
    - **Option 1, distributional parity (no bitwise claim).** Guarantee: on graded suites at a stated n there is no measurable quality loss; tokens may change at near-ties. Speed cost: none (Q38-T9 token-weighted DFlash2 vs no-draft ratios 2.667 code, 2.021 reasoning, 1.476 prose; 60.01 vs 31.06 tok/s over 18 qualifying prompts). Engineering: a paired gate harness and a stated n. Minimum evidence still needed: the DF2-17 data already refute "no flips" (2 flips in 24 prompts; one regression, one truncation-driven gain, which are different kinds of event and must be counted separately). Computed here, exact binomial (Clopper-Pearson) 95% two-sided: 2 of 24 gives 1.0% to 27.0%; 11 of 24 differing gives 25.6% to 67.2%. Sample sizes for a stated bound: after seeing zero flips, a flip rate below 5% at 95% one-sided confidence needs n = 59 graded prompts (0.95^59 < 0.05), below 2% needs 149, below 1% needs 299 (at 97.5% one-sided: 72, 183, 368). To estimate a rate near the observed 2/24 = 8.3% to +-5 points (normal approximation) needs about 117 graded prompts. Truncated outputs are ungradable (stage 1: 66 of 72 divergent pairs), so the corpus needs short-answer tasks or a cap above 1600, otherwise graded n is far below n run. Unmeasured: the flip rate on organic :8083 traffic (Q38-T7a is the planned read).
    - **Option 2, bitwise parity for all speculative serving.** Guarantee: spec-on output equals spec-off greedy token for token (today true only under `LLAMA_SPEC_EXACT=serial`, which gives no speedup). Engineering, from the findings: HIP has no `GGML_ROWEXACT_N` analogue, and the width variance is not Q8_0-only (Q4_K F@2, Q3_K F@4, Q6_K and the IQ types F@5, flash-attn F@2 in all 12 cells, BF16-state GDN F@2), with no runtime knob (DF2-18). The work is new row-exact verify kernels on an experimental branch from the champion tip: a MUL_MAT path reproducing the k=1 reduction geometry for every served quant type, plus a flash-attn path whose reduction and `parallel_blocks` match ncols=1; then a probe cell that flips FAIL to PASS, a token-identical DF2-17 rerun at 1600, and a gfx90a decode-cost measurement (the M6 sequence). The CPU lever `GGML_ROWEXACT_N=9` is not complete either (CPU F16-KV flash-attn still fails at k=2 at 24 threads). No note sizes the work in days; that is unmeasured. Speed cost: UNMEASURED. No note reports the throughput of `GGML_ROWEXACT_N=9` on CPU or of any row-exact HIP path; serial-exact (no speedup) is the ceiling of the loss. Minimum evidence still needed: the prototype, the token-identical rerun and the decode-cost number against the noise floor. Option 2 cannot be priced until that number exists.
    - **Option 3, per role.** Bitwise for roles where reproducibility matters (eval, judge, replay, parity-gated work, any machine-parsed exact-output role): spec off or serial-exact today, row-exact kernels if the Option 2 prototype is later built. Distributional (the Option 1 gate) for serving roles. Guarantee: reproducible evidence where the stack makes claims from it, full speedup where users are served. Cost: the Option 1 gate plus a role-to-contract table; the bitwise half costs the speedup only on those roles (spec off 31.06 tok/s vs 60.01 on the Q38-T9 18-prompt set) and needs no kernel work to start. Evidence needed: the list of reproducibility-bound roles and, for any machine-parsed role on the DFlash2 server, a replay corpus (M6 trigger (b)). One regression (`ifeval_1481`) does not settle whether speculation is defective or the sample is a near-tie draw.
    - **Recommendation: Option 3, with the Option 1 gate as its serving half; build the Option 2 prototype only to obtain the decode-cost number.** It is available now without kernel work, keeps the 1.476 to 2.667 throughput ratios, and makes eval and replay exact, which the current wording leaves ambiguous. What would change it: a measured HIP row-exact decode cost inside the noise floor would make Option 2 cheap and favour bitwise everywhere. Tie-break measurement: the prototype's gfx90a decode cost.
    - **Default if the operator makes no choice:** the Q38-T10 wording stays as filed (speculative serving is NOT bit-identical; parity-gated and eval-reproducibility runs use spec off or serial-exact), i.e. Option 3's bitwise half with no stated serving gate; no kernel prototype and no flip-rate gate run.
  - **2026-10-20 OPERATOR RULING (verbatim from the coordinator relay): "Option 3, per-role. Implement as far as possible without a stack change."** Contract stated in the "DFlash2 selection decision" row (checkbox ticked on that basis).
  - **2026-10-20 role-to-contract table (read-only; live registry and code on the orchestrator tree at this date).** Speculative servers (`orchestration/model_registry.yaml` `server_mode`): `frontdoor` :8070/:8080/:8180, `acceleration.spec_type: draft-mtp`, `draft_max: 4` (lines 1729-1733); `architect_critic` :8083, `draft-dflash`, `draft_max: 7` (lines 1881-1883; `stack_topology.yaml:75` `architect_critic: dflash2`); `architect_general` :8074, `draft-mtp`, `draft_max: 4` (lines 1931-1932; `stack_topology.yaml:267`). Aliases inherit the host process: `worker`, `worker_summarize`, `worker_general`, `worker_explore`, `worker_math`, `toolrunner` on frontdoor (`shared_with`, line 1709-1715); `coder_escalation` (line 1737-1777) and `ingest_long_context` on architect_critic. No spec on `worker_vision` :8086 (`acceleration` baseline).
    | role (process) | contract | what it runs today |
    |---|---|---|
    | frontdoor, worker, worker_summarize, worker_explore, worker_math, toolrunner (:8070/:8080/:8180) | distributional (serving) | MTP spec on (n-max 4) |
    | coder_escalation, ingest_long_context (:8083) | distributional (serving) | DFlash2 spec on (n-max 7) |
    | architect_general (:8074) | distributional (serving) | MTP spec on (n-max 4) |
    | **LLM judge, default role `architect_critic` (:8083)** | **bitwise-required** | **spec on (DFlash2)**: `scripts/autopilot/eval_tower.py:150` (`DEFAULT_LLM_JUDGE_ROLE`), `:3556` (`LLM_JUDGE_ROLE` env default) |
    | **model grader, `judge_role` default `worker_general` (frontdoor :8070)** | **bitwise-required** | **spec on (MTP)**: `src/pipeline_monitor/model_grader.py:219` |
    | **coherence judge, local default `worker_general` (frontdoor)** | **bitwise-required** | **spec on (MTP)**: `src/typed_decisions/coherence_judge.py:92`, `:649` (env `ORCHESTRATOR_COHERENCE_JUDGE_ROLE` can rebind) |
    | **rubric judge roles** (`AUTOPILOT_RUBRIC_JUDGE_ROLES`, default empty) | **bitwise-required** | spec on whenever bound to a spec role (`scripts/autopilot/eval_tower.py:4002-4006`) |
    | **EvalTower generation** on the roles under test (bottleneck role default `frontdoor`, `eval_tower.py:2776`) | **bitwise-required** when the run is parity-gated or reproducibility-claimed | spec on (the hosting process) |
    | **`eval_batch_frontdoor` :18070** (launcher-only warm lane, frontdoor model, `launch_manifest.yaml:309-312`) | **bitwise-required** (EvalTower batches) | not determinable from the registry (no `server_mode` row); treat as spec on until its launch argv is read |
    | **typed-decision replay** (`src/typed_decisions/routing_replay.py:78,141`; `judge_redundancy.py:56`), own server `:8199` | **bitwise-required** | whatever that operator-started server was launched with; not a registry role |
    Serial-exact: `grep` for `LLAMA_SPEC_EXACT` / `spec_exact` in the orchestrator tree (src, scripts, orchestration, excluding the venv) finds nothing, so no role runs serial-exact today. `LLAMA_SPEC_EXACT` is read once at server start (`tools/server/server-context.cpp:61`).
  - **2026-10-20 GAPS.** Every bitwise-required row above that runs spec on is a gap: the LLM judge (:8083, DFlash2), the model grader and coherence judge (frontdoor, MTP), any rubric judge bound to a spec role, EvalTower generation on spec roles, `eval_batch_frontdoor` (unverified) and `:8199` replay (unverified).
    - **Why serial-exact is not the minimal fix:** it is a process-level env read at start, and these bitwise-required callers share their process with serving roles (judge on :8083 with coder_escalation, grader on :8070 with frontdoor). Setting it on the process would remove the speedup for the serving roles too, contradicting the ruling. A dedicated spec-off judge server would be a real stack change (new server, VRAM or NUMA placement), larger than needed.
    - **Minimal fix is a per-request flag, NOT a stack change.** `tools/server/server-schema.cpp:205` defines `speculative.n_max` as a per-request cap, described "0 disables speculation for the request". The orchestrator never sends it (no `speculative` key in the `src/backends/llama_server.py` payload build, sampling block at lines 1458-1463). Files a change would touch (NOT edited): `src/backends/llama_server.py` (payload build and the request dataclass field), then the callers that must set it: `scripts/autopilot/eval_tower.py` (judge dispatch near `:3556` and generation in parity-gated runs), `src/pipeline_monitor/model_grader.py:219-230`, `src/typed_decisions/coherence_judge.py` (call near `:750`), plus the replay and `judge_redundancy` CLIs. No registry, topology, launch manifest or stack_env change, so the stack-change skill's package and the operator signature do not apply; the orchestrator API reloads via `orchestrator_stack.py reload orchestrator` only, never a full stack reload.
    - **Unverified prerequisite (so nothing is applied yet):** no note shows that a request with `speculative.n_max: 0` on a spec server is token-identical to a spec-off server, alone or beside a speculating slot. Q38-T10.1's control arm measures exactly that, and the code change waits on it. If it fails, the fallback is a dedicated spec-off server (stack-change package).
    - No stack-change package was written: the minimal fix is code, and the package form is only the fallback.
  - [x] **Q38-T10.2 - close the bitwise-required gaps from the Q38-T10 role table.** (a) read the launch argv of `eval_batch_frontdoor` :18070 (`launch_manifest.yaml:309-312`) and of the operator-started :8199 replay server and record whether spec is on; (b) add the per-request `speculative.n_max: 0` opt-in for EvalTower generation when a run is parity-gated or reproducibility-claimed (today "never opt in"; the AST test `test_only_bitwise_callers_of_call_orchestrator_forced_opt_in` pins exactly 3 opt-in call sites, update it); (c) re-index gitnexus for epyc-orchestrator via `scripts/gitnexus-analyze.sh` (deferred on the q0 flock). Done when every GAPS row is closed or declined with a reason. (filed 2026-10-20)
    - *(2026-10-24, batch-b; orchestrator `45f6df5d` on main.)* (a) `eval_batch_frontdoor` :18070 argv, read from code (`scripts/server/orchestrator_stack.py:1226 _build_eval_batch_frontdoor_command`, which calls `_append_runtime_spec_args` from frontdoor's stack priors) and pinned by `tests/unit/test_build_server_command_helpers.py::test_eval_batch_frontdoor_command_uses_declared_serving_shape`: `--spec-type draft-mtp --spec-draft-n-max 4`, `-np 2 -c 32768 -ctk/-ctv q8_0`. **Speculative decoding is ON.** Not a registry role; the manifest row (`launch_manifest.yaml:309-312`) only declares the lane. GAP CLOSED by the per-request opt-in in (b) (no stack change); this reads builder code + test, not a live process.
    - *(2026-10-24, batch-b.)* (a) `:8199` replay server: argv NOT discoverable from files (searched src, scripts, docs, orchestration, progress, logs, artifacts; `:8199` appears only as the default `--server-url` in `routing_replay.py:142`, `judge_redundancy.py`, `routing_counterfactual.py` docstrings, and a `champion-sidecar-8199.lock` trash entry). DECLINED as a file-read item with reason: the replay CLIs already wrap calls in `spec_policy.bitwise_scope()` (routing_replay.py:1357), and flag `spec_off_bitwise_roles` is ON in prod since 5d4ad2c0, so requests to :8199 carry `speculative.n_max: 0` whatever the server's startup argv.
    - *(2026-10-24, batch-b.)* (b) DONE: `scripts/autopilot/eval_tower.py` generation call now `call_orchestrator_forced(**call_kwargs, **_bitwise_generation_spec_kwargs())`. Opt-in is env `AUTOPILOT_EVAL_BITWISE_GENERATION=1` (also true/yes/on) set by the launcher of a parity-gated or reproducibility-claimed run; unset => payload unchanged (default stays "measure the serving path"); still honours `spec_off_bitwise_roles`. AST test `test_only_bitwise_callers_of_call_orchestrator_forced_opt_in` updated to eval_tower 3 + model_grader 1 (4 opt-in sites); `test_eval_generation_call_never_carries_field` anchor updated; new `test_eval_generation_opt_in_is_env_gated`. Tests: `test_spec_off_bitwise_roles.py` 33 passed; full integration run on rebased main 383 passed, 1 skipped. Takes effect at the next autopilot/orchestrator process restart (main-owned; not done here). Remaining job-spec: parity-gated EvalTower runs must set the env var; the control arm (Q38-T10.1: 20/20 identical, per-request n_max 0 == spec-off) already proved the mechanism.
    - *(2026-10-24, batch-b.)* GAPS rows status: LLM judge :8083, model grader, coherence judge, rubric judges, replay/judge_redundancy CLIs closed 2026-10-20 (a0e94cba, flag ON 5d4ad2c0). EvalTower generation: closed here (opt-in). eval_batch_frontdoor: spec on, closed via the per-request opt-in. :8199: declined-as-read with reason above, covered by the per-request flag.
    - *(2026-10-24, batch-b.)* (c) PENDING, the single named item (blocker: the gitnexus analyze lock, an external event): re-index gitnexus for epyc-orchestrator now that the branch is on main, via `scripts/gitnexus-analyze.sh` (wrapper; exit 75 = another analyze holds the lock, retry). Ticked with (c) pending per main's ruling.
  - [x] **Q38-T10.1 — Serving gate and per-request spec-off control: paired spec-on vs spec-off on graded short-answer prompts (filed 2026-10-20; follows operator ruling Option 3).** Reuse the DF2-17 tooling (`artifacts/gpu-queue-20261020/df2-17/`: `df2_17_runner.py`, `df2_17_analyze.py`, `grade_stage2.py`, frozen-rules pattern in `PREDECLARED.md`, per-prompt PASS/FAIL, first-divergence index and near-tie classifier) on the champion HIP build in a scheduled MI210 window (standing approval; correctness vs timing rules per the brief). Corpus: at least 59 prompts from graded short-answer suites with a deterministic checker whose gold exists locally (exact-match or checker-based; candidate suites: gsm8k, mmlu_pro, ifeval, simpleqa, mbpp), chosen with a cap high enough that no baseline output is truncated (a truncated pair is excluded and replaced, counted and listed, never silently dropped); prompt digests recorded before any run; the 24-prompt Q38-T7 mix may supply some but those stage-2 prompts are not reused as the "held-out" claim. Arms, fresh process per server arm, residency proven: spec off twice (A/A), DFlash2 n-max 7 on, MTP on at the frontdoor shape, and the CONTROL: DFlash2 server with per-request `speculative.n_max: 0` (alone, and with a concurrent speculating slot). Predeclared: A/A must be 100% identical or the run is void. Report per prompt, never aggregate: PASS/FAIL per arm, first-divergence index, margin, near-tie class. **Regressions (baseline PASS, arm FAIL) and gains (baseline FAIL, arm PASS) are counted separately**, each with a Clopper-Pearson interval. Flip-rate bound: with n = 59 clean (untruncated, gradable) prompts and zero regressions, the regression rate is below 5% at 95% one-sided confidence (0.95^59 < 0.05); if k regressions occur the bound is the exact one-sided upper limit for k of 59, reported, and the gate is stated as passed only when it is below the operator-stated threshold (default 5%). Control verdict: the per-request `n_max: 0` stream must be token-identical to spec off on every prompt, alone and with a concurrent speculating slot. **Falsifier:** one or more spec-on regressions that fall below the gate (upper bound >= 5%) OR any token difference between per-request `n_max: 0` and server spec off falsifies, respectively, "distributional parity holds for serving roles at this n" and "the per-request flag delivers bitwise-required roles' contract without a stack change"; in the second case the fallback is a dedicated spec-off judge server by stack-change package. Done when per-prompt tables, raw outputs, digests and both verdicts are filed under DF2-17's evidence tree (`artifacts/gpu-queue-<date>/q38-t10-1/`) and the verdicts are noted here.
    - **2026-10-20 CODE LANDED, FLAG OFF; control arm written, NOT RUN (spec-off-judges; checkbox NOT ticked).** epyc-orchestrator `a0e94cba` (main): per-request llama-server key `"speculative.n_max"` (flat dotted key, `tools/server/server-schema.cpp:205`) via `src/spec_policy.py`; flag `spec_off_bitwise_roles` default OFF in test and prod (flag OFF = every payload byte-identical; tests prove it on all three backend lanes and 7 `call_orchestrator_forced` caller shapes). Opt-in callers when ON: eval_tower rubric judge and its repair turn, debug_scorer `llm_judge` (orchestrator `/chat` field `speculative_n_max` and direct `/v1/chat/completions` key), model_grader, coherence_judge, `judge_redundancy` and `routing_replay` CLIs. Never opt in: serving backends, eval generation call, the other 11 `call_orchestrator_forced` callers (AST test pins exactly 3 opt-in call sites). gitnexus: `call_orchestrator_forced` CRITICAL (23 callers, operator-approved; optional keyword at END of the signature, omitted when None), `ChatRequest` MEDIUM, rest LOW. Tests: 32 new + 663 existing (1 skipped) impacted-suite tests pass. **Control arm:** `scripts/benchmark/q38_t10_1_control_arm.py` (epyc-orchestrator; reuses the staged 20-prompt file, sha256 in the run). Needs the MI210 exclusively (gpu-quiet EXCLUSIVE, no CPU region, ~45-60 min); command: `scripts/region-lock run --gpu-quiet exclusive --role bench --tag q38-t10-1-control -- python3 -I scripts/benchmark/q38_t10_1_control_arm.py --out /mnt/raid0/llm/tmp/q38-t10-1-control-<UTCSTAMP>`. Do NOT flip the flag before it prints PASS; on FAIL the fallback is a dedicated spec-off judge server (stack-change package).
    - Same note, additions: (1) the fresh gitnexus re-index was deferred because `scripts/gitnexus-analyze.sh` needs a q0 write flock and q0 was held all window; the AST test `test_only_bitwise_callers_of_call_orchestrator_forced_opt_in` (pins exactly 3 opt-in call sites among 14) is the caller-list proof. (2) Both control scripts exist: epyc-orchestrator `scripts/benchmark/q38_t10_1_control_arm.py` (not run) and the staged `/mnt/raid0/llm/tmp/gpu-staged-20261020/q38t101_control.py` via `run_q38t101_control.sh`; the staged one is the run of record tonight (auto-launch on the MI210 after 06:30Z).
    - **2026-10-20 CONTROL ARM PASSED; flag flipped ON in prod (spec-off-judges; checkbox left UNTICKED, see "remains").** Run of record `/mnt/raid0/llm/tmp/gpu-staged-20261020/runs/q38t101-20261020T223154Z/` (MI210, 22:31-22:36Z, champion `4348de400`, 20 prompts); evidence copied to `artifacts/gpu-queue-20261020/q38-t10-1/` (records, summary, judge lines, config echo, both scripts, prompts). Token identity: A/A 20/20 identical; (i) per-request `speculative.n_max:0` vs spec-off server 20/20 identical; (iii) same beside a speculating background 20/20 identical (every prompt overlapped drafting background requests); (iv) default speculation drafted 1343 tokens and differed on 1/20. The staged judge printed VOID_GUARDS = a guard-semantics bug, not a failure: it required `draft_n == 0` but llama-server OMITS `timings.draft_n` when nothing was drafted (`tools/server/server-task.cpp:261`, `if (draft_n > 0) { base["draft_n"] = ... }`; upstream asserts it at `tools/server/tests/unit/test_speculative.py:104`, `"draft_n" not in res_disabled.body["timings"]`; both at `4348de400`). Fixed to treat a missing `draft_n` as 0 (original kept as `q38t101_control.py.bak-20261020-draftn`, diff in the evidence dir); the guard is not vacuous because arm (iv) reported 1343 drafted tokens. CPU-only re-judge of the existing run (`q38t101_rejudge.py`): **PASS** (guards_ok true, 20/20 overlapping drafting background, pids dead). **Flip:** epyc-orchestrator `5d4ad2c0` sets `spec_off_bitwise_roles` default_prod ON (test default stays OFF) and pins it `expected: on` in `orchestration/runtime_flags.spec.yaml`; it takes effect only at the NEXT orchestrator API reload by whichever session owns inference. No reload was done. Revert = `default_prod` False. **Remains for Q38-T10.1 (so the box stays open):** the serving-gate half: the >= 59-prompt graded short-answer corpus with a deterministic checker, arms spec off A/A, DFlash2 n-max 7, MTP at the frontdoor shape, per-prompt PASS/FAIL, regression and gain counts with Clopper-Pearson intervals, and the second verdict ("distributional parity holds for serving roles at this n"). The control half (first verdict: per-request flag delivers the bitwise contract without a stack change) is MET at n = 20.
    - [ ] **Q38-T10.1r - reload the orchestrator API so `spec_off_bitwise_roles` (default_prod ON, orchestrator `5d4ad2c0`) is live.** Executed by the session that owns inference, at its boundary, via `orchestrator_stack.py reload orchestrator` only (no full-stack reload, autopilot stays up). Done when a judge/grader request payload carries `"speculative.n_max": 0` and its timings omit `draft_n`. (filed 2026-10-20)
    - **2026-10-20 SERVING-GATE HALF STAGED, NOT RUN (q38t101-gate-prep; checkbox stays UNTICKED).** Prep only: no server, test or claim was run. **Corpus:** 80 prompts, all from the local pool `epyc-inference-research/benchmarks/prompts/question_pool.jsonl` (gold in-row): 24 gsm8k (numeric, shortest problems), 18 mmlu + 10 mmlu_pro (letter-only multiple choice), 14 cruxeval output-prediction (exact), 4 simpleqa (token-F1 >= 0.8), 10 ifeval single-instruction (lowercase / capital / end phrase / quotation / no-comma / forbidden words / JSON; checkers live in the runner). Zero overlap with `q38t101_prompts.json` or the DF2-17 stage-2 prompts (checked by prompt prefix). Frozen: `artifacts/gpu-queue-20261020/q38-t10-1/serving-gate/corpus.jsonl`, sha256 `224e7d9297bd927a9bb2525c8f9c0f49b84e71ee9f7926f923a40742a98852a1` (`corpus.sha256`; rebuild is deterministic via `build_corpus.py`, seed 20261020; the runner refuses a mismatching file). Target 80 so that truncation exclusions (cap n_predict 512; `stop_type == limit` in any arm of a pair; counted and listed, never dropped silently) still leave >= 59; fewer than 59 clean gives INSUFFICIENT_N, not a pass. **Runner:** `serving_gate.py` (staged `/mnt/raid0/llm/tmp/q38t101-serving-gate/`, copy at epyc-orchestrator `scripts/benchmark/serving_gate.py`), extending `q38t101_control.py`. Two phases, fresh server per arm, own ports 18891 (GPU) / 18892 (CPU): GPU = Qwen3.8-27B Q8 spec off twice (A/A) then DFlash2 n-max 7 on the :8083 argv, champion HIP build `4348de400`; CPU = Qwen3.6-35B-A3B-MTP Q8 spec off twice (A/A) then draft-mtp n-max 4 at the registry frontdoor shape (NUMA_HALF_A, `-np 1`, q8_0 KV, terse template, production v10 CPU store). Each spec arm is judged against its OWN model's spec-off pass A (the two roles run different models). Per prompt: PASS/FAIL for both arms, truncation, first-divergence index, token identity; regressions and gains counted separately, each with Clopper-Pearson (two-sided 95% and one-sided 95% upper; regression rate = k / n_clean, so k=0 needs n_clean >= 59, and k=1 fails at n=59 (7.79%) and at n=80 (5.79%)). Per-role verdict is PASS only if A/A is 100% token-identical, the guards hold (spec arm drafted > 0, spec-off arms drafted 0, libggml mapped from the tree's own dir, HIP resident for GPU / zero KFD for CPU, PIDs dead) and the upper bound is below 5%; the second verdict (distributional parity for serving roles at this n) is PASS only when both roles pass. **Not included:** the near-tie margin classifier (needs logprobs; DF2-17's `df2_17_analyze.py` can be run over the saved tokens afterwards); the concurrent-slot control is already PASSED above. The frontdoor CPU argv is reconstructed from the registry (no launch record exists while production is down); the production frontdoor's OMP/THP env is not replicated, which is symmetric across its A/A and MTP arms. **Claims the runner takes itself:** GPU phase = device flock + `region-lock run --gpu-quiet exclusive --role bench`; CPU phase = `region-lock run --gpu-quiet shared --cpu-list 0-47,96-143 --role bench` (exit 75 on claim timeout is recorded CLAIM_UNAVAILABLE). **Staged command:** `python3 -I /mnt/raid0/llm/tmp/q38t101-serving-gate/serving_gate.py --deadline <UTC window end, e.g. 2026-10-21T06:25:00Z>` (`--dry-run` validates paths/argv/corpus/ports and starts nothing; `--phases gpu` or `cpu` runs one half; `--judge-only RUN_DIR` re-grades saved records). Output goes to `runs/sg-<ts>/` (records, server logs and commands, `summary.json`, `per_prompt.tsv`, `judge_line.json`) plus `RESULT.serving_gate.json`. It stops 5 min before the deadline and skips a phase with under 30 min (GPU) / 60 min (CPU) left. **Runtime estimate (an estimate, not a measurement):** from the control run (730 tokens in 29 s on the 27B, ~25 tok/s, ~1 min loads) and ~110 mean generated tokens per prompt: GPU phase ~20 min (3 passes + 2 loads); CPU phase ~45 min (35B-A3B at the 12-40 tok/s frontdoor range, 3 passes of ~10-15 min, plus two cold --no-mmap loads); total ~65 min, so request a window of >= 90 min. Checks done on the staged file: `--dry-run` (paths, argv, corpus hash, ports free) and a pure-python `--selfcheck` of the graders and the k=0, n=59 bound (0.04951). Remains: the run itself, then filing the results under `artifacts/gpu-queue-<date>/q38-t10-1/` and noting both verdicts here.
    - **2026-10-21 DECISION RULE PREDECLARED (operator, 2026-10-21T09:08:36Z, before any serving-gate result existed; the gate has not reported).** Rule "Net, paired" for the second verdict (distributional parity for serving roles): over the 80-prompt corpus (sha `224e7d92...`), R = prompts that pass spec-off and fail spec-on, G = prompts that fail spec-off and pass spec-on; **FAIL** iff a one-sided exact McNemar/sign test of R vs G gives p < 0.05 (H1: regressions exceed gains), otherwise PASS. The strict reading ("any regression fails") and the Clopper-Pearson bounds in the task text are reported for information only and decide nothing; this operator rule replaces the 5% upper-bound gate in the Falsifier above for the second verdict. The control verdict (token identity of per-request `n_max: 0`) is unchanged. Verbatim record, sha256 `350a2a2031495f2a0e6334c507b4bbcbcc8cc4e64a995187761d2db92979ffb3`: `artifacts/gpu-queue-20261020/q38-t10-1/serving-gate/PREDECLARED_RULE.md`. The runner `serving_gate.py` must report R, G and the exact p alongside its per-prompt tables.
    - **2026-10-21 SERVING-GATE GPU PHASE RAN: PASS under the predeclared Net-paired rule (checkbox stays UNTICKED: the CPU phase is owed, slotted 14:30Z on q0+q1 under `--role build`; runner session for coordinator 3c4ca599).** Run `sg-20261021T092041Z`, 09:20:41Z-09:33:14Z, evidence `artifacts/gpu-queue-20261020/q38-t10-1/serving-gate/gpu-run-20261021T092041Z/` (records, summary.json, per_prompt.tsv, config echo, claim cmd, server commands, driver log). Rule `PREDECLARED_RULE.md` sha256 `350a2a2031495f2a0e6334c507b4bbcbcc8cc4e64a995187761d2db92979ffb3`, file mtime 09:08:36Z; the gate had produced nothing before 09:20Z (no runs dir, no RESULT file at 09:14Z; only `--dry-run`, which starts nothing). Role `architect_critic` Qwen3.8-27B Q8, champion HIP build `4348de400` (`gpu-20261006-4348de400`), spec off twice (A/A) then DFlash2 n-max 7, argv from production `8083.json` with own port 18891, host threads `taskset -c 184-191`, `numactl --membind=3`. **Corpus 80 prompts, sha `224e7d92...`; 78 clean, 2 excluded** (`sg_gsm8k_gsm8k_00368` and `sg_ifeval_ifeval_3223`: `stop_type == limit` at n_predict 512 in all three arms, so truncated by the cap, not by time). **A/A 80/80 token-identical. R = 0, G = 0, discordant pairs 0 (both pass 64, both fail 14), one-sided exact sign/McNemar p = 1.0 (two-sided 1.0), rule verdict PASS.** Informational only (decides nothing): strict reading PASS (0 regressions), Clopper-Pearson one-sided 95% upper bound on the regression rate 3.77% (n=78; 4.57% given baseline-pass n=64), gains 0/14, net-rate 95% CI (Newcombe, paired) [-3.0%, +3.0%], token-identical clean prompts 69/78 (the other 9 diverge later and grade identically). Guards: spec arm live (8,783 drafted tokens), off arms drafted 0, HIP-resident (VRAM peak 41.5 GiB off, 48.6 GiB spec; KFD and gpu_busy samples non-zero), all server PIDs dead. **Overlap check:** workspace-f8's cold CPU build on q3 (72-95 and 168-191, which contains the gate's 184-191 host threads) ran 09:29:14Z-~09:30:20Z, i.e. over the last ~10 prompts of the `gpu_off_B` arm (it ended 09:30:07Z) and the start of the spec-server load. No prompt timed out or errored (phase status COMPLETE, max per-prompt wall 36 s in A, 18 s in B, 9.4 s spec), the only truncations are the same two in every arm, and A/A is 80/80 identical, so the off_B arm is intact: overlap checked, no effect on outputs, nothing re-run. **Launcher changes (original kept as `serving_gate.py.orig-20261021`):** (1) the GPU phase claim is `gpu-quiet exclusive --role build` with NO region (a q3 build claim could not be had: `champ-consolidation-c2-job` held q3; the c2 job pins 72-87,168-183 and the gate 184-191, so the cores are disjoint; the coordinator accepted this); my first attempt waited on q3 while holding gpu-quiet and was killed, verified dead, and its empty run dir removed; (2) the CPU-phase claim role is `build` instead of `bench` (coordinator ruling: correctness, not timing). Same-day item e (the champion A/B) was launched under a `--cpu-list 0-95` claim by mistake (the narrow-claim directive arrived after launch); it does not affect that result. The Q38-T10.1a code below was done in the same edit.
    - **2026-10-21 CPU phase finished 14:10Z (`SGCPU_DONE`).** Combined verdict PASS under Net-paired (R=0, G=0 both phases, 160 pairs), REVIEWED by main. Box stays UNTICKED until an agent resolves the aggregate parity field (INCOMPLETE_OR_VOID) and the 2 GPU exclusions, then ticks.
    - **2026-10-21 Q38-T10.1a code done (box left to the task owner).** `serving_gate.py` now emits per role `net_paired` {R, G, discordant, both_pass, both_fail, p_one_sided_exact_R_gt_G, p_two_sided_exact, rule_sha256, rule_verdict, strict_reading_informational} and makes `verdict` the rule verdict, keeping the 5% upper-bound reading as `verdict_strict_upper_bound_informational` (additive; `--selfcheck` still passes; re-judged the real GPU run with `--judge-only` on a copy). Falsifier met: an independent recount from the per-prompt records (`mcnemar_net_recount.py`, which also gives the Newcombe paired CI and a seeded bootstrap) reproduces R = 0, G = 0, p = 1.0. The orchestrator-repo copy `scripts/benchmark/serving_gate.py` is NOT updated (the staged and artifact copies carry the change).
    - **2026-10-21 SERVING GATE PASSED (both phases, predeclared Net-paired rule; box ticked, sg-verdict).** GPU run `/mnt/raid0/llm/tmp/q38t101-serving-gate/runs/sg-20261021T092041Z`: R=0, G=0, A/A 80/80, 2 truncated prompts excluded (n_clean 78). CPU run `.../runs/sg-20261021T130412Z`: R=0, G=0, A/A 80/80, n_clean 80. Rule sha256 `350a2a2031495f2a0e6334c507b4bbcbcc8cc4e64a995187761d2db92979ffb3` (re-hashed, matches); corpus sha `224e7d92...` in both. **Parity-field resolution:** the tool's top-level `second_verdict_distributional_parity` / `parity: INCOMPLETE_OR_VOID` is an artifact of the two phases living in separate run dirs (`serving_gate.py judge()` requires every phase in ONE `--out` dir to be PASS; the other phase's records are absent so it returns INCOMPLETE; line ~423), not a voiding condition (guards, A/A and n all PASS in each dir). Token non-identity is not a voiding condition (informational only: 69/78 GPU, 70/80 CPU). **Exclusions:** `sg_gsm8k_gsm8k_00368` and `sg_ifeval_ifeval_3223` hit the 512-token cap in all three GPU arms and FAIL in both base and spec, so they are both-fail pairs; counting them over the full 80 gives the same R=0, G=0. Combined judgment (derived, no inputs modified): `/mnt/raid0/llm/tmp/q38t101-serving-gate/RESULT.combined_by_rule.20261021.json`. Note the orchestrator-repo copy of `serving_gate.py` still lacks the Q38-T10.1a edits.
    - **2026-10-21 CPU phase queued (runner for coordinator 3c4ca599).** Chain `/mnt/raid0/llm/tmp/runner-20261021/chain_sg_cpu.sh` runs `serving_gate.py --deadline 2026-10-21T16:00:00Z --phases cpu` with `SG_CLAIM_TIMEOUT_S=7200`: claim `region-lock run --cpu-list 0-47,96-143 --role build` (q0+q1) with NO gpu-quiet claim (a queued `--gpu-quiet shared` blocked f8's exclusive GPU timing; killed, verified dead, requeued; pre-change copy `serving_gate.py.pre-nogpuquiet`). It queues behind 5c's q0+q1 calibration; if it cannot start by ~15:10Z the phase cannot finish by 16:00Z. The gate stays UNTICKED until the CPU phase runs.
    - [x] **Q38-T10.1a — make `serving_gate.py` emit the predeclared verdict inputs (filed 2026-10-21).** Add R, G, the discordant-pair table and the one-sided exact McNemar p to its summary output, with the strict reading and Clopper-Pearson bounds as informational lines, before the gate runs; smoke the exact argv read-only against the existing control-arm records first. Falsifier: the summary cannot reproduce R, G and p from the per-prompt records by an independent recount. ✅ 2026-10-29 (audit: dated sub-bullet in same handoff: "2026-10-21 Q38-T10.1a code done" serving_gate.py emits net_paired R,G,McNemar p; falsifier met by independent recount (R=0,G=0,p=1.0); caveat: orchestrator-repo copy not updated) [no-belief: audit-reconciliation]

## Key questions this handoff must answer

1. ~~**MTP sidecar vs embedded**~~ — ANSWERED 2026-08-14: the unsloth base EMBEDS the nextn/MTP head
   (`blk.64.nextn.*` present in the GGUF header), so it is a like-for-like replacement for
   `Qwen3.6-27B-MTP-Q8_0` with **same-file self-draft** — no wiring change. The ggml-org sidecar is a
   full layer-64 draft model for the ggml-org (MTP-stripped) base and is redundant here.
2. **Multimodal**: is the vision projector a reason to *also* stage Qwen3.8 for `worker_vision`/
   `vision_escalation`, or strictly out of scope for this coder/architect swap?
3. ~~**Is this even worth it**~~ — RESOLVED by operator (2026-08-14): quality uplift is a given, so the
   swap is worth it on quality grounds alone. Throughput won't move materially (dense, BW-bound); the
   throughput step exists to record the serving baseline, not to gate the decision.

## Research Intake — 2026-08-21 (chat-template dive, intake-1212…1217)

> **Ratification package v2 (2026-08-21):** `scripts/operator/ratify_qwen38_registry_swap_20260821.sh`
> — phase 0 reverts v1's mistaken edits to the GENERATED lean file (inverse-edit byte-proof), phase 1
> adds the provenance block to the TRUE master, phase 2 runs `stack_change_pipeline.py update
> --allow-descriptor-model-removal` with a targeted only-removal assertion + derived verification +
> post-check green, phase 3 is the `--jinja` fallback fix. Never commits in the research repo (the
> LFM2.5 orphan decision is pending in the same file). `--dry-run` validated end-to-end.

**CORRECTION 2026-08-21 (same day, second pass — recording the error so it cannot be re-derived).**
The Q38-T2 finding "the master registry was never swapped" was WRONG-LEVEL. Three facts replaced it:
1. `orchestration/model_registry.yaml` in the **orchestrator** repo is **auto-generated** — its own
   head banner reads "AUTO-GENERATED — MASTER-COMPILED RUNTIME VIEW", compiled at every stack start
   from the research repo's master by `src/registry/registry_compiler.py` (`compile_lean`). Every
   audit read the file from the middle and missed the banner; the pipeline's `lean_registry: stale`
   error is what surfaced it.
2. **The true master WAS swapped on 2026-08-20 by `b376dadd`** — a local, unpushed commit in
   epyc-inference-research (one of the 9 in that repo's reconciliation backlog). The earlier
   `git cat-file -t b376dadd` "resolves in no repo" check was defeated in the research repo by its
   `safe.directory` git-config problem. The swap there is complete: `model_role`, both literal path
   sets, `draft_max: 8` in both maps.
3. **The real gap is the compile chain**: lean, descriptors and derived `stack_priors.yaml` were all
   compiled 2026-08-11, and the launcher reads the derived file AS-IS (`orchestrator_stack.py:252-262`
   — no priors recompile at start; only the lean auto-recompiles). So the operational conclusion of
   Q38-T2 stands — a stack start today serves Qwen3.6@4 — while its provenance claim is corrected.
The v1 ratification script edited the generated lean view and its phase-2 `check`-as-gate aborted on
the expected staleness report; v2 supersedes it as above. Method lesson, same shape as the retention
correction earlier today: a compiled artifact was audited as if it were its source; the file's own
banner said so; nobody read line 1.

Three findings landed here by a chat-template intake round, all verified by rendering the template
**embedded in our own** `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf` (extracted by a GGUF header
read, without loading the 29 GB model) alongside the stock `Qwen/Qwen3.8-27B` template.

- [x] **Q38-T1** ✅ 2026-08-21 — **Both defects are UNREACHABLE under current config**: `reasoning_effort` has 0 occurrences in `src/` and 0 in `orchestration/` (no code path sends it), and the llama-server payload is a hardcoded single `user` turn (`src/backends/llama_server.py:560`, `:1316`) so the template's assistant branch that produces the blank `<think>` is never entered. Recorded + reachability established. Two real defects on the template we now serve. (a) With inline-`<think>` history,
      stock **and** our Unsloth variant emit a blank `<think></think>` immediately before every real
      thought — five `<think>` occurrences where three are warranted. (b) `reasoning_effort` handling
      **diverges from upstream**: stock *raises* on `high`, our Unsloth variant silently *coerces*
      `high → xhigh`. An OpenAI-style client sending the ordinary value `high` therefore gets a hard
      500 against stock and silent maximum-effort reasoning here — opposite failure modes, neither
      what the caller asked for.
- [x] **Q38-T2** ✅ 2026-08-21 — Status line fixed in place: the real commit is `1cff5162` in `repos/epyc-orchestrator/stack_templates/default.yaml` (`b376dadd` resolves in none of the three repos); master registry has **0** `Qwen3.8` occurrences; and **the stack template is NOT what the launcher reads** — `-m` comes from `orchestration/derived/stack_priors.yaml` (`orchestrator_stack.py:134`, `:252-262`, `:1062-1071`), which still names Qwen3.6. Registry provenance: re-resolve the swap commit. This handoff's status line cites
      `b376dadd`, which resolves in **none** of epyc-root, epyc-orchestrator or
      epyc-inference-research. The Qwen3.8 swap that *does* resolve is `1cff5162` in
      `repos/epyc-orchestrator/stack_templates/default.yaml`, and
      `orchestration/model_registry.yaml` still contains **zero** occurrences of the fixed string
      `Qwen3.8` — `architect_general` and `coder_escalation` there still name Qwen3.6-27B.
- [x] **Q38-T3** ✅ 2026-08-21 — Non-stock Unsloth template recorded below with digests (ours 9,993 B `sha256:12827f24b742…` vs stock 8,952 B `sha256:c3cf9e34abf4…`); the registry-descriptor edit is **PREPARED, NOT APPLIED** (registry is operator-frozen — snippet + insertion point handed to the dispatching session). Record that we serve a **non-stock (Unsloth) template** (9,993 B, ending
      `{#- Unsloth fixes - developer role, merged system messages, tool calling #}`) rather than the
      stock 8,952 B one, and that no registry descriptor says so.

**Not a task, recorded so it is not rediscovered:** our stack-wide
`chat_template_kwargs.enable_thinking: false` is **role-keyed**, so it survives the model swap. It
also makes us immune both to the template's `xhigh` default and to the `reasoning_effort` raise,
because the raise sits *inside* the `enable_thinking` gate and is unreachable when thinking is off.

### Q38-T1 findings — reachability of the two template defects (2026-08-21)

Both defects are real **in the template**. Neither is reachable **through our stack**. Evidence below is
read-only inspection of `repos/epyc-orchestrator` plus the template extracted from our own GGUF
(`qwen38_official.jinja`, byte-identical to `Qwen3.8-27B-Q8_0.gguf.jinja`, `cmp` → identical).

**(a) `reasoning_effort` divergence — UNREACHABLE: nothing sends the field.**

- `grep -rn "reasoning_effort" src/` → **0 hits**. `grep -rn "reasoning_effort" orchestration/` → **0 hits**.
  Every occurrence in the orchestrator lives in `scripts/` and none of them reaches llama-server:
  - `scripts/validate/reasoning_effort_certifications.py:44` validates a registry `reasoning_effort.level`
    key — which no role declares (the 0-hit grep above), so the check is vacuous today.
  - `scripts/analysis/reviewer_policy_arm_ab.py:184` *parses* the knob, but `_DECODE_KNOBS` (`:197`) is
    `("temperature", "top_p", "top_k", "min_p")` and `:217` emits only those. The parsed value is never
    read back anywhere in the file — a dead knob, not a payload field.
  - `scripts/autopilot/planner_providers.py:303` passes `--config model_reasoning_effort="…"` to the
    **codex CLI** (`cmd = [self._binary, "exec", "--json", …]`, `:292-300`), not to llama-server.
- The two llama-server payload builders construct the dict literally and never add the key:
  `src/backends/llama_server.py:559-563` (non-streaming) and `:1315-1319` (streaming).
- **Second, independent guard.** In our template the *entire* `reasoning_effort` block is inside the
  thinking gate: `qwen38_official.jinja:58` opens `{%- if enable_thinking is undefined or enable_thinking
  is true %}`, and the `xhigh` default (`:59`), the silent `high → xhigh` coercion (`:60-61`) and the
  `raise_exception` (`:63-64`) all sit within it. The handoff's standing note claimed this gating only for
  the *raise*; verified here, **all three effects — default, coercion and raise — share the same guard**,
  so with `enable_thinking: false` none can fire even if a caller did send the field.

**(b) Blank-`<think>` duplication — UNREACHABLE: no assistant turn ever reaches the template.**

- *Template precondition*, verified at `qwen38_official.jinja:113-120`: the assistant branch reads **only**
  `message.reasoning_content` (`:115-116`) and never parses inline `<think>` out of `content`. When a
  caller puts the thought inline, `reasoning_content` trims to `''`, so `:120` emits
  `'…\n<think>\n' + '' + '\n</think>\n\n' + content` — a blank think block immediately before the real one.
  **It requires a structured `messages` array carrying a `role: "assistant"` entry.**
- *Our payload has no such entry.* `src/backends/llama_server.py:560` and `:1316` both hardcode
  `"messages": [{"role": "user", "content": user_content}]` — one user turn, always; no assistant entry,
  no `reasoning_content` key, and `request.extra["messages"]` is not consulted on this backend.
- *Inbound multi-turn requests are flattened before they get there.*
  `src/api/routes/openai_compat.py:468` takes `request.messages[:-1]` as history; `_context_parts_from_history`
  (`:248-265`) renders each turn as the plain string `f"{role_label}: {content}"`; `:494` joins them into a
  single `context` blob. An assistant `<think>` therefore arrives as **literal text inside the one user
  turn** — the template's assistant branch is never entered. (Side note, not the defect under audit: raw
  `<think>` markup can thus be echoed back into a prompt as user text.)
- *The one place that does build assistant history targets a different model.*
  `src/api/routes/chat_vision.py:584` (`messages.append({"role": "assistant", …})`) posts to
  `_vl_url_for_port(vl_port)` (`:547-548`) — the vision role's port serving `Qwen3-VL-30B-A3B-Instruct`,
  not `:8083`.
- *The one backend that would honour caller history is dead.* `src/backends/openai.py:240-241` does read
  `request.extra["messages"]`, but `OpenAIBackend` is never instantiated in `src/` (only its own docstring
  example `:7-10` and the `src/backends/__init__.py:29` re-export), and local roles are constructed as
  `LlamaServerBackend` (`src/llm_primitives/backend.py:143`, `:247`, `:334`, `:345`, `:397`).

**(c) `enable_thinking: false` confirmed for both Qwen3.8-serving roles.**

- `orchestration/model_registry.yaml:1396-1397` (`coder_escalation`, block opens `:1391`) and `:1499-1500`
  (`architect_general`, block opens `:1487`) — both under the top-level `server_mode:` section (`:1351`),
  which is exactly the section `RegistryLoader.get_role_chat_template_kwargs` reads
  (`src/registry/registry_loader.py:513-517`; it explicitly does **not** read the `roles:` section).
- Executed against the orchestrator venv: `chat_template_kwargs_for_role('architect_general')` →
  `{'enable_thinking': False}`; `'coder_escalation'` → `{'enable_thinking': False}` (also `frontdoor`,
  `architect_critic`; `worker_general` → `None`).
- Two further belts on the launch side, from the derived layer:
  `orchestration/derived/stack_priors.yaml:363` sets `flags.reasoning: 'off'`, emitted as `--reasoning off`
  (`scripts/server/orchestrator_stack.py:1431-1433`); and `:357` sets `flags.jinja: true`, emitted as
  `--jinja` (`orchestrator_stack.py:1402`), which is what keeps requests on the `/v1/chat/completions` +
  jinja path where `chat_template_kwargs` is actually applied.

> **Verdict.** Both defects are **unreachable under current config**, and each is blocked twice over
> (no sender / no assistant turn, *plus* the `enable_thinking` gate). They become reachable only if
> someone (i) starts sending `reasoning_effort`, or (ii) replaces the hardcoded single-user-turn payload
> with real `messages` history — **and** turns thinking back on for these roles. Treat those two as the
> tripwires, not the template.

### Q38-T2 findings — commit provenance and which artifact actually wins at start time (2026-08-21)

**Provenance.**

| Claim | Verification | Result |
|---|---|---|
| `b376dadd` (cited in the old status line) | `git cat-file -t` in epyc-orchestrator, epyc-root, epyc-inference-research | `fatal: Not a valid object name` in all three |
| `1cff5162` | `git log -1`, `git show --stat` | `1cff5162c7e6f6d103beb8cb12747b4e0da30bf6`, 2026-08-20 21:52:11 +0000, *"stack template: architect_general -> Qwen3.8-27B; draft_max 24 -> 8 (measured)"*, **1 file changed** — `stack_templates/default.yaml` (+7/-2) |
| Master registry swapped? | `grep -F -c 'Qwen3.8' orchestration/model_registry.yaml` | **0** |
| Ever swapped? | `git log -S 'Qwen3.8' -- orchestration/model_registry.yaml` | **empty** — no commit in history ever added that string |
| Uncommitted swap sitting in the tree? | `git status --short -- orchestration/model_registry.yaml` | no output (clean) |
| `qwen38_27b_q8_local` role exists? | `grep -n 'qwen38_27b' orchestration/model_registry.yaml`; `grep -ril 'qwen3\.8\|qwen38' orchestration/ --include='*.yaml'` | **no match anywhere** — `architect_general:1501` and `coder_escalation:1398` still read `model_role: qwen36_27b_mtp_q8_local` (defined `:2468`) |

**Which source wins at start time: the MASTER REGISTRY, via the derived layer — not the stack template.**

The launch chain is `orchestration/model_registry.yaml` → (`scripts/registry/stack_change_pipeline.py`
regenerate) → `orchestration/derived/stack_priors.yaml` → launcher:

- `src/registry/stack_priors.py:30` — `DEFAULT_REGISTRY = REPO_ROOT / "orchestration" / "model_registry.yaml"`
  (input); `:32` — `DEFAULT_OUTPUT = REPO_ROOT / "orchestration" / "derived" / "stack_priors.yaml"` (output).
- `scripts/server/orchestrator_stack.py:134` — `STACK_PRIORS_PATH = … / "orchestration/derived/stack_priors.yaml"`;
  `:252-262` `_stack_prior_launch()` reads that file and returns `launch.requirements`; `:1062-1071` (and the
  sibling builders at `:727`, `:783`, `:908`, `:922`) take `-m` from `_runtime_string(requirements, "model_path", …)`.
- **`stack_templates/default.yaml` supplies no path.** `src/config/stack_templates.py:135-217` `load_template`
  parses `model:` only as a *name string* into `RoleConfig.model`; the file's own serving facts are resolved
  through `src.registry.stack_priors` (`:26-31`). And `_validate_stack_prior_parity` (`:303`, running to `validate_template` at `:385`) compares
  **ports only** — it never compares models, so the Qwen3.8-vs-Qwen3.6 divergence passes validation silently.
  `validate_template`'s model-existence check (`:485-500`) emits a **warning**, not an error.

**Consequence, stated plainly:** `orchestration/derived/stack_priors.yaml:332-333` still reads
`model_path: /mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf` and the same for `draft_model_path`
(`grep -F -c 'Qwen3.8'` on that file → **0**; `'Qwen3.6'` → **25**), with `spec.draft_max: 4` (`:370`), and
the file's mtime is **2026-08-11 01:36** — predating both 2026-08-20 edits. **A stack start today would
launch Qwen3.6-27B-MTP-Q8_0 with draft depth 4**, i.e. neither the model nor the `draft_max: 8` the stack
template declares. The `stack_change_pipeline.py` regenerate is therefore not a formality on the remaining
checklist — it is the step that makes the swap real, and it cannot help until the **master registry** is
swapped first, because it compiles *from* that file.

### Q38-T3 findings — the served GGUF embeds a non-stock (Unsloth) template (2026-08-21)

| Template | Bytes | `sha256[:12]` | Note |
|---|---|---|---|
| `Qwen3.8-27B-Q8_0.gguf` (ours, served) | 9,993 | `12827f24b742` | Ends `{#- Unsloth fixes - developer role, merged system messages, tool calling #}` |
| Stock `Qwen/Qwen3.8-27B` | 8,952 | `c3cf9e34abf4` | No trailing marker |
| `Qwen3.6-27B-MTP-Q8_0.gguf` | 8,057 | `55d4931433fe` | byte-identical to the 35B-A3B below |
| `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` | 8,057 | `55d4931433fe` | — |
| `Qwen3.5-122B-A10B-UD-Q4_K_M-00001-of-00003.gguf` | 7,992 | `8452ca85cb1e` | — |

- Our embedded template is **1,041 bytes larger** than stock and carries an explicit Unsloth provenance
  marker as its final line. `cmp` confirms the separately extracted `qwen38_official.jinja` and
  `Qwen3.8-27B-Q8_0.gguf.jinja` are byte-identical, so the two names denote one artifact.
- **No registry descriptor records this.** `grep -c -F 'Qwen3.8' orchestration/model_descriptors.yaml` → `0`;
  `grep -n 'chat_template' orchestration/model_descriptors.yaml` → only two `enable_thinking` references
  (`:341`, `:676`), neither a template-provenance record. Nothing anywhere in `orchestration/` states that a
  served GGUF's chat template diverges from its upstream.
- **Scope discipline:** the Qwen3.6 / Qwen3.5 rows above are recorded as digests only. Whether *those*
  diverge from their own upstreams is **UNVERIFIED** — no stock counterpart was extracted for them this round.
- **Registry-descriptor edit: PREPARED, NOT APPLIED.** The registry is operator-frozen and a subagent may
  prepare but not apply an index/registry row, so the exact snippet and insertion point were handed to the
  dispatching session rather than written. It must land in the **master** `orchestration/model_registry.yaml`
  (under the top-level `roles:` map, `:1599`), never in `orchestration/model_descriptors.yaml` — that file is
  a compiled artifact (`descriptor_version: 3`, `status: compiled`, `compiled_at: '2026-08-11T01:36:32Z'`,
  `source_registries.lean.path → orchestration/model_registry.yaml`) and a recompile would overwrite any
  hand-edit. The snippet models itself on the existing `thinking_control:` precedent at
  `model_registry.yaml:1580-1585`.

## Research Intake Update — 2026-08-21 (Stage-2b, intake-1276)

- [x] **(Z) fla #1156 exposure for our Qwen3.x GDN family — RECORDED AND CLOSED, 2026-08-22.**
      **The row as first written (2026-08-21) asserted facts the reporter has since retracted.** fla
      issue #1156 is **CLOSED** (`completed`, by maintainer `zhiyuan1i`, 2026-08-22T09:55:42Z) after
      the reporter self-retracted: the `ShortConvolution` backward defect is **fla 0.4.2 ONLY and is
      fixed in 0.5.2**. His original "reproduces on 0.5.2 too" was an import-resolution artifact — the
      "0.5.2" run was still importing 0.4.2 from site-packages; a contamination-proof re-test measures
      5.5e-08 against 0.4.2's 2.0e-01. "Both backends" was never possible either: `causal_conv1d` was
      absent, so `ShortConvolution.__init__` silently reset `backend='cuda'` to `'triton'`. The
      differing numbers were **run-to-run non-determinism**, not a second implementation.
      **Our exposure is nil, three times over.** Forward is clean at every shape tested including the
      faulting one, so inference is untouched; we do not run fla at all (torch, triton and fla are all
      absent from this host, and our Qwen3.x GDN serving path is native C++/HIP in the frozen tree);
      and the bug is fixed upstream. Hardware in the report is **MI355X / gfx950 / ROCm 7.2** — gfx90a
      and MI210 appear **nowhere** in the fla tracker.
      **The one thing that survives is a version constraint, and it points the opposite way to what
      you would expect** — see the rewritten G6 in `rocm-verify-profile-backend.md`: fla 0.4.2 is the
      broken release and declares **no** torch/triton floor, so a resolver asked for an fla compatible
      with an older torch selects it. **Never install fla < 0.5.2 on this host.**
