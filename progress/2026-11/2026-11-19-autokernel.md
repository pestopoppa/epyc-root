# 2026-11-19 — autokernel session (roster id `autokernel`, no lane: ad-hoc session in the shared clone)

Operator-invoked wrap-up. Every item below was re-verified as an ancestor of origin/main (root and research) before writing.

## Landed on main

| Area | Commits | Note |
|---|---|---|
| Ratifications (operator-signed, bundle verify PASS x3) | root `82bde1fa2` (P-SERVE-1), `6029e2bea` (KLD thresholds, cherry-picked after a push race), research `b620a0f23` (GPU Q38FN-hybrid top-1 floor 93%), root `56b757f9a` (code-budget baseline 37+2 modules) | The guard is still red on 43 existing-file overruns (operator decision OP-AK-CODEBUDGET-43). |
| Bundle tooling | root `27fb8e5aa`, `2bbdf7e54`, `a60ac5edc`; push-retry fix `9a3ae21fd` | |
| Gate releases | six scoped files in compute-flags/operator-ratify (rows-prefix allowlist, allow_unpark false); Pipeline session scoped releases in `3e9f5aa71` | |
| AKU wiring | research `b0cb301ff..93445e31e` | ticked S3-AKU-01, AKU-07k, AKU-10i, AKU-06i; partial AKU-04f, AKU-06l, AKU-07o, U3-SEED |
| AKX P2 batch | ticked P5a, PARETO-RETAIN, ALL-17, RUNEND-REPORT, VB-AK-HISTORY, later AKX-AUTO-9 (research `bec0d4319`, `12de4168d`) | census store + `census_live` added for P1d |
| Long-context batch | MoE-Spec belief wiring, C6 remeasure closed, EXECUTOR-WINDOW-CAP, LSA tooling, AKU-07o root side | |
| AM port | decision "faithful staged port"; fork branch `llama.cpp-experimental-am-beta-20261119` @ `c9f2e34ce`; AM-PORT-1 ticked; row `am-port2-...` published | two Expected-Attention defects fixed (hybrid hparams misparse made EA a no-op on 27B; last-position eviction) |
| W1 upstream PR | fork branch `w1-cpu-sparse-fa-prefill` @ `70ba79110` | `gh pr create` refused (no CreatePullRequest); operator opens it in the web UI (OP-W1-PR); also folds into the composite after C16 |
| R22-5 boundary | filed FAIL; real v10 MMVQ MMID ragged-m slot-overwrite bug, latent for served models (box MMID-Q8-N1-ODDM); fix `fa221af5d` on fork `ak/mmid-q8-n1-oddm-fix-20261119`; validation row `mmid-q8-n1-oddm-fix-gpu-20261119` published; research `55f9757cf` (tbo_parse regex) | |
| Intake 2694..2704 | Stage 4 root `e60ba3755`, research `6b3a75924` | boxes AK-GDN-SPEC-SPLIT, AK-GAP-1, AK-PROF-GAPHIST, AK-PROF-SCLK, AK-RESGRID-1; seeds 14, 15 |

Filed rows: c15-gv-coalesce DROP; c5-isa1 PASS; r24-10 PASS; c14-fold withdrawn; c15-cpu-fa-splitkv-a3b DROP (noise-suspect, contended); q38fn perop inconclusive (harness defect, r2 published); akx-all-31 native r2 published; aku-07j FAIL (one real runtime_recovery test failure needs a code fix); ak-cpu-aa-calibration PASS (screen floor 3.84%, serving floor 4.15%, co-tenant upper bounds, quiet pair log-sd 2.2%); ch37 a3b cpu PASS; ch37 27b gpu r1 inconclusive (detector false positive), r2 published. Rows published and pending smoke are filed by the watcher, not by this session.

## Wrap-up changes (this commit set)

