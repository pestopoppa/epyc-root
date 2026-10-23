# 2026-10-23 workspace-f8

## Morning 2026-10-23 (operator-invoked /wrap-up, subagent, branch `f8/wrapup-20261023-morning`)

Covers work since the night wrap-up (root `041291643`, 2026-10-22). Each item below was checked against git, the
run records (`PASSED`, `RUN_RECORD.json`, `VERDICT.json`, grant `.ended` files), the FILLERS register and the
process table.

### Turn-1 grammar was dead on code since UFH14-LB3; fixed on orchestrator main

- **Problem.** A conditional function-local `import os` in `_execute_turn` made `os` a local name. UFH14-LB3's
  `os.environ.get` (orch `517e24d4`, 2026-10-22) therefore raised `UnboundLocalError` on every first turn, and a
  blanket `except Exception: pass` hid it. On code at or after `517e24d4`, no turn-1 GBNF was applied in any mode,
  the `legacy` default included.
- **How it was found.** The mock proof of the 4-arm turn-1 grammar run.
- **Fix.** Orchestrator main `a498ffba`: the local import is dropped, and an AST regression test is added
  (`tests/unit/test_execute_turn_no_local_import_os.py`).
- **Exposure.** None in production. No :8000 listener existed at 00:10Z or at 06:32Z, so the live API never ran a
  post-`517e24d4` build.
- **Recorded at root `38d08bb78`.** UFH14-LB3.2 is ticked. UFH14-LB3.3 is filed (the blanket `except` must log
  and count). A caveat is added under GRAM-LAZY-1 step (1): the eager path described there is the intended path,
  not what code between `517e24d4` and `a498ffba` did.

### Jobs that passed overnight

| Job | Result | Evidence | Recorded |
|---|---|---|---|
| `akx-lb4-followups-2` (AKX-LB4-FU2) | PASSED 2026-10-22T23:02Z at experimental `581814ae8`; 36/36 steps. Worksize enumeration: the real sizer has 0 shortfalls on DS41, MQA2 and GQA12x2, and 6/6 mutant sizers are DETECTED. test-fa-rowexact with swa masks passes at threads 1/4/8/16/96 (NOT_ROW_EXACT across N, as predeclared; within tol 5e-4). | `/mnt/raid0/llm/tmp/f8-launchers-20261022/akx-lb4-followups-2/{PASSED,RUN_RECORD.json,out/}` | root `38d08bb78`: AKX-ALL-LB4.5 to LB4.8 and AKX-LB4-FU2 ticked |
| `sec-art-fingerprints` (SEC-ART-POST-a) | PASSED 00:04Z; 6/6 lineup GGUF rows registered, `check` rc 0, not_ok empty; ledger sha256 `37e9c439…675d` | `.../sec-art-fingerprints/{PASSED,RUN_RECORD.json}` | root `38d08bb78`: SEC-ART-POST-a ticked; SEC-ART-2 waits for SEC-ART-POST-f (pins in the lean registry) |
| `kvu121b-32k-dense-vs-coarse` (KVU-12.1b) | **REPLACES_DENSE at 32k**, against the predicted DENSE_STAYS. Coarse `--checkpoint-min-step 16384` keeps 534 vs 735 MiB/seq (-27.3%); prompt_n is within the dense wave spread on all four probes. Caveat: the edit_back_8192 gap (+5,908 tokens) passes only because the dense spread there is 6,644. | `.../kvu121b-32k-dense-vs-coarse/VERDICT.json` | root `2983121c7`: KVU-12.1b ticked; HYBRID-PREFIX-REUSE (b) re-opened (64k holdout with more waves next) |
| `locals-df2-lb1-ubatch-census` (DF2-LB1) | **FRAGMENTS_RARELY**: 25 of 721 qualifying verify calls fragment (3.47%), costing 43 extra ubatches. The first `census.py` pass crashed on the fixed-width `seq_id` field. The parser was fixed and re-run offline on the captured log under the same rule. | `.../locals-df2-lb1-ubatch-census/{VERDICT,RUN_RECORD.json,out/census.json}` | root `2983121c7`: census box ticked; the backend-sampling A/B half stays open |

