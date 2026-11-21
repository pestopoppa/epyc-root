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

## Wrap-up 12 (11:30Z-22:00Z)

### C17 gates (composite ed5d94969, fixed build 1b83c6967)
- **Regression found and fixed.** The device-accept lazy-logits download (default ON) fired on the first ubatch of a multi-ubatch decode, so `logits_lazy_flush` read a stale or rebuilt `t_logits` and hit an OOB assert. It killed the CH33 CPU gate and the np4 A3B server smoke, and any multi-slot llama-server on C17 could abort. Fix `1b83c6967`: lazy only on the last ubatch, flush before a graph rebuild; `test-device-accept-multiseq` fails on old code and passes on new. Lesson: a single-stream KEEP (device-accept r4 tested np2, not multi-ubatch) is not a multi-slot safety proof.
- **CPU r2 PASS.** **GPU r3 PASS**: served tok/s +11/+17/+4.5% (+10.7% geomean). Spec-vs-nospec greedy agreement is 229 chars for C17 vs 44 for C16, so C17 is more faithful; the acceptance jump (P3 0.69 to 0.87) came from non-knob code (likely the H15 alias fix), and C16's spec was diverging early. The per-step rule (r2) had FAILed it on 0.9918 and P3 0.943.
- **A3B r4: quality PASS** (A/A-anchored; the r3 dPPL 0.66% was inside the 0.44% A/A plus noise), mtp +11.0% PASS, decode PASS, **np4 0.982 [0.960, 1.005] INCONCLUSIVE** (not from device-accept, which helps np4 by +3%). Promotion is the operator's call. The gates ran code defaults with no served-recipe env, so V5I (MF=6) speed is not in them.
- Process: c17-fold-a3b r3 failed once on a stale gpu_common.py pin; when editing a pinned helper, update its sha in job.py and regenerate SOURCE.sha256.

### Replay and cache keeps
- **RS-REPLAY (GDN replay) R5 KEEP**: 27B DFlash2 np4 server-side ms/target round -7.7% [0.919, 0.927], so +8.6% decode; RS buffer -85% (4788 to 707 MiB); np1 neutral via auto mode `090d6c304` (`LLAMA_RS_REPLAY=1` replays only when n_seq_max > 1; 2 forces). np1 replay adds about 1008 graph nodes, +1.2 ms/round; at np4 snapshot bytes are 4x, so replay saves 9.5 to 10.9 ms/round. Gating lesson: wall-clock np4 tok/s on the MI210 has A/A of +-12 to 25% (noise is in the request/slot path), while ms per target round from print_timing has A/A +-0.5%.
- **Replay correctness cleared** on GPU (device bitwise 50/50; A/A divergences 9 vs replay 6; 0 hard) and CPU (r3: single-slot mismatches A/A 7 vs ON 6; the earlier 5/12 was CPU multi-slot nondeterminism; rounds -7.6%, RS 2251 to 502 MiB). Op-level: np4 8 rows 425.6 to 146.5 us (2.9x), 16 rows 998 to 269 us (3.7x). RS-REPLAY-PORT ticked earlier.
- **idxk-cache r4 KEEP** (fork 7ff5f23ad, `LLAMA_QSA_IDXK_CACHE`): Q38FN CPU +7.05% at 32K, +12.63% at 64K, neutral at 1K, acceptance identical.

### GAP2 and gap-1
- **q81-reuse KEEP**: A3B-mtp +3.0% [1.4, 4.6], identity clean. **topk-moe-multirow DROP(op)** 0.89x (one block serializes rows). **q8wv-fuseq DROP(op)** 0.33x (every workgroup re-quantizes the activation). 27B q8wv quantize-once reuse: recoverable only 0.46%, stopped before build. Lesson: reuse wins, in-workgroup fused quantize loses.
- **stoch-accept**: STOCH-CENSUS PROCEED (27B temp-1 recoverable 11.8% of decode, host 10.4%). r1 FUTILITY_IDENTITY (seeded temp-1 is not launch-deterministic on the MI210); r2 about 3-6% slower because K=32 fell back to the radix top-k (fast path only for k<=16); fix `2c032ddf3` (TOPK_FAST=32 wide path) plus K=20 default `4a9ca940d`; r3 about +0.8% per round (at floor, only ~7% of the bound captured). Kept as an enabler: prerequisite for a device-resident spec round and temp>0 tree verify.