Belief-kernel discoverability review ("is every finding the loop needs reachable from the belief kernel or handoffs?"). The AK planner reads only committed-conclusion register rows (`data/belief/committed_conclusions.jsonl`) plus handoffs, so a `[belief: cc]` tick with no register row is invisible to it (same gap fixed for three ticks on 2026-11-18, `3c02a5f1d`).

| Finding | Handoff location | Gap found | Fix |
|---|---|---|---|
| MMID ragged-m bug | autokernel-loop R22-5 line; kernel-champion MMID-Q8-N1-ODDM box | R22-5 line tagged `no-belief`, no register row | retagged `[belief: cc]`, register row (mechanism `mmvq:mmid-n1-oddm-slot-overwrite`) |
| EA defects | long-context AM-PORT-1 | tick had `no-belief: code landing`, no date, no register row; defect not stated as a finding | defects stated, retagged cc, dated, register row; new box EA-27B-EVICT-AUDIT (earlier 27B EA results may have evicted 0) |
| CPU A/A floor | autokernel-loop AK-CPU-AA-CALIB | cc tag present, no register row | register row (mechanism `cpu-aa:floor-co-tenant`) |
| GDN gap | autokernel-loop AK-GDN-SPEC-SPLIT | planned box, source-read gap, no measured result | none needed; box is discoverable, nothing to project |
| Gate rules (KLD thresholds, Q38FN-hybrid top-1 floor 93%) | kernel-research.md P-AK-SEARCH-1-A5a, `graph_kld_policy.json`; box AK-FUSE-GRAPH-KLD-1 still unticked with stale "waits on signature" | amendment absent from the box; box unticked after ratification and wiring | box ticked, note added, `[belief: cc]`, register row (kind decision) |
| AM premise defect | long-context AM-DECISIVE-1 | tagged `no-belief: audit`, no register row | retagged cc, register row (mechanism `kv-compact:am-premise-defect`) |

Also added register rows for this session's other filed results that carried `[belief: cc]` with no row: c15-cpu-fa-splitkv-a3b DROP, c5-isa1 PASS, r24-10 PASS, aku-07j FAIL, c15-gv-coalesce DROP, ch37 a3b CPU PASS. Canary `canary_cc.py` (dev mode, `CC_REGISTER`) returned `ready` after the additions.

Other sessions' 2026-11-19 `[belief: cc]` ticks without register rows (kv-cache, harness, speculative-decoding, memory, context, long-context kshift lines) were listed but not touched: they belong to those sessions.

## Operator decisions pending (added to the master queue)

1. OP-AK-CODEBUDGET-43: the 43 code-budget overruns.
2. OP-W1-PR: open the W1 upstream PR via the web UI.
3. OP-ROCM102-BUILD: ROCm 10.2 experimental build, only if AK-GAP-1 shows >= 3% launch/graph overhead.

## Wrap-up 2 (later 2026-11-19): C6 proof, GAP-1, C14, SCLK, DTREE

All commits verified on origin/main (root, research) or on the named fork branches.

| Row / track | Verdict | Evidence |
|---|---|---|
| INF48-C6-CONTROLLER-PROOF r11 | FUTILITY_CARRIER | research `7946e2196` (symbol gate on truncated hunk headers; clean-completion typed); root `ea31eadd5` |
| r12 | reached the C6 oracle, crashed on `C6SplitPolicyRefusal` | research `33041e70a` (typed sealed refusal, controller continues; q8_block precision bound for quantized MUL_MAT); root `6ba3a18fd`; r13 published (smoke queued) |
| AK-GAP-1 | PASS: idle gap/fixup futile | root `891f3ab13`; ROCm 10.2 probe and AK-RESGRID-1 not triggered; new AK-GAP-1-SAMPLE / IDSORT; step-1 row `ak-gap-1-step1-gpu-20261119` (`54bff8218`) |
| AKX-ALL-14 | v10 row PROVEN, reopened (`55b5733c1`); repeat on C14 champion PROVEN, ticked (`bc8cf3885`) | C14 recipe registered research `71a2ce3c1` + composite_build.py; note `2fc268b0a` |
| AK-PROF-SCLK | PASS DELTA (`9b8de907a`): MI210 sclk operand/power dependent (MMQ -297 MHz / -21% TOPS, FA -248 MHz / -10%) | AK-PROF-SCLK-CAPT act_dump tool research `123ec088e`; row published (`8092f9a8e`, `7745e8808`) |
| AK-LOO-CONFIRM-C14 | PASS `a5ab6dbd3`: keep all four C14 CPU keeps | dtree-build contamination window in row CONTAMINATION.json (lesson: builds need region-lock claims) |
| Q38FN-CPU-PEROP-PROFILE | PASS `fdc6c8d04`: draft FLASH_ATTN = 60% of depth growth | new Q38FN-DRAFT-FA-WINDOW, Q38FN-INDEXER-TOPK-CPU (implementation in progress) |
| AKX-P3a census | row filed pass, box open `f1cf92109` | |
| AK-GDN-SPEC-SPLIT | measured futile `1501154bb` | |