### The 4-arm turn-1 grammar run is armed and booked

This is one run that merges UFH14-LB3.1b and GRAM-LAZY-1 step (2).

- **Arms.** `off`, `legacy`, `call` and `lazy-legacy`, on a private frontdoor-shaped server with an in-process
  driver. It never touches the live API.
- **Code.** Orchestrator branch `f8/turn1-grammar-lazy` (`02bbf904` lazy-legacy + `248c86ea`), unmerged.
  `248c86ea` is the same fix as main `a498ffba`. Root notes are at `bb66ba76f`.
- **Launcher.** pid 403555 (FILLERS row `turn1-grammar-4arm`, ARMED).
- **Booking.** The operator approved appending it to the 10-23 whole-CPU block (`grant-block-20261023.sh`, last
  step, 90 min) and extended the 503 window on the 0-95 serving roles to ~12:30Z. workspace-58 booked it
  ~10:45-12:15Z.
- **Gap closed by this wrap-up.** The handoffs still read "launcher prepared, not run". Dated ARMED notes were
  added under UFH14-LB3.1b and GRAM-LAZY-1. UFH14-LB3.1c is filed: land `02bbf904` only if the verdict keeps
  `lazy-legacy`, and never merge `248c86ea`.

### Night GPU failures, root causes and re-queues

- **`kpf18-item3-v2-sameshape`: rc 75 (claim held) at 00:40Z, before any load.**
  - Cause: workspace-58's grant writer granted the job while the mi210_0 flock was still held.
  - Fix: workspace-58 fixed its writers.
  - Re-queue: the same launcher (pid 1965738) is re-granted after W2 as step 1 of
    `grant-gpu-afterw2-20261023-v2.sh` (~13:50Z, 35 min).
  - Before this wrap-up it was unrecorded in the handoff. A dated note now sits under KPF-18.0d(item 3, rest).
- **KPF-LB1.1 run 1: INCOMPLETE** (rc 1, 00:44Z). Three attempts each reached 4 leading turns, under the
  predeclared minimum of 12.
  - Root cause, in the orchestrator: `extract_code_from_response` never stripped Qwen3 `<think>` blocks.
    Reasoning prose containing `=` broke `ast.parse`, the "all comments" nudge fired, and after 3 nudges the turn
    failed.
  - Harness repair, written into PREDECLARATION Amendment 2026-10-23T06:10Z before any further compute:
    - a capture-only think shim;
    - 16 stages instead of 12;
    - `--max-turns` 24 instead of 20;
    - 4 attempts instead of 3.

    The decision rule is unchanged, and a mock capture solved 16/16 stages.
  - Re-queue: the same launcher (pid 3419004) is re-used. A kill to swap it to a GPU-only claim was refused by the
    permission check, so it runs as step 2 of the after-W2 GPU script.
- **The extractor fix landed** on orchestrator main `96c30079` (UFH14-LB11 ticked, LB11.1 filed for the stop
  sequence that can cut inside an unclosed `<think>`; root `844550ff1`, `1bf2d57bc`, `bfb43f984`).
  - Exposed roles: `architect_critic`, `coder_escalation` and `ingest_long_context` (thinking on, raw
    `/completion` while `thinking_roles_chat_lane` is off).
  - This wrap-up added a note to the KPF-LB1.1 record that `96c30079` has landed (the record still said
    "unpushed").

### Live at the operator's next API reload

Orchestrator main `a498ffba` (turn-1 grammar), `96c30079` (`<think>` strip) and `a73af3cc` (`exec_write_flags`),
plus the earlier logging changes (`d0e0e477`, `cbe542ca`). None is live: no :8000 listener. This wrap-up attached
them, with the verification bar (API pid start time after `96c30079`, 2026-10-23T06:09:49Z), to the existing
reload box under UFH14-LB10 instead of filing a second reload task.

### FILLERS hygiene

