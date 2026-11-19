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