### AK-DTREE program (operator directive: tree-verified spec decode, 27B + A3B)
- Plan P1-P6 `d69e53711`; intake-2705..2717 `c22b5b127` (DTREE-0/A/B added).
- P1 on fork `llama.cpp-experimental-dtree-20261119` (`25e6fee9d`, `d5f1ca4ca` recurrent seq_cp rollback bug fix, `6ad10b3bc`); box `09c17e1b4`. P2 rows amended to a fresh-prefill oracle gate `5f9937f69`.
- AK-DTREE-2 kernels on `llama.cpp-experimental-dtree-kernels-20261119` (`126b4dd26`, `4c95e2a87`, `cc2e450d8`, `9832d0330`, `a5ea53bbd`); CPU e2e gate 80/80 vs oracle; GPU rows queued behind the am-port EA ladder.

### Pipeline
Fixed: auto-filer filed a pass on a DROP/FUTILITY rationale (`bba1c010a`, `--correct` re-files; r12 mis-filed pass corrected). Open (reported to Pipeline): "smoke queued" rows are never smoked; local republish loops running. Index regen `827b40f6a`.

### Wrap-up edits
Next-action cells refreshed for INF-06, INF-82, INF-50 in `inference-research-index.md`. Checkbox state already synced by the per-result commits above (no new flips needed).

### Open
r13; P2/P5 dtree rows; DTREE-0 trace; SCLK-CAPT; kernel op-gate row; EA ladder (EA arms show n_beta_set 0, check at filing). Operator: W1 PR (web UI), OP-AK-CODEBUDGET-43 (both already in the master queue).

## Wrap-up 3 (since root bc8b551bc): C14 keeps, Q38FN profile, AM-PORT ladder, DTREE, code-budget ratified

All shas verified on origin/main (root, research) or on the named fork branch before writing.

| Row / track | Verdict | Evidence |
|---|---|---|
| AKX-ALL-14 | reopened, re-run on C14 PROVEN; operator kept the tick | root `bc8cf3885`; C14 recipe registered research `71a2ce3c1`; note `2fc268b0a` |
| AK-LOO-CONFIRM-C14 | PASS: keep all four C14 CPU keeps | root `a5ab6dbd3`; contamination (a subagent build overlapped the window) recorded in the LOO row |
| Q38FN-CPU-PEROP-PROFILE | PASS: draft FLASH_ATTN is 60% of the depth growth | root `fdc6c8d04`; Q38FN-DRAFT-FA-WINDOW and Q38FN-INDEXER-TOPK-CPU being implemented |
| AKX-P3a census | row filed pass, box stays open | root `f1cf92109` |
| AK-GDN-SPEC-SPLIT | measured futile | root `1501154bb` |
| AM-PORT-2B ladder | done: no safe EA/L4 ratio on hybrid 27B (EA has no beta by design; per-token eviction drops digit tokens); original row corrected to fail; bb keeps EA refused on :8083 | root `7bb72a3a2`, `6353f5d6e` |
| AK-DTREE P2 | both rows FUTILITY (path-row slower: 27B 0.57-0.81x, A3B 0.49-0.85x); 27B T9 arm showed real oracle divergence, fix in progress | |
| AK-DTREE P5 | batch-mode switch landed, CPU e2e oracle 80/80 | fork `llama.cpp-experimental-dtree-kernels-20261119` `a5ea53bbd` (not a root/research commit) |
| DTREE identity row | smoke failed on a predicate copied from the withdrawn op-gate row; being fixed. Op-gate row withdrawn as superseded; DTREE-A argmax row republished, smoke PASS | |
| AK-PROF-SCLK-RECLAIM | clock-reclaim subagent running; SCLK-CAPT hit hard-end, re-run in progress | |
| INF-48 | next-action cell fixes | root `dc859f45c`, `f26e9e703` |