- 6 finished f8 rows were marked COMPLETE and the df2 STOP file was set (main session).
- **Found by this wrap-up and not fixed:** row `dhm-mining-full` still reads ARMED with a live poller (pid
  1794793), but its job ended rc 0 at 2026-10-22T20:02Z (`grants/dhm-mining-full.ended`, results at root
  `c43175fad`). A re-written grant would re-run the mining. The fix is the same as df2's: mark it COMPLETE and touch
  `STOP.f8-dhm-mining-full`. `compute-flags/` is outside this subagent's write scope, so the fix is handed to the
  main.

### Checklist sync / derived actionables

- **Flips attributable to f8 in scope `041291643..origin/main`: 10**, all already committed by the owning commits
  and verified here:
  - UFH14-LB3.2 and UFH14-LB11;
  - AKX-ALL-LB4.5, LB4.6, LB4.7, LB4.8 and AKX-LB4-FU2;
  - the DF2-LB1 census, KVU-12.1b and SEC-ART-POST-a.

  This wrap-up made 0 new flips. The other 2 flips in range (KPF-26.1d and KPF-26.1e, `b824aabc4`) belong to
  another session.
- **Filed: 1.** UFH14-LB3.1c, the post-verdict landing rule for `f8/turn1-grammar-lazy`.
- **Already filed by the owning commits:** UFH14-LB3.3, UFH14-LB11.1 and HYBRID-PREFIX-REUSE (b).
- **Declined 1, in writing.** A second "reload the API" task for `a498ffba` and `96c30079` was not filed, because
  the existing UFH14-LB10 reload box covers the same single reload. That box gained a note with the later
  verification bar.
- **Gaps closed with dated notes: 4.**
  - The 4-arm run is ARMED and booked (UFH14-LB3.1b, GRAM-LAZY-1).
  - The `kpf18-item3-v2` rc 75 and its re-grant.
  - The KPF-LB1.1 harness amendment, and `96c30079` landed.

## Midday 2026-10-23 (operator-invoked /wrap-up, subagent, branch `f8/wrapup-20261023-midday`)

Covers work since the morning wrap-up (root `8104f630e`). Each item below was checked against git (root, orchestrator,
and the llama `fork` remote), the run records (`ENDED`, `VERDICT.json`, `RUN_RECORD.json`, grant `.ended`/`.complete`
files), the FILLERS register and the process table. f8's root commits in scope: `704067d69`, `796b88016`,
`919562ce7`, `fb29455a4`, `5220edd4a`, `870065c39`, `aa2dfaa80`, `228c0615d`, `20f80cb67`, `2fc213a5a`, `ad0635ae2`,
and after the wrap-up started, `066dfb1c7` and `eadbb8fe8`.

### gitnexus re-index (06:37-06:44Z)

- epyc-root re-indexed cleanly: 78,127 nodes, 117,195 edges, rc 0 (`compute-flags/f8-gitnexus2-run.log`).
- The epyc-orchestrator analyze segfaulted in its incremental pass. gitnexus warns that branch
  `spec-dec-mtp-refresh-2026-06-22`, not `main`, owns the orchestrator's flat index slot.
- Filed as NIB2-GNX-1 (root `704067d69`). FILLERS `f8-gitnexus2` is COMPLETE.

### Champion advance `dd3d9721c` -> `49550eda5` (~07:20Z; coordinator 3c4ca599's CAS)

