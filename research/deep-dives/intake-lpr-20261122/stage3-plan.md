# Stage-3 plan — llama.cpp PR batch + Inkling 2 Mini (intake-lpr-20261122) — AWAITING OPERATOR APPROVAL

Entries intake-2792..intake-2823 (32: 9 submitted, 23 Stage-2b across 4 waves), all dive-verified. Subagents: 2 opus/medium (GPU FA dives, CDNA/QSA sparse wave), 12 sonnet (dives and composers). No compute was used; every [inference] box below is a separately booked row, not run by intake. Nothing here is filed until approval.

## Work packets

| Packet | Action | Owner | Boxes |
|---|---|---|---|
| P1 | Port #29638/ed1254a EOG stop and #32771 trim with tests | handoffs/active/speculative-decoding.md | SPEC-STALE-1 |
| P2 | Read existing probes/smaps/launchers, then decide the #30137 port | handoffs/active/harness-program.md | PFXC-SAVE-1 |
| P3 | Band measurement row and union-fraction gate | handoffs/active/autokernel-loop.md | H12-BAND-1, H12-UNION-0 |
| P4 | Fold guard test + slot move; conflict census and recipe | handoffs/active/kernel-champion-and-promotion.md | FOLD-GUARD-H12, FOLD-CENSUS-1 |
| P5 | Extend ISA families + guidance; GDN op baseline + tests | handoffs/active/autokernel-loop.md | AK-ISA-FAMILIES, GDN-VERIFY-BASE |
| P6 | Addendum + port-cost estimate (code reading) | handoffs/active/model-evaluation-queue.md | INK2-MINI-1 |
| P7 | One-matrix Q8_0 microbench row | handoffs/active/cpu-decode-roofline-program.md | Q8-2STREAM-1 |

Safe concurrency: P1, P2, P4, P5 (ISA part) and P6 are independent code/doc work. P3, P5 (GDN) and P7 are GPU/CPU rows needing bookings; H12-UNION-0 follows H12-BAND-1 only by sharing the H12 shapes, not by dependency.

Minimum-rigor: measurement boxes (H12-BAND-1, H12-UNION-0, GDN-VERIFY-BASE, Q8-2STREAM-1) each name question, expected effect vs noise, A/A floor or bit-identity, fixed shapes, stop-on-answer and stop-on-futility, futility-only gate class. Code boxes (SPEC-STALE-1, FOLD-GUARD-H12, AK-ISA-FAMILIES) replace the six controls with red/green tests and a synthetic-regression check. PFXC-SAVE-1 and FOLD-CENSUS-1 read existing evidence only.

## Monitors and knowledge-only (durable prose, no checkbox)

