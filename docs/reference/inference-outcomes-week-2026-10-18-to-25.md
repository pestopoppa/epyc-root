# Inference outcomes, week of 2026-10-18 to 2026-10-25

Compiled 2026-10-25 by workspace-58 (subagent) from origin/main `c106003a7`. Read-only research; no compute was run for this document.

**Scope and honesty notes.**
- Every number below is copied from a source; none is computed here. Grades are the sources' own words: "observation" means single-run or unpredeclared; INDICATIVE, sign-only and PARTIAL are kept as written and are not wins.
- Citation key: `P:` = `progress/2026-10/`, `AGG` = `handoffs/active/autokernel-champion-aggregate.md`, `CAL` = `/mnt/raid0/llm/tmp/compute-calendar-20261021.md` (REVISION log), `FIL` = `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`, `RES` = `epyc-inference-research` `data/`. Line numbers were taken from per-file extraction passes; a few are approximate (marked `~`). The task text, not the line number, is the identity.
- Coverage is partial. Of 140 COMPLETE filler rows, the verdicts for `kpf13-1-reduced`, `kpf17-4-19-1a-27b-dflash2`, `gpu-zos-1a` (progress file gives spec-on 4.15% vs spec-off 1.48%, INDICATIVE), `kpf18-s1` and `ufh14-lb7` were not located in the calendar. The handoff tick pass used commit subjects, so some ticked boxes are unlisted. The belief ledger was not consulted.
- Dates are 2026-10-xx.

## Executive summary

1. **The champion line moved C2 to C5 in three days, all CAS-recorded.** C2 `49550eda5` (10-23), C3 `dcc853b55` (10-24), C4 `cdb4d8c77` and C5 `c72ec82f5` (both 10-25 about 08:23Z). C3 carries the YaRN K-shift fix, C4 the GPU HIP-graph leak fix (leak slope 0.0 MiB/request versus about 290 MiB/request before), C5 turns the broken fused-decode path off by default. Every gate that was predeclared passed, with one rule amended by the operator (see Section 3).
2. **Real defects were found by gates and fixed in the champion**, not in production: the fused MoE up+gate predicate never fired (so earlier "NMSE 0" was vacuous), the hybrid/recurrent cache-reuse bug, the YaRN K-shift bug, the GPU graph leak, special-token injection, and a fused-decode path that is about 20x slower and diverges at token 2. Production v10 was found NO-DEFECT as launched (FD-DIV-2).
3. **Several speed ideas were closed by measurement as not worth pursuing**: fused MoE up+gate (no cell faster), whisper threadpool co-run target missed (2.4-2.5x vs 5x), GSQ IQ3_XXS fails all strict quality bars, Q38FN arm P2 fails speed, the 7b AK "+4.73%" keep did not replicate, chunk-KV real-role gate failed on reference drift (since fixed in the gate), per-thread width does not help Q38FN decode. These are re-run preventions.
4. **A few measured wins are real but modest or indicative**: qwentts co-run 11.3x to 31.6x faster beside spinners (champion only, not promoted); KPF-18 item 7 fan-out TTFT about 8.5x (candidate grade); Q38FN CPU +3.63% on C3 (sign-only, no floor); DS41-1017 noise floor 2.862% stands for `dd3d9721c`; the serving gate Q38-T10.1 PASSED with R=0 G=0.
5. **A large share of the week's compute produced nothing usable**: INVALID anchors (C2 b-rerun runs 2 and 3), a VOID headline (-12.821%), a mid-week DS41-1017 vs Sept comparison declared permanently invalid, midnight-boundary queue bug, wrong region-lock argv, SIGPIPE `grep -q` false failures, a 10-25 whole-host window where two llama-bench runs measured nothing, and idle CPU/GPU episodes. Section 5 lists them.
6. **Open and honest gaps**: Q38FN floors were superseded by C2/C3 and CH-27 recalibration is on operator hold; the batched-decode batch-invariance defect (CH-31-DEF1) is open on C3 and C5; the YaRN native gate is only NOT-FAIL-underpowered; Skill-Inject showed no worker benefit (DP-G hold).
7. **Infrastructure gains**: reusable deterministic fold gate (CH-28), `grant_ok` v2, the `inference-backlog-scheduling` skill, fail-closed AK op-suite keep gate, AK in-flight keep evidence now travels on `run_aborted`, and the pipefail/`grep -q` false-result class was exposed and fixed in several launchers.

## 1. Measured wins (and positive results with their grade)

