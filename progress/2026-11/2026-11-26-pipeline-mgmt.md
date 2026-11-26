# 2026-11-26 — pipeline-mgmt

Support for the AutoKernel (AK) overnight run, the operator decision-queue triage, and the A3B taskflow canaries.

## 1. AK pipeline fixes (all deployed, verified in DEPLOYED.json)

| Fix | Commit | Defect it closed |
|---|---|---|
| cx65 auto smoke budget = measured/300 s per unit, cap 2400 s | 64d56d01f | 18,870 s budget disabled the overrun check (G-Q38FN) |
| R6 budget ignores harness-class smokes | 942a3f977 | C22 G-27B r5 refused SMOKE-BUDGET while the GPU idled |
| served_quality needs only `content` | c0a05fcc8 | DRAFTVOCAB quality row crashed after 1.5 h (MTP response shape) |
| cx66 smoke judges witnesses in every correctness unit | dfbc0e44f | C22 r4 smoke PASS, full run FUTILITY_HARNESS_WITNESS |
| cx67 reduced smoke units (kld --chunks 2) | 03ebd80b6 | hour-long smoke held three quarters idle |
| measured smoke times only raise the estimate | 91aeab115 | draftwin-confirm killed at 576 s |
| cx68b op-level gate (`--metric op_gbps`, `--op-decide`) | e0fb1d703 | op-kernel levers had no generator path |
| op rows without a served workload | 511326552 | RF7 smoke KeyError 'input' |
| cx69 + fix: exec guard (FILLER_ID or FILLER_DRYRUN) | 6062b523b, d365e9899 | INC-20261126-ungranted-mi210-replay |
| cx70 `--arm-store`, `--serving-floor` | a9dad809b | promotion rows could not compare stores |
| GPU-FENCE skips vendored harness files; arm-store + argv-json | 18cad7f49 | every CPU ak_gate row refused at publish |
| cx72 `--promotion-suites` | 825010e67 | promotion quality receipts |
| S5 served=None guard; per-item sampling record | 54ff923c5 | S5 crash |
| smoke identity prompts cut to smoke length | a660ead17 | prodcfg smokes overran on 16k-token prompts |
| cx71d parity capture + parity_assemble.py | ee673ad17 | promotion parity evidence |
| cx73 hold CPU smokes during quiet timing rows | 0a76490f3 | 4 smokes spoiled draftwin-r2's last block |

AK results observed: C22 G-Q38FN KEEP (C22 x1.109), C22 G-27B r5 KEEP (C22 x1.121, I8PC_ONLY x1.128, LOSSLESS x1.052),
DRAFTVOCAB r3 KEEP (x1.140), A3B composite futile (x0.992), RF7 chain stopped (KLD 0.039 vs 0.0004 A/A).

## 2. Incident (own)

INC-20261126-ungranted-mi210-replay (97315dfd6): a half-stubbed offline replay ran real TBO/KLD on the MI210 with no
grant for ~10 min. Remedy shipped as the exec guard above. Memory: feedback_replay_stub_every_runner.

## 3. Operator decision queue (master-handoff-index)

Triage of 42 rows: 153b10a8f (19 DONE/MOOT removed), 23e33d5ca (decisions recorded), 395982009 (OP-AK-HOLD
RESTORED after I wrongly removed it — the operator did not lift the hold), final applied-state update.
Signed today by the operator: RATIFY-HOST-MEMORY-RULES-20261021 + OP-OPCONST-3C4 (19f9eec3d; earlyoom drop-in live on
the host), P-MEMEVAL-1 for OP-42 (3ba9500c8), W-34 blacklist purge (orchestrator 59a1d469).
Open: OP-1 W-33 needs its amendment text drafted; OP-42 needs one inference window after the reboot; OP-29 kept open.

## 4. Codex lanes

Six boxes delivered (cx77-cx82): EV-SKILL-NULL-REPLAY (held-out gain +0.12 pp, CI -0.67..+0.93), AK-SHORT-ROW-CENSUS
(27B 13,680 / A3B 4,750 eligible width-1 calls; not a zero), DF2-TARGET-KV-CONTRACT, CPU-KDA-EXP-CENSUS,
SPEC-FILTER-TIES, MOE-STATIC-POOL-REPLAY (last four mostly missing-witness records). cx76 trash-sweep robustness
(89b6efdc4). cx90 canary_perf_summary.py (9728250f3). Prep wave cx83-cx89 mostly BLOCKED by my own over-tight brief;
re-brief cx83b-cx89b was stopped on operator order before finishing. cx74/cx75 stopped unfinished.

## 5. A3B taskflow canaries — what went wrong

Operator stopped everything at ~11:40Z. My errors, in order: ran the SAME 20 units on CPU and GPU (duplication, not a
split); kept the CPU on one quarter, then three, avoiding q3 contention that does not matter for a harness test;
proposed four separate servers instead of ONE A3B server with -np 4; routed a quick harness run through keeper
placement. Fixes found on the way: gpu-r1 self-deadlock (non-reentrant lane_lock re-entered by drop_lane; same
per-arm directory for every unit) -> RLock + per-unit dirs; r8k inherited a stale STOP from r8h.
Ready but not running: /mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8n-20261126 (one -np 4 server on 0-95, C22 CPU build,
skips GPU-done units). GPU-r2 has 5 completed units; r1 had 5.

## Next

Operator decides what runs next. Nothing of pipeline-mgmt is running.
