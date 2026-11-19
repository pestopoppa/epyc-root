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