| Item | What improved | Number (unit, baseline) | Verdict class | Date | Evidence |
|---|---|---|---|---|---|
| CH-30 / C4 GPU-LEAK-1c-V | HIP graph stale-exec leak fixed | slope 0.0 MiB/request vs 290.27 MiB/request defect (E1); decode tps +0.08% | VALIDATED (folded as C4) | 10-23/25 | AGG:106,108-111; `P:2026-10-24-3c4ca599.md:68` (0.0 MiB/req PASS) |
| C4 gate-e quiet re-run | no regression C4 vs C3 | pp +0.58% (floor 2.12%), tg -0.00% (floor 2.00%), identity 15/15 | PASS | 10-24 | `P:2026-10-24-workspace-58.md:161-164`; AGG:108-111 |
| C3 gates (G-e / G-bc) | YaRN fix folded without regression | 27B DFlash2 A/B identity 15 pairs, pp -0.21% / tg -0.07% inside floor; Q38FN CPU 49.18 to 50.96 tok/s (+3.63%, 5 pairs, no floor) | PASS / IDENTICAL; the +3.63% is sign claim only | 10-24 | `P:2026-10-24-workspace-58.md:11,13`; CAL:389,395,398 |
| C5 gates | fused decode off by default | G2-CONC 8/8 PASS (see Section 3 for the amendment); c5-gate-b anchor 51.45 vs 51.03 tok/s = -0.810%, floor None | PASS; -0.810% sign-only/informational | 10-24/25 | AGG:74,116,120-122; `P:2026-10-24-3c4ca599.md:67` |
| Q38-T10.1 serving gate | spec-off bitwise path | GPU R=0 G=0 n_clean=78; CPU R=0 G=0 n_clean=80; one-sided p=1.0; strict reading 3.77% upper bound | PASS (predeclared Net-paired rule) | 10-21 | `P:2026-10-21-runner-3c4ca599.md:6` |
| Bundle item e GPU A/B (dd3d9721c vs C f0c96dc1f) | no GPU regression | pp -0.99% / tg +0.27% inside 2.00% / 2.75% floors; identity true | PASS | 10-21 | `P:2026-10-21-runner-3c4ca599.md:5` |
| Slotdraft fold dd3d9721c | MTP acceptance after slot restore | 0.98-1.02x live vs 0.53-0.71x before | folded (operator) | 10-20 | `P:2026-10-20-workspace-f8.md:6,12` |
| Speech threadpool (qwentts b1a1ec7) | TTS beside CPU spinners | co-run 11.3x (+1 spinner), 20x (+8), 31.6x (+real llama-bench neighbour, which got 28x more throughput); quiet within A/A; greedy identity 10 texts + 10 clips; FLASH_ATTN_EXT 5097/5097 and 9219/9219 | PASS for qwentts; speech champion only, not promoted | 10-21 | `P:2026-10-21-qwentts-threadpool.md:12-13` |
| KPF-18 item 7 (MI210 4-way fan-out TTFT) | fork on vs off | fork_off 1312.9 s / 1404.0 s to fork_on 169.3 s / 140.0 s (~8.5x); aggregate decode 3.40/3.32 to 26.5/32.1 tok/s | CANDIDATE grade, A/B/A/B (observation) | 10-21 | `P:2026-10-21-workspace-f8.md:84` |
| KPF-64 (8 arms) | checkpoints close the prefix-hit gap | A realised 90.2% vs ideal 93.9% (gap 3.7 pp); B/C/D gap 0.35 pp; contrast -3.43 pp [-5.43,-1.92]; RAM tier adds nothing at 4 lineages; fan-out not exercised | REAL, pass 2 replicates; KPF-64 ticked | 10-24 | `P:2026-10-24-3c4ca599.md:15`; commit 1ee45b94a |
| DS41-1017 noise floor | process-unit floor for `dd3d9721c` | 2.862% (interval 1.974-5.757%, 24 A/A pairs, k=5, 7394 s); sensitivity variants 2.33-2.55% | STANDS decision-grade; valid for `dd3d9721c` only (superseded by C2/C3 changes) | 10-22 | `P:2026-10-22-workspace-f8.md:17-18` |
| DS41-1017 W5 correctness | load and quality vs Sept Q4 | ppl 2.6675 +-0.0675 vs 2.6122 +-0.0655 (+2.1%, within 1 sigma); paired coherence 0 regressions | PASS (but the later speed comparison is invalid, Section 5) | 10-21 | `P:2026-10-21-ds41-w5.md:14-16` |
| KVU-19b-fold-c1-p3 | `-kvu` vs `-no-kvu` batched decode | S_TG delta -0.94% (pairs +0.39 / -2.27%); mean 55.933 vs 56.466 t/s; v1 reference -15.23% | WITHIN_5PCT, INDICATIVE (ABAB n=2) | 10-25 | `RES:data/kvu19b-p3/VERDICT.json`; `P:2026-10-25-workspace-58.md:83` |
| U4-NOISE-W2 (GPU 27B decode co-run with Q38FN whole-host CPU) | co-run effect | decode -0.55% [-2.01,+2.30], prefill -1.11% [-2.34,+0.83]; A/A tg 0.90%, pp 0.74% | CO-RUN-OK; W1 transfer UNRESOLVED (VR upper 2.45, not <2 at n=5) | 10-23 | `P:2026-10-23-workspace-58.md:51-58`; CAL:269 |
| exl3-6c5-quality | EXL3 3.05bpw (E) vs UD-IQ4_XS (U) PPL | 2.8909 +-0.05905 vs 2.9925 +-0.06315 (-3.395%, wiki.test.raw c512 x40) | QUALITY_NOT_WORSE (PPL only, no speed figure); smoke FAIL on p1 | 10-25 | `RES:data/exl3-6c5-quality/VERDICT.json` |
| NEW-13 weight handoff (UD-IQ4_XS prefill to GSQ IQ3_XXS decode) | KLD gap recovery | R=0.2828 [0.2458,0.3219]; KLD A 0.213 / B 0.153 / C 0 / D 0.101; 0 coherence regressions; GSQ decode ~28% slower (descriptive) | PASS (quality recovery, not a speed win) | 10-23 | CAL:276; `P:2026-10-23-workspace-58.md:71-72` |
| AK ranked recall default | planner calls with no measured answer | 81.2% (recency) vs 1.6% (ranked) | KEEP, default ON by operator | 10-20 | `P:2026-10-20.md:61-62` |
| AKX-ALL-26 CPU width-invariance | which kernels vary with batch width at k=2 | `GGML_IQK=1` variant for MUL_MAT Q8_0/IQ2_XXS/IQ2_XS/IQ3_XXS/IQ3_S and F16-KV FA; Q4_K/Q3_K/Q6_K/IQ4_XS pass; `GGML_ROWEXACT_N=9` makes all 9 pass; 4,761 cells, 0 A/A-unclean; 63/66 predictions confirmed | finding (HIP half open) | 10-20/22 | `P:2026-10-20.md:50-52`; `P:2026-10-22-akx26-cpu-wire.md:4` |
| Smaller PASSes | GPU builds and probes | m4-srpf 10/10, spec-rng-1-2 9/9, ufh14-lb7-1 11/11 builds; HIL-16a 80/80 clean recordings (11 failed-task recordings, min 3); p1-phase2 148 rows 0 refused; akx-lb4-followups-3 36/36; FD-DIV-1a byte-identical (unpatched v10 still aborts rc 134) | PASS | 10-22..24 | CAL:299,303,349,353; FIL |
| g1_cascade_language (speech) | WER | tts_rt WER en 2.73% / it 2.55%; real-audio STT en 4.76% / it 2.64% | done; Italian listen check owed | 10-21 | `P:2026-10-21-runner-3c4ca599.md:15` |
| CS-8.L Italian listen (60 clips) | intelligibility | 60/60 intelligible, naturalness mean 4.62, median 5 | weak ASR agreement (Spearman -0.14, p=0.21); Italian not rejected | 10-22 | `P:2026-10-22-cs8l-ratings.md:3,6-7` |