### Weight streaming (WSTREAM)
- Entropy census PASS: net saving 5.0% on 27B, 5.4% A3B, 5.0% drafter; fp16 scales carry about 45% of the headroom. CPU decode ubench: per-code schemes (static, split, tANS, 32-lane Huffman) fail by 4-23x; `scales_only` passes the rate gate (16.2 GB/s vs 5.3 needed) but its about 3% saving (27B 3.05%, drafter 3.00%, A3B 2.69%; ceiling 5.9%) is below the CPU floor. GPU budget: scales-only about 0.4 op/B vs 6.3 available (15x headroom), so **scales-only is the GPU route** (box WSTREAM-SCALES-Q8-GPU, 27B first). Correction recorded: 27B is not CPU-served, so a CPU lever on it was meaningless.

### Other results
- **KPF-64 snapslot copy**: implemented (fork a9a4be93f / 5b36f52f5, `LLAMA_SNAPSLOT_CKPT`); CPU restore row **EQUIVALENT** (copy == cut within the ubatch-split floor). 27B GPU row pending (smoke hinted a loss: prefill ON 0.61, KLD 0.00326 > 0.003, likely warm-up order). DFlash/EAGLE/draft-model drafters refused. KPF-64-SNAPSLOT-COPY NOT ticked.
- **EPI-Q8 already dropped** (r3 27B decode 0.9959, -0.4%, engaged, identical); not ported to C17.
- **DF2-13 re-judged near-tie**: the REAL label was a rule artifact (three-way near-tie, top-2 test too narrow); floor flips come from drafter trajectory differences across launches. DF2-13-ATTRIB bisect published at priority_rank 60.
- Q38FN CPU: round-host off-model share 0.84% (D1K) and 0.55% (D32K), so no host lever; draft-depth r2 NO_GAIN (n6 +3.6% n.s., n8 -13%); draft splitKV r4 DROP by rule (acceptance -0.033, content differs) despite +10.9% tok/s (draft FA -46%), worth a follow-up with an A/A content floor; smallm-verify r1 FUTILITY_WRONG_GRANT, r2 published. Q8PK-DECODE-OPBW: dense Q8_0 decode reaches >= 85% of stream bandwidth, no VNNI GEMV lever.
- mtp-degen FUTILITY_NO_DEGENERATE (needs a real archived degenerate request). Q38FN nondet row fixed (`-b 512 -ub 1`). asm-t1-harness-r3 INCONCLUSIVE (AITER JIT compiled in-grant, ~1 h GPU wasted; pre-build the JIT first, priority_rank 900). EA-POOL-SCREEN est 109000 s, lowest filler.
- Operations: v10 disk pauses at 165G; E5 r7 owns the host about 02:00-08:00Z; rowflow resume live; priority_rank field (default 100, lower = higher, 900 for pure fillers). Lesson: refill the GPU queue from owned boxes BEFORE it drains.

### C18 fold candidates
All KEEP and not in C17: (1) RS-REPLAY auto (`090d6c304`, on fork a0c22f414 lineage; condition on n_seq_max); (2) idxk-cache (7ff5f23ad); (3) GAP2 q81-reuse (`GGML_HIP_Q8_1_REUSE_BATCH`, fork ak-gap2-levers-20261121); (4) SVD draft head (DRAFT-HEAD-CPU-IMPLEMENT KEEP, default-off `LLAMA_MTP_DRAFT_HEAD_SVD`); (5) stoch-accept enabler fixes (TOPK_FAST=32 wide path 2c032ddf3, K=20 4a9ca940d) as a knob, about +0.8%; (6) KPF-64 snapslot copy once the 27B GPU row clears. Not candidates: draft splitKV (DROP), EPI-Q8, multirow, q8wv-fuseq, nta (unfinished).

### Boxes
Ticked (verdict filed, own done-when met): AK-GAP2-Q81-REUSE, AK-GAP2-TOPK-MOE-MR, AK-GAP2-Q8WV-FUSEQ, C17-FOLD-GATES, WSTREAM-DECODE-UBENCH-CPU, Q8PK-DECODE-OPBW, Q38FN-CPU-DRAFT-DEPTH, Q38FN-DRAFT-SPLITKV (r4, 48t), AK-GAP-1-STOCH-CENSUS. RS-REPLAY-GATE-R5 was already ticked. Left open: RS-REPLAY-GATE-R3 (verdict NOT_JUDGEABLE; belief-capture refuses it, superseded by R4/R5), RS-REPLAY-GATE-R2 (verdict is FUTILITY_BELOW_BASELINE, not in its done-when set; superseded by R3-R5), Q38FN-INDEXER-TOPK-CPU (audit says remaining work: tie-order-exact top-k and cached RMS_NORM), KPF-64-SNAPSLOT-COPY (27B GPU row pending), idxk-cache (no handoff box carries it).

### Journal
Evening durable insights appended to `scripts/kernel_rnd/autokernel/loop/program.md` ("Learnings 2026-11-21 (evening)").