| Packet | Trigger / basis |
|---|---|
| M1 | Batched copy API / CUDA gather (#30881/#31391): reopen with the existing cache-idle-slots reopen trigger (harness-program.md:3842) or if PFXC-SAVE-1 shows restore transfer count dominating with idle saves off. |
| M2 | GDN column-width knob: reopen only if the GDN-VERIFY-BASE fused variant KEEPs. |
| M3 | Inkling 2 DSpark drafter alpha vs MTP: reopen when an Inkling-capable build exists and a GGUF drafter is published. |
| M4 | Full-block padding of the DFlash2/DSpark draft block: add a pad arm when the next DFlash2 X-sweep row is booked. |
| M5 | ZMM IQ3_S 2-8 rows / ZMM IQ2_S: reopen if a served IQ2_S/IQ3_S-heavy model profile shows the dot as bottleneck. |
| M6 | LDS-staged iq3s_grid on HIP: reopen if a profile shows constant-cache serialisation in IQ3_S mmvq. |
| M7 | CDNA sparse-FA break-even prior: reopen when a DSA/indexer model enters the GPU roster. |
| K1 | IQ3_XXS wide verify falls to native vec_dot: knowledge in intake-2793; no IQ3_XXS model served. |
| K2 | Stop-inside-accepted-draft frequency on served traffic is already counted: 0 of 41 v10 turns (harness-program.md:3031 @ 860023c); no new count. |

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| LPR-01 | intake-2803 #29638 dive + intake-2811 ed1254a dive | Port EOG stop into all three accept loops with a unit test | P1 / SPEC-STALE-1 |
| LPR-02 | intake-2799 #32771 dive | Port the stop-inside-accepted-draft trim with our use_ckpt_tgt | P1 / SPEC-STALE-1 |
| LPR-03 | intake-2799 #32771 dive + intake-2802 #28232 dive | Add spec-on/off cache parity, 48-EOG tail and EOG-at-row-0 checkpoint tests | P1 / SPEC-STALE-1 |
| LPR-04 | intake-2799 #32771 dive | Count affected turns from served logs | K2 |
| LPR-05 | intake-2799 #32771 dive | Run a DF2-13-style pair ending inside an accepted draft | decline: the nondeterminism case it targets already shows warm equal to spec-off arms, so stale tokens do not explain it |
| LPR-06 | intake-2800 #32758 + intake-2809 #30252 + intake-2810 tensward + intake-2823 #30137 dives | Price the save path from LB7 probe logs, smaps and launcher grep, then decide the #30137 port | P2 / PFXC-SAVE-1 |
| LPR-07 | intake-2800 #32758 dive | Adopt the restore-retry fix (draft restore failure keeps the target buffer) | P2 / PFXC-SAVE-1 |
| LPR-08 | intake-2800 #32758 + intake-2804 #32478 + intake-2810 tensward dives | THP opt-in flag or GLIBC_TUNABLES=glibc.malloc.hugetlb=1 | decline: host THP is always, so the madvise flag and the glibc tunable are no-ops on this host |
| LPR-09 | intake-2821 #31391 + intake-2822 #30881 dives | Port the batched tensor copy API and CUDA gather | M1 |
| LPR-10 | intake-2792 #32741 + intake-2819 #28770 dives | Measure the H12 ratio band 5-8 and a token-count-aware gate | P3 / H12-BAND-1 |
| LPR-11 | intake-2819 #28770 dive | Group-union H12 variant for verify batches | P3 / H12-UNION-0 |
| LPR-12 | intake-2808 #27970 + intake-2818 #31259 dives | Move FA n_seq off slot 4 and assert H12 fusion survives a fold | P4 / FOLD-GUARD-H12 |
| LPR-13 | intake-2816 #32016 dive | Merge-tree conflict census and whole-fold recipe for the DFlash refactor; launcher --spec-type audit | P4 / FOLD-CENSUS-1 |
| LPR-14 | intake-2795 #30846 dive | Resolve #30846 against our Q8_0 nrc==2 branch at fold time with a bit-equality test | P4 / FOLD-CENSUS-1 |
| LPR-15 | intake-2795 #30846 dive | Q8_0 split-stream microbench on Zen 5 | P7 / Q8-2STREAM-1 |
| LPR-16 | intake-2797 #32740 dive | Add served FA families to the ISA gate and template-not-branch AK guidance | P5 / AK-ISA-FAMILIES |
| LPR-17 | intake-2796 #32456 dive | GDN verify-shape op baseline, mild-gate tests, conditional fused reduction | P5 / GDN-VERIFY-BASE |
| LPR-18 | intake-2796 #32456 dive | Column-width (1 vs 4 per wave) knob | M2 |
| LPR-19 | intake-2805 card + intake-2812 #32694 + intake-2798 blog dives | Inkling 2 Mini addendum and port-cost estimate | P6 / INK2-MINI-1 |
| LPR-20 | intake-2807 #32218 + intake-2817 pwilkin dives | Inkling 2 DSpark drafter alpha vs native MTP | M3 |
| LPR-21 | intake-2817 pwilkin dive | Pad DFlash2/DSpark draft block to full block_size and read first X | M4 |
| LPR-22 | intake-2793 #32774 + intake-2794 #32775 dives | Port the AVX-512 iq3_s/iq2_s vec_dot kernels | decline: with iqk enabled these ggml vec_dot functions are never reached for IQ3_S/IQ2_S on our champion |
| LPR-23 | intake-2793 #32774 dive | Extend the ZMM IQ3_S gather to 2-8 rows; ZMM IQ2_S kernel | M5 |
| LPR-24 | intake-2793 #32774 dive | Doc note: IQ3_XXS wide-MoE verify falls to native ggml vec_dot | K1 |
| LPR-25 | intake-2793 #32774 dive | MI210 LDS-staged iq3s_grid in HIP mmvq | M6 |
| LPR-26 | intake-2792 #32741 + intake-2808 #27970 dives | Port the sparse tile compaction kernel / HIP port of #27970 | decline: our fused QSA kernel reads top-k indices directly, so the compaction step never runs on the served path |
| LPR-27 | intake-2792 #32741 dive | Use the CDNA break-even rule as the prior for a DSA/indexer model | M7 |
| LPR-28 | intake-2797 #32740 dive | Port the indexed-bias FA operator | P6 / INK2-MINI-1 |
| LPR-29 | intake-2796 #32456 dive | Port the SYCL kernel / 2-warp setting | decline: SYCL is not served and the 2-warp value was tuned on Arc Pro B70 |
| LPR-30 | intake-2814 #32752, intake-2813 #32704, intake-2815 #32799 dives | Standalone boxes for Inkling 2 follow-up PRs | P6 / INK2-MINI-1 |

## Proposed handoff edits (Stage 4 only, after approval)

handoffs/active/speculative-decoding.md:
- [ ] **SPEC-STALE-1** [code] Port two upstream spec-accept fixes to a fresh llama.cpp-experimental branch from champion eee3da8, one feature per commit (intake-2803#record, intake-2811#record, intake-2799#record): (a) stop accepting draft tokens at an EOG that is not the last draft token in all three accept loops of common/sampling.cpp (plain ~:708, greedy-fast ~:928, rejection ~:960-1035; #29638 + philippesic ed1254a shape); (b) when a stop string or n_predict ends generation inside an accepted draft, trim the tokens after the stop from slot.prompt.tokens and the memory once per round (#32771 shape) using OUR use_ckpt_tgt (server-context.cpp:5976, n_rollback-based). Tests: unit test {eog,eog}->1, {eog}->2; the 48-EOG ngram tail case from #28232; an EOG at accepted row 0 on the checkpoint-restore round must terminate in one extra round; spec-on vs spec-off tokens_cached parity over 20 stop words on DFlash2 and MTP types, -np 1 and -np 2. No inference row unless the parity test shows stale tokens on our accept path.
      · done when: both commits on the branch, all four tests green on CPU (pre-fix red where applicable), PR-style note with the commit SHAs in this box

handoffs/active/harness-program.md:
- [ ] **PFXC-SAVE-1** [non-inference] Price the prompt-cache save path from evidence we already have before any port (intake-2800#record, intake-2823#record, intake-2809#record, intake-2810#record): (1) read the retained LLAMA_LB7_PROBES lines (alloc_us, idle_save_us, n_ranges, checkpoint-list size, prompt_save/prompt_load ms) for :8083 and :8070 and report P50/P95 save and restore ms and their share of TTFT; (2) read /proc/<pid>/smaps AnonHugePages for one live :8083 server during a served window (read-only); (3) grep launchers and stack configs for GGML_NOHUGEPAGE_PROCESS=1. Then decide: if save P95 >= 50 ms or >= 1% of the TTFT tail, open the port box (upstream #30137 reference-counted checkpoints + no-zero-fill buffers + #32758's restore-retry fix, with checkpoint accounting deduped by pointer); otherwise close as no-gain. THP flag and glibc.malloc.hugetlb are not adopted (host THP is `always`).
      · done when: a dated note under this box with the three readings (file paths + numbers) and the decision (port box filed, or closed no-gain)

handoffs/active/autokernel-loop.md:
- [ ] **H12-BAND-1** [inference] Measure AK-ASM-H12 fused QSA vs dense FA on the MI210 at n_kv/width 5, 6 and 8 for 1, 4, 8 and 16 query tokens (op-level test-backend-ops perf, Q38FN QSA shape hd256 gqa12, OFF/OFF A/A floor, 3 repeats), and decide whether GGML_CUDA_QSA_SPARSE_MIN_KV_RATIO=8 should drop or become token-count-aware (min(nq, cap) form) (intake-2792#record, intake-2819#record). Question: does the unmeasured 4-8 band win; expected effect >= 3% op time vs A/A noise ~1%. Stop-on-answer when every cell has a paired median; stop-on-futility if the 5x and 6x cells both lose at nq 1 and 16; keep 8 if the 6x result is < 1.03x at either nq; gate-class = futility-only.
      · done when: a row result with per-cell medians and the chosen ratio/rule, cited by row id

handoffs/active/autokernel-loop.md:
- [ ] **H12-UNION-0** [code then inference] Decide whether a group-union H12 variant is worth writing (intake-2819#record): from a Q38FN top-k dump at verify batches of 2/4/8/16 tokens and n_kv/width 4/8/16, compute the union fraction |union of the batch's top-k lists| / (tokens x top_k) per kv head (zero kernel work; dump via the existing H12 debug path or a one-off test hook). If the union fraction is <= 0.6 at 16 tokens and ratio 4 (where H12 loses, 0.78x), write the variant (gather each union row once into a tokens x G MFMA tile, mask per token) and screen it vs H12 at those cells; KEEP if geomean >= 1.10 and no cell < 0.97. Stop-on-futility if the union fraction > 0.6.
      · done when: union-fraction table committed under this box, and either a NO-GO note or a KEEP/DROP row result for the variant

handoffs/active/kernel-champion-and-promotion.md:
- [ ] **FOLD-GUARD-H12** [code] Upstream-fold guard for our FA slots (intake-2808#record, intake-2818#record): at the next fresh-from-champion fold that crosses upstream #27970 (8e93a9773) or the fused TOP_K_MASK work, (a) move our FA op_params n_seq from slot 4 to slot 5 behind the accessor (readers fattn-gqa-verify.cu:682/:739, fattn-common.cuh:1079, ggml-cpu/ops.cpp:10428 @ eee3da8) and (b) add a test that asserts H12 still fuses the Q38FN QSA node with n_kv_max set and with the fused top-k-mask op present, failing loudly instead of silently falling back to dense FA.
      · done when: fold branch carries the slot move and the H12 fusion test, test green on ROCm0 and CPU

handoffs/active/kernel-champion-and-promotion.md:
- [ ] **FOLD-CENSUS-1** [code/doc] Conflict census for the next upstream bundle fold, before any fold branch is cut (intake-2816#record, intake-2795#record): run a merge-tree census of upstream #32016 (DFlash split into dflash/dflash2/dspark/lilicorr, merge 32bdc3a89) against our dflash.cpp/speculative.cpp fork commits (DFlash2 0262f0f92/8f609e10d, sinks d0f9fab7b, NVFP4 f7cbe3a35, per-token rows affe1097f, LiLiCorr c5c61e5ab, DS41 990213088) and record the plan (fold #32016 whole, re-apply features per head class, gate on greedy drafted/accepted identity at np1/np4 for 27B DFlash2 and the DS41 GGUF); record that upstream #30846 (660be5506) rewrites mul_mat_one_chunk and collides with our Q8_0 nrc==2 branch (ggml-cpu.c:1414-1418), so the fold needs an explicit resolution plus a test-backend-ops MUL_MAT Q8_0 n=2/4/8 bit-equality check; and audit launchers for --spec-type values that #32016 starts refusing (draft-dspark on a DFlash2 GGUF disables speculation silently).
      · done when: census output path, conflict-count table and the fold recipe recorded under this box

handoffs/active/autokernel-loop.md:
- [ ] **AK-ISA-FAMILIES** [code] Add fattn_vec, fattn_tile and classifier families for the gqa-verify (gv_*) and qsa-sparse (k_qsa_sparse_*) kernels to the gfx90a_isa_audit default family set and to the pre-timing ISA gate invocation, so a VGPR increase or occupancy drop in the served decode/verify FA kernels fails before timing; add to AK actor guidance that a feature bit in an FA hot loop must be a template parameter, not a runtime branch (upstream #32740 measured ~25% loss and 181->202 registers for the runtime-branch form on NVIDIA) (intake-2797#record).
      · done when: gfx90a_isa_audit lists vec/tile/gv/qsa kernels with VGPR/occupancy on the champion libggml-hip, and diff exits 1 on a synthetic +VGPR variant

handoffs/active/autokernel-loop.md:
- [ ] **GDN-VERIFY-BASE** [inference] Measure the recurrent GATED_DELTA_NET op on ROCm0 at verify shapes (F32 and bf16 state, S_v 128 and 64, H*n_seqs 48x1 and 48x4, n_tokens 1/4/8/16, 3 repeats, A/A floor) to supply the missing verify-regime GDN share, and port upstream #32456's mild-gate (g_min -0.05) GATED_DELTA_NET test cases into the fork's test-backend-ops set (intake-2796#record). Stop with NO-GO if the 8-row 48-head op is < 3% of measured per-round verify ms; only if >= 3%, author the fused float2-reduction variant (attn = g*(S^T q) + delta*(k.q)) and screen it at these shapes (KEEP if >= 10% op time at 8 rows); gate-class = futility-only.
      · done when: row result with us/layer per shape and share of verify ms, mild-gate cases green on CPU and ROCm0, and a NO-GO or variant decision

handoffs/active/model-evaluation-queue.md:
- [ ] **INK2-MINI-1** [code-reading/doc] Inkling 2 Mini addendum and port-cost estimate (intake-2805#record, intake-2812#record, intake-2798#record): record that the 2026-08-03 Inkling NO (12B active) does not cover Inkling 2 Mini (3.4B active per pass, about 5.4B effective over 3 passes, Apache-2.0), with the per-token byte estimate (~3.2 GB at IQ4_NL experts + Q8_0 rest on CPU) and the KV table (8 full + 40 SWA@1024 visit caches); size the forward-port of upstream base inkling2 (#32217) + #32694 + #32704 + #32752 + #32799 onto the champion (files, conflicts with our FA src[5]/src[6], per-head-mask FA refused by iqk CPU ops.cpp:10390 and HIP fattn.cu:591 @ eee3da8); compare the vendor card scores against Qwen3.8-27B in our lineup; recommend go/no-go for a port box.
      · done when: addendum + port-cost table committed under this box with a go/no-go recommendation for the operator

handoffs/active/cpu-decode-roofline-program.md:
- [ ] **Q8-2STREAM-1** [inference] One-matrix microbench of upstream #30846's split-stream mul_mat_one_chunk on Q8_0 (27B-shaped ffn tensor, 24 threads on one quarter q0-q2, ne11 in {2,4,8,16}, adjacent-pair vs split-stream, hot, bit-identical output check) (intake-2795#record). Question: does the Grace two-stream effect exist on Zen 5; expected effect +2.6% (bandwidth-saturated) to +15-30% (not saturated) per the source. Stop-on-futility if < 1.5% at ne11 2..8; stop-on-answer when 4 ne11 x 3 reps are done; only a pass opens an e2e 27B DFlash2 CPU verify row.
      · done when: row result table (ne11 x median gain, bit-identity) and a pass/futility verdict

Durable trigger prose (no checkbox), one line each under the owner's current track: M1 -> handoffs/active/harness-program.md; M2 -> handoffs/active/autokernel-loop.md; M3 -> handoffs/active/speculative-decoding.md; M4 -> handoffs/active/speculative-decoding.md; M5 -> handoffs/active/autokernel-loop.md; M6 -> handoffs/active/autokernel-loop.md; M7 -> handoffs/active/long-context-program.md; K1 -> handoffs/active/cpu-decode-roofline-program.md; K2 -> handoffs/active/harness-program.md.

Index rows: none. Every box lands in a handoff that already has an index row; no new stubs.

## Declined dive-surfaced sources (wave cap of 4 reached; recorded in bearing entries' dive_corrections at Stage 4)

- On intake-2808/2818/2819 (H12 fold risk, HIGH): upstream #30640/#30965/#31243 fused TOP_K_MASK, #32519, #32247, tetherto/qvac-fabric-llm.cpp#546 — covered operationally by FOLD-GUARD-H12; recommend a follow-up intake run for these.
- On intake-2812: #32217 (base arch, sized inside INK2-MINI-1), #32755, #32710, #32707, #32718, #32732, GodGMN inkling-rdna3, #32381, #32745, #32798.
- On intake-2816: #32281, #31941, #31372, fork rebases. On intake-2821..2823: #30694, #31418, #31473, #30986, #30683, #30970, #30077, fork commits/reverts.
- On intake-2800/2810: Piggidragon/llama.cpp#23, stew675/llama-cpp-rdna-boosts#248, upstream #27478 (THP=always host). On intake-2811: d7ae2f2 (duplicate rebase). On intake-2808: #28098, #28105, #28796, #29639, #25917. On intake-2805/2806: #32187, #32268, #32784, #32786. On intake-2792: the three attached perf logs (no gfx90a). On intake-2820: #31617, #29281, #28734 (cite: qwen4exp = Q38FN), #31500.

## Steering ledger
13 operator rows, all context-only (pre-authorisation, no-compute rules, per-source steering). Full verbatim rows are in the payload.

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-2792",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): H12-BAND-1"
   ]
  },
  {
   "id": "intake-2793",
   "integration_disposition": "declined",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): LPR-22 decline; M5/M6 monitors"
   ]
  },
  {
   "id": "intake-2794",
   "integration_disposition": "declined",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): LPR-22 decline (iqk displaces the function)"
   ]
  },
  {
   "id": "intake-2795",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "cpu-decode-roofline-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): FOLD-CENSUS-1 + Q8-2STREAM-1"
   ]
  },
  {
   "id": "intake-2796",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): GDN-VERIFY-BASE"
   ]
  },
  {
   "id": "intake-2797",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "model-evaluation-queue.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): AK-ISA-FAMILIES; bias path sized in INK2-MINI-1"
   ]
  },
  {
   "id": "intake-2798",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "model-evaluation-queue.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): INK2-MINI-1"
   ]
  },
  {
   "id": "intake-2799",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): SPEC-STALE-1 (b)"
   ]
  },
  {
   "id": "intake-2800",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): PFXC-SAVE-1"
   ]
  },
  {
   "id": "intake-2801",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): SPEC-STALE-1 (a)"
   ]
  },
  {
   "id": "intake-2802",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): SPEC-STALE-1 tests (48-EOG tail, EOG at row 0)"
   ]
  },
  {
   "id": "intake-2803",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): SPEC-STALE-1 (a)"
   ]
  },
  {
   "id": "intake-2804",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): LPR-08 decline; fault counts inform PFXC-SAVE-1"
   ]
  },
  {
   "id": "intake-2805",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "model-evaluation-queue.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): INK2-MINI-1"
   ]
  },
  {
   "id": "intake-2806",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): superseded by #32694/#32704 (INK2-MINI-1 scope)"
   ]
  },
  {
   "id": "intake-2807",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): M3"
   ]
  },
  {
   "id": "intake-2808",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): FOLD-GUARD-H12"
   ]
  },
  {
   "id": "intake-2809",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): PFXC-SAVE-1 (idle_save_us read)"
   ]
  },
  {
   "id": "intake-2810",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): LPR-08 decline (THP=always)"
   ]
  },
  {
   "id": "intake-2811",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): SPEC-STALE-1 (a) rejection loop"
   ]
  },
  {
   "id": "intake-2812",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "model-evaluation-queue.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): INK2-MINI-1"
   ]
  },
  {
   "id": "intake-2813",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "model-evaluation-queue.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): INK2-MINI-1 scope"
   ]
  },
  {
   "id": "intake-2814",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "model-evaluation-queue.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): INK2-MINI-1 scope"
   ]
  },
  {
   "id": "intake-2815",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "model-evaluation-queue.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): INK2-MINI-1 scope"
   ]
  },
  {
   "id": "intake-2816",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): FOLD-CENSUS-1"
   ]
  },
  {
   "id": "intake-2817",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): M4"
   ]
  },
  {
   "id": "intake-2818",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): FOLD-GUARD-H12"
   ]
  },
  {
   "id": "intake-2819",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): H12-BAND-1 + H12-UNION-0"
   ]
  },
  {
   "id": "intake-2820",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): No CDNA/QSA behaviour; fold notes in FOLD-GUARD-H12"
   ]
  },
  {
   "id": "intake-2821",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): M1"
   ]
  },
  {
   "id": "intake-2822",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): M1"
   ]
  },
  {
   "id": "intake-2823",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-lpr-20261122 Stage-3 plan (pending operator approval): PFXC-SAVE-1 port decision"
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Prefix reuse and deterministic slot state on speculative served paths",
   "implementation_ref": "tools/server/server-context.cpp:5976-6117, common/sampling.cpp:708/:928/:960-1035 @ eee3da8",
   "gap": "No EOG stop in any accept loop and no post-stop trim; hybrid targets fall back to full reprocess on stale tokens",
   "operational_change": "Port #29638/ed1254a EOG stop and #32771 trim with tests",
   "benefit_direction": "Higher prefix reuse on hybrid models; output unchanged (correctness constraint: greedy identity)",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Code + CPU tests only; an inference row only if parity shows stale tokens",
   "closure_basis": "Immediate code; broader measurement trigger-gated"
  },
  "P2": {
   "project_objective": "Prompt-cache save/restore latency on served multi-slot servers",
   "implementation_ref": "common.cpp:2189/:2207, server-task.cpp:1741, server_prompt_cache::alloc @ eee3da8; model_registry.yaml:2017-2030",
   "gap": "Save path deep-copies the checkpoint list and zero-fills buffers; no measured price yet",
   "operational_change": "Read existing probes/smaps/launchers, then decide the #30137 port",
   "benefit_direction": "Lower TTFT tail if save cost is material",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "Zero compute first; port box only on the decision rule",
   "closure_basis": "Immediate evidence read; port gated"
  },
  "P3": {
   "project_objective": "H12 sparse QSA dispatch and verify-batch efficiency on gfx90a",
   "implementation_ref": "ggml/src/ggml-cuda/qsa-sparse.cu:248/:454-600 @ eee3da8",
   "gap": "Ratio 4-8 band unmeasured; H12 shares nothing across verify tokens and loses 0.78x at ratio 4 x 16 tokens",
   "operational_change": "Band measurement row and union-fraction gate",
   "benefit_direction": "Faster Q38FN long-context verify; numerics unchanged",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "GPU rows booked separately; kernel only after the union gate",
   "closure_basis": "Immediate measurement; variant gated"
  },
  "P4": {
   "project_objective": "Safe next upstream bundle fold",
   "implementation_ref": "ggml.c:5686-5699, llama-graph.cpp:2836, ggml-cpu.c:1414-1418, common/speculative.cpp:1306-2004, src/models/dflash.cpp @ eee3da8",
   "gap": "Fold would collide on FA slot 4/src[5], the Q8_0 nrc==2 branch and DFlash files, and could silently unfuse H12",
   "operational_change": "Fold guard test + slot move; conflict census and recipe",
   "benefit_direction": "Fold correctness; no performance claim",
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "execution_conditions": "Code/doc at fold time; no compute",
   "closure_basis": "Immediate code/doc"
  },
  "P5": {
   "project_objective": "AK guard rails and GDN cost on gfx90a",
   "implementation_ref": "gfx90a_isa_audit.py:497-515; gated_delta_net.cu:560-723 @ eee3da8; rocm-kernel-authoring.md:2240 @ 860023c",
   "gap": "ISA gate excludes the served FA kernels; verify-regime GDN share unmeasured",
   "operational_change": "Extend ISA families + guidance; GDN op baseline + tests",
   "benefit_direction": "Catch register regressions; GDN work only if material",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "ISA change is code; GDN baseline is a GPU row",
   "closure_basis": "Immediate"
  },
  "P6": {
   "project_objective": "Whether Inkling 2 Mini earns a port and a role trial",
   "implementation_ref": "model-evaluation-queue.md:676 @ 860023c; no Inkling arch in eee3da8 src/llama-arch.*",
   "gap": "Prior NO rests on first-gen 12B active; no port estimate for Mini",
   "operational_change": "Addendum + port-cost estimate (code reading)",
   "benefit_direction": "Grounded go/no-go; no compute",
   "owner": "handoffs/active/model-evaluation-queue.md",
   "execution_conditions": "Doc/code-reading only; port and rows need operator go",
   "closure_basis": "Immediate doc; port gated on operator"
  },
  "P7": {
   "project_objective": "CPU verify-batch matmul bandwidth on Zen 5",
   "implementation_ref": "ggml-cpu.c:1439-1688 @ eee3da8 (one_chunk path for Q8_0 nrc==2)",
   "gap": "#30846's two-stream effect never measured on x86",
   "operational_change": "One-matrix Q8_0 microbench row",
   "benefit_direction": "Know if the fold brings speed on EPYC; bit-identical output",
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "execution_conditions": "CPU quarter q0-q2, short window, booked separately",
   "closure_basis": "Immediate measurement; e2e row gated on pass"
  },
  "M1": {
   "project_objective": "Batched copy API / CUDA gather (#30881/#31391): reopen with the existing cache-idle-slots reopen trigger (harness-program.md:3842) or if PFXC-SAVE-1 shows restore transfer count dominating with idle saves off.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "Batched copy API / CUDA gather (#30881/#31391): reopen with the existing cache-idle-slots reopen trigger (harness-program.md:3842) or if PFXC-SAVE-1 shows restore transfer count dominating with idle saves off.",
   "closure_basis": "Batched copy API / CUDA gather (#30881/#31391): reopen with the existing cache-idle-slots reopen trigger (harness-program.md:3842) or if PFXC-SAVE-1 shows restore transfer count dominating with idle saves off."
  },
  "M2": {
   "project_objective": "GDN column-width knob: reopen only if the GDN-VERIFY-BASE fused variant KEEPs.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "GDN column-width knob: reopen only if the GDN-VERIFY-BASE fused variant KEEPs.",
   "closure_basis": "GDN column-width knob: reopen only if the GDN-VERIFY-BASE fused variant KEEPs."
  },
  "M3": {
   "project_objective": "Inkling 2 DSpark drafter alpha vs MTP: reopen when an Inkling-capable build exists and a GGUF drafter is published.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Inkling 2 DSpark drafter alpha vs MTP: reopen when an Inkling-capable build exists and a GGUF drafter is published.",
   "closure_basis": "Inkling 2 DSpark drafter alpha vs MTP: reopen when an Inkling-capable build exists and a GGUF drafter is published."
  },
  "M4": {
   "project_objective": "Full-block padding of the DFlash2/DSpark draft block: add a pad arm when the next DFlash2 X-sweep row is booked.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Full-block padding of the DFlash2/DSpark draft block: add a pad arm when the next DFlash2 X-sweep row is booked.",
   "closure_basis": "Full-block padding of the DFlash2/DSpark draft block: add a pad arm when the next DFlash2 X-sweep row is booked."
  },
  "M5": {
   "project_objective": "ZMM IQ3_S 2-8 rows / ZMM IQ2_S: reopen if a served IQ2_S/IQ3_S-heavy model profile shows the dot as bottleneck.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "ZMM IQ3_S 2-8 rows / ZMM IQ2_S: reopen if a served IQ2_S/IQ3_S-heavy model profile shows the dot as bottleneck.",
   "closure_basis": "ZMM IQ3_S 2-8 rows / ZMM IQ2_S: reopen if a served IQ2_S/IQ3_S-heavy model profile shows the dot as bottleneck."
  },
  "M6": {
   "project_objective": "LDS-staged iq3s_grid on HIP: reopen if a profile shows constant-cache serialisation in IQ3_S mmvq.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "LDS-staged iq3s_grid on HIP: reopen if a profile shows constant-cache serialisation in IQ3_S mmvq.",
   "closure_basis": "LDS-staged iq3s_grid on HIP: reopen if a profile shows constant-cache serialisation in IQ3_S mmvq."
  },
  "M7": {
   "project_objective": "CDNA sparse-FA break-even prior: reopen when a DSA/indexer model enters the GPU roster.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/long-context-program.md",
   "execution_conditions": "CDNA sparse-FA break-even prior: reopen when a DSA/indexer model enters the GPU roster.",
   "closure_basis": "CDNA sparse-FA break-even prior: reopen when a DSA/indexer model enters the GPU roster."
  },
  "K1": {
   "project_objective": "IQ3_XXS wide verify falls to native vec_dot: knowledge in intake-2793; no IQ3_XXS model served.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "execution_conditions": "IQ3_XXS wide verify falls to native vec_dot: knowledge in intake-2793; no IQ3_XXS model served.",
   "closure_basis": "IQ3_XXS wide verify falls to native vec_dot: knowledge in intake-2793; no IQ3_XXS model served."
  },
  "K2": {
   "project_objective": "Stop-inside-accepted-draft frequency on served traffic is already counted: 0 of 41 v10 turns (harness-program.md:3031 @ 860023c); no new count.",
   "implementation_ref": "see recommendation basis",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until trigger",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "Stop-inside-accepted-draft frequency on served traffic is already counted: 0 of 41 v10 turns (harness-program.md:3031 @ 860023c); no new count.",
   "closure_basis": "Stop-inside-accepted-draft frequency on served traffic is already counted: 0 of 41 v10 turns (harness-program.md:3031 @ 860023c); no new count."
  }
 },
 "actionable_additions": [
  {
   "ledger_id": "LPR-01",
   "source": "intake-2803 #29638 dive + intake-2811 ed1254a dive",
   "action": "Port EOG stop into all three accept loops with a unit test",
   "terminal_mapping": "P1 / SPEC-STALE-1"
  },
  {
   "ledger_id": "LPR-02",
   "source": "intake-2799 #32771 dive",
   "action": "Port the stop-inside-accepted-draft trim with our use_ckpt_tgt",
   "terminal_mapping": "P1 / SPEC-STALE-1"
  },
  {
   "ledger_id": "LPR-03",
   "source": "intake-2799 #32771 dive + intake-2802 #28232 dive",
   "action": "Add spec-on/off cache parity, 48-EOG tail and EOG-at-row-0 checkpoint tests",
   "terminal_mapping": "P1 / SPEC-STALE-1"
  },
  {
   "ledger_id": "LPR-04",
   "source": "intake-2799 #32771 dive",
   "action": "Count affected turns from served logs",
   "terminal_mapping": "K2"
  },
  {
   "ledger_id": "LPR-05",
   "source": "intake-2799 #32771 dive",
   "action": "Run a DF2-13-style pair ending inside an accepted draft",
   "terminal_mapping": "decline: the nondeterminism case it targets already shows warm equal to spec-off arms, so stale tokens do not explain it"
  },
  {
   "ledger_id": "LPR-06",
   "source": "intake-2800 #32758 + intake-2809 #30252 + intake-2810 tensward + intake-2823 #30137 dives",
   "action": "Price the save path from LB7 probe logs, smaps and launcher grep, then decide the #30137 port",
   "terminal_mapping": "P2 / PFXC-SAVE-1"
  },
  {
   "ledger_id": "LPR-07",
   "source": "intake-2800 #32758 dive",
   "action": "Adopt the restore-retry fix (draft restore failure keeps the target buffer)",
   "terminal_mapping": "P2 / PFXC-SAVE-1"
  },
  {
   "ledger_id": "LPR-08",
   "source": "intake-2800 #32758 + intake-2804 #32478 + intake-2810 tensward dives",
   "action": "THP opt-in flag or GLIBC_TUNABLES=glibc.malloc.hugetlb=1",
   "terminal_mapping": "decline: host THP is always, so the madvise flag and the glibc tunable are no-ops on this host"
  },
  {
   "ledger_id": "LPR-09",
   "source": "intake-2821 #31391 + intake-2822 #30881 dives",
   "action": "Port the batched tensor copy API and CUDA gather",
   "terminal_mapping": "M1"
  },
  {
   "ledger_id": "LPR-10",
   "source": "intake-2792 #32741 + intake-2819 #28770 dives",
   "action": "Measure the H12 ratio band 5-8 and a token-count-aware gate",
   "terminal_mapping": "P3 / H12-BAND-1"
  },
  {
   "ledger_id": "LPR-11",
   "source": "intake-2819 #28770 dive",
   "action": "Group-union H12 variant for verify batches",
   "terminal_mapping": "P3 / H12-UNION-0"
  },
  {
   "ledger_id": "LPR-12",
   "source": "intake-2808 #27970 + intake-2818 #31259 dives",
   "action": "Move FA n_seq off slot 4 and assert H12 fusion survives a fold",
   "terminal_mapping": "P4 / FOLD-GUARD-H12"
  },
  {
   "ledger_id": "LPR-13",
   "source": "intake-2816 #32016 dive",
   "action": "Merge-tree conflict census and whole-fold recipe for the DFlash refactor; launcher --spec-type audit",
   "terminal_mapping": "P4 / FOLD-CENSUS-1"
  },
  {
   "ledger_id": "LPR-14",
   "source": "intake-2795 #30846 dive",
   "action": "Resolve #30846 against our Q8_0 nrc==2 branch at fold time with a bit-equality test",
   "terminal_mapping": "P4 / FOLD-CENSUS-1"
  },
  {
   "ledger_id": "LPR-15",
   "source": "intake-2795 #30846 dive",
   "action": "Q8_0 split-stream microbench on Zen 5",
   "terminal_mapping": "P7 / Q8-2STREAM-1"
  },
  {
   "ledger_id": "LPR-16",
   "source": "intake-2797 #32740 dive",
   "action": "Add served FA families to the ISA gate and template-not-branch AK guidance",
   "terminal_mapping": "P5 / AK-ISA-FAMILIES"
  },
  {
   "ledger_id": "LPR-17",
   "source": "intake-2796 #32456 dive",
   "action": "GDN verify-shape op baseline, mild-gate tests, conditional fused reduction",
   "terminal_mapping": "P5 / GDN-VERIFY-BASE"
  },
  {
   "ledger_id": "LPR-18",
   "source": "intake-2796 #32456 dive",
   "action": "Column-width (1 vs 4 per wave) knob",
   "terminal_mapping": "M2"
  },
  {
   "ledger_id": "LPR-19",
   "source": "intake-2805 card + intake-2812 #32694 + intake-2798 blog dives",
   "action": "Inkling 2 Mini addendum and port-cost estimate",
   "terminal_mapping": "P6 / INK2-MINI-1"
  },
  {
   "ledger_id": "LPR-20",
   "source": "intake-2807 #32218 + intake-2817 pwilkin dives",
   "action": "Inkling 2 DSpark drafter alpha vs native MTP",
   "terminal_mapping": "M3"
  },
  {
   "ledger_id": "LPR-21",
   "source": "intake-2817 pwilkin dive",
   "action": "Pad DFlash2/DSpark draft block to full block_size and read first X",
   "terminal_mapping": "M4"
  },
  {
   "ledger_id": "LPR-22",
   "source": "intake-2793 #32774 + intake-2794 #32775 dives",
   "action": "Port the AVX-512 iq3_s/iq2_s vec_dot kernels",
   "terminal_mapping": "decline: with iqk enabled these ggml vec_dot functions are never reached for IQ3_S/IQ2_S on our champion"
  },
  {
   "ledger_id": "LPR-23",
   "source": "intake-2793 #32774 dive",
   "action": "Extend the ZMM IQ3_S gather to 2-8 rows; ZMM IQ2_S kernel",
   "terminal_mapping": "M5"
  },
  {
   "ledger_id": "LPR-24",
   "source": "intake-2793 #32774 dive",
   "action": "Doc note: IQ3_XXS wide-MoE verify falls to native ggml vec_dot",
   "terminal_mapping": "K1"
  },
  {
   "ledger_id": "LPR-25",
   "source": "intake-2793 #32774 dive",
   "action": "MI210 LDS-staged iq3s_grid in HIP mmvq",
   "terminal_mapping": "M6"
  },
  {
   "ledger_id": "LPR-26",
   "source": "intake-2792 #32741 + intake-2808 #27970 dives",
   "action": "Port the sparse tile compaction kernel / HIP port of #27970",
   "terminal_mapping": "decline: our fused QSA kernel reads top-k indices directly, so the compaction step never runs on the served path"
  },
  {
   "ledger_id": "LPR-27",
   "source": "intake-2792 #32741 dive",
   "action": "Use the CDNA break-even rule as the prior for a DSA/indexer model",
   "terminal_mapping": "M7"
  },
  {
   "ledger_id": "LPR-28",
   "source": "intake-2797 #32740 dive",
   "action": "Port the indexed-bias FA operator",
   "terminal_mapping": "P6 / INK2-MINI-1"
  },
  {
   "ledger_id": "LPR-29",
   "source": "intake-2796 #32456 dive",
   "action": "Port the SYCL kernel / 2-warp setting",
   "terminal_mapping": "decline: SYCL is not served and the 2-warp value was tuned on Arc Pro B70"
  },
  {
   "ledger_id": "LPR-30",
   "source": "intake-2814 #32752, intake-2813 #32704, intake-2815 #32799 dives",
   "action": "Standalone boxes for Inkling 2 follow-up PRs",
   "terminal_mapping": "P6 / INK2-MINI-1"
  }
 ],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "verbatim": "Operator pre-authorisation: automatically accept every recommended deep dive and literature expansion, for up to four Stage 2 sweeps. Do not stop to ask about these.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Authorises dive selection and Stage-2b waves (cap 4); applied as the dive set, not a filing authority."
  },
  {
   "seq": 2,
   "stage": 1,
   "verbatim": "The steering block is context for Stage 1 ranking and Stage 3 grounding. It does not authorise handoff writes. Apply handoff changes only as the skill permits, and present anything that needs plan approval in your final report.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Run stops at the Stage-3 plan; no handoff writes before approval."
  },
  {
   "seq": 3,
   "stage": 1,
   "verbatim": "Rules: research intake never takes compute (no GPU/CPU rows, no builds); never pkill/pgrep by name; no force-push, gc, prune or stash; report hook refusals verbatim.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Process constraints; every compute step in the plan is a separately booked row, not run by intake."
  },
  {
   "seq": 4,
   "stage": 1,
   "verbatim": "1. llama.cpp PR #32741 (open): CUDA/HIP sparse tile flash-attention masking kernel, rewritten with 16-byte loads, more loads in flight, row_count in registers and compaction data staged through LDS; sparse tile path enabled and tuned for RDNA2/3/4 and CDNA1. Builds on #30370 (intake-2749). No headline numbers in the description; perf logs are attached for MI100, RX 7900 XTX and R9700. Hardware: MI100 gfx908, RDNA; not measured on gfx90a. Value: GPU sparse attention for long context after LSA-CPU-SPARSE-E2E DROP_QUALITY; INF-48/INF-59; new CDNA implication for intake-2749. Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: 16-byte vector loads, deeper load pipelining, LDS staging for index compaction, CDNA1 tile parameters carried to gfx90a.)",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #32741 dive; outcome carried into the plan via the dive ledger."
  },
  {
   "seq": 5,
   "stage": 1,
   "verbatim": "2. llama.cpp PR #32774 (open): AVX-512/VBMI assembly iq3_s x q8_K vec_dot using grid gather lookups, two blocks in flight and word-sized scale tables. Reported 395 -> 221 ns (1.79x) on a Xeon Platinum 8573C; test-quantize-fns passes. Hardware: x86 AVX-512; should run on Zen 5 (VBMI supported). Value: INF-70 CPU decode roofline; INF-82 IQ3_XXS QDEC. Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: gather-based grid lookup, two-block software pipelining and word-sized scale tables on Zen 5's AVX-512 datapath.)",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #32774 dive."
  },
  {
   "seq": 6,
   "stage": 1,
   "verbatim": "3. llama.cpp PR #32775 (open): AVX-512F/BW/VL intrinsics path for iq2_s x q8_K vec_dot. Reported 255 -> 222 ns (1.15x) on a Xeon Platinum 8573C. Hardware: x86 AVX-512; should run on Zen 5. Value: INF-70; low-bit CPU decode alongside INF-80. Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #32775 dive."
  },
  {
   "seq": 7,
   "stage": 1,
   "verbatim": "4. llama.cpp PR #30846 (merged 2026-11-21): ggml_compute_forward_mul_mat_one_chunk accesses vx0/vx1 as two separate address streams so hardware prefetch sees two streams. Gemma-4-31B batched-bench S_TG +17.12/+23.11/+20.81/+18.06/+14.33/+12.86/+2.56% at 1-64 threads; perplexity unchanged. Hardware: NVIDIA Grace (ARM) with LLAMA_ARG_REPACK=0; not measured on EPYC. Value: INF-70; WSTREAM weight-stream work; NUMA bandwidth binding under INF-45. Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: multi-stream prefetch layout on Zen 5 L2 prefetchers per NPS4 node, and whether repacked paths already capture it.)",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #30846 dive."
  },
  {
   "seq": 8,
   "stage": 1,
   "verbatim": "5. llama.cpp PR #32456 (merged 2026-11-21): SYCL gated_delta_net kernel widened from 1 to 4 state columns per warp, with q/k loaded once per token and shared; width 1 kept for launches under 1024 warps. Op speedups 1.06-3.08x; Qwen3.5 27B Q4_K_M pp2048 935.35 -> 1003.21 t/s (+7.25%) on Arc B70; tg128 24.69 -> 25.67. Hardware: Intel Arc (SYCL); not gfx90a. Value: GDN kernel cost for Qwen3.6/3.8 hybrid; RS_REPLAY / GDN replay path in INF-50 and AutoKernel. Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: column blocking per wavefront with shared q/k loads at wave64, and the small-launch width fallback.)",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #32456 dive."
  },
  {
   "seq": 9,
   "stage": 1,
   "verbatim": "6. llama.cpp PR #32740 (open): compact indexed attention bias added as an extra FLASH_ATTN_EXT parameter (CUDA, ROCm, Vulkan) so Inkling 2 runs true FA. Commenter-reported: up to 1.9x prefill at 32K on RTX 5060 Ti and 3.4x at 33k on RTX 5070 Ti; the tile-only route cost 13-15% decode until the fattn-vec follow-up; adding bias to the vec kernel as a runtime branch cost about 25% (registers 181 -> 202). Hardware: NVIDIA, plus an unspecified ROCm GPU. Value: FA kernel variant discipline in the fork (template parameters versus runtime branches); AutoKernel register-pressure checks. Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: bias as a compile-time template parameter, bins-fastest table layout to avoid the permute, per-Q-head bias forcing ncols2=1 in GQA dispatch.)",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #32740 dive."
  },
  {
   "seq": 10,
   "stage": 1,
   "verbatim": "7. Inkling 2 Mini (HF blog, 2026-11-20): looped MoE, about 26B total / 3B active; 24 physical layers with layers 6-17 looped 3x (48 visits); 5:1 SWA (window 1,024) to full attention; 8 of 128 experts; 1M context; native NVFP4/MXFP8 experts; GGUF IQ4_NL and Q8_0 published; 3-layer DSpark drafter reading visits 5, 23 and 41 (SGLang). No spec-decode speedup numbers in the text. Hardware: B300 for the SGLang benchmark; the GGUF runs on CPU/HIP; NVFP4/MXFP8 are not usable on gfx90a. Value: INF-50 drafter comparison (DSpark versus DFlash2/MTP); looped-layer KV cost for KV compaction; relates to intake-941 (Inkling family) and intake-737 (DeepSpec/DSpark). Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the Inkling 2 Mini dive."
  },
  {
   "seq": 11,
   "stage": 1,
   "verbatim": "8. llama.cpp PR #32771 (open): when a stop triggers inside an accepted draft, trims the stop token and later tokens from the slot cache, once per round. Master: 9 of 20 stop words give different cache states with versus without a draft; fix: 20/20 match; hybrid Qwen3.5-4B MTP showed extra cached tokens in about half the stop words and 3 of 10 chat endings. CPU-tested. Value: INF-50 DF2-13 determinism; prefix-cache parity in the orchestrator; hybrid/recurrent reprocessing (#28049).",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #32771 dive."
  },
  {
   "seq": 12,
   "stage": 1,
   "verbatim": "9. llama.cpp PR #32758 (open): LLAMA_SERVER_CACHE_HUGEPAGE=1 requests THP for checkpoint and RAM prompt-cache save buffers. H100, Qwen3.8-27B Q4_K_M, 16 clients: minor faults/request 256,074 -> 3,488; checkpoint save P95 45.57 -> 30.57 ms; prompt-cache save P95 100.93 -> 54.92 ms; TTFT P95 19.548 -> 16.330 s; throughput 0.8755 -> 0.9614 req/s. Host-side, so it applies to EPYC. Value: prefix-cache / PFXC checkpointing; INF-45 memory placement; orchestrator TTFT tails. Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: THP-backed cache buffers under NPS4 node binding and the 1.13 TB RAM prompt cache.)",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Steering for the #32758 dive."
  },
  {
   "seq": 13,
   "stage": 1,
   "verbatim": "Extract: the performance principles themselves \u2014 data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied as the per-dive principles-transfer table (research/deep-dives/intake-lpr-20261122/)."
  },
  {
   "seq": 14,
   "stage": 1,
   "verbatim": "Work in a fresh worktree from origin/main, never in the shared /workspace clone. Push via scripts/coordination/serialized_push.py and verify PUSH VERIFIED.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Process constraint; lane worktree intake-lpr-20261122 from origin/main."
  },
  {
   "seq": 15,
   "stage": 1,
   "verbatim": "Final report, under 400 words: the intake ids assigned; the per-source verdict and the relevance to MI210 (gfx90a) or Zen 5; the deep dives done; the concrete recommended actions with their owner/task bindings; anything awaiting operator plan approval; commit SHAs.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Report format; applied to the final hand-back."
  }
 ],
 "opportunity_scan": [
  {
   "scan_id": "S01",
   "source_ref": "intake-2803 diff common/sampling.cpp",
   "implementation_ref": "common/sampling.cpp:708 @ eee3da8",
   "mechanism": "break at non-final EOG in accept loop",
   "consumer": "spec accept loops",
   "application": "port to 3 loops",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-01"
   ],
   "basis": "absent in champion"
  },
  {
   "scan_id": "S02",
   "source_ref": "intake-2799 diff server-context.cpp",
   "implementation_ref": "server-context.cpp:6067-6117 @ eee3da8",
   "mechanism": "trim tokens after stop inside accepted draft",
   "consumer": "server slot cache",
   "application": "port trim",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-02",
    "LPR-03"
   ],
   "basis": "same structure in champion"
  },
  {
   "scan_id": "S03",
   "source_ref": "intake-2799 page",
   "implementation_ref": "harness-program.md:3031 @ 860023c",
   "mechanism": "stale-token frequency",
   "consumer": "PFXC accounting",
   "application": "count turns",
   "disposition": "covered",
   "ledger_ids": [
    "LPR-04"
   ],
   "basis": "UFH14-A7 0/41"
  },
  {
   "scan_id": "S04",
   "source_ref": "intake-2823 diff server-task",
   "implementation_ref": "server_prompt_cache::alloc @ eee3da8",
   "mechanism": "refcounted checkpoints, no zero-fill",
   "consumer": "prompt cache save",
   "application": "price then port",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-06",
    "LPR-07"
   ],
   "basis": "deep copy present"
  },
  {
   "scan_id": "S05",
   "source_ref": "intake-2800 diff madvise",
   "implementation_ref": "/sys/kernel/mm/transparent_hugepage/enabled = always",
   "mechanism": "MADV_HUGEPAGE on save buffers",
   "consumer": "save buffers",
   "application": "THP opt-in",
   "disposition": "declined",
   "ledger_ids": [
    "LPR-08"
   ],
   "basis": "host THP always"
  },
  {
   "scan_id": "S06",
   "source_ref": "intake-2821 diff ggml-cuda",
   "implementation_ref": "ggml-cuda.cu get_tensor @ eee3da8",
   "mechanism": "batched D2H gather",
   "consumer": "MI210 save path",
   "application": "port",
   "disposition": "context-only",
   "ledger_ids": [
    "LPR-09"
   ],
   "basis": "HIP compiled out; idle saves off"
  },
  {
   "scan_id": "S07",
   "source_ref": "intake-2792 diff fattn.cu host gate",
   "implementation_ref": "qsa-sparse.cu:454-600 @ eee3da8",
   "mechanism": "CDNA break-even rule",
   "consumer": "H12 dispatch",
   "application": "band measurement",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-10",
    "LPR-27"
   ],
   "basis": "MIN_KV_RATIO post hoc"
  },
  {
   "scan_id": "S08",
   "source_ref": "intake-2819 diff union lists",
   "implementation_ref": "qsa-sparse.cu:248 @ eee3da8",
   "mechanism": "union of top-k lists per query group",
   "consumer": "H12 verify",
   "application": "union variant",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-11"
   ],
   "basis": "H12 shares nothing across tokens"
  },
  {
   "scan_id": "S09",
   "source_ref": "intake-2808 diff op_params slot 4",
   "implementation_ref": "ggml.c:5686-5699 @ eee3da8",
   "mechanism": "n_kv_max in slot 4",
   "consumer": "FA op params",
   "application": "slot move + fusion test",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-12",
    "LPR-26"
   ],
   "basis": "collision"
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-2816 diff dflash split",
   "implementation_ref": "src/models/dflash.cpp @ eee3da8",
   "mechanism": "per-head DFlash classes",
   "consumer": "DFlash2 fork commits",
   "application": "census",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-13"
   ],
   "basis": "high textual conflict"
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-2795 diff one_chunk",
   "implementation_ref": "ggml-cpu.c:1414-1418 @ eee3da8",
   "mechanism": "two address streams",
   "consumer": "Q8_0 nrc==2",
   "application": "fold resolution + microbench",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-14",
    "LPR-15"
   ],
   "basis": "absent; collides"
  },
  {
   "scan_id": "S12",
   "source_ref": "intake-2797 diff template bias",
   "implementation_ref": "gfx90a_isa_audit.py:497-515",
   "mechanism": "bias as template parameter",
   "consumer": "AK ISA gate",
   "application": "families + guidance",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-16",
    "LPR-28"
   ],
   "basis": "served FA kernels not audited"
  },
  {
   "scan_id": "S13",
   "source_ref": "intake-2796 diff column blocking",
   "implementation_ref": "gated_delta_net.cu:560-723 @ eee3da8",
   "mechanism": "shared q/k across 4 columns",
   "consumer": "GDN HIP kernel",
   "application": "verify baseline",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-17",
    "LPR-18",
    "LPR-29"
   ],
   "basis": "one column per warp"
  },
  {
   "scan_id": "S14",
   "source_ref": "intake-2805 config.json",
   "implementation_ref": "model-evaluation-queue.md:676 @ 860023c",
   "mechanism": "looped 3.4B-active MoE",
   "consumer": "model roster",
   "application": "addendum + port cost",
   "disposition": "actionable",
   "ledger_ids": [
    "LPR-19",
    "LPR-30"
   ],
   "basis": "prior NO was first-gen"
  },
  {
   "scan_id": "S15",
   "source_ref": "intake-2807 diff dspark head",
   "implementation_ref": "server-context.cpp:5511 @ eee3da8",
   "mechanism": "recurrent DSpark head",
   "consumer": "drafter roster",
   "application": "alpha comparison",
   "disposition": "context-only",
   "ledger_ids": [
    "LPR-20",
    "LPR-21"
   ],
   "basis": "no build/drafter yet"
  },
  {
   "scan_id": "S16",
   "source_ref": "intake-2793 diff asm",
   "implementation_ref": "iqk_dispatch.cpp:207-216 @ eee3da8",
   "mechanism": "vpgatherdd grid lookup",
   "consumer": "CPU IQ3_S/IQ2_S",
   "application": "port kernels",
   "disposition": "declined",
   "ledger_ids": [
    "LPR-22",
    "LPR-23",
    "LPR-24",
    "LPR-25"
   ],
   "basis": "iqk path displaces"
  },
  {
   "scan_id": "S17",
   "source_ref": "intake-2799 page DF2-13",
   "implementation_ref": "speculative-decoding.md DF2-13 @ 860023c",
   "mechanism": "stop-in-draft as DF2-13 cause",
   "consumer": "DF2-13",
   "application": "pair run",
   "disposition": "declined",
   "ledger_ids": [
    "LPR-05"
   ],
   "basis": "warm == spec-off"
  }
 ],
 "outcome_reviews": {
  "LPR-01": {
   "required_outcome": "Accept loops stop at a non-final EOG on our champion line",
   "review_status": "preserved",
   "review_basis": "SPEC-STALE-1 part (a) and its unit test",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-STALE-1",
     "task_text": "- [ ] **SPEC-STALE-1** [code] Port two upstream spec-accept fixes to a fresh llama.cpp-experimental branch from champion eee3da8, one feature per commit (intake-2803#record, intake-2811#record, intake-2799#record): (a) stop accepting draft tokens at an EOG that is not the last draft token in all three accept loops of common/sampling.cpp (plain ~:708, greedy-fast ~:928, rejection ~:960-1035; #29638 + philippesic ed1254a shape); (b) when a stop string or n_predict ends generation inside an accepted draft, trim the tokens after the stop from slot.prompt.tokens and the memory once per round (#32771 shape) using OUR use_ckpt_tgt (server-context.cpp:5976, n_rollback-based). Tests: unit test {eog,eog}->1, {eog}->2; the 48-EOG ngram tail case from #28232; an EOG at accepted row 0 on the checkpoint-restore round must terminate in one extra round; spec-on vs spec-off tokens_cached parity over 20 stop words on DFlash2 and MTP types, -np 1 and -np 2. No inference row unless the parity test shows stale tokens on our accept path.",
     "acceptance": "SPEC-STALE-1 part (a) and its unit test"
    }
   ]
  },
  "LPR-02": {
   "required_outcome": "No stale post-stop tokens remain in slot cache after spec rounds",
   "review_status": "preserved",
   "review_basis": "SPEC-STALE-1 part (b) and the parity test",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-STALE-1",
     "task_text": "- [ ] **SPEC-STALE-1** [code] Port two upstream spec-accept fixes to a fresh llama.cpp-experimental branch from champion eee3da8, one feature per commit (intake-2803#record, intake-2811#record, intake-2799#record): (a) stop accepting draft tokens at an EOG that is not the last draft token in all three accept loops of common/sampling.cpp (plain ~:708, greedy-fast ~:928, rejection ~:960-1035; #29638 + philippesic ed1254a shape); (b) when a stop string or n_predict ends generation inside an accepted draft, trim the tokens after the stop from slot.prompt.tokens and the memory once per round (#32771 shape) using OUR use_ckpt_tgt (server-context.cpp:5976, n_rollback-based). Tests: unit test {eog,eog}->1, {eog}->2; the 48-EOG ngram tail case from #28232; an EOG at accepted row 0 on the checkpoint-restore round must terminate in one extra round; spec-on vs spec-off tokens_cached parity over 20 stop words on DFlash2 and MTP types, -np 1 and -np 2. No inference row unless the parity test shows stale tokens on our accept path.",
     "acceptance": "SPEC-STALE-1 part (b) and the parity test"
    }
   ]
  },
  "LPR-03": {
   "required_outcome": "Regression tests guard the accept-path fixes",
   "review_status": "preserved",
   "review_basis": "SPEC-STALE-1 test list",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-STALE-1",
     "task_text": "- [ ] **SPEC-STALE-1** [code] Port two upstream spec-accept fixes to a fresh llama.cpp-experimental branch from champion eee3da8, one feature per commit (intake-2803#record, intake-2811#record, intake-2799#record): (a) stop accepting draft tokens at an EOG that is not the last draft token in all three accept loops of common/sampling.cpp (plain ~:708, greedy-fast ~:928, rejection ~:960-1035; #29638 + philippesic ed1254a shape); (b) when a stop string or n_predict ends generation inside an accepted draft, trim the tokens after the stop from slot.prompt.tokens and the memory once per round (#32771 shape) using OUR use_ckpt_tgt (server-context.cpp:5976, n_rollback-based). Tests: unit test {eog,eog}->1, {eog}->2; the 48-EOG ngram tail case from #28232; an EOG at accepted row 0 on the checkpoint-restore round must terminate in one extra round; spec-on vs spec-off tokens_cached parity over 20 stop words on DFlash2 and MTP types, -np 1 and -np 2. No inference row unless the parity test shows stale tokens on our accept path.",
     "acceptance": "SPEC-STALE-1 test list"
    }
   ]
  },
  "LPR-04": {
   "required_outcome": "Frequency of stop-inside-accepted-draft turns on our traffic is known",
   "review_status": "closed-with-basis",
   "review_basis": "Already measured: UFH14-A7 counted 0 of 41 turns with a post-generation checkpoint past the kept text on v10 logs (harness-program.md:3031 @ 860023c); no new count needed",
   "task_refs": []
  },
  "LPR-05": {
   "required_outcome": "DF2-13 nondeterminism attribution",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: the dive found DF2-13's warm arm equals the spec-off arms (near-ties only), so the stale-token bug is not its explanation; reopen only if the parity test shows stale tokens on our path",
   "task_refs": []
  },
  "LPR-06": {
   "required_outcome": "A measured go/no-go for porting reference-counted checkpoints and no-zero-fill buffers",
   "review_status": "preserved",
   "review_basis": "PFXC-SAVE-1 readings and decision rule",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "PFXC-SAVE-1",
     "task_text": "- [ ] **PFXC-SAVE-1** [non-inference] Price the prompt-cache save path from evidence we already have before any port (intake-2800#record, intake-2823#record, intake-2809#record, intake-2810#record): (1) read the retained LLAMA_LB7_PROBES lines (alloc_us, idle_save_us, n_ranges, checkpoint-list size, prompt_save/prompt_load ms) for :8083 and :8070 and report P50/P95 save and restore ms and their share of TTFT; (2) read /proc/<pid>/smaps AnonHugePages for one live :8083 server during a served window (read-only); (3) grep launchers and stack configs for GGML_NOHUGEPAGE_PROCESS=1. Then decide: if save P95 >= 50 ms or >= 1% of the TTFT tail, open the port box (upstream #30137 reference-counted checkpoints + no-zero-fill buffers + #32758's restore-retry fix, with checkpoint accounting deduped by pointer); otherwise close as no-gain. THP flag and glibc.malloc.hugetlb are not adopted (host THP is `always`).",
     "acceptance": "PFXC-SAVE-1 readings and decision rule"
    }
   ]
  },
  "LPR-07": {
   "required_outcome": "Champion prompt-cache load no longer frees the target buffer before a draft restore",
   "review_status": "preserved",
   "review_basis": "Included in the PFXC-SAVE-1 port box contents",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "PFXC-SAVE-1",
     "task_text": "- [ ] **PFXC-SAVE-1** [non-inference] Price the prompt-cache save path from evidence we already have before any port (intake-2800#record, intake-2823#record, intake-2809#record, intake-2810#record): (1) read the retained LLAMA_LB7_PROBES lines (alloc_us, idle_save_us, n_ranges, checkpoint-list size, prompt_save/prompt_load ms) for :8083 and :8070 and report P50/P95 save and restore ms and their share of TTFT; (2) read /proc/<pid>/smaps AnonHugePages for one live :8083 server during a served window (read-only); (3) grep launchers and stack configs for GGML_NOHUGEPAGE_PROCESS=1. Then decide: if save P95 >= 50 ms or >= 1% of the TTFT tail, open the port box (upstream #30137 reference-counted checkpoints + no-zero-fill buffers + #32758's restore-retry fix, with checkpoint accounting deduped by pointer); otherwise close as no-gain. THP flag and glibc.malloc.hugetlb are not adopted (host THP is `always`).",
     "acceptance": "Included in the PFXC-SAVE-1 port box contents"
    }
   ]
  },
  "LPR-08": {
   "required_outcome": "Huge-page backing of save buffers",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: host THP enabled and defrag are both `always` (read 2026-11-22), so MADV_HUGEPAGE and the madvise-mode tunable are policy no-ops here; the tensward baseline was a madvise-mode host. Reopen only if host THP mode changes",
   "task_refs": []
  },
  "LPR-09": {
   "required_outcome": "Fewer device transfers per prompt-cache save/restore on the MI210 server",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: #31391 is compiled out on HIP; :8083 runs cache_idle_slots false (model_registry.yaml:2023) so the #30252 stall loop is not reached; LB7.1 found the cost is restore transfer count, and the run-coalesced restore already has a reopen trigger (harness-program.md:3842 @ 860023c)",
   "task_refs": []
  },
  "LPR-10": {
   "required_outcome": "H12 dispatch threshold set from measurement, not post hoc",
   "review_status": "preserved",
   "review_basis": "H12-BAND-1",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "H12-BAND-1",
     "task_text": "- [ ] **H12-BAND-1** [inference] Measure AK-ASM-H12 fused QSA vs dense FA on the MI210 at n_kv/width 5, 6 and 8 for 1, 4, 8 and 16 query tokens (op-level test-backend-ops perf, Q38FN QSA shape hd256 gqa12, OFF/OFF A/A floor, 3 repeats), and decide whether GGML_CUDA_QSA_SPARSE_MIN_KV_RATIO=8 should drop or become token-count-aware (min(nq, cap) form) (intake-2792#record, intake-2819#record). Question: does the unmeasured 4-8 band win; expected effect >= 3% op time vs A/A noise ~1%. Stop-on-answer when every cell has a paired median; stop-on-futility if the 5x and 6x cells both lose at nq 1 and 16; keep 8 if the 6x result is < 1.03x at either nq; gate-class = futility-only.",
     "acceptance": "H12-BAND-1"
    }
   ]
  },
  "LPR-11": {
   "required_outcome": "H12 wins at ratio 4 x 16 tokens where it now loses",
   "review_status": "preserved",
   "review_basis": "H12-UNION-0 union-fraction gate then variant",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "H12-UNION-0",
     "task_text": "- [ ] **H12-UNION-0** [code then inference] Decide whether a group-union H12 variant is worth writing (intake-2819#record): from a Q38FN top-k dump at verify batches of 2/4/8/16 tokens and n_kv/width 4/8/16, compute the union fraction |union of the batch's top-k lists| / (tokens x top_k) per kv head (zero kernel work; dump via the existing H12 debug path or a one-off test hook). If the union fraction is <= 0.6 at 16 tokens and ratio 4 (where H12 loses, 0.78x), write the variant (gather each union row once into a tokens x G MFMA tile, mask per token) and screen it vs H12 at those cells; KEEP if geomean >= 1.10 and no cell < 0.97. Stop-on-futility if the union fraction > 0.6.",
     "acceptance": "H12-UNION-0 union-fraction gate then variant"
    }
   ]
  },
  "LPR-12": {
   "required_outcome": "An upstream fold cannot silently disable H12 or corrupt n_seq",
   "review_status": "preserved",
   "review_basis": "FOLD-GUARD-H12",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "FOLD-GUARD-H12",
     "task_text": "- [ ] **FOLD-GUARD-H12** [code] Upstream-fold guard for our FA slots (intake-2808#record, intake-2818#record): at the next fresh-from-champion fold that crosses upstream #27970 (8e93a9773) or the fused TOP_K_MASK work, (a) move our FA op_params n_seq from slot 4 to slot 5 behind the accessor (readers fattn-gqa-verify.cu:682/:739, fattn-common.cuh:1079, ggml-cpu/ops.cpp:10428 @ eee3da8) and (b) add a test that asserts H12 still fuses the Q38FN QSA node with n_kv_max set and with the fused top-k-mask op present, failing loudly instead of silently falling back to dense FA.",
     "acceptance": "FOLD-GUARD-H12"
    }
   ]
  },
  "LPR-13": {
   "required_outcome": "The next bundle fold knows its DFlash conflict surface and launcher breakage",
   "review_status": "preserved",
   "review_basis": "FOLD-CENSUS-1",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "FOLD-CENSUS-1",
     "task_text": "- [ ] **FOLD-CENSUS-1** [code/doc] Conflict census for the next upstream bundle fold, before any fold branch is cut (intake-2816#record, intake-2795#record): run a merge-tree census of upstream #32016 (DFlash split into dflash/dflash2/dspark/lilicorr, merge 32bdc3a89) against our dflash.cpp/speculative.cpp fork commits (DFlash2 0262f0f92/8f609e10d, sinks d0f9fab7b, NVFP4 f7cbe3a35, per-token rows affe1097f, LiLiCorr c5c61e5ab, DS41 990213088) and record the plan (fold #32016 whole, re-apply features per head class, gate on greedy drafted/accepted identity at np1/np4 for 27B DFlash2 and the DS41 GGUF); record that upstream #30846 (660be5506) rewrites mul_mat_one_chunk and collides with our Q8_0 nrc==2 branch (ggml-cpu.c:1414-1418), so the fold needs an explicit resolution plus a test-backend-ops MUL_MAT Q8_0 n=2/4/8 bit-equality check; and audit launchers for --spec-type values that #32016 starts refusing (draft-dspark on a DFlash2 GGUF disables speculation silently).",
     "acceptance": "FOLD-CENSUS-1"
    }
   ]
  },
  "LPR-14": {
   "required_outcome": "Fold does not skip or duplicate Q8_0 rows",
   "review_status": "preserved",
   "review_basis": "FOLD-CENSUS-1 #30846 clause",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "FOLD-CENSUS-1",
     "task_text": "- [ ] **FOLD-CENSUS-1** [code/doc] Conflict census for the next upstream bundle fold, before any fold branch is cut (intake-2816#record, intake-2795#record): run a merge-tree census of upstream #32016 (DFlash split into dflash/dflash2/dspark/lilicorr, merge 32bdc3a89) against our dflash.cpp/speculative.cpp fork commits (DFlash2 0262f0f92/8f609e10d, sinks d0f9fab7b, NVFP4 f7cbe3a35, per-token rows affe1097f, LiLiCorr c5c61e5ab, DS41 990213088) and record the plan (fold #32016 whole, re-apply features per head class, gate on greedy drafted/accepted identity at np1/np4 for 27B DFlash2 and the DS41 GGUF); record that upstream #30846 (660be5506) rewrites mul_mat_one_chunk and collides with our Q8_0 nrc==2 branch (ggml-cpu.c:1414-1418), so the fold needs an explicit resolution plus a test-backend-ops MUL_MAT Q8_0 n=2/4/8 bit-equality check; and audit launchers for --spec-type values that #32016 starts refusing (draft-dspark on a DFlash2 GGUF disables speculation silently).",
     "acceptance": "FOLD-CENSUS-1 #30846 clause"
    }
   ]
  },
  "LPR-15": {
   "required_outcome": "Know whether the two-stream effect exists on EPYC before folding it for speed",
   "review_status": "preserved",
   "review_basis": "Q8-2STREAM-1",
   "task_refs": [
    {
     "owner": "handoffs/active/cpu-decode-roofline-program.md",
     "task_id": "Q8-2STREAM-1",
     "task_text": "- [ ] **Q8-2STREAM-1** [inference] One-matrix microbench of upstream #30846's split-stream mul_mat_one_chunk on Q8_0 (27B-shaped ffn tensor, 24 threads on one quarter q0-q2, ne11 in {2,4,8,16}, adjacent-pair vs split-stream, hot, bit-identical output check) (intake-2795#record). Question: does the Grace two-stream effect exist on Zen 5; expected effect +2.6% (bandwidth-saturated) to +15-30% (not saturated) per the source. Stop-on-futility if < 1.5% at ne11 2..8; stop-on-answer when 4 ne11 x 3 reps are done; only a pass opens an e2e 27B DFlash2 CPU verify row.",
     "acceptance": "Q8-2STREAM-1"
    }
   ]
  },
  "LPR-16": {
   "required_outcome": "VGPR/occupancy regressions in served FA kernels fail before timing",
   "review_status": "preserved",
   "review_basis": "AK-ISA-FAMILIES",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-ISA-FAMILIES",
     "task_text": "- [ ] **AK-ISA-FAMILIES** [code] Add fattn_vec, fattn_tile and classifier families for the gqa-verify (gv_*) and qsa-sparse (k_qsa_sparse_*) kernels to the gfx90a_isa_audit default family set and to the pre-timing ISA gate invocation, so a VGPR increase or occupancy drop in the served decode/verify FA kernels fails before timing; add to AK actor guidance that a feature bit in an FA hot loop must be a template parameter, not a runtime branch (upstream #32740 measured ~25% loss and 181->202 registers for the runtime-branch form on NVIDIA) (intake-2797#record).",
     "acceptance": "AK-ISA-FAMILIES"
    }
   ]
  },
  "LPR-17": {
   "required_outcome": "Verify-regime GDN share known; GDN kernel work only if it matters",
   "review_status": "preserved",
   "review_basis": "GDN-VERIFY-BASE",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "GDN-VERIFY-BASE",
     "task_text": "- [ ] **GDN-VERIFY-BASE** [inference] Measure the recurrent GATED_DELTA_NET op on ROCm0 at verify shapes (F32 and bf16 state, S_v 128 and 64, H*n_seqs 48x1 and 48x4, n_tokens 1/4/8/16, 3 repeats, A/A floor) to supply the missing verify-regime GDN share, and port upstream #32456's mild-gate (g_min -0.05) GATED_DELTA_NET test cases into the fork's test-backend-ops set (intake-2796#record). Stop with NO-GO if the 8-row 48-head op is < 3% of measured per-round verify ms; only if >= 3%, author the fused float2-reduction variant (attn = g*(S^T q) + delta*(k.q)) and screen it at these shapes (KEEP if >= 10% op time at 8 rows); gate-class = futility-only.",
     "acceptance": "GDN-VERIFY-BASE"
    }
   ]
  },
  "LPR-18": {
   "required_outcome": "Column blocking on wave64",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: only meaningful if the GDN-VERIFY-BASE fused variant KEEPs; wave64 gives 2 rows per lane at S_v=128 so the expected gain is smaller than Arc",
   "task_refs": []
  },
  "LPR-19": {
   "required_outcome": "Operator gets a grounded go/no-go for an Inkling 2 Mini port",
   "review_status": "preserved",
   "review_basis": "INK2-MINI-1",
   "task_refs": [
    {
     "owner": "handoffs/active/model-evaluation-queue.md",
     "task_id": "INK2-MINI-1",
     "task_text": "- [ ] **INK2-MINI-1** [code-reading/doc] Inkling 2 Mini addendum and port-cost estimate (intake-2805#record, intake-2812#record, intake-2798#record): record that the 2026-08-03 Inkling NO (12B active) does not cover Inkling 2 Mini (3.4B active per pass, about 5.4B effective over 3 passes, Apache-2.0), with the per-token byte estimate (~3.2 GB at IQ4_NL experts + Q8_0 rest on CPU) and the KV table (8 full + 40 SWA@1024 visit caches); size the forward-port of upstream base inkling2 (#32217) + #32694 + #32704 + #32752 + #32799 onto the champion (files, conflicts with our FA src[5]/src[6], per-head-mask FA refused by iqk CPU ops.cpp:10390 and HIP fattn.cu:591 @ eee3da8); compare the vendor card scores against Qwen3.8-27B in our lineup; recommend go/no-go for a port box.",
     "acceptance": "INK2-MINI-1"
    }
   ]
  },
  "LPR-20": {
   "required_outcome": "Drafter comparison for Inkling 2 Mini",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: needs an Inkling-capable build (INK2-MINI-1 go) and a GGUF drafter; #32218 is a CHANGES_REQUESTED draft with no acceptance numbers",
   "task_refs": []
  },
  "LPR-21": {
   "required_outcome": "Possible acceptance gain from a trained-shape draft block",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: the page supports it only for the Inkling sidecar and reports no numbers; add a pad arm when the next DFlash2 X-sweep row is booked",
   "task_refs": []
  },
  "LPR-22": {
   "required_outcome": "Faster IQ3_S/IQ2_S CPU dot products",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: with GGML_IQK=1 our IQ3_S/IQ2_S matmuls never reach ggml_vec_dot_* (iqk_dispatch.cpp:207-216, :343-352 @ eee3da8); our IQ3_S n=1 already has a ZMM gather+VNNI path whose Zen 5 profile was NO_MOVE (autokernel-loop.md:4290 @ 860023c); the PR numbers are a cache-hot single-call microbench",
   "task_refs": []
  },
  "LPR-23": {
   "required_outcome": "Wider iqk ZMM coverage",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: seed 73's NO_MOVE predicts small gain; IQ2_S has no served model; reopen if a served IQ2_S/IQ3_S-heavy model's profile shows the dot as the bottleneck",
   "task_refs": []
  },
  "LPR-24": {
   "required_outcome": "Dispatch fact recorded",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: no IQ3_XXS model is served (autokernel-akx-program.md:1705 @ 860023c); the fact lives in intake-2793",
   "task_refs": []
  },
  "LPR-25": {
   "required_outcome": "IQ3_S mmvq lookup cost on gfx90a",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: no profile shows constant-cache serialisation; open only if one does",
   "task_refs": []
  },
  "LPR-26": {
   "required_outcome": "Upstream sparse FA on gfx90a",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: H12 reads top-k indices directly so the compaction step never runs on our served QSA path; on CDNA upstream selects only the 576/512 MLA shape (intake-2818)",
   "task_refs": []
  },
  "LPR-27": {
   "required_outcome": "Sparse FA dispatch rule for future DSA models on gfx90a",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: no DSA/indexer model is on the GPU roster; reopen when one is",
   "task_refs": []
  },
  "LPR-28": {
   "required_outcome": "FA-with-bias cost is part of the Inkling port estimate",
   "review_status": "preserved",
   "review_basis": "INK2-MINI-1 sizes the bias path (per-head mask refused by our FA gates)",
   "task_refs": [
    {
     "owner": "handoffs/active/model-evaluation-queue.md",
     "task_id": "INK2-MINI-1",
     "task_text": "- [ ] **INK2-MINI-1** [code-reading/doc] Inkling 2 Mini addendum and port-cost estimate (intake-2805#record, intake-2812#record, intake-2798#record): record that the 2026-08-03 Inkling NO (12B active) does not cover Inkling 2 Mini (3.4B active per pass, about 5.4B effective over 3 passes, Apache-2.0), with the per-token byte estimate (~3.2 GB at IQ4_NL experts + Q8_0 rest on CPU) and the KV table (8 full + 40 SWA@1024 visit caches); size the forward-port of upstream base inkling2 (#32217) + #32694 + #32704 + #32752 + #32799 onto the champion (files, conflicts with our FA src[5]/src[6], per-head-mask FA refused by iqk CPU ops.cpp:10390 and HIP fattn.cu:591 @ eee3da8); compare the vendor card scores against Qwen3.8-27B in our lineup; recommend go/no-go for a port box.",
     "acceptance": "INK2-MINI-1 sizes the bias path (per-head mask refused by our FA gates)"
    }
   ]
  },
  "LPR-29": {
   "required_outcome": "SYCL GDN",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: SYCL is not served and the 2-warp value was tuned on Arc Pro B70 per the PR's own comment",
   "task_refs": []
  },
  "LPR-30": {
   "required_outcome": "Follow-ups travel with the arch port",
   "review_status": "preserved",
   "review_basis": "INK2-MINI-1 includes them in the port scope",
   "task_refs": [
    {
     "owner": "handoffs/active/model-evaluation-queue.md",
     "task_id": "INK2-MINI-1",
     "task_text": "- [ ] **INK2-MINI-1** [code-reading/doc] Inkling 2 Mini addendum and port-cost estimate (intake-2805#record, intake-2812#record, intake-2798#record): record that the 2026-08-03 Inkling NO (12B active) does not cover Inkling 2 Mini (3.4B active per pass, about 5.4B effective over 3 passes, Apache-2.0), with the per-token byte estimate (~3.2 GB at IQ4_NL experts + Q8_0 rest on CPU) and the KV table (8 full + 40 SWA@1024 visit caches); size the forward-port of upstream base inkling2 (#32217) + #32694 + #32704 + #32752 + #32799 onto the champion (files, conflicts with our FA src[5]/src[6], per-head-mask FA refused by iqk CPU ops.cpp:10390 and HIP fattn.cu:591 @ eee3da8); compare the vendor card scores against Qwen3.8-27B in our lineup; recommend go/no-go for a port box.",
     "acceptance": "INK2-MINI-1 includes them in the port scope"
    }
   ]
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-STALE-1** [code] Port two upstream spec-accept fixes to a fresh llama.cpp-experimental branch from champion eee3da8, one feature per commit (intake-2803#record, intake-2811#record, intake-2799#record): (a) stop accepting draft tokens at an EOG that is not the last draft token in all three accept loops of common/sampling.cpp (plain ~:708, greedy-fast ~:928, rejection ~:960-1035; #29638 + philippesic ed1254a shape); (b) when a stop string or n_predict ends generation inside an accepted draft, trim the tokens after the stop from slot.prompt.tokens and the memory once per round (#32771 shape) using OUR use_ckpt_tgt (server-context.cpp:5976, n_rollback-based). Tests: unit test {eog,eog}->1, {eog}->2; the 48-EOG ngram tail case from #28232; an EOG at accepted row 0 on the checkpoint-restore round must terminate in one extra round; spec-on vs spec-off tokens_cached parity over 20 stop words on DFlash2 and MTP types, -np 1 and -np 2. No inference row unless the parity test shows stale tokens on our accept path."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **PFXC-SAVE-1** [non-inference] Price the prompt-cache save path from evidence we already have before any port (intake-2800#record, intake-2823#record, intake-2809#record, intake-2810#record): (1) read the retained LLAMA_LB7_PROBES lines (alloc_us, idle_save_us, n_ranges, checkpoint-list size, prompt_save/prompt_load ms) for :8083 and :8070 and report P50/P95 save and restore ms and their share of TTFT; (2) read /proc/<pid>/smaps AnonHugePages for one live :8083 server during a served window (read-only); (3) grep launchers and stack configs for GGML_NOHUGEPAGE_PROCESS=1. Then decide: if save P95 >= 50 ms or >= 1% of the TTFT tail, open the port box (upstream #30137 reference-counted checkpoints + no-zero-fill buffers + #32758's restore-retry fix, with checkpoint accounting deduped by pointer); otherwise close as no-gain. THP flag and glibc.malloc.hugetlb are not adopted (host THP is `always`)."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **H12-BAND-1** [inference] Measure AK-ASM-H12 fused QSA vs dense FA on the MI210 at n_kv/width 5, 6 and 8 for 1, 4, 8 and 16 query tokens (op-level test-backend-ops perf, Q38FN QSA shape hd256 gqa12, OFF/OFF A/A floor, 3 repeats), and decide whether GGML_CUDA_QSA_SPARSE_MIN_KV_RATIO=8 should drop or become token-count-aware (min(nq, cap) form) (intake-2792#record, intake-2819#record). Question: does the unmeasured 4-8 band win; expected effect >= 3% op time vs A/A noise ~1%. Stop-on-answer when every cell has a paired median; stop-on-futility if the 5x and 6x cells both lose at nq 1 and 16; keep 8 if the 6x result is < 1.03x at either nq; gate-class = futility-only."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **H12-UNION-0** [code then inference] Decide whether a group-union H12 variant is worth writing (intake-2819#record): from a Q38FN top-k dump at verify batches of 2/4/8/16 tokens and n_kv/width 4/8/16, compute the union fraction |union of the batch's top-k lists| / (tokens x top_k) per kv head (zero kernel work; dump via the existing H12 debug path or a one-off test hook). If the union fraction is <= 0.6 at 16 tokens and ratio 4 (where H12 loses, 0.78x), write the variant (gather each union row once into a tokens x G MFMA tile, mask per token) and screen it vs H12 at those cells; KEEP if geomean >= 1.10 and no cell < 0.97. Stop-on-futility if the union fraction > 0.6."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **FOLD-GUARD-H12** [code] Upstream-fold guard for our FA slots (intake-2808#record, intake-2818#record): at the next fresh-from-champion fold that crosses upstream #27970 (8e93a9773) or the fused TOP_K_MASK work, (a) move our FA op_params n_seq from slot 4 to slot 5 behind the accessor (readers fattn-gqa-verify.cu:682/:739, fattn-common.cuh:1079, ggml-cpu/ops.cpp:10428 @ eee3da8) and (b) add a test that asserts H12 still fuses the Q38FN QSA node with n_kv_max set and with the fused top-k-mask op present, failing loudly instead of silently falling back to dense FA."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **FOLD-CENSUS-1** [code/doc] Conflict census for the next upstream bundle fold, before any fold branch is cut (intake-2816#record, intake-2795#record): run a merge-tree census of upstream #32016 (DFlash split into dflash/dflash2/dspark/lilicorr, merge 32bdc3a89) against our dflash.cpp/speculative.cpp fork commits (DFlash2 0262f0f92/8f609e10d, sinks d0f9fab7b, NVFP4 f7cbe3a35, per-token rows affe1097f, LiLiCorr c5c61e5ab, DS41 990213088) and record the plan (fold #32016 whole, re-apply features per head class, gate on greedy drafted/accepted identity at np1/np4 for 27B DFlash2 and the DS41 GGUF); record that upstream #30846 (660be5506) rewrites mul_mat_one_chunk and collides with our Q8_0 nrc==2 branch (ggml-cpu.c:1414-1418), so the fold needs an explicit resolution plus a test-backend-ops MUL_MAT Q8_0 n=2/4/8 bit-equality check; and audit launchers for --spec-type values that #32016 starts refusing (draft-dspark on a DFlash2 GGUF disables speculation silently)."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-ISA-FAMILIES** [code] Add fattn_vec, fattn_tile and classifier families for the gqa-verify (gv_*) and qsa-sparse (k_qsa_sparse_*) kernels to the gfx90a_isa_audit default family set and to the pre-timing ISA gate invocation, so a VGPR increase or occupancy drop in the served decode/verify FA kernels fails before timing; add to AK actor guidance that a feature bit in an FA hot loop must be a template parameter, not a runtime branch (upstream #32740 measured ~25% loss and 181->202 registers for the runtime-branch form on NVIDIA) (intake-2797#record)."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **GDN-VERIFY-BASE** [inference] Measure the recurrent GATED_DELTA_NET op on ROCm0 at verify shapes (F32 and bf16 state, S_v 128 and 64, H*n_seqs 48x1 and 48x4, n_tokens 1/4/8/16, 3 repeats, A/A floor) to supply the missing verify-regime GDN share, and port upstream #32456's mild-gate (g_min -0.05) GATED_DELTA_NET test cases into the fork's test-backend-ops set (intake-2796#record). Stop with NO-GO if the 8-row 48-head op is < 3% of measured per-round verify ms; only if >= 3%, author the fused float2-reduction variant (attn = g*(S^T q) + delta*(k.q)) and screen it at these shapes (KEEP if >= 10% op time at 8 rows); gate-class = futility-only."
  },
  {
   "owner": "handoffs/active/model-evaluation-queue.md",
   "task_text": "- [ ] **INK2-MINI-1** [code-reading/doc] Inkling 2 Mini addendum and port-cost estimate (intake-2805#record, intake-2812#record, intake-2798#record): record that the 2026-08-03 Inkling NO (12B active) does not cover Inkling 2 Mini (3.4B active per pass, about 5.4B effective over 3 passes, Apache-2.0), with the per-token byte estimate (~3.2 GB at IQ4_NL experts + Q8_0 rest on CPU) and the KV table (8 full + 40 SWA@1024 visit caches); size the forward-port of upstream base inkling2 (#32217) + #32694 + #32704 + #32752 + #32799 onto the champion (files, conflicts with our FA src[5]/src[6], per-head-mask FA refused by iqk CPU ops.cpp:10390 and HIP fattn.cu:591 @ eee3da8); compare the vendor card scores against Qwen3.8-27B in our lineup; recommend go/no-go for a port box."
  },
  {
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "task_text": "- [ ] **Q8-2STREAM-1** [inference] One-matrix microbench of upstream #30846's split-stream mul_mat_one_chunk on Q8_0 (27B-shaped ffn tensor, 24 threads on one quarter q0-q2, ne11 in {2,4,8,16}, adjacent-pair vs split-stream, hot, bit-identical output check) (intake-2795#record). Question: does the Grace two-stream effect exist on Zen 5; expected effect +2.6% (bandwidth-saturated) to +15-30% (not saturated) per the source. Stop-on-futility if < 1.5% at ne11 2..8; stop-on-answer when 4 ne11 x 3 reps are done; only a pass opens an e2e 27B DFlash2 CPU verify row."
  }
 ]
}
```
