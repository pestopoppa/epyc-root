# 2026-09-16 — closure-inflation audit of checked handoff boxes (sub-closure-audit)

Zero-inference, read-only audit. It was prompted by UTM-M7/M8, which were ticked "✅ 2026-07-29" and
claimed `select_budgeted_records()` in orchestrator `src/trace/navigation.py`. The claim text arrived
in root `4762625d` (2026-07-30), where staged files rode along. The function was on no ref until
orchestrator `74418b3c` (2026-09-16 09:59Z) added it today.

## Method

- **Scope:** every `- [x]` box (continuation lines included) in `origin/main:handoffs/active/*.md`.
  That is 3,359 boxes, and 2,335 of them carry at least one reference.
- **References extracted:** 6,485 in total, split as follows.
  - 789 backticked `func()` or CamelCase identifiers
  - 3,716 paths, from backticks and markdown links
  - 1,980 commit SHAs of 7 to 40 hex characters
- **Where each reference was checked:** root, orchestrator and research at `origin/main` (fetched
  2026-09-16).
  - Identifiers were checked with `git grep -w` over code only; markdown, JSON and handoff/progress
    files were excluded.
  - Paths were checked with exact or suffix tree matches.
  - SHAs were checked with `cat-file`, then `merge-base --is-ancestor`.
- **Fallbacks for anything unresolved:**
  1. unmerged branch tips (81 root, 78 orchestrator, 245 research)
  2. `log --all -S` history
  3. the llama.cpp, whisper, qwentts and ik trees
  4. every local clone under `/mnt/raid0/llm`
  5. a same-subject commit on main, to catch cherry-picked SHAs
  6. a fuzzy match against definitions (difflib) to catch renames
- **Classes:** a = off-main or removed, b = nowhere, c = renamed or moved, d = external. FP = false
  positive, meaning an upstream pin, HF revision, digest, store-row id, runtime or evidence artifact,
  or scratch script. `ok-equiv` = the cited SHA is off main, but a same-subject commit is on main.
- **Tick attribution:** `git log -S "[x] <box prefix>" -- handoffs/`, oldest hit.
- **Cohort sweep:** a manual sweep of all 97 lines that `4762625d` added with "2026-07-29" in them,
  also checking snake_case identifiers. The default extractor skips those. This sweep is what found
  RC-9; the script now has an opt-in `--strict-idents` flag that catches it.
- **Script:** `/mnt/raid0/llm/tmp/sub-closure-audit/closure_audit.py` (not committed). A full run
  takes about 30 minutes, mostly the branch-tip grep.
  - Raw output: `closure_audit.json`
  - Triaged table: `triaged.tsv`
  - Triage overrides: `build_report_rows.py`

## Summary counts

After automated classification, 265 references in 210 boxes stayed unresolved. After manual triage:

| class | refs | boxes | meaning |
|---|---|---|---|
| **b — exists nowhere, box asserts it was built** | 1 (+2 from the cohort sweep, +UTM-M7/M8 already remediated) | 1 (+2) | **true closure inflation** |
| a — off-main, deleted later, local-only, or uncommitted | 28 | 20 | 7 need action; the rest are intentional deletions or history |
| c — renamed, moved, or stale SHA whose code lives elsewhere | 15 | 14 | 7 boxes need a re-point (a4cb04ca8 lineage) |
| d — external or llama.cpp symbols | 3 | 2 | no action |
| ok-equiv / ok (same-subject commit on main; promoted mid-run) | 25 | 22 | cosmetic re-point |
| FP (d/FP + FP) | 193 | 156 | no action |