| Item | Result | Evidence | Recorded |
|---|---|---|---|
| AKX-ALL-LB3 premeasure (on `dd3d9721c`) | **SPLIT_UNRESOLVED**. S(N) is 40-54% solid; F(N) read 0.7-3.6%, but the instrument failed: the perf window ran through state restores, templated symbols were truncated, and barrier wait was not charged to its op. FA is not the seed; which class is stays open. | `locals-akx-lb3-cpu-lc-premeasure/VERDICT.json` (07:06Z, rc 0) | root `796b88016`; AKX-ALL-LB3.2 filed (decisive instrument re-run) |
| AKX-AUTO-6 | `detect` works on the first real advance. `plan` was blocked by a missing PROVENANCE.md; the builder (3c4ca599) wrote it, and `plan` is now actionable on the real store with one calibration. | read-only runs | root `796b88016`, `919562ce7`; AKX-AUTO-6.1 closed later at `eadbb8fe8` (research `de279ee09`). The AUTO-6 exercise box stays open (no relaunch yet). |
| iqk FA port | Re-cut onto `49550eda5` as `experimental/locals-kernel-fixes-20261023` @ `540578f55` (on `fork`; `49550eda5` is its ancestor). | `git ls-remote fork` | AKX-LB4-FU3 filed; FILLERS row ARMED, launcher pid 845486 alive |
| Fixes not in the new champion | `5f1eee195`, `452887155` (CH-LB1) and `0daa3ca8d` (UFH14-LB1) are not ancestors of `49550eda5` and not on the re-cut. They are on `experimental/locals-kernel-fixes-20261022` (on `fork`). | `git merge-base --is-ancestor` | **Gap closed by this wrap-up:** dated notes under CH-LB1.1 and UFH14-LB1.1 say the fold's trial merge goes onto `49550eda5` |

### llama-bench uninitialised `autokernel_harden` (verified in source)

- **Defect.** `parse_cmd_params` declared `cmd_params params;` and never copied `autokernel_harden` (nor the seed and
  ready-timeout) from the defaults. About half of all llama-bench processes run without `--autokernel-harden` silently
  ran the hardened protocol.
- **How it showed.** KVU-LB1.b run 1 hit rc 124 at 08:16Z. Post-mortem at root `fb29455a4`: the cause was the
  hardened protocol (40 x 8k depth fills per benchmark), not F32.
- **Fix.** `fork` branch `experimental/llama-bench-harden-init-20261023` @ `141e4bcf5` (one commit on `49550eda5`:
  llama-bench.cpp plus a test).
- **Follow-through.**
  - Root `228c0615d`: CH-28 fold, manifest V11-103 PEND, LBH-1..3, the consumer guard proposal, and belief wiring
    (VB-LLAMA-BENCH-HARDEN-PROTOCOL plus a row in `scripts/vidya/adapters/README.md`).
  - Root `20f80cb67`: INF-65 and INF-66 Next action.
  - workspace-58 relayed the fleet alert, and a memory was saved.
- **LBH-2 re-grade.** f8's additions were merged onto 3c4ca599's parallel records at root `2fc213a5a`:
  - lineage via `f744cc220`;
  - DS41-W5 llama-bench is INVALID (cross-protocol), with per-row evidence and the deleted Sept GGUF noted;
  - the C112 bisect holds on an independent like-protocol re-analysis (first bad `9b148baab`);
  - the Q38FN d0 anchor is relabelled a hardened-protocol reading;
  - the wiki W5 readings are marked INVALID.

  LBH-2 stays open for the INF-70 REQUEST-UNKNOWN group (September markdown outputs with no recoverable protocol).

### turn1-grammar-4arm: PASSED 08:42Z (30/30 cells, not a mock)

| Arm | Pass | t1 ms/token |
|---|---|---|
| off | 66.7% | 17.8 |
| legacy | 40.0% | 23.6 |
| call | 36.7% | 25.0 |
| lazy-legacy | 3.3% | 54.8 |

- **Off vs legacy:** +26.7 pp, 95% CI +10 to +46.7 (task-cluster bootstrap). The verdict file reads
  `GRAM_LAZY_1_KEEP_LEGACY`, and for UFH14-LB3.1b `off: REMOVE_GRAMMAR`.
- **Operator decision:** default OFF, on orchestrator main `93055064`.
- **Recorded** at root `5220edd4a`, `870065c39` and `aa2dfaa80`:
  - UFH14-LB3.1, LB3.1b and LB3.1c ticked;
  - GRAM-LAZY-1 closed, and the lazy branch not landed;
  - UFH14-LB3.4 (confirmation on a larger task set) filed.