## 2. Decisions settled by measurement (including NO-GO, negative and NO-REPRO)

| Decision | Evidence (number, unit) | Verdict | Date | Source |
|---|---|---|---|---|
| Fused MoE up+gate (CH-19): no speed gain | ON/OFF medians pp512 d0 0.9850, tg128 d0 0.9958, pp512 d8192 0.9901, tg128 d8192 0.9755; 0 invalid arms | not faster on any cell | 10-21 | `P:2026-10-21-workspace-f8.md:96` |
| Fused decode path (qwen4exp): defect lives in the champion, not production | fused path ~20x slower, diverges at token 2 (C5 gate ~24x slower); v10 production NO-DEFECT as launched | FD-DIV-2; fix = C5 default-OFF | 10-24 | AGG:117; commits 958b777f7, 585afc39a |
| GSQ IQ3_XXS serving quality | G1 ln-PPL ratio 0.0150 +-0.0100 (bar <=0.005); G2 mean KLD 0.322 +-0.007 (bar <=0.1045); G3 same-top-1 82.9% +-0.4 (bar >=88.55%); recapture identical (0.0215 / 0.3206 / 82.77%) | VERDICT FAIL; arm closed for serving; operator KEEP weights (NEW-13) | 10-22/23 | CAL:220,223,279; `P:2026-10-23-workspace-58.md:91-93` |
| Q38FN arm P2 (IQ4_XS experts) speed | decode -8.9%, pp5 -6.1%, pp256 +31.9%; PPL 2.9868 vs 2.9790 | speed FAIL (INDICATIVE); P2 does not ship | 10-25 | CAL:661; `P:2026-10-25-workspace-58.md:6-7` |
| Q38FN arm P v1/v2 | v2 PPL 2.9743 vs UD 2.9868 (-0.42%); pp256 +29.5% (3/3), pp5 -7.4%, tg128 -17.0% (0/3) | v1 NO-GO was a coherence harness issue; v2 GO on quality, speed FAIL (INDICATIVE); GGUF trashed | 10-24 | CAL (10-24 block ~460s) |
| 7b AK iteration 3 (query-major row schedule) | +4.73% 64k decode over 5 pairs (floor 1.365%) did NOT replicate: replicate -1.10% decode / -1.34% prefill | DISCARD; champion stays `dd3d9721c`; keep never recorded | 10-22/24 | CAL:205; `P:2026-10-24-workspace-7b.md:9-12` |
| Whisper threadpool co-run target | co-run total latency 2.4-2.5x vs predeclared >=5x (decode phase 13-34x; encoder compute-bound) | MISSED (correctness and quiet PASS); CS-50 owns follow-on | 10-21 | `P:2026-10-21-qwentts-threadpool.md:12` |
| Q38FN thread count / depth | tg128 t48 31.2 vs t96 24.8 (-21%); served decode with MTP shows no thread effect at >=32k; decode -55% and prefill -60% shallow to 128k | observation; lever is attention kernel / QSA, not threads | 10-20 | `P:2026-10-20.md:7,10,11` |
| Q38FN prefill `-tb96` | served 4k-tail prefill 198-211 vs 164 t/s (+21-29%); llama-bench pp512 t48 212 / t96 231 (+9%) | observation (within ~7% drift from 8k up) | 10-20 | `P:2026-10-20.md:7,9` |
| DF2-19 corpus-table n-gram replay | (a+b) over (a) -0.00%, (a+c) over (a) -0.04% vs GO bar >=+3.0% | STOP | 10-20 | `P:2026-10-20.md:73-74` |
| Q38-T9 per-class DFlash2 vs no-draft | token-weighted ratio code 2.667, reasoning/math/sci 2.021, instr/prose/chat 1.476; no class <1.0 | no A/B needed (replay) | 10-20 | `P:2026-10-20.md:46` |
| Q38FN IQ4_XS-uniform retired | all INF-70 CPU-decode headlines (23.16, 33.370, 43.281/27.893, 52.661, 52.7 t/s) were on the retired file; UD +40% bytes/token | headlines carry an epoch caveat | 10-20 | `P:2026-10-20-retire-iq4xs-uniform.md:29-35` |
| REPL-EMB-2.2 | kill-rule FAIL as extension-only; EG2 BF16/FP16@256 + BM25 hybrid adopted | decided | 10-20 | `P:2026-10-20-main-3c4ca599.md:30` |
| GRAM-LAZY-1 | task pass off 66.7%, legacy 40.0%, call 36.7%, lazy-legacy 3.3%; off vs legacy +26.7 pp CI +10 to +46.7 | KEEP_LEGACY; UFH14-LB3.1b off: REMOVE_GRAMMAR | 10-23 | `P:2026-10-23-workspace-f8.md:165-171` |
| CT-18 Skill-Inject | n=316: no worker benefit, worker harm under B; IB2 strongly favours B/C | DP-G hold (no prompt change) | 10-22 | `P:2026-10-22-ct18-final.md:4-5` |
| Nemotron 3.5 vs Parakeet v3 (FLEURS WER) | fr 10.78 vs 5.30, de 10.33 vs 5.24, it 5.78 vs 3.02, en 7.99 vs 4.83 | Nemotron NOT more accurate | 10-22 | `P:2026-10-22-3c4ca599.md:66` |
| PB-HOL-1 (slot-order head-of-line blocking) | off arms B/A 22.05 (A 3217.5 ms, B 70932 ms); budget-on B 83352 ms (23.2x) | CONFIRMED; prefill budget does not relieve it (confounded by -b/-ub); M4 ordering fix filed | 10-21/22 | `P:2026-10-21-workspace-f8.md:85`; `P:2026-10-22-workspace-f8.md:7` |
| KVU-12.1b at 32k | coarse checkpoints 534 vs 735 MiB/seq (-27.3%) | REPLACES_DENSE at 32k | 10-23 | `P:2026-10-23-workspace-f8.md:30` |
| KVU-12.3 | generated-span re-prefill 4.52% vs predeclared 5% | CLOSED NOT NEEDED | 10-24 | `P:2026-10-24-workspace-f8.md:259` |
| KVU-12.4 np4 L64k ABA | unified -22.78% decode sum vs 12.48% anchor floor | NO_DIFFERENCE (weak, PROPOSED-until-ratified) | 10-22 | `P:2026-10-22-workspace-f8.md:10` |
| DF2-LB1 ubatch census | 25/721 verify calls fragment (3.47%) | FRAGMENTS_RARELY | 10-23 | `P:2026-10-23-workspace-f8.md:31` |
| inf42-g1-gpu | 100% recall 50/50 at 4K/32K/64K/128K, 9/9 at 256K; f16 control 100% | FINAL GATE CLOSED (ceiling) | 10-24 | `P:2026-10-24-3c4ca599.md:43` |
| inf48-g10 case 25 | v10 FP16 CPU reference ERR 5.15-5.28e-4 vs 5e-4; FP32 reference 22/22 OK | CPU-reference artifact, not a GPU defect; not re-queued | 10-24 | CAL:~360-380 |
| GPS-PIN P1 | `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` keeps 196/196 llama-server tasks on 184-191 | PASS | 10-23 | `P:2026-10-23-workspace-58.md:29` |
| Fork vs prompt-cache (f8-fork-repro) | `slot_fork` == prompt-cache hit; KPF-13.1 1-token divergence = CPU batch-shape numerics at near-ties | FORK CLEARED | 10-22 | CAL:136 |
| SPEC-RNG.1.1 / 1.2 | np1==np4 and depth0==depth3 identity 7/8 and 6/8 differ; cause CPU batch-shape logit drift, not RNG; 1.2 probe 0/48 | DO-NOT-CARRY | 10-22/24 | `P:2026-10-22-workspace-f8.md:48`; commits 3837a842c, 1efcf20c9 |
| YaRN native gate | 18 pairs, 2 discordant (b=1,c=1); FAIL needs >=5 losses with 0 wins | FINAL NOT-FAIL, underpowered (not a pass) | 10-22/23 | `P:2026-10-22-yarn-gate-power-note.md:3,9`; CAL:270 |
| HIL-15a flag-on live | 54/56 pass; AUC table INSUFFICIENT | null (task set too easy) | 10-22 | `P:2026-10-22-3c4ca599.md:177` |
| CME-5 / CME-7 gate | hit_ratio_reusable 0.7948 vs gate 0.95; perfect layout would give about 0.91 (generated tokens not reusable) | MISS (valid run); gate basis amended to prompt_prefix before rerun | 10-22 | `P:2026-10-22-cme7-cache-miss.md:8,30` |
| DS41 test scope | operator: disregard all DS41 tests except the noise floor until AK kernel work | rows ds41-w51a-ab, ds41-t32-kvfq, ds41-t71a-drafter-timing CANCELLED | 10-22 | CAL:112 |
| HIL-6 pilot cost | HIL-6j as wired needs about 232-300 whole-host hours | redesign package filed | 10-22 | `P:2026-10-22-hil6-pilot-redesign.md:3-5` |
| V11-086 B-stall diagnosis | tg32 @ d32768: C 8.450 t/s (400 s), B 8.917 t/s (1449 s); wall_ratio 3.62 | GRAY-2-5X: slower by measured ratio, not stalled | 10-25 | `RES:data/v11-086/b-stall-diag-20261025/VERDICT.json` |
| AKX-ALL-30a arbiter (MI210, C3) | FA fetch/view R = 1.727 / 1.729; convert 7.87 / 7.95 ms/step | PARTIAL_REREAD; G3_STANDS (seed order G3 first) | 10-25 | `P:2026-10-25-workspace-58.md:81`; CAL:666 |
| M4.2a | C2 median ratio 25.227x vs band 19.845-24.255 | FAIL; M4.2b filed (paired P=0.9984, C2 ~22.01 in band); M4.2 INCOMPLETE | 10-24 | `P:2026-10-24-workspace-f8.md:239` |
| tiled FA probe | decode medians N1@8k +1.38%, N5@8k +0.86%, N1@32k +1.05%, N5@32k +14.1% (one noisy pair); none reached -1% | observation | 10-23 | `P:2026-10-23-workspace-f8.md:181-183` |
| DS41-C112 c4 bisect | `9b148baab` BAD (-23.4%, -24.8%); `ad8979943` GOOD +1.1% | low strength (n=1 per step) | 10-23 | `P:2026-10-23-3c4ca599.md:35` |