### OP-AK-CODEBUDGET-43: decided and ratified
Fable bloat review (`/mnt/raid0/llm/tmp/codebudget-bloat-review-20261119.md`), then trims in research `1c8d54874..0fe28fa6d` (~185 lines). Ratchet re-issued (root `25e09e521`), split and trim boxes filed (`85cc5987a`). Operator RATIFIED 2026-11-19T22:55Z: receipt `artifacts/operator/receipts/RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261119.json` (root `bde27ba5f`, ratify record `artifacts/operator/ratify_ak_loop_code_budget_ratchet_20261119.json`), baseline research `252684d41` on origin/main (measured at signing against research `0fe28fa6d`, 45 per-file ceilings). The master-queue row is rewritten as DECIDED + RATIFIED; deletion waits for the operator-cadence prune.

### Pipeline (from Pipeline Management)
Auto-filer pass-on-DROP fixed (`bba1c010a`, `--correct` path); queued GPU smoke never ran, fixed (`41041359b`); Codex rocm-kernel session retired; autokernel roster row added (operator synced config.yaml, bus provisioned).

### Lesson
Subagent builds need region-lock claims (memory saved); the LOO contamination is recorded in its row.

### Wrap-up edits
- New box `AK-TESTS-RESEARCH-MAIN-RED` in `handoffs/active/autokernel-loop.md`: 130 failed / 104 errors pre-existing on research main (numpy missing in system python3, `test_maintenance_execution` fakes lacking `ignore_errors`, yaml fault tests).
- INF-06 next-action cell refreshed in `inference-research-index.md`; INF-48 cell already current (`dc859f45c`).
- Checkbox flips this wrap-up: 0 ticks, 1 new open box (per-result ticks were committed with their commits). Belief-capture: the new box carries `[no-belief: tooling-repair]`.

### Skipped (operator cadence)
Step 3 pruning (OP-AK-CODEBUDGET-43 row deletion once the operator accepts; handoff compaction of autokernel-loop.md, 15k lines); Step 5 wiki sweep.

### Open
DTREE T9 oracle fix, identity row, DTREE-0 trace; Q38FN-DRAFT-FA-WINDOW, INDEXER-TOPK-CPU; SCLK-CAPT re-run and SCLK-RECLAIM; AKX-P3a box; trim-or-split boxes.

## Wrap-up 4 (since Wrap-up 3, root `3033eeb95`): code-budget ratchet ratified, audit and skill, clock reclaim, tests box closed, DTREE

All shas verified as ancestors of root origin/main, or present in research / the named fork, before writing. Fork shas live in `/mnt/raid0/llm/llama.cpp-experimental` (branch `llama.cpp-experimental-dtree-kernels-20261119`).