**Rate:** about 5 of 3,359 checked boxes (0.15%) assert code that never existed. All confirmed
cases came from one commit, **`4762625d`** (2026-07-30 11:22Z, "artifact: rewrite the operator page
as the NUMA decision package"). That commit carried the "✅ 2026-07-29" codex-lane closures across
about 40 handoffs, so the inflation is **one cohort, not a diffuse habit**. Of the other 90-odd
closures in that cohort, the spot-checks resolved (for example `05e0b8bf`, `b55b4c43`, `4c1a3ac3`,
`bdfb6c63`, `5fd85268`, `608cc54c`, and the `MemoryActionStore` pattern/DELETE code). One more
failure is outside the audit's scope, in `handoffs/completed/`.

**Belief kernel:** `python3 scripts/vidya/cli.py cite-check --as-of 2026-09-16T00:00:00Z handoffs/active`
checked 1,468 citations across 122 documents and returned exit 0:

- ok 929, record 218, unknown 166, review 153, weak 2
- **no refuted, conflicted or dangling citations**

No intake or belief entry rests on the refuted boxes. UTM-M7 cites `intake-936` for the design
rationale, not for the code.

## Top 10 most consequential cases (boxes that gate other work)

1. **RVP-C6-1 / C6-1a / C6-2** (`rocm-verify-profile-backend.md:765,777,782,844`) and **R24-1**
   (`autokernel-rebuild-program.md:2634`), plus `autokernel-research-loop.md:3266,3656`. These are the
   C6 reward-integrity measurement anchor. `a4cb04ca8f92f…` is described as "clean, pushed", but it is
   on **none of the 850 `fork` refs** (via `ls-remote`) and in no local clone.
   - The hardening lineage does exist: llama.cpp `974b5fcb3` ("harden AutoKernel measurement
     instrument"), whose sole parent is `0db32c06`, on `fork/experimental-v9-autokernel-t1-hardening`,
     plus its descendants (for example `d9fdc17bd`).
   - Class c. **Action:** re-point the pins. Check any live T0/T1 manifest that still names
     a4cb04ca8: `/mnt/raid0/llm/autokernel/iqk-*.json` still do.
2. **RC-9 rubric persistence** (`reviewer-calibration-accounting.md:30`), ticked in `4762625d`.
   - The box claims `review_ledger.v2`, `rubric_json` and `per_item_grades_json` columns.
   - None of them exists in `src/trace/review_ledger.py` or `store.py`, or anywhere in code on any
     ref. The only hits are untracked bus state.
   - Class **b**. **Action: reopen.** It gates reviewer calibration (RC-7/RC-9 run in parallel).
3. **E1a format-robust scorer** (`rlm-contested-claims-self-evaluation.md:68`), ticked in `4762625d`.
   `scripts/benchmark/niah_scorer.py` never existed on any ref of any repo. Class **b**.
   **Action: reopen.** It gates every E1 strict-plus-lenient report.
4. **UTM-M7/M8** (`unified-trace-memory-service.md:221-222`), ticked in `4762625d`. Class b until
   today; orchestrator `74418b3c` (2026-09-16) has since added the selector and its tests.
   **Action:** annotate the box with the real landing SHA. UTM-M9 and caller wiring now have a real
   base.
5. **DAR-6.3 / DAR-6.4** (`decision-aware-routing.md:215-216`, ticked by `5617b63ed`, 2026-05-27).
   - The code was built (`5f5fd8f6`) and then deleted as dead code by `771348c8` (2026-06-16).
   - A note was added today, but both boxes remain ✅.
   - **DAR-6.5 (J14 A/B) is open and depends on it**, and the `swarm_fanout` flag in `src/features.py`
     now gates nothing.
   - Class a. **Action:** re-scope DAR-6.5, or reopen 6.3/6.4.
6. **Research shared clone: local `main` is 3 commits ahead of `origin/main`.** The key commit is
   `1780fa7b` (on main as `56ef1404`) ("promote INF-70 evidence, PROD-1 recipe draft and upstream patches out of scratch",
   37 files, +4,655 lines). `data/inf70-upstream-patches-2026-09-08/` is **not on origin**.
   - This surfaced through `cpu-decode-roofline-program.md:2862,3552`.
   - Class a. **Action:** push after reconciling. It feeds upstream publication.
7. **Benchmark SQLite store** (`handoffs/completed/benchmark-results-dashboard-completed-through-2026-08-23.md:58-59`),
   ticked in `4762625d`. `scripts/dashboard/export_benchmark_artifact_sqlite.py` and
   `data/benchmark_artifacts.sqlite` exist on no ref. Class **b**, outside the active scope.
   **Action:** reopen, or file a successor row.
8. **AK-V27-RCV / AK-V27-CMP** (`autokernel-research-loop.md:64,67`). `caa22f42` and `cffb98d3` exist
   only on `codex/autokernel-v27-*`, 33 commits unmerged, and 0 of their added lines are on main.
   - The prose says not to promote wholesale, but AK-V27-C6 (open) lists them as foundations to reuse.
   - Class a. **Action:** add "branch-only" to both boxes.
9. **Hermes F plugin bundle** (`hermes-outer-shell.md:282`). `invoke_plugin_command()` and its tests
   exist only in local commit `532a49f1` in `/mnt/raid0/llm/hermes-agent`.
   - That is a NousResearch upstream clone with no fork remote, so the work can be lost.
   - Class a. **Action:** push to a fork, or record the clone path in the box.
10. **K28.5a scaffold** (`gemma-challenge-kernel-techniques-v7.md:428`). The CUDA hook and
    `docs/development/k28-fused-chunked-gdn-prototype.md` are staged but **never committed** in
    `/mnt/raid0/llm/llama.cpp-k28-prototype-20260720`. Class a.
    **Action:** commit on an experimental branch.

Also needing action: Z12 (`multiscreen-attention-evaluation.md:595`) cites
`epyc-inference-research/docs/gdn2-low-rank-static-analysis-2026-08-25.md`, which is **untracked**
on disk and informs B9. SW-4 `a1d36daf` and W0 `b62946d` are off main, but their content is on main,
so they are cosmetic re-points.

## Caveats

- Backticked snake_case names are not checked by default; use `--strict-idents`, which is noisy.
  Wider coverage would add more RC-9-style findings from outside the cohort.
- Scratch-script paths (`agents/*/…`, `evict_nodes.sh`, …) and evidence directories are classed as
  FP or evidence, not code claims.
- `origin/main` moved during the run as other sessions pushed. Three references were promoted
  mid-run (`scripts/inf70/harness1/*`).
- 62 SHA-b hits were read by hand; all were upstream pins, digests, store-row ids, or GC'd
  pre-cherry-pick SHAs whose landed twins are on main.

No boxes were ticked or unticked. No repositories were modified.

## Full table (265 unresolved references after automated passes, triaged)

Supplementary rows found only by the cohort sweep:

| handoff | box excerpt | reference | class | ticked-by | action |
|---|---|---|---|---|---|
| reviewer-calibration-accounting.md:30 | RC-9 — Rubric persistence ✅ 2026-07-29 | `rubric_json` / `per_item_grades_json` / `review_ledger.v2` (ident) | **b TRUE** | 4762625de 2026-07-30 | REOPEN |
| completed/benchmark-results-dashboard-…:58 | Persist ingested results into a queryable store (SQLite) | `scripts/dashboard/export_benchmark_artifact_sqlite.py` (path) | **b TRUE** | 4762625de 2026-07-30 | REOPEN / successor row |
| unified-trace-memory-service.md:221-222 | UTM-M7/M8 budget-conditional selector | `select_budgeted_records()` (ident) | b → fixed today (orch 74418b3c) | 4762625de 2026-07-30 | annotate with the landing SHA |

Main table. The ticked-by column is the oldest commit whose diff adds `[x] <box prefix>`:

| handoff | box excerpt | reference | class | ticked-by | action |
|---|---|---|---|---|---|
| rlm-contested-claims-self-evaluation.md:68 | E1a — Use a **format-robust scorer**, or score twice (strict + lenient | `scripts/benchmark/niah_scorer.py` (path) | **b TRUE** | 4762625de 2026-07-30 | REOPEN E1a (scorer never existed on any ref; same 4762625d cohort as UTM-M7/M8) |
| agent-collab-rnd-harness.md:40 | Compare OpenHyra's all-outcomes Experience Bank + LLM Context-Agent cr | `eb.py` (path) | a (path removed from main, historical) | b8abe1028 2026-07-22 | no action |
| attention-matching-kv-compaction.md:304 | **KV-0c — `radix_cache.py` deleted** (480 lines + shim). ✅ 2026-08-20  | `radix_cache.py` (path) | a (path removed from main, historical) | c75a2f686 2026-08-20 | no action |
| autokernel-rebuild-program.md:557 | P6.4 — **one surface, not two** ✅ 2026-08-30 (`e0ceada9`). `/loop` is  | `dashboard/static/kernel.html` (path) | a (kernel.html deleted e0ceada9, as intended) | 9870f3ad1 2026-08-30 | no action |
| autokernel-research-loop.md:3195 | **Add `KIND_STATE_TRANSITION` to `journal.py` and rewire the controlle | `TransitionRecorder` (ident) | a (deleted 2d89e90b); box closed as superseded | d49d68392 2026-08-11 | no action |
| autokernel-research-loop.md:64 | **AK-V27-RCV — keep ordinary governed refusals out of cumulative-termi | `caa22f42389fd744bac6f9213fb863504849d888` (sha) | a (branch-only by design: codex/autokernel-v27-*; 33 commits unmerged) | a82167a62 2026-08-22 | point at the branch and state "not on main" in the box |
| autokernel-research-loop.md:67 | **AK-V27-CMP — authenticate the frozen-v9 comparator without executing | `cffb98d3eb06aa81e8bdf990e22520444fd94adb` (sha) | a (branch-only by design: codex/autokernel-v27-*; 33 commits unmerged) | a82167a62 2026-08-22 | point at the branch and state "not on main" in the box |
| autopilot-decision-plane-audit-2026-07-22.md:335 | **Integrate scorer-isolation before deterministic-score replay, then r | `3f734141` (sha) | a (audit-only commit on an integrate branch) | 1ee8bd7cc 2026-08-27 | no action |
| canonical-judge-suite-revamp.md:171 | **CJ-1c. Execution requirement** — expected **none**. ✅ 2026-08-13 — * | `1715e6c3` (sha) | a (lane/mainD bookkeeping commit; the box text itself is on main) | 10ff9bdf8 2026-08-16 | no action |
| dashboard-architecture-restructure.md:381 | **D-1 (HIGH) — the production-kernel panel is absence-tolerant, QUIETL | `static/kernel.html` (path) | a (kernel.html deleted e0ceada9, as intended) | 120131f53 2026-08-12 | no action |
| decision-aware-routing.md:215 | **DAR-6.3 ✅ 2026-05-27**: `dispatch_swarm_fanout(request, targets, ... | `dispatch_swarm_fanout(request, targets, ...)` (ident) | a (deleted from main 771348c8, 2026-06-16) | 5617b63ed 2026-05-27 | annotated 2026-09-16; re-scope DAR-6.5, which is open and depends on deleted code; `swarm_fanout` flag in features.py is now dead |
| decision-aware-routing.md:215 | **DAR-6.3 ✅ 2026-05-27**: `dispatch_swarm_fanout(request, targets, ... | `src/swarm_fanout.py` (path) | a (deleted from main 771348c8, 2026-06-16) | 5617b63ed 2026-05-27 | annotated 2026-09-16; re-scope DAR-6.5, which is open and depends on deleted code; `swarm_fanout` flag in features.py is now dead |
| decision-aware-routing.md:215 | **DAR-6.3 ✅ 2026-05-27**: `dispatch_swarm_fanout(request, targets, ... | `SwarmCompletion(success=False, error=...)` (ident) | a (deleted from main 771348c8, 2026-06-16) | 5617b63ed 2026-05-27 | annotated 2026-09-16; re-scope DAR-6.5, which is open and depends on deleted code; `swarm_fanout` flag in features.py is now dead |
| decision-aware-routing.md:215 | **DAR-6.3 ✅ 2026-05-27**: `dispatch_swarm_fanout(request, targets, ... | `SwarmFanoutResult` (ident) | a (deleted from main 771348c8, 2026-06-16) | 5617b63ed 2026-05-27 | annotated 2026-09-16; re-scope DAR-6.5, which is open and depends on deleted code; `swarm_fanout` flag in features.py is now dead |
| decision-aware-routing.md:216 | **DAR-6.4 ✅ 2026-05-27**: `bradley_terry_aggregate(pairwise_scorer)` b | `bradley_terry_aggregate(pairwise_scorer)` (ident) | a (deleted from main 771348c8, 2026-06-16) | 5617b63ed 2026-05-27 | annotated 2026-09-16; re-scope DAR-6.5, which is open and depends on deleted code; `swarm_fanout` flag in features.py is now dead |
| episodic-memory-integrity.md:409 | **M-12e — scorer prerequisites, ZERO COMPUTE, do before any arm runs** | `wiki/drafts/tulving-subset-scoring-and-tau-coverage.md` (path) | a (wiki draft removed in the 25f95aa90 wiki sweep) | e6bd74058 2026-09-14 | no action |
| evidence-plane-event-sourcing-and-narrative.md:100 | **W5 — STM as generated view** (impl 4.1, ~1–2 days, needs W1): `short | `TrialOutcome` (ident) | a (retired intentionally, 2cb89f82 / STM cutover) | 4288a6dfb 2026-06-18 | no action |
| evidence-plane-event-sourcing-and-narrative.md:100 | **W5 — STM as generated view** (impl 4.1, ~1–2 days, needs W1): `short | `orchestration/autopilot_short_term_memory.md` (path) | a (retired intentionally, 2cb89f82 / STM cutover) | 4288a6dfb 2026-06-18 | no action |
| evidence-plane-event-sourcing-and-narrative.md:100 | **W5 — STM as generated view** (impl 4.1, ~1–2 days, needs W1): `short | `scripts/autopilot/short_term_memory.md` (path) | a (retired intentionally, 2cb89f82 / STM cutover) | 4288a6dfb 2026-06-18 | no action |
| evidence-plane-event-sourcing-and-narrative.md:79 | **W2 — supersession events** (impl 3.3, ~1–2 days): new row type `{typ | `ExperimentJournal.apply_scrub()` (ident) | a (retired intentionally, 2cb89f82 / STM cutover) | 1baa4a97d 2026-06-19 | no action |
| gemma-challenge-kernel-techniques-v7.md:428 | **K28.5a default-off scaffold gate ✅ 2026-07-20**: isolated worktree ` | `docs/development/k28-fused-chunked-gdn-prototype.md` (path) | a (staged, never committed, in the llama.cpp-k28-prototype-20260720 worktree) | baca3c0f2 2026-07-20 | point at the worktree; commit on an experimental branch |
| hermes-outer-shell.md:282 | **F — Re-express `x_*` overrides as a namespaced Hermes plugin bundle* | `invoke_plugin_command()` (ident) | a (local-only commit 532a49f1 in the upstream NousResearch clone /mnt/raid0/llm/hermes-agent; no fork remote) | 360eb4ce7 2026-07-06 | point at the clone; push to a fork or it can be lost |
| hermes-outer-shell.md:282 | **F — Re-express `x_*` overrides as a namespaced Hermes plugin bundle* | `tests/test_plugins.py` (path) | a (local-only commit 532a49f1 in the upstream NousResearch clone /mnt/raid0/llm/hermes-agent; no fork remote) | 360eb4ce7 2026-07-06 | point at the clone; push to a fork or it can be lost |
| hermes-outer-shell.md:282 | **F — Re-express `x_*` overrides as a namespaced Hermes plugin bundle* | `tests/test_cli_prefix_matching.py` (path) | a (local-only commit 532a49f1 in the upstream NousResearch clone /mnt/raid0/llm/hermes-agent; no fork remote) | 360eb4ce7 2026-07-06 | point at the clone; push to a fork or it can be lost |
| hermes-outer-shell.md:282 | **F — Re-express `x_*` overrides as a namespaced Hermes plugin bundle* | `tests/hermes_cli/test_commands.py` (path) | a (local-only commit 532a49f1 in the upstream NousResearch clone /mnt/raid0/llm/hermes-agent; no fork remote) | 360eb4ce7 2026-07-06 | point at the clone; push to a fork or it can be lost |
| model-capability-descriptors.md:31 | **W3 — first consumers** (~2 days, no router redesign): q_scorer cost  | `orchestration/model_quality_signatures.yaml` (path) | a (legacy YAML deleted a517793c, as intended) | 437260ac8 2026-06-14 | no action |
| multiscreen-attention-evaluation.md:595 | **Z12 (Z) — can GDN-2's `b_proj` / `w_proj` be low-rank factorized?**  | `epyc-inference-research/docs/gdn2-low-rank-static-analysis-2026-08-25.md` (path) | a (untracked doc on disk in research) | 909f47482 2026-08-27 | commit docs/gdn2-low-rank-static-analysis-2026-08-25.md |
| non-inference-backlog.md:425 | **NIB2-70** (MED): **rescue the shared research clone's uncommitted st | `63ec9f53` (sha) | a (rescue branch by design) | ffbd68234 2026-09-08 | no action |
| rocm-verify-profile-backend.md:1624 | **Z14 (Z) — DONE 2026-08-23: filed as [fla-org/flash-linear-attention# | `kernels.py:16` (path) | a (path removed from main, historical) | 8ab6eaa2e 2026-08-23 | no action |
| autokernel-rebuild-program.md:2634 | **R24-1 — wire the existing hardened bench into the live loop.** ✅ 202 | `a4cb04ca8` (sha) | c (SHA gone; lineage lives at llama.cpp 974b5fcb3, parent 0db32c06, fork/experimental-v9-autokernel-t1-hardening) | 66f423d07 2026-09-15 | point at the live branch: a4cb04ca8 ("clean, pushed") is on none of the 850 fork refs and in no local clone |
| autokernel-research-loop.md:3266 | **Migrate the durable IQK pair to proposal-v4 and regress the exact ar | `a4cb04ca` (sha) | c (SHA gone; lineage lives at llama.cpp 974b5fcb3, parent 0db32c06, fork/experimental-v9-autokernel-t1-hardening) | f9f36e3e5 2026-08-12 | point at the live branch: a4cb04ca8 ("clean, pushed") is on none of the 850 fork refs and in no local clone |
| autokernel-research-loop.md:3656 | **Bind the hardened instrument to clean, committed provenance before i | `a4cb04ca8f92fa4d665684490f609b380f9b5e96` (sha) | c (SHA gone; lineage lives at llama.cpp 974b5fcb3, parent 0db32c06, fork/experimental-v9-autokernel-t1-hardening) | 2cf63eda0 2026-08-12 | point at the live branch: a4cb04ca8 ("clean, pushed") is on none of the 850 fork refs and in no local clone |
| autopilot-continuous-optimization.md:1605 | `scripts/autopilot/start_fable_authority_daemon.py` resumed AutoPilot  | `scripts/autopilot/start_fable_authority_daemon.py` (path) | c (de-FABLE rename, 06c19cf6) | c1f92cd00 2026-07-15 | no action (historical run record) |
| autopilot-continuous-optimization.md:2785 | **The de-FABLE rename shipped broken operator-facing commands** ✅ foll | `start_fable_authority_daemon.py` (path) | c (de-FABLE rename, 06c19cf6) | 97a04febd 2026-08-11 | no action (historical run record) |
| autopilot-continuous-optimization.md:2785 | **The de-FABLE rename shipped broken operator-facing commands** ✅ foll | `fable5_gate_report.py` (path) | c (de-FABLE rename, 06c19cf6) | 97a04febd 2026-08-11 | no action (historical run record) |
| non-inference-backlog.md:106 | **NIB2-51**: X-MAS routing scaffolding (taxonomy + classifier + winner | `WinnerTableLoader` (ident) | c (built as `WinnerTable.winner_for`) | b0c694377 2026-06-14 | no action |
| orchestration-robustness-audit-2026-07-11.md:137 | Autopilot supervisor/death ledger wrapper landed (`autopilot_superviso | `start_fable_authority_daemon.py` (path) | c (de-FABLE rename, 06c19cf6) | c00bfade7 2026-07-11 | no action (historical run record) |
| orchestration-robustness-audit-2026-07-11.md:144 | W2 direct AutoPilot start bypass now fails closed in `epyc-orchestrato | `scripts/autopilot/start_fable_authority_daemon.py` (path) | c (de-FABLE rename, 06c19cf6) | 4280206a3 2026-07-14 | no action (historical run record) |
| orchestration-robustness-audit-2026-07-11.md:158 | P0.2a report-only amendment evidence view landed in `epyc-orchestrator | `fable5_gate_report.py` (path) | c (de-FABLE rename, 06c19cf6) | 77a0dc6ed 2026-07-11 | no action (historical run record) |
| orchestration-robustness-audit-2026-07-11.md:189 | P0.1 report-action hardening landed in `epyc-orchestrator` commit `2b7 | `fable5_gate_report.py` (path) | c (de-FABLE rename, 06c19cf6) | 6fabecce2 2026-07-11 | no action (historical run record) |
| rocm-verify-profile-backend.md:765 | **RVP-C6-1 — Hash-pin the measurement translation units.** `tests/test | `a4cb04ca8` (sha) | c (SHA gone; lineage lives at llama.cpp 974b5fcb3, parent 0db32c06, fork/experimental-v9-autokernel-t1-hardening) | 3dd1ec1b5 2026-08-11 | point at the live branch: a4cb04ca8 ("clean, pushed") is on none of the 850 fork refs and in no local clone |
| rocm-verify-profile-backend.md:777 | **RVP-C6-1a — Finalize the clean one-parent measurement-instrument lin | `a4cb04ca8f92fa4d665684490f609b380f9b5e96` (sha) | c (SHA gone; lineage lives at llama.cpp 974b5fcb3, parent 0db32c06, fork/experimental-v9-autokernel-t1-hardening) | 2cf63eda0 2026-08-12 | point at the live branch: a4cb04ca8 ("clean, pushed") is on none of the 850 fork refs and in no local clone |
| rocm-verify-profile-backend.md:782 | **RVP-C6-2 — Stream-escape defence.** ✅ 2026-08-11 — the hardened line | `a4cb04ca8` (sha) | c (SHA gone; lineage lives at llama.cpp 974b5fcb3, parent 0db32c06, fork/experimental-v9-autokernel-t1-hardening) | f092a65e0 2026-08-11 | point at the live branch: a4cb04ca8 ("clean, pushed") is on none of the 850 fork refs and in no local clone |
| rocm-verify-profile-backend.md:844 | **RVP-C6-8 — T1 output-invariance across repetitions, with buffer-addr | `a4cb04ca8` (sha) | c (SHA gone; lineage lives at llama.cpp 974b5fcb3, parent 0db32c06, fork/experimental-v9-autokernel-t1-hardening) | 3dd1ec1b5 2026-08-11 | point at the live branch: a4cb04ca8 ("clean, pushed") is on none of the 850 fork refs and in no local clone |
| cpu-decode-roofline-program.md:2862 | **SYNC-4 — CLOSED 2026-09-05. The premise was STALE: GET_ROWS was alre | `ggml_get_n_tasks()` (ident) | d (llama.cpp symbols); related: research local `main` has 3 unpushed commits (1780fa7b (on main as `56ef1404`) INF-70 upstream patches, 37 files) | 1cf222990 2026-09-05 | push the research shared-clone main (the INF-70 evidence is not on origin) |
| cpu-decode-roofline-program.md:2862 | **SYNC-4 — CLOSED 2026-09-05. The premise was STALE: GET_ROWS was alre | `ggml_get_rows_split_init()` (ident) | d (llama.cpp symbols); related: research local `main` has 3 unpushed commits (1780fa7b (on main as `56ef1404`) INF-70 upstream patches, 37 files) | 1cf222990 2026-09-05 | push the research shared-clone main (the INF-70 evidence is not on origin) |
| cpu-decode-roofline-program.md:3552 | **SYNC-7 — COMPLETE ✅ 2026-09-07: kernel-vs-planner classification don | `ggml_get_n_tasks()` (ident) | d (llama.cpp symbols); related: research local `main` has 3 unpushed commits (1780fa7b (on main as `56ef1404`) INF-70 upstream patches, 37 files) | baac8eb57 2026-09-07 | push the research shared-clone main (the INF-70 evidence is not on origin) |
| agentic-rocm-kernel-authoring.md:534 | **Repair the confined Claude runtime temp path.** ✅ 2026-08-12 — resea | `268115ad` (sha) | ok-equiv (same-subject commit 446a1c31 is on main) | 65c52b342 2026-08-12 | re-point (cosmetic) |
| agentic-rocm-kernel-authoring.md:538 | **Pin `268115ad` and launch a fresh seven-arm attempt.** ✅ 2026-08-12  | `268115ad` (sha) | ok-equiv (same-subject commit 446a1c31 is on main) | 9835a36cc 2026-08-12 | re-point (cosmetic) |
| agentic-rocm-kernel-authoring.md:634 | **Compile the initial EPYC C3/C5 exact-suite seam.** ✅ 2026-08-11 — re | `4320d83a` (sha) | ok-equiv (same-subject commit 5dfd14ad is on main) | 83e4c7ba0 2026-08-11 | re-point (cosmetic) |
| autokernel-rebuild-program.md:1280 | **R23-15 — boundary step2 gate defect found + repaired (operator-appro | `9c40429d` (sha) | ok-equiv (same-subject commit 765fc6bb is on main) | 3dfc20503 2026-09-02 | re-point (cosmetic) |
| autokernel-research-loop.md:4754 | **AK-DEL-2 — Review and integrate the next bounded gfx90a prior-art ca | `677a2eec` (sha) | ok-equiv (same-subject commit 35f10715 is on main) | 9d76598f2 2026-08-12 | re-point (cosmetic) |
| autokernel-research-loop.md:624 | **AK-AUD-13 — Prove measured critic feedback changes the next live pro | `268115ad` (sha) | ok-equiv (same-subject commit 446a1c31 is on main) | 65c52b342 2026-08-12 | re-point (cosmetic) |
| autokernel-unified-surface-program.md:3791 | **S3-AKU-18 (AK-RH-3) — first-class planner abstain.** Accept {"abstai | `ae8e5ef9` (sha) | ok-equiv (same-subject commit ccbfe1b8 is on main) | 93052d17a 2026-09-15 | re-point (cosmetic) |
| autopilot-decision-plane-audit-2026-07-22.md:264 | **E8 terminal bridge and focused c1 mixed-tail successor instrument**  | `5568478f` (sha) | ok-equiv (same-subject commit ac158841 is on main) | 93dc48b7a 2026-07-28 | re-point (cosmetic) |
| capability-registry-and-promotion.md:21 | **W0 — workload model** (1 day, ungated): `orchestration/workload_mode | `b62946d` (sha) | ok-equiv (about 95% of the lines are on main) | a50a6b8bc 2026-06-28 | re-point b62946d |
| eval-tower-architecture-audit-2026-07-20.md:326 | **C2 A3-era pool build invariant codified in `build_pool`** — ✅ 2026-0 | `88b1160d` (sha) | ok-equiv (same-subject commit 04124a54 is on main) | 874a6bc98 2026-09-16 | re-point (cosmetic) |
| numa-topology-cutover-resume-20260730.md:346 | **P1-3. SUPERSEDE the `dual-half-negative` seed strategy.** ✅ 2026-08- | `6dd3248d` (sha) | ok-equiv (same-subject commit 3f4b0918 is on main) | 2ce663641 2026-08-12 | re-point (cosmetic) |
| rocm-verify-profile-backend.md:157 | **HIP arm decision-grade hardening.** ✅ 2026-08-12 — research `b8d8c40 | `b8d8c409` (sha) | ok-equiv (same-subject commit 9609b686 is on main) | cfde83001 2026-08-12 | re-point (cosmetic) |
| rocm-verify-profile-backend.md:93 | **Compile the exact EPYC C3/C5 evaluation contract and controller/back | `4320d83a` (sha) | ok-equiv (same-subject commit 5dfd14ad is on main) | 83e4c7ba0 2026-08-11 | re-point (cosmetic) |
| session-bus-thin-dispatcher.md:955 | **M5b — operator disposition for preserved roster orphans.** ✅ 2026-08 | `c7f6c7fa` (sha) | ok-equiv (same-subject commit 70b49926 is on main) | 1c324e112 2026-08-11 | re-point (cosmetic) |
| shape-keyed-contention-gating.md:349 | **Bridge residual 1** — echo `GateDecision` (`admitted`/`waited_s`/`de | `a7d7bdb6` (sha) | ok-equiv (same-subject commit c61b8184 is on main) | 75ba3b4fc 2026-08-13 | re-point (cosmetic) |
| speculative-decoding-mtp-refresh.md:174 | **SW-4 — record in the registry that composed spec-dec is launch-fixed | `a1d36daf` (sha) | ok-equiv (lean view with runtime_switchability is on orch main under another SHA) | e6bd74058 2026-09-14 | re-point a1d36daf |
| vidya-belief-substrate-program.md:1099 | SC28 **Wire RVP-T0-1 saturation and AK-BH-1 vendor-baseline diagnostic | `1434ed1a` (sha) | ok-equiv (same-subject commit d72dd81c is on main) | ef10977e1 2026-08-12 | re-point (cosmetic) |
| vidya-belief-substrate-program.md:404 | SC10 **Wire the full AutoKernel `evaluation_event` write/read path pro | `3f0cb392` (sha) | ok-equiv (same-subject commit d96e8704 is on main) | ef10977e1 2026-08-12 | re-point (cosmetic) |
| vidya-belief-substrate-program.md:404 | SC10 **Wire the full AutoKernel `evaluation_event` write/read path pro | `2a83b176` (sha) | ok-equiv (same-subject commit d6201045 is on main) | ef10977e1 2026-08-12 | re-point (cosmetic) |
| vidya-belief-substrate-program.md:404 | SC10 **Wire the full AutoKernel `evaluation_event` write/read path pro | `6c9cad04` (sha) | ok-equiv (same-subject commit 20b1826b is on main) | ef10977e1 2026-08-12 | re-point (cosmetic) |
| vidya-belief-substrate-program.md:84 | **SC19 — wire `ChatResponse.contention_gate` (A14) on the write side,  | `a7d7bdb6` (sha) | ok-equiv (same-subject commit c61b8184 is on main) | decac3cb3 2026-08-26 | re-point (cosmetic) |
| agent-world-env-synthesis.md:293 | Evaluate TaleSuite/Jericho (Balances, Detective, Enter, Inhumane, Libr | `benchmark.py` (path) | ok (promoted to main during the audit run) | 4762625de 2026-07-30 | no action |
| cpu-decode-roofline-program.md:1913 | **HARNESS-1 — make the measurement harness 3–5× faster and tighten its | `evict_nodes_force.sh` (path) | ok (promoted to main during the audit run) | 97d3eba22 2026-09-08 | no action |
| cpu-decode-roofline-program.md:1913 | **HARNESS-1 — make the measurement harness 3–5× faster and tighten its | `mincore()` (ident) | ok (promoted to main during the audit run) | 97d3eba22 2026-09-08 | no action |
| vidya-belief-substrate-program.md:1602 | **SC75 (VB-INF70-ARMS) — wire the INF-70 serving-harness ARM records o | `coresummary.sh` (path) | ok (promoted to main during the audit run) | 1e9b822d0 2026-09-16 | no action |
| cpu-decode-roofline-program.md:2701 | **D6-PLACE — ★★ THE "2 MB THP BOUNDARY" DOES NOT EXIST. The mechanism  | `move_pages(2)` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 9cdb2062d 2026-09-06 | no action |
| document-parser-table-bench.md:51 | **CLI verified ✅ 2026-07-20**: `paddleocr doc_parser -i ... --vl_rec_b | `paddleocr.PaddleOCRVL(...)` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 8e1e80362 2026-07-20 | no action |
| glm52-reviewer-capability-gates.md:176 | **GC-external-1 — External ground-truth reviewer adapter / live gate ✅ | `RewardBench` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 00dd976d3 2026-07-19 | no action |
| glm52-reviewer-capability-gates.md:177 | **GC-external-1a — Pairwise external adapter + n=24 dry plans ✅ 2026-0 | `RewardBench` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 1ae1f0fed 2026-07-19 | no action |
| gpu-serving-tie-in-program.md:89 | **P2-2d (NEW) — whisper is BLOCKED: the D2 tenant cannot run on the MI | `get_supported_compute_types('cuda')` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | fcbbd8e66 2026-07-29 | no action |
| intake-derived-work-2026-07-25.md:259 | **ID-35 — A false claim from `intake-580` is load-bearing in two activ | `BaseParser` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 654bce6c6 2026-08-12 | no action |
| log-linear-gated-deltanet-readiness.md:75 | Reference implementation (github.com/HanGuo97/log-linear-attention) in | `HGatedDeltaNetForCausalLM(…, GenerationMixin)` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 40b873e2c 2026-08-12 | no action |
| mi210-big-model-and-acceleration-roadmap.md:255 | **K28-R1 — Adopt the SGLang `fla/` four-stage decomposition as K28's n | `ChunkGatedDeltaRuleFunction` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | bedbd2fae 2026-08-11 | no action |
| non-inference-backlog.md:104 | **NIB2-49**: RAO + ReDel Step 1 pre-flight gate scaffolding — [`rao-re | `KaniDelegated` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 39adb2fe4 2026-06-13 | no action |
| non-inference-backlog.md:88 | **NIB2-40**: Compaction-pipeline gap analysis — map Claude Code's 5-la | `trim_segment(segment_id)` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 20b107b64 2026-06-13 | no action |
| per-request-reasoning-budget.md:234 | Design stop-signal abstraction to slot in CGR certainty-threshold / Sp | `StopSignal` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 7c525c813 2026-07-29 | no action |
| qwen38-27b-replace-qwen36.md:394 | **(Z) fla #1156 exposure for our Qwen3.x GDN family — RECORDED AND CLO | `ShortConvolution` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | a24f8ca03 2026-08-22 | no action |
| repl-session-memory-maturity.md:57 | D-a2 — **Follow-up: pandas — DECLINE CONFIRMED, NOT-FEASIBLE.** ✅ 2026 | `BlockManager` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 1ed834cbe 2026-07-27 | no action |
| repl-session-memory-maturity.md:57 | D-a2 — **Follow-up: pandas — DECLINE CONFIRMED, NOT-FEASIBLE.** ✅ 2026 | `_new_Index(cls, d)` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | 1ed834cbe 2026-07-27 | no action |
| rocm-verify-profile-backend.md:1569 | **(Z) fla issue #1156 — RECORDED AND CLOSED, 2026-08-22. Two claims in | `ShortConvolution` (ident) | d/FP (external library or paper symbol, or a design-only name in a box closed otherwise) | a24f8ca03 2026-08-22 | no action |
| agent-collab-rnd-harness.md:40 | Compare OpenHyra's all-outcomes Experience Bank + LLM Context-Agent cr | `context_agent.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | b8abe1028 2026-07-22 | no action |
| agentic-rocm-kernel-authoring.md:264 | **Port and bind K-Search without replacing its search policy.** ✅ 2026 | `53c8fab9a5e8fab2c86610d24fbec5067f90e115` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | cf5d42e45 2026-08-11 | no action |
| agentic-rocm-kernel-authoring.md:267 | **Port and bind GEAK-v1 without replacing its evolutionary loop.** ✅ 2 | `4ffba15a55f250816598b4e27eb56ca40a699cea` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | cf5d42e45 2026-08-11 | no action |
| agentic-rocm-kernel-authoring.md:271 | **Port, bind, and repair Xe-Forge.** ✅ 2026-08-11 — research `d76fe4b9 | `4dcb5080b0f56d0b655ec8c8c9509b8e3ba0382c` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | cf5d42e45 2026-08-11 | no action |
| agentic-rocm-kernel-authoring.md:275 | **Port KernelFoundry and preserve its governed MAP-Elites/QD behavior. | `1c053e02383d12937f144923bcc1faa82fa7788f` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | cf5d42e45 2026-08-11 | no action |
| agentic-rocm-kernel-authoring.md:582 | **Close seven-arm r18 as a staged-host-input identity failure without  | `~/.claude/.claude.json` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 448af75ae 2026-08-12 | no action |
| agentic-rocm-kernel-authoring.md:613 | **Obtain and execute the exact licensed EvoEngineer source through the | `1649715a975b9022c84b5279c88aaef0b73b28dc` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 9e0fba25c 2026-08-12 | no action |
| agentic-rocm-kernel-authoring.md:660 | **GEAK-family freshness sweep completed ✅ 2026-08-03** (research-intak | `perf_knowledge/hardware/cdna2_mi200/` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 72d27f396 2026-07-29 | no action |
| agentic-rocm-kernel-authoring.md:666 | Read GEAK's `landscape/` + `languages/` sections as an external check  | `5107c7e4` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | b0366d9c6 2026-08-11 | no action |
| agentic-rocm-kernel-authoring.md:719 | Seed C5 with the HyRA sol_execbench kernels as reference specs the loo | `26ebfbe7` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | b0366d9c6 2026-08-11 | no action |
| architect-model-selection-bench.md:356 | **Promote the GPU driver scripts into the repo** (`gpu_lib.sh`, `run_a | `run_arm.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 3a146f297 2026-07-29 | no action |
| architect-model-selection-bench.md:356 | **Promote the GPU driver scripts into the repo** (`gpu_lib.sh`, `run_a | `run_budget.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 3a146f297 2026-07-29 | no action |
| architect-model-selection-bench.md:556 | **D-27B — all three operator-launched sequential downloads completed** | `dl_27b_q8.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 85f427531 2026-07-26 | no action |
| architect-model-selection-bench.md:617 | **Run a canonical-solutions acceptance gate FIRST, before any model ar | `21b6668` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | abeceffe7 2026-08-12 | no action |
| architect-model-selection-bench.md:825 | **Watch FrontisAI/OpenRSI PR #2 ("feat(gym): add OpenMLE Sandbox") to  | `docs/validation.md` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 17b2e0d8c 2026-08-11 | no action |
| autokernel-champion-aggregate.md:662 | **FOLD-3** ✅ 2026-09-08 — **fast-forward + push, NOT a relaunch** (ope | `pestopoppa/llama.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e5d1846d2 2026-09-08 | no action |
| autokernel-cross-workload-keep-gate.md:596 | **AKX-P1a — footprint extractor.** | `evaluator/surface.derive_affected_surface` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 93052d17a 2026-09-15 | no action |
| autokernel-rebuild-program.md:1068 | **R23-5 — H1 transfer falsifier EXECUTED (H1-first, operator-approved) | `2fa07724` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | b95ab81eb 2026-09-01 | no action |
| autokernel-rebuild-program.md:1508 | **R23-34 — planner/critic model split (operator directive 2026-09-03:  | `~/.codex/config.toml` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 3f2338ea7 2026-09-03 | no action |
| autokernel-rebuild-program.md:1577 | **R23-40 — FIXED+CONFIRMED ✅ 2026-09-04 — INCIDENT: Run-18 build-non-d | `7337b4bb` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 079494e41 2026-09-04 | no action |
| autokernel-rebuild-program.md:1577 | **R23-40 — FIXED+CONFIRMED ✅ 2026-09-04 — INCIDENT: Run-18 build-non-d | `6bac92af` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 079494e41 2026-09-04 | no action |
| autokernel-rebuild-program.md:1577 | **R23-40 — FIXED+CONFIRMED ✅ 2026-09-04 — INCIDENT: Run-18 build-non-d | `55f783de` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 079494e41 2026-09-04 | no action |
| autokernel-rebuild-program.md:2151 | **R23-61a — RUN THE RECALIBRATION at n >= 24 and write `n` + a CI into | `autokernel/loop-memory/serving-floor.qwen3.8-27b-q8-gpu-dflash2-np4.json` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 50ee3656a 2026-09-15 | no action |
| autokernel-research-loop.md:3435 | **Make frozen-kernel working-tree drift a first-class production-set a | `tools/math-tools/external/eigen/` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 76b6d95b5 2026-08-12 | no action |
| autokernel-research-loop.md:3435 | **Make frozen-kernel working-tree drift a first-class production-set a | `tools/math-tools/external/odeint/` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 76b6d95b5 2026-08-12 | no action |
| autokernel-research-loop.md:3457 | **Resolve or explicitly retain the frozen llama working-tree cleanline | `251bff28859af2ed2d5bdf14034175f03cafffc7` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | c199f8c3c 2026-08-12 | no action |
| autokernel-research-loop.md:3457 | **Resolve or explicitly retain the frozen llama working-tree cleanline | `9e75be5d9e435739b086aee928736fc241e77a4a` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | c199f8c3c 2026-08-12 | no action |
| autokernel-research-loop.md:3594 | The `capability.py` hoist itself: 11 audit functions, ~631 lines, 5 de | `capability.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | d49d68392 2026-08-11 | no action |
| autokernel-research-loop.md:4728 | **AK-C6-1 — Name syscall confinement explicitly in C6's acceptance cri | `openmle_gym/sandbox_exec.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e59a82ef5 2026-08-10 | no action |
| autokernel-research-loop.md:5221 | **AK-QL-8 — Operator decision: no general autocompiler; compile contro | `980faee8` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 8571fd3eb 2026-09-15 | no action |
| autokernel-restart-and-strip.md:47 | **Rotted Claude critic pin** (discovered at launch; blocked EVERY new  | `claude/versions/2.1.231` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | f90c621c6 2026-08-27 | no action |
| autokernel-unified-surface-program.md:1023 | FOLD-1..3 (champion owner) per `autokernel-champion-aggregate.md` ✅ 20 | `pestopoppa/llama.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e5d1846d2 2026-09-08 | no action |
| autokernel-unified-surface-program.md:3186 | **AKU-08f — load the published canonical projector by default without  | `ad87bdec` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 052ff259d 2026-09-09 | no action |
| autopilot-continuous-optimization.md:1601 | Bridge consent was granted in `orchestration/authority_consent.json`,  | `orchestration/authority_consent.json` (path) | FP (gitignored runtime state) | c1f92cd00 2026-07-15 | no action |
| autopilot-continuous-optimization.md:1623 | Adopt run-manifest provenance (sha256 of sources+task+evaluator + resu | `provenance.py:72-157` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 4762625de 2026-07-30 | no action |
| autopilot-continuous-optimization.md:1624 | Evaluate OpenHyra's evidence-gated stop controller (LLM may only REQUE | `stopping.py:238-263` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 403a07fec 2026-07-29 | no action |
| autopilot-continuous-optimization.md:1633 | **AP-19a — GEPA reflective mutation has never run.** ✅ 2026-07-25 — FI | `gepa/proposer/reflective_mutation/reflective_mutation.py:66-67` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | c942728ef 2026-07-25 | no action |
| autopilot-continuous-optimization.md:1727 | **Operational alternative to the ratification-grade reseed — the code  | `orchestration/autopilot_state.json` (path) | FP (gitignored runtime state) | e6bd74058 2026-09-14 | no action |
| autopilot-continuous-optimization.md:1966 | `config/stack_templates/default.yaml` is 10 validation errors stale —  | `config/stack_templates/` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 2fafc4325 2026-08-12 | no action |
| batched-decode-measurement.md:669 | **Operator decision pending — instrument-era row for the gate re-scopi | `tokens/token-queue.md` (path) | FP (bus runtime state, untracked by C45) | e618d25f5 2026-08-11 | no action |
| batched-decode-measurement.md:689 | **Offline replay DONE + decision package delivered ✅ 2026-08-11 (`main | `replay_candidates.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | f3b35713c 2026-08-11 | no action |
| batched-edit-parallel-apply.md:44 | **BEP-6 — hashline vs `current_shas`: the granularity gap does not exi | `packages/hashline/src/format.ts:112-121` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 1d8294b59 2026-08-18 | no action |
| bep-dcp-falsification-harness.md:17 | **DCP-6a content-depth/freshness repair**: branch `fix/dcp6a-context-d | `530128b7` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 7205bb0a9 2026-06-12 | no action |
| canonical-judge-suite-revamp.md:152 | **CJ-1a. Acquire corpus** — already cached (`hendrydong/gpqa_diamond`  | `8c23b9cbb` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 921113ed1 2026-08-12 | no action |
| contention-model-device-and-load-axes-rider.md:285 | **Make the unit suite reproducible** ✅ 2026-08-03 — `orchestration/run | `orchestration/runtime_flags.json` (path) | FP (gitignored runtime state) | 40c406328 2026-08-03 | no action |
| conversational-memory-eval-instrument.md:27 | **CME-1 — Author `BEAMAdapter` (a `BaseAdapter` subclass) for the 128K | `3205395e` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e4bc7d716 2026-09-16 | no action |
| conversational-memory-eval-instrument.md:66 | **CME-2 — Make the FOLD an explicit, tested contract** (intake-1337#re | `report_results.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | a48a24255 2026-09-15 | no action |
| conversational-memory-eval-instrument.md:66 | **CME-2 — Make the FOLD an explicit, tested contract** (intake-1337#re | `b2da22ea` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | a48a24255 2026-09-15 | no action |
| conversational-memory-eval-instrument.md:88 | **CME-4 — Add a `context_mode` parameter {none, retrieved, full} to th | `src/trace/query.query` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e4bc7d716 2026-09-16 | no action |
| cpu-decode-roofline-program.md:177 | **C0 — measure the roofline denominator: read-only DRAM bandwidth unde | `c5_followup.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | cdee2c12f 2026-09-02 | no action |
| cpu-decode-roofline-program.md:177 | **C0 — measure the roofline denominator: read-only DRAM bandwidth unde | `bench_stream3.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | cdee2c12f 2026-09-02 | no action |
| cpu-decode-roofline-program.md:235 | **C7 — make the placement fix permanent, everywhere a CPU model is loa | `evict_nodes.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | f276fc052 2026-09-03 | no action |
| cpu-decode-roofline-program.md:293 | **C9 — `llama-perplexity` returns NaN for qwen4exp; there is no PPL/KL | `agents/b4/gen_arm.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | dd39b5fff 2026-09-04 | no action |
| cpu-decode-roofline-program.md:293 | **C9 — `llama-perplexity` returns NaN for qwen4exp; there is no PPL/KL | `compare_gen.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | dd39b5fff 2026-09-04 | no action |
| cpu-decode-roofline-program.md:3407 | **UP-1 — upstream the two ggml contributions this campaign produced.** | `ggml-org/llama.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 8e17643f7 2026-09-07 | no action |
| cpu-decode-roofline-program.md:3433 | **HYG-1b — rebuild or remove EVERY stale build dir in the shared tree. | `scan_builds.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 8e17643f7 2026-09-07 | no action |
| cpu-decode-roofline-program.md:3693 | **B11 — CLOSED 2026-09-05 AS A NON-QUESTION. There is no missing 38%;  | `agents/prof/` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | fbce70494 2026-09-05 | no action |
| cpu-decode-roofline-program.md:3693 | **B11 — CLOSED 2026-09-05 AS A NON-QUESTION. There is no missing 38%;  | `gguf_inv.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | fbce70494 2026-09-05 | no action |
| cpu-decode-roofline-program.md:3740 | **INF-71 — EXL3 `mul1` trellis experts.** ⚠ **RENAMED 2026-09-07 from  | `turboderp/Qwen3.8-Flash-Next-exl3` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 8e17643f7 2026-09-07 | no action |
| cpu-decode-roofline-program.md:4073 | ~~INSTR-1 (original text)~~ — the co-residency sampler records PID + e | `reanchor2/arm.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | afc26c307 2026-09-04 | no action |
| cpu-decode-roofline-program.md:4158 | **BE-1 Phase 2 — THE FASTEST DEPLOYABLE CONFIGURATION.** ✅ 2026-09-04, | `pick.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | f29c573d2 2026-09-04 | no action |
| cpu-decode-roofline-program.md:534 | **B3 — restructure `mul_mat_id` for batch 1.** ✅ 2026-09-03 (both halv | `9e43dcbc8` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 58375c92c 2026-09-03 | no action |
| cpu-prefill-compute-large-models.md:139 | **PC-3 — symbolized target-selection pass ✅ 2026-07-19**: resolve the  | `597017da07b7fbe219d04036e9ca30d46654951b` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 121231e76 2026-07-19 | no action |
| decision-aware-routing.md:630 | **Pre-validated human-amendment token authored ✅ 2026-07-29**: `RATIFY | `outbox/mainB.jsonl` (path) | FP (bus runtime state, untracked by C45) | 72d27f396 2026-07-29 | no action |
| delegation-context-preassembly.md:42 | **DCP-2 — Budget-bounded assembly loop.** ✅ 2026-05-26 (flipped 2026-0 | `BudgetBands.codemap/editable/tests/task` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 32350755d 2026-07-14 | no action |
| evidence-plane-event-sourcing-and-narrative.md:102 | **W7 — session hygiene** (impl 4.3, ~half day, anytime): default `supp | `69a41f7` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 2fc118177 2026-06-13 | no action |
| evidence-plane-instrument-repair.md:88 | **W1 — ratchet + double-check hotfixes** (impl 0.1+0.2, ~1 day): `safe | `orchestration/autopilot_state.json` (path) | FP (gitignored runtime state) | a11438c2b 2026-06-12 | no action |
| evidence-plane-instrument-repair.md:95 | **W7 — item analytics** (impl 2.3, 2 days, zero inference): landed on  | `cb577e0` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | ae5d5ceeb 2026-06-12 | no action |
| evidence-plane-ledger-and-sequential-verdicts.md:324 | **W1 — qid + outcome vectors** (impl 1.1–1.2, ~1–2 days): derived stab | `3c17460` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 31580a073 2026-06-12 | no action |
| evidence-plane-ledger-and-sequential-verdicts.md:325 | **W2 — paired replay tool** (impl 1.3, ~1 day, zero inference): `scrip | `c67575b` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 31580a073 2026-06-12 | no action |
| fable5-window2-findings-05c-mi210-lever-category-matrix.md:199 | **N-gram / prompt-lookup on GPU** (L12) — **SUPERSEDED, do not run** ✅ | `a8afd338` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e9566988c 2026-08-12 | no action |
| fable5-window2-findings-05c-mi210-lever-category-matrix.md:231 | **Fused dequant-in-GEMV** (L3) ✅ 2026-07-14 — RESOLVED NON-TASK (a8afd | `a8afd338` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 32350755d 2026-07-14 | no action |
| frontier-f2-self-running-lab.md:21 | **W1 — job inventory** (1 day): `orchestration/lab_jobs.yaml`, one row | `8b4b24b` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | b06b94488 2026-06-13 | no action |
| frontier-f2-self-running-lab.md:22 | **W2 — the runner** (3–5 days) ✅ 2026-07-14 remaining acceptance met 2 | `450a366` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 32350755d 2026-07-14 | no action |
| frontier-f2-self-running-lab.md:22 | **W2 — the runner** (3–5 days) ✅ 2026-07-14 remaining acceptance met 2 | `5fad61d` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 32350755d 2026-07-14 | no action |
| gemma-challenge-kernel-techniques-v7.md:131 | **K7 — onegraph/shape-cache investigation + Lever A ✅ 2026-07-11**: Le | `llama.cpp-experimental/lever-a-shape-key.patch` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | cca45dbf8 2026-07-11 | no action |
| gemma-challenge-kernel-techniques-v7.md:420 | **K27.2 — generic Q8_0 8x8 opt-in retired; optimized path deferred ✅ 2 | `ggml-org/llama.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 486c8a5b1 2026-07-17 | no action |
| gemma-challenge-kernel-techniques-v7.md:485 | **K35.15 PaddleOCR-VL document-specialist smoke ✅ 2026-07-17**: Paddle | `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 2fde606e6 2026-07-17 | no action |
| gemma-challenge-kernel-techniques-v7.md:485 | **K35.15 PaddleOCR-VL document-specialist smoke ✅ 2026-07-17**: Paddle | `511b09642bb324401f15f97cc23bc67e8f0a291d` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 2fde606e6 2026-07-17 | no action |
| glm53-flash-evaluation.md:189 | T12c — Validate Q8 mode 2 (two weight rows across up to four activatio | `e8c93f6c` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | c6204daac 2026-09-09 | no action |
| gpu-cot-scaffold-sidecar.md:9 | **G3 prerequisite — exact Qwable IQ4_XS artifact restored and verified | `f35ea1502056a2886dd88fb8a29272f8f3c9c3a5` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 091b2052a 2026-07-28 | no action |
| gpu-serving-tie-in-program.md:63 | **P0-5** — program-authority relay sent to `inference` (the renamed Co | `../../coordination/session-bus/outbox/mainB.jsonl` (path) | FP (bus runtime state, untracked by C45) | 1acc96bd5 2026-07-29 | no action |
| harness-selection-and-integration.md:179 | **HS-5 — add a "weight-space RL adapter exists?" column to the HS-4 de | `weight_transfer.py:25` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 123433c2e 2026-07-29 | no action |
| harness-selection-and-integration.md:52 | **HS-1b — Hermes cooperation-surface audit** ✅ 2026-07-17 (A4, source- | `run_agent.py:4213` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 307f95eaf 2026-07-17 | no action |
| harness-selection-and-integration.md:53 | **HS-1c — OpenCode cooperation-surface audit** ✅ 2026-07-17 (A4, sourc | `packages/opencode/src/session/llm/request.ts:114-146` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 307f95eaf 2026-07-17 | no action |
| harness-selection-and-integration.md:53 | **HS-1c — OpenCode cooperation-surface audit** ✅ 2026-07-17 (A4, sourc | `packages/opencode/src/session/overflow.ts:28` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 307f95eaf 2026-07-17 | no action |
| harness-selection-and-integration.md:53 | **HS-1c — OpenCode cooperation-surface audit** ✅ 2026-07-17 (A4, sourc | `runner/model.ts:188-213` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 307f95eaf 2026-07-17 | no action |
| harness-selection-and-integration.md:53 | **HS-1c — OpenCode cooperation-surface audit** ✅ 2026-07-17 (A4, sourc | `packages/opencode/src/tool/task.ts` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 307f95eaf 2026-07-17 | no action |
| harness-selection-and-integration.md:57 | **HS-1d — oh-my-pi cooperation-surface audit** (intake-1148#06, source | `packages/coding-agent/src/config/models-config-schema-bundle.ts:47` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 1d8294b59 2026-08-18 | no action |
| harness-selection-and-integration.md:57 | **HS-1d — oh-my-pi cooperation-surface audit** (intake-1148#06, source | `packages/ai/src/providers/openai-shared.ts:721-722` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 1d8294b59 2026-08-18 | no action |
| harness-selection-and-integration.md:57 | **HS-1d — oh-my-pi cooperation-surface audit** (intake-1148#06, source | `openai-completions.ts:1733` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 1d8294b59 2026-08-18 | no action |
| harness-selection-and-integration.md:63 | **HS-1g — generalise the silent-no-op check into the Client Surface Au | `simple-options.js:11-12` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 49af91a00 2026-09-16 | no action |
| hermes-outer-shell.md:178 | Hermes skill authoring/install prep: Write EPYC-specific skills and ma | `~/.hermes/skills/epyc/` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 7826be15f 2026-07-06 | no action |
| hermes-outer-shell.md:265 | **B — `scripts/hermes/skills/check_drift.py` + pre-commit hook wire**  | `sync_from_swagger.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e8bb879da 2026-06-14 | no action |
| intake-derived-work-2026-07-25.md:19 | **ID-1 — GEPA reflective mutation is a guaranteed no-op, and has been  | `gepa/proposer/reflective_mutation/reflective_mutation.py:66-67` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | c942728ef 2026-07-25 | no action |
| intake-derived-work-2026-07-25.md:19 | **ID-1 — GEPA reflective mutation is a guaranteed no-op, and has been  | `reflective_mutation.py:67` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | c942728ef 2026-07-25 | no action |
| intake-derived-work-2026-07-25.md:19 | **ID-1 — GEPA reflective mutation is a guaranteed no-op, and has been  | `src/gepa/lm.py:49` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | c942728ef 2026-07-25 | no action |
| intake-derived-work-2026-07-25.md:203 | **ID-30 — Record `z-lab/Qwen3.5-122B-A10B-DFlash` (Apache-2.0) as a wa | `z-lab/Qwen3.5-122B-A10B-DFlash` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 4762625de 2026-07-30 | no action |
| intake-derived-work-2026-07-25.md:259 | **ID-35 — A false claim from `intake-580` is load-bearing in two activ | `649ece1` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 654bce6c6 2026-08-12 | no action |
| internal-kb-rag.md:397 | **K9 — Cross-encoder rerank stage.** ✅ CODE LANDED 2026-05-27; K7 meas | `reranking.py:62` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 472bdca3e 2026-05-27 | no action |
| internal-kb-rag.md:77 | **K7: Validation pass — Flywheel-template eval** (rewritten 2026-04-28 | `edba4d9` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | adc7e79d7 2026-06-13 | no action |
| learned-routing-controller.md:225 | **EPD-3-decision — DECIDED 2026-08-12: re-embed under one convention,  | `orchestration/repl_memory/sessions/` (path) | FP (gitignored runtime state) | 008f9d8c4 2026-08-12 | no action |
| learned-routing-controller.md:277 | **EPD-3-R2 — no live write site produces the canonical vector, so the  | `51aae08a` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e6bd74058 2026-09-14 | no action |
| learned-routing-controller.md:277 | **EPD-3-R2 — no live write site produces the canonical vector, so the  | `531f4890` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e6bd74058 2026-09-14 | no action |
| learned-routing-controller.md:277 | **EPD-3-R2 — no live write site produces the canonical vector, so the  | `80d975c1` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e6bd74058 2026-09-14 | no action |
| learned-routing-controller.md:277 | **EPD-3-R2 — no live write site produces the canonical vector, so the  | `a30ba0aa` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e6bd74058 2026-09-14 | no action |
| learned-routing-controller.md:291 | **EPD-3-R3 — two live writers still use foreign conventions. FIXED ✅ 2 | `531f4890` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e6bd74058 2026-09-14 | no action |
| learned-routing-controller.md:291 | **EPD-3-R3 — two live writers still use foreign conventions. FIXED ✅ 2 | `80d975c1` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e6bd74058 2026-09-14 | no action |
| learned-routing-controller.md:291 | **EPD-3-R3 — two live writers still use foreign conventions. FIXED ✅ 2 | `a30ba0aa` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | e6bd74058 2026-09-14 | no action |
| learned-routing-controller.md:479 | **P4.2** **Block-ε-separability diagnostic (medium cost)** — **COMPLET | `orchestration/repl_memory/training_data.npz` (path) | FP (gitignored runtime state) | 0ea32bbc8 2026-06-27 | no action |
| learned-routing-controller.md:482 | **P4.5** **Journal-derived soft-label SFT — zero-inference cold-start  | `orchestration/autopilot_journal.jsonl` (path) | FP (gitignored runtime state) | 1595bf71e 2026-06-26 | no action |
| learned-routing-controller.md:493 | **P5.1** **IRT discrimination scorer substrate (~80–100 LoC, ~2 sessio | `orchestration/repl_memory/training_data.npz` (path) | FP (gitignored runtime state) | 1b53aed0f 2026-06-27 | no action |
| learned-routing-controller.md:590 | **P6.2.3** Add `train_verifier_head.py`. Binary cross-entropy loss wit | `orchestration/repl_memory/verifier_head_weights.npz` (path) | FP (gitignored runtime state) | 21f2131b2 2026-05-21 | no action |
| log-linear-gated-deltanet-readiness.md:75 | Reference implementation (github.com/HanGuo97/log-linear-attention) in | `hattention/recurrent.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 40b873e2c 2026-08-12 | no action |
| loop-owned-fleet-implementation.md:183 | P2-0 Pre-create the POOL worktrees: `worktrees/pool/lane0..lane3` (ope | `worktrees/pool/lane0..lane3` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 649ea9e12 2026-08-16 | no action |
| loop-owned-fleet-implementation.md:425 | **`/workspace/repos/` was empty — the documented symlinks were gone.** | `/workspace/repos/` (path) | FP (gitignored runtime state) | 4ad13cb2c 2026-08-16 | no action |
| mi210-big-model-and-acceleration-roadmap.md:165 | **stream-K `nsm→k·nsm` + compact-LDS residual — zero-build artifact re | `kernels/fused-prefetch-NEGATIVE.patch` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 6fbb72917 2026-07-18 | no action |
| mi210-big-model-and-acceleration-roadmap.md:255 | **K28-R1 — Adopt the SGLang `fla/` four-stage decomposition as K28's n | `fla/cumsum.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | bedbd2fae 2026-08-11 | no action |
| mi210-big-model-and-acceleration-roadmap.md:255 | **K28-R1 — Adopt the SGLang `fla/` four-stage decomposition as K28's n | `fla/wy_fast.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | bedbd2fae 2026-08-11 | no action |
| mi210-big-model-and-acceleration-roadmap.md:255 | **K28-R1 — Adopt the SGLang `fla/` four-stage decomposition as K28's n | `fla/chunk_delta_h.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | bedbd2fae 2026-08-11 | no action |
| mi210-big-model-and-acceleration-roadmap.md:255 | **K28-R1 — Adopt the SGLang `fla/` four-stage decomposition as K28's n | `fla/chunk_o.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | bedbd2fae 2026-08-11 | no action |
| mi210-big-model-and-acceleration-roadmap.md:255 | **K28-R1 — Adopt the SGLang `fla/` four-stage decomposition as K28's n | `fla/chunk.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | bedbd2fae 2026-08-11 | no action |
| model-capability-descriptors.md:29 | **W1 — schema** (~1 day): `orchestration/model_descriptors.yaml`, one  | `578eb8a` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 7b63a561b 2026-06-12 | no action |
| multimodal-pipeline.md:292 | **S-1 — explain the Qwen3-TTS noise** ✅ 2026-07-31 — our port hand-rol | `qwentts.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | a5b8ac53f 2026-07-31 | no action |
| multimodal-pipeline.md:293 | **S-2 — get working speech synthesis on this host** ✅ 2026-07-31 — `qw | `qwentts.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | a5b8ac53f 2026-07-31 | no action |
| multimodal-pipeline.md:294 | **S-3 — build `qwentts.cpp` with HIP for gfx90a** ✅ 2026-07-31 — requi | `qwentts.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | a5b8ac53f 2026-07-31 | no action |
| non-inference-backlog.md:105 | **NIB2-50**: δ-mem Phase 1 setup (checkpoint + adapter download + thro | `eval_memoryagentbench.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 39adb2fe4 2026-06-13 | no action |
| non-inference-backlog.md:105 | **NIB2-50**: δ-mem Phase 1 setup (checkpoint + adapter download + thro | `eval_locomo.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 39adb2fe4 2026-06-13 | no action |
| non-inference-backlog.md:227 | **OBS-4** (MED): **`scripts/nightshift/run_wrapper.sh:79` reproduces t | `orchestration/.autopilot.lock` (path) | FP (gitignored runtime state) | f09ffe442 2026-08-23 | no action |
| non-inference-backlog.md:256 | **OBS-11** (MED): **A devcontainer rebuild silently disabled every ven | `~/.local/share/uv/python/` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 621cfeb1d 2026-08-19 | no action |
| non-inference-backlog.md:46 | **NIB2-12**: `parallel_seeding.py` + `seeding_port_sets.py` — [`routin | `parallel_seeding.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 5605e3d7b 2026-06-13 | no action |
| non-inference-backlog.md:46 | **NIB2-12**: `parallel_seeding.py` + `seeding_port_sets.py` — [`routin | `seeding_port_sets.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 5605e3d7b 2026-06-13 | no action |
| non-inference-backlog.md:49 | **NIB2-15**: Goedel-CP-8B GGUF conversion + Q4_K_M/Q8_0 quantization — | `858f3b5e04bf24aca3a1a113ea1889a4de9ed4ef` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 4bcf37b4b 2026-06-13 | no action |
| non-inference-backlog.md:81 | **NIB2-35** (added 2026-04-21): Persist `routing_meta.difficulty_*` +  | `seed_specialist_routing[_v2].py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | a389a4464 2026-04-21 | no action |
| numa-topology-cutover-resume-20260730.md:1172 | Speech kernels frozen, forked and genuinely off-host ✅ 2026-07-31 — `p | `pestopoppa/whisper.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 95bd7897b 2026-07-31 | no action |
| numa-topology-cutover-resume-20260730.md:1172 | Speech kernels frozen, forked and genuinely off-host ✅ 2026-07-31 — `p | `pestopoppa/qwentts.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 95bd7897b 2026-07-31 | no action |
| numa-topology-cutover-resume-20260730.md:1277 | **Contention matrix re-benched for the new topology.** ✅ 2026-08-01 —  | `171f86f9` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 7bd4aa004 2026-08-01 | no action |
| numa-topology-cutover-resume-20260730.md:1490 | **Migrate hardcoded `llama.cpp/build/bin` call sites to `kernel_paths. | `llama.cpp/build/bin` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 7bd4aa004 2026-08-01 | no action |
| numa-topology-cutover-resume-20260730.md:1566 | **W1-b. Re-derive all 76 edit-list anchors against current master.** ✅ | `scratchpad/editlist.md` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 7bd4aa004 2026-08-01 | no action |
| numa-topology-cutover-resume-20260730.md:875 | **Do not rebuild the C++ accelerator — its source is gone** ✅ 2026-07- | `qwentts.cpp` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | a5b8ac53f 2026-07-31 | no action |
| orchestration-robustness-audit-2026-07-11.md:191 | OP-1/P0.2 bridge code landed in `epyc-orchestrator`; focused tests rep | `orchestration/authority_consent.json` (path) | FP (gitignored runtime state) | 430f55d78 2026-07-16 | no action |
| per-request-reasoning-budget.md:238 | **PRB-T1** — Re-examine the standing `--jinja` removal workaround. It  | `Qwen/Qwen3.8-27B` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 612fbd99e 2026-08-21 | no action |
| promptforge-mutation-safety-contract.md:25 | **MHS-1 — Typed return-effect contract.** Constrain what a mutation ma | `code_runner.py:31-34` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e6bd74058 2026-09-14 | no action |
| promptforge-mutation-safety-contract.md:35 | **MHS-2 — Close the MH-9 inertness hole.** The AutoMem `schema_evoluti | `code_runner.py:64-103` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e6bd74058 2026-09-14 | no action |
| reasoning-effort-levels.md:309 | **RP-1 — Repetition-penalty probe ✅ 2026-07-23:** `repeat_penalty 1.1` | `probe_reppen.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 0ab297804 2026-07-23 | no action |
| reasoning-effort-levels.md:381 | **E-6 — Interaction with the `<think>` axis.** ✅ 2026-07-21. Effort (p | `run_budget.sh` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | e584492fe 2026-07-21 | no action |
| rocm-verify-profile-backend.md:149 | **HIP arm minimum loop closure (after the Triton loop works).** ✅ 2026 | `2dbbf1d3` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 6207e528f 2026-08-12 | no action |
| rocm-verify-profile-backend.md:1624 | **Z14 (Z) — DONE 2026-08-23: filed as [fla-org/flash-linear-attention# | `bc3b101dcb713ddc5bd8924b66754eb68b5ccf89` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 8ab6eaa2e 2026-08-23 | no action |
| rocm-verify-profile-backend.md:1624 | **Z14 (Z) — DONE 2026-08-23: filed as [fla-org/flash-linear-attention# | `fused_kl_div.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 8ab6eaa2e 2026-08-23 | no action |
| rocm-verify-profile-backend.md:1624 | **Z14 (Z) — DONE 2026-08-23: filed as [fla-org/flash-linear-attention# | `fused_linear_cross_entropy.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 8ab6eaa2e 2026-08-23 | no action |
| rocm-verify-profile-backend.md:1624 | **Z14 (Z) — DONE 2026-08-23: filed as [fla-org/flash-linear-attention# | `conv/triton/kernels.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 8ab6eaa2e 2026-08-23 | no action |
| rocm-verify-profile-backend.md:361 | Adopt the SOL-ExecBench task/scoring schema {entry_point kernel.py::ru | `provenance.py:72-157` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | b8abe1028 2026-07-22 | no action |
| rocm-verify-profile-backend.md:381 | **RVP-1 — Adopt the three-table output contract as the C4 report spec* | `scripts/analyze_llm_torch_profile.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | c5445031a 2026-08-11 | no action |
| rocm-verify-profile-backend.md:541 | **RVP-C2-2 — Property layer (the only axis independent of the sibling) | `7c1dfca1` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 8c3828961 2026-08-26 | no action |
| scoring-infra-standardization.md:322 | **Check the working tree the agent sees.** Our own repo carries `CLAUD | `/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl` (path) | FP (gitignored runtime state) | 654bce6c6 2026-08-12 | no action |
| searxng-search-backend.md:361 | **Correct two now-outdated objections in the notes** ✅ 2026-07-29 — ve | `7bd7f66de8a5b9dc391eae2fe382d3392631c3c3` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | b81bc2358 2026-07-29 | no action |
| searxng-search-backend.md:362 | **The decisive objection strengthened** ✅ 2026-07-29 — verified agains | `7bd7f66de8a5b9dc391eae2fe382d3392631c3c3` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 49d6e4168 2026-07-29 | no action |
| searxng-search-backend.md:363 | For **CA-6 (Camofox escalation)**, consider Firecrawl's **ranked engin | `7bd7f66de8a5b9dc391eae2fe382d3392631c3c3` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 3a81cfe87 2026-07-29 | no action |
| session-bus-thin-dispatcher.md:1447 | **C26 — the coordinator-daemon's `status` reports a live daemon from a | `heartbeats/coordinator-daemon.json` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 01142ba59 2026-07-29 | no action |
| session-bus-thin-dispatcher.md:1469 | **C27 — two operator SIGNATURE REQUESTS were never relayed, and the do | `inbox/coordinator-agent.jsonl` (path) | FP (bus runtime state, untracked by C45) | 01142ba59 2026-07-29 | no action |
| session-bus-thin-dispatcher.md:1469 | **C27 — two operator SIGNATURE REQUESTS were never relayed, and the do | `tokens/token-queue.md` (path) | FP (bus runtime state, untracked by C45) | 01142ba59 2026-07-29 | no action |
| session-bus-thin-dispatcher.md:2332 | **C44 — the token relay is WITHDRAWAL-BLIND: a gate whose own requeste | `tokens/token-queue.md:365` (path) | FP (bus runtime state, untracked by C45) | 7b4e0ac1e 2026-08-12 | no action |
| session-bus-thin-dispatcher.md:526 | **R8 — consolidated unblock artifact.** ✅ 2026-07-27 — | `tokens/token-queue.md` (path) | FP (bus runtime state, untracked by C45) | 6b19f206e 2026-07-27 | no action |
| session-bus-thin-dispatcher.md:593 | **M1 — skeleton + manual round-trip.** ✅ 2026-07-27 — layout, `BUS_PRO | `tokens/token-queue.md` (path) | FP (bus runtime state, untracked by C45) | 69a31cc02 2026-07-27 | no action |
| session-bus-thin-dispatcher.md:725 | **C-OWN — the C-series needs a new owner.** **CURRENT OWNER: `mainD`,  | `coordination/session-bus/tasks/mainD-c-own-delivery-plane.md` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 01142ba59 2026-07-29 | no action |
| session-bus-thin-dispatcher.md:741 | **C23 — triage disposition should not require an identical payload per | `outbox/claude-gpu-lane.jsonl` (path) | FP (bus runtime state, untracked by C45) | 2949d6ae1 2026-08-11 | no action |
| shape-keyed-contention-gating.md:303 | **Corrected: the topology guard's assumed hash.** ✅ 2026-08-01 — this  | `171f86f9` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 7bd4aa004 2026-08-01 | no action |
| speculative-decoding-mtp-refresh.md:242 | **T3 — Qwen3.5-9B dense MTP: FUNCTIONALLY VERIFIED 2026-06-22; v7 MI21 | `unsloth/Qwen3.5-9B-MTP-GGUF` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 62c665e4b 2026-06-22 | no action |
| speculative-decoding-mtp-refresh.md:382 | **Watch-item: `z-lab/Qwen3.5-122B-A10B-DFlash` (apache-2.0)** targets  | `z-lab/Qwen3.5-122B-A10B-DFlash` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 4762625de 2026-07-30 | no action |
| standardized-stack-update-pipeline-finalization.md:247 | Fix the pre-existing `test_runtime_flag_spec.py` failures (3, `prefix_ | `src/runtime_flag_spec` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 4924a115d 2026-08-23 | no action |
| standardized-stack-update-pipeline-finalization.md:247 | Fix the pre-existing `test_runtime_flag_spec.py` failures (3, `prefix_ | `src/features` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 4924a115d 2026-08-23 | no action |
| tool-use-eval-contract.md:372 | **TU-DTAP-1 — Import a reviewed, bounded Apache-2.0 DTAP subset into a | `fd5a107aedb8971c346fc0e85d4789bf510e3f5f` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | a520cb0ec 2026-08-25 | no action |
| tool-use-eval-contract.md:399 | **TU-TC-1 — Malformed JSON tool-call arguments fail open to `{}`.** ✅  | `legal_agent_bench/agents/toolcall_json_repair.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 9c3b05dc6 2026-09-14 | no action |
| tool-use-eval-contract.md:399 | **TU-TC-1 — Malformed JSON tool-call arguments fail open to `{}`.** ✅  | `c98a1680` (sha) | FP (upstream pin / HF revision / digest / store row / GC'd pre-cherry-pick SHA whose landed twin is on main) | 9c3b05dc6 2026-09-14 | no action |
| unified-trace-memory-service.md:213 | **UTM-M4 — Mine the Apache-2.0 ReasoningBank repo for the three prompt | `induce_memory.py` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 4762625de 2026-07-30 | no action |
| vidya-belief-substrate-program.md:1478 | **SC61 — `claim_statement_binding/v1`, the producer for SC56's `attest | `epyc.vidya/frame/claim_statement_binding/v1` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 9787b1eda 2026-09-08 | no action |
| vidya-belief-substrate-program.md:1671 | **VB-AK-LEGACY-SERVING-FEEDBACK — connect original direct-serving obse | `serving-beliefs/feedback-ledger.jsonl` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | b2bda9399 2026-09-10 | no action |
| wrap-up-division-of-labor-policy.md:383 | Add compute request/window schemas, the reconstructible projection, gr | `coordination/session-bus/compute_ready.json` (path) | FP (external repo path, scratch script, runtime artifact, or prose) | 3c1c2d1bf 2026-08-23 | no action |