## 3. Folded into champion / production

Production v10 itself was not modified this week. All folds are in the champion (experimental) line; CH-24/promotion ticks await the operator at v11 promotion.

| Fold | Content | Gate evidence | Date | Source |
|---|---|---|---|---|
| C1 slotdraft `dd3d9721c` | slotdraft fold (MTP acceptance after slot restore) | see Section 1 | 10-20 | `P:2026-10-20-workspace-f8.md:6,12` |
| C2 `49550eda5` (CH-25/26) | fast-forward `dd3d9721c..49550eda5`, pushed to fork; includes CT-12.3b special-token injection fix (CT-12.4 goldens A/B 164/0) | b-rerun anchors INVALID on rules; operator waived; CAS `dd3d9721c` to `49550eda5` | 10-23 | AGG:90-93; `P:2026-10-23-3c4ca599.md:6,41` |
| C2.1 `141e4bcf5` (CH-28) | llama-bench cmd_params value-init fix (V11-103); reusable deterministic fold gate (hipdev.py code-object compare) | CH-28, 28a-c ticked; 28d open | 10-23 | AGG:83,99-103; CAL:261 |
| C3 `dcc853b55` (CH-29) | V11-100 YaRN K-shift fix | gates PASS (Section 1); CAS 10-24T07:50Z operator-approved | 10-24 | AGG:81,104; commit 6f60eef31 |
| C4 `cdb4d8c77` (CH-30) | GPU-LEAK-1c HIP graph fix (3 commits) | gate-e PASS; a0 test-llama-archs FAIL is PRE-EXISTING (META-ASSERT-1), operator ruled non-blocking; CAS 10-25T08:23:52Z | 10-25 | AGG:108-111; commit 4f47fd345 |
| C5 `c72ec82f5` (CH-31) | C4 + fused decode default-OFF (`GGML_FUSED_DECODE_ON=1` opt-in) + CH-24 debug-print gating | G2-CONC: absolute re-check FAILED (concurrent 2/3), operator AMENDMENT 9 made it relative to the champion: C5 3/5 vs C3 4/5, solo SHIP x5 identical, so PASS under the amendment (the FAIL stays recorded); CH-24 done-when 55/55 sites gated, 0 tmp files; CAS 10-25T08:24:10Z | 10-25 | AGG:74,116,120-122; commit d70dcc768 |
| Speech threadpool | qwentts `b1a1ec7`, ggml `05e1ad6c`, whisper `fa5321e4` into the speech champions | qwentts PASS; whisper target missed | 10-21 | `P:2026-10-21-qwentts-threadpool.md:12-13` |
| Pending fold | V11-098 hybrid cache-reuse fix `8b08c9f25`; V11-100 K-shift (now in C3) | server pytest not run for V11-098 | 10-21 | `P:2026-10-21-hybrid-cache-reuse-fix.md:3-6` |
| Scheduling infra | `grant_ok` v2 (research `81005bcb3`, orchestrator `26affbf8`, root `a4b17f3aa`); skill `inference-backlog-scheduling` (`2c1a698e3`, "evals 94% vs 47% baseline" as quoted in the calendar) | operator-approved | 10-23 | CAL:289,268 |
| AK keeps already in champion (per-keep screening, not additive) | e.g. akm-ds41-dense-q8-tinyblas-zmm-widen +12.175%, q4k-x4t-weight-prefetch +5.683%, gemm4xn-2x-unroll +4.535% on one serving surface, 5 pairs; DS41 campaign serving gain +7.113% (baseline at AGG:313-315, not verified here) | per-keep screening only | 10-20 | `docs/reference/kernel-manifests/llama-v11-manifest.md:46-58`; AGG:313-315 |