| Item | Result | Evidence |
|---|---|---|
| Code-budget ratchet | ratified | root `bde27ba5f`, research `252684d41` |
| Session audit (Fable) | written | `/mnt/raid0/llm/tmp/autokernel-session-audit-20261119.md` |
| `row-owner-loop` skill | landed with 7 committed-conclusion register rows | root `720768eb0` |
| Pipeline requirements | 14 sent to Pipeline, which is building B1, B2, B6, B8, B9 | bus |
| AKX-ALL-31.NATIVE-C14 | NATIVE_PASS, ticked | root `0a27198d2` |
| Clock reclaim | decode is not clock-limited (1700 MHz held); prefill is power-limited (300 W cap is the maximum); SCLK-CAPT r2 CAPTURED_LIKE_RANDOM, so random operands are valid for op gates and zero operands overstate MMQ by 26%; new boxes AK-PROF-SCLK-ENERGY and AK-PROF-SCLK-DETM (DETM needs root) | root `c80dedbc3` |
| AK-TESTS-RESEARCH-MAIN-RED | ticked: 247 failing items -> 1 intermittent failure, 0 errors, 8262 passed, 111 skipped (two justified groups) | root `648774335`; research `4a59d7b0c..1108b6ec1` (17 commits, one real product bug `cec5bcb30`); root `ec5857e32` pin |
| AK-STATIC-REGISTRY-CGROUP-NLINK-FLAKE | new open box: cgroup dir `nlink` in the identity makes `test_discovery_static_registry` fail intermittently under parallel load; 54/54 alone | root `648774335` |

### Tests box detail
Per-file loop+controller suites on research `1108b6ec1`, system python3 (no numpy), `EPYC_ROOT` at a fresh root worktree, q1 region claim, nice, 4 files in parallel; `cpu_fa_verifier_record` first: 14 passed with the pin. Intermediate full runs on `a95d0558e` showed 8 and 9 failures; three were deterministic and test-side (fixed in `1108b6ec1`: conftest `EPYC_ORCHESTRATOR_REPO` outranks the fixture root; the reader C1 pin needs a git fixture root; a same-size same-tick DSO rewrite needs an explicit mtime). The rest moved between runs (`native_final_trial`, `evidence_feed`, `loadgen_selfcheck`, `static_registry`) and pass alone, i.e. load sensitivity; only `static_registry` still flakes at 4 parallel. `check_regrowth_guards.py`: 0 violations.

### AK-DTREE
- DTREE-0 filed: the verify cost is a route step at 12 rows (wvsk M<=11 at 29.8 ms vs MMQ at 46.7 ms). AK-WVSK-M10 box `b508e2972`; the T9 subagent says the cause is not wvsk.
- T9 divergence: the AK-ASM-H15 fusion corrupts conv state when `n_seqs` changes between ubatches; `GGML_CUDA_AK_H15=0` makes it clean. This may affect production np>1 if H15 is in the store builds; a fix is in progress.
- Identity rows r1-r7: ops pass bit-exact every time (GDN 131/131, SSM_CONV 66/66); DTREE-2c and P4 ticked. Oracle disagreements are near-ties within Poisson noise; gate option A was taken.
- P5 rows `ak-dtree-batch-27b-gpu-20261119` and `ak-dtree-batch-a3b-gpu-20261119` are published at fork `abda9a72c` (fixes `b66a25406`, `dd26275d6`, `abda9a72c`) and wait for a gpu-q3 window. The smoke shows 27B auto at 41 vs 103 tok/s for linear, consistent with the verify-slope cost.

### Housekeeping
Root worktrees `ak-dtree2-p5`, `ak-dtree2-p5c`, `ak-dtree-file`, `ak-sclk-reclaim-20261119` removed (landed or clean; plain remove). `ak-dtree2-p5b` kept: it holds uncommitted domain-index edits outside the discardable set.

### Wrap-up edits
- Box tick `AK-TESTS-RESEARCH-MAIN-RED` plus one new open box. Checkbox flips this wrap-up: 1 tick, 1 new open box. Belief-capture: both carry `[no-belief: tooling-repair]`.
- Derived actionables: 1 filed (the nlink flake box), 0 declined.

### Skipped (operator cadence)
Step 3 pruning and the Step 5 wiki sweep.