- **Later (`066dfb1c7`):** UFH14-LB3.3 done and LB11.1 implemented flag-off (orchestrator `f3ab78b2`).

### KVU-LB1.b run 2 (`49550eda5`, Amendment 2): NO_COST at 09:40Z

- **Decode medians:** N1@8k +1.38%, N5@8k +0.86%, N1@32k +1.05%, N5@32k +14.1% (one noisy pair). No cell reached
  -1%.
- **Prefill:** the probe reads about 0 (+1.8% / -0.1%), which matches the code: the tiled path always accumulates in
  FP32.
- **Row hygiene:** the hardened-row guard relaunched 9 sessions. Every row used is `autokernel_hardened: false`.
- **Recorded** at root `ad0635ae2`, with KVU-LB1.d (adopt always-F32) filed.

### FILLERS and schedule (checked 09:55Z)

- **COMPLETE:** `f8-gitnexus2`, `turn1-grammar-4arm`, `locals-kvu-lb1-arch-decode-ab` and
  `locals-akx-lb3-cpu-lc-premeasure`.
- **Still ARMED, launchers alive:**
  - `kpf18-item3-v2-sameshape` (pid 1965738), about 13:50Z;
  - `locals-kpf-lb1-1-27b-completion-turns` (pid 3419004, repaired harness), about 14:25Z;
  - `akx-lb4-followups-3` (pid 845486).

  workspace-58's `grant-akx3-gap-20261023-v2.sh` and `grant-akx3-20261023.sh` (both alive) book FU3 on q2: a gap
  window only if at least 3,300 s remain before 11:25Z, then after NEW-13 (by 21:55Z). **Gap closed by this wrap-up:**
  a dated ARMED and booked note under AKX-LB4-FU3.
- **Live at the operator's next API reload:** orchestrator `a498ffba`, `96c30079`, `93055064` and `a73af3cc` (all on
  origin/main), plus `f3ab78b2` since. No :8000 listener exists, so none is live.

### Checklist sync / derived actionables

- **Flips attributable to f8 in scope `8104f630e..origin/main`: 7**, all committed by the owning commits and
  verified here:
  - UFH14-LB3.1, LB3.1b, LB3.1c and GRAM-LAZY-1;
  - KVU-LB1.b;
  - UFH14-LB3.3 and AKX-AUTO-6.1 (`066dfb1c7`, `eadbb8fe8`).

  This wrap-up made 0 flips. The other flips in range (CH-22, CH-25, CH-26, HS-PROF-1 x4, CS-8.L4) belong to
  3c4ca599.
- **New tasks f8 filed in range: 11.** NIB2-GNX-1, AKX-AUTO-6.1, AKX-ALL-LB3.2, AKX-LB4-FU3, UFH14-LB3.4, CH-28,
  LBH-1, LBH-2, LBH-3, VB-LLAMA-BENCH-HARDEN-PROTOCOL and KVU-LB1.d.
- **Filed by this wrap-up: 2.** Both come from the LBH-2 W5 note, where they were stated in prose only:
  - DS41-W5d: a MUL_MAT_ID microbench at pp512 shapes as a premise test with no model load. BLOCKED on the DS41
    freeze.
  - DS41-W5e: the campaign owner annotates the S5 inbox note's -29.9% as INVALID. This is the owner's single-writer
    store.
- **Declined 1, in writing.** PROVENANCE for the 7 non-champion 10-21/22 images is not filed: no loop needs them,
  and AUTO-6.1's closing note records the same condition.
- **Gaps closed with dated notes: 3** (CH-LB1.1, UFH14-LB1.1, AKX-LB4-FU3).

### Wrap-up gates

| Gate | Result |
|---|---|
| Index regen + `index_state.py --check` | rc 0, 0 problems |
| Prune candidates (generated signal) | 0, so nothing was pruned or archived |
| README freshness | clean |
| Wiki | sweep 18 compiled 16 sources into 8 pages; lint has 0 errors and no new warnings; bare `--touch`, delta 0 afterwards |
| `vidya sync --check` | FRESH: intake-2510, lag 0 |