## 4. Infrastructure and correctness gains that came out of runs

- Fused MoE up+gate predicate was always false, so earlier NMSE 0 results were vacuous; fixed, engages on all Q4_K/Q8_0 cells, MUL_MAT_ID 815/815, FUSION 13/13, SWIGLU 24/24 (`P:2026-10-21-ch19-fix.md:6-18,25`).
- AK served-shape MXFP4 NMSE=0.0 is vacuous because test-backend-ops never allocates the CPU_REPACK buffer (`P:2026-10-21-ds41-w5ab-w62.md:13-14`).
- AK long-context identity oracle was env-less, refusing every Q38FN attention candidate; fixed (research `b27636385`, 92 tests) (`P:2026-10-20.md:15`).
- AK op-suite keep gate now fails closed; replay of 30 PASS op-unit verdicts: 28 still pass, 0 fail, 2 captures missing (`P:2026-10-21-ak-opsuite-failclosed.md:6`); AK in-flight keep evidence now travels on `run_aborted` (cause of the 10-22 lost keep) (`P:2026-10-24-workspace-7b.md:23-24`).
- Hybrid/recurrent cache reuse bug: `get_can_shift()` wrongly true; can_shift=0 on Qwen3.5-0.8B, LFM2.5-1.2B and 6 generated archs after fix (`P:2026-10-21-hybrid-cache-reuse-fix.md:3-6`).
- YaRN K-shift bug: round-trip K NMSE 8.79e-2 before; all tests <=2e-9 after (`P:2026-10-21-yarn-kshift-fix.md:3-4`).
- KPF-17.4 re-runs, after the `grep -q` pipefail false-negative fix, exposed real failures; KPF-17.1c showed all six fork failures were test defects (`P:2026-10-20-workspace-f8.md:27`; `P:2026-10-21-workspace-f8.md:41-45`).
- Four injection-path defects fixed (orchestrator `a66e4f838ec8`, 934 tests); SEC-EXEC containment 10 suites 367 passed (`P:2026-10-21-inj-fix.md:2`; `P:2026-10-21-workspace-f8.md:27-28`).
- CT-12 special-token injection open on champion, then fixed in server (CT-12.3b) and folded into C2.
- Nemotron C2 prep found a fixture generator that aborted silently (so ctests showed "Not Run"), a nonexistent `generation_settings` assertion, and a SIGPIPE bug (`P:2026-10-21-nemotron-bolt.md:13-14`).
- C3/C5 gate scripts fixed: re-exec of nonexistent `bundle_gate_c2.sh`, stale fa_nan_probe binary, false completions (rc 126 recorded as verdict), fixed in `786a30078` (`P:2026-10-24-3c4ca599.md:10,29,69`).
- V11-086 FA-VKQ integrity: 12 failures traced to the FP16 test oracle, not the REG change (REG vs C NMSE 3.3e-5 to 8.9e-5) (`P:2026-10-22-v11-086-integrity.md:3-40`).
- KPF-62.8 G1 failure was reference drift, not injection; new G1a inject vs seq_add gate bit-identical (fork `357f3117f`) (`P:2026-10-22-kpf62-fix.md:3-19`).
- KPF-64 harness: decode not reasoning-bound (predicted_n avg 119), 0.80 tok/s per slot under batch contention; fix `b93017dc9` (`P:2026-10-22-kpf64-decode-fix.md:5-9`).
- CME-7 miss causes: 52.4% client-layout schema instruction (fixed), 41.1% gate accounting, 6.5% parse-retry; `enable_thinking=False` default added after thinking consumed the token budget (`P:2026-10-22-cme7-cache-miss.md:12-15`).
- RTE-PFX thinking-off: per-request `enable_thinking:true` overrides the server default; `--reasoning off` plus a 16-token preflight added (`P:2026-10-22-rtepfx2-thinking-off.md:5-6`).
- HIL-16c recorder bugs (sorted-key replay, unrecorded REPL sub-calls) fixed (`P:2026-10-22-3c4ca599.md` findings ~62-65).
- earlyoom incident INC-20261021: 13 processes killed (3 Claude sessions) by two concurrent DS41-1017 servers; rule: one DS41-class server at a time (`P:2026-10-21-workspace-58.md:37-45`).
- Host observation: 128k prefill measured about 65 tok/s vs 195 modelled; shared-batch decode 0.08-0.12 tok/s per stream; D4 s4 cap unreachable (`P:2026-10-22-workspace-f8.md:29-30`).
- llama-bench unrequested hardened rows: 22/53 tmp jsonl files affected, AK stores 320 hardened rows all requested; llama-bench trustworthy from C2.1 (CAL:244, 261).
- Scheduling: FILLERS rule fix (ARMED must mean runnable; inf66, akx-lb3-2, hpr-b moved to BACKLOG with code-fix blockers) (CAL:668); page-cache incident 10-23 left KPF-64 arms unaffected (CAL:291).
- Smaller: INF-72 RT-1 Q38FN routing traces (27 hash-verified shards, proxy only) (`RES:data/moe-routing-rt1-q38fn-20261023/README.md`); nemo-gpu-prof rocprofv3 traces on `dcc853b55` (observation, no threshold) (`RES:data/nemo-gpu-prof/VERDICT.json`); PB-QCOST-1 frozen model held-out MAPE 12.84% (n=1) and 26.32% (n=4), refit 2.4% and 3.83%, confirm run q axis PASS, INDICATIVE (`P:2026-10-22-workspace-f8.md:8`; commit 7d76d190e).

