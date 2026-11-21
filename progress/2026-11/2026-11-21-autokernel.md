# 2026-11-21 autokernel

## Wrap-up 10 (00:00Z-03:30Z)

### Headline: V5I makes the SERVED 27B+DFlash2 9.95% faster at noise-floor numerics
- `ak-v5i-27b-dflash2-e2e-gpu-20261121` KEEP: tok/s +9.95% [1.078, 1.121], 4 pairs, acceptance unchanged, oracle 0/96.
- `ak-v5i-27b-kld-gpu-20261121` PASS: KLD 0.000387 (X/X 0.000338), dPPL +0.17%, top-1 99.118% = X/X. Box V5I-SERVED-27B ticked (pipeline) + receipt-ack. C17 fold candidate.

### What cracked it
| Lever | Evidence | Effect |
|---|---|---|
| Stage-contiguous in-place weight repack | 0689c70ee | +13-26% op bandwidth |
| Q8MF V5 kernel: 4 WG/CU at 118 VGPR, half-tile units, atomic tail, nontemporal (slc) loads | fork 1778cda76, boxes 1ad781e58/568f36302 | flat cost n1-16 (27B 34.3/37.8/40.0/41.7 ms at p1/8/12/16) |
| V6 3-stage prefetch (128 VGPR) | 4180a4b8a | NO_GAIN: prefetch depth is not the limiter |
| Packed consumers | 60c2d7397 | packed prefill convert fold-ready (p512 0.999x X); packed n1 MMVQ slower -> MMVQ_MAX=0 default |
Bandwidth: stream ceiling 1498 GB/s (MI210 peak 1.6 TB/s); best op V5I-slc 1205 GB/s = 80% of stream.

### Trees
- DTREE-ROUND-OVERHEAD (f3d9bc5a0, f468e6f57): extra per-round cost is state-save copies (GDN tree snapshot scatter 3.85 ms, conv per-column copies 3.3 ms), not verify GEMMs. Fixes 5916360ea + efaecfc5d: G12/L 0.920 -> 0.972 [0.949,0.994]. New box DTREE-ROUND-OVERHEAD-2 for the remaining ~4.5 ms.
- Greedy rows (fixed builder): 27B G12 mean len +16.4%, G16 +19.7%; measured tree acceptance 27B +5.8% at T12, +11% at T16. Round overhead is the blocker, not acceptance.

### Kernel and Q38FN levers
- H11-UNIQ FAIL(dup_ids) (96dec22d5): topk-moe fusion router emits duplicate ids on exact ties; new box AK-ASM-H11-UNIQ-FIX, fix in flight.
- DRAFT-HEAD-APPROX-RECALL r2q0 PASS (630e1275d) with faithful-arithmetic recompute (e06dcc3c9); DRAFT-HEAD-SVD-CPU built (b5d6a32a6), row r2q0 queued.
- LSA-CPU e2e build + tests PASS; row lsa-cpu-sparse-e2e-20261121-r1 queued.
- chainverify r3 (V5I) KEEP: 27B MF/OFF M4 0.788 [0.780,0.796] (r2 had silently run V3I).
- sclk-detm FAIL (5b4bb6ace, fixed clock -8.1% pp2048); sclk-energy NO_WIN (45d903ef8).
- H15 np2 fallback cheap (4ebce70c7, +0.49%); AK-GAP-1 step1 PASS (0a3c03958).

### Pipeline / keeper fixes
any-of region granting, pid-based waiters, rowflow release verb (466e6b97a), q3 build pocket.

### Process lessons
- 4 GPU rows silently failed smoke and never queued -> smoke-FAIL watcher (watch FAIL-*.json, not only .ended).
- Job stderr is tail-truncated: witness lines lost; templates must keep the first 4 KB too.
- A subagent claimed chainverify-r2 ran V5; job.py said MF=3 (V3I). Verify on disk, never on report.

### Boxes
Ticked this wrap-up: AKX-ALL-31.QDEC-CPU-MULMAT. Receipt-acks: V5I-SERVED-27B, DTREE-ROUND-OVERHEAD. Filed: AK-ASM-H11-UNIQ-FIX, DTREE-ROUND-OVERHEAD-2.

## Wrap-up 11 (overnight results, 04:00Z-11:30Z)