## 5. Runs that produced no usable result

| Run | Cause | Source |
|---|---|---|
| DS41 C vs champion item (a) -12.821% | VOID: cold page cache, both arms ramp 15 to 26.5 tok/s over the first 3 pairs | `P:2026-10-21-runner-3c4ca599.md:13` |
| DS41-W5 1017 vs Sept llama-bench (tg128 -5.1%, pp512 -29.9%) | cross-protocol, unrecoverable; operator: permanently INVALID, Sept Q4 not re-downloaded | `P:2026-10-23-3c4ca599.md:34`; CAL:255-256 |
| C2 b-rerun run 2 (anchor 50.46 t/s, CV 6.54%) | anchor CV > 6% rule; no verdict | `P:2026-10-22-3c4ca599.md:164`; CAL:210 |
| C2 b-rerun run 3 (anchor 41.47 CV 8.4%) | medians <45 rule; operator waived to CAS | `P:2026-10-23-3c4ca599.md:6,41` |
| C2 b-rerun re-arm 19:27Z | grant had no `mi210_0` token; launcher refused rc=2 | `P:2026-10-22-3c4ca599.md:165-166` |
| KPF-26.1 window 1 | arm A pass rate 0.4375 vs gate 0.6: task format forced no-CoT arithmetic (runner v2 re-armed) | `P:2026-10-22-kpf261-diagnosis.md:3,5` |
| KPF-62.8 chunk-KV real-role G1 | FAIL on reference drift, gate redesigned | `P:2026-10-22-kpf62-fix.md:3-7` |
| KPF-64 partial arms (pass1-A 196/400, pass2-D 260/400) | voided by Amendment 2; 2h50m windows cannot finish a live arm | `P:2026-10-22-kpf64-decode-fix.md:12-14` |
| Queue jobs 20/24/30 | midnight date bug in `in_blackout`; ended by 00:08Z | `P:2026-10-21-workspace-f8.md:6` |
| Overnight GPU jobs (chunk-KV P0, speech D1) | rc=64: region-lock argv wrong, dry run never exercised that path | `P:2026-10-22-3c4ca599.md:46-47` |
| PB-HOL-1 budget-on (first attempt) | harness bug (`self.srv`, summary KeyError); fixed, re-armed | `P:2026-10-21-workspace-f8.md:85` |
| CME-7 run 1 | thinking ON consumed max_output_tokens=2048, empty content | `P:2026-10-22-cme7-fix.md:4-6` |
| hsprof1-reader (twice) | pyarrow/shared lib clobbering, thinking-on empty derivation | `P:2026-10-22-3c4ca599.md:134` |
| HIL-15a first attempt; HIL-15b | trivial prompts gave insufficient AUC data; 15b got 69/80 pass with 5 variance tasks (want about 10), band MISSED | CAL:163; `P:2026-10-24-3c4ca599.md:4` |
| KVU-12 W2 CPU Tier-0; KVU-12.5 np8 L64k | lost a stream to HTTP 400 (UNDECIDABLE); confounded, s4 hit 12,000 s cap | `P:2026-10-21-workspace-f8.md:8,29`; `P:2026-10-22-workspace-f8.md:10` |
| M4.2a C2 off512 B reps | all 3 invalid (long request finished before short answered) | `P:2026-10-24-workspace-f8.md:128` |
| C4 earlier gate-e runs | pp floor 62% and 40.8% from one outlier arm; re-run not regraded | `P:2026-10-24-workspace-58.md:162-164` |
| akx-lb3-2 (two runs) | overhead -5.79% (N=4) then -5.93% / -6.30% at 64k: M build systematically faster than G, the co-tenancy explanation was retracted; no re-run until AKX-LB32-OVERHEAD-1 | CAL:359,662; `P:2026-10-25-workspace-58.md:10` |
| v11-086-cpu whole-host quiet (10-25) | two llama-bench runs of about 50 min SIGTERMed (rc -15), 7 skipped; measured nothing | `P:2026-10-25-workspace-58.md:4` |
| hpr-b-64k-holdout; hsf-5p-microbench | INVALID_SIM_DISAGREES; G4 INFO log line absent (INCONCLUSIVE by harness) | CAL:635,338 |
| CJ-18 judge pair | LLM judge invalid 15/18 | `P:2026-10-21-dpf-gates.md:7` |
| AK-HR-2 | Cohen kappa 0.245 vs bar 0.6; closed-partial, not decidable | `P:2026-10-20.md:67` |
| v11-arm-builds fa-vkq; kpf60-p0-gpu; akx-all-27b-run; new10 smoke | cherry-pick conflict rc=12; region-lock/claim rc errors; SIGABRT double-free after NaN in the fused per-layer path | CAL:131,142,145,214 |
| Harness false FAILs (not science) | inf42-g1-gpu rc=7, c3-gate-g rc=4, ch28-lbh-build rc=1 (ctest piped into grep -q, SIGPIPE), f8 "wrong build" (strings piped into grep -q) | CAL:140,247,299,333 |
| Idle compute | idle-CPU episodes 10-21 (04:45-06:30Z, 08:52-09:20Z, 16:40-18:00Z); GPU idle overnight after the 22:00Z cap; CPU idle from 05:52Z 10-25 (own miss, per calendar) | `P:2026-10-21-workspace-f8.md:11,97`; CAL:661,663 |
| Superseded anchors | Q38FN floors (2.483% / 1.365% / 1.106%) and DS41 1017 floor 2.862% superseded by C2/C3 ops changes | AGG:88,93 |

## 6. Open threads and next steps

| Thread | State | Next step | Source |
|---|---|---|---|
| CH-31-DEF1 batch-invariance | greedy at concurrent `-np 4` diverges from solo; present in C3 too (C5 3/5 vs C3 4/5) | localize op via per-op bisect | AGG:123 |
| META-ASSERT-1 | test-llama-archs rc 134 at `ggml-backend-meta.cpp:474`; PRE-EXISTING (C3 control) | fix in the champion | AGG:114; CAL:666 |
| CH-27 floor recalibration | Q38FN floors superseded; operator hold "DO NOT LAUNCH AUTOKERNEL" | recalibrate when AK is released | AGG:94 |
| CH-30b / CH-30-F1 / CH-24 | leak workarounds removal; outlier-robust gate-e estimator; CH-24 conditions pass on C5 | operator ticks CH-24 at production promotion | AGG:110-113,444-447 |
| KPF-64.3 EB | operator re-approved about 18.5 h | one-shot writer from 10-26 03:30Z | CAL:667 |
| inf66 | re-pinned `cb86b6cfd`, re-armed | whole-host quiet from 19:30Z | CAL:669 |
| akx-lb3-2 / hpr-b | BACKLOG, code-fix blockers | Codex AKX-LB32-OVERHEAD-1 | CAL:668 |
| CME-7S | confirm layout fix by rerun | armed on filler_run7 | `P:2026-10-22-cme7-cache-miss.md:37` |
| NEMO-LILI-2 | Nemotron DFlash drafter: no net win yet on MI210; 27B+DFlash2 round 78.2 ms (verify 67.1 ms), Bolt decode 33.9 ms/step | speed pair needs a GPU slot | `P:2026-10-25-workspace-58.md:84` |
| YaRN native gate / extension arms | NOT-FAIL, underpowered; extension arms about 17 GPU-h vs about 6 audited | decide power vs cost | `P:2026-10-22-yarn-native-gate-runner.md:17-33` |
| KPF-26.1d / KPF-62.8a | smaller table if arm A still <0.6 (gate not lowered); 62.8a open | rerun after v2 runner | `P:2026-10-22-kpf261-diagnosis.md:14` |
| HIL-15b / HIL-18a / HIL-6 | pass band missed; pilot redesign | HIL-18a variance tasks; operator picks redesign option | `P:2026-10-24-3c4ca599.md:4`; `P:2026-10-22-hil6-pilot-redesign.md` |
| W1 transfer (noise co-run) | VR upper 2.45, not <2 at n=5 | more samples | `P:2026-10-23-workspace-58.md:51-58` |
| DS41-W6.2 drafter alpha | Sept drafter +1.9 pp at block 2 (n=2), level at block 3; PARTIAL | remaining ABBA pairs | `P:2026-10-21-workspace-58.md:17` |
| SEQ-6 replay | 18 of 333 trials whose journaled z not reproduced | investigate | `P:2026-10-21-noninf-gates.md:8` |
| M4.2 | INCOMPLETE; M4.2b filed | run M4.2b | commit 3837a842c |
| Intake IST/SLQ | roofline estimate only (0.94-1.65x no-draft) | X0D quality, then speed passes | `P:2026-10-22-research-intake-ist-slq.md:35-60` |