### Verdicts filed
| Row | Verdict | Key numbers |
|---|---|---|
| ak-h11-uniqfix-gpu-20261121-r4 | PASS (box AK-ASM-H11-UNIQ-FIX ticked by coordinator, d147db5e2, with C17-FOLD-LEDGER item 8) | unique ids 48/48 on HIP and asm paths, asm kernel ran, speed 0.999. r1 FAIL = witness read ids view flat; r2 real asm-only defect (all -inf rows repeat last idx); r3 "fix" bypassed asm (fix_asm_ran=false, 0.967 speed FAIL) |
| ak-gap-1-idsort-step2-gpu-20261121-r3 | KEEP (AK-GAP-1-IDSORT ticked earlier) | A3B-mtp e2e 1.138 [1.104, 1.173], TOP_K op 1297 -> 26 us, oracle 467/467, 27B-dflash2 identity 4/4 |
| ak-gap-1-sample-gpu-20261121-r3 (device accept) | NO_WIN, filed inconclusive | 27B 1.027 [1.007, 1.047] (CI-lo misses 1.0084), A3B-decode 1.013, A3B-mtp 1.006. r4 27B-only 8-block confirm smoke PASS, ready; box AK-GAP-1-SAMPLE stays open |
| ak-v5i-27b-dflash2-np2-gpu-20261121-r2 | KEEP (V5I-SERVED-27B-NP2 ticked 95de92167) | 1.161 [1.137, 1.186], oracle 0/96 |
| ak-a3b-nondet-gpu-20261121 | filed | no knob (all0 included) makes A3B deterministic; repeats within one launch also vary |
| ak-draft-head-svd-cpu-20261121-r3q0 | KEEP | Q38FN CPU MTP D1K +7.79% [2.73, 12.92], acceptance 0.683 -> 0.720; D32K +1.75% n.s. |
| Q38FN drafter window 8192 | FUTILITY_ACCEPT_FAIL | 32K +7.5% n.s., 64K +10.9% n.s.; acceptance 0.76 -> 0.71 (32K), 0.53 -> 0.45 (64K) |
| idxk-cache r2 | FUTILITY_NOT_ENGAGED = witness defect | library INFO maps to TRACE; r3 adds -lv 4 |

### Dtree
Greedy G12 beats the chain on V5 (1.0266 [1.0100, 1.0432], mean len 5.448 vs 4.637, round cost 1.144 vs break-even 1.175); G16 0.997 and T16 0.959 do not. A3B V5I 0.988 (keep A3B on the X route).

### C17
Operator asked for C17 combined as soon as H11 + device-accept landed. H11 r4 PASS is in; C17 fold/build agent dispatched with device-accept default-off (r4 confirm decides only its default). Fold conditions: GGML_HIP_Q8IP_MMVQ_MAX default 0, V5I on 27B only, TOPK_FAST, packed prefill convert.

### Process lessons / bugs
- Cloning a row: regenerate SOURCE.sha256 (lsa-r2 failed twice in 5 s with no log).
- Keeper max_hold 7200 s cap ignores min_window: c16-fold-cpu refused twice, lsa r1 granted 7260 s vs min-window 12500 (rc=12). Reported to Pipeline.
- Quiet-guard quarters flagged UNDERUSED: Pipeline adds spec field quiet_guard_regions; declare on CPU rows carrying a probe once live.
- Disk pause 06:1x (165G free < 180G resume), keeper vault-churn bug: purge + keeper swap need operator approval.
- One agent ran job.py unbooked ~06:05-06:07Z on CPUs 24-71 (no contamination); another touched MI210 outside a grant.

### Boxes
Ticked by coordinator before this wrap-up (not re-ticked here): AK-ASM-H11-UNIQ-FIX. No new ticks from this wrap-up. Previously ticked: V5I-SERVED-27B-NP2, AK-GAP-1-IDSORT. Not ticked (verdict not final or box has unmet arms): AK-GAP-1-SAMPLE (r4 pending), Q38FN-DRAFT-FA-W8192 (adaptive arm unrun), LSA-CPU-SPARSE-E2E (row running/queued). DRAFT-HEAD-SVD-CPU box: not found in handoffs by id, verify owner at next boundary.

### Journal
Durable insights appended to epyc-inference-research `scripts/kernel_rnd/autokernel/loop/program.md` (new "Learnings 2026-11-21 (overnight ...)" section, also covering H11 witness and asm-post-pass lessons).
